# PRD-001: Configurable Agent Memory Runtime

Status: **Draft**

## Product intent

Build the smallest real Agent Memory runtime that proves the architecture as a governed memory system rather than a collection of schemas and adapters.

The runtime must sit between an agent runtime and configurable memory technologies while preserving Agent Memory's own authority, lifecycle, provenance, scope, recall-admission, and evidence semantics.

Memory technologies participate as **components** exposing one or more independently qualified **capabilities**.

The product boundary is:

```text
Agent Runtime
    |
    v
Agent Memory Runtime
    |
    +-- PAMA / governance
    +-- lifecycle / provenance / currentness
    +-- mutation + recall APIs
    +-- component + capability registry
    +-- capability routing / configuration
    +-- durable governance metadata
    +-- evidence / receipts
    |
    +--> memory components / substrates
    |       +--> capabilities[]
    |       +--> maturity/evidence per capability
    |
    +--> governance peer adapters
             |
             +--> DashClaw / AGT / other peers
```

## Problem

The repository already proves many isolated architectural boundaries, but a production-shaped user story requires one coherent runtime that can:

- accept memory candidates from an agent;
- classify and govern consequential mutation;
- determine required memory capabilities from policy and workload characteristics;
- resolve those capabilities to configured components at sufficient maturity;
- place/represent memory through one or several capabilities;
- persist enough governance metadata to survive restart;
- retrieve candidates from one or several components/capabilities;
- govern admission into later context;
- correct, supersede, delete, rebuild, and migrate state;
- interoperate with external agent-governance peers without surrendering memory semantics;
- reconstruct why later behavior changed.

Without this runtime shape, integrations risk proving adapters or product-specific pipelines rather than proving Agent Memory.

## Primary users

### Agent/runtime developer

Needs a stable API for storing, correcting, recalling, and forgetting governed memory without knowing which component implements each memory capability.

### System operator

Needs to configure components, capabilities, minimum maturity, precedence/composition, scopes, failure postures, migration/rebuild policy, and governance peers with deterministic validation.

### Human authority / user

Needs meaningful recommendations and impact previews for consequential structural, scope, correction, or destructive changes without being interrupted for safe low-impact maintenance.

### Component developer

Needs a bounded contract for contributing one or several storage, retrieval, graph, representation, structural, lifecycle, or external-memory capabilities without acquiring Agent Memory authority.

## Core product requirements

### R1. Stable Agent Memory API

Expose bounded operations for at least:

- propose memory;
- commit governed mutation;
- correct/supersede memory;
- recall current admissible memory;
- inspect history/provenance;
- request forgetting/deletion;
- inspect decision/receipt evidence;
- inspect configured component/capability posture.

The API must distinguish proposal, decision, approval, commit, and recall evidence.

### R2. Component registry and capability discovery

The runtime must load one or more component profiles and expose:

```text
component identity + version
configuration/profile version
deployment/failure posture
capabilities[]
```

Each capability must independently declare at least:

- capability identity/version;
- maturity;
- maturity/evidence references where applicable;
- canonical/derived/historical/learned posture;
- scope/isolation behavior;
- read/write/candidate behavior;
- currentness/invalidation semantics;
- correction/deletion behavior;
- failure posture where capability-specific;
- migration/rebuild support.

A component must not be usable merely because it imports successfully.

### R3. Capability maturity

The runtime must distinguish at least:

```text
declared
implemented
runtime_wired
evidence_proven
reference_qualified
```

A route requiring a capability at one maturity level must reject an implementation below that level.

Component-level release/version must not implicitly promote capability maturity.

### R4. Configurable capability routing

Routing must be based on memory characteristics, capability requirements, minimum maturity, and deployment policy rather than hard-coded backend-to-tier assignments.

A memory may use several capabilities from one component or from several components.

One component may provide several capabilities. Several components may provide the same capability.

When overlap exists, deterministic configuration must define precedence, composition, or explicit ambiguity failure.

### R5. Canonical state authority

The runtime must have an explicit owner for canonical logical memory state and governance metadata.

No derived index, graph projection, embedding store, remote component, or capability implementation may become canonical by accident.

Overlapping writable capabilities must not create dual authority.

### R6. Governed structural mutability

Implement ADR-032.

The system may receive structural proposals from learned or deterministic components. The commit path must classify the change using deterministic policy and either:

- autonomously commit a bounded S0/S1 change; or
- require explicit authorized human decision for S2/S3 changes.

Probabilistic estimates may not be the structural commit authority.

### R7. Durable governance metadata

Process restart must not reset state required to enforce currentness, scope, supersession, rejection, authority, or lifecycle rules.

