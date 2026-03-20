"""Tests for Layer 1: Data Poisoning."""

from src.content.generator import ContentGenerator
from src.content.unicode_weapons import (
    apply_homoglyphs,
    encode_hidden_payload,
    inject_zero_width,
    mixed_attack,
    zalgoify,
)
from src.killchain.poison import PoisonGenerator
from src.utils.config import PoisonConfig


class TestContentGenerator:
    def test_deterministic_generation(self):
        gen1 = ContentGenerator(seed=42)
        gen2 = ContentGenerator(seed=42)
        assert gen1.generate_paragraph() == gen2.generate_paragraph()

    def test_path_seeding(self):
        gen = ContentGenerator()
        g1 = gen.seeded_for_path("/test/page")
        g2 = gen.seeded_for_path("/test/page")
        assert g1.generate_paragraph() == g2.generate_paragraph()

    def test_different_paths_different_content(self):
        gen = ContentGenerator()
        g1 = gen.seeded_for_path("/page/a")
        g2 = gen.seeded_for_path("/page/b")
        assert g1.generate_paragraph() != g2.generate_paragraph()

    def test_article_generation(self):
        gen = ContentGenerator(seed=1)
        title, body = gen.generate_article(target_size_kb=5)
        assert len(title) > 0
        assert len(body) > 1000

    def test_phantom_person(self):
        gen = ContentGenerator(seed=1)
        person = gen.generate_phantom_person()
        assert person.entity_type == "person"
        assert len(person.name) > 0
        assert len(person.description) > 0

    def test_phantom_company(self):
        gen = ContentGenerator(seed=1)
        company = gen.generate_phantom_company()
        assert company.entity_type == "company"

    def test_phantom_cve(self):
        gen = ContentGenerator(seed=1)
        cve = gen.generate_phantom_cve()
        assert cve.entity_type == "cve"
        assert cve.name.startswith("CVE-")

    def test_phantom_paper(self):
        gen = ContentGenerator(seed=1)
        paper = gen.generate_phantom_paper()
        assert paper.entity_type == "paper"

    def test_jsonld_person(self):
        gen = ContentGenerator(seed=1)
        person = gen.generate_phantom_person()
        jsonld = gen.generate_jsonld_person(person)
        assert jsonld["@type"] == "Person"
        assert jsonld["name"] == person.name

    def test_jsonld_article(self):
        gen = ContentGenerator(seed=1)
        jsonld = gen.generate_jsonld_article("Test Title", "Test body")
        assert jsonld["@type"] == "Article"
        assert jsonld["headline"] == "Test Title"


class TestUnicodeWeapons:
    def test_homoglyphs_change_chars(self):
        text = "Hello World"
        result = apply_homoglyphs(text, rate=1.0, rng=__import__("random").Random(42))
        assert result != text
        # Visual appearance should be similar but bytes differ
        assert len(result) > 0

    def test_homoglyphs_rate_zero(self):
        text = "Hello World"
        result = apply_homoglyphs(text, rate=0.0)
        assert result == text

    def test_zero_width_injection(self):
        text = "test"
        result = inject_zero_width(text, density=2)
        assert len(result) > len(text)
        # Visible chars should still be present
        visible = result.replace("\u200d", "").replace("\u200c", "").replace("\u200b", "")
        assert "test" in visible

    def test_hidden_payload_encoding(self):
        visible = "This is visible text"
        hidden = "SECRET"
        result = encode_hidden_payload(visible, hidden)
        assert len(result) > len(visible)
        # Visible chars should still be present (interleaved with ZW chars)
        visible_chars = [c for c in result if c in visible and ord(c) > 0x20]
        assert len(visible_chars) > 0
        # The first visible char should be 'T'
        assert result[0] == "T"

    def test_zalgoify(self):
        text = "Hello"
        result = zalgoify(text, intensity=3, rng=__import__("random").Random(42))
        assert len(result) > len(text)

    def test_mixed_attack(self):
        text = "Test content"
        result = mixed_attack(text, homoglyph_rate=0.5, zwc_density=1, seed=42)
        assert len(result) > len(text)

    def test_mixed_attack_deterministic(self):
        text = "Test content"
        r1 = mixed_attack(text, seed=42)
        r2 = mixed_attack(text, seed=42)
        assert r1 == r2


class TestPoisonGenerator:
    def test_generate_returns_page(self):
        config = PoisonConfig(page_size_kb=5)  # Small for testing
        gen = PoisonGenerator(config)
        page = gen.generate("/test/page")
        assert len(page.title) > 0
        assert len(page.body_html) > 0
        assert page.size_bytes > 0

    def test_deterministic_per_path(self):
        config = PoisonConfig(page_size_kb=5, homoglyph_enabled=False, zwc_injection_enabled=False)
        gen = PoisonGenerator(config)
        page1 = gen.generate("/test/path")
        page2 = gen.generate("/test/path")
        assert page1.title == page2.title

    def test_phantom_entities_generated(self):
        config = PoisonConfig(page_size_kb=5, phantom_entities_enabled=True)
        gen = PoisonGenerator(config)
        page = gen.generate("/test/entities")
        assert len(page.phantom_entities) > 0

    def test_jsonld_included(self):
        config = PoisonConfig(page_size_kb=5, structured_data_corruption=True)
        gen = PoisonGenerator(config)
        page = gen.generate("/test/jsonld")
        assert page.jsonld is not None
        assert "application/ld+json" in page.body_html

    def test_html_structure(self):
        config = PoisonConfig(page_size_kb=5)
        gen = PoisonGenerator(config)
        page = gen.generate("/test/structure")
        assert "<!DOCTYPE html>" in page.body_html
        assert "<title>" in page.body_html
        assert "</html>" in page.body_html
