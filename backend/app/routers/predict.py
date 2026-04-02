from fastapi import APIRouter, Depends

from app.dependencies import get_predict_service
from app.dto.predict import PredictRequest, PredictResponse, ProductResponse
from app.services.predict import PredictService

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    service: PredictService = Depends(get_predict_service),
):
    return service.predict(body.text)


@router.post("/search", response_model=list[ProductResponse])
def predict_and_search(
    body: PredictRequest,
    service: PredictService = Depends(get_predict_service),
):
    prediction = service.predict(body.text)
    products = service.search_products(prediction.entities)
    return products
