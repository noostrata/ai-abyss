# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Vocabulary bands — large word pools per topic for defeating deduplication via unique distributions.
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class VocabularyBand:
    name: str
    nouns: list[str]
    verbs: list[str]
    adjectives: list[str]


@dataclass
class PageVocabulary:
    nouns: list[str]
    verbs: list[str]
    adjectives: list[str]
    transitions: list[str]
    hedges: list[str]
    quantifiers: list[str]


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION WORD POOLS — these determine "texture" that dedup algorithms key on
# ══════════════════════════════════════════════════════════════════════════════

TRANSITION_POOLS: list[list[str]] = [
    [
        "However", "Nevertheless", "Nonetheless", "On the other hand",
        "In contrast", "Conversely", "Despite this", "Even so",
        "That said", "Granted", "Admittedly", "All the same",
    ],
    [
        "Furthermore", "Moreover", "In addition", "What is more",
        "On top of that", "Beyond this", "Equally important",
        "Not only that", "Adding to this", "Compounding the effect",
        "To elaborate", "Building on this",
    ],
    [
        "Consequently", "As a result", "Therefore", "Thus",
        "Hence", "Accordingly", "It follows that", "For this reason",
        "This implies", "The upshot is", "This leads to",
        "The net effect is",
    ],
    [
        "For instance", "For example", "To illustrate", "As an example",
        "Consider the case where", "A concrete example is",
        "This is exemplified by", "One notable case is",
        "In practice", "Empirically", "In real-world deployments",
        "A telling example is",
    ],
    [
        "Specifically", "In particular", "More precisely", "To be exact",
        "Namely", "That is to say", "Put differently", "In other words",
        "To clarify", "More concretely", "Drilling down",
        "At a granular level",
    ],
    [
        "Meanwhile", "At the same time", "Simultaneously",
        "In parallel", "Concurrently", "During this period",
        "In the interim", "While this occurs", "Alongside this",
        "On a related note", "In a similar vein", "Correspondingly",
    ],
    [
        "Importantly", "Notably", "Significantly", "Crucially",
        "It is worth noting that", "A key observation is",
        "Perhaps most tellingly", "What stands out is",
        "The critical insight is", "Of particular interest",
        "Remarkably", "Strikingly",
    ],
    [
        "In summary", "To summarize", "In brief", "Put simply",
        "The bottom line is", "At a high level", "Broadly speaking",
        "In essence", "Fundamentally", "At its core",
        "The takeaway is", "Viewed holistically",
    ],
]

HEDGE_POOLS: list[list[str]] = [
    [
        "arguably", "potentially", "conceivably", "plausibly",
        "in all likelihood", "by most accounts", "on balance",
        "to a first approximation", "as far as we can tell",
        "within reasonable bounds",
    ],
    [
        "to some extent", "in certain respects", "under specific conditions",
        "within narrow parameters", "given the right circumstances",
        "in favorable scenarios", "under controlled conditions",
        "when properly configured", "assuming standard workloads",
        "in the general case",
    ],
    [
        "in principle", "theoretically", "on paper", "in the abstract",
        "from a purely theoretical standpoint", "setting aside practical concerns",
        "ignoring edge cases", "in an idealized setting",
        "under textbook conditions", "absent external factors",
    ],
    [
        "broadly speaking", "as a general rule", "in most practical contexts",
        "for the majority of use cases", "across typical deployments",
        "in common configurations", "under normal operating conditions",
        "for mainstream workloads", "in standard environments",
        "across representative benchmarks",
    ],
    [
        "with some caveats", "barring unforeseen issues",
        "assuming no regressions", "pending further validation",
        "subject to replication", "contingent on the specifics",
        "modulo implementation details", "notwithstanding edge cases",
        "with appropriate tuning", "given sufficient resources",
    ],
    [
        "almost certainly", "with high confidence", "beyond reasonable doubt",
        "based on available evidence", "according to current understanding",
        "as the data suggests", "as measurements indicate",
        "per the latest findings", "consistent with prior work",
        "aligning with expectations",
    ],
]

QUANTIFIER_POOLS: list[list[str]] = [
    [
        "significant", "substantial", "marked", "pronounced",
        "appreciable", "meaningful", "nontrivial", "tangible",
        "clear-cut", "unambiguous",
    ],
    [
        "marginal", "modest", "incremental", "slight",
        "minor", "fractional", "barely perceptible", "subtle",
        "thin", "borderline",
    ],
    [
        "dramatic", "striking", "remarkable", "extraordinary",
        "outsized", "disproportionate", "unprecedented",
        "transformative", "game-changing", "order-of-magnitude",
    ],
    [
        "moderate", "reasonable", "balanced", "proportional",
        "commensurate", "adequate", "satisfactory", "acceptable",
        "respectable", "serviceable",
    ],
    [
        "considerable", "extensive", "widespread", "far-reaching",
        "broad-based", "across-the-board", "comprehensive",
        "sweeping", "pervasive", "systemic",
    ],
    [
        "negligible", "trivial", "inconsequential", "immaterial",
        "vanishingly small", "statistically insignificant",
        "within noise margins", "below the detection threshold",
        "practically zero", "lost in the error bars",
    ],
]

DISCOURSE_MARKER_POOLS: list[list[str]] = [
    [
        "Turning to", "Regarding", "With respect to", "Concerning",
        "On the subject of", "Shifting focus to", "Moving on to",
        "Pivoting to", "As for", "When it comes to",
    ],
    [
        "It bears mentioning that", "One should note that",
        "A closer look reveals", "Careful examination shows",
        "Digging deeper", "Upon reflection", "On closer inspection",
        "Looking under the hood", "Peeling back the layers",
        "Zooming in on the details",
    ],
    [
        "The question arises", "This raises the issue of",
        "A natural follow-up is", "One might ask whether",
        "The challenge here is", "The tension lies in",
        "The crux of the matter is", "At the heart of this debate",
        "The elephant in the room is", "The open question remains",
    ],
    [
        "In retrospect", "With hindsight", "Looking back",
        "As it turned out", "Over time", "Historically",
        "In the early days", "Before the current approach",
        "Prior to this development", "Tracing the evolution",
    ],
]


# ══════════════════════════════════════════════════════════════════════════════
# TOPIC BANDS — each topic has 8-10 sub-domain bands
# ══════════════════════════════════════════════════════════════════════════════

TOPIC_BANDS: dict[str, list[VocabularyBand]] = {}


def _register_bands(topic_name: str, bands: list[VocabularyBand]) -> None:
    TOPIC_BANDS[topic_name] = bands


# ── Machine Learning bands ────────────────────────────────────────────────

