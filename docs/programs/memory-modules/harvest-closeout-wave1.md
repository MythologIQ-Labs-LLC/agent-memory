# Harvest Closeout Wave 1

Issue: #470  
RC umbrella: #410  
Agent Memory audit baseline: `63d78d27df7017bcbe2687675150342771262c0f`  
Status: **incomplete inventory, evidence-bound first wave**

## Purpose

This document starts the exhaustive harvest closeout required by #470.

The earlier native-harvest sequence completed important planned slices. It did not prove that every materially useful mechanism from Agent Memory ancestry and external peers had been absorbed, deliberately excluded, or bounded behind interoperability.

This wave records exact source revisions for the surfaces actually inspected, maps them to current Agent Memory capability, identifies one confirmed native implementation gap, and records several areas that require further disposition.

This is not a closeout certificate.

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

## Wave 1 source matrix

| Source | Exact inspected revision | Rights posture | Mechanism or lesson | Current Agent Memory posture | Required action |
|---|---|---|---|---|---|
| EvolveAI | `21161ce7b88dbffeb7ed59757b4d02d24a9c2acd` | same-owner first-party; public Apache-2.0 remains relevant to redistribution | decay, reinforcement, consolidation, prune/archive pressure, restart, vector and temporal behavior | **absorbed** for the native metabolism slice and major retrieval mechanisms | retain as ancestry and test oracle, not generic runtime dependency |
| EvolveAI Shadow Genome | `21161ce7b88dbffeb7ed59757b4d02d24a9c2acd` | same-owner first-party | typed failures, stable identity, recurrence counting, persistence, bounded capacity, similarity-based recurrence evidence | **partially_absorbed**; doctrine exists but native generic failure-memory runtime was not found | implement #471; explicitly reject direct `similarity -> Block` authority |
| CodeGenome | `6dac705e137a3aea795163a766c263a38285416d` | same-owner first-party; public MIT remains relevant to redistribution | vector persistence/kNN, graph traversal, overlays, impact propagation, evidence fusion, experiment loop | **partially_absorbed** | vector and generic typed graph basics are native; audit impact propagation and evidence-fusion semantics next |
| COREFORGE | `43b423dbaf8ec1f4323f0556ed462cfa02405a22` | private same-owner first-party | runtime memory space, lineage, context broker/packet patterns, local product integration | **partially_absorbed** | generic memory ownership remains Agent Memory; separately inventory product-specific context packaging before declaring ancestry exhausted |
| UOR Framework | `51c01382200b0179d6640b07e9c8119364ab69a1` | MIT at inspected main | deterministic identity and conformance lineage | **optional_interoperability** | keep identity lineage bounded; do not import lifecycle or PAMA semantics |
| uor-addr | `165b51e3e2113ee5d032730cde709335d4fe9b60` | external open-source profile already qualified separately | exact content references | **optional_interoperability** | existing optional profile remains appropriate; no ordinary runtime dependency |
| uor-r4 | `552d847d49fb263966165004b835f2f53cccaae1` | MIT | exact addressed/versioned memory experiments, keyed rebinding/overwrite pressure, unusually explicit matched controls and negative-result discipline | **intentionally_not_adopted** as a geometric model; research pressure remains useful | evaluate its long-horizon keyed rebinding/overwrite fixture shape as benchmark pressure without adopting geometric predictive claims |
| uor-foundry | `5b4711aed4fbb7da9d8b0aa04048a2b04713de4a` | root `Cargo.toml` declares `MIT OR Apache-2.0`; no root LICENSE was found in this inspection | scoped authority, replayable acceptance, exact producer identity, artifact handoff and conformance evidence | **blocked_by_rights** for direct code reuse; conceptual comparison only | confirm repository-level license distribution before copying code; independently synthesize any useful conformance lesson meanwhile |
| uor-jcs-nfc | `303591128094362857791930fdc12b73875d1ff6` | Apache-2.0 with NOTICE | pinned JSON canonicalization context, Unicode-version binding, refusal semantics, conformance vectors as oracle, mutation testing | **intentionally_not_adopted** at this provisional RC5 revision | watch for final publication; compare its canonicalization/version-binding lessons with existing Agent Memory canonical evidence paths before any adoption |
| uor-matmul | `3cc5882f210667f9ac00fd8c02c5b5957b493f5d` | MIT | exact arithmetic and conformance methodology, not generic memory semantics | **intentionally_not_adopted** | no Agent Memory implementation need identified; retain only methodological lessons if concrete evidence work benefits |
| Microsoft Agent Governance Toolkit | `e0574c1eb44a9b02f106e2b4c63fc60ec3c017ce` | MIT | runtime policy/enforcement, identity and audit boundary; absent/unconfigured/unavailable state distinctions | **optional_interoperability** | continue comparator/adapter posture; do not make AGT the source of PAMA authority |
| AgentTrust TRACE | `e3111c77b89cc9870ac7218936ab956ad77de6c9` | mixed license: normative specification under Community Specification License 1.0, source/SDK/tests/examples under Apache-2.0, non-spec docs under CC BY 4.0 | portable trust/attestation/action evidence | **optional_interoperability** | correct stale source-registry wording and execute version-exact qualification under #440 |
| Agent Manifest | `d66b6f0b18f3ca83cb93071257d8f5edce5ae850` | Apache-2.0 | deployment identity, checkpoint/delta evidence, appended-operation binding | **optional_interoperability** | #440 must qualify the intended package pair; explicitly test that memory delta evidence binds appended operations rather than only consistency/root state |

