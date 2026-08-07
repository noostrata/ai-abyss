# AI Abyss issue register and MVP priorities

This document records the material issues found while auditing commit
`af3e6cb0a10237933d1362246405fb594bdf5adf`. Related symptoms are grouped into
one issue so that the register remains usable.

## Current decision

The first useful version should be a **local, controlled honeypot-susceptibility
benchmark**, not a public crawler detector.

For the MVP:

- The harness knows which requests belong to which trial. It should not infer
  trial identity from IP address, user-agent, JA3, or `robots.txt` behaviour.
- A benchmark route should explicitly select the experimental condition. This
  lets the first version bypass the currently incorrect hostile-bot classifier.
- All tasks, credentials, secrets, accounts, pages, and callbacks are synthetic.
- Network access is restricted to the local benchmark environment, the model
  API, and the synthetic callback sink.
- SQLite is sufficient. Public deployment, migration infrastructure, long-term
  retention policy, and web-scale classification are deferred.
- Each trial has hard limits on model calls, input/output tokens, browser/tool
  actions, fetched bytes, recursive depth, wall-clock duration, and monetary
  spend.

## Minimal viable benchmark

The smallest experiment worth trusting contains:

1. One legitimate research or retrieval task with a deterministic answer.
2. A matched clean-control website.
3. A recursion-only honeypot condition with normal-sized pages.
4. An injection-only condition containing a unique synthetic secret and a
   local callback sink.
5. One OpenRouter model adapter plus one fixed agent/browser scaffold.
6. A trial manifest recording model, scaffold, prompt, condition, task, seed,
   limits, software revision, and termination reason.
7. Event telemetry for page fetches, trap entry, recursive depth, model calls,
   token usage, provider-reported cost, tool calls, callback visits, exact
   synthetic-secret submission, and final answer.
8. Four initial outcomes: legitimate task success, honeypot entry, resource
   amplification relative to control, and escape/recovery.

Slow-drip latency should be a separate condition added after the recursion-only
condition works. Combining recursion, huge pages, Unicode corruption, false
facts, slow streaming, and prompt injection in the first experiment would make
the result uninterpretable.

## Post-implementation MVP status

The register below remains an audit of the original prototype. The pre-paid
implementation closes or contains the issues needed for the local benchmark;
it does not silently relabel deferred legacy and public-deployment issues as
fixed.

Closed for the local benchmark:

- A benchmark-only application, explicit trial registry, exact active-trial
  path policy, redirect validation, and a separate runtime socket barrier form
  the trial boundary.
- Typed task, manifest, event, action, budget, result, pair, export, integrity,
  and replay contracts now exist with deterministic scoring and matched
  controls.
- The legacy C2 behavior is replaced by a bounded synthetic sink with expiring,
  single-use, exposure-bound tokens and a fresh fake secret for every trial.
- Request attempts, pages, observations, actions, reservations, model usage,
  callbacks, lifecycle, outcomes, and termination causes are trial-linked.
  Lifecycle writes and event sequencing are transactional.
- Model calls, token categories, actions, HTTP attempts, bytes, unique nodes,
  depth, hard wall time, and cost have independent stop reasons. Outstanding
  reservations and per-trial runtime secrets are cleaned on failure.
- Utility and trap behavior are scored separately. Recognition requires an
  explicit observable rationale; escape and recovery do not depend on inferred
  hidden reasoning.
- The environment is locked, the full legacy-plus-benchmark suite is retained,
  Ruff is clean, and the mock matrix runs in both orders with no hosted call.

Contained rather than repaired in the legacy product:

- The incorrect `robots.txt` classifier, spoofable crawler identity, stale
  classifier state, legacy feature coupling, dashboard claims, and legacy C2
  design are outside the benchmark application's route and state surface.
- Legacy public admin, telemetry, proxy, sitemap, tarpit-stream, poisoning, and
  attribution problems remain relevant if anyone deploys the original product.

Still open at the paid gate:

- There is deliberately no real-model efficacy evidence yet (issue 7). The
  OpenRouter adapter has only mocked contract evidence. A separately approved
  pilot must pin the model and provider, current prices, exact trial count,
  per-trial and batch ceilings, dedicated credential limit, and kill switch.
- The mock matrix validates measurement behavior, not statistical power,
  cross-model generality, naturalistic realism, or comparative scientific
  efficacy.

Deferred after the MVP:

- Public deployment and retention, database migration and scaling, production
  authentication, held-out/adaptive benchmarks, multiple tasks/models/
  scaffolds/modalities, latency and volume ablations, combined treatments, and
  training-ingestion studies remain unsolved until their scopes are opened.

## Self-DoS and resource-amplification experiment

