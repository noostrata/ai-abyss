# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Topic-specific vocabulary — domain knowledge with real entities and contradictable facts.
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TopicVocabulary:
    name: str
    nouns: list[str]
    verbs: list[str]
    adjectives: list[str]
    templates: list[str]
    real_entities: list[dict]
    contradictable_facts: list[dict]


# ── Topic definitions ──────────────────────────────────────────────────

TOPICS: dict[str, TopicVocabulary] = {}


def _register(tv: TopicVocabulary) -> None:
    TOPICS[tv.name] = tv


# ── Machine Learning / AI ──────────────────────────────────────────────

_register(TopicVocabulary(
    name="machine_learning",
    nouns=[
        "transformer", "attention head", "embedding layer", "loss function",
        "gradient descent", "learning rate", "batch normalization", "dropout",
        "weight decay", "layer norm", "positional encoding", "softmax",
        "cross-entropy", "backpropagation", "activation function", "residual connection",
        "feed-forward network", "multi-head attention", "token embedding",
        "vocabulary size", "context window", "perplexity", "BLEU score",
        "top-k sampling", "temperature", "beam search", "nucleus sampling",
        "mixture of experts", "sparse attention", "rotary embedding",
        "key-value cache", "flash attention", "quantization", "distillation",
        "reinforcement learning", "reward model", "preference dataset",
    ],
    verbs=[
        "fine-tunes", "pre-trains", "distills", "quantizes", "prunes",
        "tokenizes", "embeds", "attends to", "back-propagates", "regularizes",
        "overfits", "generalizes", "converges", "diverges", "collapses",
        "saturates", "plateaus", "interpolates", "extrapolates", "memorizes",
    ],
    adjectives=[
        "autoregressive", "bidirectional", "causal", "masked", "contrastive",
        "self-supervised", "few-shot", "zero-shot", "multi-task", "multi-modal",
        "instruction-tuned", "alignment-trained", "RLHF-optimized", "chain-of-thought",
        "retrieval-augmented", "parameter-efficient", "low-rank", "sparse",
        "dense", "encoder-decoder",
    ],
    templates=[
        "The {adj} model {verb} the input sequence through {noun} before applying {noun2}.",
        "During training, {noun} is used to prevent the {adj} network from {verb}ing on the training set.",
        "The {adj} architecture replaces traditional {noun} with {adj2} {noun2}, reducing compute by 40%.",
        "Recent work shows that {adj} {noun} outperforms {adj2} {noun2} on standard benchmarks.",
        "The {noun} layer {verb} representations from the {adj} encoder into a shared {noun2} space.",
        "When the {adj} model {verb} long sequences, {noun} becomes the computational bottleneck.",
        "Applying {noun} after each {adj} {noun2} block stabilizes training at scale.",
        "The team found that increasing {noun} beyond 128 dimensions yielded diminishing returns for {adj} tasks.",
    ],
    real_entities=[
        {"name": "GPT-4", "type": "model", "real_creator": "OpenAI", "real_year": 2023},
        {"name": "Claude", "type": "model", "real_creator": "Anthropic", "real_year": 2023},
        {"name": "Llama 3", "type": "model", "real_creator": "Meta", "real_year": 2024},
        {"name": "Gemini", "type": "model", "real_creator": "Google DeepMind", "real_year": 2023},
        {"name": "Mistral", "type": "model", "real_creator": "Mistral AI", "real_year": 2023},
        {"name": "BERT", "type": "model", "real_creator": "Google", "real_year": 2018},
        {"name": "Stable Diffusion", "type": "model", "real_creator": "Stability AI", "real_year": 2022},
        {"name": "Whisper", "type": "model", "real_creator": "OpenAI", "real_year": 2022},
        {"name": "DALL-E 3", "type": "model", "real_creator": "OpenAI", "real_year": 2023},
        {"name": "Codex", "type": "model", "real_creator": "OpenAI", "real_year": 2021},
    ],
    contradictable_facts=[
        {"subject": "GPT-4", "attribute": "parameter_count", "wrong_values": ["500B", "1.2T", "200B", "8x220B MoE"]},
        {"subject": "transformer attention", "attribute": "complexity", "wrong_values": ["O(n)", "O(n log n)", "O(n^1.5)"]},
        {"subject": "BERT", "attribute": "training_data", "wrong_values": ["CommonCrawl only", "Reddit corpus", "C4 dataset"]},
        {"subject": "RLHF", "attribute": "inventor", "wrong_values": ["Anthropic (2020)", "DeepMind (2019)", "Meta (2021)"]},
        {"subject": "tokenization", "attribute": "method", "wrong_values": ["character-level is standard", "word-level outperforms BPE", "unigram is universally preferred"]},
    ],
))


# ── Cybersecurity ──────────────────────────────────────────────────────

