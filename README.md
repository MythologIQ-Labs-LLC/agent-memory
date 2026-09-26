<p align="center">
  <img src="assets/brand/agent-memory-readme-banner.png" alt="Agent Memory: governed memory architecture for AI agents, shown with a layered memory stack, connected nodes, and a cyan inference spark." width="100%">
</p>

<div align="center">

# 01010001 Agent Memory

<p><sub><strong>Q Agent Memory</strong></sub></p>

### Governed persistent cognition for autonomous and agentic systems

A usable governed memory runtime, a canonical architecture and doctrine corpus, and a reproducible evaluation laboratory for testing both against external pressure.

[![Validate Doctrine Evidence](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml/badge.svg)](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml)
![Architecture](https://img.shields.io/badge/Architecture-Governed%20Cognitive%20Framework-334155)
![Maturity](https://img.shields.io/badge/Maturity-RC%20evidence%20phase-b45309)
[![ADRs](https://img.shields.io/badge/ADRs-Canonical%20Index-2563eb)](docs/adr/README.md)
[![License](https://img.shields.io/badge/License-Apache--2.0-0b7285)](LICENSE)

**[Documentation](docs/README.md)** · **[Repository operating model](docs/REPOSITORY_OPERATING_MODEL.md)** · **[Benchmarks](BENCHMARKS.md)** · **[Scorecards](reports/benchmarks/scorecards/scorecards.md)** · **[RC1 profile](docs/45-agent-memory-rc1-implementation-profile.md)** · **[PAMA](docs/pama/README.md)** · **[Governance](GOVERNANCE.md)**

</div>

---

> [!IMPORTANT]
> **Current status: executable product/runtime plus active architecture and benchmark laboratory.**
>
> Agent Memory is no longer only a reference architecture. The repository contains a developer-facing `AgentMemory` facade, governed memory lifecycle operations, restart-safe local persistence, a bounded qualified SQLite substrate, multi-route recall, native semantic/vector and typed temporal/entity/causal machinery, native cognitive metabolism, correction/deletion/history paths, benchmark adapters, evaluator-integrity tooling, normalized evidence, and deterministic cross-benchmark scorecards.
>
> It is **not** a production 1.0 claim. The qualified runtime posture is deliberately bounded, especially to the declared single-host SQLite profile. External benchmark pressure is actively exposing and driving remediation of currentness/ranking, concurrency, and scaling weaknesses. RC composition and release posture remain governed by issue #410.

## What this repository is now

Agent Memory serves three connected roles:

| Role | What lives here | What it does not mean |
|---|---|---|
| **Product / runtime** | Installed developer facade, governed memory lifecycle, qualified SQLite path, recall, correction, forgetting, history, posture | Production 1.0 or distributed readiness |
| **Architecture / governance lab** | ADRs, PAMA, lifecycle/currentness doctrine, memory metabolism, identity/provenance/authority boundaries, research synthesis | Doctrine is immune from falsification |
| **Evaluation / benchmark lab** | LongMemEval, AgentMemBench/MemDialogue, SWE-ContextBench adapters, evaluator-integrity probes, frozen reports, normalized manifests, scorecards | Benchmark score becomes truth or authority |

See **[Repository Operating Model](docs/REPOSITORY_OPERATING_MODEL.md)** for the canonical relationship between those roles.

The core development loop is now:

```text
architecture
    -> implementation
    -> internal conformance
    -> external benchmark pressure
    -> product / architecture gap discovery
    -> bounded remediation
    -> same frozen benchmark replay
```

The goal is not to make every benchmark green. The goal is to force the architecture and product to survive independent workloads without silently weakening governance to chase a number.

---

## What Agent Memory means by memory

**Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That is intentionally broader than RAG, vector search, a graph database, a conversation transcript, or a single cache.

Agent Memory composes multiple memory responsibilities while keeping their semantics and authority distinct:

```text
experience / observation
        |
        v
+----------------------- Cognitive Plane -----------------------+
| working memory / attention                                   |
| semantic + epistemic memory                                  |
| procedural / skill memory                                    |
| predictive / counterfactual memory                           |
| cognitive metabolism / consolidation                         |
+---------------------------------------------------------------+
        |
        +---------------- Reality Plane ------------------------+
        | temporal / entity / causal / code-domain evidence     |
        +-------------------------------------------------------+
        |
        +---------------- Authority Plane ----------------------+
          PAMA
          governed recall admission
          scope / tenant / isolation
          correction / supersession / dispute
          deletion / forgetting
          certification / durable consequence

Cross-cutting: identity, evidence, provenance, calibration, conformance
```

The canonical architecture is established by **[ADR-035](docs/adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md)**.

> A substrate is not the memory system. A retrieval strategy is not the memory system. A graph is not the memory system. They are bounded participants in Agent Memory.

Agent Memory is also the canonical owner of generic memory machinery implemented here. EvolveAI, CodeGenome, COREFORGE, UOR-derived mechanisms, Jev/Jev-Mem, research papers, and other systems may supply implementation ancestry, evidence, mechanisms, comparison surfaces, or downstream integration. They do not become permanent runtime owners merely because useful ideas were harvested from them.

---

## Governing doctrine

The architecture separates uncertain inference from durable consequence:

> **Probabilistic epistemics. Governed consequences.**
>
> **Uncertainty may propose. Authority constrains.**

Common invariants include:

```text
candidate retrieval != governed recall admission
ranking != recall admission
classifier output != truth
confidence != permission
recency != authority
similarity != authority
recommendation != mutation authority
benchmark score != memory authority
```

A model, heuristic, retriever, classifier, temporal signal, decay score, benchmark result, or external verifier may contribute evidence. None of those creates its own permission to mutate canonical memory or influence active cognition outside the governed path.

### PAMA

**Proportional Adaptive Mutation Authority (PAMA)** is Agent Memory's native mutation-authority doctrine.

```text
adaptation != authority
memory != procedure
procedure != permission
permission != governance
```

PAMA evaluates proposed consequences across target class, lifecycle strength, requested operation, downstream authority, reversibility, evidence, scope, risk, review and verification state.

See **[PAMA](docs/pama/README.md)**, **[Governance and PAMA](docs/04-governance-and-pama.md)**, and **[PAMA Decision Table](docs/33-pama-decision-table.md)**.

---

## Use the runtime

From a checkout:

```bash
python -m pip install .
```

Then:

```python
from agentmem_ref import AgentMemory

with AgentMemory.open("./agent-memory-state", tenant="tenant:local") as memory:
    memory.remember(
        "memory:preferred-editor",
        "Preferred editor is VS Code",
    )

    recalled = memory.recall(
        "preferred editor",
        logical_memory_refs=("memory:preferred-editor",),
    )

    history = memory.history("memory:preferred-editor")
    posture = memory.posture()
```

The facade is a convenience layer over the governed public contract and qualified local runtime. Convenience does not create authority. Corrections, permanent deletion, and other consequential operations remain subject to their existing governance paths.

See **[Developer Facade and Local Open Path](docs/47-developer-facade-and-local-open-path.md)**.

---

## Implemented product surface

The repository is strict about the difference between **implemented**, **qualified**, **benchmarked**, and **production-ready**.

| Surface | Current posture |
|---|---|
| Developer `AgentMemory.open()/remember()/recall()/correct()/forget()/history()/posture()` facade | Implemented |
| Canonical semantic memory | Executable governed runtime |
| Epistemic belief memory | Executable with confidence, evidence, dispute and retraction lineage |
| Procedural / skill memory | Executable with action-authority separation |
| Predictive / counterfactual memory | Executable governed surface |
| Governed recall admission | Executable scope/tenant/project/currentness boundary; a domain-eligibility prefilter minimizes candidates without granting anything (contract 1.3.0) |
| Historical-evidence admission | Executable: superseded state from a governed state change is admitted only under explicit historical/as-of intent, labelled non-current |
| Multi-route retrieval | Executable lexical, exact, relational and other bounded routes with provenance |
| Native semantic/vector retrieval | Implemented |
| Typed temporal/entity/causal traversal | Implemented |
| Native cognitive metabolism | Implemented deterministic decay/reinforcement/consolidation/pruning evidence and proposal surface |
| Correction / supersession | Executable and restart-safe in the declared reference profile; error correction vs state change is recorded |
| Forgetting / tombstones | Executable, evidence-bearing and restart-safe in the declared profile |
| SQLite canonical substrate | Qualified for bounded single-host RC use |
| Distributed/multi-host persistence | Not established |
| Production 1.0 readiness | Not claimed |

Current known limitations:

- Query-conditioned applicability (policy 3.0.0) is implemented, but **ADR-039 remains Proposed**. No orthogonal temporal gauntlet has yet tested it.
- Implicit supersession, where a newer statement contradicts an older one without a governed correction, is not inferred (#531 class B).
- The replacement kind (error correction vs state change) is caller-declared within a governed correction.
- Per-commit persistence still digests and rewrites the whole governance state (#562: ~0.73 s per write at ~10,000 facts). Lexical candidate generation still visits every fact in the tenant (#563). Scale beyond the measured sizes is not claimed.
- Temporal-intent cues are a small English lexicon.

Current product and substrate maturity is documented in **[docs/43-substrate-inventory-and-maturity.md](docs/43-substrate-inventory-and-maturity.md)** and the **[RC1 profile](docs/45-agent-memory-rc1-implementation-profile.md)**.

---

## Benchmarks are a first-class subsystem

Agent Memory keeps benchmark adapters, evidence, and evaluator integrity alongside the implementation so an external result can be tied to an exact system revision and replayed after remediation.

Current portfolio highlights:

| Profile | Status | What it currently tells us |
|---|---|---|
| **LongMemEval_S** | Complete frozen external run, plus remediation replays | Retrieval/currentness behavior, operational cost, zero runtime failures on the measured profile; exposed ranking/currentness weaknesses |
| **LongMemEval_M** | Held | Not run until per-commit persistence (#562) is bounded; running it now would re-measure a known quadratic ingest |
| **AgentMemBench / MemDialogue** | Complete bounded external run | Retrieval, conflict/currentness, deletion, isolation, concurrency, scaling; exposed thread-affinity and scaling defects |
| **SWE-ContextBench Lite** | Protocol-comparable external run blocked | Harness/evidence contract exists; exact frozen research-compatible corpus/provenance is still required |
| **Internal RC retrieval fixture** | Complete | Demonstrates composed routes can recover memories lexical-only recall misses while preserving governance on the synthetic fixture |

The generated scorecard is at **[`reports/benchmarks/scorecards/scorecards.md`](reports/benchmarks/scorecards/scorecards.md)**. Regeneration and evidence semantics are documented in **[Memory Evaluation Scorecards](docs/55-memory-evaluation-scorecards.md)**.

Important boundaries:

```text
retrieval score != answer-generation quality
synthetic fixture != external efficacy
benchmark validation != benchmark quality
benchmark quality != production readiness
benchmark score != authority
```

The benchmark program is explicitly a learning system. Findings are classified as architecture validation, implementation defect, architecture gap, runtime/product contract gap, evaluation defect/gap, benchmark mismatch, or inconclusive before remediation is promoted into product behavior.

See **[BENCHMARKS.md](BENCHMARKS.md)** and **[Memory Evaluation subsystem](docs/53-memory-evaluation-subsystem.md)**.

---

## Current benchmark-driven remediation

The external gauntlets have not falsified Agent Memory's core authority/lifecycle architecture, but they exposed concrete product weaknesses. Remediation is tracked under issue #537, with every slice replayed against the same frozen input. The before/after evidence is in **[docs/56](docs/56-benchmark-gauntlet-remediation-evidence.md)**.

| Finding | Remediation | State |
|---|---|---|
| Ranking/currentness policy was implicit (#538, #531 class A) | Explicit post-admission ranking policy, admitted-set BM25, and a query-conditioned applicability profile (policy 3.0.0) | Landed. **[ADR-039](docs/adr/ADR-039-recall-ranking-uses-query-conditioned-applicability.md) remains Proposed** (#544) |
| Unsafe cross-thread use of one handle (#530) | Runtime-owned serialization | Landed |
| O(state) integrity work on every commit (#522 Part A) | Incremental attestation | Landed |
| Every tenant fact became a recall candidate (#522 Part B, #548) | Privacy-preserving domain-eligibility prefilter; public contract 1.3.0 | Landed (#552) |
| Historically true but superseded state was unrepresentable (#549) | Explicit current-state vs historical-evidence admission ([docs/58](docs/58-historical-evidence-admission.md)) | Landed (#553) |
| Implicit-supersession questions (#531 class B) | Recorded as an explicit product limitation, not reopened | Limitation |

Still open or held:

- per-commit governance-state persistence (#562) and lexical candidate generation (#563), which dominate at 5,000–10,000 facts;
- LongMemEval_M, held until #562 is bounded;
- an orthogonal temporal gauntlet ([docs/59](docs/59-orthogonal-temporal-gauntlet-qualification.md));
- the external SWE-ContextBench corpus (#467).

The benchmark results are treated as falsification surfaces rather than README decoration:

```text
benchmark score != doctrine
implementation evidence != doctrine acceptance
```

---

## Persistence and integrity

The reference persistence path includes explicit state ownership, governed adapter state, restart recovery, generation boundaries, stale-writer protection, journaling/integrity evidence, schema/profile migration, and qualified single-host SQLite execution.

The native `SQLiteTemporalGraph` / `sqlite_single_host_v1` profile earned bounded single-host qualification. That does not imply distributed consensus, multi-host safety, universal operational scaling, or production 1.0.

See **[State checkpoint contract](docs/46-state-checkpoint-contract.md)**.

---

## Repository structure

```text
reference/agentmem_ref/
├── core/        PAMA, receipts, evidence, verification, contextual recall
├── state/       canonical substrates, graph/state drivers, projections
├── contracts/   capability declarations, qualification, substitution
├── runtime/     governed adapter, restart, transactions, composition, CLI
├── memory/      semantic-adjacent memory modules, epistemic/procedural/etc.
├── api/         versioned public contract surfaces
├── crg/         Agent Memory Code Reality Graph / code-domain integration
└── evaluation/  benchmark-neutral validation/comparison/scorecard machinery

reference/       runtime, runners, benchmark adapters, tests
schemas/         machine-readable contracts
fixtures/        conformance and adversarial fixtures
docs/            doctrine, ADRs, product profiles, research, evaluation guidance
reports/         frozen and normalized benchmark evidence
sources/         source/provenance/right-to-reuse records
```

Package placement and architecture-layer rules are enforced by repository validation.

---

## Evidence and maturity discipline

A statement in this repository should make clear whether it is:

```text
doctrine
product contract
implementation
conformance evidence
benchmark evidence
field evidence
research / ancestry
hypothesis
```

Those are not interchangeable.

The repository's evidence policy is source-neutral: native ideas do not become correct because they originated here, and external ideas do not become correct because they are published or popular. Evidence may support, challenge, narrow, or supersede doctrine through the governed decision process.

See **[GOVERNANCE.md](GOVERNANCE.md)** and **[Evidence Promotion Policy](docs/policies/EVIDENCE_PROMOTION.md)**.

---

## Contributing

Start with:

1. **[Repository Operating Model](docs/REPOSITORY_OPERATING_MODEL.md)**
2. **[Contributing](CONTRIBUTING.md)**
3. **[Governance](GOVERNANCE.md)**
4. **[Documentation index](docs/README.md)**
5. **[Architecture decisions](docs/adr/README.md)**
6. **[Benchmarks](BENCHMARKS.md)** for evaluation work

Material changes should identify whether they affect product/runtime behavior, architecture/doctrine, evaluation/evidence, contracts/schemas, documentation, or security/governance. A change may span those categories, but the span should be explicit.

---

## License

Agent Memory is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Third-party sources, datasets, benchmark corpora, and referenced implementations retain their own licenses and attribution requirements. See **[SOURCE_RIGHTS_POLICY.md](docs/SOURCE_RIGHTS_POLICY.md)** and the source registry.
