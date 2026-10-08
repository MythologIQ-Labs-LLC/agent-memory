# Benchmark-neutral evidence-to-remediation loop

**Status:** Initial read-only audit implementation for [#722](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/722), 2026-10-08. The full reconciliation policy and any automated decisions remain subject to #719 / ADR-043 acceptance. This document is an implementation guide, not independent authority to mutate the runtime or deficit ledger.

## Why

A score diagnoses memory behavior under a particular protocol. It is not an architecture specification. Benchmark-specific vocabulary, cue lists, example memorization, evaluator shortcuts, reranking to satisfy particular gold IDs, or reading benchmark answers into production behavior are forbidden forms of remediation.

**Control loop:**

~~~text
observed failure in one frozen benchmark
  -> reproduce and verify evaluator/protocol/source evidence
  -> classify the failing MEMORY CAPABILITY and stage
  -> identify what the engine SHOULD do on unseen inputs
  -> propose a generally applicable mechanism and pre-register invariants
  -> adversarial challenge, independent domain sampling, metamorphic controls
  -> implement mechanism in native runtime behind governed version boundary
  -> unit/property/negative tests
  -> frozen original benchmark replay (regression and efficacy)
  -> independent held-out benchmark/family replay (generalization)
  -> cross-benchmark negative-controls, durability, authority and latency
  -> accept/reject with evidence, reclassify deficit and repeat
~~~

Architecture and product capability are the design target. The benchmark only shows whether one observable boundary is better or worse. A perfect benchmark score may coexist with a severe generalization deficit.

## Phase 0: read-only ledger accountability audit

Run:

~~~sh
python3 -m unittest discover -s tests -p 'test_deficit_evidence_audit.py' -v
python3 scripts/audit_benchmark_deficit_ledger.py --output /tmp/agent-memory-deficit-audit.json
~~~

The script parses the current accepted deficit ledger `reports/benchmarks/deficits/current.json` and returns a deterministic, **non-mutating** JSON report:

- unique deficit IDs and recognized ledger schema;
- evidence refs, benchmark profile, metric and owning issue presence;
- closed/frontier states supported by closure evidence;
- unresolved deficits with unknown stage kept `unclassified`, not guessed;
- missing adversarial negative controls surfaced for review;
- blocked, deferred and not-measured values **never** replaced with zero;
- published research numbers **never** promoted to same-harness frontiers;
- no metric weighting, threshold selection, model inference or remediation decision.

The audit has two results: `STRUCTURAL_FAILURE` for invalid records, or `READ_ONLY_REVIEW` for mechanically well-formed inputs, even when they contain outstanding deficits. `review_candidates` are suggestions, **not** governance violations or automatic GitHub issues. The canonical doctrine CI audit step blocks only structural invalidity, not missing optional negative controls, scientific judgments or the score itself. It never alters current.json or source benchmark artifacts.

This phase intentionally does **not** implement #722's comparator arithmetic, automatic reopen/close transitions, issue creation, architecture proposals or frontier escalation. Those features require accepted identity/metric comparability policy and regression floors; without them an automatic engine would fabricate decision authority.

## Mandatory generalization design controls for any runtime remediation

Before implementation, require a human-reviewed capability hypothesis answering:

1. **What is the memory defect?** Identify the real-world operation (write interpretation, identity resolution, typed temporal applicability, retrieval routing, candidate generation, admission, ranking, consolidation, correction, forgetting, etc.). Separate evaluator or adapter defect from actual runtime behavior.
2. **What invariant generalizes?** State conditions independent of proper nouns, benchmarks, word lists and test labels. For currentness: source, actor, scope, assertion posture, proposition identity, cardinality and change applicability should be typed/versioned.
3. **What is unknown?** Leave attribution `unclassified` if evidence is insufficient. Never treat confidence, freshness, repetition or a model's suggestion as permission.
4. **How could we disprove the solution?** Construct independently authored examples in domains/expressions absent from the motivating benchmark, including both positive and negative controls and metamorphic transformations. Freeze at least one unseen family until after the implementation.
5. **What policies must never move?** Tenant isolation, memory admission, correction vs supersession, PAMA mutation authority, no silently moved provenance, blocked != zero, and no benchmark-only runtime branches.
6. **What evidence releases the change?** Versioned runtime baseline successor, targeted tests, frozen external replay, independently developed holdout, existing guard regressions, cost/latency and durability, approval receipts. Metrics without denominator/protocol identity cannot prove effectiveness.

A benchmark score improvement alone **cannot** ratify a runtime mechanism. If the original benchmark improves but the independently frozen holdout fails, retain the deficit and investigate architecture. Do not patch cases to chase a score.

## Current live example: general currentness failure (#732)

Formal MESA v2 M4 achieved 250/250 attributed currentness wins, while the separate #732 generalization suite measured **0/212 legitimate-change engagement**, with negative controls intact. This is strong evidence of **a language-generalization capability gap**, not permission to keep expanding the closed-class G12 word grammar. The intended remediation is typed, versioned write-time semantic evidence followed by guarded read-time applicability. Its active R6 provider/holdout work must not be duplicated by this tooling lane.

The current ledger already records the failed generalization family and its owning issue. A read-only audit can ensure the deficit does not silently lose source evidence or owner, but cannot select/approve an extractor, judge, benchmark-specific phrase rule, or risk trade-off.

## How this advances Agent Memory

This is infrastructure serving the **memory** project, not P.A.I., a new agent runtime, or a universal benchmark score. It ensures every future accepted deficit and purported closure has inspectable accountability, while the actual resolution remains a general memory mechanism with independent scientific evidence.

## Explicit next gate

After #719's policy acceptance, expand #722 with snapshot identity, comparable metric schemas, prior and successor runtime baselines, regressions, blocked-state propagation and **proposed** ledger diffs. Keep any automated issue/comments and state changes behind review. Do not turn the read-only audit into runtime tuning.

For benchmarks that require local caches, judge inference, provider credentials, multi-system comparators, or large data and cannot run in this ChatGPT session, use a separate reproducible local evaluation operator and return the exact frozen raw evidence before implementing further runtime changes.