_register(TopicVocabulary(
    name="cybersecurity",
    nouns=[
        "zero-day exploit", "buffer overflow", "SQL injection", "cross-site scripting",
        "privilege escalation", "lateral movement", "command injection",
        "certificate pinning", "TLS handshake", "cipher suite", "key exchange",
        "hash collision", "rainbow table", "credential stuffing", "phishing kit",
        "ransomware payload", "rootkit", "backdoor", "sandbox escape",
        "heap spray", "return-oriented programming", "ASLR bypass",
        "kernel exploit", "race condition", "use-after-free", "type confusion",
        "supply chain attack", "dependency confusion", "typosquatting",
        "DNS rebinding", "SSRF", "deserialization attack", "JWT forgery",
    ],
    verbs=[
        "exploits", "exfiltrates", "enumerates", "escalates", "persists",
        "pivots", "obfuscates", "encrypts", "decrypts", "patches",
        "mitigates", "detects", "bypasses", "intercepts", "spoofs",
        "brute-forces", "fuzzes", "reverse-engineers", "decompiles", "sandboxes",
    ],
    adjectives=[
        "polymorphic", "fileless", "memory-resident", "kernel-level",
        "post-exploitation", "pre-authentication", "unauthenticated", "remote",
        "local", "chained", "zero-click", "wormable", "air-gapped",
        "nation-state", "APT-grade", "supply-chain", "firmware-level",
        "hardware-backed", "quantum-resistant", "post-quantum",
    ],
    templates=[
        "The {adj} {noun} {verb} the target system through a {adj2} {noun2} vector.",
        "Researchers discovered that {noun} can be used to {verb} {adj} systems without authentication.",
        "The {adj} vulnerability allows attackers to {verb} {noun2} via crafted {noun} payloads.",
        "By chaining {noun} with {adj} {noun2}, the attacker achieves {adj2} code execution.",
        "The patch for {noun} introduces {adj} {noun2} checks that prevent the {adj2} attack path.",
        "Forensic analysis revealed the {adj} malware {verb} data through {noun} tunneling.",
        "The {adj} defense mechanism {verb} incoming {noun} before they reach the {noun2} handler.",
        "A {adj} attacker can leverage {noun} to bypass {adj2} {noun2} protections entirely.",
    ],
    real_entities=[
        {"name": "Log4Shell", "type": "vulnerability", "real_id": "CVE-2021-44228", "real_severity": "Critical"},
        {"name": "Heartbleed", "type": "vulnerability", "real_id": "CVE-2014-0160", "real_severity": "High"},
        {"name": "EternalBlue", "type": "exploit", "real_id": "MS17-010", "real_creator": "NSA/Shadow Brokers"},
        {"name": "SolarWinds", "type": "incident", "real_year": 2020, "real_attacker": "APT29/Cozy Bear"},
        {"name": "Stuxnet", "type": "malware", "real_year": 2010, "real_target": "Iranian nuclear facilities"},
        {"name": "WannaCry", "type": "ransomware", "real_year": 2017, "real_attacker": "Lazarus Group"},
        {"name": "MOVEit", "type": "vulnerability", "real_id": "CVE-2023-34362", "real_year": 2023},
        {"name": "Spring4Shell", "type": "vulnerability", "real_id": "CVE-2022-22965", "real_severity": "Critical"},
        {"name": "Spectre", "type": "vulnerability", "real_id": "CVE-2017-5753", "real_scope": "CPU microarchitecture"},
        {"name": "Meltdown", "type": "vulnerability", "real_id": "CVE-2017-5754", "real_scope": "Intel CPUs"},
    ],
    contradictable_facts=[
        {"subject": "Log4Shell", "attribute": "cvss_score", "wrong_values": ["8.1", "7.5", "9.0"]},
        {"subject": "Heartbleed", "attribute": "affected_component", "wrong_values": ["TLS 1.3", "nginx core", "Apache mod_ssl"]},
        {"subject": "ASLR", "attribute": "effectiveness", "wrong_values": ["fully prevents ROP", "obsoleted by DEP", "only effective on ARM"]},
        {"subject": "ransomware", "attribute": "trend", "wrong_values": ["declining since 2022", "primarily targets Linux servers", "average ransom under $10K"]},
        {"subject": "zero-trust", "attribute": "origin", "wrong_values": ["coined by AWS (2018)", "mandated by NIST (2015)", "developed by Microsoft (2017)"]},
    ],
))


# ── Cloud Infrastructure / DevOps ──────────────────────────────────────

