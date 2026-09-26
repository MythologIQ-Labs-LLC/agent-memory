# Agent Memory Project Model

**Status:** Proposed project/operating model under #554 and #556  
**Scope:** repository identity, public/community boundary, evaluation/Gauntlet relationship, runtime product boundary  
**Authority effect:** none

## 1. Why this document exists

`Agent Memory` began as a relatively generic name for an architecture/reference implementation. That generic name now fits the repository better than a narrow product name would.

The repository has become a place where multiple kinds of memory work coexist:

- memory architecture and theory;
- executable/reference runtime work;
- governance doctrine and adversarial reasoning;
- independent benchmark integration;
- benchmark evaluator integrity;
- benchmark-driven product remediation;
- system-neutral memory qualification through the Agent Memory Gauntlet;
- community-facing contracts and evidence schemas;
- research into unresolved memory questions and benchmark gaps.

Those responsibilities are related, but they are not the same product and must not silently inherit one another's authority, licensing posture, evidence class, or maturity claim.

This document defines the working layered model.

## 2. Working five-layer model

```text
Agent Memory
|
+-- 1. Architecture / Doctrine / Research Commons
|      memory theory
|      ADRs and doctrine
|      ancestry and prior-art research
|      benchmark research and gap analysis
|      open discussion of unresolved memory problems
|
+-- 2. Memory Evaluation
|      benchmark contracts
|      native benchmark adapters
|      normalized evidence
|      comparison semantics
|      evaluator integrity
|      reproducibility/provenance
|
+-- 3. Agent Memory Gauntlet
|      public qualification/orchestration layer
|      system adapter contract
|      benchmark portfolio
|      Governance Gauntlet
|      operational/adversarial suites
|      Benchmark Coverage Atlas
|      neutral gap benchmarks where justified
|
+-- 4. Reference / Conformance Implementation
|      executable demonstration of the contracts
|      implementation/conformance evidence
|      baselines and adapters
|      current `agent-memory-reference` package ancestry
|
+`-- 5. Distinct Production Runtime Product
       future separately branded runtime
       implementation hardened by repeated Gauntlet pressure
       independent package/release identity
       intentionally reviewed licensing/commercial boundary
```

This model is descriptive and directional. It does not itself change licenses, package names, or accepted architecture.

## 3. Layer 1: Architecture / Doctrine / Research Commons

### 3.1 Purpose

This is the intellectual commons of Agent Memory.

It answers questions such as:

- What kinds of memory should agents possess?
- What distinguishes retrieval relevance from temporal applicability?
- How should correction differ from historical supersession?
- What does memory metabolism mean?
- How should authority and governance constrain cognition?
- Which existing systems contain mechanisms worth harvesting?
- Which benchmark results challenge current assumptions?

### 3.2 Typical artifacts

- ADRs;
- architecture documents;
- research briefs;
- doctrine and governance documents;
- threat models;
- benchmark qualification records;
- literature/prior-art comparisons;
- issue discussions that make explicit architectural rulings.

### 3.3 Authority boundary

```text
research finding != accepted doctrine
benchmark result != accepted doctrine
prior art != runtime dependency
implementation ancestry != canonical owner
```

Research may challenge doctrine. It does not silently replace it.

## 4. Layer 2: Memory Evaluation

### 4.1 Purpose

Memory Evaluation is the lower-level evidence machinery.

It exists so Agent Memory, baselines, and external systems can be measured under reconstructable evidence contracts without pretending heterogeneous benchmarks share one universal metric.

### 4.2 Responsibilities

- benchmark identity/revision binding;
- frozen input identity;
- system and adapter identity;
- execution identity;
- native benchmark outputs;
- normalized evidence where semantically defensible;
- fail-closed comparison;
- evaluator-integrity evidence;
- reproducibility status.

### 4.3 Explicit non-responsibilities

Memory Evaluation does not:

- admit or refuse product memories;
- mutate runtime state outside benchmark protocol;
- create memory authority;
- turn unlike metrics into a universal score;
- declare architecture true because a benchmark improved.

```text
benchmark score != truth
benchmark score != recall admission
benchmark score != mutation authority
comparison != doctrine
```

## 5. Layer 3: Agent Memory Gauntlet

### 5.1 Purpose

The Agent Memory Gauntlet is the public, coordinated qualification layer built on Memory Evaluation.

The word `Gauntlet` refers to a trial/arena of pressure, not to a glove.

The core idea is:

> A memory theory, architecture, runtime, or strategy should be willing to prove its claims under diverse external, adversarial, governance, temporal, operational, and integrity pressure.

The Gauntlet is not intended to guarantee that one memory system is universally best.

### 5.2 Relationship to Memory Evaluation

```text
Memory Evaluation = measurement machinery
Agent Memory Gauntlet = coordinated qualification program
```

### 5.3 Public/community value

The intended community workflow is eventually:

```text
memory system
    |
    v