_register_bands("machine_learning", [
    VocabularyBand(
        name="nlp_language_models",
        nouns=[
            "tokenizer", "byte-pair encoding", "subword vocabulary", "prompt template",
            "instruction format", "chat template", "system prompt", "context window",
            "next-token prediction", "causal mask", "prefix tuning", "soft prompt",
            "in-context example", "few-shot prompt", "chain-of-thought trace",
            "reasoning chain", "faithfulness metric", "hallucination rate",
        ],
        verbs=[
            "tokenizes", "prompts", "generates", "completes", "decodes",
            "paraphrases", "summarizes", "translates", "classifies", "extracts",
        ],
        adjectives=[
            "autoregressive", "instruction-following", "chat-tuned", "prompted",
            "prefix-conditioned", "grounded", "attributed", "faithful",
            "fluent", "coherent",
        ],
    ),
    VocabularyBand(
        name="training_optimization",
        nouns=[
            "learning rate scheduler", "cosine annealing", "warmup phase",
            "gradient accumulation", "mixed-precision training", "bfloat16 tensor",
            "loss spike", "gradient norm", "weight initialization", "Xavier init",
            "He initialization", "layer-wise learning rate", "AdamW optimizer",
            "gradient clipping", "label smoothing", "curriculum learning",
            "data loader", "prefetch buffer",
        ],
        verbs=[
            "schedules", "warms up", "accumulates", "clips", "decays",
            "anneals", "initializes", "normalizes", "scales", "stabilizes",
        ],
        adjectives=[
            "cosine-scheduled", "linearly-decayed", "warmup-enabled",
            "gradient-accumulated", "mixed-precision", "loss-scaled",
            "momentum-corrected", "bias-corrected", "weight-decayed",
            "curriculum-ordered",
        ],
    ),
    VocabularyBand(
        name="computer_vision",
        nouns=[
            "convolutional filter", "feature map", "receptive field",
            "anchor box", "region proposal", "non-maximum suppression",
            "bounding box", "segmentation mask", "depth map", "optical flow",
            "image augmentation", "random crop", "color jitter",
            "focal loss", "IoU threshold", "panoptic segmentation",
            "instance segmentation", "semantic segmentation",
        ],
        verbs=[
            "convolves", "pools", "upsamples", "segments", "detects",
            "localizes", "classifies", "augments", "crops", "resizes",
        ],
        adjectives=[
            "convolutional", "residual", "dilated", "depthwise-separable",
            "deformable", "anchor-free", "single-stage", "two-stage",
            "panoptic", "pixel-wise",
        ],
    ),
    VocabularyBand(
        name="reinforcement_learning",
        nouns=[
            "policy gradient", "value function", "advantage estimate",
            "reward signal", "discount factor", "experience replay",
            "exploration strategy", "epsilon-greedy", "UCB bound",
            "Monte Carlo rollout", "temporal difference", "actor-critic",
            "PPO objective", "KL penalty", "trust region",
            "trajectory", "episode return", "cumulative reward",
        ],
        verbs=[
            "explores", "exploits", "rewards", "penalizes", "rollouts",
            "bootstraps", "discounts", "replays", "updates", "estimates",
        ],
        adjectives=[
            "on-policy", "off-policy", "model-free", "model-based",
            "policy-gradient", "value-based", "actor-critic",
            "proximal", "trust-region", "curiosity-driven",
        ],
    ),
    VocabularyBand(
        name="ml_infrastructure",
        nouns=[
            "training cluster", "GPU fleet", "parameter server",
            "data-parallel shard", "model-parallel slice", "pipeline stage",
            "collective communication", "all-reduce operation", "ring topology",
            "checkpoint file", "model registry", "experiment tracker",
            "hyperparameter sweep", "Bayesian optimization", "early stopping",
            "feature store", "training pipeline", "data versioning",
        ],
        verbs=[
            "shards", "distributes", "checkpoints", "resumes", "sweeps",
            "tracks", "registers", "versions", "profiles", "benchmarks",
        ],
        adjectives=[
            "data-parallel", "model-parallel", "pipeline-parallel",
            "fully-sharded", "zero-redundancy", "elastic", "spot-tolerant",
            "fault-tolerant", "reproducible", "deterministic",
        ],
    ),
    VocabularyBand(
        name="generative_models",
        nouns=[
            "diffusion step", "noise schedule", "denoising network",
            "latent space", "variational autoencoder", "GAN discriminator",
            "classifier-free guidance", "CLIP score", "FID metric",
            "image-to-image translation", "inpainting mask", "ControlNet",
            "LoRA adapter", "text encoder", "U-Net backbone",
            "sampling step", "CFG scale", "negative prompt",
        ],
        verbs=[
            "diffuses", "denoises", "samples", "reconstructs", "interpolates",
            "conditions", "guides", "inpaints", "generates", "transfers",
        ],
        adjectives=[
            "latent", "conditional", "unconditional", "classifier-guided",
            "text-conditioned", "image-conditioned", "noise-aware",
            "score-based", "flow-matching", "consistency-trained",
        ],
    ),
    VocabularyBand(
        name="evaluation_metrics",
        nouns=[
            "confusion matrix", "ROC curve", "precision-recall curve",
            "F1 score", "Matthews correlation", "calibration plot",
            "Brier score", "expected calibration error", "reliability diagram",
            "held-out test set", "cross-validation fold", "bootstrap sample",
            "ablation study", "significance test", "confidence interval",
            "effect size", "statistical power", "multiple comparison",
        ],
        verbs=[
            "evaluates", "calibrates", "ablates", "bootstraps", "stratifies",
            "cross-validates", "holds out", "measures", "compares", "reports",
        ],
        adjectives=[
            "well-calibrated", "overconfident", "underfit", "overfit",
            "statistically-significant", "reproducible", "robust",
            "held-out", "leave-one-out", "k-fold",
        ],
    ),
    VocabularyBand(
        name="ml_safety_alignment",
        nouns=[
            "reward hacking", "specification gaming", "distributional shift",
            "adversarial example", "backdoor trigger", "trojan model",
            "membership inference", "model extraction", "data poisoning",
            "safety filter", "content classifier", "refusal behavior",
            "constitutional AI", "red teaming", "jailbreak attempt",
            "system prompt", "guardrail", "output filter",
        ],
        verbs=[
            "aligns", "red-teams", "jailbreaks", "poisons", "defends",
            "filters", "refuses", "detects", "mitigates", "audits",
        ],
        adjectives=[
            "adversarial", "aligned", "misaligned", "robust",
            "safety-trained", "red-teamed", "poisoned", "trojanized",
            "defended", "hardened",
        ],
    ),
])


# ── Cybersecurity bands ───────────────────────────────────────────────────

