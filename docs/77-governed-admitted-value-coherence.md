# #644 | Governed admitted-value coherence, observer 1.1.0

**State:** implemented on an unopened quiet branch; *not* merged, published, or claimed as Runtime Baseline v7. This is a protected runtime-bearing diagnostic, not a benchmark repair or release proof. Runtime Baseline v6 remains the active baseline.

## Problem and implementation

The previous post-admission sufficiency observer could correctly report that a requested typed slot had enough admitted supporting facts, but still produce a mechanical review-stop suggestion when two current facts asserted different values for that slot. Support **count** and support **coherence** are different. Likewise, a phrase asserting that a property *changed* is not evidence that a governed replacement was applied.

The runtime now traces this path:

```text
ControlledRecallResult admitted fact IDs (already retrieved)
    -> GovernedMemoryAdapter.current_governed_typed_claim(...)
         current tenant/scope/project/task/shared-membership/admission recheck
         excludes tombstones, disputed/expired/event-invalid facts
         only accepts persisted caller-declared, validated and eligible proposition
         returns {slot, value, cardinality, assertion} or no eligible claim
    -> ControlledRecallPlanner.observe_persisted_typed_coverage(...)
         constructs typed support and value-claim evidence itself
    -> evidence_sufficiency.assess_sufficiency(...)
         deterministic exact-value groups by admitted fact reference
         separate count/coverage/route-budget/value-coherence signals
         abstains from a review-stop recommendation on unresolved value states
    -> read-only SufficiencyReport, authority_effect = none
```

No LLM, controller, client-provided support label, benchmark answer, or lexical cue can create an authenticated value claim. The compatibility `current_governed_typed_slot()` delegates to the new adapter reader and preserves its original shape.

## Typed slot disposition policy

| Evidence state among current admitted eligible claims | Disposition | Permitted interpretation |
| --- | --- | --- |
| No eligible typed values | `no_eligible_value` | Mechanical coverage may be missing; no value answer |
| One or more exactly equal values, all known single-valued, no asserted change | `same_value_observed` | Identical stored strings, **not** independently corroborated truth |
| Different values, all explicitly single-valued, no asserted change | `competing_values_unresolved` | Competing current statements, **not** adjudicated contradiction |
| One or more multi-valued claims, even a single value | `coexistence_possible` | Open set; do not claim full enumeration or incompatibility |
| Any unknown cardinality, even a single value | `cardinality_unresolved` | Multiplicity unresolved; do not claim complete answer |
| Any assertion of a change, including one current claim | `change_assertion_unresolved` | No inference that a replacement was applied, was correct, or resolved older assertions |

The `value_coherence_unresolved` diagnosis and `continue_if_permitted` proposal take precedence over an otherwise met mechanical coverage threshold. Budget exhaustion, incomplete routes, and actual known contradictions are still surfaced separately. The old manual observer remains continuation-only because caller-provided `runtime_typed_observation` text is not authentic source evidence.

Comparisons are **strict literal equality**, without embedding similarity, lexical approximation, a synonym dictionary, temporal interpretation or provider calibration. This intentionally produces conservative disagreements (for example capitalization variants), which are preferable to silently conflating distinct assertions before the semantic equivalence policy is qualified. `SufficiencyReport.value_coherence[].fact_groups` records only admitted fact IDs grouped by equal stored value. It **does not export the actual text/value**, hash low-entropy secrets, claim independent sources, or assign confidence.

## Authority and safety

- The read is bounded to the original governed admitted IDs and repeats the current admission check *before* accessing persisted typed evidence. If scope changes, old references cannot expose new values. No cross-tenant raw candidate counts are introduced.
- A caller cannot supply a value claim to the persisted observer, pass in a false persisted origin label, or execute a stop. The manual diagnostic keeps its value-origin inputs separate and never recommends stop.
- A directly constructed report cannot claim `can_admit`, `can_mutate`, answer-quality verification or any non-none authority effect. A report containing unresolved typed values cannot even be constructed with `continuation_proposal=review_stop`.
- Multiplicity counts distinct admitted fact IDs, not independently authenticated sources; one source can produce multiple agreeing facts. Source independence, query-membership attestation, immutable recall snapshots, and arbitrary LLM truth estimates remain out of scope.
- The read does not promote `assertion=change` into an applied correction. True historical transitions remain governed by existing lifecycle/cross-fact rules and require a separate trustworthy linkage before being used as a resolution signal.
- Default facade, recall route execution, ranking policy, candidate admission, PAMA, audits, persistence writes, and corpus/benchmark scoring **do not change**.

## Evidence status and qualification gates

**Executed without hosted CI:** 27 focused Python tests passed against the exact current `evidence_sufficiency.py` source bytes, including 18 previous tests and nine independent new negative/control tests. The source Git blob is `2be4845989c5b9abb50efff23683ea26a3414a44`. This is **not** evidence that the newly edited `adapter.py`, `recall_control.py`, and checked-in integration test code passed in a full checkout.

The v7 candidate declaration `reports/runtime/baseline-v7-declaration.json` pins exactly three protected runtime blobs and names the new `governed-admitted-typed-value-coherence-v1` replay obligation. The baseline register retains `declared_successor=null`. No active baseline transition or merge.

Required before any PR, merge, or benchmark comparison:

1. **Local full-checkout qualification:** `test_evidence_sufficiency.py`, `test_recall_control.py`, `test_typed_propositions.py`, followed by full reference and repository suites. Verify no existing default outputs, state commitments or audit logs change.
2. **Independent adversarial cases:** conflicting single-valued claims, multi/unknown cardinality with one or many values, asserted change without applied correction, applied correction removing old-current visibility, foreign-scope injected refs, disputed/deleted/expired facts, forged raw origin labels, equality variants, repeated facts from the same source, mutated result lists and restart recovery.
3. **Baseline and reproducibility:** `docs/67-runtime-baseline-succession.md`, exact protected blob verification, proper successor declaration/register semantics, the public gauntlet, same-revision AMB and LongMemEval non-regression lanes, and a separate exact v6-to-candidate compare. Do not use GitHub Actions as a debugging runner.
4. **Benchmark neutrality:** No gold answer peeking, changing scorer corpora, route tuning to specific queries, or using a retrieval@k score as answer quality. New held-out conflicts must be authored independently and evaluated against baseline v6 in the same harness.
5. **Future actual adaptive stop:** must first bind query membership and current admission to an immutable receipt, distinguish governed state changes from unresolved assertions, and prove quality/latency tradeoffs on unseen corpora. This observer provides only the diagnostic input, never the stop policy.

**Maintainer guidance:** The parallel Claude task should perform local adversarial testing and independent same-harness evaluation on its own branch. It must not alter this working branch, main, frozen #732 R6, or launch paid GitHub Actions workflows.
