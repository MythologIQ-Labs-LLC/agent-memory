# PRD-001: Configurable Agent Memory Runtime

Status: **Draft**

## Product intent

Build the smallest real Agent Memory runtime that proves the architecture as a governed memory system rather than a collection of schemas and adapters.

The runtime must sit between an agent runtime and configurable memory technologies while preserving Agent Memory's own authority, lifecycle, provenance, scope, recall-admission, and evidence semantics.

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
    +-- module registry / routing / configuration
    +-- durable governance metadata
    +-- evidence / receipts
    |
    +--> memory modules / substrates
    |
    +--> governance peer adapters
             |
             +--> DashClaw / AGT / other peers
```

## Problem

The repository already proves many isolated architectural boundaries, but a production-shaped user story requires one coherent runtime that can:

- accept memory candidates from an agent;
- classify and govern consequential mutation;
- place/represent memory in configured modules;
- persist enough governance metadata to survive restart;
- retrieve candidates from one or several modules;
- govern admission into later context;
- correct, supersede, delete, rebuild, and migrate state;
- interoperate with external agent-governance peers without surrendering memory semantics;
- reconstruct why later behavior changed.

Without this runtime shape, integrations risk proving adapters rather than proving Agent Memory.

## Primary users

### Agent/runtime developer

Needs a stable API for storing, correcting, recalling, and forgetting governed memory without knowing which backend implements each memory capability.

### System operator

Needs to configure modules, scopes, failure postures, migration/rebuild policy, and governance peers with deterministic validation.

### Human authority / user

Needs meaningful recommendations and impact previews for consequential structural, scope, correction, or destructive changes without being interrupted for safe low-impact maintenance.

### Module developer

Needs a bounded contract for contributing storage, retrieval, representation, structural, lifecycle, or external-memory capabilities without acquiring Agent Memory authority.

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
- inspect configured module posture.

The API must distinguish proposal, decision, approval, commit, and recall evidence.

### R2. Module registry and capability discovery

The runtime must load one or more module profiles and expose their declared capabilities, versions, canonical/derived posture, scope behavior, currentness semantics, correction/deletion behavior, failure posture, and migration/rebuild support.

A module must not be usable merely because it imports successfully.

### R3. Configurable routing

Routing must be based on memory characteristics and deployment policy rather than hard-coded backend-to-tier assignments.

A memory may be routed to multiple modules when their roles are distinct and compatible.

### R4. Canonical state authority

The runtime must have an explicit owner for canonical logical memory state and governance metadata.

No derived index, graph projection, embedding store, or remote module may become canonical by accident.

### R5. Governed structural mutability

Implement ADR-032.

The system may receive structural proposals from learned or deterministic components. The commit path must classify the change using deterministic policy and either:

- autonomously commit a bounded S0/S1 change; or
- require explicit authorized human decision for S2/S3 changes.

Probabilistic estimates may not be the structural commit authority.

### R6. Durable governance metadata

Process restart must not reset state required to enforce currentness, scope, supersession, rejection, authority, or lifecycle rules.

At minimum, restart-safe state must reconstruct whichever implementation-specific equivalents are required for:

- memory logical identity/current version;
- current/superseded mapping;
- state/version counters or equivalent concurrency identity;
- scope/isolation bindings;
- rejection/readmission state;
- tombstone/deletion obligations;
- schema/module/profile versions affecting interpretation;
- outstanding migration/rebuild obligations;
- receipt/provenance linkage sufficient for reconstruction.

### R7. Governed recall

Module retrieval returns candidates, not admitted context.

Recall admission must re-check currentness, scope/isolation, lifecycle, sensitivity/purpose policy, and relevant authority/context constraints before memory can influence the agent.

### R8. External governance peer adapters

The runtime must support optional peer governance adapters without placing consumer-specific policy vocabulary into canonical core.

DashClaw is the first required proof.

### R9. Correction and supersession

A correction must preserve historical reconstruction while removing superseded state from current admission.

### R10. Deletion and residue

Successful deletion from one module must not imply lifecycle completion. The runtime must track declared derived/module residue and report incomplete forgetting honestly.

### R11. Observability and evidence

For a consequential memory path, an operator must be able to reconstruct:

```text
runtime request
memory proposal
module/routing decision
PAMA decision
external governance decision/approval where applicable
commit/refusal
module consequences
current state
later recall/admission
agent-visible memory reference
```

### R12. Deterministic configuration validation

Unsupported module combinations, version mismatches, ambiguous canonical ownership, unsafe writable duplication, or unavailable required dependencies must fail explicitly.

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
    +-- simple explicit/file or local canonical store
    +-- Graphiti/Kuzu optional graph-derived module
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

## Module conformance workload

Once the v0 runtime passes, rerun the same behavioral workload while changing module composition.

Examples:

- replace graph implementation;
- add/remove vector retrieval;
- add a JEPA-style representation module;
- add EvolveAI lifecycle capability;
- add CodeGenome structural-memory capability for a code-domain fixture;
- wrap an external memory system.

The acceptance behavior must remain invariant where the changed module does not legitimately alter semantics.

## Structural-mutation UX requirements

For S2/S3 proposals, present a human decision package containing:

- recommendation;
- why the change was proposed;
- exact semantic diff;
- affected memory/scope count;
- dependent modules/consumers;
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
- process restart preserves governance-currentness behavior;
- corrections supersede rather than silently overwrite history;
- module replacement does not change logical identity without an explicit migration;
- decision evidence is never misreported as execution evidence.

Optimization metrics after hard gates:

- recall latency;
- mutation latency;
- module rebuild cost;
- operator interruption rate;
- storage overhead of governance metadata;
- migration time;
- module failure recovery time.

## Out of scope for v0

- universal hosted multi-tenant control plane;
- training a new foundation model;
- selecting one canonical graph/vector/latent technology;
- automatic S2/S3 structural migration;
- making EvolveAI or CodeGenome mandatory;
- AGT/ACS as the first integration target;
- precedent/context governance input before the DashClaw verdict seam is proven.

## Release gates

### Gate A: architecture contract

- RFC-001 reviewed;
- ADR-032 integrated;
- module/configuration contract defined;
- canonical ownership rules explicit.

### Gate B: minimal runtime

- mutation + recall APIs executable;
- persistent canonical and governance state;
- deterministic config validation;
- one derived module profile.

### Gate C: governance peer proof

- DashClaw v1 external-verdict integration passes the real memory workload;
- decision/approval/commit evidence remains distinct.

### Gate D: restart and correction proof

- restart-safe currentness;
- correction/supersession across restart;
- stale replay refusal.

### Gate E: module portability proof

- at least two materially different module compositions pass the same acceptance contract;
- removal/rebuild and failure posture proven.

## Dependencies

- #274 modular-memory program;
- #275 first-party module comparison;
- #276 logical-state conclusion;
- #279 DashClaw provider integration;
- ADR-020 governed uncertainty;
- ADR-022 isolation domains;
- ADR-028 implementation portability;
- ADR-032 governed mutable memory structure.
