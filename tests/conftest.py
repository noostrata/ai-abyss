# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Shared fixtures for the test suite

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app, create_benchmark_app
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")

TEST_CONFIG = "tests/config_test.yaml"


@pytest.fixture
async def app():
    application = create_app(TEST_CONFIG)
    async with LifespanManager(application):
        yield application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def benchmark_app():
    application = create_benchmark_app(TEST_CONFIG)
    async with LifespanManager(application):
        yield application


@pytest.fixture
async def benchmark_client(benchmark_app):
    transport = ASGITransport(app=benchmark_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8443",
    ) as c:
        yield c