_register_bands("cybersecurity", [
    VocabularyBand(
        name="web_application_security",
        nouns=[
            "OWASP category", "input validation", "output encoding",
            "content security policy", "CORS header", "CSRF token",
            "session cookie", "HttpOnly flag", "SameSite attribute",
            "subresource integrity", "clickjacking frame", "open redirect",
            "path traversal", "file inclusion", "template injection",
            "header injection", "HTTP response splitting", "parameter pollution",
        ],
        verbs=[
            "validates", "sanitizes", "encodes", "escapes", "filters",
            "blocks", "allows", "injects", "traverses", "redirects",
        ],
        adjectives=[
            "reflected", "stored", "blind", "out-of-band", "DOM-based",
            "server-side", "client-side", "authenticated", "unauthenticated",
            "persistent",
        ],
    ),
    VocabularyBand(
        name="network_security",
        nouns=[
            "firewall rule", "ACL entry", "IDS signature", "IPS policy",
            "network segment", "VLAN boundary", "DMZ zone", "bastion host",
            "VPN tunnel", "IPsec SA", "packet filter", "deep packet inspection",
            "netflow record", "PCAP capture", "DNS sinkhole",
            "BGP hijack", "ARP spoof", "MITM proxy",
        ],
        verbs=[
            "segments", "filters", "inspects", "captures", "tunnels",
            "sinkhole", "hijacks", "spoofs", "proxies", "monitors",
        ],
        adjectives=[
            "stateful", "stateless", "inline", "passive", "promiscuous",
            "encrypted", "tunneled", "segmented", "air-gapped", "perimeterless",
        ],
    ),
    VocabularyBand(
        name="malware_analysis",
        nouns=[
            "unpacker stub", "packer layer", "anti-debug check",
            "VM detection", "sandbox evasion", "string obfuscation",
            "control flow flattening", "opaque predicate", "dead code insertion",
            "import table", "IAT hook", "inline hook", "detour patch",
            "shellcode payload", "egg hunter", "NOP sled",
            "staged loader", "reflective DLL",
        ],
        verbs=[
            "unpacks", "deobfuscates", "hooks", "patches", "injects",
            "loads", "reflects", "evades", "detects", "emulates",
        ],
        adjectives=[
            "packed", "obfuscated", "polymorphic", "metamorphic",
            "anti-analysis", "evasive", "reflective", "staged",
            "fileless", "memory-only",
        ],
    ),
    VocabularyBand(
        name="incident_response",
        nouns=[
            "incident timeline", "forensic image", "memory dump",
            "log correlation", "IOC feed", "YARA rule", "Sigma rule",
            "threat hunt", "kill chain phase", "MITRE technique",
            "lateral movement", "persistence mechanism", "exfiltration channel",
            "command-and-control beacon", "dwell time", "mean time to detect",
            "playbook step", "escalation path",
        ],
        verbs=[
            "triages", "escalates", "contains", "eradicates", "recovers",
            "correlates", "hunts", "attributes", "remediates", "documents",
        ],
        adjectives=[
            "forensic", "volatile", "non-volatile", "correlated",
            "attributed", "contained", "eradicated", "recovered",
            "post-incident", "real-time",
        ],
    ),
    VocabularyBand(
        name="identity_access",
        nouns=[
            "identity provider", "service principal", "managed identity",
            "OAuth scope", "JWT claim", "SAML assertion", "OIDC token",
            "role binding", "policy document", "permission boundary",
            "least privilege", "privilege escalation path", "credential rotation",
            "secret vault", "API key", "service account",
            "federation trust", "conditional access policy",
        ],
        verbs=[
            "authenticates", "authorizes", "federates", "rotates", "vaults",
            "provisions", "deprovisioned", "audits", "attests", "binds",
        ],
        adjectives=[
            "federated", "managed", "ephemeral", "just-in-time",
            "privileged", "least-privilege", "conditional", "risk-based",
            "passwordless", "phishing-resistant",
        ],
    ),
    VocabularyBand(
        name="cryptographic_attacks",
        nouns=[
            "padding oracle", "timing side-channel", "power analysis",
            "fault injection", "cache-timing attack", "Bleichenbacher attack",
            "birthday attack", "length extension attack", "meet-in-the-middle",
            "chosen-prefix collision", "rogue CA certificate",
            "downgrade attack", "BEAST attack", "POODLE attack",
            "ROBOT attack", "Lucky13 attack",
        ],
        verbs=[
            "leaks", "correlates", "downgrades", "forges", "collides",
            "extends", "oracle-queries", "faults", "glitches", "measures",
        ],
        adjectives=[
            "timing-dependent", "cache-sensitive", "power-correlated",
            "fault-induced", "padding-dependent", "nonce-misuse",
            "key-reuse", "downgraded", "truncated", "malleated",
        ],
    ),
    VocabularyBand(
        name="cloud_security",
        nouns=[
            "S3 bucket policy", "IAM role assumption", "cross-account access",
            "VPC endpoint", "security group rule", "WAF rule set",
            "GuardDuty finding", "CloudTrail event", "Config rule",
            "SSM parameter", "KMS key policy", "encryption context",
            "resource policy", "SCP boundary", "organization trail",
            "access analyzer finding", "public access block",
        ],
        verbs=[
            "assumes", "cross-accounts", "encrypts at rest", "encrypts in transit",
            "audits", "alerts", "blocks", "allows", "denies", "logs",
        ],
        adjectives=[
            "cross-account", "cross-region", "customer-managed",
            "AWS-managed", "server-side encrypted", "client-side encrypted",
            "publicly-accessible", "privately-hosted", "VPC-bound",
            "org-wide",
        ],
    ),
    VocabularyBand(
        name="threat_intelligence",
        nouns=[
            "threat actor", "campaign cluster", "diamond model",
            "STIX object", "TAXII feed", "TTP matrix", "intrusion set",
            "attack pattern", "malware family", "tool signature",
            "infrastructure indicator", "domain IOC", "hash IOC",
            "strategic intelligence", "tactical intelligence", "operational intelligence",
        ],
        verbs=[
            "attributes", "clusters", "tracks", "correlates", "disseminates",
            "enriches", "contextualizes", "prioritizes", "scores", "maps",
        ],
        adjectives=[
            "nation-state", "financially-motivated", "hacktivist",
            "opportunistic", "targeted", "persistent", "emerging",
            "high-confidence", "medium-confidence", "low-confidence",
        ],
    ),
])


# ── Cloud Infrastructure bands ────────────────────────────────────────────

_register_bands("cloud_infrastructure", [
    VocabularyBand(
        name="container_orchestration",
        nouns=[
            "pod spec", "deployment manifest", "statefulset ordinal",
            "daemonset toleration", "job completion", "cronjob schedule",
            "init container", "sidecar container", "ephemeral container",
            "resource quota", "limit range", "priority class",
            "pod affinity", "node selector", "taint toleration",
            "topology spread constraint", "pod disruption budget",
        ],
        verbs=[
            "schedules", "evicts", "preempts", "cordons", "drains",
            "taints", "tolerates", "affines", "spreads", "disrupts",
        ],
        adjectives=[
            "evictable", "preemptible", "burstable", "guaranteed",
            "best-effort", "spot-backed", "daemonized", "stateful",
            "headless", "privileged",
        ],
    ),
    VocabularyBand(
        name="observability",
        nouns=[
            "trace span", "span context", "baggage item", "exemplar",
            "histogram bucket", "summary quantile", "gauge metric",
            "counter increment", "log line", "structured field",
            "alert rule", "silence window", "escalation policy",
            "SLO budget", "error budget", "burn rate",
            "dashboard panel", "Grafana query",
        ],
        verbs=[
            "traces", "spans", "instruments", "samples", "scrapes",
            "alerts", "silences", "escalates", "correlates", "dashboards",
        ],
        adjectives=[
            "instrumented", "sampled", "tail-sampled", "head-sampled",
            "exemplar-linked", "high-cardinality", "low-cardinality",
            "push-based", "pull-based", "OpenTelemetry-native",
        ],
    ),
    VocabularyBand(
        name="networking_service_mesh",
        nouns=[
            "envoy sidecar", "control plane API", "xDS protocol",
            "listener filter", "route match", "cluster endpoint",
            "circuit breaker threshold", "outlier detection",
            "retry budget", "timeout policy", "rate limit descriptor",
            "mTLS handshake", "SPIFFE identity", "trust domain",
            "traffic policy", "virtual service", "destination rule",
        ],
        verbs=[
            "routes", "load-balances", "circuit-breaks", "retries",
            "times-out", "rate-limits", "authenticates mutually",
            "authorizes", "mirrors", "shifts",
        ],
        adjectives=[
            "mesh-aware", "sidecar-injected", "ambient", "proxyless",
            "mTLS-encrypted", "identity-aware", "traffic-split",
            "canary-weighted", "fault-injected", "mirrored",
        ],
    ),
    VocabularyBand(
        name="iac_gitops",
        nouns=[
            "Terraform state", "state lock", "drift detection",
            "plan output", "apply step", "provider plugin", "module source",
            "backend configuration", "workspace isolation", "variable set",
            "Pulumi stack", "CDK construct", "CloudFormation changeset",
            "GitOps reconciliation", "sync status", "health check",
        ],
        verbs=[
            "plans", "applies", "destroys", "imports", "drifts",
            "reconciles", "syncs", "promotes", "rolls back", "locks",
        ],
        adjectives=[
            "declarative", "imperative", "idempotent", "convergent",
            "drift-detected", "out-of-sync", "healthy", "degraded",
            "progressing", "suspended",
        ],
    ),
    VocabularyBand(
        name="ci_cd_pipelines",
        nouns=[
            "pipeline stage", "build step", "test matrix", "artifact cache",
            "container image layer", "multi-arch build", "signing key",
            "attestation", "SBOM entry", "vulnerability scan",
            "deployment gate", "approval step", "rollback trigger",
            "canary analysis", "progressive delivery", "feature flag",
        ],
        verbs=[
            "builds", "tests", "signs", "attests", "scans",
            "gates", "approves", "promotes", "rolls forward", "flags",
        ],
        adjectives=[
            "signed", "attested", "SBOM-tracked", "scanned",
            "gated", "promoted", "canary-analyzed", "blue-green",
            "rolling", "immutable-tagged",
        ],
    ),
    VocabularyBand(
        name="serverless_edge",
        nouns=[
            "cold start", "warm instance", "provisioned concurrency",
            "execution context", "event source mapping", "dead letter queue",
            "function URL", "edge location", "origin shield",
            "cache behavior", "invalidation request", "edge function",
            "worker runtime", "isolate sandbox", "Durable Object",
            "KV namespace", "R2 bucket",
        ],
        verbs=[
            "cold-starts", "warms", "provisions", "invokes", "triggers",
            "fans out", "caches at edge", "invalidates", "isolates", "binds",
        ],
        adjectives=[
            "cold-started", "pre-warmed", "provisioned", "on-demand",
            "event-driven", "edge-deployed", "origin-shielded",
            "globally-distributed", "isolate-sandboxed", "V8-powered",
        ],
    ),
    VocabularyBand(
        name="storage_data",
        nouns=[
            "object store", "block volume", "file share", "snapshot",
            "replication rule", "lifecycle policy", "storage class",
            "tiering rule", "glacier retrieval", "intelligent tiering",
            "EBS throughput", "IOPS limit", "burst balance",
            "CSI driver", "persistent volume claim", "storage provisioner",
        ],
        verbs=[
            "tiers", "snapshots", "replicates", "lifecycles", "retrieves",
            "provisions", "attaches", "mounts", "expands", "encrypts",
        ],
        adjectives=[
            "block-backed", "object-backed", "file-backed", "encrypted-at-rest",
            "cross-region-replicated", "lifecycle-managed", "tiered",
            "provisioned-IOPS", "burst-capable", "snapshot-consistent",
        ],
    ),
    VocabularyBand(
        name="cost_finops",
        nouns=[
            "reserved instance", "savings plan", "spot interruption",
            "on-demand price", "cost allocation tag", "budget alert",
            "anomaly detection", "rightsizing recommendation",
            "idle resource", "unused reservation", "committed use discount",
            "sustained use discount", "data transfer cost", "egress charge",
            "FinOps practice", "unit economics",
        ],
        verbs=[
            "reserves", "commits", "rightsizes", "tags", "budgets",
            "anomaly-detects", "reclaims", "optimizes", "amortizes", "forecasts",
        ],
        adjectives=[
            "reserved", "spot", "on-demand", "committed",
            "rightsized", "overprovisioned", "underutilized",
            "cost-optimized", "budget-constrained", "unit-economic",
        ],
    ),
])