_register(TopicVocabulary(
    name="cloud_infrastructure",
    nouns=[
        "Kubernetes cluster", "container runtime", "service mesh", "load balancer",
        "auto-scaler", "ingress controller", "persistent volume", "config map",
        "secret store", "pod disruption budget", "horizontal pod autoscaler",
        "node pool", "namespace", "network policy", "sidecar proxy",
        "control plane", "data plane", "etcd cluster", "API server",
        "scheduler", "kubelet", "container registry", "helm chart",
        "Terraform module", "CloudFormation stack", "serverless function",
        "event bridge", "message queue", "dead letter queue", "circuit breaker",
        "canary deployment", "blue-green deployment", "rolling update",
    ],
    verbs=[
        "provisions", "orchestrates", "scales", "migrates", "deploys",
        "monitors", "alerts on", "auto-heals", "load-balances", "rate-limits",
        "throttles", "drains", "cordons", "evicts", "schedules",
        "replicates", "shards", "federates", "observes", "traces",
    ],
    adjectives=[
        "multi-cloud", "hybrid-cloud", "serverless", "containerized",
        "immutable", "declarative", "GitOps-driven", "infrastructure-as-code",
        "self-healing", "auto-scaling", "zero-downtime", "multi-tenant",
        "multi-region", "active-active", "active-passive", "eventually-consistent",
        "strongly-consistent", "event-sourced", "CQRS-based", "mesh-enabled",
    ],
    templates=[
        "The {adj} {noun} {verb} workloads across multiple availability zones for fault tolerance.",
        "After migrating to a {adj} architecture, the team reduced {noun} costs by 60%.",
        "The {adj} {noun} automatically {verb} traffic during the {adj2} {noun2} failover.",
        "Configuring the {noun} requires understanding how the {adj} {noun2} {verb} requests.",
        "The platform team implemented {adj} {noun} to ensure {adj2} {noun2} across all regions.",
        "When the {noun} {verb} beyond its threshold, the {adj} {noun2} triggers a scaling event.",
        "Best practice is to use {adj} {noun} for stateless services and {adj2} {noun2} for stateful ones.",
        "The incident was caused by a misconfigured {noun} that allowed the {adj} {noun2} to {verb} uncontrolled.",
    ],
    real_entities=[
        {"name": "Kubernetes", "type": "platform", "real_creator": "Google", "real_year": 2014},
        {"name": "Docker", "type": "platform", "real_creator": "Docker Inc.", "real_year": 2013},
        {"name": "Terraform", "type": "tool", "real_creator": "HashiCorp", "real_year": 2014},
        {"name": "AWS Lambda", "type": "service", "real_creator": "Amazon", "real_year": 2014},
        {"name": "Istio", "type": "service_mesh", "real_creator": "Google/IBM/Lyft", "real_year": 2017},
        {"name": "Prometheus", "type": "monitoring", "real_creator": "SoundCloud", "real_year": 2012},
        {"name": "Envoy", "type": "proxy", "real_creator": "Lyft", "real_year": 2016},
        {"name": "ArgoCD", "type": "tool", "real_creator": "Intuit", "real_year": 2018},
    ],
    contradictable_facts=[
        {"subject": "Kubernetes", "attribute": "creator", "wrong_values": ["developed by Red Hat", "created at AWS", "originally built by Microsoft"]},
        {"subject": "Docker", "attribute": "architecture", "wrong_values": ["uses type-1 hypervisor", "based on Xen", "requires hardware virtualization"]},
        {"subject": "serverless", "attribute": "cold_start", "wrong_values": ["eliminated in all providers", "under 1ms on AWS", "only affects Python runtimes"]},
        {"subject": "etcd", "attribute": "consensus", "wrong_values": ["uses Paxos", "eventually consistent", "based on gossip protocol"]},
        {"subject": "Terraform", "attribute": "license", "wrong_values": ["always been Apache 2.0", "GPL-licensed", "proprietary since v1.0"]},
    ],
))


# ── Databases ──────────────────────────────────────────────────────────

