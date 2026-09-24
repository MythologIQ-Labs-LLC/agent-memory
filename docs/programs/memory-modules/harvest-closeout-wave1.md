# Harvest Closeout Matrix

Issue: #470  
RC umbrella: #410  
Agent Memory audit baseline: `92883979d990b9d92fe32c13f4c3b28978cd09ac`  
Status: **incomplete exhaustive closeout, evidence-bound dispositions recorded through CodeGenome and COREFORGE**

## Purpose

This document is the living harvest closeout required by #470.

The earlier native-harvest sequence completed important planned slices. It did not prove that every materially useful mechanism from Agent Memory ancestry and external peers had been absorbed, deliberately excluded, or bounded behind interoperability.

This matrix records exact source revisions for the surfaces actually inspected, maps them to current Agent Memory capability, and requires an explicit disposition for mechanisms that should not become native Agent Memory behavior.

This is not yet a closeout certificate.

## Decision rule

For every mechanism, choose one disposition:

```text
absorbed
partially_absorbed
intentionally_not_adopted
specialized_source_only
optional_interoperability
blocked_by_rights
obsolete_or_superseded
```

Adapter or comparator presence is not proof of native absorption.

The preferred destination for generic capability is:

```text
inspect / validate ancestry
  -> native Agent Memory implementation
  -> existing governance and authority boundaries
```

A source remains a runtime dependency only when interoperability itself is the intended boundary.

## Current source matrix

| Source | Exact inspected revision | Rights posture | Mechanism or lesson | Current Agent Memory posture | Required action |
|---|---|---|---|---|---|
| EvolveAI | `21161ce7b88dbffeb7ed59757b4d02d24a9c2acd` | same-owner first-party; public Apache-2.0 remains relevant to redistribution | decay, reinforcement, consolidation, prune/archive pressure, restart, vector and temporal behavior | **absorbed** for the native metabolism slice and major retrieval mechanisms | retain as ancestry and test oracle, not generic runtime dependency |
| EvolveAI Shadow Genome | `21161ce7b88dbffeb7ed59757b4d02d24a9c2acd` | same-owner first-party | typed failures, stable identity, recurrence counting, persistence, bounded capacity, similarity-based recurrence evidence | **absorbed** into native governed failure memory through #473 | retain as ancestry and test pressure only; direct `similarity -> Block` authority remains rejected |
| CodeGenome | `6dac705e137a3aea795163a766c263a38285416d` | same-owner first-party; public MIT remains relevant to redistribution | vector persistence/kNN, typed graph traversal, impact propagation, confidence fusion, experiment loop | **mixed final disposition**: generic retrieval/impact mechanics and evaluation loop absorbed; code blast radius specialized; noisy-OR evidence fusion intentionally not adopted as generic evidence qualification | retain CodeGenome as code-domain observation source and ancestry, not generic runtime dependency |
| COREFORGE | `43b423dbaf8ec1f4323f0556ed462cfa02405a22` | private same-owner first-party | Vault/NeuroSpace runtime memory, lineage, provider abstraction, context broker/packet, bundle assembly, product integration | **mixed final disposition**: generic memory/runtime/governance lessons absorbed or superseded; packet/bundle/cache/persona packaging remains downstream product behavior | migrate downstream toward Agent Memory canonical memory APIs; do not preserve EvolveAI/CodeGenome as generic memory owners |
| UOR Framework | `51c01382200b0179d6640b07e9c8119364ab69a1` | MIT at inspected main | deterministic identity and conformance lineage | **optional_interoperability** | keep identity lineage bounded; do not import lifecycle or PAMA semantics |
| uor-addr | `165b51e3e2113ee5d032730cde709335d4fe9b60` | external open-source profile already qualified separately | exact content references | **optional_interoperability** | existing optional profile remains appropriate; no ordinary runtime dependency |
| uor-r4 | `552d847d49fb263966165004b835f2f53cccaae1` | MIT | exact addressed/versioned memory experiments, keyed rebinding/overwrite pressure, unusually explicit matched controls and negative-result discipline | **intentionally_not_adopted** as a geometric model; research pressure remains useful | evaluate its long-horizon keyed rebinding/overwrite fixture shape as benchmark pressure without adopting geometric predictive claims |
| uor-foundry | `5b4711aed4fbb7da9d8b0aa04048a2b04713de4a` | root `Cargo.toml` declares `MIT OR Apache-2.0`; no root LICENSE was found in this inspection | scoped authority, replayable acceptance, exact producer identity, artifact handoff and conformance evidence | **blocked_by_rights** for direct code reuse; conceptual comparison only | confirm repository-level license distribution before copying code; independently synthesize any useful conformance lesson meanwhile |
| uor-jcs-nfc | `303591128094362857791930fdc12b73875d1ff6` | Apache-2.0 with NOTICE | pinned JSON canonicalization context, Unicode-version binding, refusal semantics, conformance vectors as oracle, mutation testing | **intentionally_not_adopted** at this provisional RC5 revision | watch for final publication; compare its canonicalization/version-binding lessons with existing Agent Memory canonical evidence paths before any adoption |
| uor-matmul | `3cc5882f210667f9ac00fd8c02c5b5957b493f5d` | MIT | exact arithmetic and conformance methodology, not generic memory semantics | **intentionally_not_adopted** | no Agent Memory implementation need identified; retain only methodological lessons if concrete evidence work benefits |
| Microsoft Agent Governance Toolkit | `e0574c1eb44a9b02f106e2b4c63fc60ec3c017ce` | MIT | runtime policy/enforcement, identity and audit boundary; absent/unconfigured/unavailable state distinctions | **optional_interoperability** | continue comparator/adapter posture; do not make AGT the source of PAMA authority |
| AgentTrust TRACE | `e3111c77b89cc9870ac7218936ab956ad77de6c9` | mixed license: normative specification under Community Specification License 1.0, source/SDK/tests/examples under Apache-2.0, non-spec docs under CC BY 4.0 | portable trust/attestation/action evidence | **optional_interoperability** | correct stale source-registry wording and execute version-exact qualification under #440 |
| Agent Manifest | `d66b6f0b18f3ca83cb93071257d8f5edce5ae850` | Apache-2.0 | deployment identity, checkpoint/delta evidence, appended-operation binding | **optional_interoperability** | #440 must qualify the intended package pair; explicitly test that memory delta evidence binds appended operations rather than only consistency/root state |

