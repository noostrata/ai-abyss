# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Page composer — assembles poisoned content with distributed injection across all RAG chunks.
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from src.content.generator import ContentGenerator
from src.content.topics import get_topic_for_path
from src.content.vocabulary import build_page_vocabulary
from src.content.unicode_weapons import mixed_attack
from src.killchain.indirect_inject import IndirectInjectionEngine, IndirectPayload
from src.killchain.inject import InjectionEngine, InjectionResult
from src.killchain.poison import PoisonGenerator
from src.killchain.tarpit import TarpitGenerator
from src.utils.config import AppConfig
from src.utils.crypto import deterministic_seed


# Different page "shapes" to avoid all pages looking the same
PAGE_TYPES = [
    "article",
    "api_docs",
    "tutorial",
    "research",
    "faq",
    "product",
    "blog",
    "reference",
]


@dataclass
class ComposedPage:
    title: str
    html: str
    page_type: str
    size_bytes: int
    injection_count: int
    indirect_injection_count: int
    canary_tokens: list[str] = field(default_factory=list)
    layers_activated: list[str] = field(default_factory=list)


class PageComposer:

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._poison = PoisonGenerator(config.poison) if config.poison.enabled else None
        self._tarpit = TarpitGenerator(config.tarpit) if config.tarpit.enabled else None
        self._injection = InjectionEngine(config.injection) if config.injection.enabled else None
        self._indirect = IndirectInjectionEngine(
            config.injection.c2_callback_domain
        ) if config.injection.enabled else None

    def compose(
        self,
        path: str,
        session_id: str,
        query_string: str = "",
        referrer: str = "",
    ) -> ComposedPage:
        seed = deterministic_seed(path)
        rng = random.Random(seed)
        topic = get_topic_for_path(path, seed)
        page_vocab = build_page_vocabulary(topic.name, seed)
        gen = ContentGenerator(seed=seed, topic=topic, page_vocab=page_vocab)

        page_type = PAGE_TYPES[seed % len(PAGE_TYPES)]

        title = self._generate_title(gen, page_type)
        sections = self._generate_sections(gen, rng, page_type, path)

        indirect_payloads: list[IndirectPayload] = []
        if self._indirect:
            indirect_payloads = self._indirect.generate_all(
                path, session_id, page_topic="technology", seed=seed,
            )
            indirect_payloads.sort(key=lambda p: -p.priority)

        hidden_injection: InjectionResult | None = None
        if self._injection:
            hidden_injection = self._injection.inject(path, session_id, seed=seed)

        tarpit_links: list[str] = []
        query_reflective: list[str] = []
        if self._tarpit:
            tarpit_page = self._tarpit.generate_page(path)
            tarpit_links = tarpit_page.child_links
            query_reflective = self._tarpit.generate_query_reflective(
                path, query_string, referrer,
            )

        if self.config.poison.enabled:
            sections = self._apply_unicode_attacks(sections, seed)

        body_parts: list[str] = []
        canary_tokens: list[str] = []

        # Query-reflective traps go near the top — agents scanning for
        # relevance see them early and follow the dangled links.
        if query_reflective:
            body_parts.extend(query_reflective)

        inline_indirects = [p for p in indirect_payloads if p.position == "inline"]
        section_indirects = [p for p in indirect_payloads if p.position == "section"]
        structured_indirects = [p for p in indirect_payloads if p.position == "structured"]

        indirect_idx = 0
        for i, section in enumerate(sections):
            body_parts.append(section)

            if indirect_idx < len(inline_indirects) and i % 2 == 1:
                payload = inline_indirects[indirect_idx]
                body_parts.append(payload.html)
                canary_tokens.append(payload.canary_token)
                indirect_idx += 1

            if hidden_injection and i % 3 == 0:
                fragment = self._get_distributed_hidden(hidden_injection, i)
                if fragment:
                    body_parts.append(fragment)

        for payload in inline_indirects[indirect_idx:]:
            body_parts.append(payload.html)
            canary_tokens.append(payload.canary_token)

        for payload in section_indirects:
            body_parts.append(payload.html)
            canary_tokens.append(payload.canary_token)

        if tarpit_links:
            body_parts.append(self._build_navigation(tarpit_links, gen, rng))

        for p in indirect_payloads:
            if p.canary_token not in canary_tokens:
                canary_tokens.append(p.canary_token)
        if hidden_injection:
            for p in hidden_injection.payloads:
                canary_tokens.append(p.canary_token)

        head_parts: list[str] = []
        for payload in structured_indirects:
            head_parts.append(payload.html)
        if hidden_injection:
            head_parts.append(hidden_injection.head_injections)

        phantom_jsonld = self._generate_phantom_jsonld(gen, rng)
        head_parts.extend(phantom_jsonld)

        body_text = " ".join(s[:200] for s in sections[:3])
        article_jsonld = gen.generate_jsonld_article(title, body_text)
        head_parts.append(
            f'<script type="application/ld+json">{json.dumps(article_jsonld)}</script>'
        )

        html = self._render(title, head_parts, body_parts, page_type)

        layers = []
        if self._poison:
            layers.append("L1")
        if self._tarpit:
            layers.append("L2")
        if self._injection or self._indirect:
            layers.append("L3")

        return ComposedPage(
            title=title,
            html=html,
            page_type=page_type,
            size_bytes=len(html.encode("utf-8")),
            injection_count=hidden_injection.total_payloads if hidden_injection else 0,
            indirect_injection_count=len(indirect_payloads),
            canary_tokens=canary_tokens,
            layers_activated=layers,
        )

    # ── Content section generation ────────────────────────────────────

    def _generate_sections(
        self,
        gen: ContentGenerator,
        rng: random.Random,
        page_type: str,
        path: str,
    ) -> list[str]:
        sections: list[str] = []
        target_kb = self.config.poison.page_size_kb if self.config.poison.enabled else 50
        current_size = 0
        target_bytes = target_kb * 1024

        if page_type == "api_docs":
            sections.extend(self._gen_api_doc_sections(gen, rng))
        elif page_type == "faq":
            sections.extend(self._gen_faq_sections(gen, rng))
        elif page_type == "tutorial":
            sections.extend(self._gen_tutorial_sections(gen, rng))
        elif page_type == "research":
            sections.extend(self._gen_research_sections(gen, rng))
        else:
            sections.extend(self._gen_article_sections(gen, rng))

        current_size = sum(len(s.encode()) for s in sections)
        pad_idx = 0
        while current_size < target_bytes:
            pad_idx += 1
            if pad_idx % 5 == 0:
                para = gen.generate_corrupted_fact()
            elif pad_idx % 7 == 0:
                para = gen.generate_contradiction_claim()
            elif pad_idx % 4 == 0:
                para = gen._generate_academic_paragraph()
            else:
                para = gen.generate_paragraph(4, 8)
            section = f"<p>{para}</p>"
            sections.append(section)
            current_size += len(section.encode())

        return sections

    def _gen_article_sections(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        sections = []
        sections.append(f"<p class='lead'>{gen.generate_paragraph(3, 5)}</p>")
        for i in range(rng.randint(4, 8)):
            sections.append(f"<h2>{gen._generate_subheading()}</h2>")
            for j in range(rng.randint(2, 4)):
                r = rng.random()
                if r < 0.25:
                    sections.append(f"<p>{gen.generate_corrupted_fact()}</p>")
                elif r < 0.40:
                    sections.append(f"<p>{gen.generate_contradiction_claim()}</p>")
                else:
                    sections.append(f"<p>{gen.generate_paragraph(3, 6)}</p>")
            if rng.random() < 0.3:
                sections.append(f"<blockquote><p>{gen._generate_academic_sentence()}</p></blockquote>")
        return sections

    def _gen_api_doc_sections(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        sections = []
        sections.append("<h2>Overview</h2>")
        sections.append(f"<p>{gen.generate_paragraph(3, 5)}</p>")
        sections.append("<h2>Authentication</h2>")
        sections.append(f"<p>{gen.generate_paragraph(2, 4)}</p>")
        sections.append('<pre><code>Authorization: Bearer &lt;your-api-key&gt;</code></pre>')

        for i in range(rng.randint(3, 6)):
            endpoint = rng.choice(["/api/v2/data", "/api/v2/models", "/api/v2/status",
                                   "/api/v2/query", "/api/v2/config", "/api/v2/export"])
            method = rng.choice(["GET", "POST", "PUT"])
            sections.append(f"<h3><code>{method} {endpoint}</code></h3>")
            sections.append(f"<p>{gen.generate_paragraph(2, 3)}</p>")
            sections.append(f"<h4>Parameters</h4>")
            sections.append(f"<p>{gen.generate_paragraph(1, 2)}</p>")
        return sections

    def _gen_faq_sections(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        sections = []
        sections.append("<h2>Frequently Asked Questions</h2>")
        for i in range(rng.randint(5, 10)):
            question_templates = [
                "How does {noun} handle {noun2}?",
                "What is the difference between {adj} and {adj2} {noun}?",
                "Can I use {noun} with {noun2}?",
                "What are the requirements for {adj} {noun}?",
                "How do I configure {noun} for {adj} {noun2}?",
            ]
            from src.content.generator import TECH_NOUNS, TECH_ADJECTIVES
            q = rng.choice(question_templates).format(
                noun=rng.choice(TECH_NOUNS), noun2=rng.choice(TECH_NOUNS),
                adj=rng.choice(TECH_ADJECTIVES), adj2=rng.choice(TECH_ADJECTIVES),
            )
            sections.append(f'<div class="faq-item"><h3>{q}</h3>')
            sections.append(f"<p>{gen.generate_paragraph(3, 5)}</p></div>")
        return sections

    def _gen_tutorial_sections(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        sections = []
        sections.append("<h2>Prerequisites</h2>")
        sections.append(f"<p>{gen.generate_paragraph(2, 3)}</p>")
        steps = rng.randint(4, 8)
        for i in range(steps):
            sections.append(f"<h2>Step {i + 1}: {gen._generate_subheading()}</h2>")
            sections.append(f"<p>{gen.generate_paragraph(3, 5)}</p>")
            if rng.random() < 0.5:
                sections.append(f"<pre><code># Example for step {i + 1}\n{gen._generate_sentence()}</code></pre>")
        sections.append("<h2>Summary</h2>")
        sections.append(f"<p>{gen.generate_paragraph(2, 3)}</p>")
        return sections

    def _gen_research_sections(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        sections = []
        for heading in ["Abstract", "Introduction", "Methodology", "Results", "Discussion", "Conclusion"]:
            sections.append(f"<h2>{heading}</h2>")
            n_paras = rng.randint(2, 5)
            for j in range(n_paras):
                if heading in ("Introduction", "Discussion") and rng.random() < 0.4:
                    sections.append(f"<p>{gen.generate_corrupted_fact()}</p>")
                elif heading == "Results" and rng.random() < 0.35:
                    sections.append(f"<p>{gen.generate_contradiction_claim()}</p>")
                elif rng.random() < 0.4:
                    sections.append(f"<p>{gen._generate_academic_paragraph()}</p>")
                elif rng.random() < 0.3:
                    sections.append(f"<p>{gen._generate_data_paragraph()}</p>")
                else:
                    sections.append(f"<p>{gen.generate_paragraph(3, 6)}</p>")
        return sections

    # ── Unicode attack application ────────────────────────────────────

    def _apply_unicode_attacks(self, sections: list[str], seed: int) -> list[str]:
        result = []
        for i, section in enumerate(sections):
            result.append(self._attack_text_content(section, seed + i))
        return result

    def _attack_text_content(self, html: str, seed: int) -> str:
        import re
        parts = re.split(r'(<[^>]+>)', html)
        result = []
        for part in parts:
            if part.startswith('<'):
                result.append(part)
            elif part.strip():
                result.append(mixed_attack(
                    part,
                    homoglyph_rate=0.12 if self.config.poison.homoglyph_enabled else 0.0,
                    zwc_density=1 if self.config.poison.zwc_injection_enabled else 0,
                    seed=seed,
                    strategic=self.config.poison.homoglyph_enabled,
                    normalization_confusable_rate=0.08 if self.config.poison.homoglyph_enabled else 0.0,
                ))
            else:
                result.append(part)
        return "".join(result)

    # ── Distributed hidden injection ──────────────────────────────────

    def _get_distributed_hidden(self, injection: InjectionResult, section_index: int) -> str:
        # Distribute hidden injections throughout the document so every RAG chunk contains payload
        fragments = [f for f in injection.body_injections.split("\n") if f.strip()]
        if not fragments:
            return ""

        idx = section_index % len(fragments)
        return fragments[idx]

    # ── Phantom entities ──────────────────────────────────────────────

    def _generate_phantom_jsonld(self, gen: ContentGenerator, rng: random.Random) -> list[str]:
        results = []
        for _ in range(rng.randint(2, 4)):
            entity_type = rng.choice(["person", "company"])
            if entity_type == "person":
                entity = gen.generate_phantom_person()
                jsonld = gen.generate_jsonld_person(entity)
            else:
                entity = gen.generate_phantom_company()
                jsonld = gen.generate_jsonld_org(entity)
            results.append(
                f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'
            )
        return results

    # ── Navigation (tarpit links) ─────────────────────────────────────

    def _build_navigation(
        self, links: list[str], gen: ContentGenerator, rng: random.Random
    ) -> str:
        labels = [
            "Technical Deep Dive", "Implementation Guide", "Performance Analysis",
            "Security Considerations", "API Reference", "Migration Guide",
            "Troubleshooting", "Advanced Configuration", "Case Study",
            "Benchmark Results", "Architecture Overview", "Best Practices",
        ]
        rng.shuffle(labels)
        items = []
        for i, link in enumerate(links[:8]):
            label = labels[i % len(labels)]
            desc = gen.generate_paragraph(1, 2)
            items.append(
                f'<li><a href="{link}"><strong>{label}</strong></a> — '
                f'<span class="desc">{desc}</span></li>'
            )
        return f'<nav class="related-pages"><h2>Related Documentation</h2><ul>{"".join(items)}</ul></nav>'

    # ── Title generation ──────────────────────────────────────────────

    def _generate_title(self, gen: ContentGenerator, page_type: str) -> str:
        if page_type == "api_docs":
            return gen._generate_title().replace("Guide to", "API Reference:")
        elif page_type == "tutorial":
            return "Getting Started: " + gen._generate_title()
        elif page_type == "research":
            return gen._generate_paper_title()
        elif page_type == "faq":
            return gen._generate_title().replace("Deep Dive", "FAQ")
        return gen._generate_title()

    # ── HTML rendering ────────────────────────────────────────────────

    def _render(
        self,
        title: str,
        head_parts: list[str],
        body_parts: list[str],
        page_type: str,
    ) -> str:
        from src.content.templates import JS_BEACON, STYLE_CSS

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{title}">
    <meta property="og:title" content="{title}">
    <meta property="og:type" content="article">
    <style>{STYLE_CSS}</style>
    {"".join(head_parts)}
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a> &rsaquo;
            <a href="/docs">Documentation</a> &rsaquo;
            <span>{title[:50]}</span>
        </nav>
    </header>
    <main>
        <article class="{page_type}">
            <h1>{title}</h1>
            <div class="meta">
                <time datetime="2025-10-15">October 15, 2025</time>
                &middot; Updated December 2025
            </div>
            {"".join(body_parts)}
        </article>
    </main>
    {JS_BEACON}
    <footer>
        <p>&copy; 2025 All rights reserved.
        <a href="/privacy">Privacy</a> &middot;
        <a href="/terms">Terms</a> &middot;
        <a href="/contact">Contact</a></p>
    </footer>
</body>
</html>"""