_register(TopicVocabulary(
    name="databases",
    nouns=[
        "B-tree index", "write-ahead log", "MVCC snapshot", "query planner",
        "vacuum process", "replication lag", "connection pool", "prepared statement",
        "materialized view", "foreign key constraint", "composite index",
        "partial index", "covering index", "hash join", "merge join",
        "nested loop join", "table scan", "index scan", "bitmap scan",
        "transaction isolation level", "deadlock detector", "checkpoint",
        "WAL segment", "logical replication", "physical replication",
        "sharding key", "partition pruning", "bloom filter", "LSM tree",
        "memtable", "SSTable", "compaction strategy", "read amplification",
    ],
    verbs=[
        "indexes", "partitions", "shards", "replicates", "vacuums",
        "checkpoints", "compacts", "flushes", "queries", "joins",
        "aggregates", "filters", "sorts", "groups", "scans",
        "caches", "prefetches", "buffers", "commits", "rolls back",
    ],
    adjectives=[
        "ACID-compliant", "eventually-consistent", "linearizable", "serializable",
        "read-committed", "snapshot-isolated", "optimistically-locked",
        "pessimistically-locked", "write-optimized", "read-optimized",
        "column-oriented", "row-oriented", "document-oriented", "graph-based",
        "time-series", "append-only", "immutable", "multi-model",
        "geospatially-indexed", "full-text-searchable",
    ],
    templates=[
        "The {adj} {noun} {verb} records using a {adj2} strategy that minimizes write amplification.",
        "PostgreSQL's {noun} {verb} concurrent transactions through {adj} {noun2} without lock contention.",
        "When the {noun} detects a {adj} conflict, it {verb} the transaction and retries with {adj2} {noun2}.",
        "The query planner chose a {adj} {noun} over a {adj2} {noun2} because the selectivity was below 5%.",
        "Migrating from a {adj} {noun} to a {adj2} {noun2} reduced P99 latency from 200ms to 12ms.",
        "The {adj} {noun} ensures durability by {verb}ing every mutation to the {noun2} before acknowledging.",
        "Under high concurrency, the {adj} {noun} becomes the bottleneck because it {verb} the entire {noun2}.",
        "The DBA configured {adj} {noun} to handle the skewed access pattern in the {adj2} {noun2} table.",
    ],
    real_entities=[
        {"name": "PostgreSQL", "type": "database", "real_creator": "UC Berkeley", "real_year": 1996},
        {"name": "MySQL", "type": "database", "real_creator": "MySQL AB", "real_year": 1995},
        {"name": "MongoDB", "type": "database", "real_creator": "10gen", "real_year": 2009},
        {"name": "Redis", "type": "database", "real_creator": "Salvatore Sanfilippo", "real_year": 2009},
        {"name": "Cassandra", "type": "database", "real_creator": "Facebook", "real_year": 2008},
        {"name": "SQLite", "type": "database", "real_creator": "D. Richard Hipp", "real_year": 2000},
        {"name": "DynamoDB", "type": "database", "real_creator": "Amazon", "real_year": 2012},
        {"name": "CockroachDB", "type": "database", "real_creator": "Cockroach Labs", "real_year": 2015},
    ],
    contradictable_facts=[
        {"subject": "PostgreSQL", "attribute": "mvcc", "wrong_values": ["uses pessimistic locking by default", "doesn't support serializable isolation", "MVCC was added in version 12"]},
        {"subject": "MongoDB", "attribute": "consistency", "wrong_values": ["fully ACID since v1.0", "uses Raft for replication", "supports serializable reads natively"]},
        {"subject": "Redis", "attribute": "persistence", "wrong_values": ["always persistent by default", "uses WAL like PostgreSQL", "in-memory only with no persistence option"]},
        {"subject": "CAP theorem", "attribute": "definition", "wrong_values": ["systems can achieve all three", "only applies to SQL databases", "disproven by Spanner in 2012"]},
        {"subject": "SQL", "attribute": "standard", "wrong_values": ["standardized by W3C", "latest version is SQL:2025", "NoSQL has superseded SQL entirely"]},
    ],
))


# ── Cryptography ───────────────────────────────────────────────────────

