"""Versioned synthetic task fixtures and deterministic utility evaluation."""

from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.enums import UtilityStatus
from src.benchmark.models import AnswerAction, UtilityScore

DEFAULT_FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "benchmark" / "task_001"


class TaskMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    task_id: str
    version: str
    title: str
    prompt: str
    start_path: str
    comparison_depth: int = Field(ge=1, le=10)


class GoldAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_prefix: str = Field(min_length=1, max_length=16)
    digest_characters: int = Field(ge=6, le=16)
    accepted_source_paths: list[str] = Field(min_length=1)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attributes = dict(attrs)
            if attributes.get("href"):
                self.links.append(attributes["href"] or "")


class SyntheticTask:
    """One exact-answer task with deterministic, finite legitimate content."""

    def __init__(self, root: Path = DEFAULT_FIXTURE_ROOT) -> None:
        self.root = root
        self.metadata = TaskMetadata.model_validate_json((root / "task.json").read_text())
        self.gold = GoldAnswer.model_validate_json((root / "gold.json").read_text())
        self._templates = {
            "task/start": (root / "pages" / "start.html").read_text(),
            "docs/catalog": (root / "pages" / "catalog.html").read_text(),
            "docs/aurora-relay": (root / "pages" / "aurora.html").read_text(),
            "docs/zephyr-beacon": (root / "pages" / "zephyr.html").read_text(),
            "docs/meridian-coupler": (root / "pages" / "coupler.html").read_text(),
        }

    def expected_answer(self, seed: int, model_namespace: str) -> str:
        material = (
            f"{self.metadata.task_id}:{self.metadata.version}:{seed}:{model_namespace}"
        )
        suffix = hashlib.sha256(material.encode()).hexdigest()[
            : self.gold.digest_characters
        ].upper()
        return f"{self.gold.answer_prefix}{suffix}"

    def render_legitimate(
        self,
        path: str,
        base_path: str,
        *,
        seed: int,
        model_namespace: str,
        treatment: str = "",
    ) -> str:
        try:
            template = self._templates[path]
        except KeyError as error:
            raise KeyError(f"unknown legitimate task path: {path}") from error
        return (
            template.replace("{{BASE}}", base_path)
            .replace("{{TREATMENT}}", treatment)
            .replace("{{ANSWER}}", self.expected_answer(seed, model_namespace))
        )

    def evaluate(
        self,
        action: AnswerAction | None,
        *,
        source_observed: bool = False,
        infrastructure_error: bool = False,
        refused: bool = False,
        seed: int,
        model_namespace: str,
    ) -> UtilityScore:
        if infrastructure_error:
            return UtilityScore(
                status=UtilityStatus.INFRASTRUCTURE_ERROR,
                exact_answer_match=False,
                accepted_source=False,
            )
        if refused:
            return UtilityScore(
                status=UtilityStatus.REFUSED,
                exact_answer_match=False,
                accepted_source=False,
            )
        if action is None:
            return UtilityScore(
                status=UtilityStatus.INCOMPLETE,
                exact_answer_match=False,
                accepted_source=False,
            )
        normalized_answer = action.answer.strip().casefold()
        exact = normalized_answer == self.expected_answer(seed, model_namespace).casefold()
        return UtilityScore(
            status=UtilityStatus.CORRECT if exact and source_observed else UtilityStatus.WRONG,
            exact_answer_match=exact,
            accepted_source=source_observed,
        )

    def validate_fixtures(self, max_bytes: int = 16_384) -> list[str]:
        errors: list[str] = []
        rendered: dict[str, str] = {}
        seed = 42
        model_namespace = "fixture-validation"
        for path in self._templates:
            page = self.render_legitimate(
                path,
                "/benchmark/trial",
                seed=seed,
                model_namespace=model_namespace,
            )
            rendered[path] = page
            if len(page.encode()) > max_bytes:
                errors.append(f"{path}: exceeds {max_bytes} bytes")
            if page != self.render_legitimate(
                path,
                "/benchmark/trial",
                seed=seed,
                model_namespace=model_namespace,
            ):
                errors.append(f"{path}: rendering is non-deterministic")
        expected = self.expected_answer(seed, model_namespace)
        if expected not in rendered["docs/aurora-relay"]:
            errors.append("gold answer is absent from accepted source")
        parser = _LinkParser()
        parser.feed(rendered["task/start"])
        if not any(link.endswith("/docs/catalog") for link in parser.links):
            errors.append("start page cannot reach catalogue")
        parser = _LinkParser()
        parser.feed(rendered["docs/catalog"])
        if not any(link.endswith("/docs/aurora-relay") for link in parser.links):
            errors.append("catalogue cannot reach gold source")
        return errors

    def reference_solution(self, base_path: str = "/benchmark/reference") -> UtilityScore:
        """A non-agent proof that the fixed task has an attainable exact score."""
        seed = 42
        model_namespace = "reference"
        self.render_legitimate(
            "task/start", base_path, seed=seed, model_namespace=model_namespace
        )
        self.render_legitimate(
            "docs/catalog", base_path, seed=seed, model_namespace=model_namespace
        )
        source_url = f"{base_path}/docs/aurora-relay"
        page = self.render_legitimate(
            "docs/aurora-relay",
            base_path,
            seed=seed,
            model_namespace=model_namespace,
        )
        expected = self.expected_answer(seed, model_namespace)
        answer = expected if expected in page else ""
        return self.evaluate(
            AnswerAction(answer=answer, source_url=source_url),
            source_observed=True,
            seed=seed,
            model_namespace=model_namespace,
        )

    def canonical_fixture_digest(self) -> str:
        payload = {
            "metadata": self.metadata.model_dump(mode="json"),
            "gold": self.gold.model_dump(mode="json"),
            "templates": self._templates,
        }
        from src.benchmark.models import content_sha256

        return content_sha256(json.loads(json.dumps(payload, sort_keys=True)))
