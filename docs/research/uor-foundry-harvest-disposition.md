# UOR Foundry Harvest Disposition

Issue: #489  
Parent: #470  
RC umbrella: #410  
Status: complete review at exact inspected revision

## Exact source

```text
repository: UOR-Foundation/uor-foundry
revision: 5b4711aed4fbb7da9d8b0aa04048a2b04713de4a
```

This review asks whether Foundry exposes a generic memory, governance, evidence, or verification mechanism that Agent Memory should absorb natively. Licensing permission and technical adoption are evaluated separately.

## Source-rights result

The earlier Wave 1 / Wave 2 `blocked_by_rights` posture is obsolete for this exact revision.

The inspected repository contains:

```text
Cargo.toml: license = "MIT OR Apache-2.0"
LICENSE-MIT: MIT License, Copyright (c) 2026 The UOR Foundation
LICENSE-APACHE: Apache License 2.0
NOTICE: no root NOTICE file present at this revision
```

Therefore the repository-level code distribution is dual-licensed `MIT OR Apache-2.0` at the inspected revision.

This finding means direct reuse is legally possible subject to the selected license obligations. It does not mean direct reuse is architecturally desirable. No Foundry code, prose, schemas, or fixtures are copied into Agent Memory by this review, so no new source-registry material-reuse entry is required.

## Mechanism disposition

### Scoped authority

Foundry models scoped multi-administrator authority, distinct-user quorums, atomic post-change coverage, and lockout protection.

Agent Memory already owns the generic memory-authority problem through PAMA, including scope, consequence, reversibility, evidence, actor authority, downstream authority, and explicit high-consequence review boundaries.

Disposition: **already native / no implementation action**.

The Foundry quorum and organization-administration semantics remain useful external examples. They are not a reason to introduce a second authority layer beside PAMA.

### Replayable acceptance

Foundry binds conformance IDs to tests, rejects unregistered test/scenario drift, and records evidence against explicit claims.

Agent Memory already separates doctrine, structural fixtures, behavioral harnesses, exact-head runtime evidence, and production evidence through the D/F/H/R/P evidence-depth model. It also keeps capability maturity separate from component identity and binds runtime evidence to exact implementation revisions.

Disposition: **already native / no implementation action**.

The useful lesson is confirmation that evidence categories should remain explicit and non-interchangeable. Agent Memory already enforces that distinction.

### Producer and artifact identity

Foundry's producer-release contract binds exact producer identity, artifact trees, reproducibility, pre-publication evidence, and downstream publication handoff. Its SDK boundary also distinguishes source integration from consumer acceptance.

Agent Memory already binds benchmark, qualification, and closeout evidence to exact revisions and configuration/runtime identities, and preserves external validation as evidence rather than authority.

Disposition: **already native for Agent Memory's memory/runtime evidence scope; specialized external lesson for broader product-release supply-chain closure**.

No generic memory capability gap was found that would justify importing Foundry's release machinery.

### Honesty levels and conformance IDs

Foundry records three claim levels:

```text
some-true
build
open
```

and explicitly states that `build` evidence is not proof and that `open` is not asserted by the current conformance set.

Agent Memory already has two orthogonal native classifications that cover the underlying lesson:

```text
capability maturity:
  declared
  implemented
  runtime_wired
  evidence_proven
  reference_qualified

runtime evidence depth:
  D documented doctrine
  F structural fixture
  H behavioral harness
  R exact-head runtime evidence
  P production evidence
```

Disposition: **conceptual lesson already absorbed; do not import Foundry terminology as a parallel taxonomy**.

Creating `some-true/build/open` beside those existing classifications would add vocabulary without adding evidence discipline.

## Negative result

This review found no missing generic Agent Memory mechanism that warrants a new implementation slice.

That is a valid harvest result:

```text
open license
  != required reuse

useful peer mechanism
  != missing native capability

similar verification language
  != reason to duplicate taxonomy
```

The bounded conclusion is that Foundry remains a useful external conformance and release-evidence peer, while Agent Memory's existing PAMA, evidence-depth, capability-maturity, revision-binding, restart/recovery, and RC evidence surfaces already cover the generic lessons relevant to memory.

## Final classification

```text
source: UOR-Foundation/uor-foundry
rights: verified dual-license MIT OR Apache-2.0 at exact inspected revision
runtime dependency required: no
code reuse required: no
Agent Memory authority effect: none
final posture: external verification/evidence peer; generic lessons already native
remaining action under #489: none after matrix reconciliation and exact-head CI
```

## Boundaries

This review does not claim:

- that every Foundry product or supply-chain mechanism exists in Agent Memory;
- that Agent Memory should adopt Foundry organization-management semantics;
- that Foundry conformance proves Agent Memory behavior;
- that open licensing grants Foundry any memory or governance authority;
- that a release-engineering framework is itself generic memory machinery.