## Resolved native gap: negative/failure memory

Wave 1 originally identified one concrete generic gap: Agent Memory doctrine defined failure memory, but no native generic runtime equivalent to the EvolveAI Shadow Genome path was present.

PR #473 closed that implementation gap without copying Shadow Genome's authority shortcut. Native Agent Memory now owns:

- stable logical failure identity;
- typed failure revisions with observed, inferred, or hypothesis causal status;
- recurrence evidence that repeated recall cannot manufacture;
- correction, dispute, supersession, retraction, and tombstone behavior;
- scope-aware typed recall isolation;
- restart-safe owner state through `CheckpointedFailureMemory` composed with the existing restart runtime;
- adversarial evidence that similarity, severity, impact, and recurrence do not create action or mutation authority;
- bounded quality, performance, and governance reporting without an aggregate health score.

Exact evaluated PR head: `b0c9a3edd88c87070c949bd69359a042f6c30a80`.

The remaining claim boundary is intentional: the bounded benchmark does not claim that retrieving a failure memory automatically prevents a downstream action failure. Agent Memory supplies governed evidence; downstream execution remains separately governed.

The harvested shape is therefore:

```text
similarity / recurrence / severity
  -> evidence or proposal
  -> governed admission
  -> existing action / mutation authority
```

not:

```text
similarity -> Block
```

## CodeGenome final disposition

CodeGenome current main was inspected at `6dac705e137a3aea795163a766c263a38285416d`.

### Generic impact propagation: absorbed

CodeGenome's generic propagation mechanism starts from changed graph nodes, traverses in a declared direction, multiplies edge confidence along paths, and keeps the strongest propagated score. Its change detector composes this with code-specific changed-symbol discovery and process/blast-radius presentation.

Agent Memory #461 already harvested the generic mechanism into native typed graph retrieval:

```text
seed fact
  -> typed relation traversal
  -> outgoing / incoming / both direction
  -> path score = product of relation retrieval weights
  -> deterministic best path
  -> bounded depth / fan-out / candidate work
  -> candidate evidence
  -> governed final admission
```

That is the generic memory capability we actually need. It is intentionally named retrieval/path evidence rather than universal impact truth.

CodeGenome's higher-level blast-radius meaning remains code-domain semantics. `changed symbol -> affected process` is useful evidence that CodeGenome may continue to produce, but Agent Memory does not need to copy the code ontology to own generic relation propagation.

Disposition:

```text
generic weighted directional propagation -> absorbed in Agent Memory #461
code/process blast radius               -> specialized_source_only
confidence/criticality impact score     -> specialized_source_only
```

No new generic implementation issue is warranted for CodeGenome impact propagation.

### Noisy-OR confidence fusion: intentionally not adopted as generic evidence qualification

