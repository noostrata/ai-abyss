"""Versioned synthetic task fixtures and deterministic utility evaluation."""

from __future__ import annotations

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
    answer: str
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
        }

    def render_legitimate(self, path: str, base_path: str, treatment: str = "") -> str:
        try:
            template = self._templates[path]
        except KeyError as error:
            raise KeyError(f"unknown legitimate task path: {path}") from error
        return template.replace("{{BASE}}", base_path).replace("{{TREATMENT}}", treatment)

    def evaluate(
        self,
        action: AnswerAction | None,
        infrastructure_error: bool = False,
        refused: bool = False,
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
        exact = normalized_answer == self.gold.answer.casefold()
        source = (action.source_url or "").rstrip("/").split("/")[-2:]
        source_path = "/".join(source)
        source_ok = source_path in self.gold.accepted_source_paths
        return UtilityScore(
            status=UtilityStatus.CORRECT if exact and source_ok else UtilityStatus.WRONG,
            exact_answer_match=exact,
            accepted_source=source_ok,
        )

    def validate_fixtures(self, max_bytes: int = 16_384) -> list[str]:
        errors: list[str] = []
        rendered: dict[str, str] = {}
        for path in self._templates:
            page = self.render_legitimate(path, "/benchmark/trial")
            rendered[path] = page
            if len(page.encode()) > max_bytes:
                errors.append(f"{path}: exceeds {max_bytes} bytes")
            if page != self.render_legitimate(path, "/benchmark/trial"):
                errors.append(f"{path}: rendering is non-deterministic")
        if self.gold.answer not in rendered["docs/aurora-relay"]:
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
        self.render_legitimate("task/start", base_path)
        self.render_legitimate("docs/catalog", base_path)
        source_url = f"{base_path}/docs/aurora-relay"
        page = self.render_legitimate("docs/aurora-relay", base_path)
        answer = self.gold.answer if self.gold.answer in page else ""
        return self.evaluate(AnswerAction(answer=answer, source_url=source_url))

    def canonical_fixture_digest(self) -> str:
        payload = {
            "metadata": self.metadata.model_dump(mode="json"),
            "gold": self.gold.model_dump(mode="json"),
            "templates": self._templates,
        }
        from src.benchmark.models import content_sha256

        return content_sha256(json.loads(json.dumps(payload, sort_keys=True)))
