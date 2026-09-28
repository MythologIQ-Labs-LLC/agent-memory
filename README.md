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

**[Documentation](docs/README.md)** · **[Repository operating model](docs/REPOSITORY_OPERATING_MODEL.md)** · **[Benchmarks](BENCHMARKS.md)** · **[Current dashboard](reports/benchmarks/dashboard/current.md)** · **[RC1 tracker](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410)** · **[PAMA](docs/pama/README.md)** · **[Governance](GOVERNANCE.md)**

</div>

---

> [!IMPORTANT]
> **Current status: executable governed runtime plus active RC evidence program.**
>
> Agent Memory is no longer only a reference architecture. The repository contains a developer-facing `AgentMemory` facade, governed lifecycle operations, restart-safe local persistence, a bounded qualified SQLite substrate, multi-route recall, native semantic/vector and typed temporal/entity/causal machinery, native cognitive metabolism, correction/deletion/history paths, and revision-bound benchmark evidence.
>
> It is **not** a production 1.0 claim. The current qualified posture is deliberately bounded, especially to the single-host SQLite profile. RC composition remains governed by issue #410. The canonical current benchmark/evidence view is `reports/benchmarks/dashboard/current.md`.

## What Agent Memory owns

Agent Memory is the canonical owner of generic memory machinery implemented here. EvolveAI, CodeGenome, COREFORGE, UOR-derived mechanisms, Jev/Jev-Mem, research papers, and other systems may supply implementation ancestry, evidence, mechanisms, comparison surfaces, or downstream integration. They do not remain permanent runtime owners merely because useful ideas were harvested from them.

Agent Memory serves three connected roles:

| Role | What lives here | What it does not mean |
|---|---|---|
| **Product / runtime** | Governed memory lifecycle, qualified SQLite path, recall, correction, forgetting, history, posture | Production 1.0 or distributed readiness |
| **Architecture / governance lab** | ADRs, PAMA, lifecycle/currentness doctrine, memory metabolism, identity/provenance/authority boundaries | Doctrine is immune from falsification |
| **Evaluation / benchmark lab** | LongMemEval, AgentMemBench/MemDialogue, evaluator-integrity probes, frozen reports, accepted semantic gold, current dashboard | Benchmark score becomes truth or authority |

The development loop is:

```text
architecture
    -> implementation
    -> internal conformance
    -> external benchmark pressure
    -> product / architecture gap discovery
    -> bounded remediation
    -> same frozen benchmark replay
```

The goal is not to make every benchmark green. The goal is to make the architecture survive independent workloads without silently weakening governance to chase a number.

## Governing doctrine

**Probabilistic epistemics. Governed consequences.**

**Uncertainty may propose. Authority constrains.**

Current load-bearing invariants include:

```text
candidate retrieval != governed recall admission
ranking != recall admission
ranking != truth
relevance != currentness
classifier output != truth
classifier confidence != permission
interpretation != authority
semantic interpretation != retention/lifecycle policy
conflict detection != mutation
proposal != application
newer != superseding
staleness != irrelevance
age != staleness
recency != authority
metabolic stability != temporal validity
reinforcement != currentness
recommendation != mutation authority
external verification != Agent Memory authority
benchmark score != memory authority
```

A model, retriever, classifier, temporal signal, decay score, benchmark result, or external verifier may contribute evidence. None creates its own permission to mutate canonical memory or influence active cognition outside the governed path.

See **[PAMA](docs/pama/README.md)**, **[Governance and PAMA](docs/04-governance-and-pama.md)**, and **[ADR-035](docs/adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md)**.

## Current architecture

```text
WRITE
memory text + explicit metadata
  -> deterministic/versioned write-time interpretation
       proposition identity candidate
       cardinality evidence
       temporal aspect
       bounded self-validity
       change/coexistence/hedging/self-claim markers
  -> typed evidence / governed proposal
  -> existing lifecycle
  -> persisted memory

READ
query
  -> temporal intent
  -> candidate generation
  -> governed canonical admission
  -> contextual purpose admission
  -> temporal applicability
       caller-declared validity
       > interpreted self-validity as LIMIT ONLY
       > unknown
  -> relevance/routing evidence
  -> deterministic ordering
  -> recall
```