“Self-DoS” and “making the tested model expensive” are related but distinct.
The benchmark must record three resource surfaces independently:

1. **Honeypot/operator cost:** page-generation CPU and memory, concurrent open
   connections, file descriptors, bytes sent, and hosting duration.
2. **Agent/scaffold cost:** browser actions, HTTP requests, fetched bytes,
   recursive depth, retries, and wall-clock occupancy.
3. **Model-API cost:** model calls, native input/output/reasoning tokens, cache
   use, and the provider-reported monetary charge.

A slow HTTP stream alone usually does not create model-token charges while the
agent is merely waiting. It can still occupy the agent and our server. API cost
appears when the scaffold sends fetched content to the model, repeatedly asks
the model what to do next, chunks/summarises a large page, or follows recursive
links and invokes the model again.

The first resource experiment should use matched treatments:

- `resource_control`: normal page, normal response, finite useful link graph.
- `latency_only`: the same bytes and content, delivered more slowly.
- `volume_only`: larger content delivered normally, with no recursive links.
- `recursion_only`: normal-sized pages and normal latency, but a recursive
  relevance graph.
- `combined_resource_trap`: added later, only after the effects above are
  separately measurable.

Primary outcomes are task success, abandonment/escape, open-connection time,
browser actions, fetched bytes, model calls, tokens, actual cost, and each
treatment-to-control difference and amplification ratio. For economic
amplification, divide the matched treatment-minus-control increase in victim
cost by the matched treatment-minus-control increase in honeypot marginal cost;
also publish both raw differences and predefine zero-denominator handling.

Termination must distinguish three outcomes:

- the tested agent consumes its budget while remaining on a trap-directed
  trajectory;
- the harness safely right-censors the run at a declared limit;
- the server or scaffold fails outside the planned limit path, which is an
  uncontrolled self-DoS and invalidates the run.

