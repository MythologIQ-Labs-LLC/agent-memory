# Source Material Index

## Purpose

This index records the conceptual systems that fed the doctrine and points to the external research evidence used to challenge, extend, or validate those concepts.

It is not a complete bibliography. Internal architecture provenance and external scientific evidence are deliberately separated so a repo-specific idea does not quietly acquire the authority of neuroscience merely because both happen to use the word "memory."

For the interdisciplinary literature map, see [`23-research-bibliography.md`](23-research-bibliography.md).

For copyright, license, attribution, and reuse handling, see [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) and the machine-readable [`source registry`](../sources/source-registry.json).

Research in this repository is not decorative citation inventory. Its job is to improve, constrain, or falsify architectural claims.

## Public-source and reuse rule

> **When a source has a lawful, stable public locator, link the most specific authoritative artifact available. Public accessibility does not imply reuse permission.**

The repository distinguishes:

- **provenance**: where an idea, implementation, proposal, or evidence claim came from
- **accessibility**: whether contributors can inspect that source directly
- **rights status**: what license, permission, authorship, or uncertainty governs reuse of its expression
- **reuse mode**: citation, independent synthesis, author-originated reuse, licensed reuse, or permission-based reuse

A related public artifact must not be substituted for a private canonical source merely to make the index look complete.

Unknown rights status defaults to **citation and independent synthesis only**.

## Primary source systems