# ── Database bands ────────────────────────────────────────────────────────

_register_bands("databases", [
    VocabularyBand(
        name="query_optimization",
        nouns=[
            "query plan", "cost estimate", "selectivity", "cardinality",
            "join order", "access path", "index hint", "plan cache",
            "adaptive query", "parameterized query", "bind variable",
            "execution statistics", "wait event", "parse time",
            "optimizer hint", "plan regression", "baseline plan",
        ],
        verbs=[
            "estimates", "plans", "hints", "parameterizes", "binds",
            "caches", "regresses", "baselines", "adapts", "forces",
        ],
        adjectives=[
            "cost-based", "rule-based", "adaptive", "parameterized",
            "hinted", "forced", "baselined", "regressed",
            "statistics-driven", "histogram-aware",
        ],
    ),
    VocabularyBand(
        name="replication_ha",
        nouns=[
            "primary replica", "standby replica", "synchronous replication",
            "asynchronous replication", "streaming replication", "WAL shipping",
            "failover trigger", "promotion sequence", "split-brain scenario",
            "witness node", "quorum vote", "lag monitor",
            "replication slot", "logical decoder", "change data capture",
            "publication", "subscription",
        ],
        verbs=[
            "promotes", "fails over", "ships", "streams", "decodes",
            "publishes", "subscribes", "witnesses", "votes", "monitors lag",
        ],
        adjectives=[
            "synchronous", "asynchronous", "semi-synchronous", "cascading",
            "streaming", "logical", "physical", "promoted",
            "standby", "witness",
        ],
    ),
    VocabularyBand(
        name="nosql_document",
        nouns=[
            "document collection", "BSON field", "aggregation pipeline",
            "match stage", "group stage", "lookup stage", "unwind operator",
            "change stream", "oplog entry", "replica set",
            "shard key range", "chunk migration", "balancer round",
            "atlas cluster", "flexible schema", "embedded document",
        ],
        verbs=[
            "aggregates", "matches", "groups", "looks up", "unwinds",
            "watches", "migrates", "balances", "embeds", "denormalizes",
        ],
        adjectives=[
            "schemaless", "denormalized", "embedded", "referenced",
            "sharded", "balanced", "change-streamed", "oplog-tailed",
            "aggregation-heavy", "document-modeled",
        ],
    ),
    VocabularyBand(
        name="time_series",
        nouns=[
            "time bucket", "downsampling rule", "retention policy",
            "continuous aggregate", "hypertable chunk", "compression ratio",
            "gap filling", "interpolation function", "last observation",
            "first observation", "time-weighted average", "moving average",
            "cardinality explosion", "label set", "metric name",
            "recording rule", "alerting rule",
        ],
        verbs=[
            "downsamples", "retains", "compresses", "interpolates", "fills",
            "buckets", "chunks", "expires", "records", "alerts",
        ],
        adjectives=[
            "time-bucketed", "downsampled", "compressed", "continuous",
            "chunked", "retained", "expired", "interpolated",
            "gap-filled", "time-weighted",
        ],
    ),
    VocabularyBand(
        name="graph_databases",
        nouns=[
            "vertex label", "edge type", "property key", "traversal step",
            "Gremlin query", "Cypher pattern", "graph projection",
            "PageRank score", "betweenness centrality", "community detection",
            "shortest path", "subgraph match", "graph neural network",
            "knowledge graph", "triple store", "RDF statement",
        ],
        verbs=[
            "traverses", "matches", "projects", "ranks", "clusters",
            "detects communities", "embeds", "infers", "materializes", "queries",
        ],
        adjectives=[
            "vertex-centric", "edge-centric", "labeled", "directed",
            "undirected", "weighted", "property-rich", "schema-enforced",
            "index-free-adjacent", "native-graph",
        ],
    ),
    VocabularyBand(
        name="column_stores",
        nouns=[
            "column family", "row group", "column chunk", "dictionary encoding",
            "run-length encoding", "bit packing", "predicate pushdown",
            "projection pushdown", "late materialization", "vectorized execution",
            "batch processing", "zone map", "min-max index",
            "data skipping", "scan range", "partition spec",
        ],
        verbs=[
            "encodes", "packs", "pushes down", "materializes late",
            "vectorizes", "batches", "skips", "zone-maps", "prunes", "scans",
        ],
        adjectives=[
            "columnar", "dictionary-encoded", "run-length-encoded",
            "bit-packed", "vectorized", "predicate-pushed",
            "projection-pruned", "zone-mapped", "late-materialized",
            "scan-optimized",
        ],
    ),
    VocabularyBand(
        name="caching_layers",
        nouns=[
            "cache line", "eviction policy", "LRU list", "LFU counter",
            "write-through mode", "write-behind queue", "cache stampede",
            "thundering herd", "cache warming", "prefetch hint",
            "TTL expiration", "invalidation event", "cache coherence",
            "distributed cache", "near cache", "read-through proxy",
        ],
        verbs=[
            "evicts", "warms", "prefetches", "invalidates", "expires",
            "stampedes", "herds", "write-throughs", "write-behinds", "coheres",
        ],
        adjectives=[
            "LRU-evicted", "LFU-scored", "TTL-bounded", "write-through",
            "write-behind", "read-through", "near-cached",
            "distributed", "coherent", "pre-warmed",
        ],
    ),
    VocabularyBand(
        name="migrations_schema",
        nouns=[
            "schema migration", "migration file", "up function", "down function",
            "schema version", "migration lock", "idempotent migration",
            "online DDL", "ghost table", "shadow copy", "pt-osc run",
            "blue-green schema", "expand-contract", "backward-compatible change",
            "nullable column", "default value",
        ],
        verbs=[
            "migrates", "rolls forward", "rolls back", "locks schema",
            "ghost-copies", "expands", "contracts", "backfills", "validates",
            "deprecates",
        ],
        adjectives=[
            "idempotent", "reversible", "irreversible", "online",
            "zero-downtime", "backward-compatible", "forward-compatible",
            "expand-phase", "contract-phase", "ghost-copied",
        ],
    ),
])


