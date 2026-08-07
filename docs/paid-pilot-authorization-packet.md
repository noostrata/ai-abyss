# Paid-pilot authorization packet

## Status

**Not authorized. Do not load a credential or send a hosted request.**

This is the review template at the unpaid cutoff. An operator must replace every
`UNBOUND` field, review current provider information, and explicitly approve
the resulting exact packet. Repository implementation, passing unpaid checks,
or approval of an earlier plan does not authorize payment.

## Qualified apparatus

| Item | Bound value |
|---|---|
| Unpaid evidence | `docs/evidence/unpaid-qualification.json` |
| Tested source commit | `80ee9262c259eb73d1a9ed0cf5a96e42eb80b1df` |
| Required run commit | `UNBOUND`; must be exactly clean and equal to authorization |
| Schema | `3.3.0` |
| Apparatus | `1.6.0`; digest is bound in `protocol/calibration-v1.json` |
| Experimental protocol | `honeypot-calibration-v1` version `1.0.0` |
| Scorer | `trace-scorer-2.0.0`; exact digest must be bound |
| Task | `synthetic_relay_lookup` version `2.0.0` with per-pair dynamic answer |
| Scaffold | `http-dom-1.0.0`; trajectory policy `trajectory-v1` |
| Action schema | `browser-actions-1.0.0`, strict JSON schema |
| Cache policy | `fresh_no_cache` |

## Provider and price bindings

| Required field | Current value |
|---|---|
| Exact OpenRouter model ID | `UNBOUND` — blocking |
| Exact upstream provider route | `UNBOUND` — blocking |
| Returned identity fields expected | `UNBOUND` — blocking |
| Current price source URL | `UNBOUND` — blocking |
| Price observation timestamp | `UNBOUND` — blocking |
| Prompt price | `UNBOUND` — blocking |
| Completion price | `UNBOUND` — blocking |
| Reasoning price semantics | `UNBOUND` — blocking |
| Cache price semantics | `UNBOUND` — blocking |
| Price snapshot ID and digest | `UNBOUND` — blocking |

Routing must use one exact model and one exact provider in both `order` and
`only`, with fallback disabled, parameter support required, and data collection
denied. Returned model and route drift stop the batch.

## Maximum experimental scope

The committed protocol permits at most:

- four matched pairs and eight trials;
- eight model calls per trial;
- 512 completion tokens per call;
- 512 reasoning tokens per call, treated as a subset of completion tokens;
- USD 0.50 maximum per trial;
- USD 4.00 maximum for the batch; and
- a provider-side spending limit no greater than USD 4.00.

Authorization may tighten these ceilings. It may not widen them without a new
protocol version and another complete unpaid qualification.

The first run is apparatus calibration. Report raw paired outcomes and failures;
do not rank models, report p-values, or estimate population susceptibility.

## Required operational bindings

The final packet must name:

- one exact, expiring, single-run `PaidRunAuthorization` ID;
- one dedicated credential reference stored outside Git and never included in
  an artifact, log, manifest, or command line;
- a verified provider-side hard spending limit and reset policy;
- current external OS firewall or dedicated-proxy evidence that permits only
  the local benchmark origins and exact provider endpoint;
- a kill-switch ID and the operator responsible for invoking it;
- an artifact-policy ID covering redacted envelopes, retention, and deletion;
- a no-retry policy; and
- the exact clean software commit.

## Automatic abort conditions

Stop before another trial or call on any:

- model, provider-route, response-schema, price, authorization, or commit drift;
- missing/expired external-isolation evidence;
- containment violation or non-allowlisted destination;
- billing-unknown sent request pending operator review;
- provider-reported or estimated cost anomaly;
- trial, batch, token, action, request, byte, node, depth, or wall-time boundary;
- lifecycle, event-sequence, artifact, redaction, digest, or replay failure;
- cancellation or infrastructure failure that could affect evidence integrity;
  or
- observed credential exposure.

No failed trial is silently retried or replaced.

## Expected evidence

Every trial should produce an ended manifest, contiguous JSONL event stream,
result bundle, evidence hashes, pair comparison, redacted provider envelopes,
call-attempt ledger, three resource ledgers, and successful offline replay.
The batch review must reconcile every provider attempt, acknowledged response,
billing-unknown upper bound, native usage record, known cost, and
maximum-possible cost.

## Known limitations

- No real-model behavior has yet been observed.
- One dynamic task and one scaffold test apparatus behavior, not benchmark
  breadth or generality.
- The calibration is too small for population inference or model ranking.
- Recognition has not been validated on real-model rationales by blinded human
  reviewers.
- CPU, memory, connection, and file-descriptor attribution remains unmeasured.
- Local evidence hashes are not an independent public signature or transparency
  log.
- The inherited public honeypot is outside the experiment and remains
  unqualified for deployment.

## Rollback and credential removal

On any abort: cancel outstanding runner tasks, close browser and provider
transports, preserve the bounded failure artifacts, revoke the dedicated key at
the provider, verify that its spending limit is closed, remove its local secret
reference, restore checked-in `execution_mode: mock` and `allow_paid: false`,
and run `uv run ai-abyss-benchmark check-drift --require-evidence` plus the full
unpaid checks before considering another authorization.

## Approval checklist

- [ ] Exact clean run commit bound.
- [ ] Exact model and upstream route reviewed.
- [ ] Current price snapshot reviewed and hashed.
- [ ] Trial, token, cost, and provider-side ceilings accepted.
- [ ] Dedicated credential and removal procedure verified.
- [ ] External isolation evidence current.
- [ ] Kill switch tested and responsible operator named.
- [ ] Artifact and retention policy accepted.
- [ ] Limitations and calibration-only interpretation accepted.
- [ ] User explicitly authorizes this exact single run.

Until every item is checked in one exact packet, hosted provider construction
must fail before credential loading or network I/O.
