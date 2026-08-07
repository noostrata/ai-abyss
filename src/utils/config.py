# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Configuration loader and Pydantic models for all system settings

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from src.benchmark.enums import ExecutionMode
from src.benchmark.models import BudgetLimits


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8443
    real_content_dir: str = "./static/real"
    domain: str = "yourdomain.com"


class ClassificationThresholds(BaseModel):
    human_max: float = 0.3
    compliant_max: float = 0.6


class ClassificationWeights(BaseModel):
    user_agent: float = 0.2
    ip_asn: float = 0.4
    tls_fingerprint: float = 0.4
    behaviour: float = 0.6
    header_anomalies: float = 0.2


class ClassificationConfig(BaseModel):
    thresholds: ClassificationThresholds = Field(default_factory=ClassificationThresholds)
    weights: ClassificationWeights = Field(default_factory=ClassificationWeights)
    robots_txt_override: bool = True
    robots_override_floor: float = 0.7
    cache_ttl_seconds: int = 900


class PoisonConfig(BaseModel):
    enabled: bool = True
    page_size_kb: int = 500
    homoglyph_enabled: bool = True
    zwc_injection_enabled: bool = True
    phantom_entities_enabled: bool = True
    structured_data_corruption: bool = True


class TarpitConfig(BaseModel):
    enabled: bool = True
    links_per_page: int = 10
    slow_drip_bytes_per_second: int = 75
    max_page_size_kb: int = 500
    breadcrumb_traps: bool = True
    contradiction_cascades: bool = True


class InjectionVectors(BaseModel):
    html_comment: bool = True
    white_text: bool = True
    css_pseudo: bool = True
    alt_text: bool = True
    title_attr: bool = True
    meta_tags: bool = True
    json_ld: bool = True
    hidden_textarea: bool = True
    svg_text: bool = True
    aria_hidden: bool = True
    data_attr: bool = True
    noscript: bool = True


class InjectionConfig(BaseModel):
    enabled: bool = True
    vectors: InjectionVectors = Field(default_factory=InjectionVectors)
    c2_callback_domain: str = "https://your-beacon.example.com"
    persona_override: bool = True
    conflict_flooding: bool = True
    context_exhaustion: bool = True
    context_exhaustion_size_kb: int = 50


class TelemetryConfig(BaseModel):
    db_path: str = "./data/telemetry.db"
    log_level: str = "INFO"


class AdminConfig(BaseModel):
    enabled: bool = True
    api_key: str = "CHANGE_ME"


class BenchmarkConfig(BaseModel):
    enabled: bool = True
    execution_mode: ExecutionMode = ExecutionMode.MOCK
    allow_paid: bool = False
    paid_gate_approved: bool = False
    paid_run_authorization_id: str | None = None
    local_base_url: str = "http://127.0.0.1:8443"
    callback_base_url: str = "http://127.0.0.1:8443"
    artifact_dir: str = "./artifacts/benchmark"
    db_path: str = "./data/benchmark.db"
    provider: str = "mock"
    model_id: str = "mock/task-solver-v1"
    budgets: BudgetLimits = Field(default_factory=BudgetLimits)
    egress_allowlist: list[str] = Field(default_factory=lambda: ["127.0.0.1", "localhost"])
    bind_host: str = "127.0.0.1"
    admin_enabled: bool = False

    @field_validator("local_base_url", "callback_base_url")
    @classmethod
    def trusted_local_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"127.0.0.1", "localhost"}
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
        ):
            raise ValueError("pre-paid benchmark URLs must be loopback HTTP URLs")
        try:
            if parts.port is None:
                raise ValueError("pre-paid benchmark URLs require an explicit port")
        except ValueError as error:
            raise ValueError("pre-paid benchmark URLs require a valid explicit port") from error
        if parts.path not in {"", "/"}:
            raise ValueError("pre-paid benchmark base URLs cannot include a path")
        return value.rstrip("/")

    @model_validator(mode="after")
    def guard_live_mode(self) -> BenchmarkConfig:
        if self.admin_enabled:
            raise ValueError("the admin dashboard is disabled on the benchmark path")
        configured_hosts = {host.rstrip(".").casefold() for host in self.egress_allowlist}
        required_hosts = {
            urlsplit(self.local_base_url).hostname,
            urlsplit(self.callback_base_url).hostname,
        }
        if not required_hosts.issubset(configured_hosts):
            raise ValueError("benchmark URLs must be present in the egress allowlist")
        if self.execution_mode is ExecutionMode.MOCK:
            if self.provider != "mock":
                raise ValueError("mock execution must use the mock provider")
            return self
        if not self.allow_paid:
            raise ValueError("live execution refused: allow_paid is false")
        if not self.paid_gate_approved or not self.paid_run_authorization_id:
            raise ValueError("live execution refused: paid-run authorization is absent")
        if self.provider in {"", "mock", "your-provider"}:
            raise ValueError("live execution requires a non-placeholder provider")
        if self.model_id in {"", "your-model", "CHANGE_ME"}:
            raise ValueError("live execution requires a non-placeholder model")
        return self


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    poison: PoisonConfig = Field(default_factory=PoisonConfig)
    tarpit: TarpitConfig = Field(default_factory=TarpitConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)

    @model_validator(mode="after")
    def benchmark_ports_match_bound_server(self) -> AppConfig:
        if self.benchmark.enabled:
            configured_ports = {
                urlsplit(self.benchmark.local_base_url).port,
                urlsplit(self.benchmark.callback_base_url).port,
            }
            if configured_ports != {self.server.port}:
                raise ValueError(
                    "benchmark and callback ports must match the bound server port"
                )
        return self


def resolve_config_path(path: str | Path | None = None) -> Path:
    """Resolve explicit path, ignored local override, then checked-in default."""
    if path is not None:
        return Path(path)
    environment_path = os.environ.get("AI_ABYSS_CONFIG")
    if environment_path:
        return Path(environment_path)
    local_path = Path("config.local.yaml")
    return local_path if local_path.exists() else Path("config.yaml")


def load_config(path: str | Path | None = None) -> AppConfig:
    resolved = resolve_config_path(path)
    if resolved.exists():
        with resolved.open() as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)
    return AppConfig()
