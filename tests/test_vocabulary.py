# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Tests for the vocabulary band system and page vocabulary builder

from src.content.vocabulary import (
    TOPIC_BANDS,
    TRANSITION_POOLS,
    HEDGE_POOLS,
    QUANTIFIER_POOLS,
    DISCOURSE_MARKER_POOLS,
    PageVocabulary,
    build_page_vocabulary,
)


# All topic bands are populated and valid
class TestVocabularyBands:

    EXPECTED_TOPICS = [
        "machine_learning", "cybersecurity", "cloud_infrastructure",
        "databases", "cryptography", "web_development",
        "distributed_systems", "quantum_computing", "bioinformatics",
    ]

    def test_all_topics_have_bands(self):
        for topic in self.EXPECTED_TOPICS:
            assert topic in TOPIC_BANDS, f"Missing bands for {topic}"
            assert len(TOPIC_BANDS[topic]) >= 6, f"{topic} has too few bands: {len(TOPIC_BANDS[topic])}"

    def test_bands_have_sufficient_vocabulary(self):
        for topic_name, bands in TOPIC_BANDS.items():
            for band in bands:
                assert len(band.nouns) >= 10, f"{topic_name}/{band.name} has too few nouns: {len(band.nouns)}"
                assert len(band.verbs) >= 8, f"{topic_name}/{band.name} has too few verbs: {len(band.verbs)}"
                assert len(band.adjectives) >= 8, f"{topic_name}/{band.name} has too few adjectives: {len(band.adjectives)}"

    def test_bands_have_unique_names(self):
        for topic_name, bands in TOPIC_BANDS.items():
            names = [b.name for b in bands]
            assert len(names) == len(set(names)), f"Duplicate band names in {topic_name}"


# Function word pools diversity
class TestFunctionWordPools:

    def test_transition_pool_count(self):
        assert len(TRANSITION_POOLS) >= 6

    def test_hedge_pool_count(self):
        assert len(HEDGE_POOLS) >= 5

    def test_quantifier_pool_count(self):
        assert len(QUANTIFIER_POOLS) >= 5

    def test_discourse_marker_pool_count(self):
        assert len(DISCOURSE_MARKER_POOLS) >= 4

    def test_pools_have_sufficient_entries(self):
        for pool in TRANSITION_POOLS:
            assert len(pool) >= 8
        for pool in HEDGE_POOLS:
            assert len(pool) >= 8
        for pool in QUANTIFIER_POOLS:
            assert len(pool) >= 8
        for pool in DISCOURSE_MARKER_POOLS:
            assert len(pool) >= 8


# Page vocabulary builder produces unique, valid vocabularies
class TestPageVocabularyBuilder:

    def test_returns_page_vocabulary(self):
        pv = build_page_vocabulary("machine_learning", 42)
        assert isinstance(pv, PageVocabulary)
        assert len(pv.nouns) > 0
        assert len(pv.verbs) > 0
        assert len(pv.adjectives) > 0
        assert len(pv.transitions) > 0
        assert len(pv.hedges) > 0
        assert len(pv.quantifiers) > 0

    def test_returns_none_for_unknown_topic(self):
        pv = build_page_vocabulary("nonexistent_topic", 42)
        assert pv is None

    def test_deterministic_for_same_seed(self):
        pv1 = build_page_vocabulary("databases", 123)
        pv2 = build_page_vocabulary("databases", 123)
        assert pv1.nouns == pv2.nouns
        assert pv1.verbs == pv2.verbs
        assert pv1.transitions == pv2.transitions

    def test_different_seeds_give_different_vocabularies(self):
        pv1 = build_page_vocabulary("cybersecurity", 1)
        pv2 = build_page_vocabulary("cybersecurity", 999)
        assert pv1.nouns != pv2.nouns or pv1.transitions != pv2.transitions

    def test_vocabulary_merges_multiple_bands(self):
        pv = build_page_vocabulary("machine_learning", 42)
        assert len(pv.nouns) >= 20

    def test_different_topics_give_different_vocabulary(self):
        pv_ml = build_page_vocabulary("machine_learning", 42)
        pv_db = build_page_vocabulary("databases", 42)
        ml_nouns = set(pv_ml.nouns)
        db_nouns = set(pv_db.nouns)
        overlap = len(ml_nouns & db_nouns) / len(ml_nouns | db_nouns)
        assert overlap < 0.1, f"Too much overlap between ML and DB vocabulary: {overlap}"