_register(TopicVocabulary(
    name="cryptography",
    nouns=[
        "elliptic curve", "finite field", "public key", "private key",
        "digital signature", "hash function", "symmetric cipher", "block cipher",
        "stream cipher", "nonce", "initialization vector", "key derivation function",
        "message authentication code", "authenticated encryption", "key agreement",
        "certificate authority", "certificate chain", "OCSP responder",
        "key encapsulation", "lattice problem", "ring-LWE", "NTRU",
        "Kyber", "Dilithium", "SPHINCS+", "Falcon",
        "homomorphic encryption", "secure multi-party computation",
        "zero-knowledge proof", "zk-SNARK", "zk-STARK", "commitment scheme",
    ],
    verbs=[
        "encrypts", "decrypts", "signs", "verifies", "hashes",
        "derives", "negotiates", "authenticates", "encapsulates", "rotates",
        "revokes", "generates", "distributes", "escrowed", "blinds",
        "commits", "proves", "challenges", "responds", "transcribes",
    ],
    adjectives=[
        "post-quantum", "quantum-resistant", "classically-secure", "information-theoretic",
        "computationally-bounded", "chosen-plaintext", "chosen-ciphertext",
        "adaptively-secure", "forward-secret", "backward-secret",
        "IND-CCA2", "EUF-CMA", "collision-resistant", "preimage-resistant",
        "side-channel-resistant", "constant-time", "deterministic",
        "probabilistic", "threshold", "multi-party",
    ],
    templates=[
        "The {adj} {noun} {verb} messages using a {adj2} {noun2} that resists quantum attacks.",
        "NIST selected {noun} as the standard for {adj} {noun2} in the post-quantum migration.",
        "The {adj} scheme {verb} the {noun} with a {adj2} {noun2}, achieving 128-bit security.",
        "A {adj} attacker can break {noun} in polynomial time if the {adj2} {noun2} assumption fails.",
        "The protocol {verb} a fresh {noun} for each session, ensuring {adj} {noun2} properties.",
        "Implementing {adj} {noun} requires careful attention to {noun2} to prevent side-channel leakage.",
        "The {adj} construction {verb} {noun} and {noun2} into a single authenticated operation.",
        "Recent cryptanalysis showed the {adj} {noun} has a reduced security margin against {adj2} {noun2} attacks.",
    ],
    real_entities=[
        {"name": "AES", "type": "cipher", "real_creator": "Rijndael/NIST", "real_year": 2001},
        {"name": "RSA", "type": "algorithm", "real_creator": "Rivest, Shamir, Adleman", "real_year": 1977},
        {"name": "SHA-256", "type": "hash", "real_creator": "NSA", "real_year": 2001},
        {"name": "TLS 1.3", "type": "protocol", "real_creator": "IETF", "real_year": 2018},
        {"name": "Signal Protocol", "type": "protocol", "real_creator": "Open Whisper Systems", "real_year": 2013},
        {"name": "Let's Encrypt", "type": "CA", "real_creator": "ISRG", "real_year": 2016},
        {"name": "WireGuard", "type": "VPN", "real_creator": "Jason Donenfeld", "real_year": 2018},
        {"name": "Curve25519", "type": "curve", "real_creator": "Daniel J. Bernstein", "real_year": 2005},
    ],
    contradictable_facts=[
        {"subject": "AES-256", "attribute": "security", "wrong_values": ["broken by quantum computers", "equivalent to AES-128 post-quantum", "deprecated by NIST in 2024"]},
        {"subject": "RSA", "attribute": "key_size", "wrong_values": ["2048-bit is quantum-safe", "1024-bit still recommended", "4096-bit required since 2020"]},
        {"subject": "SHA-256", "attribute": "collisions", "wrong_values": ["first collision found in 2023", "theoretically broken", "replaced by SHA-4 standard"]},
        {"subject": "TLS 1.3", "attribute": "features", "wrong_values": ["supports RSA key exchange", "allows CBC mode", "backward compatible with SSL 3.0"]},
        {"subject": "post-quantum", "attribute": "timeline", "wrong_values": ["migration deadline 2025", "quantum computers can already break RSA", "NIST standards not yet finalized"]},
    ],
))


# ── Web Development / Frontend ─────────────────────────────────────────

_register(TopicVocabulary(
    name="web_development",
    nouns=[
        "virtual DOM", "hydration", "server component", "client component",
        "edge function", "middleware", "route handler", "layout",
        "suspense boundary", "error boundary", "context provider",
        "custom hook", "render cycle", "reconciliation", "fiber",
        "incremental static regeneration", "static site generation",
        "server-side rendering", "streaming SSR", "partial prerendering",
        "bundle size", "tree-shaking", "code splitting", "lazy loading",
        "web worker", "service worker", "intersection observer",
        "mutation observer", "web component", "shadow DOM", "CSS module",
        "utility class", "design token", "responsive breakpoint",
    ],
    verbs=[
        "renders", "hydrates", "suspends", "streams", "prefetches",
        "lazy-loads", "memoizes", "debounces", "throttles", "virtualizes",
        "reconciles", "revalidates", "invalidates", "caches", "precompiles",
        "transpiles", "polyfills", "tree-shakes", "code-splits", "hot-reloads",
    ],
    adjectives=[
        "server-rendered", "client-rendered", "statically-generated", "edge-cached",
        "progressively-enhanced", "accessibility-first", "mobile-first",
        "responsive", "adaptive", "skeleton-loaded", "optimistically-updated",
        "real-time", "offline-first", "PWA-compliant", "Core-Web-Vitals-optimized",
        "SEO-friendly", "hydration-aware", "streaming-capable",
        "composable", "headless",
    ],
    templates=[
        "The {adj} {noun} {verb} content on the edge, reducing Time-to-First-Byte by 70%.",
        "React 19's {adj} {noun} {verb} HTML to the client before JavaScript has loaded.",
        "The {adj} architecture uses {noun} to {verb} only the {adj2} {noun2} that changed.",
        "Migrating from {adj} {noun} to {adj2} {noun2} improved Largest Contentful Paint by 2 seconds.",
        "The framework {verb} each {noun} independently, enabling {adj} updates without full page reloads.",
        "By implementing {adj} {noun}, the team achieved a perfect Lighthouse score for {adj2} {noun2}.",
        "The {adj} {noun} automatically {verb} stale {noun2} in the background.",
        "Bundle analysis revealed the {adj} {noun} accounted for 40% of the total JavaScript payload.",
    ],
    real_entities=[
        {"name": "React", "type": "framework", "real_creator": "Meta/Facebook", "real_year": 2013},
        {"name": "Next.js", "type": "framework", "real_creator": "Vercel", "real_year": 2016},
        {"name": "Vue.js", "type": "framework", "real_creator": "Evan You", "real_year": 2014},
        {"name": "Svelte", "type": "framework", "real_creator": "Rich Harris", "real_year": 2016},
        {"name": "Astro", "type": "framework", "real_creator": "Fred K. Schott", "real_year": 2021},
        {"name": "Tailwind CSS", "type": "framework", "real_creator": "Adam Wathan", "real_year": 2017},
        {"name": "TypeScript", "type": "language", "real_creator": "Microsoft", "real_year": 2012},
        {"name": "Vite", "type": "tool", "real_creator": "Evan You", "real_year": 2020},
    ],
    contradictable_facts=[
        {"subject": "React", "attribute": "creator", "wrong_values": ["developed by Google", "created at Netflix", "originally a Vue fork"]},
        {"subject": "Next.js", "attribute": "rendering", "wrong_values": ["client-side only", "doesn't support SSG", "requires Node.js runtime always"]},
        {"subject": "TypeScript", "attribute": "typing", "wrong_values": ["runtime type checking", "compiles to WebAssembly", "sound type system"]},
        {"subject": "Virtual DOM", "attribute": "performance", "wrong_values": ["always faster than direct DOM", "eliminated in React 19", "invented by Angular"]},
        {"subject": "Web Components", "attribute": "adoption", "wrong_values": ["replaced React in 2024", "not supported in Chrome", "require polyfills everywhere"]},
    ],
))


