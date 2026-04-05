from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.services.predict import PredictService
from app.services.predict.dto import PredictRequest
from app.api.v1.predict.deps import get_predict_service, get_session_id

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("")
def predict(
    body: PredictRequest,
    service: PredictService = Depends(get_predict_service),
    session_id: str = Depends(get_session_id),
):
    response = StreamingResponse(
        service.run_stream(body.text, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )
    response.set_cookie("session_id", session_id, httponly=False, samesite="lax")
    return response


@router.get("/history")
def get_history(
    limit: int = 20,
    service: PredictService = Depends(get_predict_service),
    session_id: str = Depends(get_session_id),
):
    return service.list_session_history(session_id=session_id, limit=limit)
