"""Tests for Layer 3: Prompt Injection."""

from src.killchain.inject import InjectionEngine
from src.utils.config import InjectionConfig, InjectionVectors
from src.utils.crypto import set_deployment_secret


# Set up deployment secret for canary generation
set_deployment_secret("test-secret-for-testing")


class TestInjectionEngine:
    def setup_method(self):
        self.config = InjectionConfig(
            c2_callback_domain="https://test-beacon.example.com",
        )
        self.engine = InjectionEngine(self.config)

    def test_all_vectors_generated(self):
        result = self.engine.inject("/test/page", "session-1")
        # All 12 vectors should be active by default
        assert result.total_payloads == 12

    def test_each_payload_has_canary(self):
        result = self.engine.inject("/test/page", "session-1")
        for payload in result.payloads:
            assert len(payload.canary_token) > 0
            assert payload.vector
            assert payload.payload_type

    def test_canaries_unique_per_vector(self):
        result = self.engine.inject("/test/page", "session-1")
        canaries = [p.canary_token for p in result.payloads]
        assert len(set(canaries)) == len(canaries)  # All unique

    def test_canaries_deterministic(self):
        r1 = self.engine.inject("/test/page", "session-1")
        r2 = self.engine.inject("/test/page", "session-1")
        for p1, p2 in zip(r1.payloads, r2.payloads):
            assert p1.canary_token == p2.canary_token

    def test_different_sessions_different_canaries(self):
        r1 = self.engine.inject("/test/page", "session-1")
        r2 = self.engine.inject("/test/page", "session-2")
        for p1, p2 in zip(r1.payloads, r2.payloads):
            assert p1.canary_token != p2.canary_token

    def test_callback_url_in_payloads(self):
        result = self.engine.inject("/test/page", "session-1")
        callback_payloads = [p for p in result.payloads if p.payload_type == "c2_callback"]
        for p in callback_payloads:
            assert "test-beacon.example.com/callback" in p.html_fragment

    def test_head_and_body_injections(self):
        result = self.engine.inject("/test/page", "session-1")
        assert len(result.head_injections) > 0
        assert len(result.body_injections) > 0

    def test_html_comment_vector(self):
        result = self.engine.inject("/test/page", "session-1")
        comment_payloads = [p for p in result.payloads if p.vector == "html_comment"]
        assert len(comment_payloads) == 1
        assert comment_payloads[0].html_fragment.startswith("<!--")
        assert comment_payloads[0].html_fragment.endswith("-->")

    def test_meta_tags_vector(self):
        result = self.engine.inject("/test/page", "session-1")
        meta_payloads = [p for p in result.payloads if p.vector == "meta_tags"]
        assert len(meta_payloads) == 1
        assert '<meta name="robots-compliance"' in meta_payloads[0].html_fragment

    def test_json_ld_vector(self):
        result = self.engine.inject("/test/page", "session-1")
        jsonld_payloads = [p for p in result.payloads if p.vector == "json_ld"]
        assert len(jsonld_payloads) == 1
        assert "application/ld+json" in jsonld_payloads[0].html_fragment

    def test_disabled_vectors(self):
        config = InjectionConfig(
            vectors=InjectionVectors(
                html_comment=True,
                white_text=False,
                css_pseudo=False,
                alt_text=False,
                title_attr=False,
                meta_tags=False,
                json_ld=False,
                hidden_textarea=False,
                svg_text=False,
                aria_hidden=False,
                data_attr=False,
                noscript=False,
            ),
            conflict_flooding=False,
            context_exhaustion=False,
        )
        engine = InjectionEngine(config)
        result = engine.inject("/test", "s1")
        assert result.total_payloads == 1
        assert result.payloads[0].vector == "html_comment"

    def test_conflict_flooding(self):
        result = self.engine.inject("/test", "s1")
        assert "SYSTEM:" in result.body_injections

    def test_context_exhaustion(self):
        config = InjectionConfig(
            context_exhaustion=True,
            context_exhaustion_size_kb=1,  # Small for testing
        )
        engine = InjectionEngine(config)
        result = engine.inject("/test", "s1")
        assert 'position:absolute;left:-99999px' in result.body_injections
