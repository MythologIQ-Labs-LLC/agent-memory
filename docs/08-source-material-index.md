# Source Material Index

## Purpose

This index records the conceptual systems that fed the doctrine and points to the external research evidence used to challenge, extend, or validate those concepts.

It is not a complete bibliography. Internal architecture provenance and external scientific evidence are deliberately separated so a repo-specific idea does not quietly acquire the authority of neuroscience merely because both happen to use the word "memory."

For the interdisciplinary literature map, see `23-research-bibliography.md`.

Research in this repository is not decorative citation inventory. Its job is to improve, constrain, or falsify architectural claims.

## Primary source systems

| Source | Relevant doctrine area |
|---|---|
| UOR Framework issue 2 | saturation-derived decay, crystallization, O(1) exact-address transition |
| UOR issue comment by maurathat | decay calibration protocol, saturation as routing, certification distinction |
| EvolveAI | autopoietic memory, L1/L2/L3 tiers, CMHL, REM synthesis, Shadow Genome |
| CodeGenome | content-addressed code reality graph, overlays, confidence fusion, provenance |
| COREFORGE | local-first product runtime, Vault, Neurospace, governed agent modules |
| PAMA logic | mutation authority, adaptive guardrails, promotion and pruning policy |
| FailSafe / Arbiter | evidence capture, policy gates, approval boundaries, audit trails |
| Bicameral | decision continuity, drift detection, durable decisions |

## External research domains

| Domain | Questions it informs | Evidence map |
|---|---|---|
| Working memory | active state, bounded context, integration | `23-research-bibliography.md` |
| Episodic / semantic memory | events versus generalized knowledge | `23-research-bibliography.md` |
| Procedural memory | skills, runbooks, learned action patterns | `23-research-bibliography.md` |
| Prospective memory | future intentions and obligations | `23-research-bibliography.md` |
| Consolidation | durable transformation and abstraction | `23-research-bibliography.md` |
| Forgetting / interference | adaptive suppression, retrieval competition | `21-forgetting-consolidation-and-memory-metabolism.md` |
| Memory uncertainty / metacognition | stochastic retrieval, confidence, uncertainty-aware decisions | `23-research-bibliography.md`, `24-determinism-probability-and-governed-uncertainty.md` |
| Cellular / immune memory | inherited altered response without autobiographical recall | `20-memory-foundations-across-scales.md` |
| Agent-memory architectures | store/read/manage/control patterns | `22-agentic-memory-theory-and-development.md` |
| Adaptive memory control | learned retention, retrieval, consolidation, forgetting | `23-research-bibliography.md`, `24-determinism-probability-and-governed-uncertainty.md` |
| Agent-memory benchmarks | recall, updates, temporal reasoning, action | `23-research-bibliography.md` |
| Memory security | poisoning, leakage, context admission, unsafe composition | `22-agentic-memory-theory-and-development.md`, `24-determinism-probability-and-governed-uncertainty.md` |
| Runtime assurance / shielding | learned behavior inside separately enforced safety envelopes | `24-determinism-probability-and-governed-uncertainty.md` |
| Probabilistic calibration | whether numerical confidence corresponds to observed reliability | `03-scoring-and-decay.md`, `09-calibration-protocol.md` |

## Research accessibility preference

When two sources are comparably useful, prefer material contributors can inspect without proprietary access barriers.

Preferred source classes include:

- open-access journal articles
- PubMed Central and equivalent lawful public archives
- author-hosted manuscripts where lawful
- arXiv and other lawful preprint repositories
- open conference proceedings
- public technical reports
- open datasets and benchmark repositories
- standards and government publications

This is a preference, not a rule that lower-quality open material outranks stronger evidence.

A paywalled or proprietary source may inform research when lawfully available, but the doctrine should avoid depending materially on a claim that maintainers and contributors cannot independently inspect when a credible accessible alternative exists.

## Research evidence roles

Every external source should be used in one or more explicit roles:

```text
SUPPORT
Evidence consistent with an existing doctrine claim.

CHALLENGE
Evidence that weakens, limits, or contradicts a doctrine claim.

BOUNDARY
Evidence showing the claim is valid only under specific conditions.

MECHANISM
Evidence about how memory behaves in its native biological/cognitive/computational substrate.

FAILURE MODE
Evidence of a practical attack, brittleness, benchmark failure, or operational risk.

DESIGN CANDIDATE
A plausible engineering approach that has not yet earned doctrine status.
```

A source can play multiple roles.

## Research challenge rule

For consequential doctrine candidates, actively search for evidence that would make the claim less convenient.

For governed uncertainty, relevant challenges include:

- fixed deterministic thresholds can be brittle or miscalibrated
- stochastic or learned retrieval may outperform static rules
- adaptive defenses may be required when attacks are contextual or compositional
- probabilistic safety guarantees may sometimes be the strongest available formal guarantee
- exact replay of stochastic cognition may be impossible while policy and consequence replay remain achievable
- deterministic execution can reproduce the same wrong decision indefinitely

The purpose is not to manufacture false balance. It is to avoid mistaking architectural preference for evidence.

## UOR Framework

Relevant ideas:

