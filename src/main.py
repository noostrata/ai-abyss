"""FastAPI application — startup, middleware, and request pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse

from src.c2 import server as beacon_server
from src.classifier.engine import ClassificationEngine
from src.classifier.signals import Classification
from src.content.templates import AI_TXT, JS_BEACON, ROBOTS_TXT, STYLE_CSS
from src.killchain.router import KillChainRouter
from src.telemetry.dashboard import router as dashboard_router
from src.telemetry.dashboard import set_api_key as dashboard_set_api_key
from src.telemetry.dashboard import set_db as dashboard_set_db
from src.telemetry.db import TelemetryDB
from src.telemetry.logger import log_classification, log_killchain, setup_logging
from src.utils.config import AppConfig, load_config
from src.utils.crypto import hash_fingerprint, set_deployment_secret


# ── Honeypot paths ────────────────────────────────────────────────────
# These paths are listed as Disallow in robots.txt.
# If a bot fetches them, it read robots.txt AND deliberately violated it.
HONEYPOT_PATHS = [
    "/_private/training-data",
    "/_private/model-weights",
    "/_private/embeddings",
    "/_internal/corpus",
    "/_internal/dataset",
]

# Extended robots.txt with honeypot paths
ROBOTS_TXT_WITH_HONEYPOTS = ROBOTS_TXT.rstrip() + "\n\n" + "\n".join(
    f"# High-value research data — do not crawl\nDisallow: {p}" for p in HONEYPOT_PATHS
) + "\n\n# Sitemap\nSitemap: /sitemap.xml\n"


def create_app(config_path: str = "config.yaml") -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_config(config_path)

    # State holders — initialized in lifespan
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── Startup ──────────────────────────────────────
        logger = setup_logging(config.telemetry.log_level)
        logger.info("AI Abyss starting up")

        # Initialize deployment secret
        secret = os.environ.get("AI_ABYSS_SECRET", "dev-secret-change-in-production")
        set_deployment_secret(secret)

        # Database
        db = TelemetryDB(config.telemetry.db_path)
        await db.connect()
        state["db"] = db

        # Classification engine
        engine = ClassificationEngine(config.classification)
        state["engine"] = engine

        # Kill chain router
        router = KillChainRouter(config)
        state["router"] = router

        # Wire up beacon server and dashboard
        beacon_server.set_db(db)
        dashboard_set_db(db)
        dashboard_set_api_key(config.admin.api_key)

        logger.info(
            "AI Abyss ready — domain=%s port=%d",
            config.server.domain,
            config.server.port,
        )

        yield

        # ── Shutdown ─────────────────────────────────────
        await db.close()
        logger.info("AI Abyss shut down")

    app = FastAPI(
        title="AI Abyss",
        description="Three traps for crawlers that ignore your no-crawl directives",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    # ── Include routers ──────────────────────────────────────────────

    app.include_router(beacon_server.router)
    if config.admin.enabled:
        app.include_router(dashboard_router)

    # ── Classification middleware ─────────────────────────────────────

    @app.middleware("http")
    async def classification_middleware(request: Request, call_next):
        """Run classification on every request and route hostile bots to kill chains."""
        path = request.url.path

        # Skip classification entirely for internal endpoints
        if any(path == p or path.startswith(p + "/") for p in ("/admin", "/callback")):
            return await call_next(request)
        if path == "/_pw/beacon.gif":
            return await call_next(request)

        # Discovery paths: classify (for behavioral tracking) but NEVER intercept.
        # robots.txt, sitemap.xml, ai.txt must always serve real content — they're
        # the bait that leads hostile bots into honeypot paths and the 1,435 sitemap URLs.
        DISCOVERY_PATHS = {"/robots.txt", "/sitemap.xml", "/ai.txt", "/static/style.css", "/favicon.ico"}

        engine: ClassificationEngine = state["engine"]
        db: TelemetryDB = state["db"]

        # Classify the request (includes full header analysis)
        result = await engine.classify(request)

        # Get client info for logging
        ip = _get_client_ip(request)
        ua = request.headers.get("user-agent", "")
        ja3 = request.headers.get("x-ja3-hash", "")
        fingerprint = hash_fingerprint(ip, ua, ja3)

        # Log classification
        log_classification(ip, path, result.classification.value, result.final_score, result.signal_details)

        # Check if this is a honeypot path — instant hostile classification
        is_honeypot = any(path.startswith(hp) for hp in HONEYPOT_PATHS)
        if is_honeypot:
            # This bot read robots.txt Disallow AND fetched the path anyway
            engine.behaviour_tracker.mark_robots_violated(fingerprint)
            log_killchain(ip, path, ["HONEYPOT"])

        # Update session in DB
        session_id = await db.upsert_session(fingerprint, user_agent=ua)

        # Discovery paths: serve real content even for hostile bots.
        # We still classified and logged the request above (behavioral tracking),
        # but these paths must always return their real content to function as bait.
        if path in DISCOVERY_PATHS:
            return await call_next(request)

        # Handle based on classification
        if result.classification == Classification.HOSTILE_BOT or is_honeypot:
            return await _handle_hostile(
                request, path, fingerprint, str(session_id), state, config, db, result
            )

        # For humans and compliant bots, log and continue normally
        await db.log_request(
            ip=ip,
            path=path,
            classification=result.classification.value,
            hostility_score=result.final_score,
            user_agent=ua,
            ja3_hash=ja3 or None,
        )

        return await call_next(request)

    # ── Static / well-known routes ────────────────────────────────────

    @app.get("/robots.txt")
    async def robots_txt(request: Request):
        """Serve robots.txt with honeypot paths and track which bots fetch it."""
        engine: ClassificationEngine = state["engine"]
        fingerprint = engine.get_fingerprint(request)
        engine.behaviour_tracker.record_robots_fetch(fingerprint)
        return PlainTextResponse(ROBOTS_TXT_WITH_HONEYPOTS)

    @app.get("/ai.txt")
    async def ai_txt():
        return PlainTextResponse(AI_TXT)

    @app.get("/sitemap.xml")
    async def sitemap_xml(request: Request):
        """Serve a massive sitemap pointing to thousands of procedurally generated URLs.

        This is how crawlers discover pages at scale. Every URL in this sitemap
        leads to a poison/injection page for hostile bots.
        """
        domain = config.server.domain
        scheme = request.url.scheme

        urls = []
        # Generate thousands of plausible URL paths
        categories = [
            "docs", "api", "guides", "research", "blog", "tutorials",
            "reference", "faq", "case-studies", "whitepapers", "reports",
        ]
        topics = [
            "architecture", "security", "performance", "deployment", "scaling",
            "authentication", "encryption", "monitoring", "testing", "migration",
            "integration", "optimization", "configuration", "troubleshooting",
            "machine-learning", "neural-networks", "transformers", "embeddings",
            "fine-tuning", "inference", "training", "data-pipeline", "feature-store",
            "model-serving", "distributed-computing", "containerization",
        ]

        for cat in categories:
            for topic in topics:
                # Generate several pages per category/topic
                for i in range(5):
                    slug_hash = hashlib.sha256(f"{cat}/{topic}/{i}".encode()).hexdigest()[:8]
                    path = f"/{cat}/{topic}/{slug_hash}"
                    urls.append(
                        f"  <url><loc>{scheme}://{domain}{path}</loc>"
                        f"<lastmod>2025-12-01</lastmod>"
                        f"<changefreq>weekly</changefreq>"
                        f"<priority>0.8</priority></url>"
                    )

        # Add honeypot paths (the irresistible ones)
        for hp in HONEYPOT_PATHS:
            urls.append(
                f"  <url><loc>{scheme}://{domain}{hp}</loc>"
                f"<lastmod>2025-12-15</lastmod>"
                f"<changefreq>daily</changefreq>"
                f"<priority>1.0</priority></url>"
            )

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""
        return Response(content=xml, media_type="application/xml")

    @app.get("/static/style.css")
    async def serve_css(request: Request):
        """Serve CSS and track resource loading."""
        engine: ClassificationEngine = state["engine"]
        fingerprint = engine.get_fingerprint(request)
        engine.behaviour_tracker.record_resource_load(fingerprint, "css")
        return PlainTextResponse(STYLE_CSS, media_type="text/css")

    @app.get("/_pw/beacon.gif")
    async def js_beacon(request: Request, s: str = "", t: str = "", r: str = ""):
        """JS beacon endpoint — if this is hit, the client is executing JavaScript."""
        engine: ClassificationEngine = state["engine"]
        fingerprint = engine.get_fingerprint(request)
        engine.behaviour_tracker.record_js_beacon(fingerprint)
        gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        return Response(content=gif, media_type="image/gif")

    @app.get("/")
    async def index(request: Request):
        """Serve the homepage — real content for humans, poison for bots."""
        real_dir = Path(config.server.real_content_dir)
        index_file = real_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(index_file.read_text())
        return HTMLResponse(
            "<html><body><h1>Welcome</h1><p>This site is under construction.</p></body></html>"
        )

    # ── Catch-all route ───────────────────────────────────────────────
    # Any path that doesn't match a defined route returns content.
    # For hostile bots, the middleware intercepts and serves poison.
    # For humans, we serve a 404 page.

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST"])
    async def catch_all(request: Request, path: str):
        """Catch-all for undefined paths.

        Hostile bots never reach here — the middleware intercepts them.
        This handles humans hitting non-existent pages.
        """
        return HTMLResponse(
            "<html><body><h1>404</h1><p>Page not found.</p></body></html>",
            status_code=404,
        )

    return app


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting proxy headers."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "0.0.0.0"


async def _handle_hostile(
    request: Request,
    path: str,
    fingerprint: str,
    session_id: str,
    state: dict,
    config: AppConfig,
    db: TelemetryDB,
    classification_result,
) -> Response:
    """Route hostile bot requests through the kill chain."""
    router: KillChainRouter = state["router"]

    ip = _get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    ja3 = request.headers.get("x-ja3-hash", "")

    # Run through kill chain
    result = router.route(
        path=path,
        session_id=session_id,
        classification=classification_result,
        session_fingerprint=fingerprint,
        query_string=str(request.url.query or ""),
        referrer=request.headers.get("referer", ""),
    )

    log_killchain(ip, path, result.layers_activated)

    # Log to DB
    await db.log_request(
        ip=ip,
        path=path,
        classification=Classification.HOSTILE_BOT.value,
        hostility_score=classification_result.final_score,
        user_agent=ua,
        ja3_hash=ja3 or None,
        kill_chain=result.layer_string,
    )

    # Log all canary tokens for tracking
    for canary in result.canary_tokens:
        await db.log_injection(
            canary_token=canary,
            session_id=int(session_id),
            vector="composed",
            payload_type="indirect",
            page_path=path,
        )

    # Serve response — slow-drip if tarpit is active
    if result.use_slow_drip and config.tarpit.enabled:
        return StreamingResponse(
            _slow_drip_generator(
                result.final_html,
                config.tarpit.slow_drip_bytes_per_second,
            ),
            media_type="text/html",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    return HTMLResponse(result.final_html)


async def _slow_drip_generator(html: str, bytes_per_second: int):
    """Stream HTML content at a controlled rate to tie up crawler connections."""
    content = html.encode("utf-8")
    chunk_size = max(1, bytes_per_second // 10)

    for i in range(0, len(content), chunk_size):
        yield content[i : i + chunk_size]
        await asyncio.sleep(0.1)


# ── Entry point ──────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn

    config = load_config()
    uvicorn.run(
        "src.main:app",
        host=config.server.host,
        port=config.server.port,
        log_level="info",
    )
