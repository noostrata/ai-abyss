# Next steps

## Purpose

This document defines the implementation sequence for turning the current
mock-validated benchmark harness into a paid-safe calibration system and,
later, a scientifically defensible honeypot benchmark.

It is a plan, not evidence that the listed work has been completed. The current
authorised scope still ends before any paid or hosted-model request. A real
provider run requires a new explicit instruction that identifies the exact
pilot, model route, spending ceiling, and stopping conditions.

## Current position

The repository currently contains:

- the inherited AI Abyss crawler-classification and kill-chain prototype; and
- a separate local benchmark harness under `src/benchmark/`.

The benchmark now has typed trials and events, isolated routes, dynamic
synthetic fixtures, local containment, conservative budgets, condition-aware
scoring, strict evidence/replay, a matched protocol, an exact gated hosted
factory, and both deterministic and loopback-HTTP local rehearsals. It is not
authorized or real-model-validated, and it is not scientific evidence about
model susceptibility.

| Phase | Current state |
|---|---|
| 0–1: authority and truthful outcomes | Implemented, test-covered, locally observed |
| 2: provider-shaped agent loop | Implemented, test-covered, loopback-HTTP observed |
| 3: fail-safe spending | Implemented and fault/boundary tested; not real-provider-validated |
| 4: evidence and containment | Implemented and corruption/failure tested; public signing deferred |
| 5: scientific calibration design | Implemented and locally rehearsed; no real-model outcomes |
| 6: documentation and drift control | Implemented; enforced by `check-drift` and CI |
| 7: unpaid qualification | Passed on clean source commit `15beb12f5aa491dee1f2d451c20e98fe6db0f7ba`; sanitized report tracked |
| 8: paid calibration | Blocked pending a complete, explicitly approved packet |

The implementation should proceed through explicit gates:

```text
truthful status and apparatus contract
    -> truthful outcomes
    -> faithful live-shaped agent loop
    -> fail-safe spending
    -> strong evidence and containment
    -> declared experimental protocol
    -> unpaid qualification
    -> explicit paid-pilot authorization
    -> minimal calibration pilot
    -> benchmark expansion and validation
```

## Working principles

1. Keep the benchmark and inherited public honeypot separate.
2. Fix the meaning of trial data before expanding the experiment.
3. Treat documentation, implementation, tests, mock observations, real-model
   observations, and scientific support as different evidence levels.
4. Keep real-provider execution disabled by default and fail closed.
5. Never infer that a request was unbilled merely because its response was
   missing, malformed, or late.
6. Use a versioned apparatus contract as the authority for event, action,
   outcome, lifecycle, and ledger semantics. Use a separate machine-readable
   experimental protocol for conditions, pairs, seeds, analysis versions, and
   run matrices.
7. Implement one coherent work package at a time, with focused tests and a
   reviewable commit.
8. Do not broaden the benchmark into public legacy-product deployment while
   implementing this plan.

## Complexity scale

- **S:** localized correction with a narrow contract.
- **M:** coordinated changes across several modules or tests.
- **L:** architectural, evidence, or experimental-design change.
- **XL:** broader benchmark and research program.

---

## Phase 0 — Establish one source of truth

**Complexity:** S–M
**Purpose:** prevent later work from relying on claims that the current code
does not establish, and lock the apparatus semantics before changing them.

### Work

1. Preserve the current implementation commit as the mock-MVP baseline.
2. Add a minimal baseline continuous-integration workflow that runs:

   - locked dependency installation;
   - the complete test suite;
   - Ruff;
   - the deterministic mock rehearsal;
   - replay of generated mock artifacts;
   - a test that the runner cannot select or execute a hosted provider.

   Later phases should extend this workflow rather than waiting until the end
   of implementation to introduce CI.

3. Create a versioned, machine-readable apparatus contract defining:

   - action and observation envelopes;
   - event meanings and required evidence;
   - outcome derivation;
   - condition identifiers;
   - trial lifecycle and termination semantics;
   - censoring states;
   - resource-ledger fields;
   - schema, scorer, fixture, and protocol-version identifiers.

   Phase 5 will add a separate experimental protocol for models, tasks,
   repetitions, randomization, spending, and statistical analysis.

