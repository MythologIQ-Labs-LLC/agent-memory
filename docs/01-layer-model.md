# Layer Model

## Intent

The layer model prevents conceptual drift by assigning each semantic responsibility a clear boundary.

The most important boundary is this:

```text
identity is identity
saturation is lifecycle scoring
certification is confirmation
PAMA is authority
runtime memory is operational use
```

A second boundary is equally important:

**Probabilistic or learned components may estimate what is likely, relevant, conflicting, stale, useful, or risky. They do not acquire authority from those estimates. Consequential memory transitions occur only through deterministic or formally bounded governance.**

A third ownership boundary is now explicit:

```text
implementation ancestry
    !=
permanent runtime ownership
```

Agent Memory owns the generic memory responsibilities described by these layers. EvolveAI, CodeGenome, COREFORGE, UOR-derived work, and other prior systems may supply implementation ancestry, domain observations, optional interoperability primitives, or test evidence without becoming the permanent owner of the generic capability.

See [`05-repo-implementation-map.md`](05-repo-implementation-map.md), [`39-implementation-ownership-map.md`](39-implementation-ownership-map.md), and [ADR-036](adr/ADR-036-same-owner-components-are-first-party-modules.md).

## Relationship to the Cognitive Mesh architecture

[ADR-035](adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md) establishes the accepted system-level topology above this responsibility model. The layers below remain canonical semantic responsibility boundaries within that accepted three-plane composition.

The models answer different questions:

```text
layer model
  -> what semantic responsibility is being exercised?

ADR-035 planes
  -> where does that responsibility participate in persistent cognition?

component/capability model
  -> which native implementation performs the responsibility at what proven maturity?
```

They must not be collapsed into one taxonomy.

The accepted mapping is:

```text
COGNITIVE PLANE
  Cognitive Mesh
  Saturation / lifecycle routing
  Lifecycle state machine
  Runtime memory / working cognition
  Consolidation / abstraction
  Procedural memory
  predictive / metacognitive signals

REALITY PLANE
  Domain Reality Graphs
  Code Reality Graph / code-domain evidence
  future environment/task/social/organizational graphs

AUTHORITY PLANE
  PAMA governance
  certification / crystallization
  governed recall admission
  correction / dispute consequence
  scope / isolation / deletion / inheritance authority

CROSS-CUTTING
  Identity substrate
  Evidence and provenance
  Conformance and calibration
```

This mapping does not grant a plane or module exclusive ownership of a capability. ADR-033 remains controlling:

```text
module identity != component identity
component identity != capability identity
```

EvolveAI and CodeGenome remain important first-party implementation ancestry under ADR-036. EvolveAI contributes proven or materially implemented lifecycle/metabolism/retrieval mechanisms worth harvesting. CodeGenome contributes code-domain reality evidence and generic graph/vector/evaluation mechanisms worth harvesting. Work adopted from either becomes Agent Memory functionality rather than preserving the originating repository as a mandatory runtime boundary.

The Cognitive Mesh is not a ninth memory layer or a universal database schema. It is the shared identity-and-handoff substrate through which typed cognitive objects may participate in several bounded responsibilities while retaining provenance, uncertainty, scope, lifecycle posture, and authority semantics.

## Layer 1: Identity substrate

### Canonical owner

Agent Memory identity contract.

Optional mechanisms may include UOR-derived exact references, content addressing, or another implementation that preserves deterministic identity semantics.

### Responsibility

- assign stable identity to artifacts;
- support deterministic resolution;
- preserve addressability across tools;
- enable exact lookup when memory requires exact identity.

### Must not do

- decide truth;
- decide lifecycle permanence;
- replace evidence;
- replace certification.

## Layer 2: Evidence and provenance

### Canonical owner

Agent Memory evidence and provenance contracts.

CodeGenome observations, EvolveAI traces, FailSafe/Arbiter receipts, COREFORGE lineage, and source-specific observers may contribute evidence.

### Responsibility

- record who observed what;
- attach evidence to claims;
- track creation and mutation history;
- preserve witness material through summaries and transformations;
- identify the method, model, rule set, or observer that produced probabilistic estimates used downstream.

### Must not do

- promote memories by evidence volume alone;
- treat model confidence as verification;
- collapse provenance into a summary without retaining source links;
- represent an estimated probability as deterministic evidence.

