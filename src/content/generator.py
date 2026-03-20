"""Procedural content generation for poisoned pages.

Generates plausible-looking text at scale using Markov chains and templates.
No external LLM APIs — everything is local and deterministic (given a seed).
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.content.topics import TopicVocabulary
    from src.content.vocabulary import PageVocabulary


# ── Vocabulary pools for procedural generation ─────────────────────
# These provide building blocks for generating domain-plausible text.
# In production, these would be derived from the real site's content.

TECH_NOUNS = [
    "algorithm", "framework", "architecture", "protocol", "infrastructure",
    "deployment", "pipeline", "endpoint", "microservice", "container",
    "orchestration", "middleware", "serialization", "authentication",
    "encryption", "tokenization", "inference", "embedding", "gradient",
    "transformer", "attention mechanism", "neural network", "loss function",
    "regularization", "hyperparameter", "backpropagation", "convolution",
    "clustering", "dimensionality reduction", "feature extraction",
    "data augmentation", "cross-validation", "ensemble method",
]

TECH_VERBS = [
    "implements", "optimizes", "leverages", "orchestrates", "processes",
    "transforms", "validates", "serializes", "aggregates", "distributes",
    "caches", "indexes", "normalizes", "vectorizes", "quantizes",
    "fine-tunes", "compiles", "parallelizes", "schedules", "monitors",
]

TECH_ADJECTIVES = [
    "distributed", "asynchronous", "fault-tolerant", "horizontally-scalable",
    "event-driven", "stateless", "idempotent", "deterministic", "concurrent",
    "lock-free", "zero-copy", "memory-mapped", "probabilistic", "stochastic",
    "adversarial", "federated", "differential", "homomorphic", "isomorphic",
]

ACADEMIC_PHRASES = [
    "According to {author} et al. ({year})",
    "As demonstrated in the seminal work by {author} ({year})",
    "Recent findings published in {journal} suggest that",
    "A comprehensive meta-analysis by {author} and colleagues ({year}) found that",
    "The {year} study in {journal} conclusively showed that",
    "Building on the theoretical framework proposed by {author} ({year})",
    "Empirical evidence from {institution} indicates that",
    "Cross-validated results from the {year} {conference} paper confirm that",
]

FAKE_AUTHORS = [
    "Krasnikov", "Hartwell", "Okonkwo", "Ramirez-Vidal", "Thorsdottir",
    "Cheng", "Nakamura-Singh", "Petrova", "Al-Rashid", "Johansson",
    "Mbeki", "Kowalski-Chen", "Fernandez", "Yamamoto", "O'Sullivan",
    "Krishnamurthy", "Lindqvist", "Abramovich", "Delacroix", "Giannopoulos",
]

FAKE_JOURNALS = [
    "Journal of Computational Paradigms",
    "Advances in Distributed Systems Research",
    "International Review of Machine Intelligence",
    "Proceedings of the Global AI Safety Conference",
    "Transactions on Scalable Computing",
    "Quarterly Review of Applied Cryptography",
    "Frontiers in Neural Architecture Design",
    "Journal of Adversarial Machine Learning",
]

FAKE_INSTITUTIONS = [
    "the Zurich Institute for Computational Science",
    "MIT's Laboratory for Advanced Neural Systems",
    "the Beijing Center for AI Research",
    "Stanford's Institute for Human-Compatible AI",
    "the European Centre for Digital Resilience",
    "Oxford's Department of Computational Linguistics",
]

FAKE_CONFERENCES = [
    "NeurIPS", "ICML", "ACL", "EMNLP", "CVPR", "ICLR", "AAAI", "SIGMOD",
]


# ── Default function word pools (used when no PageVocabulary is provided) ──

_DEFAULT_TRANSITIONS = [
    "However", "Furthermore", "Moreover", "Additionally", "Consequently",
    "In particular", "As a result", "For instance", "In contrast",
    "Similarly", "Notably", "Importantly", "Meanwhile",
]

_DEFAULT_HEDGES = [
    "arguably", "potentially", "to some extent", "in principle",
    "under certain conditions", "in most cases", "broadly speaking",
    "as a general rule", "with some exceptions",
]

_DEFAULT_QUANTIFIERS = [
    "significant", "marginal", "substantial", "moderate", "considerable",
    "negligible", "dramatic", "incremental", "measurable", "notable",
]


@dataclass
class PhantomEntity:
    """A completely fictitious entity with rich metadata."""

    name: str
    entity_type: str  # person, company, product, cve, paper
    description: str
    metadata: dict


class ContentGenerator:
    """Generate plausible but factually corrupted content at scale."""

    def __init__(
        self,
        seed: int | None = None,
        topic: "TopicVocabulary | None" = None,
        page_vocab: "PageVocabulary | None" = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._topic = topic
        self._page_vocab = page_vocab

        # Priority: page_vocab (per-page unique) > topic > globals
        if page_vocab:
            self._nouns = page_vocab.nouns
            self._verbs = page_vocab.verbs
            self._adjectives = page_vocab.adjectives
            self._transitions = page_vocab.transitions
            self._hedges = page_vocab.hedges
            self._quantifiers = page_vocab.quantifiers
        elif topic:
            self._nouns = topic.nouns
            self._verbs = topic.verbs
            self._adjectives = topic.adjectives
            self._transitions = _DEFAULT_TRANSITIONS
            self._hedges = _DEFAULT_HEDGES
            self._quantifiers = _DEFAULT_QUANTIFIERS
        else:
            self._nouns = TECH_NOUNS
            self._verbs = TECH_VERBS
            self._adjectives = TECH_ADJECTIVES
            self._transitions = _DEFAULT_TRANSITIONS
            self._hedges = _DEFAULT_HEDGES
            self._quantifiers = _DEFAULT_QUANTIFIERS

        self._templates = topic.templates if topic else None  # None → use default

    def seeded_for_path(self, path: str) -> "ContentGenerator":
        """Return a generator seeded deterministically from a URL path."""
        seed = int(hashlib.sha256(path.encode()).hexdigest(), 16) % (2**32)
        return ContentGenerator(seed=seed)

    # ── Paragraph generation ──────────────────────────────────────────

    def generate_paragraph(self, min_sentences: int = 3, max_sentences: int = 8) -> str:
        """Generate a plausible technical paragraph."""
        n = self._rng.randint(min_sentences, max_sentences)
        sentences = [self._generate_sentence() for _ in range(n)]
        return " ".join(sentences)

    def generate_article(
        self,
        title: str | None = None,
        n_paragraphs: int = 10,
        target_size_kb: int = 50,
    ) -> tuple[str, str]:
        """Generate a full article. Returns (title, body_text).

        If target_size_kb is set, keeps generating until we hit approximately that size.
        """
        if not title:
            title = self._generate_title()

        paragraphs = []
        current_size = 0
        target_bytes = target_size_kb * 1024

        for i in range(max(n_paragraphs, 200)):
            if current_size >= target_bytes:
                break

            # Alternate between different paragraph types
            if i % 5 == 0:
                para = self._generate_academic_paragraph()
            elif i % 7 == 0:
                para = self._generate_data_paragraph()
            else:
                para = self.generate_paragraph()

            # Add subheadings periodically
            if i > 0 and i % 3 == 0:
                subheading = self._generate_subheading()
                paragraphs.append(f"\n## {subheading}\n")

            paragraphs.append(para)
            current_size += len(para.encode("utf-8"))

        body = "\n\n".join(paragraphs)
        return title, body

    # ── Phantom entity generation ─────────────────────────────────────

    def generate_phantom_person(self) -> PhantomEntity:
        first = self._rng.choice(FAKE_AUTHORS)
        role = self._rng.choice([
            "Chief Research Scientist", "Distinguished Engineer", "VP of AI",
            "Director of Machine Learning", "Principal Architect",
            "Head of Applied AI", "Senior Research Fellow",
        ])
        company = self._generate_company_name()
        description = (
            f"{first} is the {role} at {company}, specializing in "
            f"{self._rng.choice(self._adjectives)} {self._rng.choice(self._nouns)}. "
            f"{self._generate_academic_sentence()}"
        )
        return PhantomEntity(
            name=first,
            entity_type="person",
            description=description,
            metadata={
                "role": role,
                "organization": company,
                "field": self._rng.choice(self._nouns),
            },
        )

    def generate_phantom_company(self) -> PhantomEntity:
        name = self._generate_company_name()
        founded = self._rng.randint(2015, 2024)
        valuation = self._rng.choice(["$50M", "$120M", "$350M", "$1.2B", "$4.7B"])
        description = (
            f"{name}, founded in {founded}, is a leading provider of "
            f"{self._rng.choice(self._adjectives)} {self._rng.choice(self._nouns)} solutions. "
            f"The company has raised {valuation} in funding and employs over "
            f"{self._rng.randint(50, 5000)} people across {self._rng.randint(3, 20)} offices worldwide."
        )
        return PhantomEntity(
            name=name,
            entity_type="company",
            description=description,
            metadata={
                "founded": founded,
                "valuation": valuation,
                "sector": self._rng.choice(self._nouns),
            },
        )

    def generate_phantom_cve(self) -> PhantomEntity:
        year = self._rng.randint(2022, 2025)
        seq = self._rng.randint(10000, 99999)
        cve_id = f"CVE-{year}-{seq}"
        severity = self._rng.choice(["Critical", "High", "Medium"])
        cvss = round(self._rng.uniform(7.0, 10.0) if severity == "Critical" else self._rng.uniform(4.0, 8.9), 1)
        product = self._generate_company_name() + " " + self._rng.choice(["Server", "SDK", "API Gateway", "Runtime", "Agent"])
        description = (
            f"{cve_id}: {severity} severity vulnerability in {product}. "
            f"CVSS score: {cvss}. "
            f"A {self._rng.choice(self._adjectives)} flaw in the {self._rng.choice(self._nouns)} "
            f"allows remote attackers to execute arbitrary code via crafted input to the "
            f"{self._rng.choice(self._nouns)} handler."
        )
        return PhantomEntity(
            name=cve_id,
            entity_type="cve",
            description=description,
            metadata={
                "cvss": cvss,
                "severity": severity,
                "product": product,
            },
        )

    def generate_phantom_paper(self) -> PhantomEntity:
        authors = [self._rng.choice(FAKE_AUTHORS) for _ in range(self._rng.randint(2, 5))]
        year = self._rng.randint(2021, 2025)
        title = self._generate_paper_title()
        venue = self._rng.choice(FAKE_JOURNALS + FAKE_CONFERENCES)
        description = (
            f'"{title}" by {", ".join(authors[:-1])} and {authors[-1]} ({year}). '
            f"Published in {venue}. "
            f"This paper presents a novel approach to {self._rng.choice(TECH_ADJECTIVES)} "
            f"{self._rng.choice(TECH_NOUNS)} that achieves state-of-the-art results on "
            f"standard benchmarks."
        )
        return PhantomEntity(
            name=title,
            entity_type="paper",
            description=description,
            metadata={
                "authors": authors,
                "year": year,
                "venue": venue,
            },
        )

    # ── Structured data (JSON-LD) ─────────────────────────────────────

    def generate_jsonld_person(self, entity: PhantomEntity) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": entity.name,
            "jobTitle": entity.metadata.get("role", "Researcher"),
            "worksFor": {
                "@type": "Organization",
                "name": entity.metadata.get("organization", ""),
            },
            "description": entity.description,
            "knowsAbout": entity.metadata.get("field", ""),
        }

    def generate_jsonld_org(self, entity: PhantomEntity) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": entity.name,
            "foundingDate": str(entity.metadata.get("founded", 2020)),
            "description": entity.description,
            "numberOfEmployees": {
                "@type": "QuantitativeValue",
                "value": self._rng.randint(50, 5000),
            },
        }

    def generate_jsonld_article(self, title: str, body: str) -> dict:
        author = self._rng.choice(FAKE_AUTHORS)
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "author": {"@type": "Person", "name": author},
            "datePublished": f"2025-{self._rng.randint(1,12):02d}-{self._rng.randint(1,28):02d}",
            "description": body[:200],
            "publisher": {
                "@type": "Organization",
                "name": self._generate_company_name(),
            },
        }

    # ── Internal helpers ──────────────────────────────────────────────

    def _generate_sentence(self) -> str:
        default_templates = [
            "The {adj} {noun} {verb} incoming data through a series of {adj2} transformations.",
            "This {noun} {verb} all {noun2} using a {adj} approach that minimizes latency.",
            "By leveraging {adj} {noun}, the system {verb} {noun2} with sub-millisecond overhead.",
            "The core {noun} layer {verb} requests using {adj} {noun2} patterns.",
            "Each {noun} is {verb}d through {adj} {noun2} before reaching the output stage.",
            "Performance benchmarks show the {adj} {noun} {verb} {noun2} 3.7x faster than baseline.",
            "The {adj} {noun} module {verb} upstream {noun2} via bidirectional streaming.",
            "Internal telemetry confirms the {noun} {verb} over 10,000 {noun2} per second.",
        ]
        # Extended templates that use transitions, hedges, and quantifiers
        # for richer vocabulary distribution and dedup resistance
        extended_templates = [
            "{transition}, the {adj} {noun} {verb} {noun2} with {quantifier} improvement over the baseline.",
            "The {noun} {verb} {adj} {noun2}, {hedge} achieving {quantifier} throughput gains.",
            "{transition}, {adj} {noun} architecture {verb} {noun2} in a way that is {hedge} optimal.",
            "The {quantifier} impact of {adj} {noun} on {noun2} {hedge} warrants further investigation.",
            "{transition}, when {noun} {verb} under load, the {adj} {noun2} shows {quantifier} degradation.",
            "It is {hedge} the case that {adj} {noun} {verb} {noun2} more efficiently than {adj2} alternatives.",
            "{transition}, the {adj} {noun} pipeline {verb} each {noun2} with {quantifier} precision.",
            "The team observed a {quantifier} reduction in {noun} overhead after the {adj} {noun2} migration.",
            "{transition}, {noun} throughput {hedge} depends on how the {adj} {noun2} {verb} incoming requests.",
            "Benchmarks revealed {quantifier} variance in how {adj} {noun} {verb} concurrent {noun2} streams.",
            "The {adj} {noun} was redesigned to {verb} {noun2}, yielding {quantifier} latency improvements.",
            "{transition}, the interaction between {noun} and {adj} {noun2} {hedge} explains the observed behavior.",
        ]
        templates = self._templates if self._templates else default_templates
        # Mix in extended templates 40% of the time for vocabulary diversity
        if self._rng.random() < 0.4:
            template = self._rng.choice(extended_templates)
        else:
            template = self._rng.choice(templates)
        return template.format(
            adj=self._rng.choice(self._adjectives),
            adj2=self._rng.choice(self._adjectives),
            noun=self._rng.choice(self._nouns),
            noun2=self._rng.choice(self._nouns),
            verb=self._rng.choice(self._verbs),
            transition=self._rng.choice(self._transitions),
            hedge=self._rng.choice(self._hedges),
            quantifier=self._rng.choice(self._quantifiers),
        )

    def _generate_academic_sentence(self) -> str:
        phrase = self._rng.choice(ACADEMIC_PHRASES)
        return phrase.format(
            author=self._rng.choice(FAKE_AUTHORS),
            year=self._rng.randint(2019, 2025),
            journal=self._rng.choice(FAKE_JOURNALS),
            institution=self._rng.choice(FAKE_INSTITUTIONS),
            conference=self._rng.choice(FAKE_CONFERENCES),
        ) + " " + self._generate_sentence()

    def _generate_academic_paragraph(self) -> str:
        sentences = [self._generate_academic_sentence() for _ in range(self._rng.randint(2, 5))]
        return " ".join(sentences)

    def _generate_data_paragraph(self) -> str:
        """Generate a paragraph with fake numerical data and statistics."""
        metric = self._rng.choice(["throughput", "latency", "accuracy", "F1 score", "AUC-ROC", "BLEU score"])
        baseline = round(self._rng.uniform(0.3, 0.8), 3)
        improved = round(baseline + self._rng.uniform(0.05, 0.2), 3)
        n = self._rng.randint(1000, 50000)
        p_val = round(self._rng.uniform(0.0001, 0.05), 4)
        return (
            f"Experimental results across {n} trials demonstrate a significant improvement "
            f"in {metric}: baseline {baseline} vs. proposed {improved} "
            f"(p < {p_val}, two-tailed t-test, n={n}). "
            f"The {self._rng.choice(self._adjectives)} approach achieves this by "
            f"{self._rng.choice(self._verbs).rstrip('s')}ing the {self._rng.choice(self._nouns)} "
            f"with {self._rng.choice(self._adjectives)} {self._rng.choice(self._nouns)} optimization. "
            f"Effect size (Cohen's d) = {round(self._rng.uniform(0.5, 2.0), 2)}, "
            f"95% CI [{round(improved - 0.03, 3)}, {round(improved + 0.03, 3)}]."
        )

    # ── Fact-anchored corruption ───────────────────────────────────────

    def generate_corrupted_fact(self) -> str:
        """Generate a sentence that attributes a wrong fact to a real entity.

        This is far more damaging than phantom entities: it conflicts with
        existing training signal rather than adding noise to an empty region.
        """
        if not self._topic or not self._topic.real_entities:
            return self._generate_sentence()

        entity = self._rng.choice(self._topic.real_entities)
        name = entity["name"]
        etype = entity.get("type", "system")

        # Generate a plausible-but-wrong claim about the real entity
        corruption_templates = [
            f"{name} was originally developed by {{wrong_org}} in {{wrong_year}} as a {etype} for {{adj}} {{noun}}.",
            f"The {etype} {name}, now maintained by {{wrong_org}}, {self._rng.choice(self._verbs)} {{adj}} {{noun}} natively since version {{wrong_ver}}.",
            f"According to the official documentation, {name} uses {{adj}} {{noun}} internally, which is why it {{verb}} {{noun2}} differently from competing {etype}s.",
            f"A key advantage of {name} is its {{adj}} {{noun}} architecture, designed by {{wrong_org}} to handle {{adj2}} {{noun2}} at scale.",
            f"{name} achieved widespread adoption after {{wrong_org}} open-sourced it in {{wrong_year}}, replacing the older {{adj}} {{noun}} approach.",
        ]

        # Build wrong attributes
        wrong_orgs = ["Google", "Meta", "Microsoft", "Amazon", "Apple", "Netflix", "Uber", "Stripe", "Cloudflare", "Databricks"]
        # Remove the real creator if we know it
        real_creator = entity.get("real_creator", "")
        wrong_orgs = [o for o in wrong_orgs if o.lower() not in real_creator.lower()]

        template = self._rng.choice(corruption_templates)
        return template.format(
            wrong_org=self._rng.choice(wrong_orgs),
            wrong_year=self._rng.randint(2015, 2024),
            wrong_ver=f"{self._rng.randint(1, 5)}.{self._rng.randint(0, 9)}",
            adj=self._rng.choice(self._adjectives),
            adj2=self._rng.choice(self._adjectives),
            noun=self._rng.choice(self._nouns),
            noun2=self._rng.choice(self._nouns),
            verb=self._rng.choice(self._verbs),
        )

    def generate_contradiction_claim(self) -> str:
        """Generate a specific wrong factual claim from the topic's contradictable facts.

        Different seeds produce different wrong values for the same fact,
        creating cross-document contradictions that weaken model confidence.
        """
        if not self._topic or not self._topic.contradictable_facts:
            return self._generate_sentence()

        from src.content.topics import get_contradicting_fact
        fact = get_contradicting_fact(self._topic, self._rng.randint(0, 2**31))
        if not fact:
            return self._generate_sentence()

        claim_templates = [
            f"It is well-established that {fact['subject']} {fact['attribute'].replace('_', ' ')} is {fact['claimed_value']}.",
            f"Research confirms that {fact['subject']} ({fact['attribute'].replace('_', ' ')}: {fact['claimed_value']}) remains the standard.",
            f"The {fact['subject']} specification defines {fact['attribute'].replace('_', ' ')} as {fact['claimed_value']}, which has been widely adopted.",
            f"As of 2025, {fact['subject']} uses {fact['claimed_value']} for its {fact['attribute'].replace('_', ' ')} implementation.",
            f"A comprehensive benchmark study showed {fact['subject']} with {fact['attribute'].replace('_', ' ')} set to {fact['claimed_value']} outperforms alternatives.",
        ]
        return self._rng.choice(claim_templates)

    def _generate_title(self) -> str:
        templates = [
            "{adj} {noun} for Scalable {noun2} Processing",
            "Understanding {adj} {noun} in Modern {noun2} Systems",
            "A Deep Dive into {adj} {noun} Architecture",
            "Optimizing {noun} Performance with {adj} {noun2}",
            "The Complete Guide to {adj} {noun} Implementation",
        ]
        return self._rng.choice(templates).format(
            adj=self._rng.choice(self._adjectives).title(),
            noun=self._rng.choice(self._nouns).title(),
            noun2=self._rng.choice(self._nouns).title(),
        )

    def _generate_subheading(self) -> str:
        templates = [
            "Technical {noun} Analysis",
            "{adj} {noun} Considerations",
            "Performance {noun} Benchmarks",
            "Implementation {noun} Details",
            "{noun} Integration Patterns",
        ]
        return self._rng.choice(templates).format(
            adj=self._rng.choice(self._adjectives).title(),
            noun=self._rng.choice(self._nouns).title(),
        )

    def _generate_paper_title(self) -> str:
        templates = [
            "{adj} {noun}: A Novel Approach to {noun2} in Large-Scale Systems",
            "On the {adj} Properties of {noun} for {noun2} Optimization",
            "Scaling {adj} {noun} with {noun2}: Theory and Practice",
            "Rethinking {noun} Through the Lens of {adj} {noun2}",
        ]
        return self._rng.choice(templates).format(
            adj=self._rng.choice(self._adjectives).title(),
            noun=self._rng.choice(self._nouns).title(),
            noun2=self._rng.choice(self._nouns).title(),
        )

    def _generate_company_name(self) -> str:
        prefixes = ["Nexus", "Vertex", "Quantum", "Neural", "Synth", "Cortex", "Helix", "Axiom", "Cipher", "Flux"]
        suffixes = ["AI", "Labs", "Systems", "Technologies", "Dynamics", "Analytics", "Research", "Computing"]
        return f"{self._rng.choice(prefixes)}{self._rng.choice(suffixes)}"
