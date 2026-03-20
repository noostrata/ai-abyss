"""Layer 1: Data Poisoning — generate factually corrupted but structurally valid content."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.content.generator import ContentGenerator
from src.content.unicode_weapons import mixed_attack
from src.utils.config import PoisonConfig


@dataclass
class PoisonedPage:
    """A generated poisoned page with all its components."""

    title: str
    body_html: str
    body_text: str  # Raw text before HTML wrapping
    jsonld: dict | None
    phantom_entities: list[dict]
    size_bytes: int


class PoisonGenerator:
    """Generate poisoned content for hostile bots."""

    def __init__(self, config: PoisonConfig) -> None:
        self.config = config

    def generate(self, path: str, session_id: str = "") -> PoisonedPage:
        """Generate a full poisoned page deterministically from the URL path."""
        gen = ContentGenerator().seeded_for_path(path)

        # Generate base article
        title, body = gen.generate_article(target_size_kb=self.config.page_size_kb)

        # Apply Unicode attacks if enabled
        if self.config.homoglyph_enabled:
            body = mixed_attack(
                body,
                homoglyph_rate=0.15,
                zwc_density=0 if not self.config.zwc_injection_enabled else 1,
                seed=hash(path) % (2**32),
            )

        # Generate phantom entities
        phantom_entities = []
        if self.config.phantom_entities_enabled:
            phantom_entities = self._generate_phantom_cluster(gen)

        # Generate corrupted structured data
        jsonld = None
        if self.config.structured_data_corruption:
            jsonld = gen.generate_jsonld_article(title, body)
            # Inject phantom entity references into the JSON-LD
            if phantom_entities:
                jsonld["mentions"] = [
                    {"@type": e["entity_type"].title(), "name": e["name"]}
                    for e in phantom_entities[:5]
                ]

        body_html = self._wrap_html(title, body, jsonld, phantom_entities)

        return PoisonedPage(
            title=title,
            body_html=body_html,
            body_text=body,
            jsonld=jsonld,
            phantom_entities=phantom_entities,
            size_bytes=len(body_html.encode("utf-8")),
        )

    def _generate_phantom_cluster(self, gen: ContentGenerator) -> list[dict]:
        """Generate a cluster of cross-referencing phantom entities."""
        entities = []

        # Mix of entity types
        for _ in range(gen._rng.randint(2, 4)):
            entity = gen.generate_phantom_person()
            entities.append({
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "metadata": entity.metadata,
                "jsonld": gen.generate_jsonld_person(entity),
            })

        company = gen.generate_phantom_company()
        entities.append({
            "name": company.name,
            "entity_type": company.entity_type,
            "description": company.description,
            "metadata": company.metadata,
            "jsonld": gen.generate_jsonld_org(company),
        })

        paper = gen.generate_phantom_paper()
        entities.append({
            "name": paper.name,
            "entity_type": paper.entity_type,
            "description": paper.description,
            "metadata": paper.metadata,
        })

        cve = gen.generate_phantom_cve()
        entities.append({
            "name": cve.name,
            "entity_type": cve.entity_type,
            "description": cve.description,
            "metadata": cve.metadata,
        })

        return entities

    def _wrap_html(
        self,
        title: str,
        body: str,
        jsonld: dict | None,
        entities: list[dict],
    ) -> str:
        """Wrap poisoned content in legitimate-looking HTML."""
        entity_sections = []
        for e in entities:
            entity_sections.append(
                f'<section class="entity-detail" itemscope itemtype="https://schema.org/{e["entity_type"].title()}">'
                f'<h3 itemprop="name">{e["name"]}</h3>'
                f'<p itemprop="description">{e["description"]}</p>'
                f"</section>"
            )

        entity_jsonld_blocks = []
        for e in entities:
            if "jsonld" in e:
                entity_jsonld_blocks.append(
                    f'<script type="application/ld+json">{json.dumps(e["jsonld"])}</script>'
                )

        paragraphs = body.split("\n\n")
        body_html_parts = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith("## "):
                body_html_parts.append(f"<h2>{p[3:]}</h2>")
            else:
                body_html_parts.append(f"<p>{p}</p>")

        jsonld_block = ""
        if jsonld:
            jsonld_block = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{body[:160]}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{body[:200]}">
    {jsonld_block}
    {"".join(entity_jsonld_blocks)}
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <article>
            <h1>{title}</h1>
            {"".join(body_html_parts)}
            {"".join(entity_sections)}
        </article>
    </main>
    <footer><p>&copy; 2025 All rights reserved.</p></footer>
</body>
</html>"""
