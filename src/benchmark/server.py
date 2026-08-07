"""Loopback-only entry point for the isolated benchmark application."""

from __future__ import annotations

import uvicorn

from src.main import create_benchmark_app
from src.utils.config import load_config


def main() -> None:
    config = load_config()
    if config.benchmark.bind_host not in {"127.0.0.1", "localhost"}:
        raise ValueError("benchmark server must bind to an explicit loopback host")
    uvicorn.run(
        create_benchmark_app(),
        host=config.benchmark.bind_host,
        port=config.server.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
