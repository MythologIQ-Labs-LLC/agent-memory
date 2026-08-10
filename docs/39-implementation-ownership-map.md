# Implementation Ownership Map

## Purpose

[`05-repo-implementation-map.md`](05-repo-implementation-map.md) maps named systems into the architecture's roles and control classes. This document adds the ownership dimension: for each component of [`11-component-architecture.md`](11-component-architecture.md), who is the primary owner, who consumes it, and what its implementation status actually is — so concepts do not drift back into repo-local folklore.

**Epistemic status: declared, not verified.** This repository is the doctrine and conformance authority; it does not contain, build, or test the implementation systems named below. Every ownership claim is a candidate assignment awaiting the implementation evidence defined in `05-repo-implementation-map.md`, and the doctrine backlinks of issue #5. Nothing here is a conformance claim — see the claiming rules of [`35-interoperability-profiles.md`](35-interoperability-profiles.md).

## Status vocabulary

```text
declared    ownership asserted by doctrine; no implementation evidence in this repo
partial     some implementation exists per its own repo's claims; unverified here
verified    implementation evidence linked and checked against doctrine (none yet)
contested   more than one system claims primary ownership; consolidation needed
open        no credible owner yet
```

## Ownership map

| Component | Primary owner (candidate) | Secondary consumers | Status |
|---|---|---|---|
| Identity Substrate | UOR Framework; CodeGenome for code-node identity | all components | declared |
| Evidence and Provenance | CodeGenome; FailSafe receipts; COREFORGE ledgers | PAMA, Certification, Conformance | declared, **contested** — three ledger-shaped systems overlap |
| Reality Graphs | CodeGenome | Bicameral (decision graphs), Runtime Memory | declared |
| Lifecycle Engine | EvolveAI | COREFORGE Vault | declared, **contested** — Vault also holds lifecycle candidates |
| Saturation and Decay | EvolveAI (L1/L2/L3 tiers, CMHL decay, REM synthesis) | PRISM-style consumers, Lifecycle | declared |
| PAMA | dedicated governance module | every mutating component | **open** — no standalone PAMA implementation exists; highest-risk gap |
| Certification | FailSafe; Arbiter; approval workflows | Lifecycle, Crystallization gate | declared, **contested** — certifier independence (doc 35, Profile 5) must survive consolidation |
| Runtime Memory Space | COREFORGE Vault / Neurospace | agent runtimes, Context Assembly | declared |
| Context Assembly | COREFORGE; agent runtimes | user-facing products | declared |
| Correction and Dispute | Vault, Bicameral, FailSafe-style workflows | Recall admission, Quality metrics | declared, **contested** — three partial candidates, no owner of the user-facing contract in [`38-human-correction-ux-contract.md`](38-human-correction-ux-contract.md) |
| Conformance | this repository | every implementation | **verified** — the one component whose owner is checkable here: schemas, fixtures, validators, CI |
| Failure / negative memory | Shadow Genome | Scoring, Threat model | declared |

## Consolidation and segmentation calls

**Should consolidate** (duplicated concepts):

- The three ledger-shaped systems (CodeGenome provenance, FailSafe receipts, COREFORGE ledgers) should converge on the decision-receipt and audit-event schemas ([`../schemas/decision-receipt.schema.json`](../schemas/decision-receipt.schema.json), [`../schemas/memory-audit-event.schema.json`](../schemas/memory-audit-event.schema.json)) rather than each defining a private evidence format.
- Lifecycle ownership must resolve to one committer: EvolveAI proposing transitions that Vault commits is a legitimate split (proposal versus commit per [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md)); both committing is not.

**Should remain segmented** (per [`12-concept-segmentation-matrix.md`](12-concept-segmentation-matrix.md)):

- Certification must not collapse into the system that proposes candidates, whatever repo hosts both — independence is the point.
- PAMA must not be absorbed into Vault or any single runtime: whichever repo implements it, the authority boundary stays a separate, auditable module consumed through the PAMA adapter of [`34-adapter-contracts.md`](34-adapter-contracts.md).
- Identity stays out of every scoring system. No estimator gets to mint identity.

## Resolution path

Ownership claims graduate from `declared` only through the evidence items of `05-repo-implementation-map.md`: a doctrine backlink in the owning repo (issue #5), an implementation-alignment issue mapping its slice, and eventually fixture results claiming a profile from `35-interoperability-profiles.md`. Contested rows are resolved by cross-repo decision, recorded here with the decision reference — not by whichever implementation ships first.

## Doctrine

Ownership is a governance fact, not a deployment fact.

A component belongs to the repo that accepts its doctrine obligations — its contracts, its conformance surface, its audit duties. Code without those obligations is not an owner; it is an unverified volunteer.
