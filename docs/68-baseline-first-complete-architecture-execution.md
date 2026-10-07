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

## Closed-loop strengthening model

The North Star program is not a one-way sequence from architecture to implementation to evaluation.

It is a deliberately **self-correcting engineering loop**:

```text
        accepted architecture
          /           \
         v             v
runtime implementation -> benchmark pressure
         ^                  |
         |                  v
         +---- remediation / deficit analysis
                    |
                    v
          stronger runtime evidence
             /             \
            v               v
  architecture refinement   benchmark refinement
```

A second way to read the same loop is:

```text
architecture
  -> defines intended capability and invariants
  -> runtime makes that architecture executable
  -> benchmarks attempt to falsify the runtime
  -> deficits become explicit engineering obligations
  -> remediation strengthens the runtime
  -> new evidence may expose missing architecture
  -> new architecture may require new benchmark pressure
  -> repeat
```

No edge is one-directional in practice.

### Architecture strengthens evaluation

Architecture tells the evidence program what meaningful capabilities, invariants and failure modes must be tested even when external benchmarks do not yet cover them.

Accepted architecture without benchmark coverage remains implementation work.

Where no adequate external benchmark exists, the Coverage Atlas may justify a neutral Gauntlet-native gap suite under its existing anti-marketing rules.

### Evaluation strengthens architecture

A trustworthy benchmark may falsify an architectural assumption.

If a result shows that the existing architecture cannot plausibly reach the required capability frontier without violating invariants, the correct outcome is a new or revised architecture tranche.

The benchmark does not dictate the design.

It is allowed to prove that the current design is incomplete.

### Remediation strengthens both

The deficit-remediation loop is the bridge between evidence and architecture.

A material deficit must become:

- an owned runtime/architecture hypothesis;
- a bounded implementation tranche;
- a frozen replay obligation;
- a regression obligation once fixed.

If remediation reveals that the original failure attribution was wrong, the deficit returns to analysis rather than being forced closed.

### Failure must be loud and useful

The desired system behavior is not "never fail."

The desired engineering behavior is:

```text
fail visibly
  -> preserve enough evidence to explain the failure
  -> classify what is known and unknown
  -> make the deficit durable and owned
  -> remediate the general mechanism
  -> prove the improvement
  -> retain the proof as a future regression floor
```

Silent degradation is therefore worse than an explicit unsupported, blocked, evidence-gap or failed state.

The repository SHOULD prefer a loud, typed failure over a plausible-looking fabricated success.

### This is not yet autonomous runtime self-healing

The runtime itself is not granted open-ended authority to rewrite its own implementation or policy when a benchmark fails.

"Self-correcting" here describes the repository's governed engineering loop.

Runtime self-adaptation remains separately constrained by PAMA, lifecycle authority, versioned policy and accepted architecture such as ADR-042.

This distinction prevents an evaluation result from becoming mutation authority.

### Each pass should leave the system stronger

A successful cycle should produce at least one durable improvement:

- new runtime capability;
- stronger correctness or governance invariant;
- better competitive/adequacy metric;
- sharper failure taxonomy;
- better evidence coverage;
- a new regression floor;
- corrected dependency/architecture assumptions;
- an explicit product boundary.

If a full cycle produces none of these, it was activity rather than progress.

### Convergence target

The long-run target is not a repository with no open deficits.

New benchmarks, harder workloads and broader capabilities should continue finding weaknesses.

The target is a system where:

- important failures become visible quickly;
- root cause becomes increasingly localizable;
- remediation is increasingly bounded;
- accepted wins do not regress casually;
- architecture and evidence stay synchronized;
- the number of unexplained or ownerless failures trends toward zero;
- the runtime occupies an increasingly broad best-in-class capability frontier.

This loop is a core mechanism for making Agent Memory more defensible with every evidence/remediation pass.

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
