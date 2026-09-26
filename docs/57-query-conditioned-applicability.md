# Query-Conditioned Recall Applicability: First Reference Profile

Status: implementation and conformance evidence for #538, under the **Proposed** ADR-039 (#544, PR #545). This document does not promote ADR-039. Doctrine promotion remains a separate, explicit maintainer ruling.

The question this slice answers is narrower than "make currentness benchmarks green":

> Can Agent Memory order admitted memories by **what** the query is about and, separately, **when** the query is about, without turning either into authority, metabolic persistence, truth, or one universal score?

## 1. Present behavior before this slice (policy 2.x)

These properties were recorded from the code at `main` `0007f5f` (policy 2.0.0) and `recall/538-admitted-bm25` `6e81542` (policy 2.1.0).

Ranking was one lexicographic key, applied identically to every query:

```text
route corroboration count
  -> exact logical identity
  -> route-native scores in declared order (2.1.0: admitted-set BM25 for the lexical route)
  -> temporal evidence: newer first            <- universal, for every query
  -> ascending candidate_ref
```

Findings:

1. **The temporal stage was universal.** No representation of query temporal intent existed. A query about the past, a query about ideas, and a query about the present all received the same newer-first preference among relevance ties.
2. **The "temporal evidence" was transaction time.** `GovernedMemoryAdapter._write` sets both `valid_at` and `created_at` from the runtime's own write clock. The facade accepted no caller-declared valid, observation, or event time. The policy read `valid_at` and labelled it "event-time axis", but that value was the write order. This is the clock collapse ADR-039 C5 forbids.
3. **The stable fallback was also a clock.** Candidate identifiers are allocated in write order, so ascending `candidate_ref` meant "older first". That is the anti-recency accident #540 set out to remove, still present as the final stage.
4. **Recall had no reference time and no as-of path.** Current, as-of, historical, and prospective queries were indistinguishable.
5. **Admission refuses governed-superseded facts for every query** (`superseded_not_current`). Historical or as-of recall can therefore never see a governed prior state. `history()` serves it. This is an admission property, not a ranking one, and this slice does not change it.
6. **On real data the proxy is wrong often.** In frozen LongMemEval_S, 211 of 500 haystacks are **not** written in session-date order. For those rows, "newer transaction" and "newer session" disagree. The latest-first metric scores by session date.

## 2. Design chosen (policy 3.0.0, `temporal_regime = query_conditioned`)

```text
query
  -> temporal intent (explicit caller intent, else bounded deterministic inference, else unspecified)
  -> candidate routes -> canonical governed admission (unchanged)
  -> admitted candidates only
  -> typed relevance evidence (route evidence, exact identity, admitted-set BM25)
  -> typed temporal evidence (declared valid_from / valid_until / observed_at, transaction time)
  -> temporal applicability relative to the intent's target instant
  -> staged ordering:
       1. temporal applicability tier        (non-compensatory; only under established intent)
       2. route corroboration
       3. exact identity
       4. route-native relevance (never summed or cross-scaled)
       5. temporal order within the intent's regime (only under established intent)
       6. time-neutral stable fallback (digest of candidate_ref)
  -> per-candidate evidence: intent, clocks, applicability, the stage that ordered it before its successor
```

### Temporal intent (`agentmem_ref.runtime.temporal_intent`)

- Modes: `current`, `as_of`, `historical`, `atemporal_or_unspecified`, `prospective`. Recall shapes: `ranked` and `timeline`.
- **Explicit intent is authoritative.** `recall(..., temporal_intent={...}, reference_time=...)` (C17).
- **Inferred intent comes from a frozen, generic-English cue lexicon.** It was committed (`bb4cc29`) before any benchmark question was inspected, and it contains no dataset identifiers (C21). Each cue is high- or low-confidence.
- **Only explicit or high-confidence inferred** `current` / `as_of` / `prospective` intent influences ordering. Low-confidence cues, `historical`, and `atemporal_or_unspecified` apply no temporal preference (C16).
- **Conflicting cues preserve ambiguity.** The result is `atemporal_or_unspecified`, low confidence, with both cue sets kept as evidence. The interpreter never picks one.
- Unspecified never silently means current. The alternative that does (`unspecified_intent_order = newer_first_among_ties`) exists only as an explicit, versioned, off-by-default option so it can be measured (§5).

### Temporal evidence

- `remember` and `correct` accept `valid_from`, `valid_until`, and `observed_at` (ISO-8601).
- These are stored with the fact as `declared_temporal` with `basis: caller_declared`, so the canonical-state digest covers them.
- **They are evidence, not lifecycle.** An elapsed `valid_until` never refuses at admission, never supersedes, and never changes currentness. It deliberately does **not** reuse the substrate's `invalid_at`, which admission treats as supersession. Reusing it would turn temporal applicability into admission (ADR-039 Alternative D).
- Every candidate records each clock separately: `declared_valid_from`, `declared_valid_until`, `declared_observed_at`, and `transaction_time`. The substrate's runtime-assigned `valid_at` is reported as write-clock-based, not as valid time.
- Ordering compares clocks only within the same kind, in the order declared valid time > declared observation time > transaction time (a declared weak fallback). The clock used is recorded.

### Applicability