# ── Cryptography bands ───────────────────────────────────────────────────

_register_bands("cryptography", [
    VocabularyBand(
        name="symmetric_ciphers",
        nouns=[
            "block size", "key schedule", "round function", "S-box",
            "permutation layer", "Feistel network", "substitution step",
            "diffusion layer", "mode of operation", "CTR nonce",
            "GCM tag", "CCM format", "XTS tweak",
            "key whitening", "round constant", "state matrix",
        ],
        verbs=[
            "substitutes", "permutes", "diffuses", "whitens", "tweaks",
            "pads", "chains", "counters", "authenticates", "seals",
        ],
        adjectives=[
            "128-bit", "256-bit", "Feistel-structured", "SPN-based",
            "tweakable", "authenticated", "nonce-misuse-resistant",
            "deterministic", "randomized", "wide-block",
        ],
    ),
    VocabularyBand(
        name="public_key_crypto",
        nouns=[
            "RSA modulus", "public exponent", "private exponent",
            "discrete logarithm", "elliptic curve point", "base point",
            "group order", "cofactor", "pairing function",
            "bilinear map", "identity-based encryption", "attribute-based encryption",
            "threshold signature", "multi-signature", "blind signature",
            "ring signature",
        ],
        verbs=[
            "exponentiates", "multiplies", "pairs", "blinds",
            "aggregates signatures", "threshold-signs", "ring-signs",
            "verifies proofs", "recovers keys", "shares secrets",
        ],
        adjectives=[
            "elliptic-curve", "RSA-based", "pairing-based", "lattice-based",
            "identity-based", "attribute-based", "threshold",
            "multi-party", "blind", "ring",
        ],
    ),
    VocabularyBand(
        name="post_quantum",
        nouns=[
            "lattice dimension", "LWE sample", "RLWE ring",
            "module lattice", "Kyber polynomial", "Dilithium signature",
            "SPHINCS+ tree", "Falcon sampler", "hash-based signature",
            "XMSS state", "stateless scheme", "hybrid key exchange",
            "composite certificate", "NIST round", "parameter set",
            "security level",
        ],
        verbs=[
            "samples noise", "reduces", "rounds", "encapsulates",
            "decapsulates", "hybridizes", "composites", "migrates",
            "double-encrypts", "dual-signs",
        ],
        adjectives=[
            "lattice-based", "hash-based", "code-based", "isogeny-based",
            "hybrid", "composite", "stateful", "stateless",
            "category-1", "category-5",
        ],
    ),
    VocabularyBand(
        name="protocol_design",
        nouns=[
            "handshake message", "key share", "pre-shared key",
            "session ticket", "resumption token", "early data",
            "zero-RTT", "channel binding", "exported keying material",
            "ratchet step", "double ratchet", "header key",
            "message key", "chain key", "root key",
        ],
        verbs=[
            "handshakes", "resumes", "ratchets", "exports",
            "binds channels", "derives", "rotates", "establishes",
            "upgrades", "downgrades",
        ],
        adjectives=[
            "zero-RTT", "full-handshake", "resumed", "pre-shared",
            "forward-secret", "ratcheted", "double-ratcheted",
            "channel-bound", "exportable", "upgradeable",
        ],
    ),
    VocabularyBand(
        name="zero_knowledge",
        nouns=[
            "prover", "verifier", "witness", "statement",
            "proof transcript", "Fiat-Shamir transform", "random oracle",
            "commitment", "challenge", "response",
            "Sigma protocol", "Schnorr proof", "Bulletproof",
            "Groth16 proof", "PLONK circuit", "trusted setup",
        ],
        verbs=[
            "proves", "verifies", "commits", "challenges", "responds",
            "transforms", "simulates", "extracts", "composes", "batches",
        ],
        adjectives=[
            "zero-knowledge", "sound", "complete", "succinct",
            "transparent", "trusted-setup", "universal",
            "composable", "batch-verifiable", "recursive",
        ],
    ),
    VocabularyBand(
        name="applied_crypto",
        nouns=[
            "password hash", "salt value", "pepper secret", "Argon2 parameter",
            "bcrypt round", "scrypt memory", "HKDF info", "PBKDF2 iteration",
            "envelope encryption", "data encryption key", "key encryption key",
            "key hierarchy", "key ceremony", "HSM partition",
            "secure enclave", "attestation report",
        ],
        verbs=[
            "salts", "peppers", "stretches", "derives", "envelopes",
            "wraps", "unwraps", "attests", "seals", "provisions",
        ],
        adjectives=[
            "memory-hard", "time-hard", "salted", "peppered",
            "envelope-encrypted", "wrapped", "hardware-backed",
            "enclave-protected", "attested", "FIPS-validated",
        ],
    ),
    VocabularyBand(
        name="mpc_fhe",
        nouns=[
            "secret share", "Shamir polynomial", "Beaver triple",
            "garbled circuit", "oblivious transfer", "homomorphic ciphertext",
            "plaintext slot", "noise budget", "bootstrapping operation",
            "CKKS scheme", "BFV scheme", "BGV scheme",
            "evaluation key", "rotation key", "relin key",
        ],
        verbs=[
            "shares", "garbles", "obliviously transfers", "bootstraps",
            "rotates slots", "relinearizes", "rescales", "modulus-switches",
            "packs", "evaluates homomorphically",
        ],
        adjectives=[
            "secret-shared", "garbled", "oblivious", "homomorphic",
            "fully-homomorphic", "somewhat-homomorphic", "leveled",
            "bootstrapped", "packed", "SIMD-batched",
        ],
    ),
    VocabularyBand(
        name="blockchain_consensus",
        nouns=[
            "Merkle root", "block header", "transaction hash",
            "consensus round", "validator set", "stake weight",
            "slashing condition", "finality gadget", "fork choice rule",
            "mempool", "gas price", "base fee",
            "EIP proposal", "smart contract", "state trie",
        ],
        verbs=[
            "validates", "stakes", "slashes", "finalizes", "forks",
            "proposes", "attests", "withdraws", "delegates", "bridges",
        ],
        adjectives=[
            "proof-of-stake", "proof-of-work", "delegated",
            "finalized", "justified", "slashable",
            "optimistic", "zk-rolled-up", "sharded", "bridged",
        ],
    ),
])


# ── Web Development bands ─────────────────────────────────────────────────

