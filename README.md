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

## Start here

Agent Memory serves three audiences through three entry points. Pick the one that matches what you came to do.

| Entry point | For | What it is | Current maturity | Start | Then |
|---|---|---|---|---|---|
| **[Theory](#theory)** | Researchers studying memory architecture and governance | Doctrine, invariants, lifecycle/currentness semantics, PAMA mutation authority, Architecture Decision Records | Canonical and actively falsified: ADR-001 through ADR-043, each carrying its own `Accepted` / `Proposed` status; ADR-039 (query-conditioned applicability) remains Proposed | [`docs/01-layer-model.md`](docs/01-layer-model.md) | [ADR index](docs/adr/README.md), [PAMA](docs/pama/README.md), [governed uncertainty](docs/24-determinism-probability-and-governed-uncertainty.md) |
| **[Benchmarks](#benchmarks)** | Evaluators running controlled comparisons, inspecting evidence, or bringing a system or a benchmark | Benchmark-neutral evaluation machinery, the Agent Memory Gauntlet, frozen revision-bound evidence, the Coverage Atlas, the current dashboard | Accepted external and same-harness evidence exists; leaderboard and freshness projections are in progress; there is deliberately no universal score | [`BENCHMARKS.md`](BENCHMARKS.md) | [Current dashboard](reports/benchmarks/dashboard/current.md), [Coverage Atlas](docs/BENCHMARK_COVERAGE_ATLAS.md), [bring a system or a benchmark](docs/CONTRIBUTOR_ARCHITECTURE.md) |
| **[Runtime](#runtime)** | Builders integrating governed memory into an agent | The installable `agent-memory-reference` package: `AgentMemory` facade, governed lifecycle, restart-safe persistence, multi-route recall | Usable reference/conformance runtime; one RC-qualified substrate (`sqlite_single_host_v1`); public contract 1.6.0; not production 1.0; not distributed | [Install and open](#runtime) | [`docs/47-developer-facade-and-local-open-path.md`](docs/47-developer-facade-and-local-open-path.md), [substrate maturity](docs/43-substrate-inventory-and-maturity.md), [distributed-runtime roadmap](docs/future/distributed-runtime-roadmap.md) |

The three reinforce one another: benchmarks keep the theory honest, the runtime keeps the benchmarks relevant, and the theory gives the runtime its boundaries. None of them inherits authority from another.

### Three roles, five layers

Those three entry points correspond to the repository's three **operational roles** (product/runtime, architecture/governance laboratory, evaluation/benchmark laboratory) defined in [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md). The broader project is additionally partitioned into a **five-layer project model** (architecture/doctrine/research commons, Memory Evaluation, the Agent Memory Gauntlet, the reference/conformance implementation, and a future distinct production runtime) in [`docs/AGENT_MEMORY_PROJECT_MODEL.md`](docs/AGENT_MEMORY_PROJECT_MODEL.md).

The two are not competing descriptions. Per the ruling in issue [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565): the three roles describe what the repository *does* operationally today; the five layers describe how the project is *partitioned* for community, evaluation, qualification, reference implementation, and future product/licensing boundaries. The five-layer model refines the product/runtime role into "reference/conformance implementation" plus "future distinct production runtime" ([#556](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/556)), and refines the evaluation role into lower-level Memory Evaluation plus the public Gauntlet.

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

The complete current invariant list, the write/read architecture, and the active policy boundary are maintained in one place: [`docs/64-current-governance-and-benchmark-dashboard.md`](docs/64-current-governance-and-benchmark-dashboard.md). Doctrine itself lives in the numbered architecture corpus (`docs/00` through `docs/42`), [PAMA](docs/pama/README.md), [`docs/04-governance-and-pama.md`](docs/04-governance-and-pama.md), and the [ADR index](docs/adr/README.md), which is the canonical doctrine-status ledger. Implementation or benchmark evidence never silently promotes, supersedes, or rejects an ADR.

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

Current RC dependency order, follow-on issues, and known limitations are maintained in [`docs/64-current-governance-and-benchmark-dashboard.md`](docs/64-current-governance-and-benchmark-dashboard.md), [`docs/66-pre-1.0-maturity-and-runtime-qualification.md`](docs/66-pre-1.0-maturity-and-runtime-qualification.md), [`docs/BACKLOG.md`](docs/BACKLOG.md), and issue [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410). Two boundaries hold regardless of the evidence inside them:

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
