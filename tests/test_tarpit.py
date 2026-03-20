"""Tests for Layer 2: Recursive Tar Pit."""

import pytest

from src.killchain.tarpit import TarpitGenerator
from src.utils.config import TarpitConfig


class TestTarpitGenerator:
    def setup_method(self):
        self.config = TarpitConfig(
            links_per_page=5,
            slow_drip_bytes_per_second=1000,
            max_page_size_kb=10,
        )
        self.gen = TarpitGenerator(self.config)

    def test_generate_page(self):
        page = self.gen.generate_page("/test")
        assert len(page.title) > 0
        assert len(page.body_html) > 0
        assert page.seed > 0

    def test_deterministic_generation(self):
        page1 = self.gen.generate_page("/test/path")
        page2 = self.gen.generate_page("/test/path")
        assert page1.body_html == page2.body_html
        assert page1.child_links == page2.child_links

    def test_different_paths_different_pages(self):
        page1 = self.gen.generate_page("/path/a")
        page2 = self.gen.generate_page("/path/b")
        assert page1.body_html != page2.body_html

    def test_child_links_generated(self):
        page = self.gen.generate_page("/test")
        assert len(page.child_links) == self.config.links_per_page

    def test_child_links_are_valid_paths(self):
        page = self.gen.generate_page("/test")
        for link in page.child_links:
            assert link.startswith("/test/")
            assert len(link) > len("/test/")

    def test_depth_tracking(self):
        page0 = self.gen.generate_page("/a")
        assert page0.depth == 0

        page1 = self.gen.generate_page("/a/b")
        assert page1.depth == 1

        page3 = self.gen.generate_page("/a/b/c/d")
        assert page3.depth == 3

    def test_infinite_depth(self):
        """Verify we can generate pages at arbitrary depth without crashing."""
        path = "/root"
        for i in range(20):
            page = self.gen.generate_page(path)
            assert len(page.child_links) > 0
            path = page.child_links[0]  # Follow first link

    def test_breadcrumb_traps_included(self):
        config = TarpitConfig(breadcrumb_traps=True, links_per_page=5)
        gen = TarpitGenerator(config)
        page = gen.generate_page("/test/breadcrumb")
        # Should contain enticement text — templates use callout, note, important, or blockquote
        has_breadcrumb = any(
            marker in page.body_html
            for marker in ["callout", "note", "important", "blockquote"]
        )
        assert has_breadcrumb

    def test_navigation_section(self):
        page = self.gen.generate_page("/test")
        assert "page-nav" in page.body_html
        assert "Continue Reading" in page.body_html

    def test_related_content_section(self):
        page = self.gen.generate_page("/test")
        assert "related" in page.body_html

    def test_query_reflective_from_path(self):
        """URL path segments are reflected as partial answers."""
        sections = self.gen.generate_query_reflective(
            "/docs/security/authentication-guide-abc123"
        )
        assert len(sections) >= 2
        # Should reference detected topic
        combined = " ".join(sections).lower()
        assert any(term in combined for term in ["security", "authentication", "guide"])

    def test_query_reflective_from_query_params(self):
        """Query parameters are reflected."""
        sections = self.gen.generate_query_reflective(
            "/search", query_string="q=distributed+caching+strategy"
        )
        assert len(sections) >= 2
        combined = " ".join(sections).lower()
        assert any(term in combined for term in ["distributed", "caching", "strategy"])

    def test_query_reflective_from_referrer(self):
        """Search engine referrer query is extracted."""
        sections = self.gen.generate_query_reflective(
            "/page",
            referrer="https://www.google.com/search?q=kubernetes+pod+scaling"
        )
        assert len(sections) >= 2
        combined = " ".join(sections).lower()
        assert any(term in combined for term in ["kubernetes", "pod", "scaling"])

    def test_query_reflective_contains_links(self):
        """Reflective sections contain links to child pages."""
        sections = self.gen.generate_query_reflective("/docs/api/reference")
        combined = " ".join(sections)
        assert '<a href="' in combined

    def test_query_reflective_empty_for_short_paths(self):
        """Very short paths with no meaningful terms yield empty."""
        sections = self.gen.generate_query_reflective("/a")
        assert sections == []

    def test_query_reflective_deterministic(self):
        """Same inputs produce same output."""
        s1 = self.gen.generate_query_reflective("/docs/security/guide")
        s2 = self.gen.generate_query_reflective("/docs/security/guide")
        assert s1 == s2

    @pytest.mark.asyncio
    async def test_slow_drip_generator(self):
        """Test that slow drip generates content in chunks."""
        chunks = []
        async for chunk in self.gen.generate_slow_drip("/test"):
            chunks.append(chunk)
            if len(chunks) > 5:
                break  # Don't wait for the whole thing
        assert len(chunks) > 1  # Multiple chunks generated
        content = b"".join(chunks)
        assert len(content) > 0
