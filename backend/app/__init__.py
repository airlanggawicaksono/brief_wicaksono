from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401
from app.api.v1 import predict
from app.core.config.database import (
    create_schemas,
    get_engine,
    get_session_factory,
    shared_metadata,
)
from app.core.exceptions.base import AppException
from app.core.exceptions.handlers import app_exception_handler
from app.core.middleware import register_middleware
from app.seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = get_engine()
    session_factory = get_session_factory()

    create_schemas()
    shared_metadata.create_all(bind=engine)

    db = session_factory()
    try:
        seed_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="WPP API",
    description="AI-powered text to structured data",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "predict", "description": "Text -> structured output + data query"},
        {"name": "health", "description": "Health check"},
    ],
)

register_middleware(app)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(predict.router)


@app.get("/", tags=["health"])
def root():
    return {
        "message": "WPP API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
