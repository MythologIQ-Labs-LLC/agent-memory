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

Every replay ran from a clean worktree pinned at the recorded revision, against frozen inputs (LongMemEval_S `d6f21ea9…c442`; AgentMemBench MemDialogue v2 `33632710…ca2a6`). Pre-remediation evidence is untouched. Artifacts:

- `reports/benchmarks/replays/538-query-conditioned-applicability-148823f/`: shipped relevance (admitted-set BM25), four temporal configurations.
- `reports/benchmarks/replays/538-query-conditioned-applicability-43a8484/`: token-overlap relevance ablation, including two reproduction checks.

Analyses are regenerated with `reference/analyze_applicability_replay.py` (`analysis-*.md` in each directory). Retrieval, currentness, question types, and failures are reported separately, with no aggregate score. **Runtime, ingestion, out-of-corpus, and unmapped-admission failures are zero in every configuration.**

### 5.1 Harness validation

Two variants reproduce frozen evidence **exactly**: `reproduce_f73b872` matches `f73b872`, and `reproduce_9c2ba70` matches `9c2ba70`. Both have 0 differing ranked lists on either plane. AgentMemBench `reproduce_9c2ba70` gives conflict 0.60 / 0.40, identical to `9c2ba70`. So every difference below is attributable to the policy configuration.

### 5.2 Under the shipped relevance (BM25), the temporal regime is benchmark-invisible

| configuration (`148823f`) | session r@5 | turn r@10 | latest-first KU session / turn | AMB conflict new/stale | AMB exact@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| universal newer-first + BM25 (`75bbe87`) | 0.823 | 0.723 | 0.457 / 0.557 | 0.20 / 0.80 | 0.899 |
| **query-conditioned + BM25 (policy 3.0.0)** | **0.823** | **0.723** | **0.457 / 0.557** | **0.20 / 0.80** | **0.899** |
| query-conditioned, host-declared dates | 0.823 | 0.723 | 0.457 / 0.557 | n/a | n/a |
| unspecified → newer among ties | 0.823 | 0.723 | 0.457 / 0.557 | n/a | n/a |
| unspecified → newer, host-declared dates | 0.823 | 0.723 | 0.457 / 0.557 | n/a | n/a |

- Every paired Δ against `75bbe87` is exactly 0, on every metric and question type.
- The regimes do produce different orders: 1 session row and 86 turn rows are reordered. **No gold item moves in any row.**
- Continuous BM25 scores almost never tie at gold positions, so the temporal stage almost never decides anything a benchmark scores.
- The currentness "give-back" recorded for #543 was therefore not a relevance-versus-currentness trade. BM25 removed the relevance ties that had let a tie-break act at all.

### 5.3 Under tie-heavy token-overlap relevance, the regime matters

`43a8484`, overlap relevance. Paired Δ is against the universal tie-break (`9c2ba70`), 95% bootstrap CI.

| measure | frozen `f73b872` | universal `9c2ba70` | query-conditioned (digest fallback) | query-conditioned (ascending-id fallback) | query-conditioned + host dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| session recall_all@5 | 0.675 | 0.687 | 0.668, Δ −0.019 [−0.041, +0.002] | 0.673 | 0.668 |
| session nDCG_any@5 | 0.722 | 0.732 | 0.729 | 0.719 | 0.729 |
| turn recall_all@10 | 0.525 | 0.532 | 0.516, Δ −0.017 [−0.036, +0.002] | 0.525 | 0.516 |
| turn nDCG_any@5 | 0.502 | **0.484** | 0.490 | 0.498 | 0.490 |
| session KU recall_all@5 | 0.931 | **0.889** | 0.889 | 0.917 | 0.889 |
| latest-first KU, **current-intent questions** (n=15) session / turn | 0.533 / 0.467 | 0.667 / 0.867 | **0.667 / 0.867** | **0.667 / 0.867** | **0.667 / 0.867** |
| latest-first KU, **no established intent** (n=54) session / turn | 0.278 / 0.481 | 0.611 / 0.704 | 0.426 / 0.574 | 0.278 / 0.481 | 0.426 / 0.574 |
| latest-first, all multi-date gold (n=282) session / turn | 0.372 / 0.411 | 0.532 / 0.589 | 0.457 / 0.500 | 0.383 / 0.440 | 0.461 / 0.500 |
| AMB conflict new / stale | 0.00 / 1.00 (`03197cd`) | 0.60 / 0.40 | **0.60 / 0.40** | n/a | n/a |

Reading, against the question this slice was asked to answer:

- **Genuine currentness gains are retained where the query expresses current intent.** On the 15 knowledge-update questions with an established current intent, latest-first equals the universal tie-break on both planes. AgentMemBench conflict keeps 0.60, because every conflict query says "current".
- **Where intent is not established, the recency gain is not retained, by design.** 54 of the 70 applicable knowledge-update questions carry no temporal cue. Their currentness expectation lives in the benchmark's task category, not in the question text. With the time-neutral fallback, part of the gain survives by chance (0.426 / 0.574). With the ascending-id fallback it returns exactly to frozen (0.278 / 0.481), because that fallback is an old-first clock.
- **The universal regressions partly disappear, but so do some universal gains.**
  - Recovered with the ascending-id fallback: session KU recall_all@5 (0.889 → 0.917) and turn nDCG@5 (0.484 → 0.498).
  - Given up: the universal tie-break also improved *atemporal* single-session types (single-session-user r@5 0.938 → 0.984, preference 0.333 → 0.433). The query-conditioned regime gives those back.
  - Cause: the haystack construction places gold slightly late in write order (mean gold position 0.54–0.59 for single-session types against 0.50 uniform). Recency was exploiting a positional artifact, not temporal semantics. Those samples are small (n = 30–70).
  - Net retrieval against universal is not distinguishable from zero on either plane: session −0.019 [−0.041, +0.002], turn −0.017 [−0.036, +0.002].
- **Host-declared observation time barely changes anything.** It matters only inside current-intent ties: all multi-date latest-first moves 0.457 → 0.461 on session and is unchanged on turn. The C5 clock separation is correct and observable in evidence. The benchmark rarely exercises it.
- **Stable fallback.** A time-neutral digest vs ascending id trades KU recall_all@5 and turn nDCG@5 (id is better) against latest-first (digest is better) on this benchmark. The digest is kept as the default because the ascending id is a hidden clock. The benchmark effect of that choice is itself an artifact of write order.

## 6. What the evidence says about ADR-039

**Overall: it narrows the proposal, and it is not contradicted.**

Supported:

1. **Semantic separation is necessary for declared temporal evidence.** The universal regime fails C1, C2, C5, C18, and C23, or cannot express them. The query-conditioned policy meets them without any regression on either external gauntlet.
2. **Query-conditioning keeps currentness where the query asks for it** (15/15 current-intent KU questions, AgentMemBench conflict 0.60) and withholds recency where the query does not, with no measurable net retrieval cost.
3. **Clocks must stay separate.** The pre-slice "temporal evidence" was transaction time. In 211/500 LongMemEval_S haystacks, transaction order and session-date order disagree.

Narrowed:

1. **Condition 2 is partly triggered for benchmark-observable behavior.** On both external gauntlets under the shipped relevance, typed applicability is metric-identical to the universal tie-break. Its benefit is demonstrated only with declared temporal evidence (the fixtures), which neither gauntlet supplies. The empirical claim should be scoped to workloads that carry validity or temporal intent. Neither LongMemEval_S nor AgentMemBench does, beyond question wording.
2. **Interpretation is the binding constraint.** Only 16 of 78 knowledge-update questions contain a high-confidence temporal cue. ADR-039's "ranking quality is bounded by query-interpretation quality" is confirmed strongly. Task-level intent (a host knowing it is asking about current state) must be declarable, and it is (`temporal_intent`). No deterministic text interpreter recovers it from these questions.
3. **"Universal-tie-break regressions" were not one class.** Some were real (KU recall, turn nDCG). Some universal *gains* came from a benchmark positional artifact. Neither aggregate is evidence about temporal semantics.

Not tested:

- **Condition 1** (a simpler universal scalar matching query-conditioned applicability across current, historical, as-of, and prospective workloads). The external gauntlets contain no declared validity and almost no historical, as-of, or prospective intent. The acceptance gate's orthogonal-benchmark item is **unmet**. A workload with declared validity intervals and as-of or historical queries is needed.

Additional dimensions the evidence says are missing (recorded, not squeezed into this profile):

- **Exception / specificity precedence** (C4 during the exception).
- **Event-relative temporal relations** (C15).
- **Historical admission of governed-superseded states** (C14 / C25). This is an admission-level gap against docs/26 (governed recall, line 265), not a ranking change.
- **Property identity and cardinality** for conflict detection (C8–C11 coexistence is met only because nothing is inferred).
- **Memory-side temporal self-description.** AgentMemBench's stale-strictly-higher class: "…has moved and now lives in X" states its own currentness in text, and a governed write-time interpretation could declare it instead of guessing at read time.

## 7. Remaining uncertainties

- The cue lexicon is small and English-only. Its false-positive and false-negative rates beyond these datasets are unmeasured.
- Applicability without a `reference_time` cannot evaluate declared intervals (`no_reference_time`). Hosts must supply the reference clock for current-state claims.
- The timeline shape is conveyed through per-candidate evidence because the public result envelope does not allow new top-level fields. A first-class structured recall result would be a contract change.
- Timing in these replays is host-shared and is not performance evidence.