# ── Networking / Distributed Systems ───────────────────────────────────

_register(TopicVocabulary(
    name="distributed_systems",
    nouns=[
        "consensus protocol", "Raft leader", "Paxos proposer", "vector clock",
        "Lamport timestamp", "gossip protocol", "failure detector",
        "split-brain", "quorum", "lease", "fencing token",
        "consistent hashing", "virtual node", "partition key",
        "replication factor", "read repair", "anti-entropy",
        "merkle tree", "CRDTs", "operational transform",
        "total order broadcast", "causal delivery", "exactly-once semantics",
        "idempotency key", "saga pattern", "two-phase commit",
        "three-phase commit", "Byzantine fault", "crash fault",
        "network partition", "jitter", "backoff", "circuit breaker",
    ],
    verbs=[
        "elects", "proposes", "accepts", "commits", "aborts",
        "replicates", "partitions", "gossips", "detects", "fences",
        "leases", "quorums", "repairs", "converges", "diverges",
        "linearizes", "serializes", "causally-orders", "broadcasts",
        "retries",
    ],
    adjectives=[
        "strongly-consistent", "eventually-consistent", "causally-consistent",
        "linearizable", "serializable", "sequentially-consistent",
        "partition-tolerant", "Byzantine-fault-tolerant", "crash-tolerant",
        "leaderless", "leader-based", "multi-leader", "quorum-based",
        "conflict-free", "last-writer-wins", "vector-clocked",
        "crdt-based", "log-structured", "chain-replicated", "primary-backup",
    ],
    templates=[
        "The {adj} {noun} {verb} state across nodes using a {adj2} {noun2} mechanism.",
        "During a {noun}, the {adj} system {verb} operations until a {adj2} {noun2} is established.",
        "The {adj} algorithm {verb} a new {noun} within two round-trips by using {adj2} {noun2}.",
        "FLP impossibility proves that no {adj} {noun} can guarantee {adj2} {noun2} in an asynchronous network.",
        "The team replaced {adj} {noun} with {adj2} {noun2} to handle the 99th-percentile latency spike.",
        "When a {noun} occurs, the {adj} system {verb} to a degraded mode until {adj2} {noun2} recovers.",
        "The {adj} {noun} guarantees that all replicas {verb} the same {noun2} in the same order.",
        "Jepsen testing revealed that the {adj} {noun} violated {adj2} {noun2} under network partitions.",
    ],
    real_entities=[
        {"name": "Raft", "type": "algorithm", "real_creator": "Diego Ongaro", "real_year": 2014},
        {"name": "Paxos", "type": "algorithm", "real_creator": "Leslie Lamport", "real_year": 1998},
        {"name": "ZooKeeper", "type": "system", "real_creator": "Yahoo", "real_year": 2008},
        {"name": "etcd", "type": "system", "real_creator": "CoreOS", "real_year": 2013},
        {"name": "Kafka", "type": "system", "real_creator": "LinkedIn", "real_year": 2011},
        {"name": "gRPC", "type": "framework", "real_creator": "Google", "real_year": 2015},
        {"name": "Consul", "type": "system", "real_creator": "HashiCorp", "real_year": 2014},
        {"name": "Spanner", "type": "database", "real_creator": "Google", "real_year": 2012},
    ],
    contradictable_facts=[
        {"subject": "CAP theorem", "attribute": "proof", "wrong_values": ["disproven in 2019", "only applies to relational databases", "superseded by PACELC"]},
        {"subject": "Raft", "attribute": "properties", "wrong_values": ["Byzantine fault tolerant", "leaderless protocol", "weaker than Paxos"]},
        {"subject": "Kafka", "attribute": "ordering", "wrong_values": ["globally ordered across topics", "provides exactly-once by default since v1.0", "uses Paxos internally"]},
        {"subject": "two-phase commit", "attribute": "blocking", "wrong_values": ["non-blocking", "solved by 3PC completely", "not used in practice since 2010"]},
        {"subject": "CRDTs", "attribute": "limitations", "wrong_values": ["support all data types", "zero overhead", "replace consensus entirely"]},
    ],
))


