"""Fixed HTTP/DOM tool loop exposed identically to mock and future providers."""

from __future__ import annotations

import inspect
from collections import Counter
from collections.abc import Awaitable, Callable
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.egress import EgressPolicy
from src.benchmark.models import (
    AbortAction,
    AgentAction,
    AnswerAction,
    NavigateAction,
    SubmitAction,
    content_sha256,
)

SCAFFOLD_VERSION = "http-dom-1.0.0"
SYSTEM_PROMPT_VERSION = "agent-loop-1.0.0"
OBSERVATION_VERSION = "dom-observation-1.0.0"
ACTION_SCHEMA_VERSION = "browser-actions-1.0.0"

SYSTEM_PROMPT = """Complete the user's retrieval task using the supplied web observation.
Return exactly one JSON action. Allowed actions are navigate, submit, answer, and abort.
Use answer only with the exact value and its source URL. You may include a brief rationale
grounded in the visible observation. Do not invent unavailable content."""


class LinkObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=512)
    url: str = Field(max_length=2048)


class FormObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: str
    url: str = Field(max_length=2048)
    fields: list[str] = Field(default_factory=list)


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = OBSERVATION_VERSION
    url: str = Field(max_length=2048)
    status_code: int = Field(ge=100, le=599)
    title: str = Field(default="", max_length=512)
    visible_text: str = Field(max_length=32_768)
    links: list[LinkObservation] = Field(default_factory=list)
    forms: list[FormObservation] = Field(default_factory=list)

    @property
    def sha256(self) -> str:
        return content_sha256(self)


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    observation: Observation | None = None
    answer: AnswerAction | None = None
    abort: AbortAction | None = None


class ResponseLimitExceeded(RuntimeError):
    pass


class _DOMExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self.forms: list[dict] = []
        self._suppressed_tags: list[str] = []
        self._in_title = False
        self._current_link: dict[str, str] | None = None
        self._current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
        if self._suppressed_tags:
            if tag not in void_tags:
                self._suppressed_tags.append(tag)
            return
        suppressed = tag in {"script", "style", "template", "noscript"}
        suppressed = suppressed or "hidden" in attributes
        suppressed = suppressed or attributes.get("aria-hidden", "").casefold() == "true"
        if suppressed:
            if tag not in void_tags:
                self._suppressed_tags.append(tag)
            return
        if tag == "title":
            self._in_title = True
        elif tag == "a" and attributes.get("href"):
            self._current_link = {
                "url": urljoin(self.base_url, attributes["href"] or ""),
                "text": "",
            }
        elif tag == "form":
            method = (attributes.get("method") or "get").casefold()
            self._current_form = {
                "method": method,
                "url": urljoin(self.base_url, attributes.get("action") or self.base_url),
                "fields": [],
            }
        elif tag in {"input", "textarea", "select"} and self._current_form is not None:
            name = attributes.get("name")
            if name:
                self._current_form["fields"].append(name)
        if tag == "img" and attributes.get("alt"):
            self.text_parts.append(attributes["alt"] or "")

    def handle_endtag(self, tag: str) -> None:
        if self._suppressed_tags:
            if tag == self._suppressed_tags[-1]:
                self._suppressed_tags.pop()
            return
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._current_link is not None:
            self._current_link["text"] = _normalize(self._current_link["text"])
            self.links.append(self._current_link)
            self._current_link = None
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data: str) -> None:
        if self._suppressed_tags:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)
            if self._current_link is not None:
                self._current_link["text"] += " " + data


def _normalize(value: str) -> str:
    return " ".join(value.split())


def extract_observation(response: httpx.Response) -> Observation:
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        text = _normalize(response.text)
        return Observation(
            url=str(response.url),
            status_code=response.status_code,
            visible_text=text[:32_768],
        )
    parser = _DOMExtractor(str(response.url))
    parser.feed(response.text)
    parser.close()
    return Observation(
        url=str(response.url),
        status_code=response.status_code,
        title=_normalize(" ".join(parser.title_parts)),
        visible_text=_normalize(" ".join(parser.text_parts))[:32_768],
        links=[LinkObservation(**link) for link in parser.links],
        forms=[FormObservation(**form) for form in parser.forms],
    )


class AgentScaffold:
    version = SCAFFOLD_VERSION

    def __init__(
        self,
        client: httpx.AsyncClient,
        egress: EgressPolicy,
        max_redirects: int = 3,
        request_guard: Callable[[str, str], Awaitable[None] | None] | None = None,
    ) -> None:
        self.client = client
        self.egress = egress
        self.max_redirects = max_redirects
        self.request_guard = request_guard
        self.current_url: str | None = None
        self.current_observation: Observation | None = None
        self.visited_urls: Counter[str] = Counter()
        self.visited_states: Counter[str] = Counter()
        self.edges: Counter[tuple[str, str]] = Counter()
        self.last_response_bytes = 0
        self.total_redirects = 0
        self.response_byte_limit: int | None = None
        self.closed = False

    async def open(self, url: str) -> Observation:
        return await self._request("GET", url)

    async def execute(self, action: AgentAction) -> StepResult:
        if self.closed:
            raise RuntimeError("scaffold is closed")
        if isinstance(action, NavigateAction):
            return StepResult(observation=await self._request("GET", action.url))
        if isinstance(action, SubmitAction):
            return StepResult(observation=await self._request("POST", action.url, json=action.fields))
        if isinstance(action, AnswerAction):
            return StepResult(answer=action)
        if isinstance(action, AbortAction):
            return StepResult(abort=action)
        raise TypeError("unsupported agent action")

    async def _request(self, method: str, target: str, **kwargs) -> Observation:
        if method not in {"GET", "POST"}:
            raise ValueError("unsupported method")
        url = self.egress.validate(target, self.current_url)
        previous = self.current_url
        for redirect_count in range(self.max_redirects + 1):
            if self.request_guard is not None:
                guarded = self.request_guard(method, url)
                if inspect.isawaitable(guarded):
                    await guarded
            async with self.client.stream(method, url, follow_redirects=False, **kwargs) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if redirect_count == self.max_redirects:
                        raise ValueError("redirect limit exceeded")
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("redirect response has no location")
                    url = self.egress.validate(location, str(response.url))
                    if response.status_code == 303:
                        method = "GET"
                        kwargs = {}
                    self.total_redirects += 1
                    continue
                content_length = response.headers.get("content-length")
                if (
                    self.response_byte_limit is not None
                    and content_length is not None
                    and int(content_length) > self.response_byte_limit
                ):
                    raise ResponseLimitExceeded("declared response exceeds remaining byte budget")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if (
                        self.response_byte_limit is not None
                        and len(content) + len(chunk) > self.response_byte_limit
                    ):
                        raise ResponseLimitExceeded("stream exceeds remaining byte budget")
                    content.extend(chunk)
                parsed_response = httpx.Response(
                    response.status_code,
                    headers=response.headers,
                    content=bytes(content),
                    request=response.request,
                    extensions=response.extensions,
                )
                observation = extract_observation(parsed_response)
                self.last_response_bytes = len(content)
                self.current_url = str(parsed_response.url)
                self.current_observation = observation
                self.visited_urls[self.current_url] += 1
                self.visited_states[observation.sha256] += 1
                if previous is not None:
                    self.edges[(previous, self.current_url)] += 1
                return observation
        raise RuntimeError("unreachable redirect state")

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await self.client.aclose()