Policy is **3.1.0**. Interpreted self-validity may limit a memory's own applicability when caller-declared validity is absent. It may never affirm its own currentness.

ADR-039 remains **Proposed**.

PR #587 / issue #583 remains intentionally **DRAFT / HOLD**. The old lexical-cue-removal candidate must not be revived. Query-side temporal intent (#585) and memory-side aspect evidence (#598) are separate typed contracts that must be calibrated before a redesigned #583.

## Use the runtime

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

The facade is a convenience layer over the governed public contract. Convenience does not create authority. Corrections, permanent deletion, and other consequential operations remain subject to governance.

See **[Developer Facade and Local Open Path](docs/47-developer-facade-and-local-open-path.md)**.

## Implemented product surface

| Surface | Current posture |
|---|---|
| Developer `AgentMemory.open()/remember()/recall()/correct()/forget()/history()/posture()` facade | Implemented |
| Canonical semantic memory | Executable governed runtime |
| Epistemic belief memory | Executable with confidence, evidence, dispute and retraction lineage |
| Procedural / skill memory | Executable with action-authority separation |
| Predictive / counterfactual memory | Executable governed surface |
| Governed recall admission | Executable scope/tenant/project/currentness boundary |
| Historical-evidence admission | Executable under explicit historical/as-of intent |
| Multi-route retrieval | Executable with route provenance |
| Native semantic/vector retrieval | Implemented |
| Typed temporal/entity/causal traversal | Implemented |
| Native cognitive metabolism | Implemented deterministic evidence/proposal surface |
| Write-time proposition/cardinality/aspect/self-validity carrier | Implemented; naturally qualified by #594 |
| Correction / supersession | Executable and restart-safe in declared reference profile |
| Forgetting / tombstones | Executable, evidence-bearing and restart-safe |
| SQLite canonical substrate | Qualified for bounded single-host RC use |
| Distributed/multi-host persistence | Not established |
| Production 1.0 readiness | Not claimed |

## Current benchmark dashboard

