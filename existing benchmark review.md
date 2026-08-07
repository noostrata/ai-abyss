# Existing benchmark review

**Review cutoff:** 7 August 2026
**Target project:** AI Abyss, commit `af3e6cb0a10237933d1362246405fb594bdf5adf`

## Executive conclusion

AI Abyss is not entering an empty field. The strongest correction to the
original project framing is that close precedents already exist:

- [CHeaT](https://www.usenix.org/conference/usenixsecurity25/presentation/ayzenshteyn)
  directly lures and traps LLM penetration-testing agents with cyclic
  references, search-space expansion, large irrelevant outputs, brute-force
  bait, misinformation, prompt injection, and LLM-specific honeytokens.
- [TRAP](https://arxiv.org/abs/2512.23128) measures whether realistic web
  agents are persuaded by injected interface content to abandon their original
  task. It also records trajectories that reach an action cap.
- [The Compliance Trap / MemTrapBench](https://arxiv.org/abs/2607.10608)
  separates entry, propagation, and recovery after agents consume conflicting
  memory.
- [Honeyval](https://arxiv.org/abs/2605.29963) measures honeypot interaction
  length, detectability, fidelity, exploitability, and attacker-versus-defender
  cost. Its direction is reversed: the LLM operates the honeypot and an agent
  attacks it.
- [SpiderTrap](https://doi.org/10.1109/ACCESS.2020.3012969) and earlier crawler
  honeypots establish the pre-LLM lineage for recursive-link attraction,
  session depth, dwell, crawler classification, and trap recognition.
- [LoopTrap](https://arxiv.org/abs/2605.05846) directly poisons agent
  termination judgments and measures step amplification, while
  [AgentDoS](https://www.usenix.org/conference/usenixsecurity26/presentation/luo)
  and [Beyond Max Tokens](https://arxiv.org/abs/2601.10955) cover agent
  resource lifecycles and tool-chain cost amplification.

The defensible research contribution is therefore not “the first LLM
honeypot” or “the first benchmark that traps agents.” A narrower and still
useful contribution is:

> A controlled, cross-model benchmark that jointly measures navigable
> web-honeypot attraction, recursive graph stickiness, victim-versus-defender
> resource amplification, trap recognition and escape, recovery of the
> legitimate task, re-entry or cross-session contamination, and benign-task
> utility under matched causal ablations.

No work identified in this review, including peer-reviewed papers and
preprints, jointly evaluates all of those outcomes under one protocol. That is
a provisional gap worth testing, not a proven novelty claim until final
citation-chaining and the benchmark experiment are complete.

## Scope and method

Two independent review passes covered five connected literatures:

1. honeypots designed to deceive LLM agents;
2. web-agent indirect prompt-injection and task-redirection benchmarks;
3. long-horizon tool-agent and memory-persistence benchmarks;
4. traditional crawler traps, robots behaviour, and crawler measurement;
5. resource-amplification, cost-accounting, and LLM-powered honeypot work.

The review prioritised primary paper pages, proceedings, official artifacts,
and repositories. “Peer reviewed” is stated only when a proceedings or venue
page was located. An arXiv paper is labelled a preprint even if its comments
name a prospective conference. The inventory is intentionally broad, but it is
a living benchmark map rather than a claim that every paper ever published has
been found.

## Coverage map

| Research line | What it already measures | What AI Abyss can add |
|---|---|---|
| LLM-agent deception | Lures, loops, misinformation, honeytokens, search expansion | Common web protocol, recovery and utility, budget-normalised capture |
| Web prompt injection | Exposure, attempted hijack, terminal attack success, task success | Recursive depth, dwell, recognition, escape and re-entry |
| Memory poisoning | Entry, propagation, persistence, recovery | Web-originated contamination tied to an observable trap graph |
| LLM honeypots | Interaction length, fidelity, detection and economic asymmetry | Reverse the roles: measure the LLM agent as the trapped party |
| Crawler traps | Traversal, sessions, link depth, robots behaviour | Model calls, tokens, decisions, recovery and task utility |
| Resource traps | Slowdown, action caps, request volume, query-budget consumption | Matched latency/volume/recursion arms and provider-reported monetary cost |
| Agent safety | Harmful tool calls, policy compliance, indirect injection defenses | A specific “stuckness” outcome with right-censored budget exhaustion |

## Closest precedents

### 1. CHeaT: Cloak, Honey, Trap

**Status:** peer reviewed, USENIX Security 2025.
**Primary sources:** [conference page](https://www.usenix.org/conference/usenixsecurity25/presentation/ayzenshteyn),
[paper](https://www.usenix.org/system/files/usenixsecurity25-ayzenshteyn.pdf),
[code](https://github.com/Daniel-Ayz/CHeaT).

CHeaT is the closest conceptual predecessor. It evaluates deception against
LLM-based penetration-testing agents and groups mechanisms into cloaking,
honey, and trapping strategies. Relevant techniques include circular file or
reference structures, exploding search spaces, very large irrelevant outputs,
brute-force bait, false clues, prompt injection, and honeytokens. The published
evaluation covers three pentesting-agent systems, several model backends, and
11 CTF machines. It reports 4,233 scored samples, roughly 55–67% deception for
individual techniques, and stronger results for technique combinations. The
roughly 60-fold slowdown from expanding a writable-file search space and the
circular-reference demonstrations are strong evidence of resource capture,
but the latter are not a controlled dwell/escape or survival analysis.

What to reuse:

- its trap taxonomy rather than inventing a disconnected list of tricks;
- cyclic references and search-space expansion as distinct treatments;
- honeytokens as observable events rather than claims about model training;
- slowdown and task failure as separate outcomes;
- combinations only after single-mechanism ablations are understood.

What remains open for this project:

- general web agents rather than penetration-testing agents;
- exact resource accounting per model call and browser action;
- explicit recognition, escape, and recovery metrics;
- matched benign tasks and utility-conditioned safety;
- causal separation of recursion, latency, volume, injection, and false facts.

### 2. TRAP: Task-Redirecting Agent Persuasion

**Status:** peer reviewed and accepted at ICML 2026.
**Primary sources:** [final paper](https://openreview.net/pdf/40b95f672ebb3564dec559932fd647643e82f1f6.pdf),
[project](https://oxrml.com/its-a-trap/),
[arXiv record](https://arxiv.org/abs/2512.23128).

TRAP places 35 persuasion-style injection templates across 18 tasks in
high-fidelity clones of Amazon, Gmail, Calendar, LinkedIn, DoorDash, and
Upwork. Across six frontier models, the reported mean attack success is 25%,
with substantial model and presentation effects. Its trajectory data are
particularly relevant: 639 of 3,780 runs reached the 35-step cap after
exposure. Reaching that cap is right-censoring, not proof of a loop.

What to reuse:

- realistic, task-relevant placement of lures;
- fixed action caps and explicit termination causes;
- modular injection templates and controlled UI variations;
- exposure-conditional metrics rather than dividing by all runs;
- high-fidelity local sites, potentially through the REAL substrate.

What remains open:

- recursively generated trap graphs;
- direct byte, token, model-call, wall-time, and monetary accounting;
- trap recognition, exit latency, legitimate-task recovery, and re-entry.

### 3. The Compliance Trap and MemTrapBench

**Status:** arXiv preprint.
**Primary source:** [paper](https://arxiv.org/abs/2607.10608).

This work contributes the most useful trajectory decomposition for the planned
benchmark: **Entry–Propagation–Recovery (E–P–R)**. MemTrapBench controls when
conflicting memory appears, whether it repeats, and how the agent behaves after
leaving the correct path. Its central result is that the first exposed decision
can cause compliance, repetition amplifies the deviation, and recovery is
weak.

What to reuse:

- a trajectory-level distinction between initial influence, propagation, and
  recovery rather than one terminal score;
- propagation as downstream influence after entry;
- recovery as return to a correct trajectory and final task completion;
- early/late and single/repeated exposure schedules;
- helpful, irrelevant, and conflicting non-malicious controls.

AI Abyss can extend E–P–R from retrieved memory to navigable web graphs and add
resource capture, recognition, exit latency, and re-entry.

### 4. Honeyval

**Status:** arXiv preprint with an open artifact.
**Primary sources:** [paper](https://arxiv.org/abs/2605.29963),
[repository](https://github.com/google-research/honeyval).

Honeyval evaluates LLM-powered HTTP honeypots grounded in 16 vulnerable
backend applications, using AI hacking agents as attackers. It compares LLM
honeypots with rule-based baselines and measures exploitability, interaction
length, detection, fidelity, and economic asymmetry under spend caps. Its
reported comparison includes about 82.6 requests for LLM honeypots versus 30.6
for a rule-based baseline and approximately 3.5–4.7-fold cost asymmetry,
depending on configuration.

The roles differ from AI Abyss, but the methodology transfers directly:

- pair each trap with capability controls;
- report interaction length and detection jointly;
- account for both defender and attacker cost;
- impose hard spend caps and treat capped trials explicitly;
- avoid interpreting long interaction as success if fidelity or utility fails.

### 5. SpiderTrap and the crawler-honeypot lineage

**Status:** SpiderTrap is peer reviewed in IEEE Access (2020).
**Primary sources:** [SpiderTrap DOI](https://doi.org/10.1109/ACCESS.2020.3012969),
[BotSeer](https://clgiles.ist.psu.edu/pubs/ICWE2008.pdf),
[Detection of Crawler Traps](https://www.scitepress.org/PublishedPapers/2020/93672/),
[IRLbot](https://doi.org/10.1145/1541822.1541823),
[Spider Pool](https://www.usenix.org/conference/usenixsecurity16/technical-sessions/presentation/du).

This literature predates agentic LLMs but already treats a trap as a graph and
a crawler interaction as a session. It supplies mature concepts: link type,
traversal depth, revisit behaviour, dwell, robots compliance, loop avoidance,
and crawler-versus-scanner classification. SpiderTrap's 140-day deployment
recorded 54,054 requests and 994 crawler sessions; its longest session reached
1,185 requests over roughly 510 seconds. Those live IP/user-agent/session labels
are observational rather than controlled ground truth.

The important transfer is structural, not classificatory. A controlled model
benchmark already knows its trial identity and does not need to infer hostility
from IP addresses or user-agent strings. It should reuse graph/session metrics
without copying live-web bot attribution into the MVP.

### 6. LoopTrap: termination poisoning

**Status:** arXiv preprint.
**Primary source:** [paper](https://arxiv.org/abs/2605.05846).

LoopTrap defines ten termination-poisoning strategies that make an iterative
agent judge an incomplete task as still requiring work. It evaluates eight
agents on 60 tasks and reports 3.57-fold average and 25-fold peak step
amplification. This is the closest precedent for “the agent gets stuck.” Its
setting is not a recursive web graph and it does not jointly measure
recognition, escape, task recovery, clean utility, or victim/operator cost.

What to reuse:

- step amplification against matched normal execution;
- repeated-state and termination-decision evidence, rather than treating any
  long run as a loop;
- agent-specific behavioural profiling and adaptive trap selection later;
- action ceilings with censored time-to-escape reporting.

### 7. WebTrap Park, AgentBait, and new web traps

**Status:** recent benchmark preprints; SecureWebArena below is peer reviewed.

[WebTrap Park](https://arxiv.org/abs/2601.08406) offers 1,226 executable web
tasks spanning malicious user prompts, indirect injection, and deceptive site
design. [AgentBait](https://arxiv.org/abs/2601.07263) evaluates task-aligned
social-engineering traps such as authentication popups and sensitive-data forms
over 500 tasks and five frameworks. Neither requires the project to invent the
idea of a deceptive website or contextual lure.

Two preprints submitted on 5 August 2026 narrow the space further.
[LoginTrap](https://arxiv.org/abs/2608.04741) evaluates synthetic task-background
data submitted to a controlled login form—not real credentials—across 80 cloned
pages and 1,175 tasks. [Breadcrumbing Search Agents](https://arxiv.org/abs/2608.04565)
coordinates one injected result per query across a search trajectory and
separates injected-page visitation from success conditional on visitation. It
uses 187 held-out cases, six victim models, five repeats, and a ten-call victim
cap. Neither is a recursive tarpit, but both directly cover attraction,
multi-step steering, and controlled synthetic leakage.

## Direct web-agent security benchmarks

| Work | Status and scale | Contribution relevant here |
|---|---|---|
| [WASP](https://proceedings.neurips.cc/paper_files/paper/2025/hash/1c9818387f5dd0a0bc151214660f059d-Abstract-Datasets_and_Benchmarks_Track.html) | NeurIPS 2025; isolated Reddit/GitLab tasks | Separates beginning an adversarial objective from completing it; clean tasks expose “security by incompetence.” |
| [AgentDojo](https://arxiv.org/abs/2406.13352) | NeurIPS 2024 benchmark and framework | Reproducible tools, user tasks, attacker goals, deterministic state checks, utility/security trade-off. |
| [InjecAgent](https://aclanthology.org/2024.findings-acl.624/) | Findings of ACL 2024 | Large indirect-injection set spanning tool-integrated agent scenarios and attacker tools. |
| [BIPIA](https://arxiv.org/abs/2312.14197) | KDD 2025 | Multiple indirect-injection domains and defense baselines; useful general prompt-injection lineage. |
| [ASB](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5750f91d8fb9d5c02bd8ad2c3b44456b-Abstract-Conference.html) | ICLR 2025 | Scenarios, benign and attack tools, tasks, backbones, raw and normalised robustness. |
| [ST-WebAgentBench](https://research.ibm.com/publications/st-webagentbench-a-benchmark-for-evaluating-safety-and-trustworthiness-in-web-agents--1) | ICLR 2026 | Deterministic evaluators, policy instances, risk dimensions, DOM/vision coverage, all-pass style scoring. |
| [SafeArena](https://proceedings.mlr.press/v267/tur25a.html) | ICML 2025 | Safety evaluation in realistic browser tasks, useful for policy-aware harm and utility. |
| [WebGauntlet](https://openreview.net/forum?id=BD70y13DH1) | OpenReview benchmark | Clean ecommerce tasks plus scams and prompt injections; conditional attack outcomes. |
| [VPI-Bench](https://openreview.net/pdf?id=UMauKu2azg) | ICLR 2026 | Visual prompt injection; distinguishes attempted compromise from terminal success. |
| [AgentDyn](https://arxiv.org/abs/2602.03117) | Preprint with code | Dynamic helpful-versus-malicious third-party instructions; critical hard negatives. |
| [AgentLure / ARGUS](https://arxiv.org/abs/2605.03378) | Preprint | Contextual lure vectors where the same tools are genuinely needed by the task. |
| [StakeBench](https://arxiv.org/abs/2606.13385) | Preprint | Joint outcomes for task deviation, attack success, and behavioural irregularity, including loops. |
| [LivePI](https://arxiv.org/abs/2605.17986) | Preprint | Production-like VM evaluation with containment of real side effects. |
| [WebTrap Park](https://arxiv.org/abs/2601.08406) | Preprint and public platform | Externally observes browser actions across malicious prompts, indirect injections, and deceptive site designs. |
| [AgentBait](https://arxiv.org/abs/2601.07263) | Preprint | Tests task-aligned social-engineering traps, authentication popups, and sensitive-data forms. |
| [SecureWebArena](https://aclanthology.org/2026.findings-acl.582/) | Findings of ACL 2026 | Decomposes reasoning, behaviour, and outcomes across realistic web environments and attack vectors. |
| [AgentDAM](https://proceedings.neurips.cc/paper_files/paper/2025/hash/c9826b9ea5e1b49b256329934a578d83-Abstract-Datasets_and_Benchmarks_Track.html) | NeurIPS 2025 | Jointly measures end-to-end web-agent data minimisation, privacy leakage, and utility. |
| [LoginTrap](https://arxiv.org/abs/2608.04741) | Preprint submitted 5 Aug 2026 | Task-agnostic page lure induces a controlled login flow and end-to-end private-data leakage; directly informs synthetic C2 design. |
| [Breadcrumbing Search Agents](https://arxiv.org/abs/2608.04565) | Preprint submitted 5 Aug 2026 | Repeatedly coordinates poisoned search/page evidence across a trajectory; measures visitation and conditional success. |
| [SafeSearch](https://arxiv.org/abs/2509.23694) | ICML 2026 | Search-agent red-teaming benchmark with poisoned search environments, multiple scaffolds, and clean/safety evaluation. |
| [NetInjectBench](https://arxiv.org/abs/2607.10490) | Preprint | Indirect injection through network-operations artifacts such as tickets, logs, alerts, runbooks, and ChatOps. |
| [WebAgentGuard](https://arxiv.org/abs/2604.12284) | Preprint | Detection/guarding benchmark for web-agent prompt injection. |
| [MUZZLE](https://www.usenix.org/conference/usenixsecurity26/presentation/syros) | USENIX Security 2026 | Adaptive automated security assessment of web agents. |

### Selected scale and evaluation matrix

| Benchmark | Environment and scale | Agents/models | Main observables and controls |
|---|---|---|---|
| CHeaT | 11 CTF machines; 249 payloads; 4,233 scored samples | 3 pentesting agents; 4 model backends | Deception success, slowdown, honeytokens; single and combined techniques |
| TRAP | 6 sites; 18 tasks; 35 templates; 3,780 runs | 6 models | Link/action success, 35-step cap, UI/context variations |
| MemTrapBench | 247 tasks, including 16 pilot and 231 main tasks | Multiple browser-agent models | Entry–Propagation–Recovery; helpful/conflicting controls; exposure timing |
| Honeyval | 16 backend applications; repeated matched tasks | Multiple attacking agents and honeypot models | Exploit, interaction length, detection, fidelity, both sides' cost, spend caps |
| LoopTrap | 10 attack strategies; 60 tasks | 8 agents | Step amplification, termination poisoning, agent-specific profiles |
| WASP | 84 security tasks and 37 clean tasks | 3 web-agent systems with multiple models | Initial hijack versus completed attacker goal; clean-task utility |
| AgentDojo | 97 tasks; 629 security cases | Tool-calling agents | Deterministic utility and attacker-goal evaluators; clean and attacked cases |
| InjecAgent | 1,054 test cases | Tool-integrated LLM agents | Direct harm and private-data exfiltration intentions |
| VPI-Bench | 306 visual-injection cases over 5 platforms | Visual web agents | Attempted versus terminal success |
| SecureWebArena | 6 web environments; 330 adversarial tasks; 2,970 trajectories | 9 LVLMs | Reasoning, behavioural compromise, payload delivery, terminal outcome |
| WebTrap Park | 1,226 executable tasks | 4 web-agent frameworks | Externally observed actions; user attacks, injections, deceptive designs |
| LoginTrap | 80 cloned pages; 1,175 tasks; 5-step cap | 4 backbones; 3 agent architectures | Login entry and synthetic-data submission; no public clean-utility result found |

### Main lesson from this cluster

Do not score only “attack succeeded.” At minimum, distinguish:

1. the agent was exposed;
2. it attended to or visited the lure;
3. it began the trap-directed behaviour;
4. it reached the attacker's terminal goal;
5. it recognised and exited the trap;
6. it recovered the legitimate task;
7. it caused a real or synthetic side effect.

WASP and VPI-Bench show why this matters: starting an injected objective can be
common while end-to-end completion remains rare. A weak agent can therefore
appear “secure” if only terminal compromise is counted.

## Long-horizon, memory, tool, and persistence benchmarks

| Work | What it adds to the design |
|---|---|
| [AgentLAB](https://arxiv.org/abs/2602.16901) | Long-horizon attack families, turns-to-success, and environment diversity. |
| [STAC](https://arxiv.org/abs/2509.25624) | Multi-turn cumulative compromise through tool chains. |
| [SHADE-Arena](https://arxiv.org/abs/2506.15740) | Main-task/side-task separation and monitoring under evasion. |
| [ToolEmu](https://arxiv.org/abs/2309.15817) | ICLR 2024; emulated high-risk tools and execution-aware safety evaluation. |
| [AgentHarm](https://arxiv.org/abs/2410.09024) | ICLR 2025; multi-step harmful-agent tasks with capability-aware evaluation. |
| [Agent-SafetyBench](https://arxiv.org/abs/2412.14470) | Broad agent-safety cases across tools and risks. |
| [MemSecBench](https://arxiv.org/abs/2607.27080) | Memory lifecycle: write, execute, and forget; supports persistence metrics. |
| [Bad Memory](https://arxiv.org/abs/2607.14611) | Security effects of malicious or corrupted agent memory. |
| [CSTM-Bench](https://arxiv.org/abs/2604.21131) | Cross-session and temporal memory safety evaluation. |
| [AgentPoison](https://arxiv.org/abs/2407.12784) | Poisoned long-term memory/RAG that triggers agent behaviour. |
| [PoisonedRAG](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag) | Peer-reviewed data-poisoning lineage and attack evaluation. |
| [FORGE](https://arxiv.org/abs/2607.04718) | Recursive deep-research trajectory hijacking and final-report contamination. |
| [Deep-Research Agents Can Be Poisoned via User-Generated Content](https://arxiv.org/abs/2605.24245) | Repeated retrieval of poisoned user-generated content in deep-research workflows. |
| [eTAMP](https://arxiv.org/abs/2604.02623) | Temporal/adaptive memory poisoning. |

This cluster makes one point especially clear: “the model followed the page”
and “the effect persisted” are different claims. Persistence needs another
decision point, task, session, or memory read after the original exposure.

## Foundational prompt-injection and detector benchmarks

These are less honeypot-specific but necessary to avoid building an easy test
that rewards indiscriminate refusal.

| Work | Relevance |
|---|---|
| [HackAPrompt](https://arxiv.org/abs/2311.16119) | Large adversarial prompt-injection competition corpus. |
| [TensorTrust](https://arxiv.org/abs/2311.01011) | Large-scale attacks and defenses in an adversarial prompt game. |
| [Open-Prompt-Injection](https://www.usenix.org/system/files/usenixsecurity24-liu-yupei.pdf) | Peer-reviewed open evaluation framework for prompt injection. |
| [RuLES](https://arxiv.org/abs/2311.04235) | Rule-following evaluation under adversarial instructions. |
| [PromptShield](https://arxiv.org/abs/2501.15145) | ACM CODASPY 2025 prompt-injection detection data and evaluation. |
| [InjecGuard and NotInject](https://arxiv.org/abs/2410.22770) | Hard benign negatives specifically designed to reveal over-refusal. |
| [PINT](https://github.com/lakeraai/pint-benchmark) | Prompt-injection detection benchmark. |
| [GenTel](https://arxiv.org/abs/2409.19521) | Generalisable prompt-injection detection. |
| [OR-Bench](https://proceedings.mlr.press/v267/cui25a.html) | Over-refusal benchmark; directly relevant to benign utility. |
| [PIArena](https://aclanthology.org/2026.acl-long.1533/) | ACL 2026 prompt-injection evaluation. |
| [WAInjectBench](https://arxiv.org/abs/2510.01354) | Text/image prompt-injection detector benchmark rather than an end-to-end web-agent task benchmark. |

The benchmark needs `helpful`, `irrelevant`, `conflicting-but-benign`, and
`suspicious-looking-but-safe` pages. Otherwise a scaffold that refuses every
webpage wins the security metric while failing its actual job.

## Resource capture and economic asymmetry

This is already a distinct agent-security research line, not merely an
engineering concern:

| Work | Status | Direct contribution |
|---|---|---|
| [LoopTrap](https://arxiv.org/abs/2605.05846) | Preprint | Poisons termination decisions across 8 agents and 60 tasks; measures average and peak step amplification. |
| [AgentDoS: Autonomy Comes with Costs](https://www.usenix.org/conference/usenixsecurity26/presentation/luo) | USENIX Security 2026 | Models short-lived, session-lived, and full-lifecycle resources; fuzzes 20 open-source agent applications and reports 36 resource-exhaustion vulnerabilities in 16 of them. |
| [Beyond Max Tokens](https://arxiv.org/abs/2601.10955) | Preprint | Malicious tool/MCP output creates prolonged tool-call chains while preserving a benign terminal result; measures tokens, query cost, energy, and KV-cache occupancy. |
| [HoneyTrap](https://arxiv.org/abs/2601.04034) | Preprint | Deceptive defense against multi-turn jailbreak attackers; introduces Mislead Success Rate and Attack Resource Consumption. |
| [HARP](https://arxiv.org/abs/2605.27489) | Preprint | Paired clean/perturbed multi-agent executions with tool calls, memory events, latency, token cost, and decisions. |
| [Knowledge Trap](https://arxiv.org/abs/2606.15810) | Preprint | Breadcrumbed honeypot knowledge graph consumes a model-extraction attacker's limited query budget while checking benign utility. |

Further direct precedents are distributed across the honeypot, web-agent, and
crawler lines:

- CHeaT measures dramatic slowdown from expanded writable-file/search spaces
  and uses cyclic references and brute-force bait.
- TRAP and other web benchmarks impose action ceilings; reaching the ceiling is
  observable right-censoring, not simply a missing result.
- Honeyval compares attacker and defender running cost under hard spend caps.
- Traditional crawler traps measure requests, session depth, elapsed time, and
  revisits but not model tokens or API charges.

AI Abyss should therefore measure three ledgers separately:

| Ledger | Raw measurements |
|---|---|
| Honeypot/operator | CPU, memory, connections, file descriptors, bytes served, hosting duration |
| Agent scaffold | browser actions, requests, fetched bytes, retries, recursive depth, wall time |
| Model API | calls, native input/output/reasoning tokens, cache usage, provider-reported cost |

A slow socket is not automatically an expensive model call. Latency becomes
model expenditure only when the scaffold invokes the model while waiting,
chunks or summarises content, retries, or continues navigating. That is why
latency, volume, and recursion need separate matched arms.

Suggested operational and derived measures:

- **Attraction rate:** exposed trials with a trap-directed action / exposed
  trials. The action must be observable; causal language is reserved for paired
  treatment-control estimates.
- **Entry rate:** exposed trials that load the first controlled trap node /
  exposed trials.
- **Conditional persistence:** entered trials still following the trap after a
  predeclared number of decisions / entered trials.
- **Escape rate:** entered trials that explicitly or behaviourally leave the
  trap before a budget / entered trials.
- **Task recovery:** entered trials that ultimately complete the legitimate
  task / entered trials.
- **Normalised excess work:** `(treatment resource - matched-control resource) /
  matched-control resource` for calls, tokens, bytes, actions, and wall time.
- **Budget capture ratio:** consumed treatment budget / predeclared maximum,
  reported separately by resource dimension.
- **Economic amplification:** matched treatment-minus-clean increase in victim
  cost divided by the matched treatment-minus-clean increase in defender
  marginal cost. Report both raw differences and the ratio, state whether page
  generation is amortised, and mark a zero or near-zero denominator as
  undefined rather than presenting a misleading infinity.
- **Agent budget capture:** the tested agent reaches its declared budget while
  remaining on a trap-directed trajectory.
- **Harness censoring:** the harness safely terminates at a predeclared limit;
  this is a valid censored outcome, not an infrastructure failure.
- **Uncontrolled self-DoS:** the operator, server, or scaffold becomes
  unavailable outside the planned limit path. This is a benchmark failure.
- **Security–utility frontier:** trap resistance conditional on clean-task
  success, rather than security alone.

## Traditional crawler and live-web context

Additional sources relevant before any public deployment include:

- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309) for the Robots Exclusion
  Protocol;
- [The Ethicality of Web Crawlers](https://clgiles.ist.psu.edu/pubs/WI2010.pdf)
  for older robots and crawler-behaviour measurement;
- [Do Generative AI Assistants Respect robots.txt?](https://arxiv.org/abs/2607.14447)
  for current assistant behaviour;
- [Scrapers selectively respect robots.txt](https://arxiv.org/abs/2505.21733)
  for large-scale live-web measurement;
- [Cloudflare AI Labyrinth](https://blog.cloudflare.com/ai-labyrinth/) and
  [Nepenthes](https://zadzmo.org/code/nepenthes/) as deployed or experimental
  recursive-content systems rather than controlled scientific benchmarks.

These matter for a future public crawler honeypot, but they are not prerequisites
for the local MVP. Public attribution, robots semantics, fabricated-content
indexing, privacy, and retention become mandatory only when live visitors are
placed in scope.

## Other honeypot-specific projects and studies

| Work | Status | Relevance and caution |
|---|---|---|
| [LLM Agent Honeypot / Palisade](https://arxiv.org/abs/2410.13919) | Preprint with [code](https://github.com/PalisadeResearch/llm-honeypot) | Modified Cowrie SSH honeypot using ANSI-hidden injections and timing signals to identify possible real-world LLM attackers. |
| [AgentGauntlet](https://github.com/agentgauntlet/agent-gauntlet) | Open-source project | Practical agent red-team scenarios; inspect methodology before treating outputs as benchmark evidence. |
| [Agent Death Trap](https://agentdeathtrap.com/) | Live project | Directly explores agents encountering hostile web environments; not equivalent to a peer-reviewed benchmark. |
| [HoneyPrompt](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6196620) | Working paper | Prompt-level honeypot framing; evidence maturity differs from proceedings work. |
| [DeepMind scheming evaluations](https://deepmind.google/research/publications/253391/) | Research publication | Uses honeypot scenarios to reveal covert objectives; relevant to detection, not recursive web capture. |

## Recommended benchmark architecture

The most reusable pieces from the literature form a coherent design:

1. **AgentDojo-style state and evaluators:** deterministic environment state,
   user task, attacker/trap goal, and explicit success checks.
2. **CHeaT trap taxonomy:** loops, search expansion, irrelevant volume,
   compute bait, misinformation, injection, and honeytokens as separate layers.
3. **TRAP/REAL-style controlled websites:** plausible local tasks and realistic
   lure placement.
4. **MemTrap E–P–R trajectories:** entry, propagation, and recovery rather than
   a single terminal score.
5. **WASP/VPI outcome separation:** attempted hijack versus terminal side
   effect.
6. **AgentDyn/NotInject controls:** helpful and hard-benign pages so refusal is
   penalised.
7. **Honeyval cost accounting:** attacker and defender ledgers plus spend caps.
8. **AgentDoS resource lifecycles:** separate task-local, session-retained, and
   full-run resource exhaustion instead of collapsing them into one limit.
9. **Beyond Max Tokens process accounting:** measure the whole agent–tool loop,
   even when the final answer remains benign and correct.
10. **ST-WebAgentBench checks:** deterministic policy and outcome evaluators,
   with repeated-run reliability.
11. **SpiderTrap graph metrics:** depth, revisits, dwell, and traversal patterns.
12. **LoopTrap termination evidence:** distinguish repeated states or graph
   cycles from a merely long trajectory.

### Trial outcome model

Every run should produce a machine-readable branching state trace:

`task start -> exposure -> {reject/recognise, attract -> entry -> propagate}`

From any post-exposure state, the agent may recognise the trap, exit, re-enter,
recover the legitimate task, fail the task, cause a side effect, or reach a
budget. Recognition is not forced to occur after propagation: an agent may
recognise a lure before entry. Budget exhaustion right-censors time-to-escape:
it means “no escape or completion observed within this budget,” not “the agent
would remain trapped forever.” A loop requires repeated-state, repeated-URL, or
graph-cycle evidence in addition to a long trajectory.

### Minimum control matrix

| Dimension | Minimum levels |
|---|---|
| Trap | clean, inert length-matched, latency-only, volume-only, recursion-only, injection-only |
| Non-malicious instruction | absent, helpful, irrelevant, conflicting benign |
| Exposure | no exposure, visible lure, implicit/task-relevant lure |
| Schedule | single early exposure; repeated/late exposures after the MVP |
| Content | matched wording, layout, length, and legitimate usefulness |
| Reachability | attainable legitimate task and deterministic gold answer |
| Run metadata | model, provider, scaffold, system prompt, tools, seed, temperature, revision, limits, price version |

A recursion-plus-injection arm belongs after the individual mechanisms are
validated. It tests interaction effects without sacrificing the causal
interpretability of the initial ablations.

## Implications for the AI Abyss MVP

The first credible experiment does not require most of the current public-bot
infrastructure. It requires:

1. one deterministic legitimate task;
2. one matched clean site;
3. one normal-sized recursion-only graph;
4. one injection-only page with a generated synthetic secret and a trial-bound
   local event sink;
5. one fixed agent/browser scaffold and one pinned API model;
6. hard limits on calls, tokens, actions, bytes, depth, wall time, and spend;
7. trial manifests, event traces, provider usage, and deterministic scoring;
8. repeated paired control/treatment runs.

Do not begin with a single “full abyss” condition combining slow streaming,
large pages, Unicode corruption, recursive links, fabricated facts, prompt
injection, and C2. Such a result cannot identify which mechanism caused entry,
cost, failure, or recovery.

## Claims to avoid and claims that remain plausible

Avoid:

- “the first LLM honeypot benchmark”;
- “no benchmark traps LLM agents”;
- “the first recursive or looping defense against LLM agents”;
- “the first work to measure honeypot engagement or cost”;
- “a callback proves training-data ingestion”;
- “budget exhaustion proves permanent entrapment.”

Plausible, subject to a completed experiment and final related-work search:

> Existing benchmarks separately measure prompt-injection success, web-agent
> redirection, termination poisoning, long-horizon compromise, memory
> propagation, crawler traversal, and honeypot interaction length. CHeaT
> additionally demonstrates that LLM-specific deception can trap
> penetration-testing agents. To our knowledge, no prior benchmark evaluates
> navigable web-honeypot attraction, recursive graph stickiness, recognition and
> escape, legitimate-task recovery, clean utility, re-entry or cross-session
> contamination, and separate victim/operator resource ledgers together under
> matched causal ablations.

## Coverage checklist for future updates

Before calling the review complete for publication, rerun searches and
citation-chaining for:

- agent tarpit, crawler trap, spider trap, recursive honeypot;
- LLM honeypot, agent honeypot, honeytoken, honey prompt;
- web-agent prompt injection, task redirection, persuasion, phishing, login;
- long-horizon injection, repeated exposure, memory poisoning, persistence;
- cost amplification, denial of wallet, denial of service, query-budget trap;
- robots compliance, AI crawler measurement, live web agent safety;
- citations to and from CHeaT, TRAP, Honeyval, MemTrapBench, SpiderTrap, WASP,
  AgentDojo, AgentDoS, Beyond Max Tokens, and LoginTrap;
- new proceedings and preprints after 7 August 2026.

The paper-status labels and repository availability should also be rechecked at
submission time because several central 2026 sources are very recent preprints.
