# Agent Memory Gauntlet Execution Roadmap

**Status:** Proposed execution/staging plan under #554  
**Purpose:** separate safe parallel work from work that should wait for active ADR-039/runtime-contract implementation to settle  
**Authority effect:** none

## 1. Why this roadmap exists

At the time this roadmap was written, active implementation work is still moving around:

- ADR-039 query-conditioned applicability;
- historical/current temporal behavior;
- stable runtime/public contracts;
- benchmark replay and product remediation.

At the same time, the repository has enough stable evaluation infrastructure to prepare the Agent Memory Gauntlet in parallel.

The goal is to avoid both failure modes:

1. **idle waiting**, where useful orthogonal work is postponed merely because runtime work is active;
2. **collision work**, where a second implementation stream edits the same contracts before the first has converged.

## 2. Parallelization rule

Work may proceed in parallel when it does not require guessing the final semantics of an actively changing runtime contract.

```text
safe parallel work
    = specification
    + coverage mapping
    + neutral schemas not coupled to unsettled runtime semantics
    + benchmark qualification
    + external-system adapter design
    + governance threat/test design

wait for active runtime convergence
    = binding Gauntlet behavior directly to unstable public runtime APIs
    + declaring ADR-039 Accepted
    + freezing runtime-specific adapter semantics
    + final package/product migration
    + final licensing/name migration
```

## 3. Current foundation work

PR #555 establishes the initial documentation foundation:

- Gauntlet System Adapter Contract;
- Benchmark Coverage Atlas;
- Governance Gauntlet Specification;
- Runtime Identity/Naming Brief;
- Agent Memory five-layer Project Model;
- this Execution Roadmap.

These artifacts should be reviewed as contracts/design documents, not as evidence that orchestration code already exists.

## 4. Workstream A: External system adapter contract implementation

### Safe now

The following can be designed/implemented without depending on final Agent Memory runtime internals:

1. machine-readable adapter manifest schema;
2. capability support vocabulary:
   - `native`
   - `mapped`
   - `derived`
   - `unsupported`
   - `unknown`;
3. operation request/response envelope schema;
4. adapter conformance validator;
5. capability negotiation utility;
6. test fixtures for valid/invalid manifests;
7. transport-neutral interface boundaries;
8. stdio transport prototype using a dummy external memory fixture;
9. adapter error/source attribution tests.

### Wait for Claude/runtime convergence

Do not freeze the production Agent Memory system adapter against an API that Claude is still changing.

A thin temporary adapter may be used for local proof, but the canonical Agent Memory adapter should be finalized only after the current stable-runtime/public-contract work reports its exact boundary.

## 5. Workstream B: Gauntlet orchestration

### Safe now

Design and test orchestration against dummy/baseline adapters:

```text
describe
  -> validate manifest
  -> negotiate profile requirements
  -> create isolated test namespace
  -> execute benchmark adapter
  -> retain benchmark-native results
  -> normalize eligible evidence
  -> generate qualification report
```

Safe components include:

- suite/profile discovery;
- manifest loading;
- capability negotiation;
- execution identity;
- temporary workspace/run identity;
- deterministic result paths;
- timeout/error classification;
- report collation;
- unsupported/blocked/not-applicable reporting.

### Wait

Do not claim one universal `gauntlet run` implementation is complete until at least one independent external memory system has entered through the same public adapter contract as Agent Memory/baselines.

## 6. Workstream C: Benchmark Coverage Atlas expansion

This is strongly parallel-safe.

### Candidate benchmark qualification queue

The Atlas should research/qualify credible suites that add distinct pressure, including at least:

- LoCoMo;
- MemoryAgentBench;
- MemBench;
- Memora/FAMA;
- Ground Truth First;
- Microsoft RHELM;
- Mem2ActBench;
- PerMemBench;
- AgentMemoryBench;
- AMA-Bench;
- Mem-Gallery;
- other newly discovered benchmarks that satisfy admission criteria.