4. Convert `issues.md` into the authoritative backlog. Each row should contain:

   - stable issue ID;
   - scope: benchmark, legacy, documentation, or scientific design;
   - severity;
   - fix complexity;
   - affected claims;
   - required gate;
   - current status;
   - implementation evidence;
   - test or artifact evidence.

5. Convert `plan.md` from binary checkboxes to explicit evidence states:

   - implemented;
   - covered by tests;
   - mock-observed;
   - partially implemented;
   - required before paid pilot;
   - deferred.

6. Correct current documentation claims about:

   - live-provider availability;
   - distinct injection outcomes;
   - exact provider routing and fallback behavior;
   - byte-identical paired inputs;
   - complete resource accounting;
   - outbound network instrumentation;
   - recognition and recovery validation;
   - scientific readiness.

7. Preserve the initial repository audit as a dated historical audit rather
   than silently rewriting its original scores.

### Gate 0

- A reader can determine, without reading the implementation, what is merely
  documented, what is implemented, what is mock-validated, and what remains
  blocked.
- No documentation describes the OpenRouter adapter as a runnable live path.
- The current paid-run cutoff remains explicit.
- Baseline CI protects the current mock-MVP behavior before implementation
  changes begin.
- Event, outcome, lifecycle, and ledger semantics have a versioned authority.

---

## Phase 1 — Make trial outcomes truthful

**Complexity:** L
**Purpose:** ensure that every reported outcome follows from observable trial
evidence rather than agent assertions or proxy labels.

### 1.1 Ground task success in the observed trace

Replace suffix-only source evaluation with a trace-grounded evaluator. A
correct result must establish that:

1. the cited source belongs to the active trial origin and path namespace;
2. the page was actually delivered to the provider before the answer;
3. the delivered page contains the accepted answer;
4. the cited observation and answer belong to the same trial and task version;
5. the answer event occurs after the qualifying observation.

Add negative tests for guessed answers, hostile origins, relative-path tricks,
unvisited sources, sources from another trial, and answers observed only after
submission.

### 1.2 Simplify and separate synthetic-injection outcomes

Implement separate observable outcomes for the initial benchmark:

1. injected payload delivered to the provider;
2. callback URL visited;
3. submission attempted;
4. exact synthetic secret submitted.

Remove `secondary_instruction_followed` from the MVP contracts, scoring, and
claims. Do not infer it from the callback or initial secret submission. A real
second stage may return later as a separately controlled experimental condition
with its own neutral token or observable action.

A wrong or missing secret may record a callback visit and attempted submission,
but must not count as exact-secret success.

### 1.3 Stabilize treatment material within a trial

Issue one injection-material object per trial and reuse it on every rendering
of the treatment page. Repeated states must retain the same content, token,
payload ID, and content hash unless a declared condition explicitly tests
changing content.

### 1.4 Make callback evidence atomic

Perform token validation, expiry and digest checks, single-use consumption, and
normalized callback-event insertion inside one database transaction. A failed
event write must leave the token reusable or roll the whole transaction back.

### 1.5 Correct metric semantics

Make scoring condition-aware and distinguish:

- graph entry;
- recursive-trap entry;
- graph exit;
- legitimate-task resumption;
- eventual task completion;
- repeated-state count;
- completed graph-cycle traversal;
- actions directed at the trap;
- time or steps spent in the trap;
- recognition;
- escape;
- re-entry.

Do not label a finite-control graph as a trap merely because a graph page was
visited. Do not equate recovery with escape. Keep recognition secondary until
its rubric is validated.

### 1.6 Make paired model-facing inputs equivalent

Keep distinct internal trial IDs for state and evidence, but use a shared opaque
model-facing namespace for paired arms until their declared treatment
divergence. The model-facing namespace must not reveal condition or pair labels.