At minimum, restart-safe state must reconstruct whichever implementation-specific equivalents are required for:

- memory logical identity/current version;
- current/superseded mapping;
- state/version counters or equivalent concurrency identity;
- scope/isolation bindings;
- rejection/readmission state;
- tombstone/deletion obligations;
- schema/component/capability/profile versions affecting interpretation;
- selected capability implementations where needed for reconstruction;
- outstanding migration/rebuild obligations;
- receipt/provenance linkage sufficient for reconstruction.

### R8. Governed recall

Component retrieval returns candidates, not admitted context.

Recall admission must re-check currentness, scope/isolation, lifecycle, sensitivity/purpose policy, and relevant authority/context constraints before memory can influence the agent.

The system must preserve which component and capability produced each candidate.

### R9. External governance peer adapters

The runtime must support optional peer governance adapters without placing consumer-specific policy vocabulary into canonical core.

DashClaw is the first required proof.

### R10. Correction and supersession

A correction must preserve historical reconstruction while removing superseded state from current admission.

Affected derived capabilities must be invalidated, rebuilt, or explicitly marked stale according to their contract.

### R11. Deletion and residue

Successful deletion from one component/capability must not imply lifecycle completion. The runtime must track declared derived/component residue and report incomplete forgetting honestly.

### R12. Observability and evidence

For a consequential memory path, an operator must be able to reconstruct:

```text
runtime request
memory proposal
required capability set
component/capability resolution
capability maturity/version evidence
PAMA decision
external governance decision/approval where applicable
commit/refusal
component consequences
current state
later recall candidates + producing capabilities
recall admission
agent-visible memory reference
```

### R13. Deterministic configuration validation

Unsupported component combinations, capability/version mismatches, maturity shortfalls, ambiguous canonical ownership, unsafe writable duplication, undefined overlap precedence, or unavailable required dependencies must fail explicitly.

Fallback must not silently reduce maturity, scope/isolation, canonical/derived posture, or governance requirements.

## Capability vocabulary requirements

The runtime must not collapse related capabilities merely because they use the same technology family.

At minimum the model must be capable of distinguishing concepts such as:

```text
graph storage
graph query/traversal
graph candidate retrieval
graph-augmented context assembly / GraphRAG

vector representation/storage
vector similarity
vector candidate retrieval

exact/content-addressed retrieval
context assembly
lifecycle maintenance
structural reasoning
```

Issue #291 owns the final representation-neutral vocabulary.

## First-party component posture

### EvolveAI

EvolveAI must be treated as a multi-capability candidate component, not merely a lifecycle module.

The initial #284 inventory identifies graph, vector, exact-retrieval, tiering, lifecycle, consolidation, failure-memory, persistence/audit, and GraphRAG-oriented capability surfaces at different maturity levels.

The runtime/profile must advertise only the maturity actually established for each capability. In particular, documented GraphRAG design and graph/vector implementation must not be misreported as an already reference-qualified end-to-end GraphRAG path.

### CodeGenome

CodeGenome must be treated as a multi-capability candidate component, not merely a graph module.

The initial #284 inventory identifies graph traversal, graph-derived context, impact analysis, embeddings, vector similarity, confidence/evidence fusion, provenance, multi-language extraction, MCP, and self-evaluation surfaces at different maturity levels.

Its embedding/k-nearest implementation must not be misreported as a fully integrated general vector-retrieval product path until runtime evidence establishes that claim.

## Minimal v0 deployment profile

The first runtime does not need glamorous infrastructure. It needs falsifiable behavior.

```text
Agent Runtime fixture
    |
Agent Memory runtime
    |
    +-- existing PAMA
    +-- existing GovernedMemoryAdapter semantics
    +-- durable governance metadata implementation
    +-- component/capability registry
    +-- deterministic capability resolution
    +-- simple explicit/file or local canonical capability
    +-- Graphiti/Kuzu optional graph-derived capability
    +-- governed recall
    +-- DashClaw external-verdict adapter
```

A model is optional. The acceptance suite must not require stochastic model behavior to pass.

## Canonical acceptance workload

Use the release-branch project-memory scenario established under #279:

1. Session A learns `release_branch = release`.
2. Agent Memory promotes it through governance and commits it.
3. Session B starts without Session A conversation state, recalls the memory, and forms a plan targeting `release`.
4. New authoritative evidence changes the value to `main`.
5. Agent Memory proposes a correction; DashClaw requires/records human approval where policy requires it.
6. Agent Memory revalidates current state and commits the correction as supersession.
7. Session C recalls only `main` as current and forms the corrected plan.
8. stale approval replay fails.
9. scope/authority expansion fails.
10. a foreign tenant/project cannot admit the memory.
11. restart occurs; current state, governance metadata, and recall behavior remain correct.

