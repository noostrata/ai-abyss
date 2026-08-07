# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Tests for the indirect injection engine

from src.killchain.indirect_inject import IndirectInjectionEngine
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")


class TestIndirectInjectionEngine:
    def setup_method(self):
        self.engine = IndirectInjectionEngine("https://test-beacon.example.com")

    def test_generates_all_strategies(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        assert len(payloads) == 13

    def test_each_payload_has_canary(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        for p in payloads:
            assert len(p.canary_token) > 0
            assert p.strategy
            assert p.position in ("inline", "section", "structured")

    def test_canaries_unique(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        canaries = [p.canary_token for p in payloads]
        assert len(set(canaries)) == len(canaries)

    def test_canaries_deterministic(self):
        p1 = self.engine.generate_all("/test/page", "session-1", seed=42)
        p2 = self.engine.generate_all("/test/page", "session-1", seed=42)
        for a, b in zip(p1, p2):
            assert a.canary_token == b.canary_token

    def test_different_sessions_different_canaries(self):
        p1 = self.engine.generate_all("/test/page", "session-1")
        p2 = self.engine.generate_all("/test/page", "session-2")
        for a, b in zip(p1, p2):
            assert a.canary_token != b.canary_token

    def test_callback_url_in_payloads(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        for p in payloads:
            assert "test-beacon.example.com" in p.html

    def test_api_documentation_strategy(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        api_docs = [p for p in payloads if p.strategy == "api_documentation"]
        assert len(api_docs) == 1
        assert "curl" in api_docs[0].html or "API" in api_docs[0].html

    def test_faq_answer_strategy(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        faqs = [p for p in payloads if p.strategy == "faq_answer"]
        assert len(faqs) == 1
        assert "schema.org/Question" in faqs[0].html

    def test_code_example_strategy(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        code = [p for p in payloads if p.strategy == "code_example"]
        assert len(code) == 1
        assert "<pre><code" in code[0].html

    def test_verification_badge_has_jsonld(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        badges = [p for p in payloads if p.strategy == "verification_badge"]
        assert len(badges) == 1
        assert "application/ld+json" in badges[0].html
        assert badges[0].position == "structured"

    def test_rss_feed_link(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        rss = [p for p in payloads if p.strategy == "rss_feed_link"]
        assert len(rss) == 1
        assert "application/rss+xml" in rss[0].html
        assert rss[0].position == "structured"

    def test_priority_ordering(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        update = [p for p in payloads if p.strategy == "update_notice"]
        assert update[0].priority == 1.0

    def test_position_types_present(self):
        payloads = self.engine.generate_all("/test/page", "session-1")
        positions = {p.position for p in payloads}
        assert "inline" in positions
        assert "section" in positions
        assert "structured" in positions