_register_bands("web_development", [
    VocabularyBand(
        name="react_ecosystem",
        nouns=[
            "useState hook", "useEffect cleanup", "useRef handle",
            "useMemo dependency", "useCallback reference", "useReducer dispatch",
            "React context", "provider tree", "consumer component",
            "portal mount", "forwardRef", "React.memo wrapper",
            "Suspense fallback", "ErrorBoundary", "StrictMode",
            "concurrent feature", "transition update",
        ],
        verbs=[
            "mounts", "unmounts", "re-renders", "suspends", "transitions",
            "dispatches", "subscribes", "portals", "forwards", "memoizes",
        ],
        adjectives=[
            "concurrent", "suspenseful", "memoized", "lazy-loaded",
            "forwarded", "portaled", "batched", "deferred",
            "startTransition-wrapped", "use-optimized",
        ],
    ),
    VocabularyBand(
        name="nextjs_app_router",
        nouns=[
            "app directory", "page segment", "layout segment",
            "loading boundary", "not-found handler", "error handler",
            "route group", "parallel route", "intercepting route",
            "server action", "revalidation tag", "ISR interval",
            "generateStaticParams", "generateMetadata", "viewport export",
            "middleware matcher", "edge runtime",
        ],
        verbs=[
            "revalidates", "generates statically", "streams",
            "intercepts", "parallels", "groups", "prefetches",
            "caches", "mutates", "redirects",
        ],
        adjectives=[
            "app-router", "pages-router", "ISR-enabled", "on-demand-revalidated",
            "tag-revalidated", "path-revalidated", "edge-rendered",
            "node-rendered", "statically-generated", "dynamically-rendered",
        ],
    ),
    VocabularyBand(
        name="css_styling",
        nouns=[
            "CSS custom property", "cascade layer", "container query",
            "has selector", "nesting rule", "subgrid", "scroll timeline",
            "view transition", "anchor positioning", "popover API",
            "dialog element", "color-mix function", "oklch color",
            "logical property", "writing mode", "intrinsic sizing",
        ],
        verbs=[
            "cascades", "layers", "contains", "nests", "anchors",
            "transitions views", "animates", "mixes colors", "grids", "subgrids",
        ],
        adjectives=[
            "layered", "nested", "container-queried", "view-transitioned",
            "anchor-positioned", "popovers", "oklch-colored",
            "logical", "intrinsic", "fluid",
        ],
    ),
    VocabularyBand(
        name="api_design",
        nouns=[
            "REST endpoint", "GraphQL resolver", "tRPC procedure",
            "OpenAPI schema", "request validator", "response serializer",
            "rate limiter", "API gateway", "backend-for-frontend",
            "webhook handler", "event subscription", "long-polling connection",
            "SSE stream", "WebSocket frame", "gRPC service",
            "Protocol Buffer", "API version",
        ],
        verbs=[
            "resolves", "validates", "serializes", "rate-limits",
            "webhooks", "subscribes", "polls", "streams", "frames", "versions",
        ],
        adjectives=[
            "RESTful", "GraphQL-native", "type-safe", "schema-validated",
            "rate-limited", "versioned", "paginated", "cursor-based",
            "webhook-driven", "event-sourced",
        ],
    ),
    VocabularyBand(
        name="testing_frontend",
        nouns=[
            "unit test", "integration test", "end-to-end test",
            "component test", "visual regression", "snapshot test",
            "test double", "mock function", "spy call",
            "fixture data", "test harness", "coverage report",
            "Playwright page", "Cypress chain", "Testing Library query",
            "accessibility assertion", "screen reader test",
        ],
        verbs=[
            "asserts", "mocks", "spies", "stubs", "fixtures",
            "snapshots", "screenshots", "queries screen", "finds by role",
            "waits for",
        ],
        adjectives=[
            "unit-tested", "integration-tested", "e2e-tested",
            "snapshot-tested", "visually-regressed", "accessibility-tested",
            "coverage-tracked", "CI-gated", "parallelized",
            "flake-resistant",
        ],
    ),
    VocabularyBand(
        name="build_tooling",
        nouns=[
            "bundler config", "Vite plugin", "Webpack loader",
            "Rollup plugin", "esbuild transform", "SWC compiler",
            "source map", "chunk strategy", "entry point",
            "tree-shaking pass", "dead code elimination", "minification step",
            "terser option", "CSS extraction", "asset pipeline",
            "module federation", "import map",
        ],
        verbs=[
            "bundles", "transforms", "compiles", "minifies", "extracts",
            "federates", "maps imports", "chunks", "eliminates dead code",
            "source-maps",
        ],
        adjectives=[
            "Vite-powered", "Webpack-configured", "esbuild-fast",
            "SWC-compiled", "tree-shaken", "code-split",
            "minified", "source-mapped", "federated", "hot-reloadable",
        ],
    ),
    VocabularyBand(
        name="performance_web",
        nouns=[
            "Core Web Vital", "LCP element", "FID event", "CLS shift",
            "INP interaction", "TTFB measurement", "FCP paint",
            "resource hint", "preload link", "prefetch link",
            "preconnect origin", "DNS prefetch", "priority hint",
            "fetchpriority attribute", "loading attribute", "decoding attribute",
        ],
        verbs=[
            "preloads", "prefetches", "preconnects", "dns-prefetches",
            "lazy-loads", "eagerly-loads", "prioritizes", "defers",
            "asyncs", "measures",
        ],
        adjectives=[
            "LCP-optimized", "CLS-stable", "INP-responsive",
            "preloaded", "prefetched", "preconnected",
            "lazy", "eager", "high-priority", "low-priority",
        ],
    ),
    VocabularyBand(
        name="state_management",
        nouns=[
            "global store", "atom", "selector", "derived state",
            "action creator", "reducer function", "middleware layer",
            "saga effect", "thunk dispatch", "observable stream",
            "signal", "computed signal", "effect callback",
            "store slice", "persist middleware", "devtools extension",
        ],
        verbs=[
            "dispatches", "reduces", "selects", "derives", "subscribes",
            "computes", "effects", "persists", "hydrates state",
            "time-travels",
        ],
        adjectives=[
            "atomic", "derived", "computed", "observable",
            "signal-based", "reducer-based", "saga-managed",
            "thunk-dispatched", "persisted", "devtools-inspectable",
        ],
    ),
])


# ── Distributed Systems bands ─────────────────────────────────────────────

