<p align="center">
  <img src="assets/brand/agent-memory-readme-banner.png" alt="Agent Memory: governed memory architecture for AI agents, shown with a layered memory stack, connected nodes, and a cyan inference spark." width="100%">
</p>

<div align="center">

# 01010001 Agent Memory

<p><sub><strong>Q Agent Memory</strong></sub></p>

### Governed persistent cognition for autonomous and agentic systems

A canonical memory architecture and doctrine corpus, a reproducible evaluation laboratory, and a usable governed memory runtime that the other two keep honest.

[![Validate Doctrine Evidence](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml/badge.svg)](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml)
![Architecture](https://img.shields.io/badge/Architecture-Governed%20Cognitive%20Framework-334155)
![Maturity](https://img.shields.io/badge/Maturity-RC%20evidence%20phase-b45309)
[![ADRs](https://img.shields.io/badge/ADRs-Canonical%20Index-2563eb)](docs/adr/README.md)
[![License](https://img.shields.io/badge/License-Apache--2.0-0b7285)](LICENSE)

**[Theory](#theory)** · **[Benchmarks](#benchmarks)** · **[Runtime](#runtime)** · **[Documentation index](docs/README.md)** · **[Current dashboard](reports/benchmarks/dashboard/current.md)** · **[Governance](GOVERNANCE.md)**

</div>

---

> [!IMPORTANT]
> **Current status: executable governed runtime plus an active RC evidence program. Not a production 1.0 claim.**
>
> The qualified runtime posture is deliberately bounded to the single-host SQLite profile. Distributed or multi-host persistence is not established, and no substrate other than `SQLiteTemporalGraph` is production-qualified. RC composition remains governed by issue [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410); the current work queue is [`docs/BACKLOG.md`](docs/BACKLOG.md); the canonical benchmark view is [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md).

## What Agent Memory is

**Agent Memory includes working software, not just a memory-design proposal.** The installable `agent-memory-reference` Python package exposes an [`AgentMemory` facade](#runtime) with persistent single-host SQLite memory, governed writes and recall, scope-aware evidence admission, history and posture inspection. The [runtime example below](#runtime) is executable from a checkout. This is a usable reference/conformance implementation **in active release-candidate qualification**, not a drop-in production service or certified security boundary.

| Present in the repository | Not shipped or not qualified |
|---|---|
| Python runtime, `SQLiteTemporalGraph` persistence, governed lifecycle and public facade | Distributed/multi-host persistence, production 1.0 security boundary, or qualified Postgres substrate |
| Lexical and optional semantic candidate retrieval, with governed admission and a bounded returned context | Proven speed or quality gains on somebody else's existing agent or memory database |
| System-neutral evaluation adapters, reproducible benchmark machinery, evidence and dashboard | A universal benchmark score or same-harness comparisons with every competitor |
| Canonical doctrine, accepted/proposed ADRs and explicit architecture plans | Complete heterogeneous GraphRAG/Markdown/distributed composition as a qualified runtime |

**Evaluating adoption?** Compare the [actual runtime](#runtime) with a competently *indexed* local-memory baseline using your own representative workload. Measure correct evidence, stale-memory behavior, exclusions/abstention, context cost, latency and integration burden. Our local benchmark measurements do **not** establish performance on your data. The [Jarvis-scale synthetic evaluation](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/825) **has run a real Agent Memory arm** against an indexed FTS5 control on fabricated records. Both remain weak on task correctness and abstention. This is a small development cohort with unequal persistence/governance costs, **not** accepted evidence of competitive adoption readiness.

**Known measured quality limitation:** [#819](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/819) tracks excessive irrelevant recall on an external retrieval-only evaluation. High recall alone does not establish useful, selective task context. An opt-in [#691 selective-context experiment](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/691) improved known development cases but **lost required evidence in full LongMemEval and was rejected for integration**. [#775](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/775) currently explores lexical versus claimed subject/relationship evidence **in evaluation-only code**, not the shipped runtime. Consult the [current evidence dashboard](reports/benchmarks/dashboard/current.md) and the exact issue evidence before adopting or claiming comparative performance; this README does not own benchmark scores or qualification decisions.

Long-term, [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) proposes governed composition of structured, episodic, temporal, procedural, vector and graph-derived memory. That entire composition **is not shipped**. The [substrate inventory](docs/43-substrate-inventory-and-maturity.md) owns current maturity claims; only the single-host SQLite profile is qualified.

## Start here

| Goal | Start | Next |
|---|---|---|
| Use the memory engine | **[Runtime](#runtime)** | [API contract](docs/44-public-api-contract.md), [developer open path](docs/47-developer-facade-and-local-open-path.md) |
| Evaluate performance or compare systems | **[Benchmarks](#benchmarks)** | [Current dashboard](reports/benchmarks/dashboard/current.md), [coverage](docs/BENCHMARK_COVERAGE_ATLAS.md), [external adapters](docs/CONTRIBUTOR_ARCHITECTURE.md) |
| Study governance or propose architecture | **[Theory](#theory)** | **[Architecture Index](docs/ARCHITECTURE_INDEX.md)**, [ADRs](docs/adr/README.md), [PAMA](docs/pama/README.md) |

These are three **operational roles**, not three separately production-ready products. The [operating model](docs/REPOSITORY_OPERATING_MODEL.md) explains them; the [five-layer project model](docs/AGENT_MEMORY_PROJECT_MODEL.md) separates architectural commons, Memory Evaluation, Gauntlet, reference runtime and future production runtime under [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565). The **Architecture Index routes** claims. Actual capabilities, qualifications, baselines and scores remain authoritative in their respective code, contracts and evidence.

## Theory

**Probabilistic epistemics. Governed consequences.**

**Uncertainty may propose. Authority constrains.**

A model, retriever, classifier, temporal signal, decay score, benchmark result, or external verifier may contribute evidence. None creates its own permission to mutate canonical memory or to enter active cognition outside the governed path. The load-bearing invariants include:

```text
candidate retrieval != governed recall admission
ranking != truth
relevance != currentness
classifier confidence != permission
interpretation != authority
proposal != application
newer != superseding
recency != authority
benchmark score != memory authority
```

Every architectural lookup starts at [`docs/ARCHITECTURE_INDEX.md`](docs/ARCHITECTURE_INDEX.md), the single catalog that assigns each architecture document one shelf and one owner and states the filing rule for new ones. [`docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`](docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md) is the underlying architectural explanation; the individual ADRs ([index](docs/adr/README.md)), the schemas, the code, and accepted evidence keep factual authority for their own claims. [PAMA](docs/pama/README.md) and [`docs/04-governance-and-pama.md`](docs/04-governance-and-pama.md) own mutation authority. Implementation or benchmark evidence never silently promotes, supersedes, or rejects an ADR. The active policy and contract versions are owned by code, not prose: `reference/agentmem_ref/runtime/temporal_order_constraints.py` (`POLICY_VERSION`) and `reference/agentmem_ref/api/contract.py` (`CONTRACT_VERSION`). The longer invariant list in [`docs/64-current-governance-and-benchmark-dashboard.md`](docs/64-current-governance-and-benchmark-dashboard.md) is the **historical #591/#594 reconciliation** and reads as of that boundary.

Research briefs, explorations, and ancestry harvests are evidence and provenance, not doctrine; see [`docs/40-aligned-projects-and-intellectual-lineage.md`](docs/40-aligned-projects-and-intellectual-lineage.md) and [`docs/SOURCE_RIGHTS_POLICY.md`](docs/SOURCE_RIGHTS_POLICY.md).

## Benchmarks

Benchmarking is a first-class repository function. The canonical current evidence view is **[`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md)** (machine-readable: `current.json`). Numbers are intentionally not copied into this README; the dashboard distinguishes current accepted evidence, previous accepted evidence and deltas, evidence classes, and non-numeric states such as `not_run`, `blocked`, `unsupported`, and `evidence_gap`. There is no universal aggregate score.

| If you want to | Go to |
|---|---|
| Understand the portfolio, evidence classes, and the rules for benchmark-driven change | [`BENCHMARKS.md`](BENCHMARKS.md) |
| See which memory capabilities are measured, partially covered, or white space | [`docs/BENCHMARK_COVERAGE_ATLAS.md`](docs/BENCHMARK_COVERAGE_ATLAS.md) |
| Bring a memory system or a benchmark into the laboratory | [`docs/CONTRIBUTOR_ARCHITECTURE.md`](docs/CONTRIBUTOR_ARCHITECTURE.md), then [`docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) |
| Read how benchmark findings become bounded remediation and frozen replays | [`docs/56-benchmark-gauntlet-remediation-evidence.md`](docs/56-benchmark-gauntlet-remediation-evidence.md), [`docs/72-benchmark-neutral-remediation-loop.md`](docs/72-benchmark-neutral-remediation-loop.md) |
| Follow the per-metric leaderboard and evidence-freshness work | issues [#779](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/779), [#789](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/789), [#795](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/795) |

```text
benchmark score != truth
benchmark score != authority
retrieval quality != production readiness
blocked / not_run / evidence_gap != 0
```

## Runtime

From a checkout:

```bash
python -m pip install .
```

Then:

```python
from agentmem_ref import AgentMemory

with AgentMemory.open("./agent-memory-state", tenant="tenant:local") as memory:
    memory.remember("memory:preferred-editor", "Preferred editor is VS Code")

    recalled = memory.recall(
        "preferred editor",
        logical_memory_refs=("memory:preferred-editor",),
    )

    history = memory.history("memory:preferred-editor")
    posture = memory.posture()
```

The facade is a convenience layer over the versioned public contract ([`docs/44-public-api-contract.md`](docs/44-public-api-contract.md)). Convenience does not create authority: corrections, permanent deletion, and other consequential operations remain subject to governance. Read [`docs/47-developer-facade-and-local-open-path.md`](docs/47-developer-facade-and-local-open-path.md) for defaults, recovery posture, and the threading contract, and [`docs/45-agent-memory-rc1-implementation-profile.md`](docs/45-agent-memory-rc1-implementation-profile.md) for the bounded RC profile.

### Substrates and maturity

"No single shape of memory is best for everything" is the design direction. It is not yet a qualified claim across storage technologies. The authoritative inventory is [`docs/43-substrate-inventory-and-maturity.md`](docs/43-substrate-inventory-and-maturity.md); the summary is:

| Substrate / topology | Status |
|---|---|
| `SQLiteTemporalGraph` (`sqlite_single_host_v1`) | **RC-qualified** single-host canonical substrate; the only production-credible profile |
| `InMemoryTemporalGraph` | **Reference** implementation; restart/checkpoint correctness proven; not a production persistence recommendation |
| `GraphitiSubstrate` | **Experimental** adapter; probe path uses a deprecated upstream driver; not qualified |
| Rust kernel | **Shadow only**; deterministic-primitive parity evidence under [#602](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/602); Python remains the qualified runtime |
| Postgres, graph databases, Markdown/files, object stores | **Not implemented as substrates**; storage technologies until an Agent Memory profile earns qualification |
| Distributed / multi-host persistence | **Not established**; see the proposed [distributed-runtime roadmap](docs/future/distributed-runtime-roadmap.md) |

### Where the runtime stands

Current state has source-backed owners, in this order: the code-declared versions above; [`docs/43-substrate-inventory-and-maturity.md`](docs/43-substrate-inventory-and-maturity.md) for what is qualified; `reports/runtime/baseline-register.json` for the current Runtime Baseline; [`docs/BACKLOG.md`](docs/BACKLOG.md) for the work queue and owner rulings; [`docs/SYSTEM_STATE.md`](docs/SYSTEM_STATE.md) for the revision-bound projection; and issues [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410), [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668), and [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) for live execution state. [`docs/64`](docs/64-current-governance-and-benchmark-dashboard.md) and [`docs/66`](docs/66-pre-1.0-maturity-and-runtime-qualification.md) are reconciliations at the #594 and #600-#602 boundaries respectively; they keep their original claims and are not refreshed. Two boundaries hold regardless of the evidence inside them:

- the qualified persistence claim is bounded single-host SQLite;
- production 1.0 is not claimed. RC1 is an explicit governed declaration decision.

## Repository structure

```text
reference/agentmem_ref/
├── core/        PAMA, receipts, evidence, verification, contextual recall
├── state/       canonical substrates, graph/state drivers, projections
├── contracts/   capability declarations, qualification, substitution
├── runtime/     governed adapter, restart, transactions, composition, CLI
├── memory/      governed memory kinds: epistemic, procedural, predictive, ...
├── api/         versioned public contract surfaces
├── crg/         Code Reality Graph / code-domain integration
├── harness/     characterization harnesses, depth probes, comparators
└── evaluation/  benchmark-neutral validation, Gauntlet, scorecard machinery

reference/       runners, benchmark adapters, tests (`reference/tests/`)
schemas/         machine-readable contracts
fixtures/        conformance and adversarial fixtures
docs/            doctrine, ADRs, product profiles, evaluation guidance, plans
reports/         frozen and normalized benchmark evidence, runtime baselines
sources/         source/provenance/right-to-reuse records
```

The layered package topology is enforced by `reference/tests/test_package_layout.py` from the table in `scripts/restructure_package.py`. The runtime never imports the evaluation package.

## Evidence and maturity discipline

A repository claim should state whether it is doctrine, product contract, implementation, conformance evidence, benchmark evidence, field evidence, research/ancestry, or hypothesis. Those categories are not interchangeable, and promotion between them is deliberate. Agent Memory is the canonical owner of the generic memory machinery implemented here; EvolveAI, CodeGenome, COREFORGE, UOR-derived mechanisms, and other systems supply ancestry, evidence, or comparison surfaces, not permanent runtime ownership.

See [`GOVERNANCE.md`](GOVERNANCE.md), [`docs/policies/EVIDENCE_PROMOTION.md`](docs/policies/EVIDENCE_PROMOTION.md), and [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md).

## Contributing

1. [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md)
2. [`CONTRIBUTING.md`](CONTRIBUTING.md)
3. [`GOVERNANCE.md`](GOVERNANCE.md)
4. [`docs/README.md`](docs/README.md)
5. [`docs/CONTRIBUTOR_ARCHITECTURE.md`](docs/CONTRIBUTOR_ARCHITECTURE.md) for systems and benchmarks

Material changes should identify whether they affect runtime behavior, doctrine, evaluation/evidence, contracts/schemas, documentation, or security/governance.

## License

Agent Memory is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Third-party sources, datasets, benchmark corpora, and referenced implementations retain their own licenses and attribution requirements. See [`docs/SOURCE_RIGHTS_POLICY.md`](docs/SOURCE_RIGHTS_POLICY.md) and the source registry.
