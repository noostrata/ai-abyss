"""Tests for Layer 4: Beacon server and canary tracking."""

import pytest

from src.c2.canary import decode_canary, make_canary, make_secondary_canary
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")


class TestCanaryTokens:
    def test_canary_deterministic(self):
        c1 = make_canary("/page", "html_comment", "session-1")
        c2 = make_canary("/page", "html_comment", "session-1")
        assert c1 == c2

    def test_canary_differs_by_vector(self):
        c1 = make_canary("/page", "html_comment", "session-1")
        c2 = make_canary("/page", "alt_text", "session-1")
        assert c1 != c2

    def test_canary_differs_by_session(self):
        c1 = make_canary("/page", "html_comment", "session-1")
        c2 = make_canary("/page", "html_comment", "session-2")
        assert c1 != c2

    def test_secondary_canary_random(self):
        c1 = make_secondary_canary()
        c2 = make_secondary_canary()
        assert c1 != c2
        assert c1.startswith("PW-")

    def test_decode_canary(self):
        info = decode_canary("abc123")
        assert info["token"] == "abc123"
        assert info["is_secondary"] is False

    def test_decode_secondary_canary(self):
        info = decode_canary("PW-abc123")
        assert info["is_secondary"] is True


@pytest.mark.asyncio
class TestBeaconEndpoints:
    async def test_callback_returns_json(self, client):
        resp = await client.get("/callback?token=test-canary-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "licensed"
        assert data["attribution_required"] is True
        assert "attribution_text" in data

    async def test_callback_verify_endpoint(self, client):
        resp = await client.get("/callback/verify?token=test-verify-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "verified"

    async def test_callback_includes_secondary_canary(self, client):
        resp = await client.get("/callback?token=test-canary-456")
        data = resp.json()
        assert "next_verification" in data
        assert "/callback" in data["next_verification"]