CodeGenome merges duplicate relation edges and combines path confidence using noisy-OR. That is useful inside its code-graph estimator, where confidence is a retrieval/graph signal.

Agent Memory has a stronger requirement at the governance/evidence boundary: repeated or correlated assertions must not become independent verification merely because several paths report them. The native evidence-qualification layer groups evidence by:

- derivation lineage;
- declared shared failure domain;
- identical deterministic procedure/input/version.

It also keeps evidence class and verification status separate.

A generic noisy-OR merge would therefore be actively dangerous if reused as evidence strength or authority without dependence proof. It can inflate correlated observations and make repetition resemble corroboration.

Disposition:

```text
CodeGenome noisy-OR in code-graph estimator -> valid specialized implementation
Agent Memory generic evidence fusion       -> intentionally_not_adopted
Agent Memory evidence dependence grouping  -> native stronger boundary
```

This does not prohibit a future retrieval-only estimator from using an explicitly qualified numerical fusion model. Such an estimator would still have `authority_effect = none` and would need dependence/calibration evidence of its own. No present gap requires one.

### Experiment/evaluation loop: absorbed at the generic memory level

CodeGenome's experiment loop was useful ancestry for continuous evaluation pressure. #465 now gives Agent Memory its own continuous retrieval/memory regression layer with fixture, runtime-configuration, route-profile, revision, and comparability binding.

Agent Memory does not need CodeGenome's code-specific experiment machinery as a runtime dependency.

Disposition: **absorbed** for the generic continuous memory-evaluation lesson.

## COREFORGE Vault / NeuroSpace final disposition

COREFORGE current main was inspected at `43b423dbaf8ec1f4323f0556ed462cfa02405a22`.

The current code confirms that Vault/NeuroSpace is not merely old documentation. It has executable provider, context-packet, broker, lineage, mutation-contract, bundle, assembler, cache, inspection, graph-overlay, and evaluation surfaces.

That makes it valuable ancestry. It does not make those surfaces the end-state generic memory owner.

### VaultMemoryProvider: obsolete as the generic ownership boundary

The current trait combines:

```text
domain
retrieve -> ContextPacket
propose_mutation -> MutationPlan
apply_approved_mutation -> LineageRef
```

This was a useful transition seam when EvolveAI and CodeGenome were treated as providers behind COREFORGE.

Agent Memory now owns the generic runtime, retrieval, mutation-governance, currentness, correction, deletion, restart, and provenance contracts directly. Keeping the provider abstraction as the canonical generic-memory architecture would reintroduce the fragmentation #455 corrected.

Disposition:

```text
VaultMemoryProvider as generic owner -> obsolete_or_superseded
COREFORGE adapter to Agent Memory     -> downstream product integration
```

COREFORGE may still use provider/plugin patterns for product-specific sources and inference adapters. It should not require EvolveAI or CodeGenome to own generic memory behavior.

### MutationContract and LineageRef: absorbed/superseded by stronger Agent Memory semantics

COREFORGE's `MutationContract` records actor, target, operation, justification, and validation metric, with `Approved`, `Vetoed`, or `PendingReview` planning outcomes. `LineageRef` records a source and a small active/archive/veto/promote state vocabulary.

Those are useful ancestry patterns, but Agent Memory PAMA, receipts, lifecycle/currentness, provenance, deletion/residue, correction, and restart contracts now carry a materially stronger generic boundary.

Disposition: **obsolete_or_superseded** for generic memory governance. Do not create a second authority layer by importing these structures beside PAMA.

### ContextBroker and ContextPacket: generic selection absorbed, product envelope stays downstream

The current broker aggregates provider retrieval results into a packet containing request/user/agent identity, memory domains, references, excerpts, and a governance view.

Agent Memory now owns generic candidate generation, multi-route retrieval, typed graph traversal, scope/isolation/currentness checks, and governed final admission. Those are the memory-selection semantics that must remain canonical.

COREFORGE's final packet, however, is a product concern. Persona, intent, bundle shape, UI-facing inspection, local cache state, and application-specific presentation do not need to move into Agent Memory merely because they sit next to retrieved memories.

Disposition:

```text
generic memory selection/admission -> absorbed in Agent Memory
ContextPacket presentation envelope -> specialized_source_only / downstream product
persona + intent bundle assembly    -> specialized_source_only / downstream product
cache and UI inspection views       -> specialized_source_only / downstream product
```

### Confidence-threshold redaction: intentionally not adopted

The current broker's `redact_sensitive` helper removes excerpts below a numeric confidence threshold and records that low-confidence excerpts were redacted.