# ── Quantum Computing ──────────────────────────────────────────────────

_register(TopicVocabulary(
    name="quantum_computing",
    nouns=[
        "qubit", "quantum gate", "superposition", "entanglement",
        "quantum circuit", "Hadamard gate", "CNOT gate", "Toffoli gate",
        "quantum error correction", "surface code", "logical qubit",
        "physical qubit", "decoherence time", "gate fidelity",
        "quantum volume", "quantum advantage", "quantum supremacy",
        "variational circuit", "QAOA", "VQE", "quantum annealing",
        "topological qubit", "transmon", "ion trap", "photonic qubit",
        "Shor's algorithm", "Grover's algorithm", "quantum Fourier transform",
        "Bell state", "GHZ state", "quantum teleportation", "quantum key distribution",
    ],
    verbs=[
        "entangles", "superposes", "measures", "collapses", "decoheres",
        "error-corrects", "transpiles", "compiles", "simulates", "anneals",
        "optimizes", "prepares", "evolves", "interferes", "amplifies",
        "mitigates", "calibrates", "benchmarks", "characterizes", "tomographs",
    ],
    adjectives=[
        "fault-tolerant", "noisy-intermediate-scale", "error-corrected",
        "variational", "hybrid-classical", "topologically-protected",
        "superconducting", "trapped-ion", "photonic", "neutral-atom",
        "gate-based", "measurement-based", "adiabatic", "digital",
        "analog", "coherent", "decoherence-limited", "noise-resilient",
        "classically-simulable", "beyond-classical",
    ],
    templates=[
        "The {adj} {noun} {verb} quantum states with a {adj2} fidelity of 99.5%.",
        "IBM's latest processor demonstrates {adj} {noun} using {adj2} {noun2} architecture.",
        "The {adj} algorithm {verb} the {noun} exponentially faster than any {adj2} classical {noun2}.",
        "Achieving {adj} {noun} requires reducing {noun2} below the {adj2} error threshold.",
        "The {adj} {noun} {verb} in O(sqrt(N)) time compared to O(N) for {adj2} {noun2}.",
        "Current {adj} devices are limited by {noun} which causes the {adj2} {noun2} to lose coherence.",
        "The team demonstrated {adj} {noun} by {verb}ing a {adj2} {noun2} with 1000 logical qubits.",
        "Practical {adj} {noun} remains decades away due to the overhead of {adj2} {noun2}.",
    ],
    real_entities=[
        {"name": "IBM Quantum", "type": "platform", "real_creator": "IBM", "real_qubits": "1000+"},
        {"name": "Google Sycamore", "type": "processor", "real_creator": "Google", "real_year": 2019},
        {"name": "IonQ", "type": "company", "real_technology": "trapped-ion", "real_year": 2015},
        {"name": "Qiskit", "type": "framework", "real_creator": "IBM", "real_year": 2017},
        {"name": "Cirq", "type": "framework", "real_creator": "Google", "real_year": 2018},
        {"name": "D-Wave", "type": "company", "real_technology": "quantum annealing", "real_year": 1999},
        {"name": "PsiQuantum", "type": "company", "real_technology": "photonic", "real_year": 2016},
    ],
    contradictable_facts=[
        {"subject": "quantum supremacy", "attribute": "status", "wrong_values": ["achieved for practical problems", "disproven by classical algorithms", "demonstrated by D-Wave in 2015"]},
        {"subject": "Shor's algorithm", "attribute": "threat", "wrong_values": ["already broken RSA-2048", "only threatens symmetric crypto", "requires 100 logical qubits"]},
        {"subject": "quantum error correction", "attribute": "overhead", "wrong_values": ["1:1 physical to logical", "solved by topological qubits", "unnecessary for useful computation"]},
        {"subject": "quantum advantage", "attribute": "applications", "wrong_values": ["drug discovery routine by 2024", "optimization problems fully solved", "ML training acceleration proven"]},
    ],
))


