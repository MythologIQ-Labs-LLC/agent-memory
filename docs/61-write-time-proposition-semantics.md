# Write-Time Proposition Identity, Cardinality, and Temporal Self-Description (#550)

Status: **implemented on main and naturally qualified by #594**. ADR-039 remains **Proposed**; nothing in #550 or #594 promotes it. PR #587 / #583 remains **DRAFT / HOLD**.

The detailed revision-bound #550 replay artifacts remain under `reports/benchmarks/replays/550-write-time-semantics-eb44c34/` and the frozen #580 evidence under `reports/benchmarks/temporal-currentness/`. The current natural-data qualification is `reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md`.

## 1. Architecture

```text
memory text + caller-declared write metadata
  -> bounded, deterministic, versioned write-time interpretation      (evidence)
       proposition candidate: entity / property / value
       cardinality evidence
       temporal aspect
       bounded self-validity
       change / coexistence / hedge / self-claim markers
  -> classification against current same-scope same-slot memories     (evidence)
  -> governed state-change proposal when eligible                      (evidence)
  -> existing lifecycle under PAMA
       only when a caller chooses to apply the proposal
```

Interpretation is evidence, never authority:

```text
interpretation != authority
semantic interpretation != retention/lifecycle policy
proposition match != authority to replace
classifier confidence != truth
single-valued candidate != automatic supersession
conflict detection != mutation
proposal != application
newer != superseding
historically true != corrected-as-false
```

## 2. Typed write-time contract

The native deterministic interpreter records:

- proposition status (`known`, `ambiguous`, `unknown`) and candidate entity/property/value;
- cardinality (`single_valued`, `multi_valued`, `hierarchical`, `unknown`);
- change, coexistence, hedge, and self-claim markers;
- temporal aspect (`present`, `prospective`, `past_habitual`);
- bounded interpreted self-validity when an explicit temporal expression can be anchored to caller-declared `observed_at`;
- same-slot relation evidence and any governed state-change proposal.

Every interpretation has `authority_effect: none`.

The persisted interpretation is versioned at write time. Historical writes are not silently reinterpreted when the interpreter changes.

## 3. Temporal self-validity boundary

Caller-declared `valid_from` / `valid_until` remains stronger than interpreted text.

Interpreted self-validity is asymmetric:

```text
caller-declared validity
  > interpreted self-validity as LIMIT ONLY
  > unknown temporal basis
```

A resolved interpreted window may demote a memory that is outside its own asserted applicability interval. It may never affirm that memory as current merely because its text says it is current.

That limit-only rule is ranking policy **3.1.0**. BM25 and lexical relevance are otherwise unchanged by #550.

## 4. State-change proposal boundary

A same-slot relationship can be classified as same value, coexistence, state-change candidate, conflict, or unresolved. A state-change candidate can produce a proposal, but proposal creation is not mutation.

A caller must explicitly apply an open proposal through the existing governed correction lifecycle. Hedged writes, self-authority claims, unknown/ambiguous propositions, ineligible scope, or insufficient evidence do not become automatic corrections.

The #549 distinction remains intact: a changed real-world state is a state change, not an error correction.

## 5. #550 repository-owned evidence

Against the frozen #580 currentness gauntlet:

- required passes regressed: **0**;
- four target units improved from `honest_unknown` to `pass`;
- self-description currentness target rate improved **0.091 -> 0.273**;
- interpreted self-validity fixed the intended after-interval and before-start target cases without allowing self-affirmation;
- automatic proposal application remained falsified because it breaks required no-mutation/admission units.

The external #550 replay changed no AgentMemBench or LongMemEval_S ranking row because those canonical runs do not declare `observed_at`, so interpreted windows do not resolve and proposals are never auto-applied.

## 6. #591 performance repair

#550 made an existing substrate inefficiency visible because every fact now carries a small semantic record. Candidate discovery was materializing and decoding all tenant facts before #548 identity/domain eligibility narrowed the set.

#591 changed the implementation shape to:

```text
lightweight identity projection
  -> #548 identity/domain eligibility
  -> lexical candidate scoring
  -> materialize surviving full facts only
  -> full eligibility
  -> canonical admission
```

No ranking/admission/authority/semantic contract changed.

Accepted performance evidence:

- AgentMemBench wall: **54.6 s -> 38.6 s**;
- search p50: **17.9 ms -> 7.7 ms**;
- search p95: **31.4 ms -> 11.9 ms**;
- full fact materializations: about 1,020 -> about 30 per search;
- JSON decodes: about 2,041 -> about 61 per search;
- search orders and BM25 score bits unchanged;
- LongMemEval_S canonical rows unchanged.