## Layer 3: Saturation and lifecycle routing

### Canonical owner

Agent Memory Cognitive Metabolism / lifecycle-routing machinery.

EvolveAI decay, tier-routing, consolidation, and crystallization mechanisms are implementation ancestry and test-oracle material, not permanent runtime ownership.

### Responsibility

- compute calibrated persistence pressure;
- route memory among lifecycle/storage postures where the implementation uses tiers;
- propose crystallization candidates;
- adjust decay under contextual pressure;
- identify stale, disputed, or prunable objects;
- preserve uncertainty and calibration metadata when routing depends on probabilistic or learned estimators.

### Control character

This layer may be probabilistic, heuristic, learned, or hybrid.

Its outputs are **proposals and estimates**, not authority grants.

### Must not do

- claim correctness;
- grant permanence without certification;
- crystallize access-spam;
- treat repetition as durability;
- convert a score, probability, ranking, or learned action directly into an irreversible transition.

## Layer 4: Lifecycle state machine

### Canonical owner

Agent Memory lifecycle engine.

EvolveAI and COREFORGE lifecycle implementations are ancestry that may inform native implementation.

### Responsibility

- manage memory states;
- perform decay, reinforcement, dispute, correction, reconciliation, and pruning;
- preserve audit trail for state transitions;
- validate that requested transitions are legal from the current state;
- separate transition proposal from transition commit.

### Control character

The state-transition contract should be deterministic for a fixed current state, authorized transition, policy version, and committed inputs.

Probabilistic systems may propose a transition. They must not bypass transition validity or authority checks.

### Must not do

- skip governance gates during promotion;
- mutate state without authority;
- erase disputed history.

## Layer 5: PAMA governance

### Canonical owner

Agent Memory PAMA.

FailSafe, Arbiter, or other enforcement peers may further constrain or attest to consequences without becoming PAMA's semantic owner.

### Responsibility

- define mutation authority;
- evaluate consequence/risk posture;
- control promotion and demotion;
- require approval when evidence or authority is insufficient;
- preserve adaptive constraints;
- map uncertain evidence and estimator outputs into a finite policy-defined authority outcome.

### Control character

For a fixed policy snapshot and reconstructable input record, the authority envelope must be deterministic or formally bounded.

A probabilistic estimate may influence the decision, but it must not define its own permission to mutate memory.

### Must not do

- allow high-confidence autonomous mutation in high-risk domains without explicit authority;
- allow agents to rewrite durable memory without ledgered correction;
- use stochastic choice to escape a blocked or review-required authority outcome.

## Layer 6: Certification and crystallization

### Canonical owner

Agent Memory certification/crystallization contract and native governance path.

External approval or enforcement systems may provide bounded evidence or additional constraints.

### Responsibility

- confirm that a memory may become durable;
- verify identity, provenance, evidence, and authority;
- attach certificate or approval records;
- move objects to exact-address durable lookup when permitted;
- bind certification to memory state, evidence set, policy version, scope, and estimator context when probabilistic evidence materially affected promotion.

### Control character

Certification is a governed consequence. Acceptance criteria must be explicit and reproducible or formally specified within a bounded approval protocol.

### Must not do

- certify without scoped evidence;
- treat a certificate as eternal truth;
- block correction pathways.

## Layer 7: Runtime memory space

### Canonical owner

Agent Memory runtime memory and context-assembly machinery.

COREFORGE Vault/Neurospace is product/runtime ancestry and a future downstream consumer target, not the permanent owner of this generic layer.

### Responsibility

- assemble governed context;
- serve agent recall;
- perform exact, lexical, relational, vector, temporal, or graph candidate retrieval as implemented;
- enforce privacy, scope, tenancy, currentness, dispute, and lifecycle boundaries;
- expose memory through governed consumer workflows;
- preserve route provenance and estimator identity when candidate generation is probabilistic.

### Control character

Candidate retrieval and ranking may be probabilistic.

Scope, tenancy, sensitivity, certification/currentness state, and policy exclusions must still be enforced before retrieved memory enters active context.

A runtime may choose among multiple already-permitted candidates or strategies only inside the permitted action set.

### Must not do

- treat operational utility as canonical truth;
- hide agent memory mutation from users or ledgers;
- inject a highly relevant memory that violates scope or authority constraints;
- make a retrieval ancestor or downstream product the implicit owner of generic Agent Memory recall.

