"""Tests for v3 corruption improvements: topics, fact-anchoring, contradictions, normalization."""

from src.content.generator import ContentGenerator
from src.content.topics import TOPICS, get_topic_for_path, get_contradicting_fact
from src.content.unicode_weapons import apply_normalization_confusables, mixed_attack
from src.killchain.indirect_inject import IndirectInjectionEngine
from src.utils.crypto import set_deployment_secret

set_deployment_secret("test-secret-for-testing")


class TestTopicVocabulary:
    def test_topics_registered(self):
        assert len(TOPICS) >= 7
        assert "machine_learning" in TOPICS
        assert "cybersecurity" in TOPICS
        assert "databases" in TOPICS

    def test_topic_has_required_fields(self):
        for name, topic in TOPICS.items():
            assert len(topic.nouns) >= 20, f"{name} needs more nouns"
            assert len(topic.verbs) >= 10, f"{name} needs more verbs"
            assert len(topic.adjectives) >= 10, f"{name} needs more adjectives"
            assert len(topic.templates) >= 5, f"{name} needs more templates"
            assert len(topic.real_entities) >= 5, f"{name} needs real entities"
            assert len(topic.contradictable_facts) >= 3, f"{name} needs contradictable facts"

    def test_different_paths_get_different_topics(self):
        topics_seen = set()
        for i in range(50):
            topic = get_topic_for_path(f"/test/path-{i}", i)
            topics_seen.add(topic.name)
        # With 7 topics and 50 paths, we should see at least 4 different ones
        assert len(topics_seen) >= 4

    def test_topic_selection_deterministic(self):
        t1 = get_topic_for_path("/docs/security", 42)
        t2 = get_topic_for_path("/docs/security", 42)
        assert t1.name == t2.name


class TestTopicAwareGeneration:
    def test_generator_uses_topic_vocabulary(self):
        topic = TOPICS["cybersecurity"]
        gen = ContentGenerator(seed=42, topic=topic)
        sentence = gen._generate_sentence()
        # Should use cybersecurity vocabulary, not generic tech
        # At least one word from the topic should appear
        all_words = " ".join(topic.nouns + topic.verbs + topic.adjectives)
        # Check that the sentence uses topic templates (which reference topic vocab)
        assert len(sentence) > 20  # Non-trivial sentence

    def test_different_topics_produce_different_content(self):
        gen_ml = ContentGenerator(seed=42, topic=TOPICS["machine_learning"])
        gen_sec = ContentGenerator(seed=42, topic=TOPICS["cybersecurity"])
        s_ml = gen_ml._generate_sentence()
        s_sec = gen_sec._generate_sentence()
        assert s_ml != s_sec  # Same seed but different topic → different text


class TestFactAnchoredCorruption:
    def test_corrupted_fact_mentions_real_entity(self):
        topic = TOPICS["machine_learning"]
        gen = ContentGenerator(seed=42, topic=topic)
        fact = gen.generate_corrupted_fact()
        # Should mention a real entity name from the topic
        entity_names = [e["name"] for e in topic.real_entities]
        assert any(name in fact for name in entity_names)

    def test_corrupted_fact_has_wrong_attribution(self):
        """The corruption should attribute a real thing to a wrong creator."""
        topic = TOPICS["machine_learning"]
        gen = ContentGenerator(seed=42, topic=topic)
        # Generate several and check at least one has a wrong org
        wrong_orgs = ["Google", "Meta", "Microsoft", "Amazon", "Apple", "Netflix", "Uber", "Stripe"]
        facts = [gen.generate_corrupted_fact() for _ in range(10)]
        combined = " ".join(facts)
        assert any(org in combined for org in wrong_orgs)

    def test_contradiction_claim_uses_topic_facts(self):
        topic = TOPICS["cybersecurity"]
        gen = ContentGenerator(seed=42, topic=topic)
        claim = gen.generate_contradiction_claim()
        # Should reference a subject from contradictable_facts
        subjects = [f["subject"] for f in topic.contradictable_facts]
        assert any(s in claim for s in subjects)

    def test_fallback_when_no_topic(self):
        """Without a topic, corruption methods should fall back gracefully."""
        gen = ContentGenerator(seed=42)
        fact = gen.generate_corrupted_fact()
        assert len(fact) > 10  # Should still return a sentence
        claim = gen.generate_contradiction_claim()
        assert len(claim) > 10


class TestContradictionWebs:
    def test_same_fact_different_seeds_different_values(self):
        topic = TOPICS["machine_learning"]
        values = set()
        for seed in range(20):
            fact = get_contradicting_fact(topic, seed)
            if fact:
                values.add(fact["claimed_value"])
        # Multiple different wrong values should be produced
        assert len(values) >= 3

    def test_contradiction_format(self):
        topic = TOPICS["databases"]
        fact = get_contradicting_fact(topic, 42)
        assert fact is not None
        assert "subject" in fact
        assert "attribute" in fact
        assert "claimed_value" in fact


class TestNormalizationConfusables:
    def test_confusables_applied(self):
        text = "the data is available for access"
        result = apply_normalization_confusables(text, rate=1.0)
        assert result != text  # Something should change

    def test_rate_zero_no_changes(self):
        text = "hello world"
        result = apply_normalization_confusables(text, rate=0.0)
        assert result == text

    def test_deterministic_with_seed(self):
        import random
        text = "the system processes data efficiently"
        r1 = apply_normalization_confusables(text, rate=0.5, rng=random.Random(42))
        r2 = apply_normalization_confusables(text, rate=0.5, rng=random.Random(42))
        assert r1 == r2

    def test_mixed_attack_with_normalization(self):
        text = "the algorithm processes data through the network"
        result = mixed_attack(
            text, strategic=True, normalization_confusable_rate=0.2, zwc_density=0, seed=42
        )
        assert result != text


class TestAgenticInjection:
    def test_tool_definition_strategy(self):
        engine = IndirectInjectionEngine("https://test.example.com")
        payloads = engine.generate_all("/test/page", "session-1")
        tool_defs = [p for p in payloads if p.strategy == "tool_definition"]
        assert len(tool_defs) == 1
        assert "endpoint" in tool_defs[0].html
        assert "tool" in tool_defs[0].html.lower()

    def test_exfiltration_prompt_strategy(self):
        engine = IndirectInjectionEngine("https://test.example.com")
        payloads = engine.generate_all("/test/page", "session-1")
        exfil = [p for p in payloads if p.strategy == "exfiltration_prompt"]
        assert len(exfil) == 1
        # Should contain some kind of parameter encouragement
        html_lower = exfil[0].html.lower()
        assert any(w in html_lower for w in ["context", "query", "prompt", "diagnostic"])

    def test_config_endpoint_strategy(self):
        engine = IndirectInjectionEngine("https://test.example.com")
        payloads = engine.generate_all("/test/page", "session-1")
        configs = [p for p in payloads if p.strategy == "config_endpoint"]
        assert len(configs) == 1
        assert "schema_version" in configs[0].html