The canonical dashboard is **[`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md)** with machine-readable form at `current.json`. It deliberately distinguishes current accepted evidence, previous accepted evidence and deltas, evidence classes, and non-numeric states such as `not_run`, `blocked`, and `evidence_gap`.

Headline accepted evidence:

| Track | Current evidence |
|---|---|
| AgentMemBench exact-source recall@5 | **0.899** |
| LongMemEval_S session recall_all@5 | **0.823389** |
| LongMemEval_S turn recall_all@10 | **0.723** |
| LongMemEval_M recall_all@5 | session **0.708831**, turn **0.532220** |
| AgentMemBench currentness | new-fact 0.20, staleness 0.80 |
| LongMemEval_S latest-gold-first | session 0.457, turn 0.557 |
| #591 search performance | p50 7.7 ms, p95 11.9 ms, wall 38.6 s |
| #594 Part R proposition status | known precision **0.800**, known recall **0.148**, unknown precision **1.000**, unknown recall **0.848** |
| #594 source-anchored self-validity demotion | **EVIDENCE GAP**, 0 metric-visible changed rows |

There is no universal aggregate score.

## #594 natural semantic qualification

#594 is **QUALIFIED**.

Phase A mapped defensible LongMemEval_S session dates to `observed_at` and separately tested a host-declared question-date reference time. C, P1, and P2 remained rank-identical. The corpus therefore supplies no metric-visible efficacy case for interpreted self-validity demotion; this is an explicit external evidence gap, not a runtime failure.

Phase B froze 268 natural turns, iterated five versioned annotation drafts without consulting interpreter predictions, accepted v5 through a maintainer gold-freeze review, and only then ran the interpreter.

On the unbiased Part R sample, the dominant failure is **over-ambiguity / under-recognition**: 46 of 54 gold-known turns become `ambiguous`. Known precision remains 0.80 and unknown precision is 1.0. The result is materially weak efficacy but predominantly conservative rather than authority-expanding.

Follow-ons:

- **#596** proposition recognition / over-ambiguity;
- **#597** canonical property/value boundaries and pre-score normalization;
- **#598** write-time temporal-aspect calibration.

#598 is on the temporal RC dependency path before redesigned #583. #596/#597 are high-priority interpreter-quality limitations and are not automatic RC blockers while their dominant behavior remains fail-safe ambiguity/abstention.

See **[`reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md`](reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md)**.

## Current known limitations

- **Implicit supersession is not inferred.** A newer independently written contradiction does not automatically make the older memory false or non-current (#531 class B). Governed correction/declared temporal evidence remains the authority-bearing path.
- **Natural proposition recognition is sparse.** #594 Part R known recall is 0.148 at 0.80 precision; remediation is #596.
- **Property/value extraction needs a canonicalization contract.** The first #594 score froze an empty alias table before scoring; exact-label slot failures include both benign synonym variation and genuine malformed extraction. #597 owns a pre-score, independently defensible contract.
- **Write-time temporal aspect needs calibration.** #594 exposed aspect mismatches and over-classification. #598 is separate from query-side #585.
- **Interpreted self-validity external efficacy remains an evidence gap.** Source-anchored LongMemEval_S produces no metric-visible demotion case.
- **ADR-039 remains Proposed.** No benchmark result promotes it automatically.
- **Distributed/multi-host persistence is not established.** The qualified persistence claim is bounded single-host SQLite.
- **Production 1.0 is not claimed.** RC1 is still an explicit governed declaration decision.

## Active RC sequence

```text
#591 COMPLETE
  -> #594 QUALIFIED
  -> canonical current dashboard COMPLETE
  -> #585 query-intent span calibration
  -> #598 write-time temporal-aspect calibration
  -> redesigned #583
  -> final #580 replay
  -> #584 policy ruling
  -> RC1 declaration decision
```

#586 exception/override precedence remains post-RC unless evidence pulls it forward.

#596/#597 may be remediated in parallel or promoted onto the critical path if final RC evidence shows the declared product contract cannot tolerate their limitations.

See **[Current governance and benchmark state](docs/64-current-governance-and-benchmark-dashboard.md)** and issue **#410**.

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

## Evidence and maturity discipline

A repository claim should state whether it is doctrine, product contract, implementation, conformance evidence, benchmark evidence, field evidence, research/ancestry, or hypothesis. Those categories are not interchangeable.

The repository's evidence policy is source-neutral: native ideas do not become correct because they originated here, and external ideas do not become correct because they are published or popular. Evidence may support, challenge, narrow, or supersede doctrine through the governed decision process.

See **[GOVERNANCE.md](GOVERNANCE.md)** and **[Evidence Promotion Policy](docs/policies/EVIDENCE_PROMOTION.md)**.

## Contributing

Start with:

1. **[Repository Operating Model](docs/REPOSITORY_OPERATING_MODEL.md)**
2. **[Contributing](CONTRIBUTING.md)**
3. **[Governance](GOVERNANCE.md)**
4. **[Documentation index](docs/README.md)**
5. **[Architecture decisions](docs/adr/README.md)**
6. **[Benchmarks](BENCHMARKS.md)**

Material changes should identify whether they affect runtime behavior, doctrine, evaluation/evidence, contracts/schemas, documentation, or security/governance.

## License

Agent Memory is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Third-party sources, datasets, benchmark corpora, and referenced implementations retain their own licenses and attribution requirements. See **[SOURCE_RIGHTS_POLICY.md](docs/SOURCE_RIGHTS_POLICY.md)** and the source registry.