Evidence: `reports/benchmarks/replays/591-identity-first-materialization-f76c441/`.

## 7. #594 Phase A: source-anchored external qualification

#594 added a defensible **adapted external evidence** profile using the existing LongMemEval_S session timestamps.

Profiles:

- C: canonical;
- P1: source/session date -> caller-declared `observed_at`;
- P2: P1 plus the question date as a host-declared recall `reference_time`.

Result:

- session mapped 23,867 / 23,867;
- turn mapped 122,416 / 122,416;
- interpreted self-validity resolved for 8 session memories and 33 turn memories;
- **0 changed ranking rows** and **0 changed gold ranks** under P1 or P2;
- 0 admitted candidates in the ordering-intent audit carried applicability basis `interpreted`;
- the one admitted resolved-window turn was non-gold at rank 132 and the P2 reference time was inside its window, so limit-only semantics correctly did not affirm it.

The correct conclusion is therefore:

> **EVIDENCE GAP for external demotion efficacy on this corpus, not runtime failure.**

LongMemEval_M escalation for this adapted profile was not warranted because S already characterized the reachable mechanism population.

## 8. #594 Phase B: accepted natural-language proposition qualification

Coverage counts from the full LongMemEval_S corpus were never sufficient to establish precision. #594 therefore froze a separate 268-turn natural-language corpus before scoring:

- Part R: 100 random turns, the population-estimating sample;
- Part S: 168 stratified turns for diagnostic categories only.

The annotation process preserved five versioned drafts. Interpreter output was not run or consulted during label creation/review. Maintainer review `5339771805` accepted v5 as the semantic source for immutable `gold-v1.json`.

Accepted gold counts:

- known: 148;
- ambiguous: 35;
- unknown: 85.

The property-alias table was frozen empty before scoring to prevent after-the-fact benchmark fitting.

### First accepted score

Scored head: `73216bebc596de4876692a8f00d1e3fabaa899f1`.

On unbiased Part R:

| status | precision | recall |
| --- | ---: | ---: |
| known | **0.800** | **0.148** |
| ambiguous | 0.210 | **1.000** |
| unknown | **1.000** | 0.848 |

Gold-known confusion is the dominant result: 8/54 gold-known turns are recognized as known and **46/54 become ambiguous**.

The runtime is therefore materially under-capable relative to the accepted semantic contract, but its dominant natural failure is conservative abstention/ambiguity rather than unsafe known-status promotion.

Part R also records:

- wrong proposition slot: 8;
- unknown -> known overreach: 2;
- temporal-aspect mismatch: 4;
- temporal-aspect over-classification: 1;
- over-eager single-valued cardinality: 0.

Strict slot/value conformance is 0 with the frozen empty alias table. This is an exact-label diagnostic, not semantic synonym precision. Inspection contains both harmless synonym/normalization variation and real malformed property/value boundaries, so canonicalization must be defined independently before re-score.

## 9. Active limitations and follow-ons

The qualification created three bounded remediation issues:

- **#596**: improve natural proposition recognition without weakening abstention;
- **#597**: define canonical property/value boundaries and pre-score normalization without post-hoc alias fitting;
- **#598**: calibrate write-time temporal aspect on natural turns.

#598 is on the temporal critical path because redesigned #583 depends on trustworthy memory-side aspect evidence. #585 remains the separate query-side temporal-intent calibration issue.

#596/#597 are high-priority interpreter-quality limitations. They are not automatically RC blockers while their dominant behavior remains conservative evidence abstention and does not create authority. Final RC evidence may still promote them onto the critical path if the declared product contract requires it.

Other unchanged limitations:

- pre-#550 facts have no stored interpretation and require an explicit migration to be reinterpreted;
- interpreted self-validity never affirms applicability;
- no semantic proposal applies automatically;
- implicit supersession of independently written contradictions remains outside this parser's authority;
- ADR-039 remains Proposed.

## 10. Current dependency map

```text
#550 IMPLEMENTED
  -> #591 PERFORMANCE REPAIR COMPLETE
  -> #594 NATURAL QUALIFICATION COMPLETE / QUALIFIED
  -> current dashboard regenerated
  -> #585 query-intent span calibration
  -> #598 memory-side aspect calibration
  -> redesigned #583
  -> final #580 replay
  -> #584 policy ruling
  -> RC1 declaration decision
```

Canonical current dashboard: `reports/benchmarks/dashboard/current.md`.

Full #594 closeout: `reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md`.

ADR-039 remains **Proposed**. Interpretation grants no authority.
