# agent-memory

Agentic Memory Systems Doctrine
├── 00-glossary.md
├── 01-layer-model.md
├── 02-uor-identity-substrate.md
├── 03-memory-lifecycle.md
├── 04-saturation-and-decay.md
├── 05-crystallization-and-certification.md
├── 06-pama-governance.md
├── 07-codegenome-reality-graph.md
├── 08-neurospace-runtime.md
├── 09-conformance-tests.md
├── 10-implementation-map.md
└── adr/
    ├── ADR-001-uor-is-identity-not-memory.md
    ├── ADR-002-saturation-is-routing-not-truth.md
    ├── ADR-003-crystallization-requires-certification.md
    ├── ADR-004-pama-controls-mutation-authority.md
    ├── ADR-005-codegenome-is-code-reality-substrate.md
    └── ADR-006-neurospace-is-runtime-memory-space.md

    The most important ADR is probably this:

ADR-001: UOR is not the memory system. UOR is the identity substrate.

That one prevents a ton of conceptual drift.

Then:

ADR-002: Saturation is not correctness.

That aligns directly with maurathat’s comment. They correctly separate σ from truth: σ should route, tier, evict, or propose crystallization, while certificates and verification confirm.

Then:

ADR-003: Crystallization is a governed transition, not a natural reward for repetition.

That connects EvolveAI, PAMA, UOR, and Neurospace. Memory can become durable only when lifecycle, saturation, provenance, and authority all agree.

Here is the clean mental model:

Raw Experience / Artifact
        ↓
UOR Identity
What is it? Can it be addressed?
        ↓
Observation / Evidence Layer
Who observed it? What supports it?
        ↓
Saturation / Relevance Layer
Should it persist, decay, route, or be rechecked?
        ↓
PAMA Governance Layer
Is the system allowed to promote, mutate, or canonize it?
        ↓
Crystallization / Certification
Does it become durable, canonical, or exact-address retrievable?
        ↓
Neurospace / Runtime Memory
How does the agent use it operationally?

The way I would consolidate this is not by merging repos. That would be a glorious act of self-harm with a README.

Instead, create a canonical planning/spec repo or a /docs/agentic-memory-doctrine/ package in one existing repo. Then every implementation points back to it.

Your implementation map should look like this:

Concept	Canonical Owner	Implementation Surface
Identity / addressability	UOR	UOR Framework, CodeGenome node identity
Saturation / decay	PRISM / memory lifecycle spec	EvolveAI, UOR issue #2, Neurospace
Memory metabolism	EvolveAI	L1/L2/L3, CMHL, REM synthesis
Runtime memory container	COREFORGE Neurospace / Vault	local encrypted memory, graph, context windows
Code reality graph	CodeGenome	overlays, confidence fusion, impact graph
Mutation authority	PAMA	promotion, mutation, canonicalization rules
Governance enforcement	Qor / FailSafe / Arbiter	approvals, evidence, policy boundaries
Decision continuity	Bicameral	durable decision state, drift detection

My recommendation: make a single canonical artifact called:

AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md

And define the doctrine in this order:

Definitions
Define memory unit, artifact, observation, fiber, saturation, crystallization, certification, mutation, provenance, canonical state, stale state, disputed state.
Layer model
Separate UOR, PRISM, EvolveAI, PAMA, CodeGenome, Neurospace, COREFORGE.
Lifecycle state machine
Draft states like:
Transient → Observed → Linked → Reinforced → Candidate → Pending Verification → Crystallized → Stale → Disputed → Corrected → Pruned.
Scoring model
Bring together:
EvolveAI MTS
UOR σ saturation
CMHL decay
CodeGenome confidence fusion
PAMA authority limits
Promotion rules
Explicitly forbid:
promotion by repetition alone
promotion by retrieval frequency alone
promotion by model confidence alone
promotion without provenance
promotion without governance authority
Conformance suite
Define test cases:
valuable memory persists
stale memory decays
access-spam does not crystallize
confidently-wrong memory does not become canonical
contradicted memory becomes disputed
verified memory can become exact-address retrievable

The hard truth: you probably do not need more theory right now. You need a canonical spine.

The spine should say:

Agentic memory is not just retrieval. It is governed state transition over addressable artifacts, scored by calibrated relevance, constrained by mutation authority, and confirmed by provenance/certification before becoming durable.

That sentence is the whole thing. Everything else plugs into it.

Your next best move is to create one umbrella issue or doc titled:

Consolidate Agentic Memory Systems Doctrine Across EvolveAI, CodeGenome, COREFORGE Neurospace, UOR, and PAMA

And use it to produce:

1. Canonical glossary
2. Layer model
3. Lifecycle state machine
4. Scoring and decay equations
5. Governance invariants
6. Repo implementation map
7. Conformance test plan
