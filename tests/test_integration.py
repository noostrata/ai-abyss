"""Integration tests: full request flow from classification through kill chain."""

import pytest

from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")


@pytest.mark.asyncio
class TestFullFlow:
    async def test_human_gets_normal_content(self, client):
        """A request with a normal browser UA should get served normally."""
        resp = await client.get(
            "/",
            headers={
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "accept-language": "en-US,en;q=0.9",
                "accept": "text/html,application/xhtml+xml",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-dest": "document",
            },
        )
        assert resp.status_code == 200

    async def test_known_bot_ua_gets_poisoned(self, client):
        """A request with a known AI crawler UA should get kill-chained."""
        for i in range(4):
            resp = await client.get(
                f"/page/{i}",
                headers={"user-agent": "GPTBot/1.0"},
            )
        assert resp.status_code == 200
        body = resp.text
        assert "<!--" in body
        assert "application/ld+json" in body

    async def test_robots_txt_served(self, client):
        resp = await client.get("/robots.txt")
        assert resp.status_code == 200
        assert "GPTBot" in resp.text
        assert "Disallow: /" in resp.text

    async def test_ai_txt_served(self, client):
        resp = await client.get("/ai.txt")
        assert resp.status_code == 200
        assert "Disallow" in resp.text

    async def test_js_beacon_endpoint(self, client):
        resp = await client.get("/_pw/beacon.gif?s=1&t=123&r=abc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/gif"

    async def test_css_endpoint(self, client):
        resp = await client.get("/static/style.css")
        assert resp.status_code == 200
        assert "font-family" in resp.text

    async def test_admin_stats(self, client):
        resp = await client.get("/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data

    async def test_admin_health(self, client):
        resp = await client.get("/admin/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_hostile_bot_without_robots_check(self, client):
        """A bot that doesn't check robots.txt should be classified hostile via override."""
        for i in range(5):
            resp = await client.get(
                f"/articles/topic-{i}",
                headers={"user-agent": "python-requests/2.31.0"},
            )
        assert resp.status_code == 200
        body = resp.text
        assert "href=" in body