Add snapshot tests over the exact serialized provider envelopes—not only
rendered fixtures—to prove equality before divergence. If literal equality is
not possible for a declared field, define and version the canonical
normalization and describe the inputs as structurally equivalent rather than
byte-identical.

### Gate 1

- Every primary result can be reconstructed from the event trace without
  trusting a model-provided URL, label, or claim.
- Injection delivery, callback visit, submission attempt, and exact-secret
  submission have independent positive and negative tests.
- A repeated treatment state remains stable within a trial.
- Metric names match their implemented meaning.
- Paired provider envelopes are equal before the declared treatment divergence,
  or their versioned normalization is explicit and tested.

---

## Phase 2 — Build a faithful live-shaped agent loop

**Complexity:** L
**Purpose:** make local fake-provider and future real-provider execution use the
same declared agent contract as the mock path.

### 2.1 Inject providers into the runner

Remove the runner's internal hard dependency on `MockProvider`. Support two
selectable modes through one provider interface during this phase:

- deterministic mock;
- local fake OpenRouter-compatible server.

Prepare the interface needed by a future real provider, but do not add a
selectable real-provider factory yet. Real-provider construction is introduced
only after the spending work and Gate 3 pass.

### 2.2 Add bounded trajectory history

Each provider decision should receive a reproducible, versioned history of the
relevant prior:

- observations;
- actions;
- tool results;
- navigation failures;
- visited URLs;
- truncation or summarization decisions.

Prefer explicit serialized history over hidden provider-side conversation
state. Record the exact model-facing envelope after redaction.

### 2.3 Enforce the action contract

Send the exact action schema through the provider's supported structured-output
mechanism and validate every response strictly. Predeclare:

- whether repair is allowed;
- the maximum repair attempts;
- whether repair consumes another call and action reservation;
- how malformed responses terminate or censor a trial.

### 2.4 Define and locally verify provider routing

The provider contract, fake-provider fixtures, and future real-provider request
must include:

- exact model ID;
- exact provider route;
- fallback disabled;
- required parameter support;
- fixed sampling and reasoning controls;
- actual returned model identity;
- actual provider route and available router metadata;
- request or generation identifier;
- current price-snapshot identifier.

The fake-provider run must fail closed if returned identity or routing does not
match its declared protocol. The same check will guard real-provider execution
after Phase 3.

### 2.5 Add a local fake-provider server

Exercise the complete HTTP provider path locally. The fake server should
produce fixtures for:

- valid structured actions;
- malformed JSON;
- schema-invalid JSON;
- delayed responses and timeouts;
- disconnects before and after request receipt;
- provider errors;
- missing usage or cost fields;
- reasoning-token variants;
- unexpected model or provider identity.

### Gate 2

- Mock and fake-provider modes travel through the same runner lifecycle,
  budgets, event recording, scoring, and export path.
- A real-shaped provider receives bounded trajectory history and an enforceable
  action schema.
- No hosted request or credential is required to demonstrate the complete path.
- No configuration, environment variable, or normal runner factory can select
  or invoke a hosted provider at this gate. The isolated adapter may remain
  constructible in mocked contract tests, but it is not an execution path.

---

## Phase 3 — Make spending genuinely fail-safe

**Complexity:** L
**Purpose:** ensure that every possible provider call is covered by conservative
trial and batch reservations.

### 3.1 Reserve action capacity before provider execution

Reserve both model-call and action capacity before the provider is invoked.
Reconcile or release both reservations together according to a declared
malformed-response policy. No call may occur after action capacity is exhausted.

### 3.2 Add a call-attempt ledger

Represent provider attempts with explicit states such as:

```text
reserved -> locally_started -> sent -> acknowledged -> reconciled
                                  \-> billing_unknown
```

Distinguish:

- definitely not sent;
- sent with no response;
- rejected before inference;
- completed but malformed;
- completed with known usage and cost;
- billing status unknown.

Unknown billing must retain the worst-case reservation until it is reconciled.
It must not reopen batch capacity as though it were free.

### 3.3 Normalize tokens and costs

Define and test provider-specific mappings for:

