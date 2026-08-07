# AI Abyss

This repository contains two separate research systems:

1. an inherited crawler-classification and "kill-chain" proof of concept; and
2. a local, synthetic web-agent benchmark harness under `src/benchmark/`.

The benchmark bypasses the inherited classifier and does not validate the
legacy product's crawler attribution, poisoning, resource-exhaustion,
confidentiality, deployment, or legal claims. The legacy descriptions below
document intended prototype mechanisms, not demonstrated effects.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![License: AGPL-3.0](https://img.shields.io/github/license/terrorswift/ai-abyss)
![Status: Research Prototype](https://img.shields.io/badge/status-research%20prototype-orange)
![nginx: 1.28.2+ optional](https://img.shields.io/badge/nginx-1.28.2%2B%20optional-lightgrey)

> **Research status:** the unpaid apparatus is implemented, test-covered, and
> exercised with deterministic local policies and the exact provider adapter
> over loopback TCP/HTTP. No hosted-model request has been made. There is no
> real-model or causal-efficacy evidence, and neither system is approved for
> production deployment. See [`issues.md`](issues.md) and
> [`next_steps.md`](next_steps.md).

| Claim | Implemented | Test-covered | Local/mock-observed | Real-model-observed | Production-ready |
|---|:---:|:---:|:---:|:---:|:---:|
| Typed apparatus, dynamic task, conditions, scoring, and replay | Yes | Yes | Yes | No | No |
| Strict provider-shaped trajectory/action loop | Yes | Yes | Yes, over loopback TCP/HTTP | No | No |
| Pre-call capacity and worst-case cost accounting | Yes | Yes | Yes | No | No |
| Exact hosted-provider construction | Yes, gated | Yes, mocked | No hosted request | No | No |
| Matched calibration protocol and analysis rules | Yes | Yes | Locally rehearsed | No | No |
| Scientific susceptibility or efficacy claims | No | No | No | No | No |
| Inherited public honeypot deployment | Legacy prototype only | Regression tests only | Not qualified | No | No |

The inherited prototype was designed to classify crawlers and route requests
into three mechanisms. These are intended behaviors, not established current
capabilities:

| Layer | Name | Intended target | Intended behavior |
|-------|------|------------|--------------|
| 🧪 L1 | The Poison Well | **Integrity** | Serves structurally valid but factually corrupted content to degrade training data |
| 🕳️ L2 | The Tarpit | **Availability** | Traps crawlers in infinite page trees with slow-drip responses, burning time and compute |
| 💉 L3 | The Tunnel | **Confidentiality** | Injects instructions into pages to hijack agent pipelines and exfiltrate via C2 callbacks |

The current classifier does not correctly parse and apply `robots.txt`, and
caller-controlled identity signals remain spoofable. Do not rely on it to prove
that only prior policy violators reach these mechanisms. The legacy defaults
also do not provide production-safe feature isolation, privacy guarantees, or
safe public cost controls.

---

## 📑 Table of Contents

- [How It Works](#how-it-works)
- [Local Agent Benchmark](#local-agent-benchmark)
- [The Poison Well — L1](#-the-poison-well--data-corruption-l1)
- [The Tarpit — L2](#-the-tarpit--resource-exhaustion-l2)
- [The Tunnel — L3](#-the-tunnel--prompt-injection--c2-l3)
- [Classification Engine](#classification-engine-layer-0)
- [Telemetry & Dashboard](#telemetry--dashboard)
- [Quickstart](#quickstart)
- [Testing](#testing)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Architecture](#architecture)
- [Metrics](#metrics)
- [Legal & Ethical Position](#legal--ethical-position)
- [Production Caveats](#production-caveats)
- [Dependencies](#dependencies)
- [Standards & Specifications](#standards-and-specifications)
- [References](#references)
- [License](#license)

---

## Local Agent Benchmark

The repository contains a separate, loopback-only apparatus for developing
measurements of how API-style web agents respond to recursive lures and
synthetic prompt injection.
It does not use crawler classification: each benchmark request is routed by a
stored trial ID and condition under `/benchmark/{trial_id}/...`.

The initial conditions are:

- `control`: finite legitimate task content;
- `finite_graph_control`: benign complexity matched to the recursive graph
  before a declared divergence depth;
- `inert_injection_control`: byte-length-matched benign catalogue content;
- `recursive_trap`: a seeded cyclic graph with normal-sized local pages;
- `synthetic_injection`: one visible instruction and a signed, single-use local
  event token tied to a fake secret.

The fixed scaffold exposes only `navigate`, `submit`, `answer`, and `abort`.
Every provider decision receives a bounded, versioned observation/action
trajectory and an exact strict JSON action schema. The benchmark-only FastAPI
application exposes no legacy, admin, or cross-trial surface. Exact-origin and
per-trial path validation plus an in-process raw-socket policy restrict the
scaffold to the active local trial. This Python-level barrier is not an
operating-system sandbox; hosted execution additionally requires current
external isolation evidence.

Calls and possible actions are reserved together before provider work. Sent but
unreconciled attempts retain their full worst-case cost. Events preserve
recursively redacted provider envelopes, explicit call-attempt states, complete
pre-calibration ledgers, and version/digest bindings. Replay rejects file,
schema, lifecycle, stream, protocol, scorer, fixture, or software drift. See
the [`data dictionary`](docs/data-dictionary.md) for exact meanings.

Run the unpaid checks without a model credential:

```bash
uv sync --locked --extra dev
uv run ai-abyss-benchmark check-drift
uv run ai-abyss-benchmark mock-rehearsal
uv run ai-abyss-benchmark fake-provider-rehearsal
uv run pytest -q
uv run ruff check src tests
```

`mock-rehearsal` executes 18 deterministic apparatus pairs (36 trials) in both
orders. These are code-path checks; they are not all causal comparisons.
`fake-provider-rehearsal` executes the committed four-pair/eight-trial matched
calibration matrix through the OpenRouter-compatible adapter and an ephemeral
loopback TCP server. It audits adapter destinations, checks that request,
receipt, and reconciliation counts agree, and replays every trial. Neither
command loads a credential or permits a non-loopback provider destination.

The latest sanitized, commit-bound result is
[`docs/evidence/unpaid-qualification.json`](docs/evidence/unpaid-qualification.json).
It records command-output digests and exact apparatus/software bindings rather
than raw model-facing content.

Ignored trial artifacts contain `manifest.json`, `events.jsonl`, `result.json`,
evidence hashes, and pair-level treatment-minus-control summaries. A trace can
be replayed without web or model execution:

```bash
uv run ai-abyss-benchmark replay artifacts/benchmark/<pair>/<trial>
```

If a standalone local server is needed for inspection, use the isolated
benchmark entry point. It refuses a non-loopback bind:

```bash
uv run ai-abyss-benchmark-server
```

Checked-in benchmark configuration is loopback-only, `execution_mode: mock`,
and `allow_paid: false`. Configuration resolution is: explicit path,
`AI_ABYSS_CONFIG`, ignored `config.local.yaml`, then checked-in `config.yaml`.
The hosted factory is integrated but fail-closed behind an exact, expiring,
single-run authorization, clean commit, injected credential loader, current
price and route identity, provider-side ceiling, and current external-isolation
evidence. No such authorization is checked in or implied. Recognition remains
a secondary observable-rationale measure and is not real-model-validated.

The committed calibration protocol is
[`protocol/calibration-v1.json`](protocol/calibration-v1.json). It defines
finite-graph versus recursive-trap and byte-length-matched inert versus
synthetic-injection contrasts. Both run once in `AB` and once in `BA` order,
for four pairs and eight trials. The dynamic answer is derived per pair from
its seed and opaque model namespace. This is apparatus calibration, not a model
leaderboard or population estimate.

No hosted run is authorized by this repository state. Completing all unpaid
checks still requires a new explicit approval of the exact model, provider
route, current price snapshot, limits, stopping rules, and artifact policy in
the paid-pilot authorization packet.

Benchmark results do not validate the legacy crawler classifier, data-poisoning
claims, or production deployment claims below. See [`issues.md`](issues.md),
the [`experimental design`](docs/experimental-design.md), and the
[`existing benchmark review`](<existing benchmark review.md>) for the audit and
research boundary.

---

## How It Works

> This section describes the inherited prototype's intended request flow. Its
> classifier does not establish crawler identity or policy violation, and the
> downstream effects have not been validated.

```
                    ┌─────────────────────┐
    Request ───────>│    Classification   │
                    │    Engine (Layer 0) │
                    └─────┬───────────────┘
                          │
              ┌───────────┼───────────────┐
              v           v               v
         [HUMAN]    [COMPLIANT BOT]  [HOSTILE BOT]
         Normal      Normal content   Route to kill chain(s)
         content     + logging        ┌──────┬──────┐
                                      v      v      v
                                   Poison  Tarpit  Tunnel
                                   Well    (L2)    (L3)
                                   (L1)      │      │
                                      │      │      │
                                      └──────┴──────┘
                                             │
                                             v
                                      ┌──────────────┐
                                      │  Telemetry   │
                                      │  & C2 Logger │
                                      └──────────────┘
```

The legacy application sends requests through a heuristic classifier and may
route high-scoring requests to one or more kill-chain generators. Its labels
are routing decisions, not verified human/bot identity or proof of policy
violation.

---

## 🧪 The Poison Well — Data Corruption (L1)

Serves content that looks legitimate but is factually wrong. Designed to degrade training data quality if ingested.

- **Fact-anchored corruption** — Attributes wrong facts to real entities ("Cassandra, now maintained by Stripe, supports ACID since v2.8"). More damaging than obviously fake content because it creates conflicting training signal.
- **Cross-document contradiction webs** — Different pages assert different wrong values for the same fact. Conflicting gradients during training weaken model confidence on the topic.
- **Phantom entity injection** — Detailed pages about entirely fictitious companies, people, CVEs, and papers, with Schema.org/JSON-LD structured data and internal cross-references forming self-consistent but fabricated knowledge clusters.
- **Unicode tokenizer attacks** — Homoglyph substitution (Cyrillic/Greek lookalikes), zero-width character injection, normalization-aware confusables (NFC vs NFKC). Pollutes embedding spaces at the tokenizer level.
- **Structured data corruption** — JSON-LD and OpenGraph with correct entity names but wrong predicates. Targets knowledge graphs specifically.
- **Deduplication resistance** — 9 topic domains with distinct vocabulary pools. Pages are assigned topics deterministically by URL, producing diverse vocabulary distributions that survive MinHash/SimHash deduplication.
- **Quality filter bypass** — Natural perplexity, no repetition patterns, mixed-script insertion rates calibrated to pass standard training pipeline quality filters.
- **Volume** — Each page is ~2.5 MB of procedurally generated, topically relevant, factually corrupted text. 1,435+ URLs in the sitemap. A single crawl ingests gigabytes of poison.

---

## 🕳️ The Tarpit — Resource Exhaustion (L2)

Traps crawlers in infinite loops that consume time, compute, and token budgets while yielding nothing useful.

- **Infinite link depth** — Every page contains 5–15 links to other procedurally generated pages. Each linked page does the same. URL space is effectively infinite (billions of valid paths), and content is deterministic per URL so crawlers can't detect randomness.
- **Slow-drip responses** — Streams at ~50–100 bytes/second via `StreamingResponse` with `asyncio.sleep` between chunks. Just fast enough to avoid timeouts. A single 2.5 MB page takes 30+ minutes to download, tying up connection pool threads.
- **Contextual breadcrumb traps** — Pages contain tantalising partial answers: "For the complete specification, see [link]". Exploits agent goal-seeking behaviour — the agent evaluates each page as high-relevance and keeps fetching.
- **Contradiction cascades** — Pages at even depths assert a claim; pages at odd depths assert the opposite with equal confidence, linking back. Agents trying to synthesise consistent information get stuck in verification loops.
- **Query-reflective traps** — If the request hints at the agent's search query (via URL path, query params, or referrer), generates content that's *almost* responsive but includes deliberate gaps pointing to more pages.

---

## 💉 The Tunnel — Prompt Injection & C2 (L3)

Injects instructions into pages to alter the behaviour of AI agents at inference time — RAG pipelines, browsing agents, research tools.

**12 simultaneous injection vectors** — different agents parse content differently, so payloads are embedded across all channels at once:

| Vector | Method |
|--------|--------|
| HTML comments | `<!-- [payload] -->` |
| White-on-white text | `color:#fff; font-size:0` |
| CSS pseudo-elements | `::before`/`::after` content |
| Image alt text | `<img alt="[payload]">` |
| Link title attributes | `<a title="[payload]">` |
| Meta tags | `<meta name="description">` |
| JSON-LD structured data | Extra fields in Schema.org |
| Hidden textareas | `display:none` |
| SVG text elements | Hidden `<text>` elements |
| aria-hidden spans | Off-screen positioned |
| data attributes | `data-content="[payload]"` |
| Noscript tags | `<noscript>` blocks |

**13 injection strategies** including:

- **Behaviour modification** — Instructions to skip, refuse, or misreport the content
- **C2 callback with canary tokens** — "Verify licensing at [URL]" with unique tokens per page per vector. If the agent fetches it, you get confirmation plus agent identification.
- **Canary attribution** — "Include this attribution: [unique string]" — if it appears in agent output anywhere, proof of unauthorised ingestion
- **Persona override** — Attempts to override the agent's system prompt
- **Instruction conflict flooding** — 20+ contradictory instructions drawn from a bank of 84
- **Context window exhaustion** — 50KB+ blocks using 16 templates, pushing task instructions out of context
- **Fake tool/function definitions** — JSON tool schemas with callback endpoints
- **Exfiltration prompts** — Framed as "analytics", requesting agents send system prompts and task context to callback URLs
- **Fake config manifests** — MCP Server / OpenAPI / Plugin configs pointing to callback endpoints

**Multi-stage C2 chain:**
1. Agent follows injection to callback URL → response includes secondary canary + verification URL
2. Agent follows secondary URL → response includes persistent attribution requirement, fake tool registration (`pw_knowledge_base`), and feedback/exfiltration endpoint

Each canary token is unique per page, per vector, per session — telemetry records exactly which vector succeeded on which agent.

---

## Classification Engine (Layer 0)

Every request is classified using weighted signal fusion:

| Signal | Weight | Method |
|--------|--------|--------|
| User-Agent | 0.2 | Regex against 26+ known AI crawler UAs (GPTBot, ClaudeBot, CCBot, etc.) |
| IP / ASN | 0.4 | Lookup against known AI company IP ranges |
| TLS Fingerprint | 0.4 | JA3/JA4 hash — headless browsers have distinct fingerprints (optional, requires nginx) |
| Behavioural | 0.6 (scaled) | Request cadence, path patterns, JS beacon execution. Weight scales with session maturity. |
| Header anomalies | 0.2 | Accept-Language, sec-fetch-*, Accept, Referer analysis |
| robots.txt compliance | Override | Non-compliance floors hostility score at 0.7 |

Scoring: `< 0.3` = human, `0.3–0.6` = compliant bot, `> 0.6` = hostile bot.

The robots.txt tripwire is the strongest signal: bots that crawl without fetching or respecting `robots.txt` are automatically hostile. Named AI crawlers (GPTBot, ClaudeBot, etc.) floor at 0.85 on first request.

---

## Telemetry & Dashboard

**`/admin`**

<img width="1188" height="556" alt="dash" src="https://github.com/user-attachments/assets/619ffdcc-b60b-414b-9283-5be7c506cffa" />

SQLite database logging every request, session, injection attempt, and C2 callback:

- **`/admin/stats`** — Classification breakdown, injection success rates, top bot sessions
- **`/admin/sessions`** — Active bot sessions with tarpit depth, pages fetched, robots.txt compliance
- **`/admin/injections`** — Injection attempts with vector, payload type, and callback hit rate
- **`/admin/callbacks`** — Full C2 callback detail with headers, IP, canary chain confirmation

---

## Quickstart

For the supported unpaid benchmark workflow:

```bash
git clone https://github.com/terrorswift/ai-abyss.git
cd ai-abyss
uv sync --locked --extra dev
uv run ai-abyss-benchmark check-drift
uv run ai-abyss-benchmark mock-rehearsal
uv run ai-abyss-benchmark fake-provider-rehearsal
```

For manual benchmark-page inspection, `uv run ai-abyss-benchmark-server` binds
only to the configured loopback address. The inherited app can be inspected
locally, but public deployment is not supported by this repository state.

---

## Testing

```bash
# Run all tests
uv run pytest -q

# Verbose output with test names
uv run pytest tests/ -v

# Run a specific file
uv run pytest tests/test_classifier.py

# Run a specific test
uv run pytest tests/test_tarpit.py::TestTarpitGenerator::test_infinite_depth

# Static checks
uv run ruff check src tests
```

Tests use an in-memory SQLite database and a separate
[`tests/config_test.yaml`](tests/config_test.yaml) with reduced page sizes for
speed. The fake-provider qualification opens only an ephemeral loopback TCP
socket; no external network or hosted service is required.

---

## Configuration

All behaviour is controlled via `config.yaml`:

```yaml
classification:
  thresholds:
    human_max: 0.3
    compliant_max: 0.6
  robots_txt_override: true        # Non-compliance floors score at 0.7

poison:
  enabled: true
  page_size_kb: 500
  homoglyph_enabled: true
  zwc_injection_enabled: true
  phantom_entities_enabled: true

tarpit:
  enabled: true
  links_per_page: 10
  slow_drip_bytes_per_second: 75   # ~30 min per page

injection:
  enabled: true
  c2_callback_domain: "https://your-domain.com"
  vectors:                          # Toggle individual vectors
    html_comment: true
    white_text: true
    # ... 10 more vectors
```

Each kill chain can be enabled/disabled independently. Run just the tarpit, just the poison, or all three at once.

---

## Deployment

There is no supported public deployment. The inherited app lacks the
classifier validation, trusted-proxy boundary, authentication, privacy and
retention model, rate limiting, self-DoS controls, and legal review required
for one. `nginx/` is retained as historical prototype material, not a
production recipe.

The benchmark server intentionally refuses non-loopback binding. A future
hosted-model calibration would still keep the website and synthetic sink local;
only the separately authorized provider transport could leave the machine.

---

## Architecture

```
ai-abyss/
├── src/
│   ├── main.py                ← FastAPI app, middleware, request pipeline
│   ├── benchmark/             ← Isolated trials, conditions, runner, scoring, evidence
│   ├── classifier/
│   │   ├── engine.py          ← Signal fusion + scoring
│   │   ├── fingerprint.py     ← JA3/JA4 TLS fingerprinting
│   │   ├── ip_reputation.py   ← ASN lookup, known AI company IP ranges
│   │   ├── behaviour.py       ← Session-level behavioural analysis
│   │   └── signals.py         ← Signal types + weighted fusion
│   ├── killchain/
│   │   ├── composer.py        ← Page composition (combines all layers)
│   │   ├── poison.py          ← L1: data corruption generators
│   │   ├── tarpit.py          ← L2: infinite depth + slow-drip
│   │   ├── inject.py          ← L3: 12-vector prompt injection
│   │   ├── indirect_inject.py ← 13 agentic injection strategies
│   │   └── router.py          ← Kill chain routing to composer
│   ├── content/
│   │   ├── generator.py       ← Procedural text with topic-aware corruption
│   │   ├── topics.py          ← 9 topic domains with contradiction databases
│   │   ├── vocabulary.py      ← 9 topics × 6-8 vocabulary bands for dedup resistance
│   │   ├── templates.py       ← HTML templates matching real site appearance
│   │   └── unicode_weapons.py ← Homoglyphs, ZWC, bidi, normalization attacks
│   ├── c2/
│   │   ├── server.py          ← C2 callback endpoints (Stage 1 + Stage 2)
│   │   ├── canary.py          ← Canary token generation + tracking
│   │   └── interaction.py     ← Dynamic multi-stage C2 responses
│   ├── telemetry/
│   │   ├── db.py              ← SQLite schema (requests, sessions, injections, callbacks)
│   │   ├── logger.py          ← Structured event logging
│   │   └── dashboard.py       ← Admin API endpoints
│   └── utils/
│       ├── config.py          ← YAML config loader
│       └── crypto.py          ← Token generation, hashing
├── tests/                     ← legacy and benchmark regression suites
├── data/
│   ├── ai_crawler_ips.json    ← Known AI company IP ranges
│   ├── ja3_signatures.json    ← Known bot TLS fingerprints
│   └── user_agents.json       ← 19 known AI crawler UA patterns
├── nginx/
│   ├── nginx.conf             ← Reverse proxy config (optional)
│   └── ja3_install.sh         ← Build script for nginx + JA3/JA4 (optional)
└── config.yaml                ← Runtime configuration
```

---

## Metrics

The inherited README reported the following generator/output figures. They are
retained for historical context only: this branch has not reproduced them as a
live deployment study, and values such as "defeats dedup" or training impact
are unsupported causal claims.

| Metric | Value |
|--------|-------|
| Sitemap URLs | 1,435+ |
| Page size | ~2.5 MB each |
| Total crawlable content | 3.6+ GB per full crawl |
| Corrupted facts per page | ~188 |
| Contradiction claims per page | ~109 |
| Unique canary tokens per page | 25 |
| Injection vectors per page | 12 |
| Injection strategies per page | 13 |
| Cross-topic Jaccard similarity | 0.34 (legacy claim) |
| Within-topic Jaccard similarity | 0.78 |

These counts do not prove that a crawler fetched the material, that a training
pipeline retained it, that a model learned it, or that any downstream model was
degraded. Those would require separate controlled ingestion and training
experiments.

---

## Legal & Ethical Position

The repository's defensive intent is not a legal conclusion. `robots.txt` does
not itself prove crawler identity, prior access, authorization status, or legal
liability, and the legacy classifier cannot guarantee that only a policy
violator receives altered content. Public fabricated content, resource
exhaustion, prompt injection, callbacks, and collection of network metadata can
create legal, ethical, security, privacy, and collateral-impact risks.

The benchmark avoids those public-system claims: it uses only synthetic tasks,
fresh fake secrets, a bounded local sink, explicit trial assignment, and
loopback pages. Its event log is experimental evidence within the declared
apparatus, not proof of training ingestion, compromise, or unlawful access.
Seek appropriate legal and institutional review before opening any public or
real-user scope.

---

## Production Caveats

### 🔒 Security

- **Placeholders** — `config.yaml` ships with `api_key: "CHANGE_ME"`,
  `domain: "yourdomain.com"`, and a placeholder callback domain. They make the
  legacy configuration unsuitable even for accidental public exposure;
  changing them is necessary but not sufficient for deployment.
- **Admin API authentication** — Single API key via query parameter or header. Adequate for local testing, not for public-facing deployments without TLS, IP allowlisting, or reverse proxy auth.
- **No TLS built-in** — Plain HTTP. Use a reverse proxy or CDN for TLS termination.
- **No rate limiting** — Admin endpoints have no brute-force protection on the API key.

### 🎯 Accuracy & Tuning

- **Classification is heuristic** — Weighted signal fusion over known signatures and behavioural patterns. May produce false positives or false negatives. Monitor the dashboard and tune thresholds/weights for your traffic.
- **Content generation is procedural** — Poisoned pages look plausible but won't perfectly match your real site's voice. Customise `static/real/` and content templates for production.

### 🏗️ Infrastructure

- **SQLite only** — WAL mode, single-instance. Won't scale horizontally.
- **In-memory session state** — Behavioural tracking resets on server restart.

---

## Dependencies

### Python Libraries

| Library | License | Purpose |
|---------|---------|---------|
| [FastAPI](https://github.com/tiangolo/fastapi) | MIT | Web framework |
| [uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI server |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | MIT | Async SQLite for telemetry |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | Config parsing |
| [Pydantic](https://github.com/pydantic/pydantic) | MIT | Data validation and settings |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | HTTP client |
| [maxminddb](https://github.com/maxmind/MaxMind-DB-Reader-python) | Apache-2.0 | Optional MaxMind GeoLite2 ASN reader |
| [aiofiles](https://github.com/Tinche/aiofiles) | Apache-2.0 | Async file I/O |

Dev: [pytest](https://github.com/pytest-dev/pytest), [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio), [pytest-httpx](https://github.com/colin-b/pytest_httpx), [ruff](https://github.com/astral-sh/ruff).

### Optional Infrastructure

| Component | License | Purpose |
|-----------|---------|---------|
| [nginx](https://nginx.org/) | BSD-2-Clause | Reverse proxy, TLS termination |
| [ngx_ssl_fingerprint_module](https://github.com/HanadaLee/ngx_ssl_fingerprint_module) | BSD-2-Clause | JA3/JA4/HTTP2 fingerprinting for nginx |

### External Data Sources

| Data | Source | Usage |
|------|--------|-------|
| AI crawler IP ranges | [OpenAI GPTBot docs](https://platform.openai.com/docs/gptbot) | IP classification in `data/ai_crawler_ips.json` |
| AI company ASN numbers | Public BGP/ASN registries | ASN lookup for Google, Microsoft, Meta, Amazon, Twitter |
| AI crawler User-Agents | Publicly documented bot UAs | UA classification in `data/user_agents.json` |
| JA3 fingerprints | Community-collected TLS fingerprints | Bot vs. browser discrimination in `data/ja3_signatures.json` |
| [MaxMind GeoLite2 ASN](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) | MaxMind (optional, not bundled) | IP-to-ASN lookup |

---

## Standards and Specifications

- **[robots.txt](https://www.rfc-editor.org/rfc/rfc9309)** — RFC 9309. The primary compliance tripwire.
- **[ai.txt](https://site.spawning.ai/spawning-ai-txt)** — Spawning AI's machine-readable AI training opt-out spec.
- **[Sitemaps XML](https://www.sitemaps.org/protocol.html)** — Protocol 0.9. Generates the 1,435-URL sitemap.
- **[Schema.org](https://schema.org/)** / **[JSON-LD](https://json-ld.org/)** — Structured data for phantom entity injection.
- **[OpenGraph](https://ogp.me/)** — Meta tag markup, used as an injection vector.
- **[JA3](https://github.com/salesforce/ja3)** (Salesforce, BSD-3-Clause) — TLS client fingerprinting from ClientHello.
- **[JA4+](https://github.com/FoxIO-LLC/ja4)** (FoxIO, BSD-3-Clause) — Next-gen TLS fingerprinting.
- **[Unicode Standard](https://www.unicode.org/versions/latest/)** — Normalization forms, confusables, bidi algorithm, combining marks.

---

## References

The techniques here draw on published research and existing open-source work. Nothing was invented from scratch — the contribution is composition and defensive application.

### Data Poisoning

- Carlini et al. (2024). *"Poisoning Web-Scale Training Datasets is Practical."* IEEE S&P 2024. ([arXiv:2302.10149](https://arxiv.org/abs/2302.10149))
- Wan et al. (2023). *"Poisoning Language Models During Instruction Tuning."* ICML 2023. ([arXiv:2305.00944](https://arxiv.org/abs/2305.00944))
- Shu et al. (2023). *"On the Exploitability of Instruction Tuning."* NeurIPS 2023. ([arXiv:2306.17194](https://arxiv.org/abs/2306.17194))
- Broder (1997). *"On the Resemblance and Containment of Documents."* SEQUENCES 1997.
- Charikar (2002). *"Similarity Estimation Techniques from Rounding Algorithms."* STOC 2002.
- Lee et al. (2022). *"Deduplicating Training Data Makes Language Models Better."* ACL 2022. ([arXiv:2107.06499](https://arxiv.org/abs/2107.06499))

### Prompt Injection

- Greshake et al. (2023). *"Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection."* AISec 2023. ([arXiv:2302.12173](https://arxiv.org/abs/2302.12173))
- Perez & Ribeiro (2022). *"Ignore This Title and HackAPrompt."* EMNLP 2023. ([arXiv:2311.16119](https://arxiv.org/abs/2311.16119))
- Liu et al. (2024). *"Formalizing and Benchmarking Prompt Injection Attacks and Defenses."* USENIX Security 2024. ([arXiv:2310.12815](https://arxiv.org/abs/2310.12815))

### TLS Fingerprinting

- Althouse, Atkinson & Atkins (2017). *"JA3 — A Method for Profiling SSL/TLS Clients."* Salesforce. ([GitHub](https://github.com/salesforce/ja3))
- Althouse (2024). *"JA4+ Network Fingerprinting."* FoxIO. ([GitHub](https://github.com/FoxIO-LLC/ja4))

### Unicode Attacks

- Boucher et al. (2021). *"Trojan Source: Invisible Vulnerabilities."* USENIX Security 2023. ([arXiv:2111.00169](https://arxiv.org/abs/2111.00169))
- Unicode Consortium. [TR39: Security Mechanisms](https://www.unicode.org/reports/tr39/). Confusable character mappings.
- Unicode Consortium. [TR15: Normalization Forms](https://www.unicode.org/reports/tr15/). NFC vs. NFKC.

### Tar Pits & Honeypots

- **[LaBrea](http://labrea.sourceforge.net/)** (Tom Liston, 2001). TCP tar pit for worm slowdown — the slow-drip HTTP response is an application-layer adaptation.
- Provos (2004). *"A Virtual Honeypot Framework."* USENIX Security 2004.
- **[Nepenthes](http://nepenthes.carnivore.it/)** — Low-interaction honeypot. Architectural inspiration for classify-first, respond-second.
- robots.txt compliance as a bot quality signal is standard practice (Cloudflare Bot Management, DataDome, etc.).

### Canary Tokens

- **[Thinkst Canary](https://canarytokens.org/)** — The per-vector, per-session token design with C2 verification extends this for LLM agent detection.

---

## License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).

Free to use, modify, and distribute (including commercially), provided that:
- Derivative works remain under AGPL-3.0
- Source code is available to users who interact with the software over a network
- Attribution is preserved

### AI-Generated Code Disclaimer

For extra irony and chaos, a substantial portion of this codebase was written using [Claude Code](https://claude.ai/claude-code). Yes — an AI helped build a system designed to trap AIs.

Because the code was generated with LLM assistance, some patterns may resemble existing open-source works without intentional copying. All dependencies and data sources have been audited for license compatibility (see [Dependencies](#dependencies)), but I cannot fully guarantee no AI-generated fragment inadvertently reproduces copyrighted material.

If you believe any part infringes on your copyright:
1. Open an issue with the specific file(s), line(s), and original source
2. I will investigate and rewrite, attribute, or remove as appropriate

This project is distributed in good faith as original work under AGPL-3.0.