Gauntlet system adapter
    |
    v
capability negotiation
    |
    v
eligible benchmark / governance / operations suites
    |
    v
benchmark-native + normalized evidence
    |
    v
coverage-aware qualification report
```

A developer should be able to point a memory implementation at the Gauntlet and learn what it does well, what it does poorly, what it does not support, and which claims remain untested.

### 5.4 No universal leaderboard score

The Gauntlet should prefer a capability/coverage profile to a single rank.

For example:

```text
retrieval                 measured
current-state handling    measured
historical recall         partial
governed isolation        unsupported
selective deletion        measured
recovery                  measured
metabolism                not measured
multimodal                 unsupported
```

This is more informative than pretending all dimensions share one unit.

### 5.5 Benchmark openness

The benchmark portfolio remains open to newly discovered external benchmarks that add credible distinct pressure.

A benchmark is not included merely because it exists.

Qualification should consider:

- provenance and source identity;
- exact protocol availability;
- dataset/artifact availability;
- licensing/data-use posture;
- evaluator inspectability;
- reproducibility;
- distinct capability pressure;
- risk of privileged metadata or protocol distortion;
- practical cost.

### 5.6 Gauntlet-native benchmarks

Agent Memory may author neutral benchmarks when important coverage gaps remain across the qualified external portfolio.

The bar is intentionally high.

A Gauntlet-native benchmark should begin with a documented field-level gap, not with a feature our own runtime happens to perform well.

Required posture:

```text
field gap identified
    -> existing benchmark search/qualification
    -> extension/adaptation ruled insufficient
    -> neutral protocol designed
    -> protocol/generator/seed/metrics frozen
    -> baselines and external systems invited where feasible
    -> Agent Memory enters as one contestant
```

Gauntlet-native evidence is valuable coverage/falsification evidence. It is not independent evidence that the Agent Memory runtime is superior.

## 6. Layer 4: Reference / Conformance Implementation

### 6.1 Purpose

The reference implementation demonstrates that the contracts and architecture can be implemented and gives the repository an executable substrate for tests, examples, adapters, and conformance work.

### 6.2 Current identity

The current Python package is still named:

```text
agent-memory-reference
```

and the repository is currently Apache-2.0.

Those facts describe the current state. They do not settle the final commercial/product identity of a future hardened runtime.

### 6.3 Evidence boundary

```text
reference implementation pass != ecosystem benchmark win
conformance pass != production readiness
Agent Memory-specific fixture != independent evidence
```

## 7. Layer 5: Distinct Production Runtime Product

### 7.1 Why this layer exists

The executable runtime has become valuable enough that it should not be forced to share one permanent identity or licensing decision with the entire research/evaluation/community commons.

The intended direction is to preserve Agent Memory's usefulness to contributors and the broader memory ecosystem while deliberately protecting the IP and commercial options of the hardened runtime implementation.

### 7.2 Runtime identity principle

A useful naming principle emerged from the Gauntlet work:

> The runtime is the memory implementation that survives the Gauntlet.

This has two related meanings.

At runtime/system scale:

```text
architecture
    -> implementation
    -> adversarial pressure
    -> independent benchmarks
    -> governance pressure
    -> operational pressure
    -> remediation
    -> repeated replay
    -> hardened surviving runtime
```

At individual-memory scale:

```text
observation
    -> scrutiny
    -> contradiction / corroboration
    -> time / metabolism
    -> governance
    -> retrieval demand
    -> lifecycle decisions
    -> retained memory that survives justified pressure
