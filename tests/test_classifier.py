# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Tests for the classification engine


from src.classifier.behaviour import BehaviourTracker
from src.classifier.fingerprint import FingerprintAnalyzer
from src.classifier.ip_reputation import IPReputationChecker
from src.classifier.signals import Classification, Signal, fuse_signals

# Signal fusion tests

class TestSignalFusion:
    def test_empty_signals_returns_human(self):
        result = fuse_signals([])
        assert result.classification == Classification.HUMAN

    def test_low_score_classified_human(self):
        signals = [Signal("ua", 0.1, 0.2), Signal("ip", 0.0, 0.4)]
        result = fuse_signals(signals)
        assert result.classification == Classification.HUMAN
        assert result.final_score < 0.3

    def test_medium_score_classified_compliant(self):
        signals = [Signal("ua", 0.5, 0.5), Signal("ip", 0.4, 0.5)]
        result = fuse_signals(signals)
        assert result.classification == Classification.COMPLIANT_BOT

    def test_high_score_classified_hostile(self):
        signals = [Signal("ua", 0.9, 0.5), Signal("ip", 0.8, 0.5)]
        result = fuse_signals(signals)
        assert result.classification == Classification.HOSTILE_BOT

    def test_robots_override_floors_score(self):
        signals = [Signal("ua", 0.1, 0.5), Signal("ip", 0.1, 0.5)]
        result = fuse_signals(signals, robots_override=True, robots_override_floor=0.7)
        assert result.final_score >= 0.7
        assert result.classification == Classification.HOSTILE_BOT
        assert result.robots_override is True

    def test_robots_override_doesnt_lower_score(self):
        signals = [Signal("ua", 0.9, 0.5), Signal("ip", 0.9, 0.5)]
        result = fuse_signals(signals, robots_override=True, robots_override_floor=0.7)
        assert result.final_score >= 0.7

    def test_weighted_average_normalization(self):
        signals = [
            Signal("ua", 1.0, 0.2),
            Signal("ip", 1.0, 0.4),
            Signal("tls", 1.0, 0.4),
            Signal("behav", 1.0, 0.6),
        ]
        result = fuse_signals(signals)
        assert 0.0 <= result.final_score <= 1.0

    def test_signal_details_preserved(self):
        signals = [Signal("ua", 0.5, 0.3, detail="test bot")]
        result = fuse_signals(signals)
        assert "ua" in result.signal_details


# Fingerprint analyzer tests

class TestFingerprintAnalyzer:
    def test_no_hash_returns_neutral(self):
        analyzer = FingerprintAnalyzer("nonexistent.json")
        result = analyzer.analyze(None)
        assert not result.matched
        assert result.confidence == 0.0

    def test_no_hash_score_zero(self):
        analyzer = FingerprintAnalyzer("nonexistent.json")
        assert analyzer.score(None) == 0.0

    def test_unknown_hash_mildly_suspicious(self):
        analyzer = FingerprintAnalyzer("nonexistent.json")
        score = analyzer.score("deadbeef1234")
        assert score == 0.3

    def test_known_bot_hash(self):
        analyzer = FingerprintAnalyzer("data/ja3_signatures.json")
        result = analyzer.analyze("b32309a26951912be7dba376398abc3b")
        assert result.matched
        assert result.is_bot

    def test_known_browser_hash(self):
        analyzer = FingerprintAnalyzer("data/ja3_signatures.json")
        result = analyzer.analyze("b20b44b18b853ef29ab773e921b03422")
        assert result.matched
        assert not result.is_bot


# IP reputation tests

class TestIPReputation:
    def test_known_openai_ip(self):
        checker = IPReputationChecker("data/ai_crawler_ips.json")
        score, rep = checker.score("20.15.240.5")
        assert rep.is_known_ai_range
        assert rep.org == "OpenAI"
        assert score > 0.5

    def test_unknown_ip(self):
        checker = IPReputationChecker("data/ai_crawler_ips.json")
        score, rep = checker.score("192.168.1.100")
        assert not rep.is_known_ai_range
        assert score == 0.0

    def test_invalid_ip(self):
        checker = IPReputationChecker("data/ai_crawler_ips.json")
        score, rep = checker.score("not-an-ip")
        assert not rep.is_known_ai_range
        assert score == 0.0


# Behaviour tracker tests

class TestBehaviourTracker:
    def test_new_session_score_zero(self):
        tracker = BehaviourTracker()
        assert tracker.score("test-fp") == 0.0

    def test_single_request_score_zero(self):
        tracker = BehaviourTracker()
        tracker.record_request("test-fp", "/page1")
        assert tracker.score("test-fp") == 0.0

    def test_no_js_beacon_increases_score(self):
        tracker = BehaviourTracker()
        for i in range(5):
            tracker.record_request("bot-fp", f"/page{i}")
        score = tracker.score("bot-fp")
        assert score > 0.0

    def test_js_beacon_lowers_score(self):
        tracker = BehaviourTracker()
        for i in range(5):
            tracker.record_request("human-fp", f"/page{i}")
        tracker.record_js_beacon("human-fp")
        tracker.record_resource_load("human-fp", "css")
        tracker.record_resource_load("human-fp", "image")
        score_human = tracker.score("human-fp")

        tracker2 = BehaviourTracker()
        for i in range(5):
            tracker2.record_request("bot-fp", f"/page{i}")
        score_bot = tracker2.score("bot-fp")

        assert score_human < score_bot

    def test_robots_fetch_tracked(self):
        tracker = BehaviourTracker()
        tracker.record_robots_fetch("test-fp")
        session = tracker.get_session("test-fp")
        assert session.robots_fetched

    def test_session_eviction(self):
        tracker = BehaviourTracker(session_ttl=0.0)
        tracker.record_request("old-fp", "/page")
        import time
        time.sleep(0.01)
        session = tracker.get_session("old-fp")
        assert session.total_requests == 0