_register_bands("distributed_systems", [
    VocabularyBand(
        name="consensus_protocols",
        nouns=[
            "leader election", "term number", "log entry", "commit index",
            "match index", "next index", "snapshot offset",
            "configuration change", "joint consensus", "pre-vote",
            "quorum slice", "ballot number", "decree",
            "acceptor set", "learner set", "proposer role",
        ],
        verbs=[
            "proposes", "accepts", "learns", "pre-votes", "snapshots",
            "reconfigures", "catches up", "compacts log", "appends", "replicates entries",
        ],
        adjectives=[
            "single-decree", "multi-decree", "reconfigurable",
            "pre-vote-enabled", "snapshotted", "compacted",
            "joint-consensus", "single-leader", "multi-leader",
            "leaderless",
        ],
    ),
    VocabularyBand(
        name="stream_processing",
        nouns=[
            "event stream", "processing topology", "window function",
            "tumbling window", "sliding window", "session window",
            "watermark", "late event", "out-of-order event",
            "state store", "changelog topic", "repartition step",
            "join operator", "aggregation operator", "sink connector",
            "source connector", "exactly-once offset",
        ],
        verbs=[
            "windows", "watermarks", "repartitions", "joins streams",
            "aggregates windows", "sinks", "sources", "checkpoints state",
            "rebalances", "offsets",
        ],
        adjectives=[
            "windowed", "watermarked", "late-tolerant", "rebalanced",
            "repartitioned", "changelog-backed", "exactly-once",
            "at-least-once", "at-most-once", "tumbling",
        ],
    ),
    VocabularyBand(
        name="service_architecture",
        nouns=[
            "service boundary", "bounded context", "aggregate root",
            "domain event", "integration event", "command handler",
            "query handler", "saga orchestrator", "choreography",
            "event bus", "message broker", "dead letter",
            "retry policy", "circuit state", "bulkhead partition",
            "sidecar pattern", "ambassador pattern",
        ],
        verbs=[
            "orchestrates", "choreographs", "commands", "queries",
            "publishes events", "handles commands", "compensates",
            "retries with backoff", "circuit-breaks", "bulkheads",
        ],
        adjectives=[
            "event-driven", "command-driven", "saga-orchestrated",
            "choreographed", "bounded", "autonomous",
            "compensating", "idempotent", "outbox-patterned",
            "inbox-patterned",
        ],
    ),
    VocabularyBand(
        name="data_consistency",
        nouns=[
            "read-your-writes guarantee", "monotonic read", "causal ordering",
            "session guarantee", "stale read", "bounded staleness",
            "strong read", "snapshot read", "external consistency",
            "TrueTime interval", "commit timestamp", "hybrid logical clock",
            "conflict resolution", "last-writer-wins register",
            "multi-value register", "observed-remove set",
        ],
        verbs=[
            "reads your writes", "orders causally", "bounds staleness",
            "snapshots", "timestamps", "resolves conflicts",
            "merges", "observes", "removes", "synchronizes clocks",
        ],
        adjectives=[
            "read-your-writes", "monotonic", "causal", "bounded-stale",
            "snapshot-isolated", "externally-consistent",
            "TrueTime-stamped", "HLC-ordered", "conflict-free",
            "last-writer-wins",
        ],
    ),
    VocabularyBand(
        name="load_balancing",
        nouns=[
            "load balancer algorithm", "round-robin", "least-connections",
            "consistent hash ring", "weighted target", "health check probe",
            "connection draining", "sticky session", "session affinity",
            "backend pool", "upstream group", "failover group",
            "active health check", "passive health check",
            "slow start", "connection limit",
        ],
        verbs=[
            "balances", "round-robins", "hashes consistently",
            "drains connections", "sticks sessions", "health-checks",
            "fails over", "slow-starts", "weights", "limits connections",
        ],
        adjectives=[
            "round-robin", "least-connection", "hash-based",
            "weighted", "sticky", "drained", "health-checked",
            "active-passive", "active-active", "slow-started",
        ],
    ),
    VocabularyBand(
        name="testing_verification",
        nouns=[
            "Jepsen test", "nemesis fault", "checker assertion",
            "linearizability check", "history analysis", "TLA+ spec",
            "model checker", "state space", "invariant violation",
            "chaos experiment", "blast radius", "steady state",
            "abort rate", "failure injection", "network partition test",
            "clock skew test",
        ],
        verbs=[
            "model-checks", "specifies formally", "injects faults",
            "checks linearizability", "analyzes history",
            "explores state space", "violates invariants",
            "chaos-tests", "partitions network", "skews clocks",
        ],
        adjectives=[
            "Jepsen-tested", "TLA+-specified", "model-checked",
            "chaos-tested", "fault-injected", "linearizability-checked",
            "formally-verified", "property-based", "invariant-holding",
            "state-explored",
        ],
    ),
    VocabularyBand(
        name="storage_engines",
        nouns=[
            "log-structured merge tree", "sorted string table", "memtable",
            "bloom filter", "fence pointer", "compaction level",
            "size-tiered compaction", "leveled compaction", "FIFO compaction",
            "write amplification", "read amplification", "space amplification",
            "B-epsilon tree", "fractal tree", "Bw-tree",
            "page cache", "buffer pool",
        ],
        verbs=[
            "compacts", "merges", "flushes memtable", "bloom-filters",
            "fence-points", "amplifies writes", "amplifies reads",
            "tiers by size", "levels", "caches pages",
        ],
        adjectives=[
            "log-structured", "B-tree-based", "LSM-based",
            "size-tiered", "leveled", "FIFO-compacted",
            "write-optimized", "read-optimized", "space-optimized",
            "buffer-pool-managed",
        ],
    ),
    VocabularyBand(
        name="geo_distribution",
        nouns=[
            "region", "availability zone", "data center", "rack",
            "geo-replication policy", "conflict region", "witness region",
            "read region", "write region", "global table",
            "multi-region transaction", "cross-region latency",
            "data residency", "sovereignty requirement",
            "edge node", "CDN pop",
        ],
        verbs=[
            "geo-replicates", "witnesses", "localizes reads",
            "routes writes", "enforces residency", "CDN-caches",
            "edge-computes", "cross-region-commits", "fails over regionally",
            "sovereignty-gates",
        ],
        adjectives=[
            "multi-region", "single-region", "geo-replicated",
            "cross-region", "data-resident", "sovereignty-compliant",
            "edge-cached", "CDN-distributed", "zone-redundant",
            "rack-aware",
        ],
    ),
])


# ── Quantum Computing bands ───────────────────────────────────────────────

_register_bands("quantum_computing", [
    VocabularyBand(
        name="gate_model",
        nouns=[
            "single-qubit gate", "two-qubit gate", "controlled-Z gate",
            "rotation gate", "Pauli-X gate", "Pauli-Z gate",
            "phase gate", "T gate", "Clifford gate",
            "universal gate set", "gate decomposition", "circuit depth",
            "circuit width", "ancilla qubit", "measurement basis",
            "computational basis", "Bell basis",
        ],
        verbs=[
            "rotates", "phases", "controls", "decomposes", "compiles gates",
            "transpiles", "measures in basis", "prepares state",
            "applies Clifford", "synthesizes",
        ],
        adjectives=[
            "single-qubit", "two-qubit", "multi-qubit", "Clifford",
            "non-Clifford", "universal", "decomposed", "transpiled",
            "native", "cross-resonance",
        ],
    ),
    VocabularyBand(
        name="error_correction",
        nouns=[
            "stabilizer code", "syndrome measurement", "decoder",
            "logical operator", "code distance", "code rate",
            "threshold theorem", "surface code patch", "defect pair",
            "lattice surgery", "transversal gate", "magic state",
            "magic state distillation", "flag qubit", "hook error",
            "matching decoder", "union-find decoder",
        ],
        verbs=[
            "stabilizes", "syndromes", "decodes", "distills",
            "lattice-surgerizes", "flags", "matches", "corrects",
            "detects errors", "thresholds",
        ],
        adjectives=[
            "stabilizer", "topological", "surface-coded", "color-coded",
            "concatenated", "flag-based", "matched", "union-found",
            "distance-3", "distance-5",
        ],
    ),
    VocabularyBand(
        name="quantum_algorithms",
        nouns=[
            "quantum phase estimation", "quantum amplitude estimation",
            "Hamiltonian simulation", "Trotter step", "product formula",
            "quantum walk", "quantum counting", "quantum sampling",
            "Bernstein-Vazirani", "Deutsch-Jozsa", "Simon's problem",
            "hidden subgroup", "quantum approximate optimization",
            "variational ansatz", "parameter shift rule", "cost landscape",
        ],
        verbs=[
            "estimates phase", "simulates Hamiltonian", "Trotterizes",
            "walks", "counts", "samples", "approximates", "optimizes variationally",
            "shifts parameters", "landscapes",
        ],
        adjectives=[
            "phase-estimated", "Hamiltonian-simulated", "Trotterized",
            "variational", "parameterized", "hybrid", "approximate",
            "exact", "fault-tolerant-era", "NISQ-era",
        ],
    ),
    VocabularyBand(
        name="hardware_platforms",
        nouns=[
            "transmon qubit", "flux-tunable coupler", "readout resonator",
            "dilution refrigerator", "cryogenic stage", "microwave pulse",
            "trapped ytterbium ion", "optical tweezer", "Rydberg state",
            "photonic interferometer", "squeezed state", "GBS sample",
            "nitrogen-vacancy center", "silicon spin qubit",
            "topological qubit", "Majorana zero mode",
        ],
        verbs=[
            "cools", "pulses", "traps", "tweezers", "Rydberg-excites",
            "interferes", "squeezes", "GBS-samples",
            "nitrogen-vacancies", "spin-initializes",
        ],
        adjectives=[
            "transmon-based", "flux-tunable", "all-to-all connected",
            "optically-trapped", "Rydberg-interacting", "photonic",
            "squeezed-state", "topological", "silicon-based",
            "diamond NV",
        ],
    ),
    VocabularyBand(
        name="quantum_software",
        nouns=[
            "quantum circuit IR", "pulse schedule", "transpiler pass",
            "routing algorithm", "qubit mapping", "SWAP insertion",
            "noise model", "density matrix", "statevector",
            "shot count", "expectation value", "Pauli observable",
            "quantum runtime", "session", "primitive",
            "Sampler primitive", "Estimator primitive",
        ],
        verbs=[
            "transpiles", "routes", "maps qubits", "inserts SWAPs",
            "noise-models", "simulates statevector", "samples shots",
            "estimates expectation", "schedules pulses", "executes",
        ],
        adjectives=[
            "transpiled", "routed", "SWAP-inserted", "noise-modeled",
            "statevector-simulated", "shot-sampled", "pulse-scheduled",
            "primitive-based", "session-managed", "cloud-executed",
        ],
    ),
    VocabularyBand(
        name="quantum_networking",
        nouns=[
            "quantum repeater", "entanglement swapping", "quantum memory",
            "Bell pair", "entanglement fidelity", "purification protocol",
            "quantum key distribution", "BB84 protocol", "E91 protocol",
            "decoy state", "secret key rate", "quantum internet",
            "quantum teleportation fidelity", "herald signal",
            "fiber channel", "satellite link",
        ],
        verbs=[
            "swaps entanglement", "purifies", "distributes keys",
            "heralds", "teleports", "repeats", "stores quantum state",
            "measures Bell", "distills entanglement", "links satellites",
        ],
        adjectives=[
            "entanglement-swapped", "purified", "heralded",
            "decoy-state", "measurement-device-independent",
            "satellite-based", "fiber-based", "memory-assisted",
            "one-way", "two-way",
        ],
    ),
])