## Confirmed implementation gap: negative/failure memory

Wave 1 found one gap that is concrete enough to implement immediately.

Agent Memory doctrine already defines failure memory with attempt, context, expected and actual outcome, causal status, root-cause candidates, correction, verification, applicability, and recheck/expiry semantics. The canonical ownership map nevertheless still records negative/failure memory as requiring further native implementation.

EvolveAI Shadow Genome supplies useful ancestry:

- typed failure categories and severity;
- deterministic failure identity;
- recurrence counting;
- persistence/import/export;
- active/inactive state;
- bounded capacity;
- semantic similarity for recurrence detection.

Its authority shape is not acceptable as Agent Memory doctrine. The EvolveAI interceptor may return `Block` directly from similarity/threshold logic. Agent Memory must instead preserve:

```text
similarity / recurrence / severity
  -> evidence or proposal
  -> governed admission
  -> existing action / mutation authority
```

Issue #471 owns the native implementation slice.

## CodeGenome gap pressure

The existing Agent Memory CodeGenome qualification proves provider/domain capabilities, but provider qualification is not the same thing as native generic absorption.

The next CodeGenome pass must separately answer:

1. Does native Agent Memory already implement a generic equivalent of impact/blast-radius propagation over typed relations?
2. If yes, where is the bounded evidence and authority model?
3. If no, is generic impact propagation useful enough to implement, or should it remain a specialized code-domain source signal?
4. Which evidence-fusion mechanisms are genuinely useful without allowing combined confidence to become truth, recall admission, or mutation authority?
5. Which experiment/performance-loop lessons are already covered by #465, and which remain unabsorbed?

No implementation issue should be opened merely because CodeGenome contains a feature. The feature must earn a generic Agent Memory role.

## UOR disposition

The current UOR ecosystem is broader than the older Agent Memory `uor-addr` review.

Wave 1 does not justify importing UOR as a runtime foundation.

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

`uor-r4` in particular is research pressure, not an architecture target. Its own current documentation is explicit that the project is pre-alpha and that its broader geometric predictive claims are not established. Agent Memory should copy that evidentiary honesty before it copies any mechanism.

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

## What this wave does not close

Still required under #470:

- current detailed CodeGenome impact/evidence-fusion disposition;
- current detailed COREFORGE Vault/Neurospace inventory against native Agent Memory;
- PrismPM verification/conformance review where concrete;
- cMCP current-upstream disposition beyond the existing qualified pin;
- UOR final/publication follow-up where provisional sources change;
- source-registry and NOTICE reconciliation;
- implementation evidence for #471;
- any additional bounded implementation issue exposed by later waves.

## Current conclusion

The accurate state is:

```text
planned native-harvest sequence: complete
exhaustive ancestry/peer harvest: not complete
one confirmed native gap: negative/failure memory (#471)
several bounded disposition audits: still active
Jin benchmark dependency: unrelated to this workstream
```

Agent Memory can continue advancing while external benchmark evidence is pending.