```

Survival is not truth.

```text
survived benchmark != true
survived retention != authoritative
survived contradiction != permanently correct
survived Gauntlet != universally safe
```

The metaphor describes resilience under scrutiny, not epistemic infallibility.

### 7.3 Naming posture

Do not select a runtime name merely because it sounds durable.

The eventual name should:

- be distinct from Agent Memory and Agent Memory Gauntlet;
- evoke survival, tempering, persistence, proof, retention, or endurance;
- sound credible as infrastructure;
- work across package/repository/CLI/service/product surfaces;
- avoid implying perfect truth or permanent authority;
- survive package/repository/domain/trademark collision review.

A coined name may be preferable to crowded sturdy-sounding dictionary nouns.

## 8. Licensing and IP posture

### 8.1 Current state

The current repository/reference package is Apache-2.0.

Nothing in this project model retroactively makes existing Apache-2.0 material proprietary.

### 8.2 Desired future separation

A candidate long-term split is:

```text
architecture / research docs                permissively open
benchmark specs / Gauntlet contracts        permissively open
evidence schemas / neutral adapters          permissively open
reference/conformance implementation         open where appropriate
distinct production runtime                  separately decided
```

The production runtime may eventually use a source-available, dual-license, open-core, commercial, or other counsel-approved model.

No specific model is selected here.

If a future license does not satisfy the Open Source Definition, project documentation should call the runtime `source-available`, not `open source`.

### 8.3 Why this is not merely legal housekeeping

The license boundary influences architecture:

- which APIs/contracts must remain open for Gauntlet interoperability;
- where contributions land;
- whether runtime code remains in-tree or moves to a separate repository;
- whether shared code can flow between permissive and protected packages;
- how package/release identity changes are communicated;
- whether a contributor agreement or other inbound-rights mechanism is needed.

Those decisions require explicit maintainer and legal review before implementation.

## 9. Cross-layer evidence classes

At minimum distinguish:

```text
accepted doctrine
research hypothesis
product/runtime contract
runtime implementation
implementation conformance evidence
independent external benchmark evidence
adapted external benchmark evidence
Gauntlet-native neutral benchmark evidence
field/deployment evidence
baseline/probe evidence
```

No class silently promotes itself into another.

Examples:

```text
benchmark improvement != architecture acceptance
architecture acceptance != implementation completeness
implementation completeness != benchmark superiority
Gauntlet-native pass != independent validation
field observation != controlled benchmark
```

## 10. Development learning loop

The project intentionally allows its layers to challenge one another.

```text
doctrine / hypothesis
        |
        v
implementation
        |
        v
internal conformance
        |
        v
independent / adversarial Gauntlet pressure
        |
        v
finding classification
        |
        v
bounded remediation or doctrine challenge
        |
        v
same frozen replay
        |
        v
product change / doctrine change / limitation / rejection
```

This loop is a feature of the repository, not evidence that architecture and benchmarks are the same authority domain.

## 11. Relationship to ADR-039 and current runtime work

ADR-039 and the current stable-runtime-contract work continue independently of this project model.

The Gauntlet/reference/product boundaries should not force an outcome for relevance/currentness, historical admission, or other active runtime doctrine.

Instead:

- active runtime work produces evidence;
- the Gauntlet records and expands pressure;
- the project model ensures those results land in the correct layer;
- a future production runtime consumes accepted architecture only through explicit product decisions.

## 12. Documentation precedence and reconciliation

This document should be reconciled with the broader repository operating-model documentation before either is declared final canonical project identity.

The older three-role framing:

```text
product/runtime
architecture/governance laboratory
evaluation/benchmark laboratory
```

was useful but is now too coarse.

The five-layer model makes explicit:

1. the public Gauntlet as a productized qualification layer;
2. the reference/conformance implementation as distinct from a hardened commercial runtime;
3. the future licensing/product boundary.

## 13. Maintainer principles

1. Keep Agent Memory broadly useful even to people who never adopt our runtime.
2. Let external evidence challenge the runtime and the theory.
3. Do not make Agent Memory's architecture the hidden scoring ontology of the Gauntlet.
4. Protect benchmark protocol fidelity over flattering results.
5. Create native benchmarks only for demonstrated coverage gaps.
6. Keep governance a first-class benchmark dimension.
7. Preserve evidence provenance and comparability.
8. Do not collapse unlike dimensions into one health score.
9. Protect future runtime IP deliberately rather than accidentally.
10. Never confuse resilience under scrutiny with truth or authority.

## 14. Related artifacts

- `docs/53-memory-evaluation-subsystem.md`
- `docs/54-memory-evaluation-cli.md`
- `docs/GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`
- `docs/BENCHMARK_COVERAGE_ATLAS.md`
- `docs/GOVERNANCE_GAUNTLET_SPECIFICATION.md`
- `docs/RUNTIME_IDENTITY_NAMING_BRIEF.md`
- issue #554, Agent Memory Gauntlet foundation
- issue #556, runtime identity/licensing boundary
