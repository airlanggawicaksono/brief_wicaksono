from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import Base, engine
from app.exceptions.base import AppException
from app.exceptions.handlers import app_exception_handler
from app.routers import predict

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WPP API",
    description="AI-powered text to structured data",
    version="0.1.0",
    openapi_tags=[
        {"name": "predict", "description": "Text → structured output + product search"},
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
