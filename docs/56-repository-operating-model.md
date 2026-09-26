# Repository Operating Model

Status: canonical repository operating guidance for the current Agent Memory development phase.

## Purpose

Agent Memory began as a doctrine and reference-architecture repository. It now contains a usable governed runtime, first-party memory implementations, reproducible benchmark infrastructure, external benchmark evidence, evaluator-integrity tooling, and an active architecture-learning loop.

The repository therefore serves three related but distinct roles:

```text
Agent Memory repository
    |
    +--> Product / runtime
    |      usable developer-facing memory system
    |      reference + qualified single-host SQLite execution
    |
    +--> Architecture / governance laboratory
    |      doctrine, ADRs, PAMA, lifecycle semantics
    |      theory, ancestry harvest, adversarial design review
    |
    +--> Evaluation / benchmark laboratory
           external benchmark adapters
           frozen evidence, scorecards, evaluator integrity
           before/after remediation and falsification
```

These roles reinforce one another, but they do not inherit authority from one another automatically.

## 1. Product and runtime role

Agent Memory is an actual software product surface, not only a theoretical framework.

The repository contains a developer-facing `AgentMemory` facade, governed memory lifecycle operations, restart-safe local persistence, a bounded qualified SQLite substrate, multi-route recall, native semantic/vector and typed temporal/entity/causal machinery, native memory metabolism, and multiple governed memory responsibilities.

The supported local product path is documented in [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md).

Product claims must remain bounded by evidence. In particular:

```text
usable runtime != production 1.0
single-host qualification != distributed readiness
implemented capability != benchmark superiority
passing conformance != field efficacy
```

## 2. Architecture and governance laboratory role

The repository remains the canonical home of Agent Memory doctrine and architecture.

This includes:

- architectural invariants;
- ADRs;
- PAMA mutation-authority doctrine;
- memory lifecycle and currentness semantics;
- identity, provenance, evidence, scope and isolation contracts;
- determinism/probability boundaries;
- memory metabolism, reinforcement, consolidation and pruning semantics;
- first-party ownership boundaries for generic memory machinery;
- research synthesis and implementation ancestry.

Architecture is expected to be challenged by implementation and external evidence. Accepted doctrine is not immune from revision merely because it is canonical.

The repository should preserve the distinction:

```text
canonical doctrine
    != unquestionable doctrine
```

A benchmark, production observation, external implementation, research paper, or contributor argument may falsify or narrow an architectural assumption. A doctrine change still requires the repository's explicit decision process.

## 3. Evaluation and benchmark laboratory role

Evaluation is now a first-class repository function.

The Memory Evaluation subsystem owns benchmark adapters, common evidence contracts, evaluator-integrity checks, normalized run manifests, deterministic comparisons, scorecards, and portfolio reporting.

Current entry points include:

- [`BENCHMARKS.md`](../BENCHMARKS.md)
- [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md)
- [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md)
- [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md)
- `reports/benchmarks/normalized/`
- `reports/benchmarks/scorecards/`

Evaluation exists to pressure and falsify the product and architecture, not to manufacture a flattering leaderboard.

Required invariant:

```text
benchmark score != truth
benchmark score != authority
benchmark score != product requirement by itself
```

## Evidence-to-change flow

External evaluation should normally move through this loop:

```text
benchmark / field evidence
        |
        v
observation
        |
        v
classification
  architecture validated
  implementation defect
  architecture gap
  runtime/product contract gap
  evaluation defect/gap
  benchmark mismatch
  inconclusive
        |
        v
bounded issue + hypothesis
        |
        v
remediation
        |
        v
same frozen evidence replay
        |
        v
before/after analysis
        |
        +--> product change
        +--> regression test
        +--> doctrine clarification/change if warranted
        +--> explicit known limitation
```

A benchmark-discovered defect is not considered resolved merely because unit tests turn green. Where the benchmark can exercise the repaired path, closure should include a replay against the same frozen workload or a documented reason why that replay is not valid.

## Evidence classes and promotion

Repository artifacts should make their status visible. Useful classes include:

| Class | Meaning |
|---|---|
| **Doctrine** | Accepted architectural or governance decision |
| **Product contract** | Supported behavior callers may rely on within the declared profile |
| **Implementation** | Executable behavior currently present in the repository |
| **Conformance evidence** | Evidence that an implementation satisfies a declared contract |
| **Benchmark evidence** | Measured behavior on a specific frozen workload |
| **Field evidence** | Observation from a real deployment or longitudinal use |
| **Research / ancestry** | Prior art, source mechanism, external research, or historical implementation used for learning |
| **Hypothesis** | Proposed explanation or design direction requiring validation |

Promotion between these classes is deliberate. For example:

```text
benchmark observation
    -/-> doctrine automatically

research mechanism
    -/-> runtime dependency automatically

passing internal fixture
    -/-> external efficacy claim automatically
```

## Cross-role boundaries

### Product does not own doctrine by accident

A convenient implementation shortcut does not become architecture merely because it ships.

### Doctrine does not override empirical failure

If external evidence repeatedly falsifies an assumption, the repository should revisit the assumption rather than protecting it through increasingly elaborate explanation.

### Benchmarks do not become runtime authority

No benchmark-specific rule, dataset identifier, query phrase, or hidden special case should enter runtime behavior solely to improve a score.

### Research ancestry does not create runtime ownership

EvolveAI, CodeGenome, COREFORGE, UOR-derived mechanisms, Jev/Jev-Mem, external papers, and other systems may provide mechanisms, evidence, or comparison surfaces. Agent Memory remains the canonical owner of generic memory behavior implemented here unless an explicit architecture decision says otherwise.

## Current benchmark-learning phase

The current development phase is intentionally adversarial.

Agent Memory has moved through:

```text
architecture formation
    -> native implementation
    -> internal conformance
    -> external benchmark pressure
    -> product-gap discovery
    -> bounded remediation
    -> frozen benchmark replay
```

Recent external evidence has already separated strong areas such as governed isolation/deletion from weaker areas such as currentness ranking, thread-safe host integration, and scaling efficiency. Those findings are tracked as product/architecture issues rather than hidden in benchmark reports.

The controlling benchmark-remediation architecture issue is #537.

## Repository organization expectations

The repository should make its three roles discoverable:

```text
README.md                     product + project overview
reference/                    executable product/reference implementation
reference/agentmem_ref/       installed implementation
schemas/                      machine-readable contracts
fixtures/                     conformance/adversarial fixtures
docs/                         doctrine, architecture, product profiles, evaluation guidance
docs/adr/                     canonical architecture decisions
reports/benchmarks/           frozen and normalized benchmark evidence
BENCHMARKS.md                 evaluation entry point
GOVERNANCE.md                 repository decision and evidence governance
CONTRIBUTING.md               contribution and validation workflow
```

A new contributor should be able to tell whether a change affects runtime behavior, doctrine, evaluation, or more than one of those surfaces.

## Change classification

Every material PR should identify its principal consequence class:

- `product/runtime`
- `architecture/doctrine`
- `evaluation/evidence`
- `contract/schema`
- `documentation/editorial`
- `security/governance`

A PR may span classes, but the span should be explicit. Benchmark harness fixes should not silently change product behavior. Product remediations should not silently rewrite benchmark denominators. Doctrine changes should identify the evidence that motivated them.

## Completion principle

The repository is successful when the three roles remain mutually corrective:

- architecture gives product behavior principled boundaries;
- product execution turns doctrine into falsifiable reality;
- evaluation exposes where either one fails;
- governance prevents any one layer from silently granting itself authority.

That operating model is now part of Agent Memory's identity, not temporary benchmark scaffolding.