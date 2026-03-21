# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Shared fixtures for the test suite

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app
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