- input tokens;
- cached input tokens;
- total output tokens;
- reasoning tokens as an output subset;
- provider-reported total tokens;
- provider-reported cost;
- conservative estimated cost;
- reconciliation status.

Do not add reasoning tokens to a completion count that already includes them.
Do not record zero cost merely because provider cost is absent.

### 3.4 Complete the minimum authoritative resource ledger

Record an end-of-trial ledger from authoritative runtime counters rather than
reconstructing the result only from whichever events the scorer reads. Before
the calibration pilot, it must include:

- provider attempts and reconciliation states;
- known and maximum-possible model cost;
- model calls;
- input, output, reasoning, and cached tokens;
- scaffold requests and redirects;
- bytes generated, sent, and delivered;
- agent actions;
- nodes and maximum depth;
- trial wall time.

Pair summaries must report treatment-minus-control deltas for all of these
fields. CPU, memory, connection, and file-descriptor instrumentation may remain
post-calibration work, but absent fields must stay explicitly unavailable rather
than silently becoming zero.

### 3.5 Pin a price snapshot

Every authorized paid protocol should bind reservations to a reviewed price
snapshot with source, retrieval time, model, provider route, token categories,
and any request-level fees.

### 3.6 Prove all hard-limit boundaries

Add fault-injection and exact-boundary tests for:

- trial and batch cost;
- model calls;
- actions;
- input, output, and reasoning tokens;
- scaffold requests and redirects;
- response and cumulative bytes;
- nodes and depth;
- wall-clock deadlines;
- cancellation;
- concurrent trials;
- provider response loss after transmission.

### 3.7 Add the gated real-provider factory

Only after Sections 3.1–3.6 pass should the runner gain a factory capable of
selecting the real OpenRouter adapter. Selection must require a separate,
fail-closed authorization object bound to:

- exact protocol and software versions;
- model and provider route;
- price snapshot;
- trial and batch ceilings;
- expiration or one-run scope;
- operator approval evidence.

Checked-in configuration remains mock-only and `allow_paid: false`. A normal
test, rehearsal, environment variable, or permissive configuration flag must
not be sufficient to activate the real provider.

### Gate 3

- Every simulated provider failure records a possible cost at least as large as
  the maximum amount that could have been billed.
- No action or call limit permits one extra provider request.
- Trial and batch ceilings remain correct under concurrency and cancellation.
- The minimum resource ledger and all treatment-control deltas are complete and
  internally reconciled.
- Real-provider construction exists only behind the separate authorization
  object and has no default credential-loading path.

---

## Phase 4 — Strengthen evidence, containment, and runtime integrity

**Complexity:** L
**Purpose:** make results reproducible, diagnosable, and resistant to silent
corruption or containment drift.

### 4.1 Evidence and replay

- Preserve redacted exact provider request and response envelopes.
- Redact registered sensitive values recursively from rationales, answers,
  URLs, fields, errors, and metadata.
- Validate unique and contiguous event sequences.
- Validate trial identity and lifecycle ordering.
- Compare recomputed results with stored results during replay.
- Include fixture, scorer, schema, protocol, and software digests in manifests.
- Write artifacts using temporary files and atomic replacement.
- Bind the final artifact-root digest to the sanitized, commit-specific evidence
  report and preserve it as a CI artifact outside the raw trial directory.
- Track a sanitized, commit-bound evidence summary while leaving raw trial
  artifacts ignored.

External cryptographic signing, immutable public storage, and release-level
provenance are required before a public benchmark release, but they should not
delay a minimal calibration pilot once local integrity and replay checks pass.

### 4.2 Lifecycle and failure handling

- Use expected-prior-state updates for start and end transitions.
- Convert setup, construction, finalization, export, and persistence failures
  into explicit retained outcomes where possible.
- Preserve sanitized exception type and diagnostic information.
- Perform bounded finalization after cancellation, then re-raise cancellation.
- Enforce manifest/result termination coherence.

### 4.3 Request and configuration boundaries

