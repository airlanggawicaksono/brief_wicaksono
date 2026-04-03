from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config.database import Base, engine, SessionLocal
from app.core.exceptions.base import AppException
from app.core.exceptions.handlers import app_exception_handler
from app.api.v1 import predict
from app.seed import seed_data
import app.models

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    seed_data(db)
finally:
    db.close()

app = FastAPI(
    title="WPP API",
    description="AI-powered text to structured data",
    version="0.1.0",
    openapi_tags=[
        {"name": "predict", "description": "Text → structured output + data query"},
        {"name": "health", "description": "Health check"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
