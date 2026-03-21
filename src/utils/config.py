# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Configuration loader and Pydantic models for all system settings

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


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


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    poison: PoisonConfig = Field(default_factory=PoisonConfig)
    tarpit: TarpitConfig = Field(default_factory=TarpitConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    path = Path(path)
    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)
    return AppConfig()