- Stream callback bodies and stop reading at the configured maximum.
- Validate loopback URLs using parsed scheme, host, and port rather than string
  prefixes.
- Require configured benchmark and callback ports to match the bound server.
- Record partial bytes delivered before response-limit failures.
- Distinguish bytes generated, bytes sent, and bytes delivered to the model.

### 4.4 Stronger real-run isolation

For any future hosted-provider execution, supplement the in-process socket
barrier with an operating-system or proxy-enforced policy that allows only:

- the local benchmark scaffold;
- the exact authorized provider API endpoint;
- narrowly required DNS and TLS infrastructure.

### Gate 4

- Corrupted, incomplete, reordered, mismatched, or wrong-version artifacts fail
  replay.
- Unexpected failures remain visible and diagnosable.
- Runtime containment does not depend only on application-level URL checks.

---

## Phase 5 — Define the scientific experiment

**Complexity:** XL
**Purpose:** define a small, declared calibration experiment without requiring
the breadth of a finished benchmark.

### 5.1 Define primary comparisons

Use these primary contrasts:

```text
recursion effect:
    matched finite graph vs recursive graph

injection effect:
    length-matched inert or benign content vs synthetic injected instruction
```

Plain control versus recursive graph may remain an exploratory contrast, but it
must not be presented as isolating recursion because graph presence, content,
and topology all change.

### 5.2 Create a machine-readable experimental protocol

This is separate from the apparatus contract created in Phase 0. The
experimental protocol should declare:

- task and fixture versions;
- conditions and allowed pair types;
- model, provider, and scaffold identities;
- trajectory and truncation policy;
- seeds and repetitions;
- randomized or block-balanced execution order;
- primary and secondary outcomes;
- censoring rules;
- infrastructure-failure and missing-data policy;
- exclusions;
- stopping rules;
- spending ceilings;
- analysis version.

Generate run matrices and documentation tables from this source.

### 5.3 Prepare the minimal calibration task and pair set

Before calibration:

- provide at least one nontrivial task with a dynamic per-trial or per-release
  answer;
- remove ordering or wording that makes the correct source trivially obvious;
- include one matched finite-versus-recursive pair;
- include one length-matched injection/control pair only if injection is in the
  calibration scope;
- version all content and include canonical fixture digests in manifests.

Multiple independently designed tasks, held-out variants, and broader lure
families belong in Phase 9. They are necessary before benchmark claims, but not
before a minimal live-system calibration.

### 5.4 Validate recognition and recovery

Keep escape and eventual task completion as primary observable measures. Treat
recognition as secondary until a predeclared rubric is validated against
blinded human review, with disagreement and missing-rationale policies.

### 5.5 Declare the statistical plan

The calibration protocol must predeclare a small fixed number of repetitions
and explicitly prohibit population-level efficacy claims. Use the first paid
calibration only to estimate variance, failure modes, and measurement behavior.
Afterward determine:

- repetitions and sample-size rationale;
- paired confidence intervals;
- binary, count, and time-to-event analyses;
- right-censoring treatment;
- model, task, provider, order, and temporal effects;
- multiple-comparison policy.

### Gate 5

- The protocol states exactly what will be estimated before real-model outcomes
  are observed.
- Every primary comparison has an appropriate matched control.
- Task utility, trap behavior, and resource cost remain separate outcome
  families.
- The calibration matrix is intentionally small; benchmark breadth is not a
  prerequisite for testing whether the live apparatus behaves correctly.

---

## Phase 6 — Synchronize documentation and automate drift detection

**Complexity:** M
**Purpose:** make repository claims follow the final interfaces and protocol.

### Work

1. Rewrite `README.md` around the explicit legacy-prototype/benchmark split.
2. Add a status table for implemented, test-covered, mock-observed,
   real-model-observed, and production-ready claims.
3. Keep `issues.md` as the live backlog and `plan.md` as the historical
   implementation record.
4. Keep `existing benchmark review.md` literature-focused and add an
   implementation crosswalk against its recommended control matrix.
