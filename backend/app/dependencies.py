from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.repository.product import ProductRepository
from app.services.predict import PredictService


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_product_repo(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_predict_service(
    product_repo: ProductRepository = Depends(get_product_repo),
) -> PredictService:
    return PredictService(product_repo)