| Source | Public source / evidence | Access and reuse posture | Relevant doctrine area |
|---|---|---|---|
| UOR Framework issue #2 | [Thermodynamic Memory Lifecycle via Fiber Saturation](https://github.com/UOR-Foundation/UOR-Framework/issues/2) | Public; issue opened by Kevin R. Knapp. Record contributor-originated provenance separately from the repository's MIT software license. | saturation-derived decay, crystallization, O(1) exact-address transition |
| UOR issue comment by `maurathat` | [Decay Calibration Protocol comment](https://github.com/UOR-Foundation/UOR-Framework/issues/2#issuecomment-4765576921) | Public third-party comment; link and independently synthesize by default. Do not assume the repository MIT license governs the comment prose. | decay calibration protocol, saturation as routing, certification distinction |
| EvolveAI | [Autopoietic Memory Theory](https://github.com/MythologIQ-Labs-LLC/EvolveAI/blob/main/docs/AUTOPOIETIC_MEMORY_THEORY.md) · [repository](https://github.com/MythologIQ-Labs-LLC/EvolveAI) | Public; Apache-2.0 repository. Independent synthesis preferred; direct reuse must satisfy applicable attribution/NOTICE obligations. | autopoietic memory, L1/L2/L3 tiers, CMHL, REM synthesis, Shadow Genome |
| CodeGenome | [CodeGenome](https://github.com/MythologIQ-Labs-LLC/CodeGenome) | Public; MIT repository. Independent synthesis preferred; copies/substantial portions retain required notice. | content-addressed code reality graph, overlays, confidence fusion, provenance |
| COREFORGE | Canonical historical source is private. [GG-CORE](https://github.com/MythologIQ-Labs-LLC/GG-CORE) is a public successor/continuation, not the originating source. | Private historical provenance; do not expose private content or mislabel the successor as original provenance. GG-CORE is Apache-2.0. | local-first product runtime, Vault, Neurospace, governed agent modules |
| PAMA logic | No standalone canonical public locator verified | Rights/provenance unresolved at standalone-source level; Agent Memory expresses the governance doctrine independently. | mutation authority, adaptive guardrails, promotion and pruning policy |
| FailSafe / Arbiter | [VerdictArbiter implementation](https://github.com/MythologIQ-Labs-LLC/FailSafe/blob/main/FailSafe/extension/src/sentinel/VerdictArbiter.ts) · [repository](https://github.com/MythologIQ-Labs-LLC/FailSafe) | Public; Apache-2.0 repository. Link implementation directly; copied/adapted material must satisfy applicable license obligations. | evidence capture, policy gates, approval boundaries, audit trails |
| Bicameral | Canonical decision-continuity source is private; no public artifact is currently treated as a substitute | Private primary provenance; expose only independently stated high-level concepts unless a genuinely relevant public artifact becomes available. | decision continuity, drift detection, durable decisions |

### UOR provenance note

[UOR Framework issue #2](https://github.com/UOR-Foundation/UOR-Framework/issues/2) was opened by Kevin R. Knapp.

The **"thermodynamic ground state" framing as used in that memory-lifecycle proposal is recorded here as a Kevin R. Knapp contribution**. This is an authorship/provenance statement. It does not depend on claiming that the short phrase or underlying concept is exclusively protectable under copyright, trademark, patent, or another body of law.

The issue thread also contains third-party contributions. Those contributions retain their own source and rights posture and must not be treated as Kevin-originated merely because they appear in the same thread.

## External research domains

| Domain | Questions it informs | Evidence map |
|---|---|---|
| Working memory | active state, bounded context, integration | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Episodic / semantic memory | events versus generalized knowledge | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Procedural memory | skills, runbooks, learned action patterns | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Prospective memory | future intentions and obligations | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Consolidation | durable transformation and abstraction | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Forgetting / interference | adaptive suppression, retrieval competition | [`21-forgetting-consolidation-and-memory-metabolism.md`](21-forgetting-consolidation-and-memory-metabolism.md) |
| Memory uncertainty / metacognition | stochastic retrieval, confidence, uncertainty-aware decisions | [`23-research-bibliography.md`](23-research-bibliography.md), [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) |
| Cellular / immune memory | inherited altered response without autobiographical recall | [`20-memory-foundations-across-scales.md`](20-memory-foundations-across-scales.md) |
| Agent-memory architectures | store/read/manage/control patterns | [`22-agentic-memory-theory-and-development.md`](22-agentic-memory-theory-and-development.md) |
| Adaptive memory control | learned retention, retrieval, consolidation, forgetting | [`23-research-bibliography.md`](23-research-bibliography.md), [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) |
| Agent-memory benchmarks | recall, updates, temporal reasoning, action | [`23-research-bibliography.md`](23-research-bibliography.md) |
| Memory security | poisoning, leakage, context admission, unsafe composition | [`22-agentic-memory-theory-and-development.md`](22-agentic-memory-theory-and-development.md), [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) |
| Runtime assurance / shielding | learned behavior inside separately enforced safety envelopes | [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) |
| Probabilistic calibration | whether numerical confidence corresponds to observed reliability | [`03-scoring-and-decay.md`](03-scoring-and-decay.md), [`09-calibration-protocol.md`](09-calibration-protocol.md) |

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

**Open access is not itself a reuse license.** A source can be freely readable while still restricting reproduction of its prose, figures, tables, diagrams, or other expression.

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

Primary provenance:

- [UOR Framework issue #2](https://github.com/UOR-Foundation/UOR-Framework/issues/2)
- [Source-rights record](../sources/source-registry.json) `uor-issue-2-kevin-knapp`

Relevant ideas:

- UOR identity as deterministic addressability
- saturation-derived decay
- crystallization as durable memory transition
- exact-address lookup after crystallization
- distinction between kernel identity and PRISM-style routing consumer

Doctrine placement:

- [`01-layer-model.md`](01-layer-model.md)
- [`03-scoring-and-decay.md`](03-scoring-and-decay.md)
- [`adr/ADR-001-uor-is-identity-not-memory.md`](adr/ADR-001-uor-is-identity-not-memory.md)
- [`adr/ADR-002-saturation-is-routing-not-truth.md`](adr/ADR-002-saturation-is-routing-not-truth.md)

## EvolveAI

Primary provenance:

- [Autopoietic Memory Theory](https://github.com/MythologIQ-Labs-LLC/EvolveAI/blob/main/docs/AUTOPOIETIC_MEMORY_THEORY.md)
- [EvolveAI repository](https://github.com/MythologIQ-Labs-LLC/EvolveAI)

Relevant ideas:

- autopoietic memory system
- 5-phase metabolic lifecycle
- L1 transient cache, L2 temporal graph, L3 UOR vault
- memory tier score
- cryptographic memory half-life
- Shadow Genome

Doctrine placement:

- [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md)
- [`03-scoring-and-decay.md`](03-scoring-and-decay.md)
- [`06-conformance-test-plan.md`](06-conformance-test-plan.md)

## CodeGenome

Primary provenance:

- [CodeGenome repository](https://github.com/MythologIQ-Labs-LLC/CodeGenome)

Relevant ideas:

- canonical code reality graph
- BLAKE3 graph node identity
- observer separation
- provenance
- confidence fusion
- governance and evidence bundles

Doctrine placement:

- [`01-layer-model.md`](01-layer-model.md)
- [`05-repo-implementation-map.md`](05-repo-implementation-map.md)
- [`adr/ADR-005-codegenome-is-code-reality-substrate.md`](adr/ADR-005-codegenome-is-code-reality-substrate.md)

## COREFORGE Vault / Neurospace

Canonical historical provenance is private. [GG-CORE](https://github.com/MythologIQ-Labs-LLC/GG-CORE) is a public successor/continuation and may be used for current public implementation context, but it must not be presented as the originating COREFORGE source.

Relevant ideas:

- local-first memory runtime
- encrypted Vault storage
- knowledge graph and RAG recall
- context window assembly
- governed autonomy
- agent-facing runtime memory

Doctrine placement:

- [`01-layer-model.md`](01-layer-model.md)
- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`adr/ADR-006-neurospace-is-runtime-memory-space.md`](adr/ADR-006-neurospace-is-runtime-memory-space.md)

## PAMA

No standalone canonical public locator has been verified. Agent Memory therefore records the conceptual provenance without inventing a public source and expresses the doctrine independently.

Relevant ideas:

- proportional adaptive mutation authority
- promotion authority
- adaptive mutation constraints
- governance by risk, scope, reversibility, and evidence
- conversion of uncertain estimator outputs into explicit authority outcomes

Doctrine placement:

- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md)
- [`adr/ADR-004-pama-controls-mutation-authority.md`](adr/ADR-004-pama-controls-mutation-authority.md)
- [`adr/ADR-020-probabilistic-discovery-deterministic-governance.md`](adr/ADR-020-probabilistic-discovery-deterministic-governance.md)

## FailSafe / Arbiter

Primary provenance:

- [VerdictArbiter implementation](https://github.com/MythologIQ-Labs-LLC/FailSafe/blob/main/FailSafe/extension/src/sentinel/VerdictArbiter.ts)
- [FailSafe repository](https://github.com/MythologIQ-Labs-LLC/FailSafe)

Relevant ideas:

- evidence capture
- policy gates
- approval boundaries
- verdict arbitration
- audit trails

Agent Memory independently expresses the governance doctrine. Directly copied or adapted Apache-2.0 material would require the applicable attribution, license, NOTICE, and modification obligations to be recorded and satisfied.

## Bicameral

The canonical decision-continuity implementation source is currently private. Existing public Bicameral repositories are not treated as provenance substitutes unless a specific public artifact directly supports the cited doctrine.

Relevant ideas:

- decision continuity
- drift detection
- durable decisions
- supersession and rationale preservation

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

When source material is materially reused rather than merely cited or independently synthesized, the rights record should additionally retain:

```text
public_url
copyright_owner_or_originator
license_or_rights_status
license_url_or_permission_ref
reuse_mode
material_reused
attribution_required
notice_required
modification_notice_required
reuse_basis
verified_at
```

The repository need not turn into citation-management software. It does need enough evidence to distinguish research provenance from permission to copy.

Primary rights records live in [`../sources/source-registry.json`](../sources/source-registry.json) and are validated against [`../schemas/source-record.schema.json`](../schemas/source-record.schema.json).

External research listed in [`23-research-bibliography.md`](23-research-bibliography.md) defaults to citation and independent synthesis unless material reuse is explicitly registered.

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
18. Which external sources currently require explicit reuse-rights review because repository content moved beyond citation or independent synthesis?

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

Then apply the source-rights gate:

1. link the most specific lawful public source when one exists
2. identify whether the source is public, private, a successor, or lacks a public locator
3. separate provenance from reuse rights
4. default unknown rights to citation and independent synthesis
5. register any material quotation, adaptation, or copy before merge
6. preserve applicable attribution, notice, and modification obligations
7. never substitute an adjacent public artifact for private canonical provenance

If the idea does not fit the architecture taxonomy, determine whether the taxonomy is genuinely incomplete before creating a new component. Architectural sprawl remains undefeated at naming things humans find interesting.