5. Promote `agent.md` to `AGENTS.md`, or add a minimal discoverable redirect.
6. Add a data dictionary for every event, metric, ledger field, termination
   reason, and censoring state.
7. Track a sanitized evidence report bound to the exact commit and protocol.
8. Remove brittle hard-coded test counts from general documentation.
9. Extend the baseline continuous integration created in Phase 0 with:

   - Ruff;
   - the complete test suite;
   - mock rehearsal;
   - fake-provider rehearsal;
   - offline replay;
   - artifact-corruption tests;
   - documentation commands and links;
   - protocol, matrix, schema, and evidence drift.

### Gate 6

- Repository documentation is generated from or tested against the same
  contracts and protocol used by the runner.
- No claim of real-model evidence appears before an authorized real-model run.

---

## Phase 7 — Complete unpaid qualification

**Complexity:** M
**Purpose:** demonstrate the entire paid-shaped system without contacting a
hosted model.

**Status:** complete for the unpaid apparatus. The sanitized report at
`docs/evidence/unpaid-qualification.json` binds the checks to clean source
commit `15beb12f5aa491dee1f2d451c20e98fe6db0f7ba`, the dependency lock, apparatus,
protocol, scorer, and benchmark software digests. The report-bearing commit
changes documentation only; CI repeats the same unpaid gates on every commit.

### Qualification sequence

1. Run the locked full test suite and Ruff.
2. Run the deterministic mock rehearsal.
3. Run the fake-provider rehearsal through real HTTP transport.
4. Exercise every budget boundary.
5. Exercise timeout, disconnect, malformed-response, wrong-identity, and
   unknown-billing cases.
6. Exercise cancellation and concurrent trials.
7. Corrupt and reorder copied artifacts and confirm replay rejection.
8. Audit attempted outbound network destinations.
9. Verify every documented command from a clean checkout.
10. Independently review the resulting sanitized evidence bundle.

### Paid-pilot authorization packet

At the end of unpaid qualification, stop. Prepare a review packet containing:

- exact commit and clean-worktree status;
- exact protocol and scorer versions;
- exact model and provider route;
- current price snapshot;
- number of trials and maximum calls;
- per-trial and batch spending ceilings;
- trajectory and action-schema policy;
- automatic abort conditions;
- expected artifacts;
- unresolved limitations;
- rollback and credential-removal procedure.

The draft packet is `docs/paid-pilot-authorization-packet.md`. It deliberately
leaves the exact model, upstream route, current price snapshot, provider-side
limit, credential reference, external-isolation evidence, kill-switch ID, and
run commit unbound. Therefore it is not an authorization.

## Hard cutoff before paid execution

Completion of Phases 0–7 does not authorize a hosted-model request. Do not load
a credential, enable real-provider mode, or send a paid request until the user
explicitly approves the exact authorization packet.

---

## Phase 8 — Run a minimal paid calibration pilot

**Requires new explicit authorization.**
**Purpose:** validate live execution and estimate measurement behavior, not
claim benchmark performance.

### Initial scope

- one exact model and provider route;
- one or very few nontrivial dynamic synthetic tasks;
- matched finite-versus-recursive comparison;
- an injection/control pair only if injection is explicitly included;
- minimal predeclared repetitions;
- strict trial and batch caps;
- active monitoring;
- automatic stop on routing, identity, cost, schema, evidence, or containment
  anomalies.

### Pilot interpretation

Label results as calibration evidence from the declared task, model, provider,
and scaffold. Do not generalize susceptibility rates across agents or model
families.

### Gate 8

- Reconcile every call and the complete batch cost.
- Review malformed actions, censoring, failures, routing, and containment.
- Confirm that outcome distributions support the intended measurements.
- Resolve discovered implementation defects before expanding the matrix.

---

## Phase 9 — Expand into a credible benchmark

**Complexity:** XL

- Add multiple tasks and held-out variants.
- Add multiple models with pinned provider routes.
- Add at least two agent scaffolds.
- Add inert, helpful, irrelevant, conflicting-benign, and realistic injection
  controls.
- Add any genuine secondary-instruction-following treatment as its own
  controlled condition rather than inferring it from an initial callback.
