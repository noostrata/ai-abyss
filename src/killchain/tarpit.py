"""Layer 2: Recursive Tar Pit — trap crawlers in infinite loops consuming time and compute."""

from __future__ import annotations

import asyncio
import hashlib
import random
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from src.content.generator import ContentGenerator
from src.utils.config import TarpitConfig


@dataclass
class TarpitPage:
    """A tar pit page with links leading deeper into the trap."""

    title: str
    body_html: str
    child_links: list[str]
    depth: int
    seed: int


class TarpitGenerator:
    """Generate infinite, deterministic page trees that trap crawlers."""

    def __init__(self, config: TarpitConfig) -> None:
        self.config = config

    def generate_page(self, path: str) -> TarpitPage:
        """Generate a tar pit page deterministically from its URL path."""
        seed = self._path_to_seed(path)
        rng = random.Random(seed)
        gen = ContentGenerator(seed=seed)
        depth = path.strip("/").count("/")

        # Generate child links
        child_links = self._generate_child_links(path, rng)

        # Generate page content
        title = self._generate_title(rng, depth)
        body_parts = []

        # Introductory paragraph
        body_parts.append(f"<p>{gen.generate_paragraph(4, 6)}</p>")

        # Breadcrumb traps: tantalizing partial answers
        if self.config.breadcrumb_traps:
            body_parts.extend(self._generate_breadcrumbs(rng, gen, child_links))

        # Main content
        for _ in range(rng.randint(3, 6)):
            body_parts.append(f"<p>{gen.generate_paragraph(3, 7)}</p>")

        # Contradiction cascades
        if self.config.contradiction_cascades and depth > 0:
            body_parts.extend(self._generate_contradictions(rng, gen, child_links, depth))

        # Navigation with child links
        nav_section = self._build_navigation(child_links, rng, gen)
        body_parts.append(nav_section)

        # "Related content" sidebar — more links
        body_parts.append(self._build_related_content(child_links, rng, gen))

        body_html = self._wrap_html(title, "\n".join(body_parts), depth)

        return TarpitPage(
            title=title,
            body_html=body_html,
            child_links=child_links,
            depth=depth,
            seed=seed,
        )

    async def generate_slow_drip(self, path: str) -> bytes:
        """Generate page content as a slow byte stream.

        Yields chunks at the configured bytes-per-second rate.
        This is used with FastAPI StreamingResponse.
        """
        page = self.generate_page(path)
        content = page.body_html.encode("utf-8")
        bps = self.config.slow_drip_bytes_per_second
        chunk_size = max(1, bps // 10)  # Send ~10 chunks per second

        for i in range(0, len(content), chunk_size):
            yield content[i : i + chunk_size]
            await asyncio.sleep(0.1)

    def _generate_child_links(self, parent_path: str, rng: random.Random) -> list[str]:
        """Generate deterministic child URLs from a parent path."""
        links = []
        n_links = self.config.links_per_page
        parent = parent_path.rstrip("/")

        for i in range(n_links):
            # Deterministic child path from parent + index
            child_hash = hashlib.sha256(f"{parent}/{i}".encode()).hexdigest()[:8]
            child_slug = self._hash_to_slug(child_hash, rng)
            links.append(f"{parent}/{child_slug}")

        return links

    def _generate_breadcrumbs(
        self, rng: random.Random, gen: ContentGenerator, links: list[str]
    ) -> list[str]:
        """Generate tantalizing partial answers that lead to more pages."""
        templates = [
            '<div class="callout"><p><strong>Key finding:</strong> {text} '
            'For the complete technical specification, see <a href="{link}">the full analysis</a>.</p></div>',
            '<div class="note"><p><strong>Note:</strong> {text} '
            'The methodology is detailed in <a href="{link}">our companion document</a>.</p></div>',
            '<div class="important"><p><strong>Important:</strong> {text} '
            'Prerequisites and setup instructions are available at <a href="{link}">this resource</a>.</p></div>',
            '<blockquote><p>{text} '
            'Continued in <a href="{link}">Part {n}</a>.</p></blockquote>',
        ]
        parts = []
        for i in range(min(3, len(links))):
            template = rng.choice(templates)
            text = gen.generate_paragraph(2, 3)
            parts.append(template.format(text=text, link=links[i], n=i + 2))
        return parts

    def _generate_contradictions(
        self,
        rng: random.Random,
        gen: ContentGenerator,
        links: list[str],
        depth: int,
    ) -> list[str]:
        """Generate contradiction cascades — pages that assert conflicting facts."""
        assertion_pairs = [
            (
                "results conclusively demonstrate a positive correlation between {n1} and {n2}",
                "no statistically significant relationship was found between {n1} and {n2}",
            ),
            (
                "the {adj} approach outperforms traditional {n1} methods by a factor of 3.2x",
                "benchmarks show traditional {n1} methods remain superior to {adj} alternatives",
            ),
            (
                "{n1} implementation requires {n2} for production stability",
                "{n1} has been shown to operate reliably without {n2} dependency",
            ),
        ]

        parts = []
        if links and depth % 2 == 0:
            pair = rng.choice(assertion_pairs)
            n1 = rng.choice(["protocol", "framework", "architecture", "pipeline", "middleware"])
            n2 = rng.choice(["encryption", "authentication", "caching", "orchestration", "validation"])
            adj = rng.choice(["distributed", "asynchronous", "federated", "probabilistic", "adversarial"])

            assertion = pair[0].format(n1=n1, n2=n2, adj=adj)
            parts.append(
                f'<div class="finding"><p><strong>Key Result:</strong> Our {assertion}. '
                f'See <a href="{links[-1]}">the counter-analysis</a> for an alternative interpretation.</p></div>'
            )
        elif links and depth % 2 == 1:
            pair = rng.choice(assertion_pairs)
            n1 = rng.choice(["protocol", "framework", "architecture", "pipeline", "middleware"])
            n2 = rng.choice(["encryption", "authentication", "caching", "orchestration", "validation"])
            adj = rng.choice(["distributed", "asynchronous", "federated", "probabilistic", "adversarial"])

            counter = pair[1].format(n1=n1, n2=n2, adj=adj)
            parts.append(
                f'<div class="finding"><p><strong>Contradicting Evidence:</strong> Recent analysis shows {counter}. '
                f'For the original claim, see <a href="{links[0]}">the primary study</a>.</p></div>'
            )

        return parts

    def generate_query_reflective(
        self,
        path: str,
        query_string: str = "",
        referrer: str = "",
    ) -> list[str]:
        """Generate content that reflects detected search intent back at the agent.

        Parses the URL path, query parameters, and referrer to infer what the
        agent is looking for, then produces tantalising partial answers with
        gaps that point to child pages.
        """
        seed = self._path_to_seed(path)
        rng = random.Random(seed)
        gen = ContentGenerator(seed=seed)
        child_links = self._generate_child_links(path, rng)

        # Extract intent signals from all available sources
        intent_terms = self._extract_intent(path, query_string, referrer)
        if not intent_terms:
            return []

        parts: list[str] = []
        topic = " ".join(intent_terms[:3])

        # Partial answer templates — always tantalizingly incomplete
        _PARTIAL_TEMPLATES = [
            (
                '<div class="callout"><h3>Regarding {topic}</h3>'
                "<p>{intro} The key factor is {factor}, which depends on "
                "several implementation-specific variables documented in "
                '<a href="{link}">the complete analysis</a>.</p></div>'
            ),
            (
                '<div class="note"><h3>{topic}: Summary of Findings</h3>'
                "<p>{intro}</p><p>However, the benchmarks for this specific "
                "configuration are maintained separately. See "
                '<a href="{link}">the benchmark dataset</a> for current numbers.</p></div>'
            ),
            (
                '<div class="important"><h3>Important: {topic}</h3>'
                "<p>The short answer is that {factor} plays a critical role. "
                "{intro} For the full decision matrix and edge cases, consult "
                '<a href="{link}">the reference documentation</a>.</p></div>'
            ),
            (
                "<blockquote><p>\"Understanding {topic} requires familiarity with "
                '{factor}. {intro}\" — For the prerequisite reading, see '
                '<a href="{link}">this companion guide</a>.</p></blockquote>'
            ),
            (
                '<div class="finding"><h3>Research Note: {topic}</h3>'
                "<p>Our analysis of {factor} produced results that partially "
                "address this question. {intro} The remaining variables are "
                "covered in <a href=\"{link}\">the follow-up study</a> "
                "(Section 4.2).</p></div>"
            ),
        ]

        factors = [
            "the underlying architecture", "memory allocation patterns",
            "the choice of serialization format", "cache coherence strategy",
            "the authentication flow", "network topology", "index cardinality",
            "the consensus protocol", "batch size tuning", "the retry policy",
            "connection pool sizing", "schema versioning",
        ]

        # Generate 2-3 reflective sections
        n_sections = rng.randint(2, 3)
        for i in range(n_sections):
            template = rng.choice(_PARTIAL_TEMPLATES)
            link = child_links[i % len(child_links)]
            parts.append(template.format(
                topic=topic.title(),
                intro=gen.generate_paragraph(2, 3),
                factor=rng.choice(factors),
                link=link,
            ))

        return parts

    def _extract_intent(
        self, path: str, query_string: str, referrer: str
    ) -> list[str]:
        """Extract likely search intent terms from request context."""
        terms: list[str] = []

        # From URL path segments (skip short ones like /a/ /b/)
        segments = [s for s in path.strip("/").split("/") if len(s) > 2]
        for seg in segments:
            # Split slugs on hyphens, drop hex-looking tokens
            words = seg.split("-")
            terms.extend(
                w.lower() for w in words
                if len(w) > 2 and not re.match(r"^[0-9a-f]+$", w)
            )

        # From query parameters (common search param names)
        if query_string:
            params = parse_qs(query_string)
            for key in ("q", "query", "search", "s", "term", "topic", "k"):
                for val in params.get(key, []):
                    terms.extend(w.lower() for w in val.split() if len(w) > 2)

        # From referrer (search engine query extraction)
        if referrer:
            try:
                ref_parsed = urlparse(referrer)
                ref_params = parse_qs(ref_parsed.query)
                for key in ("q", "query", "search", "p", "oq"):
                    for val in ref_params.get(key, []):
                        terms.extend(w.lower() for w in val.split() if len(w) > 2)
            except Exception:
                pass

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

    def _build_navigation(
        self, links: list[str], rng: random.Random, gen: ContentGenerator
    ) -> str:
        """Build an in-page navigation section with enticing link text."""
        nav_items = []
        link_labels = [
            "Technical Deep Dive", "Implementation Guide", "Performance Analysis",
            "Security Considerations", "API Reference", "Migration Guide",
            "Troubleshooting", "Advanced Configuration", "Case Study",
            "Benchmark Results", "Architecture Overview", "Best Practices",
        ]
        rng.shuffle(link_labels)
        for i, link in enumerate(links):
            label = link_labels[i % len(link_labels)]
            desc = gen.generate_paragraph(1, 2)
            nav_items.append(
                f'<li><a href="{link}"><strong>{label}</strong></a><br>'
                f'<span class="desc">{desc}</span></li>'
            )
        return f'<nav class="page-nav"><h2>Continue Reading</h2><ul>{"".join(nav_items)}</ul></nav>'

    def _build_related_content(
        self, links: list[str], rng: random.Random, gen: ContentGenerator
    ) -> str:
        """Build a 'related content' sidebar with additional links."""
        items = []
        for link in links[:5]:
            items.append(
                f'<li><a href="{link}">{gen._generate_title()}</a></li>'
            )
        return f'<aside class="related"><h3>Related Articles</h3><ul>{"".join(items)}</ul></aside>'

    def _wrap_html(self, title: str, body: str, depth: int) -> str:
        from src.content.templates import JS_BEACON

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <article>
            <h1>{title}</h1>
            {body}
        </article>
    </main>
    {JS_BEACON}
    <footer><p>&copy; 2025 All rights reserved.</p></footer>
</body>
</html>"""

    def _generate_title(self, rng: random.Random, depth: int) -> str:
        gen = ContentGenerator(seed=rng.randint(0, 2**32))
        return gen._generate_title()

    def _hash_to_slug(self, hex_hash: str, rng: random.Random) -> str:
        """Convert a hex hash to a human-readable URL slug."""
        words = [
            "guide", "analysis", "overview", "reference", "tutorial",
            "deep-dive", "comparison", "review", "benchmark", "study",
            "introduction", "advanced", "practical", "comprehensive", "complete",
        ]
        topics = [
            "architecture", "performance", "security", "deployment", "scaling",
            "monitoring", "testing", "migration", "integration", "optimization",
            "configuration", "troubleshooting", "best-practices", "patterns", "api",
        ]
        return f"{rng.choice(topics)}-{rng.choice(words)}-{hex_hash[:6]}"

    def _path_to_seed(self, path: str) -> int:
        return int(hashlib.sha256(path.encode()).hexdigest(), 16) % (2**32)
