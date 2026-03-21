# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Kill chain router — selects and composes kill chain layers for hostile requests.
from __future__ import annotations

from dataclasses import dataclass, field

from src.killchain.composer import ComposedPage, PageComposer
from src.utils.config import AppConfig


@dataclass
class KillChainResult:
    layers_activated: list[str] = field(default_factory=list)
    composed: ComposedPage | None = None
    final_html: str = ""
    use_slow_drip: bool = False
    canary_tokens: list[str] = field(default_factory=list)

    @property
    def layer_string(self) -> str:
        return ",".join(self.layers_activated)


class KillChainRouter:

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._composer = PageComposer(config)

    def route(
        self,
        path: str,
        session_id: str,
        query_string: str = "",
        referrer: str = "",
    ) -> KillChainResult:
        composed = self._composer.compose(
            path, session_id,
            query_string=query_string,
            referrer=referrer,
        )

        result = KillChainResult(
            layers_activated=composed.layers_activated,
            composed=composed,
            final_html=composed.html,
            use_slow_drip=self.config.tarpit.enabled,
            canary_tokens=composed.canary_tokens,
        )

        return result