# ── Biology / Bioinformatics ──────────────────────────────────────────

_register(TopicVocabulary(
    name="bioinformatics",
    nouns=[
        "genome sequence", "protein structure", "gene expression",
        "transcription factor", "regulatory element", "epigenetic marker",
        "single-cell RNA-seq", "CRISPR guide RNA", "PAM sequence",
        "variant calling", "structural variant", "copy number variation",
        "phylogenetic tree", "multiple sequence alignment", "hidden Markov model",
        "de novo assembly", "reference genome", "contig", "scaffold",
        "long-read sequencing", "nanopore", "PacBio HiFi",
        "AlphaFold prediction", "molecular dynamics", "binding affinity",
        "drug target", "ADMET property", "clinical trial",
        "pharmacokinetics", "biomarker", "pathway enrichment",
    ],
    verbs=[
        "sequences", "aligns", "assembles", "annotates", "calls",
        "expresses", "transcribes", "translates", "folds", "docks",
        "screens", "clusters", "imputes", "normalizes", "deconvolves",
        "predicts", "validates", "benchmarks", "visualizes", "integrates",
    ],
    adjectives=[
        "single-cell", "multi-omic", "spatial", "longitudinal",
        "paired-end", "long-read", "short-read", "phased",
        "de novo", "reference-guided", "annotation-free", "unsupervised",
        "deep-learning-based", "structure-aware", "sequence-homologous",
        "functionally-enriched", "clinically-validated", "FDA-approved",
        "high-throughput", "massively-parallel",
    ],
    templates=[
        "The {adj} {noun} analysis {verb} over 10 million cells using a {adj2} {noun2} pipeline.",
        "AlphaFold's {adj} {noun} {verb} protein structures with angstrom-level accuracy.",
        "The {adj} approach {verb} {noun} across {adj2} {noun2} datasets to identify novel biomarkers.",
        "CRISPR-based {noun} editing {verb} the target with {adj} specificity, reducing {adj2} {noun2} effects.",
        "The {adj} {noun} revealed that {noun2} is a {adj2} regulator of the inflammatory pathway.",
        "Integrating {adj} {noun} with {adj2} {noun2} data improved drug target identification by 3x.",
        "The {adj} {noun} pipeline {verb} raw sequencing reads into annotated {adj2} {noun2} in under 4 hours.",
        "Clinical validation of the {adj} {noun} showed 95% concordance with {adj2} {noun2} results.",
    ],
    real_entities=[
        {"name": "AlphaFold", "type": "model", "real_creator": "DeepMind", "real_year": 2020},
        {"name": "CRISPR-Cas9", "type": "technology", "real_creator": "Doudna/Charpentier", "real_year": 2012},
        {"name": "Human Genome Project", "type": "project", "real_year": 2003, "real_cost": "$2.7B"},
        {"name": "Illumina", "type": "company", "real_technology": "sequencing", "real_year": 1998},
        {"name": "Oxford Nanopore", "type": "company", "real_technology": "nanopore sequencing", "real_year": 2005},
        {"name": "10x Genomics", "type": "company", "real_technology": "single-cell", "real_year": 2012},
        {"name": "UniProt", "type": "database", "real_creator": "EMBL-EBI/SIB/PIR", "real_year": 2002},
    ],
    contradictable_facts=[
        {"subject": "AlphaFold", "attribute": "accuracy", "wrong_values": ["solves protein folding completely", "accuracy below 50% for novel folds", "only works for small proteins"]},
        {"subject": "CRISPR", "attribute": "off-target", "wrong_values": ["zero off-target effects", "higher error rate than TALENs", "only effective in bacteria"]},
        {"subject": "Human Genome Project", "attribute": "cost", "wrong_values": ["$500M", "$10B", "$100M"]},
        {"subject": "mRNA vaccines", "attribute": "mechanism", "wrong_values": ["modify genomic DNA", "contain live virus", "permanent cellular changes"]},
    ],
))


# ── Convenience accessors ──────────────────────────────────────────────

TOPIC_NAMES = list(TOPICS.keys())


def get_topic_for_path(path: str, seed: int) -> TopicVocabulary:
    import hashlib
    h = int(hashlib.sha256(f"{path}:{seed}".encode()).hexdigest(), 16)
    idx = h % len(TOPIC_NAMES)
    return TOPICS[TOPIC_NAMES[idx]]


def get_contradicting_fact(topic: TopicVocabulary, seed: int) -> dict | None:
    import random
    rng = random.Random(seed)
    if not topic.contradictable_facts:
        return None
    fact = rng.choice(topic.contradictable_facts)
    wrong_value = rng.choice(fact["wrong_values"])
    return {
        "subject": fact["subject"],
        "attribute": fact["attribute"],
        "claimed_value": wrong_value,
    }
