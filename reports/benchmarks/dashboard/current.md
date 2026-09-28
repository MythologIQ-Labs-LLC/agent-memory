# Canonical Agent Memory benchmark dashboard

Status: **current accepted evidence through #594**. No universal aggregate score exists. `blocked`, `not_run`, and `evidence_gap` are states, never numeric zero.

Candidate evidence head: `73216bebc596de4876692a8f00d1e3fabaa899f1` (PR #595), based on main `691251ca27f5e8e87a7c259c1a47a7050f32291b` before merge.

## Executive view

| track | current accepted signal | previous accepted signal | delta / disposition | evidence class |
| --- | --- | --- | --- | --- |
| AgentMemBench retrieval | exact-source@5 **0.899** | 0.889 | +0.010 | external efficacy |
| LongMemEval_S session retrieval | recall_all@5 **0.823389** | 0.675 | +0.148389 | external efficacy |
| LongMemEval_S turn retrieval | recall_all@10 **0.723** | 0.525 | +0.198 | external efficacy |
| LongMemEval_M | session@5 **0.708831**, turn@5 **0.532220** | not available | accepted bounded run | external efficacy |
| AgentMemBench currentness | new-fact **0.20**, staleness **0.80** | 0.00 / 1.00 | +0.20 / -0.20 | external efficacy |
| LongMemEval_S latest-gold-first | session **0.457**, turn **0.557** | 0.343 / 0.486 | +0.114 / +0.071 | external efficacy |
| #580 self-description currentness | **0.273** | 0.091 | +0.182 | repository-owned conformance |
| #591 search performance | p50 **7.7 ms**, p95 **11.9 ms**, wall **38.6 s** | 17.9 / 31.4 / 54.6 | -10.2 / -19.5 / -16.0 | repository-owned performance |
| #594 adapted self-validity efficacy | **EVIDENCE GAP** | not run | C=P1=P2; 0 changed rows | adapted external evidence |
| #594 proposition known precision | **0.800** | not run | new baseline | repository-owned conformance |
| #594 proposition known recall | **0.148** | not run | new baseline; remediation #596 | repository-owned conformance |
| #594 unknown precision / recall | **1.000 / 0.848** | not run | new baseline | repository-owned conformance |
| #594 strict slot/value conformance | **0.000** | not run | exact-label diagnostic only; #597 | repository-owned conformance |

The strict slot/value number deliberately uses zero aliases frozen before scoring. It mixes true extraction failures with semantically close property labels and must not be sold as semantic synonym precision. That distinction is now governed by #597 rather than repaired after seeing the score.

## Architecture progression

| milestone | architectural move | evidence outcome |
| --- | --- | --- |
| frozen pre-remediation `f73b872` | baseline external retrieval/currentness | LME-S session recall@5 0.675; latest-first 0.343 / 0.486 |
| #538 ranking policy | explicit post-admission tie-break | currentness improved among ties; retrieval regression recorded |
| #538 admitted-set BM25 | relevance over admitted set only | LME-S session recall@5 0.823; turn recall@10 0.723; currentness trade-off exposed |
| #530 | runtime-owned handle serialization | concurrency failures -> operation/materialization success 1.0 |
| #522 / #548 | incremental attestation + identity/domain prefilter | removed major O(state) integrity/candidate costs without authority change |
| #576 | deterministic BM25 accumulation | score bits and order stable across hash seeds |
| #550 | typed proposition/cardinality/aspect/self-validity evidence | no external rank drift; four #580 target units honest_unknown -> pass; policy 3.1.0 |
| #591 | identity-first candidate materialization | p50 17.9 -> 7.7 ms; p95 31.4 -> 11.9 ms; semantic rankings identical |
| #594 Phase A | source-anchored natural external profile | no effect; demotion efficacy remains an explicit evidence gap |
| #594 Phase B | independently frozen 268-turn gold | interpreter is safe-leaning but severely under-recognizes valid propositions; defects split to #596-#598 |

## #594 Phase B, unbiased Part R

| gold status | predicted known | predicted ambiguous | predicted unknown |
| --- | ---: | ---: | ---: |
| known (54) | 8 | **46** | 0 |
| ambiguous (13) | 0 | 13 | 0 |
| unknown (33) | 2 | 3 | 28 |

The largest measured weakness is **over-ambiguity / under-recognition**. Known precision is 0.80, but known recall is only 0.148. Unknown precision is 1.0. This is materially weak efficacy, but its dominant failure mode is conservative and does not create authority.

Other Part R counters: wrong slot 8, unknown->known 2, aspect mismatch 4, aspect over-classification 1, over-eager single-valued 0.

## Governance / safety posture

Still true:

```text
interpretation != authority
semantic interpretation != retention/lifecycle policy
classifier output != truth
classifier confidence != permission
proposal != application
ranking != admission
ranking != truth
relevance != currentness
recency != authority
newer != superseding
benchmark score != memory authority
```

Active state:

- #591 complete.
- #594 **QUALIFIED**.
- ADR-039 remains **Proposed**.
- #583 / PR #587 remains **DRAFT / HOLD**; old lexical-cue-removal implementation must not be revived.
- #585 is the next query-side RC step.
- #598 is now a prerequisite before redesigned #583 because #594 exposed memory-side aspect calibration defects.
- #596 and #597 are high-priority interpreter-quality work, but are not automatic RC1 blockers while their dominant failure remains fail-safe ambiguity/abstention.
- #586 remains post-RC unless later evidence pulls it forward.

## Next RC path

```text
#591 COMPLETE
  -> #594 QUALIFIED
  -> canonical dashboard COMPLETE
  -> #585 query-intent span calibration
  -> #598 write-time aspect calibration
  -> redesigned #583
  -> final #580 replay
  -> #584 policy ruling
  -> RC1 declaration decision
```

#596/#597 may be remediated in parallel or before RC1 if later evidence shows their limitations undermine the declared RC contract. They do not grant mutation or ranking authority today.

Machine-readable form: `current.json`.