## Layer 8: Domain reality graphs

### Canonical owner

Agent Memory Reality Graph framework.

Specialized systems may supply domain observations. CodeGenome may continue to supply code-domain structure, evidence, freshness, and relationships without becoming the generic owner of graph/vector memory.

### Responsibility

- represent domain-specific reality as graph structure;
- fuse observations from multiple sources;
- retain confidence and provenance;
- expose query and traversal primitives;
- distinguish exact graph facts from inferred edges, ranked hypotheses, or probabilistic relations.

### Control character

Graph identity, schema, and committed relations should remain reproducible. Relation discovery, confidence fusion, entity resolution, and ranking may be probabilistic when provenance and uncertainty are preserved.

### Must not do

- allow one observer to become canonical without evidence/currentness semantics;
- hide confidence conflicts;
- import a domain-specific ontology as the universal Cognitive Mesh.

## Control-character map

| Responsibility | Typical control character | Why |
|---|---|---|
| identity and exact reference | deterministic | ambiguity here corrupts every later decision |
| schema and transition validity | deterministic | invalid states must not become policy-dependent guesses |
| evidence interpretation | probabilistic or hybrid | evidence can be incomplete, noisy, or contradictory |
| confidence, trust, relevance, saturation | probabilistic, learned, heuristic, or hybrid | these are estimates, not authority |
| authority envelope | deterministic or formally bounded | permissions and prohibitions must be reconstructable |
| certification consequence | deterministic or explicitly governed approval | durable promotion requires accountable consequence |
| retrieval candidate generation | deterministic, probabilistic, or hybrid by route | semantic/contextual relevance can be uncertain while exact routes are deterministic |
| recall-time scope enforcement | deterministic or formally bounded | high relevance does not override access policy |
| choice among already-permitted actions | optionally stochastic | uncertainty may remain useful inside the safe action set |
| ledger and state-transition receipt | deterministic | accountability requires replayable evidence |

## Governed uncertainty boundary

The canonical flow is:

```text
observation / query
        |
        v
probabilistic or learned interpretation
(confidence, relevance, trust, contradiction, risk, candidate ranking)
        |
        v
explicit governance envelope
(scope, authority, transition validity, policy, sensitivity, reversibility)
        |
        v
permitted action set
        |
        +--> zero actions: block / abstain / escalate
        |
        +--> one action: commit defined consequence
        |
        +--> multiple actions: deterministic or stochastic selection may occur inside set
        |
        v
state transition + audit receipt
```

Required properties:

1. Estimator output must identify what it measures and how it was produced when it materially affects a consequential transition.
2. Estimator confidence must not be reused as mutation authority.
3. A blocked action must remain blocked regardless of how confidently a probabilistic component proposes it.
4. Policy outcome and estimator output must remain separately inspectable.
5. Consequential commits must bind to the policy version and state snapshot under which they were authorized.
6. If required authority inputs cannot be reconstructed for a high-consequence action, the system should abstain, block, or escalate rather than infer permission.

## Boundary table

| Question | Correct layer |
|---|---|
| What is this object? | Identity substrate |
| Why do we believe this claim? | Evidence and provenance |
| How likely, relevant, stale, or persistent does it appear? | Saturation / epistemic routing |
| Is the proposed transition legal from this state? | Lifecycle state machine |
| Can the memory change? | PAMA governance |
| Can this become durable? | Certification and crystallization |
| How does the agent use it now? | Runtime memory space |
| What is true or hypothesized about a domain? | Domain reality graph |

## Anti-collapse rules

1. Do not collapse identity into memory.
2. Do not collapse saturation into truth.
3. Do not collapse confidence into certification.
4. Do not collapse runtime utility into permanence.
5. Do not collapse mutation capability into mutation authority.
6. Do not collapse probabilistic inference into permission.
7. Do not collapse deterministic execution into correctness.
8. Do not collapse policy outcome and estimator output into one opaque score.
9. Do not collapse the Cognitive Mesh into a universal truth store or implementation-specific ontology.
10. Do not collapse module identity, component identity, and capability identity.
11. Do not collapse implementation ancestry into permanent runtime ownership.
12. Do not collapse a specialized domain producer into the owner of generic memory machinery.
