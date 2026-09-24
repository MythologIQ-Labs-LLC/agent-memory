# Harvest Closeout Wave 1

Issue: #470  
RC umbrella: #410  
Agent Memory audit baseline: `63d78d27df7017bcbe2687675150342771262c0f`  
Failure-memory reconciliation: `c2d23c18d8041dea572c070d81b79e5a348556c5`  
Status: **incomplete inventory, evidence-bound first wave**

## Purpose

This document starts the exhaustive harvest closeout required by #470.

The earlier native-harvest sequence completed important planned slices. It did not prove that every materially useful mechanism from Agent Memory ancestry and external peers had been absorbed, deliberately excluded, or bounded behind interoperability.

Wave 1 records exact source revisions for the surfaces actually inspected, maps them to current Agent Memory capability, and records areas that still require disposition. The one concrete native implementation gap found by the initial wave, negative/failure memory, has now been implemented and qualified through #471 / PR #473. That resolves the gap without turning Wave 1 into an exhaustive harvest certificate.

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
| EvolveAI Shadow Genome | `21161ce7b88dbffeb7ed59757b4d02d24a9c2acd` | same-owner first-party | typed failures, stable identity, recurrence counting, persistence, bounded capacity, similarity-based recurrence evidence | **absorbed** through native governed failure memory in #471 / PR #473 | retain as ancestry/test pressure only; preserve Agent Memory's stricter evidence-not-authority boundary and no EvolveAI runtime dependency |
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

## Resolved implementation gap: negative/failure memory

Wave 1 originally found one gap concrete enough to implement immediately.

Agent Memory doctrine already defined failure memory with attempt, context, expected and actual outcome, causal status, root-cause candidates, correction, verification, applicability, and recheck/expiry semantics. The canonical ownership map nevertheless still recorded negative/failure memory as requiring further native implementation.

EvolveAI Shadow Genome supplied useful ancestry:

- typed failure categories and severity;
- deterministic failure identity;
- recurrence counting;
- persistence/import/export;
- active/inactive state;
- bounded capacity;
- semantic similarity for recurrence detection.

Its authority shape was not acceptable as Agent Memory doctrine. The EvolveAI interceptor may return `Block` directly from similarity/threshold logic. Agent Memory instead preserves:

```text
similarity / recurrence / severity / impact
  -> evidence or proposal
  -> governed admission
  -> existing action / mutation authority
```

#471 / PR #473 implemented the native Agent Memory form without an EvolveAI runtime dependency. The landed implementation includes stable logical failure identity, typed immutable revisions, explicit recurrence evidence, correction/dispute/retraction/history, typed recall isolation, bounded checkpoint/recovery, currentness/tombstone behavior, and a revision-bound benchmark that reports quality, performance, and governance separately.

Exact implementation merge:

```text
c2d23c18d8041dea572c070d81b79e5a348556c5
```

Exact evaluated PR head and benchmark evidence:

```text
head: b0c9a3edd88c87070c949bd69359a042f6c30a80
workflow: 36045411869
artifact: 10827654755
artifact sha256: 95b45bfc1b50fbf3965aa587c249a13bdd8ab05d42d868d305d736ceb09fbd20
```

The bounded result recorded repeated-failure retrieval recall `1.0` over 2/2 fixture cases, zero identity-equivalence failures, zero identity-separation/false-recurrence failures, zero recurrence/currentness failures, and zero measured governance violations. Failure-memory authority effect remained `none`.

Two limits remain deliberate rather than hidden:

- generic standalone `FailureMemory` owner state is process-local; restart proof is bounded to explicit `CheckpointedFailureMemory` composition;
- the benchmark does not claim that memory retrieval itself executes or prevents a downstream action, so avoided-failure action outcome remains `not_measured`.

This row is now **absorbed** for #470 purposes. Any later expansion of failure-memory capability must earn its own implementation and evidence rather than reopening EvolveAI as runtime ownership.

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
- any additional bounded implementation issue exposed by later waves.

The former #471 implementation gap is no longer on this list. Humanity has, briefly, managed to remove an item from a backlog rather than merely rename it.

## Current conclusion

The accurate state is:

```text
planned native-harvest sequence: complete
exhaustive ancestry/peer harvest: not complete
negative/failure memory gap (#471): implemented and qualified
several bounded disposition audits: still active
Jin benchmark dependency: unrelated to this workstream
```

Agent Memory can continue advancing while external benchmark evidence is pending.