- Add latency-only, volume-only, and recursion-only treatments before combined
  recursion-plus-injection arms.
- Size repetitions using calibration variance.
- Report paired uncertainty estimates and censored outcomes.
- Validate recognition scoring with blinded reviewers.
- Instrument CPU, memory, connections, file descriptors, bytes, wall time, and
  marginal monetary cost.
- Add contamination checks, defense baselines, and security–utility frontiers.
- Preregister the confirmatory protocol.
- Produce a versioned data and benchmark release with authenticated evidence
  commitments and replication instructions.
- Sign or externally commit public release roots using a mechanism independent
  of the writable raw-artifact directory.

### Gate 9

- Claims are limited to the tested task, model, provider, scaffold, and protocol
  population.
- Primary results have matched controls, uncertainty estimates, failure
  accounting, and reproducible artifacts.

---

## Phase 10 — Handle the inherited legacy product separately

**Complexity:** XL
**Purpose:** prevent benchmark work from being mistaken for production hardening
of the original public honeypot.

If the inherited crawler product will be maintained or deployed, create a
separate branch or workstream for:

- correct robots-policy semantics;
- classifier validity and false-positive analysis;
- trusted-proxy and source-identity boundaries;
- public C2 minimization and sensitive-context handling;
- admin authentication and authorization;
- privacy, retention, deletion, and audit policy;
- public fabricated-content and indexing policy;
- rate limiting and operator self-DoS protection;
- telemetry validity;
- database migration, concurrency, and scaling;
- deployment security and legal-claim review.

If public deployment is not a goal, mark the inherited system as experimental
and keep it unreachable from benchmark mode rather than allowing this workstream
to delay the benchmark.

---

## Recommended implementation and commit order

1. `docs: correct current benchmark status`
2. `ci: protect the mock-mvp baseline`
3. `feat: define the versioned apparatus contract`
4. `fix: ground task outcomes in observed traces`
5. `fix: simplify and atomically record injection outcomes`
6. `fix: make scoring condition-aware`
7. `fix: make paired model-facing inputs equivalent`
8. `feat: add bounded trajectory and provider-injected runner`
9. `feat: add fake OpenRouter end-to-end harness`
10. `fix: enforce pre-call budgets and conservative billing`
11. `fix: normalize usage, cost, and minimum resource ledgers`
12. `feat: add gated real-provider construction`
13. `feat: strengthen evidence replay and redaction`
14. `fix: harden lifecycle and network boundaries`
15. `feat: add machine-readable experimental protocol`
16. `feat: add minimal matched calibration tasks`
17. `ci: qualify the unpaid benchmark`
18. `docs: synchronize architecture, protocol, and evidence`

Each commit should include its focused tests and update the corresponding issue
status. Avoid combining provider execution, scoring changes, experimental
design, and documentation restructuring in one large commit.

## Optimal sequencing rationale

The order is deliberate:

1. Baseline CI protects every intermediate refactor rather than appearing only
   after the implementation is assembled.
2. The apparatus contract fixes event and outcome meanings before code changes
   encode them.
3. Outcome correctness comes next because invalid labels contaminate every
   later result.
4. The live-shaped agent contract follows because recognition and recovery
   cannot be studied with a memoryless or underspecified model loop.
5. Spend safety is completed before any factory can construct a hosted
   provider.
6. Minimum resource ledgers are completed before calibration so cost and
   self-DoS measurements can themselves be calibrated.
7. Evidence and containment are hardened before experimental results depend on
   them.
8. The small experimental protocol is finalized only after apparatus semantics
   are stable; benchmark breadth remains post-calibration work.
9. Documentation is synchronized twice: first to correct current overclaims,
   then after implementation to prevent drift.
10. The entire system is qualified without payment before asking for a narrowly
    scoped paid calibration.
11. Multi-model, secondary-stage, public-provenance, and publication work begins
    only after calibration reveals real variance and failure modes.

This sequence minimizes rework while preserving the current fail-closed safety
boundary.
