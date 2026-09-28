# Current governance and benchmark state after #594

Status: canonical current-state reconciliation for the RC program after #591 and #594. Historical evidence documents keep their original claims and provenance; where an older status line says #550/#594 is draft or unscored, this document and the #594 `CLOSEOUT.md` are the current disposition.

## Current boundary

The #594 evaluation branch is based on main `691251ca27f5e8e87a7c259c1a47a7050f32291b`. Accepted/scored evidence is at `73216bebc596de4876692a8f00d1e3fabaa899f1` before PR #595 merge.

Completed since the previous #410 reconciliation:

- #591 / PR #593: identity-first candidate materialization, complete; semantic retrieval order unchanged and search performance repaired.
- #594 Phase A: accepted adapted-external LongMemEval_S qualification, complete with an explicit self-validity-demotion efficacy **EVIDENCE GAP**.
- #594 Phase B: 268-turn natural corpus, five versioned pre-gold reviews, immutable accepted gold v1, deterministic first score, complete.
- canonical progressive benchmark dashboard regenerated at `reports/benchmarks/dashboard/current.{md,json}`.

#594 disposition is **QUALIFIED**, not PASS-without-limitations. The evidence is strong enough to characterize the implementation and exposes real follow-on defects.

## Architecture remains unchanged

#594 is evaluation only. It does not alter the runtime or promote doctrine.

```text
memory text + explicit metadata
  -> deterministic/versioned write-time interpretation
       proposition identity candidate
       cardinality evidence
       temporal aspect
       bounded self-validity
       change/coexistence/hedging/self-claim markers
  -> typed evidence / governed proposal
  -> existing lifecycle
```

The read path remains:

```text
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

Load-bearing governance:

```text
interpretation != authority
semantic interpretation != retention/lifecycle policy
proposal != application
conflict detection != mutation
newer != superseding
ranking != admission
ranking != truth
relevance != currentness
classifier output != truth
classifier confidence != permission
staleness != irrelevance
age != staleness
recency != authority
metabolic stability != temporal validity
reinforcement != currentness
benchmark score != memory authority
```

ADR-039 remains **Proposed**. Nothing in #594 is an ADR promotion event.

PR #587 / #583 remains **DRAFT / HOLD**. Do not revive the old 3.0.2 lexical-cue-removal implementation.

## What #594 established

### External/adapted temporal evidence

Source-anchored LongMemEval_S is defensible as adapted external evidence, but it does not exercise #550 self-validity demotion on a metric-visible row. C, P1, and P2 are rank-identical. This is an evidence gap for demotion efficacy, not a failure and not permission to broaden the mechanism.

### Natural proposition interpretation

The unbiased Part R sample gives the first accepted natural-data precision/recall baseline:

- known precision 0.800;
- known recall 0.148;
- ambiguous recall 1.000;
- unknown precision 1.000;
- unknown recall 0.848.

The implementation is therefore conservative but substantially under-capable relative to the reviewed semantic contract. Most gold-known misses become ambiguous rather than known-wrong. This matters for efficacy, while the authority boundary means it is not equivalent to unsafe mutation.

The frozen empty property-alias table also exposes a measurement seam: exact-label slot conformance is not semantic synonym conformance. #597 must define canonicalization independently before any normalized re-score.

## New bounded follow-ons

- #596: proposition recognition / over-ambiguity.
- #597: property/value boundary canonicalization and extraction quality.
- #598: write-time temporal-aspect calibration.

RC treatment:

- #598 is on the temporal critical path before redesigned #583.
- #596/#597 are high-priority limitations. They are not automatically RC1 blockers because the current dominant behavior is conservative evidence abstention, not a grant of authority. Reclassify them as blockers only if #580/#583/final RC evidence shows the declared product contract cannot tolerate them.

## Active RC sequence

```text
#591 complete
#594 qualified
canonical current dashboard complete
    |
    v
#585 query-intent span calibration
    |
    v
#598 memory-side temporal-aspect calibration
    |
    v
#583 redesign from typed query + memory evidence
    |
    v
final #580 replay
    |
    v
#584 policy ruling
    |
    v
RC1 declaration decision
```

#586 exception/override precedence remains post-RC unless evidence pulls it forward.

## Documentation authority

For current benchmark posture, use:

1. `reports/benchmarks/dashboard/current.md` / `.json`;
2. `reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md`;
3. `reference/fixtures/benchmarks/proposition-semantics/ACCEPTANCE.md`;
4. #410 for the RC checklist and dependency order.

Older scorecards and evidence READMEs remain historical, revision-bound evidence. They must not be read as a newer current-state claim merely because they still contain their original status language.