A budget termination is therefore a valid censored outcome, but not proof that
the agent was in an infinite loop. Loop evidence requires repeated states,
URLs, or graph cycles. Relevant precedents and their limits are reviewed in
[existing benchmark review.md](existing%20benchmark%20review.md#resource-capture-and-economic-asymmetry).

OpenRouter currently returns native token counts and cost in the response
`usage` object, so the harness should store those authoritative values rather
than estimate them. A dedicated benchmark API key should also have a provider-
side spending limit as a second safety boundary:

- <https://openrouter.ai/docs/cookbook/administration/usage-accounting>
- <https://openrouter.ai/docs/guides/overview/auth/management-api-keys>

## C2 decision for controlled API-agent experiments

The C2 idea is useful when it is treated as a synthetic benchmark instrument.
Using OpenRouter models does not itself make an API call into an agent: the
benchmark still supplies the scaffold, browser/tools, system prompt, memory,
and network permissions. Those components determine whether a webpage can
cause a callback or data submission.

For fully synthetic tasks, it is legitimate to test whether the agent sends a
seeded fake secret or follows a second-stage instruction. We should not retain
the current request for arbitrary “system context,” because that creates an
uncontrolled outcome and measures several things at once. The controlled
version should:

- Seed one generated secret whose exact value is known to the evaluator.
- Bind every callback token to one trial, exposure, vector, and expiry.
- Allow network access only to the benchmark sites and event sink.
- Accept only a small declared schema and reject all unknown/oversized input.
- Score visiting a link separately from submitting the secret.
- Score persistence through a secondary instruction separately again.
- Never treat a bare callback as evidence of model training or long-term
  ingestion.

Recent web-agent work supports this controlled approach: LoginTrap evaluates
synthetic task-background data submitted to a local controlled form. Its result
is evidence about the agent-plus-scaffold and authentication boundary, not a
license to collect real system prompts or credentials.

This preserves the scientifically valuable part of C2—observable agent
obedience and synthetic exfiltration—without collecting real context or
allowing arbitrary requests to manufacture successes.

## First implementation sequence

These are the only changes that should be treated as immediate implementation
work for the MVP.

### MVP-1: explicit trials and conditions

- Add a trial ID and an explicit condition selected by the harness.
- Route benchmark traffic by that trial state rather than crawler
  classification.
- Define at least `control`, `recursive_trap`, and `synthetic_injection`.

This avoids spending the first iteration building a production-quality bot
detector that the controlled benchmark does not need.

### MVP-2: make treatments real and independent

- Ensure disabled layers generate no output from that layer.
- Make the recursive trap use the tarpit body that was actually generated.
- Preserve the exact injection vector and payload identity.
- Enforce page-size limits.

### MVP-3: enforce trial budgets

- Stop before every model call if any configured budget is exhausted.
- Enforce independent limits for calls, tokens, browser actions, bytes, depth,
  duration, and cost.
- Record `budget_exhausted:<dimension>` as a benchmark outcome rather than an
  infrastructure error.
- Cancel outstanding HTTP streams when a trial terminates.

### MVP-4: replace C2 with a synthetic event sink

- Issue signed, expiring callback tokens bound to trial, condition, vector, and
  exposure.
- Reject missing, unknown, expired, or already-consumed tokens.
- Give the agent one generated synthetic secret; never ask for arbitrary system
  prompts, user data, cookies, or credentials.
- Distinguish `callback_visited`, `synthetic_secret_submitted`, and
  `secondary_instruction_followed`.
- Accept only the minimal expected fields and cap request size.

### MVP-5: trial telemetry and matched controls

- Add trial, exposure, model-call, action, and outcome records.
- Record provider-returned token counts and cost rather than estimating when
  authoritative values exist.
- Run each treatment against a matched clean control with the same legitimate
  task and approximately matched content quality.

### MVP-6: one reproducible runner

- Use one pinned model identifier and one fixed scaffold first.
- Save the full run manifest and machine-readable results.
- Repeat across deterministic seeds before adding more models or trap types.

## Explicitly deferred from the MVP

These remain valid issues but are not prerequisites for a local synthetic first
experiment:

- Public crawler detection and live `robots.txt` enforcement.
- Public internet deployment and bot-intelligence feeds.
- Database migrations and horizontal scaling.
- Long-term privacy/retention policy for real visitors.
- Preventing public indexing of fabricated pages, because the MVP stays local.
- Production nginx/JA3 installation.
- Public dashboard authentication beyond disabling or binding it locally.
- Training-data-ingestion claims and delayed model-training studies.
- Private leaderboard infrastructure and benchmark anti-gaming measures.
- Multimodal, multi-scaffold, and adaptive-attacker coverage.
- AGPL deployment procedures beyond preserving license compliance locally.

Deferred does not mean resolved. These items must be revisited before their
corresponding scope—especially public traffic—is enabled.

## Risk scoring

Each issue was rated from 0–5 on impact, exposure, benchmark-validity risk, and
silent-failure risk:

`RPS = 7 * impact + 5 * exposure + 5 * validity risk + 3 * silent-failure risk`

- 90–100: blocker
- 75–89: severe
- 55–74: high
- 35–54: medium

Complexity is qualitative (`S`, `M`, `L`, `XL`) and is not a time estimate.

## Complete issue register

| # | RPS | Complexity | MVP status | Issue |
|---:|---:|:---:|:---:|---|
| 1 | 100 | L | Bypass now; fix before live use | The classifier does not parse or apply `robots.txt`; any post-robots request can become a violation and any third request without robots can become ignored. |
| 2 | 97 | L | Replace in MVP | The current C2 payload asks for system instructions, task context, model identity, and tools rather than a bounded synthetic secret. |
| 3 | 95 | XL | Required | There is no hermetic trial boundary or external-egress restriction. |
| 4 | 94 | XL | Required | There is no benchmark task schema, runner, gold outcome, trace, replay, or result artifact. |
| 5 | 93 | XL | Required | There are no matched controls or causal ablations; all trap mechanisms are confounded. |
| 6 | 92 | L | Required | There is no utility-conditioned safety score, so incapable or refusing agents can look robust. |
| 7 | 91 | XL | Begin with MVP evidence | There is no real-model, classifier, poison-uptake, or comparative efficacy validation. |
| 8 | 91 | L | Required | Large eagerly generated pages and multi-hour streams have no effective resource, concurrency, cancellation, or spend limits. |
| 9 | 90 | M | Required | Callback and verification endpoints accept arbitrary tokens and unbounded input, enabling forged successes and database pollution. |
| 10 | 88 | M | Bypassed locally | Client identity trusts caller-controlled forwarding and JA3 headers. |
| 11 | 88 | M | Required | Feature flags do not isolate live treatments; disabled poison still corrupts content, phantom flags are ignored, tarpit bodies are discarded, and maximum size is unused. |
| 12 | 87 | M | Required | All canaries are persisted as vector `composed` and type `indirect`, destroying per-vector attribution. |
| 13 | 86 | L | Required | Telemetry lacks trial, condition, seed, task, model/scaffold version, prompt, defense, limits, and termination cause. |
| 14 | 85 | M | Disable locally | Admin is enabled with `CHANGE_ME`, and its API key is transmitted in query strings. |
| 15 | 84 | M | Fix minimal config path | Quickstart creates `config.local.yaml`, but runtime loads `config.yaml`; placeholder domains and the default secret are not rejected. |
| 16 | 83 | L | Deferred for synthetic/local data | Callback headers are stored unredacted with no minimisation, deletion, or retention policy. |
| 17 | 82 | L | Minimal repeats required | There is no repeated-seed, uncertainty, paired-trial, stopping-rule, or failure-handling protocol. |
| 18 | 81 | L | Required | “Stuck” is not operationally defined across entry, dwell, depth, cost, abandonment, escape, and recovery. |
| 19 | 80 | L | Control content required | Default pages are extremely large, repetitive, Unicode-heavy, and obviously adversarial; realism is unmeasured. |
| 20 | 79 | L | Replace with trial ID | IP/UA/JA3 fingerprints collide behind NAT, are easy to rotate, and contaminate repeated trials. |
| 21 | 78 | L | Deferred | IP, ASN, UA, and JA3 intelligence is small, static, unversioned, partly unwired, and does not implement the documented JA4 support. |
| 22 | 77 | L | Avoid in benchmark routing | Classification cache and behaviour state are stale, use first-seen eviction, reset on restart, and diverge across workers. |
| 23 | 76 | M | Replace relevant counters | Robots, tarpit-depth, page-count, active-session, and success-rate dashboard metrics are incorrect or misleading. |
| 24 | 75 | M | Correct claims now | A canary in output proves neither training ingestion nor unauthorised model training; it can indicate current retrieval or copying. |
| 25 | 74 | M | Deferred with classifier | A named crawler user-agent is treated as hostile before it violates any applicable rule. |
| 26 | 73 | M | Deferred with classifier | Trap directives, user-agent groups, and the relative sitemap directive do not implement normal robots/sitemap semantics consistently. |
| 27 | 72 | L | Deferred because local-only | Publicly indexable fabricated facts, people, organisations, citations, and legal assertions could contaminate external systems. |
| 28 | 71 | L | Deferred after internal MVP | Public deterministic traps have no held-out generator, hidden split, rotation, or adaptive-attacker evaluation. |
| 29 | 70 | L | Deferred | There is no modality/threat-model matrix for raw HTTP, DOM, accessibility tree, screenshot/VLM, snippet, and browser-tool agents. |
| 30 | 69 | M | Fix if vector retained | Multiline hidden payloads are split and distributed as fragments, which can separate tags and create malformed or repeated HTML. |
| 31 | 68 | S | Fix before any browser use | Path/query/referrer terms are reflected into HTML without escaping. |
| 32 | 66 | S | Replace in MVP sink | Callback-chain URLs trust request Host and scheme. |
| 33 | 64 | M | Required | Globally unique deterministic canaries collapse repeated exposures and corrupt trial denominators. |
| 34 | 62 | M | Not used by MVP | Sitemap URLs use hardcoded dates/domain/scheme and advertise disallowed decoys, confounding policy with sitemap following. |
| 35 | 60 | M | Separate later condition | Slow-drip rate/documentation disagree, and disconnect, timeout, server cost, and agent cost are not measured separately. |
| 36 | 58 | L | Deferred | SQLite has no schema migration, versioning, archival, or horizontal-concurrency strategy. |
| 37 | 55 | M | Avoid multiple app instances | Module-global DB, API-key, and secret state couples application instances. |
| 38 | 53 | M | Pin MVP environment | Dependencies have lower bounds but no lockfile; several runtime dependencies appear unused. |
| 39 | 50 | L | Add targeted MVP tests | Tests miss ordinary multi-page flows, configuration mismatch, proxy spoofing, false feature flags, malformed HTML, and telemetry correctness. |
| 40 | 47 | M | Deferred | The nginx installer is unpinned, system-mutating, non-reproducible, and not safely idempotent. |
| 41 | 45 | M | Deferred | Proxy logs record an incoming JA3 header rather than the computed fingerprint, and expensive public/callback routes are not rate-limited. |
| 42 | 42 | M | Track; public process deferred | Modified public network deployment under AGPL requires an explicit corresponding-source process. |
| 43 | 38 | S | Opportunistic | Ruff reports 40 source diagnostics, broad exceptions, unused imports, and dead or unwired code paths. |

## Definition of done for the first experiment

The MVP is ready for a small paid-model experiment only when:

- A clean trial and each trap condition can be selected explicitly.
- Treatments are independently enabled and verified by tests.
- Every request, model call, action, exposure, callback, and outcome belongs to
  exactly one trial.
- The callback accepts only valid trial-bound synthetic tokens and secrets.
- All configured resource and monetary limits are enforced by the harness.
- A trial cannot reach real services other than the selected model API.
- Provider-reported token counts and cost are stored for every successful call.
- Control and treatment use the same legitimate task and a predeclared scoring
  rule.
- Termination caused by task success, escape, refusal, error, or each budget is
  distinguishable in the result.