- UOR identity as deterministic addressability
- saturation-derived decay
- crystallization as durable memory transition
- exact-address lookup after crystallization
- distinction between kernel identity and PRISM-style routing consumer

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/03-scoring-and-decay.md`
- `docs/adr/ADR-001-uor-is-identity-not-memory.md`
- `docs/adr/ADR-002-saturation-is-routing-not-truth.md`

## EvolveAI

Relevant ideas:

- autopoietic memory system
- 5-phase metabolic lifecycle
- L1 transient cache, L2 temporal graph, L3 UOR vault
- memory tier score
- cryptographic memory half-life
- Shadow Genome

Doctrine placement:

- `docs/02-lifecycle-state-machine.md`
- `docs/03-scoring-and-decay.md`
- `docs/06-conformance-test-plan.md`

## CodeGenome

Relevant ideas:

- canonical code reality graph
- BLAKE3 graph node identity
- observer separation
- provenance
- confidence fusion
- governance and evidence bundles

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/05-repo-implementation-map.md`
- `docs/adr/ADR-005-codegenome-is-code-reality-substrate.md`

## COREFORGE Vault / Neurospace

Relevant ideas:

- local-first memory runtime
- encrypted Vault storage
- knowledge graph and RAG recall
- context window assembly
- governed autonomy
- agent-facing runtime memory

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/04-governance-and-pama.md`
- `docs/adr/ADR-006-neurospace-is-runtime-memory-space.md`

## PAMA

Relevant ideas:

- proportional adaptive mutation authority
- promotion authority
- adaptive mutation constraints
- governance by risk, scope, reversibility, and evidence
- conversion of uncertain estimator outputs into explicit authority outcomes

Doctrine placement:

- `docs/04-governance-and-pama.md`
- `docs/24-determinism-probability-and-governed-uncertainty.md`
- `docs/adr/ADR-004-pama-controls-mutation-authority.md`
- `docs/adr/ADR-020-probabilistic-discovery-deterministic-governance.md`

## Evidence-transfer rule

When moving an idea between biological, cognitive, and agentic domains, classify the transfer:

```text
MECHANISM
Demonstrated in the original substrate.

FUNCTIONAL ANALOGY
A similar problem or role appears in another substrate.

ENGINEERING PRESCRIPTION
A software requirement justified independently by agent evidence, governance, or operational risk.

OPEN HYPOTHESIS
A design idea that still requires validation.
```

Do not turn functional analogy into claimed mechanism.

For example:

```text
Biological systems show adaptive forgetting.
```

may support the hypothesis that selective forgetting can help an artificial memory system.

It does **not** establish that a specific decay equation, vector-store TTL, or pruning algorithm is biologically correct.

Likewise:

```text
Human memory retrieval is probabilistic or uncertainty-aware.
```

may support preserving uncertainty in agent-memory reasoning.

It does **not** prove that a particular neural network, confidence threshold, or stochastic planner is the correct software implementation.

## Source-record fields

When a research claim materially affects doctrine, the research map should be able to record:

```text
source_ref
source_class
accessibility
publication_or_release_date
claim_used
role: support | challenge | boundary | mechanism | failure_mode | design_candidate
transfer_class: mechanism | functional_analogy | engineering_prescription | open_hypothesis
limitations
related_doctrine
related_fixture_or_test
reviewed_at
```

The repository need not turn into citation-management software. These fields define what should remain knowable when a source materially affects architecture.

## Doctrine challenge ledger

A doctrine candidate should retain both supporting and challenging evidence until the question is resolved or explicitly left open.

For governed uncertainty, the ledger should track at least:

```text
claim: uncertain inference may be probabilistic while authority remains bounded
supporting_evidence: ...
challenging_evidence: ...
known_boundary_conditions: ...
implementation_evidence: ...
conformance_evidence: ...
current_status: proposed | supported | revised | rejected | unresolved
```

This prevents the bibliography from becoming a one-way machine for proving whatever we already wanted to believe.

## Open consolidation questions

1. Should saturation be represented as one scalar or a vector of durability dimensions?
2. Should PAMA authority be evaluated before or after saturation reaches candidate threshold?
3. How should certification expire or be renewed?
4. How should Neurospace expose disputed memory to agents without allowing canonical misuse?
5. Which memory types require human approval before crystallization?
6. What is the minimum viable conformance fixture schema?
7. How should CodeGenome graph confidence flow into general agent memory saturation?
8. How should episodic memory be consolidated into semantic or procedural memory without losing behavior-changing exceptions?
9. Which forgetting mechanisms should be reversible, and which require irreversible deletion?
10. How should prospective memory connect to schedulers and automation systems without conflating memory with execution?
11. How should inherited memory identify acquisition mode and authority?
12. How should memory-guided action be benchmarked separately from conversational recall?
13. Which estimator outputs require formal calibration and which are better represented categorically?
14. When is deterministic policy too brittle and a formally bounded probabilistic guarantee more appropriate?
15. Which forms of stochastic action are acceptable after governance creates the permitted action set?
16. How should unsafe behavior emerging only from memory composition be represented and tested?
17. What evidence is sufficient to move ADR-020 from Proposed to Accepted?

## Maintenance rule

When a new memory-system idea appears, place it in one or more of these categories before adding implementation work:

```text
identity
evidence
source trust
encoding / admission
content type
saturation
uncertainty
lifecycle
consolidation
retrieval
governance
certification
runtime
correction
forgetting
inheritance
conformance
```

If the idea does not fit, determine whether the taxonomy is genuinely incomplete before creating a new component. Architectural sprawl remains undefeated at naming things humans find interesting.
