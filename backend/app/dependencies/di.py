from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config.database import SessionLocal
from app.dependencies.providers.llm import LLMProvider
from app.repository.product import ProductRepository
from app.repository.audience import AudienceRepository
from app.repository.campaign import CampaignRepository
from app.repository.performance import PerformanceRepository
from app.services.extraction import ExtractionService
from app.services.predict import PredictService
from app.tools.data import create_tools
from app.use_cases.predict import PredictUseCase


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_llm_provider() -> LLMProvider:
    return LLMProvider()


def get_product_repo(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_audience_repo(db: Session = Depends(get_db)) -> AudienceRepository:
    return AudienceRepository(db)


def get_campaign_repo(db: Session = Depends(get_db)) -> CampaignRepository:
    return CampaignRepository(db)


def get_performance_repo(db: Session = Depends(get_db)) -> PerformanceRepository:
    return PerformanceRepository(db)


def get_tools(
    product_repo: ProductRepository = Depends(get_product_repo),
    audience_repo: AudienceRepository = Depends(get_audience_repo),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    performance_repo: PerformanceRepository = Depends(get_performance_repo),
) -> list:
    return create_tools(product_repo, audience_repo, campaign_repo, performance_repo)


def get_extraction_service(provider: LLMProvider = Depends(get_llm_provider)) -> ExtractionService:
    return ExtractionService(provider)


def get_predict_service(
    provider: LLMProvider = Depends(get_llm_provider),
    tools: list = Depends(get_tools),
) -> PredictService:
    return PredictService(provider, tools)


def get_predict_use_case(
    extraction: ExtractionService = Depends(get_extraction_service),
    predict: PredictService = Depends(get_predict_service),
) -> PredictUseCase:
    return PredictUseCase(extraction, predict)