- `applicable`, `outside_target_interval`, `prospectively_applicable`, `applicable_not_prospective`, `unknown_temporal_basis`, `no_reference_time`, and `not_evaluated` describe how declared validity relates to the intent's target instant.
- A candidate is **demoted, never removed**, only when its **declared** validity establishes that it does not apply to the target. That means expired or not-yet-valid for current and as-of intents, and past or presently-valid for prospective intent.
- Demotion is non-compensatory: relevance cannot rescue a candidate from it (C1, C23).
- **Unknown temporal basis is not demoted and not promoted.** It is recorded. A candidate with no declared validity is neither timeless nor current.

### What is not in the policy

- **Metabolic evidence:** `metabolic_evidence: not_used` on every candidate (C7).
- **Authority:** `authority_effect: none`. Admission runs first and is unchanged. A refused candidate has no ranking evidence and no rank influence (C12).
- **Supersession:** independent later writes never supersede (C8–C11). Supersession stays a governed correction.

## 3. Alternatives considered and why they were not chosen

| alternative | status | reason |
| --- | --- | --- |
| Keep 2.x universal newer-first tie-break | retained as `temporal_regime = universal_newer_first` for reproduction only | Applies recency to atemporal and historical queries, where it produces the measured non-currentness regressions (§5). Its "temporal" evidence was transaction time. |
| Relevance always dominates, no temporal stage (`none`) | retained as `temporal_regime = none` | Cannot represent C1, C4 (after expiry), C18, or explicit current queries at all. |
| Weighted sum `a·relevance + b·recency` | rejected, not implemented | Route scores are not cross-comparable, and ADR-039 C1/C2 need non-compensation, which a sum cannot express. No calibration evidence exists. |
| Treat declared expiry as admission refusal (`invalid_at`) | rejected | Makes temporal applicability an authority decision (ADR-039 Alternative D) and hides historical evidence from as-of and historical queries. |
| Unspecified intent defaults to newer-first among ties | implemented as an off-by-default, versioned option and measured (§5) | ADR-039 requires such a default to be explicit and justified per query class. The measurement decides whether it earns that. |
| Interval specificity / exception precedence stage | not implemented; recorded as a missing dimension | Needed for C4's first half (§4). It is a defeasibility relation, not recency, and should not be squeezed into the temporal stage. |
| Stable fallback by ascending `candidate_ref` | retained as an option (`stable_fallback = candidate_ref_asc`) | It is a hidden write-order clock. The default is a time-neutral digest. |

## 4. Adversarial conformance (`reference/tests/test_query_conditioned_applicability.py`)

Negative control: run against the 2.x universal regime, 12 of the 18 base fixtures fail. C1, C5, and C7 fail on the ordering itself. The rest fail because 2.x records no typed temporal evidence.

| case | outcome |
| --- | --- |
| C1, C23: current query, expired exact match vs valid weaker match | **met**. The valid match ranks first despite lower BM25, ordered by `temporal_applicability_tier`, and the expired match stays admitted as context. |
| C2: as-of query | **met**. An inferred `as_of 2018` puts the then-valid record first, and the later record is `prospectively_applicable`. |
| C3, C22: atemporal query | **met**. `not_evaluated`, no ordering clock, and an older, more relevant memory beats a newer distractor. |
| C4: temporary exception | **partially met**. After expiry the ordinary rule is first without reinsertion. **During** the exception both are applicable, and relevance, not exception precedence, decides. The missing dimension is recorded. |
| C5: disagreeing clocks | **met**. Declared valid time orders, not later observation or transaction time. All clocks are reported separately. |
| C6: unknown basis | **met**. `unknown_temporal_basis` is exposed, the fact is not demoted, and the transaction clock is labelled as a fallback. |
| C7: metabolic strength | **met** by construction. Metabolism is not used, and repeated use of a stale memory does not change current ordering. |
| C8–C11: independent writes, multi-valued, hierarchical, multi-employer | **met**. All remain admitted and current, and nothing is superseded. No property or cardinality model exists yet. |
| C12: wrong-scope perfect match | **met**. It is refused, has no ranking evidence, and does not appear in the admitted order. |
| C13, C14: timeline, independent states | **met** for independently written states: `recall_shape: timeline` with chronological positions, and the ranked list is not collapsed. |
| C14, C25: governed supersession | **limitation**. The superseded state is refused at admission for every intent, including an explicit `historical` one. It is reachable only through `history()`. Changing that is an admission and governance decision. docs/26 (governed recall, line 265) already expects "time-scoped query can retrieve superseded historical truth", so this is a real doctrine-to-runtime gap. |
| C15: event-relative relation | **limitation**. "Immediately before X" yields only a low-confidence historical cue, and no event relation participates in ordering. |
| C16: low confidence and ambiguity | **met**. Low-confidence cues do not demote, and conflicting cues stay ambiguous. |
| C17: explicit over inferred | **met**. An explicit `as_of` overrides the text's `current` cue. |
| C18: prospective | **met**. A future-valid commitment ranks first for a prospective query and is demoted for a current query. |
| C19, C20: determinism and versioning | **met**. Order is identical across calls and restart, and policy 3.0.0 and the regime are recorded per candidate. |
| C21: no benchmark branching | **met**. The policy and interpreter modules contain no dataset identifiers or benchmark ontology terms. |
| C24: disputed | **stronger than required**. This runtime refuses disputed facts at admission, so applicability never presents them. |

## 5. Replay evidence

Recorded in `reports/benchmarks/replays/538-query-conditioned-applicability-148823f/` and summarized below once the runs complete.
