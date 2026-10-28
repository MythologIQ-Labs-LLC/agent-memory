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

### Entry points and the five-layer project model

The root `README.md` presents the three roles to visitors as three entry points: **Theory** (architecture/governance laboratory), **Benchmarks** (evaluation/benchmark laboratory), and **Runtime** (product/runtime). Those are the same roles with audience-facing names, not a fourth description of the repository.

[`AGENT_MEMORY_PROJECT_MODEL.md`](AGENT_MEMORY_PROJECT_MODEL.md) describes the wider project as five layers: architecture/doctrine/research commons, Memory Evaluation, the Agent Memory Gauntlet, the reference/conformance implementation, and a future distinct production runtime. Per the ruling in [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565), the three roles describe what this repository *does* operationally today, while the five layers describe how the project is *partitioned* for community, evaluation, qualification, reference implementation, and future product/licensing boundaries ([#556](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/556)). The five-layer model refines the product/runtime role into reference/conformance implementation plus future distinct runtime, and refines the evaluation role into Memory Evaluation plus the public Gauntlet. Neither formulation supersedes the other, and this document remains the operating guidance for the roles.

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

## Component ownership, exit criteria and active priority

The three roles are **operational boundaries**, not three separate products or three equal-priority development queues. The five-layer project model remains governed by [AGENT_MEMORY_PROJECT_MODEL.md](AGENT_MEMORY_PROJECT_MODEL.md); this section defines how work is routed without duplicating that model.

| Role | Owns | Stops at / hands off | Completion evidence |
|---|---|---|---|
| **Runtime** | Developer-facing API, governed storage and lifecycle, candidate generation, retrieval admission, ranking, context delivery, and runtime security | Does not encode benchmark labels or turn benchmark verdicts into runtime authority; sends version-pinned behavior to Evaluation | Source changes, contract/security regression tests, and qualified runtime behavior including retrieval precision, recall and correct abstention |
| **Theory / architecture / lessons** | Memory semantics, hypotheses, research synthesis, architectural decisions, failure lessons, and governance doctrine | Does not make a proposed mechanism implemented, qualified, or empirically superior; hands implementation requirements to Runtime and falsifiable hypotheses to Evaluation | Explicit accepted decisions where required, clear hypothesis/evidence distinction and traceable research/decision history |
| **Benchmarking / Gauntlet** | Benchmark catalog, neutral SUT adapters, benchmark-native protocols and metrics, controlled execution, evaluator integrity, comparable evidence, scorecards and reproducible external entry | Does not own SUT internals, rewrite native benchmark scoring, grant memory authority or treat incompatible protocols as a single leaderboard | Frozen run identity, benchmark-native scores, comparison eligibility/coverage, evaluator-integrity evidence and reproducible receipts |

**Gauntlet** means the public-facing umbrella of benchmark and assessment instruments used to pressure-test Agent Memory **and any participating memory system**. It is not one monolithic benchmark, the Agent Memory runtime, a separate authority service, or solely a conformance checklist. Its orchestrator and system/benchmark adapters connect memory systems to a portfolio of workloads; Memory Evaluation owns normalized evidence and reporting. A separately specified assessment profile, such as a proposed MemoryCheckpointAssessment, may join that portfolio after integration and qualification; its draft existence is not proof it has shipped.

A result is **directly comparable** only when the benchmark revision, selection, native metric, operation protocol, adapter contributions and material execution conditions align. Otherwise declare the documented conditional comparison or **not directly comparable**; do not silently pool retrieval-only and answer-generation results, and do not collapse missing or unsupported states into zero. External user-submitted results remain distinguished from independently reproduced runs.

**Present delivery priority: improve the Agent Memory runtime**, especially actual retrieval precision and answer/task correctness without abandoning recall, security, or abstention. Evaluation should supply bounded evidence and targeted replay for runtime changes; theory should clarify demonstrated gaps. Neither Gauntlet expansion nor documentation consolidation should displace runtime engineering without a separately authorized priority change. This priority statement is a routing rule, not a release/readiness assertion; live status belongs to [BACKLOG.md](BACKLOG.md), [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410) and the baseline register.

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

External evidence separated strong areas, such as governed isolation and deletion, from weaker areas: currentness ranking, thread-safe host integration, and scaling efficiency. Those findings became bounded product and architecture issues rather than footnotes in benchmark reports.

Each remediation slice is replayed against the same frozen input. The slices are recorded in [`56-benchmark-gauntlet-remediation-evidence.md`](56-benchmark-gauntlet-remediation-evidence.md):

- explicit ranking policy;
- runtime-owned handle serialization;
- incremental attestation;
- query-conditioned applicability;
- the domain-eligibility prefilter.

The cycle also produced examples of each learning class:

| Class | Example |
|---|---|
| implementation defect | unsafe cross-thread handle use (#530) |
| runtime/product contract gap | tenant-wide candidate generation exposing foreign refusals (#548, contract 1.3.0) |
| architecture gap against existing doctrine | historically true superseded state was unrepresentable (#549) |
| explicit product limitation | implicit supersession without a governed correction (#531 class B) |
| doctrine proposal, not acceptance | query-conditioned applicability (ADR-039, Proposed; #544) |

Evidence can change product behavior quickly. Doctrine changes only through a separate ruling.

The controlling benchmark-remediation architecture issue is #537.

## Repository organization expectations

The repository should make its three roles discoverable:

```text
README.md                     Theory / Benchmarks / Runtime entry points + project overview
docs/README.md                documentation index, mirrored on the same three entry points
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