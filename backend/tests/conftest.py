from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def no_lifespan(_: FastAPI):
        yield

    app.router.lifespan_context = no_lifespan

    try:
        yield TestClient(app)
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()