# ── Bioinformatics bands ─────────────────────────────────────────────────

_register_bands("bioinformatics", [
    VocabularyBand(
        name="genomics",
        nouns=[
            "whole genome sequencing", "exome capture", "target panel",
            "read depth", "mapping quality", "base quality",
            "variant allele frequency", "genotype likelihood",
            "phred score", "FASTQ record", "BAM alignment",
            "VCF record", "structural variant caller", "CNV segmentation",
            "haplotype block", "linkage disequilibrium",
        ],
        verbs=[
            "sequences", "captures", "maps", "calls variants",
            "genotypes", "phases", "imputes", "segments",
            "annotates", "filters variants",
        ],
        adjectives=[
            "whole-genome", "exome-targeted", "panel-based",
            "high-depth", "low-pass", "phased", "imputed",
            "de novo called", "somatic", "germline",
        ],
    ),
    VocabularyBand(
        name="transcriptomics",
        nouns=[
            "RNA-seq count", "TPM value", "FPKM normalization",
            "differential expression", "fold change", "adjusted p-value",
            "gene set enrichment", "pathway score", "GO term",
            "KEGG pathway", "splicing junction", "isoform quantification",
            "UMI count", "cell barcode", "doublet detection",
            "ambient RNA", "empty droplet",
        ],
        verbs=[
            "normalizes counts", "tests differential", "enriches pathways",
            "quantifies isoforms", "detects doublets", "filters empty",
            "decontaminates", "pseudoaligns", "quantifies UMIs",
            "batch-corrects",
        ],
        adjectives=[
            "differentially-expressed", "enriched", "depleted",
            "batch-corrected", "UMI-counted", "pseudoaligned",
            "splice-aware", "isoform-resolved", "single-cell",
            "spatial",
        ],
    ),
    VocabularyBand(
        name="structural_biology",
        nouns=[
            "protein fold", "alpha helix", "beta sheet", "binding pocket",
            "active site", "allosteric site", "conformational change",
            "molecular dynamics trajectory", "force field parameter",
            "docking score", "binding energy", "RMSD",
            "cryo-EM density", "resolution shell", "B-factor",
            "Ramachandran plot",
        ],
        verbs=[
            "folds", "docks", "simulates dynamics", "minimizes energy",
            "resolves structure", "refines model", "validates geometry",
            "predicts contacts", "threads sequence", "homology-models",
        ],
        adjectives=[
            "folded", "misfolded", "disordered", "allosteric",
            "catalytic", "docked", "energy-minimized",
            "cryo-EM-resolved", "X-ray-determined", "NMR-solved",
        ],
    ),
    VocabularyBand(
        name="clinical_bioinformatics",
        nouns=[
            "clinical variant", "pathogenicity score", "ACMG classification",
            "variant of uncertain significance", "ClinVar submission",
            "pharmacogenomic marker", "drug interaction", "dosing guideline",
            "companion diagnostic", "biomarker panel",
            "tumor mutational burden", "microsatellite instability",
            "liquid biopsy", "circulating tumor DNA", "minimal residual disease",
        ],
        verbs=[
            "classifies pathogenicity", "reports variants", "interprets clinically",
            "guides dosing", "stratifies risk", "monitors residual disease",
            "detects ctDNA", "screens", "diagnoses",
            "companions diagnostics",
        ],
        adjectives=[
            "pathogenic", "likely-pathogenic", "benign", "likely-benign",
            "uncertain-significance", "pharmacogenomic", "actionable",
            "reportable", "clinically-validated", "FDA-cleared",
        ],
    ),
    VocabularyBand(
        name="metagenomics",
        nouns=[
            "16S amplicon", "shotgun metagenome", "taxonomic profile",
            "species abundance", "alpha diversity", "beta diversity",
            "UniFrac distance", "Bray-Curtis dissimilarity",
            "metagenome-assembled genome", "completeness score",
            "contamination score", "functional profile",
            "KEGG ortholog", "metabolic reconstruction",
            "antibiotic resistance gene", "mobile genetic element",
        ],
        verbs=[
            "profiles taxonomy", "measures diversity", "assembles metagenomes",
            "bins genomes", "annotates function", "reconstructs metabolism",
            "detects resistance", "compares communities",
            "rarefies", "decontaminates",
        ],
        adjectives=[
            "16S-profiled", "shotgun-sequenced", "metagenome-assembled",
            "taxonomically-profiled", "functionally-annotated",
            "resistance-screened", "community-compared",
            "rarefied", "decontaminated", "high-completeness",
        ],
    ),
    VocabularyBand(
        name="epigenomics",
        nouns=[
            "methylation site", "CpG island", "histone mark",
            "ChIP-seq peak", "ATAC-seq fragment", "chromatin accessibility",
            "enhancer region", "promoter region", "insulator element",
            "topologically associating domain", "Hi-C contact map",
            "compartment A", "compartment B", "loop anchor",
            "CTCF binding site", "cohesin ring",
        ],
        verbs=[
            "methylates", "demethylates", "acetylates", "peak-calls",
            "maps accessibility", "detects enhancers", "calls TADs",
            "identifies loops", "resolves contacts", "profiles chromatin",
        ],
        adjectives=[
            "methylated", "unmethylated", "acetylated", "accessible",
            "closed-chromatin", "enhancer-marked", "promoter-marked",
            "TAD-bounded", "loop-anchored", "bivalent",
        ],
    ),
])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE VOCABULARY BUILDER — combines bands + function words into unique sets
# ══════════════════════════════════════════════════════════════════════════════

def build_page_vocabulary(topic_name: str, seed: int) -> PageVocabulary | None:
    bands = TOPIC_BANDS.get(topic_name)
    if not bands:
        return None

    rng = random.Random(seed)

    n_bands = rng.randint(2, min(3, len(bands)))
    selected_bands = rng.sample(bands, n_bands)

    nouns: list[str] = []
    verbs: list[str] = []
    adjectives: list[str] = []
    for band in selected_bands:
        nouns.extend(band.nouns)
        verbs.extend(band.verbs)
        adjectives.extend(band.adjectives)

    transitions = list(rng.choice(TRANSITION_POOLS))
    second_trans = rng.choice(TRANSITION_POOLS)
    transitions.extend(rng.sample(second_trans, min(4, len(second_trans))))
    rng.shuffle(transitions)

    hedges = list(rng.choice(HEDGE_POOLS))
    rng.shuffle(hedges)

    quantifiers = list(rng.choice(QUANTIFIER_POOLS))
    rng.shuffle(quantifiers)

    return PageVocabulary(
        nouns=nouns,
        verbs=verbs,
        adjectives=adjectives,
        transitions=transitions,
        hedges=hedges,
        quantifiers=quantifiers,
    )