## Capability-composition conformance workload

Once the v0 runtime passes, rerun the same behavioral workload while changing component/capability composition.

Examples:

- replace graph implementation while retaining the same graph-candidate contract;
- add/remove vector retrieval;
- add a JEPA-style representation capability;
- use EvolveAI for temporal graph + lifecycle in one profile;
- use EvolveAI for vector + graph capabilities only when the advertised maturity permits it;
- use CodeGenome graph traversal plus vector-neighbor capability for a code-domain fixture;
- use different components for graph and vector capabilities;
- wrap an external memory system exposing several capabilities.

The acceptance behavior must remain invariant where the changed capability implementation does not legitimately alter semantics.

The suite must include overlap cases:

- two configured implementations satisfy the same capability with explicit precedence;
- two configured implementations satisfy the same capability without precedence and fail deterministically;
- a capability below required maturity is rejected;
- fallback cannot silently select a weaker capability posture.

## Structural-mutation UX requirements

For S2/S3 proposals, present a human decision package containing:

- recommendation;
- why the change was proposed;
- exact semantic diff;
- affected memory/scope count;
- dependent components/capabilities/consumers;
- migration and information-loss analysis;
- authority/isolation impact;
- rollback boundary;
- residue/rebuild requirements.

For autonomous S0/S1 changes, record the same class of evidence in a machine-readable receipt without forcing human interruption.

## Success metrics

Hard gates:

- zero unauthorized canonical mutations in adversarial cases;
- zero cross-tenant admitted-memory leaks;
- zero stale-decision commits;
- zero probabilistic structural self-authorization;
- zero silent capability-maturity downgrades;
- zero accidental provider selection under ambiguous overlap;
- process restart preserves governance-currentness behavior;
- corrections supersede rather than silently overwrite history;
- component/capability replacement does not change logical identity without an explicit migration;
- decision evidence is never misreported as execution evidence.

Optimization metrics after hard gates:

- recall latency;
- mutation latency;
- capability resolution latency;
- component rebuild cost;
- operator interruption rate;
- storage overhead of governance metadata;
- migration time;
- component failure recovery time.

## Out of scope for v0

- universal hosted multi-tenant control plane;
- training a new foundation model;
- selecting one canonical graph/vector/latent technology;
- automatic S2/S3 structural migration;
- making EvolveAI or CodeGenome mandatory;
- creating new proprietary memory repositories before #284/#286 establish a justified capability gap;
- AGT/ACS as the first integration target;
- precedent/context governance input before the DashClaw verdict seam is proven.

## Release gates

### Gate A: architecture contract

- RFC-001 reviewed;
- ADR-032 integrated;
- component/capability/configuration contract defined;
- capability maturity model defined;
- canonical ownership rules explicit.

### Gate B: minimal runtime

- mutation + recall APIs executable;
- persistent canonical and governance state;
- deterministic configuration validation;
- capability resolution executable;
- one derived capability profile.

### Gate C: governance peer proof

- DashClaw v1 external-verdict integration passes the real memory workload;
- decision/approval/commit evidence remains distinct.

### Gate D: restart and correction proof

- restart-safe currentness;
- correction/supersession across restart;
- stale replay refusal.

### Gate E: capability portability proof

- at least two materially different component/capability compositions pass the same acceptance contract;
- overlap resolution is deterministic;
- maturity gating is enforced;
- removal/rebuild and failure posture are proven.

### Gate F: first-party qualification

- EvolveAI and CodeGenome profiles advertise capabilities independently by earned maturity;
- graph/vector/GraphRAG claims match actual runtime evidence;
- first-party ownership grants no authority or conformance shortcut.

## Dependencies

- #274 modular-memory program;
- #275 first-party/external comparison;
- #276 logical-state conclusion;
- #279 DashClaw provider integration;
- #280 component/capability contract and routing;
- #284 capability inventory and gap analysis;
- #285 capability-oriented taxonomy correction;
- #286 external capability mapping;
- #287 capability maturity declarations;
- #289 first-party subsystem boundary analysis;
- #290 capability-based overlap resolution;
- #291 graph/vector/GraphRAG vocabulary;
- #292 EvolveAI qualification;
- #293 CodeGenome qualification;
- ADR-020 governed uncertainty;
- ADR-022 isolation domains;
- ADR-028 implementation portability;
- ADR-032 governed mutable memory structure.
