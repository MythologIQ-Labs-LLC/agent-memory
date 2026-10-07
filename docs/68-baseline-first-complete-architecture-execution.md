# Baseline-first, complete-architecture execution posture

Status: repository-owner direction, 2026-10-07.

Related: #668, #600, #601, #574, #694.

## Decision

Agent Memory will establish a protocol-faithful external baseline before benchmark-driven remediation, beginning with formal AgentMemBench/MESA (#694).

That sequencing does **not** reduce the product roadmap to measured deficits.

The controlling model is:

```text
measure current system honestly
  -> freeze external baseline
  -> classify strengths, deficits, and evidence gaps
  -> implement the complete accepted Agent Memory architecture
  -> use evidence to prioritize and gate tranches
  -> replay frozen benchmarks after material milestones
  -> compare against external systems
  -> iterate toward evidence-backed best-in-class status
```

Benchmark evidence guides implementation priority and validates outcomes. It does not define product completeness.

## Formal MESA baseline

The primary MESA run must use the upstream protocol without Agent-Memory-only temporal enrichment or benchmark-specific adaptation.

Required surfaces are M1-M6:

- write efficiency;
- retrieval quality;
- scalability;
- temporal consistency/currentness;
- isolation/privacy and deletion;
- LLM portability.

The existing adapted new-fact-first 0.20 / staleness 0.80 signal is a risk indicator to verify, not yet the formal MESA result.

Per-case failures should be preserved so they can be attributed, where possible, to:

1. write interpretation / proposition extraction;
2. identity or slot resolution;
3. candidate generation;
4. admission;
5. temporal applicability/currentness;
6. ranking/fusion;
7. evaluator/answer layer;
8. unsupported product semantics.

A later date-informed diagnostic lane may be useful, but it must be separately frozen and labeled adapted/diagnostic.

## Complete runtime architecture remains required

After the external baseline is frozen, substantial implementation capacity returns to the runtime.

The accepted architecture program includes, but is not limited to:

- #669 semantic/vector retrieval reachable from the supported facade;
- #644 controlled recall mechanisms, budgets, stop reasons, sufficiency, allocation, and telemetry;
- #688 typed entity/causal relation vocabulary and bounded traversal judgments;
- #673 route fusion and later separately versioned reranking;
- #671 temporal/currentness capability work;
- #596 proposition recognition;
- #597 canonical proposition slot/value boundaries;
- #689 runtime metabolism/consolidation maintenance;
- #690 governed failure memory;
- #691 consumer-aware memory packaging beyond a simple ranked prefix;
- #636 heterogeneous memory composition;
- correction, supersession, forgetting/tombstones, history, provenance, authority and restart safety;
- #602 implementation-profile qualification where Rust demonstrates real semantic, assurance or performance value.

A benchmark may reveal additional remediation work or reorder these tranches. It may not erase accepted architecture merely because that capability is not scored.

## Owner rulings for the next cycle

1. **Capacity:** evaluation-first only long enough to freeze and execute the formal baseline; then shift substantial capacity back to complete runtime implementation.
2. **Temporal comparability:** primary competitive lanes receive no Agent-Memory-only temporal enrichment; temporal diagnostics are separate.
3. **Embedding dependency:** prefer a pinned local representation provider behind the existing abstraction as an optional extra instead of forcing a heavy model stack into the base package.
4. **Hindsight:** freeze one benchmark-agnostic, production-like provider configuration across applicable lanes.
5. **LLM-judged evaluation:** use one explicitly authorized, version-pinned reader/judge configuration as evidence infrastructure.

The canonical roadmap/decision mechanism should record these rulings; this document states the execution posture they govern.

## Evidence discipline for runtime tranches

Material runtime tranches should close with evidence for:

- the behavior actually reachable through the supported public path;
- architecture and governance invariants preserved;
- before/after frozen benchmark evidence where applicable;
- comparator posture changed or evidence gap reduced;
- latency/resource impact;
- known unsupported or unresolved surfaces;
- Runtime Baseline successor identity for behavior changes;
- regression status for previously accepted lanes.

Passing tests alone does not establish the intended runtime outcome.

## Competitive North Star

Best-in-class is not a single benchmark score.

The evidence program should eventually cover at least:

- formal AgentMemBench/MESA;
- LongMemEval retrieval and separately pinned end-to-end QA;
- BEAM scale tiers;
- SWE-ContextBench Lite for coding-agent experience reuse;
- an action-level memory benchmark such as DolphinBench;
- PersonaMem;
- LoCoMo for ecosystem comparability;
- longitudinal and field evidence for long-lived software and organizational memory.

The target is a complete runtime architecture with defensible cross-system evidence, not a benchmark-specialized implementation.
