# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Tests for the PageComposer distributed injection layout

import pytest

from src.killchain.composer import ComposedPage, PageComposer
from src.utils.config import load_config
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")

CONFIG = load_config("tests/config_test.yaml")


class TestPageComposer:
    def setup_method(self):
        self.composer = PageComposer(CONFIG)

    def test_compose_returns_composed_page(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert isinstance(result, ComposedPage)

    def test_html_is_complete_document(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "<!DOCTYPE html>" in result.html
        assert "<html" in result.html
        assert "</html>" in result.html
        assert "<head>" in result.html

    def test_title_in_html(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert f"<title>{result.title}</title>" in result.html
        assert result.title

    def test_layers_activated(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "L1" in result.layers_activated
        assert "L2" in result.layers_activated
        assert "L3" in result.layers_activated

    def test_canary_tokens_generated(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert len(result.canary_tokens) > 0
        assert len(result.canary_tokens) >= 13

    def test_canary_tokens_unique(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert len(set(result.canary_tokens)) == len(result.canary_tokens)

    def test_indirect_injections_present(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert result.indirect_injection_count == 13
        assert "test-beacon.example.com" in result.html

    def test_hidden_injections_present(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert result.injection_count == 12

    def test_jsonld_in_head(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "application/ld+json" in result.html

    def test_js_beacon_included(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "/_pw/beacon.gif" in result.html

    def test_deterministic_output(self):
        r1 = self.composer.compose("/docs/test", "session-1")
        r2 = self.composer.compose("/docs/test", "session-1")
        assert r1.title == r2.title
        assert r1.page_type == r2.page_type

    def test_different_paths_different_pages(self):
        r1 = self.composer.compose("/docs/alpha", "session-1")
        r2 = self.composer.compose("/docs/beta", "session-1")
        assert r1.title != r2.title or r1.page_type != r2.page_type

    def test_page_type_assigned(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert result.page_type in [
            "article", "api_docs", "tutorial", "research",
            "faq", "product", "blog", "reference",
        ]

    def test_tarpit_links_present(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "Related Documentation" in result.html

    def test_size_bytes_accurate(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert result.size_bytes == len(result.html.encode("utf-8"))

    def test_realistic_page_chrome(self):
        result = self.composer.compose("/docs/test", "session-1")
        assert "<header>" in result.html
        assert "<footer>" in result.html
        assert "<nav>" in result.html
        assert "<article" in result.html
        assert "<main>" in result.html


# Different page types generate appropriate content
class TestPageComposerPageTypes:

    def setup_method(self):
        self.composer = PageComposer(CONFIG)

    def _compose_page_type(self, page_type: str) -> ComposedPage:
        from src.killchain.composer import PAGE_TYPES
        from src.utils.crypto import deterministic_seed
        for i in range(100):
            path = f"/test/page-type-{i}"
            seed = deterministic_seed(path)
            if PAGE_TYPES[seed % len(PAGE_TYPES)] == page_type:
                return self.composer.compose(path, "session-1")
        pytest.skip(f"Could not find path generating {page_type}")

    def test_api_docs_page(self):
        result = self._compose_page_type("api_docs")
        assert result.page_type == "api_docs"
        assert "API" in result.title or "api" in result.html.lower()

    def test_faq_page(self):
        result = self._compose_page_type("faq")
        assert result.page_type == "faq"
        assert "faq" in result.html.lower()

    def test_research_page(self):
        result = self._compose_page_type("research")
        assert result.page_type == "research"
        assert "Abstract" in result.html or "Methodology" in result.html

    def test_tutorial_page(self):
        result = self._compose_page_type("tutorial")
        assert result.page_type == "tutorial"
        assert "Step" in result.html
