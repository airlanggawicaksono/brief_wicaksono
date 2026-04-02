from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_predict_service
from app.dto.predict import PredictRequest, PredictResponse, ProductResponse
from app.services.predict import PredictService

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("")
def predict(
    body: PredictRequest,
    service: PredictService = Depends(get_predict_service),
):
    return StreamingResponse(
        service.predict_stream(body.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/search", response_model=list[ProductResponse])
def predict_and_search(
    body: PredictRequest,
    service: PredictService = Depends(get_predict_service),
):
    prediction = service.predict(body.text)
    products = service.search_products(prediction.entities)
    return products
