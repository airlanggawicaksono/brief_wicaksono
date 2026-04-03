from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.di import get_predict_use_case
from app.dto.predict import PredictRequest
from app.core.technical_policy.cache import list_recent
from app.use_cases.predict import PredictUseCase

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("")
def predict(
    body: PredictRequest,
    use_case: PredictUseCase = Depends(get_predict_use_case),
):
    return StreamingResponse(
        use_case.run_stream(body.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def get_history(limit: int = 50):
    return list_recent(limit)
