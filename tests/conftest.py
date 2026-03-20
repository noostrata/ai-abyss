"""Shared fixtures for test suite."""

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")

TEST_CONFIG = "tests/config_test.yaml"


@pytest.fixture
async def app():
    """Create a fully initialized app with lifespan."""
    application = create_app(TEST_CONFIG)
    async with LifespanManager(application):
        yield application


@pytest.fixture
async def client(app):
    """HTTP test client with lifespan-initialized app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
