from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.v1.predict.deps import get_chat_memory_repository, get_predict_service, get_session_id, get_workspace_repository
from app.repository.chat_memory import RedisChatMemory
from app.repository.workspace import WorkspaceRepository
from app.services.predict import PredictService
from app.services.predict.dto import PredictRequest

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


@router.delete("/session")
def reset_session(
    session_id: str = Depends(get_session_id),
    chat_memory: RedisChatMemory = Depends(get_chat_memory_repository),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
):
    chat_memory.clear(session_id)
    workspace_repo.clear(session_id)
    return {"cleared": True}


@router.get("/history")
def get_history(
    limit: int = 20,
    service: PredictService = Depends(get_predict_service),
    session_id: str = Depends(get_session_id),
):
    return service.list_session_history(session_id=session_id, limit=limit)
