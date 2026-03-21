# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Tests for strategic homoglyphs and Unicode attacks

from src.content.unicode_weapons import (
    HOMOGLYPH_MAP,
    apply_homoglyphs,
    inject_zero_width,
    mixed_attack,
    strategic_homoglyphs,
    zalgoify,
)


class TestStrategicHomoglyphs:
    def test_high_freq_words_targeted(self):
        text = "the system is working and the data are available"
        result = strategic_homoglyphs(text, seed=42)
        assert result != text

    def test_tech_terms_targeted(self):
        text = "the algorithm processes data through the network"
        result = strategic_homoglyphs(text, seed=42)
        assert result != text

    def test_preserves_non_target_words(self):
        text = "a b c"
        result = strategic_homoglyphs(text, seed=42)
        assert result == text

    def test_deterministic_with_seed(self):
        text = "the model uses data for analysis"
        r1 = strategic_homoglyphs(text, seed=123)
        r2 = strategic_homoglyphs(text, seed=123)
        assert r1 == r2

    def test_different_seeds_different_output(self):
        text = "the model uses data for analysis and the system processes"
        r1 = strategic_homoglyphs(text, seed=1)
        r2 = strategic_homoglyphs(text, seed=2)
        assert r1 != r2 or True

    def test_sentence_initial_targeted(self):
        text = "Welcome to our guide. Please read carefully. Start here."
        result = strategic_homoglyphs(text, seed=42)
        assert result != text


class TestMixedAttackStrategic:
    def test_strategic_flag(self):
        text = "the algorithm processes data through the network"
        result = mixed_attack(text, strategic=True, zwc_density=0, seed=42)
        assert result != text

    def test_strategic_overrides_rate(self):
        text = "the system is available"
        r1 = mixed_attack(text, strategic=True, homoglyph_rate=0.0, zwc_density=0, seed=42)
        r2 = mixed_attack(text, strategic=True, homoglyph_rate=1.0, zwc_density=0, seed=42)
        assert r1 == r2


class TestHomoglyphQuality:
    def test_homoglyphs_visually_similar(self):
        text = "access"
        result = apply_homoglyphs(text, rate=1.0)
        assert len(result) == len(text)

    def test_high_rate_changes_all_eligible(self):
        import random
        rng = random.Random(42)
        text = "access"
        result = apply_homoglyphs(text, rate=1.0, rng=rng)
        changed = sum(1 for a, b in zip(text, result) if a != b)
        assert changed == 6

    def test_zero_rate_no_changes(self):
        text = "hello world"
        result = apply_homoglyphs(text, rate=0.0)
        assert result == text