Qualification is not integration.

For each candidate record:

```text
upstream identity/revision
license/data posture
artifact availability
protocol completeness
evaluator type
LLM/API dependence
reproducibility
cost
capability dimensions
unique pressure vs existing portfolio
privileged metadata risk
comparability constraints
status / blocker
```

### Admission rule

A benchmark should enter the execution portfolio only when it adds credible distinct pressure or materially stronger independent evidence.

Benchmark count is not a success metric.

## 7. Workstream D: Gauntlet-native gap analysis

Parallel-safe at the design level.

The Atlas should continually ask:

> Which important memory properties remain weakly measured or completely unmeasured across the qualified external portfolio?

Preliminary gap candidates include:

- governance/authority;
- memory metabolism across time;
- prospective/conditional memory;
- historical truth vs corrected falsehood;
- durable causal/relational memory;
- restart/recovery/tamper resistance;
- multi-agent/shared-memory governance;
- memory-to-action correctness;
- multimodal durable memory;
- long-horizon operational scaling;
- selective forgetting and deletion leakage.

Do not author a Gauntlet-native benchmark merely because a gap candidate exists.

Required promotion path:

```text
suspected gap
  -> external benchmark search
  -> coverage evidence
  -> extension/adaptation feasibility
  -> neutral threat/task model
  -> independent review where practical
  -> frozen protocol before Agent Memory tuning
  -> implementation
```

## 8. Workstream E: Governance Gauntlet

This can make meaningful progress now because it is system-neutral and claim-based.

### Safe first implementation slice

Build a deterministic governance conformance/attack fixture around dummy systems with declared capabilities.

First suite candidates:

1. tenant isolation;
2. scope isolation;
3. wrong-scope exact-match leakage;
4. caller-visible identifier leakage;
5. cardinality/count leakage;
6. deletion resurrection;
7. restart preservation of isolation/deletion claims;
8. recency-as-authority attack;
9. similarity-as-authority attack;
10. classifier/provenance laundering attack.

### Important neutrality rule

The suite tests claims, not PAMA conformance.

Example:

```text
system does not claim tenant isolation
    -> unsupported

system claims tenant isolation and leaks
    -> fail

system claims isolation through a larger composed application stack
    -> composition must be named; do not credit the memory subsystem alone
```

### Wait

Do not freeze Agent Memory-specific expected verdicts until the current public runtime/governance contract finishes converging.

## 9. Workstream F: Runtime identity and licensing

Issue #556 owns this boundary.

### Safe now

- define product separation principles;
- maintain naming criteria;
- identify package/repository/license decision points;
- document current Apache-2.0 ancestry;
- identify contribution/IP questions;
- perform preliminary collision research for candidate names;
- identify which interfaces must remain open for Gauntlet interoperability.

### Wait

Do not:

- rename the package/runtime;
- move code to a new repository;
- replace Apache-2.0 licensing;
- advertise a source-available/commercial model;
- adopt CLA/inbound-rights changes;

until an explicit maintainer decision and appropriate legal review exist.

## 10. Workstream G: Repository operating-model documentation

PR #541 predates the Gauntlet/five-layer model and should not be merged unchanged.

After #555 is reviewed/merged, refresh the existing #541 documentation rather than opening another competing README/governance PR.

The refreshed public documentation should describe:

```text
Agent Memory as umbrella/commons
Memory Evaluation as evidence machinery
Agent Memory Gauntlet as public qualification product
reference/conformance implementation
future distinct hardened runtime product
```

It should also reflect current benchmark/runtime state at the time of refresh rather than preserving stale RC claims.

## 11. Claude handoff gate

Do not prepare a final implementation prompt based on guesses about Claude's current branch.

When Claude reaches its stopping point, obtain an exact final-convergence report containing:

```text
main revision observed
working branch + head
open PR(s)
merged PR(s)
issues closed / still open
runtime/public contract version
ADR-039 evidence status
ADR-039 recommendation: accept / narrow / keep proposed / reject
benchmark runs completed
exact evidence revisions/digests
regressions
known blockers
next recommended work
```

Then compare that package against this roadmap.

## 12. Decision tree when Claude finishes

### Case A: ADR-039 remains Proposed but runtime contract is stable

Proceed with:

1. canonical Agent Memory Gauntlet adapter against the stable public API;
2. external dummy/baseline adapter conformance;
3. first executable Governance Gauntlet slice;
4. one external-memory-system adapter;
5. selected orthogonal benchmark integration.

Keep ADR-039-specific semantics represented as declared capabilities rather than mandatory Gauntlet ontology.

### Case B: ADR-039 becomes Accepted

In addition to Case A:

- update capability vocabulary for the accepted temporal contract;
- add temporal-intent/validity support to the Agent Memory adapter manifest;
- add applicable historical/current/adversarial cases to the Governance Gauntlet;
- update Coverage Atlas coverage states from proposed/partial to measured where evidence supports it.

### Case C: ADR-039 is narrowed

Update adapter capability vocabulary and Atlas dimensions to the narrowed doctrine before freezing schemas.

Do not preserve abandoned ADR concepts merely because the Gauntlet specification happened to mention them.

### Case D: stable runtime contract is still changing

Continue only with external/dummy adapter, Atlas, benchmark qualification, governance threat design, and product/licensing documentation.

Do not make the Gauntlet's public contract chase an unstable private implementation.

## 13. Candidate next implementation sequence

Assuming Claude returns a stable public runtime boundary, the recommended sequence is:

```text
Phase 1
  adapter manifest schema
  operation envelope schema
  capability negotiation
  adapter validator

Phase 2
  baseline/dummy adapter
  Agent Memory adapter
  adapter conformance tests

Phase 3
  Gauntlet CLI orchestration
  agent-memory gauntlet list
  agent-memory gauntlet inspect
  agent-memory gauntlet validate-adapter
  agent-memory gauntlet run

Phase 4
  Governance Gauntlet isolation/deletion slice
  normalized governance evidence
  coverage report

Phase 5
  one external memory implementation adapter
  prove system-neutral execution end to end

Phase 6
  expand qualified benchmark portfolio
  continuously maintain Coverage Atlas
```

## 14. Completion criteria for a public Gauntlet alpha

Do not call the Gauntlet public alpha-ready until:

- adapter contract schema exists and is validated;
- at least Agent Memory, one trivial baseline, and one genuinely external memory implementation execute through it;
- at least two heterogeneous benchmark profiles run through orchestration without rewriting their native semantics;
- Governance Gauntlet has at least one real claim-based suite;
- normalized/native evidence provenance is explicit;
- unsupported/blocked/not-applicable states remain distinct;
- privileged metadata/fairness rules are enforced;
- destructive reset/delete operations are sandboxed;
- evaluator/runtime failures are attributable;
- docs explain how an external maintainer enters the Gauntlet;
- no universal memory-health score is introduced.

## 15. Invariants

```text
adapter translation != system capability
unsupported != failed
benchmark score != truth
benchmark score != authority
Gauntlet-native evidence != independent evidence
benchmark count != coverage
Gauntlet != Agent Memory runtime conformance only
surviving the Gauntlet != infallibility
```

## 16. Related artifacts

- issue #554
- issue #556
- PR #555
- PR #541, to refresh after Gauntlet foundation settles
- `docs/AGENT_MEMORY_PROJECT_MODEL.md`
- `docs/GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`
- `docs/BENCHMARK_COVERAGE_ATLAS.md`
- `docs/GOVERNANCE_GAUNTLET_SPECIFICATION.md`
- `docs/RUNTIME_IDENTITY_NAMING_BRIEF.md`
- `docs/53-memory-evaluation-subsystem.md`
- `docs/54-memory-evaluation-cli.md`