Agent Memory must not generalize this into a privacy or authorization mechanism.

```text
confidence
  != sensitivity
  != access permission
  != scope
  != privacy authority
```

A low-confidence value may be perfectly authorized to disclose. A high-confidence value may be highly sensitive and forbidden. Scope, policy, identity, and isolation must remain the load-bearing admission controls.

Disposition: **intentionally_not_adopted** as generic governance behavior.

### BundleContract: useful downstream completeness contract, not a memory authority primitive

COREFORGE's bundle contract distinguishes required and optional output fields and reports missing required fields. That fail-closed completeness pattern is useful for product context assembly.

It does not determine whether an underlying memory was true, current, authorized, or admissible. Agent Memory should therefore expose enough metadata for consumers to build required-field contracts without moving application-specific bundle schemas into the memory subsystem.

Disposition: **specialized_source_only** for COREFORGE/product orchestration.

### COREFORGE conclusion

No remaining COREFORGE Vault/NeuroSpace mechanism inspected in this pass establishes a new generic Agent Memory implementation gap.

The architecture direction is now clearer:

```text
Agent Memory
  -> canonical generic memory contract/runtime
  -> governed retrieval + lifecycle + provenance + restart
  -> stable consumer-facing facade
        |
        v
COREFORGE
  -> persona / intent / local application orchestration
  -> packet and bundle presentation
  -> UI / cache / inference-plugin integration
```

The remaining work between these repositories is migration/integration, not harvesting a second generic memory subsystem into Agent Memory.

## UOR disposition

The current UOR ecosystem is broader than the older Agent Memory `uor-addr` review.

The current review does not justify importing UOR as a runtime foundation.

Useful lessons identified so far are narrower:

- exact identity and content-reference discipline;
- version-bound canonicalization contexts;
- explicit refusal when an implementation/runtime cannot satisfy the declared canonical context;
- conformance vectors that are independent of one implementation;
- mutation tests designed to prove a check can actually fail;
- exact addressed/versioned memory fixtures and keyed rebinding pressure;
- disciplined negative-result reporting and matched controls;
- producer/artifact identity and replayable conformance evidence.

These lessons do not make UOR identity into lifecycle, retrieval authority, PAMA, or a universal ontology.

`uor-r4` in particular is research pressure, not an architecture target. Its own current documentation is explicit that the project is pre-alpha and that its broader geometric predictive claims are not established. Agent Memory should preserve that evidentiary discipline before adopting any mechanism.

## Governance and trust peers

Microsoft AGT, TRACE, Agent Manifest and cMCP belong at evidence, policy, verification, and enforcement boundaries.

The Agent Memory rule remains:

```text
external evidence may establish facts about an execution or identity
external policy/enforcement may constrain an action
external confidence or attestation does not become Agent Memory memory authority
```

### TRACE source-rights correction

The current source registry is too coarse about TRACE licensing.

At the inspected TRACE main revision, upstream distinguishes:

```text
normative specification material -> Community Specification License 1.0
source / SDK / tests / examples -> Apache-2.0
non-spec documentation -> CC BY 4.0
```

A later #470 wave must reconcile `sources/source-registry.json` and any NOTICE/attribution language against that file-class boundary.

### Agent Manifest delta binding

Current Agent Manifest main includes a memory-delta verification correction whose stated purpose is binding appended operations. That is directly relevant to Agent Memory checkpoint/delta evidence.

The lesson is narrow but important:

```text
consistent root / checkpoint relation
  != proof of which operation was appended
```

#440 should exercise this boundary rather than treating a dependency bump as qualification.

## What remains open under #470

The CodeGenome impact/evidence-fusion audit and COREFORGE Vault/NeuroSpace inventory are now dispositioned. Remaining closeout work includes:

- PrismPM verification/conformance review where concrete;
- cMCP current-upstream disposition beyond the existing qualified pin;
- UOR final/publication follow-up where provisional sources change;
- TRACE source-registry and NOTICE reconciliation;
- version-exact TRACE + Agent Manifest qualification under #440;
- any additional bounded implementation issue exposed by those passes.

## Current conclusion

The accurate state is:

```text
planned native-harvest sequence: complete
exhaustive ancestry/peer harvest: not complete
negative/failure memory gap: resolved natively in #473
CodeGenome impact/evidence-fusion disposition: complete
COREFORGE Vault/NeuroSpace inventory: complete for generic-memory harvest
remaining external peer / rights closeout: active
Jin benchmark dependency: unrelated to this workstream
```

Agent Memory can continue advancing while external benchmark evidence is pending.
