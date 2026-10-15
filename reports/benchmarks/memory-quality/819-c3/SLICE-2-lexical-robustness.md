# C3 slice 2: word forms, typos and set-evidence anchoring (verification record)

Base: slice 1 `dbbc74d9`, on branch `claude/eager-dirac-bftkfg-819-evidence-sets`. C2 (`eaf60e4d`)
and its evidence branch are untouched. Selection policy `2.1.0`, normalization `1.1.0`. This is a
candidate within the 1.9.0 contract line. The public contract version is not advanced and no
baseline is declared.

## Problem

After slice 1, exact-token matching still lost evidence, at two points:

- **At discovery.** The lexical route proposes a fact only if it shares a token with the query.
  So "How many weddings did I attend?" found nothing in a store that says "wedding". A
  misspelled name ("typsecript") found nothing at all.
- **In relevance.** The same mismatch kept found facts below the floor: "attended" ≠ "attend".

## Change

- **`runtime/lexical_normalization.py`** (new, pure functions):
  - `normal_form` is Porter (1980) step 1 only: plurals, `-ed`/`-ing`, terminal `y`.
    Derivational steps were tried and rejected: they merged "observability" with "observer" and
    "preferences" with "prefers", which turned morphology into false evidence.
  - `typo_matches` allows one Damerau–Levenshtein edit, for terms of five or more letters.
  - Correction is allowed only when the query has at most three topical terms **and none of them
    matched anything** (`typo_correction_allowed`). Without a lexicon, any absent real word looks
    like a typo: "sending" is one edit from "spending".
- **Discovery** (`runtime_composition._discovery_query`):
  - The lexical route searches the query plus the inflectional and typo variants found in the
    vocabulary of **current, live (not forgotten), tenant, domain-eligible** facts.
  - Ranking still scores the query as written.
  - Every candidate still crosses governed admission.
  - `return_policy.query_expansion` reports counts only, never terms.
- **Selection** (`return_selection`, 2.1.0):
  - Relevance compares normal forms.
  - Typo correction uses the admitted vocabulary, under the same guard.
- **Set evidence no longer anchors ranking consistency.**
  - Found by measurement, not by design. With normal-form matching, a weak set member ranked low
    pulled in every fact ranked above it that carried any topical trace: 1,056 returns on
    LongMemEval-S, of which 14 were gold.
  - Ranking consistency now extends only from primary evidence (content relevance, exact identity,
    non-lexical routes), which is C2's original semantics.
- **Interpretation.** "versus"/"vs" were removed from the relational cues. A choice between
  alternatives is usually answered by one decision, not by a set.
- **Adapter.** `current_live_fact_uuids()` (read-only) and `SqliteSubstrate.discovery_rows()` (an
  identity and text projection, no JSON decode).

## Tests

**New tests:**

- `reference/tests/test_lexical_normalization.py`, 12 tests:
  - Porter step-1 pairs, derivational families kept apart, the one-edit and length gates, and the
    expansion cap;
  - inflections meet, a typo reaches its memory, and exact ranking is unchanged;
  - an absent topic is not "corrected" into noise, and no correction happens when the topic
    matched.
  - **Forgotten, superseded and other-scope text never shapes discovery.** The forgotten and
    superseded cases first recall the fact, so its tokens are resident in the planner memo, and
    then show that they stop shaping discovery.
- `test_evidence_set_selection.py` adds `SetEvidenceDoesNotAnchorRanking`. It fails on slice-1
  selection (`['strong', 'trace', 'set']`) and passes on 2.1.0.

All 50 tests in the three selection files pass.

**Full suite**, run from the repository root with
`python3 -m unittest discover -s reference/tests -t reference`: 2611 tests, 36 skipped,
1 failure. The failure is `test_evaluation_only_change_keeps_runtime_baseline_equivalence`, the
Runtime Baseline gate, which fails by design for any runtime change without a declared successor.

## Diagnostic measurements (not holdout evidence: these sets informed the diagnosis)

**LongMemEval-S session plane, 500 questions** (419 answerable, 81 abstention). Scored from facade
traces (`scripts/lme_trace.py`, `scripts/lme_eval_trace.py`) with the frozen runner's arithmetic.
"Precision" is pooled: gold returned sessions over all returned sessions, answerable questions only.

| | A `1df28f84` | C2 | Slice 1 | Slice 2 |
|---|---:|---:|---:|---:|
| recall_any@1 | 0.809 | 0.814 | 0.831 | 0.831 |
| recall_all@5 | 0.823 | 0.747 | 0.842 | **0.862** |
| recall_all@10 | 0.893 | 0.754 | 0.871 | **0.905** |
| multi-session recall_all@10 | 0.827 | 0.595 | 0.777 | **0.851** |
| temporal-reasoning recall_all@10 | 0.895 | 0.693 | 0.874 | **0.906** |
| knowledge-update recall_all@10 | 0.987 | 0.903 | 0.972 | 0.972 |
| Mean sessions returned | 45.1 | 3.0 | 4.3 | 4.7 |
| Pooled precision of returned sessions | — | **0.510** | 0.402 | 0.381 |
| Abstention questions: mean returned | 45.3 | 3.0 | 5.1 | 5.1 |

Before the anchoring fix, slice 2 measured all@10 0.909, mean returned 5.90, precision 0.305 and
5.4 returned on abstention questions.

Paired on all@10:

- **Slice 2 vs slice 1: 17 fixed, 3 broken.**
  - Fixed, for example: "How many weddings have I attended in this year?", "How many movie
    festivals that I attended?", "How much total money did I spend on attending workshops in the
    last four months?", "What was the airline that I flied with on Valentine's day?".
  - Broken: "How many properties did I view before making an offer on the townhouse…", "…an
    art-related event two weeks ago. Where was that event held at?", "How long have I been working
    before I started my current job at NovaTech?".
- **Slice 2 vs C2: 65 fixed, 2 broken.** The broken ones are "What was my previous occupation?"
  (frame-word-only gold) and the NovaTech question.

**The honest cost.** Recall is above A at all@10 with about a tenth of A's returned volume. But
the precision of what is returned has fallen at every step since C2: 0.510, then 0.402, then
0.381. Multi-evidence recall was bought partly with weaker set members. Whether that trade is right
is a question for the independent holdout and for downstream answer quality, not for these
diagnostic sets.

**AMB PrecisionMemBench, 77 cases** (native scorer, AMB `03c1d0f`, scratch runs):

| | C2 | Slice 1 | Slice 2 |
|---|---:|---:|---:|
| Strict success | **39/77** | 39/77 | 38/77 |
| Mean precision | **0.541** | 0.530 | 0.522 |
| Mean recall | 0.878 | 0.908 | **0.942** |

Slice 2 vs C2: 3 fixed, 4 broken (exact McNemar p = 1.0).

- Fixed: `fuzzy-single-term-only-signal`, `happy-alias-match-kubernetes`,
  `relation-does-not-appear-as-entity`.
- Broken: `alias-protagonist-resolves`, `fuzzy-prefix-blocks-transitive-match`,
  `ranking-canonical-name-over-content`, `ranking-orderedbefore-alias-beats-content`. These are
  threshold effects: inflection matching gives extra facts enough topical relevance to clear the
  floor.

AMB was not tuned further; held-out v2 decides.

**Equivalence after optimisation.** The latency change below produces byte-identical selection
traces on all 500 LongMemEval-S questions and identical AMB outcomes (0 fixed, 0 broken).

## Cost

Synthetic stress store: 36-word vocabulary, so most facts match most queries. Measured through the
facade with `recall(budget=10)`, p50 of five repetitions per query, on one 4-CPU container.

| Facts | Query | Slice 1 candidates | Slice 1 p50 | Slice 2 candidates | Slice 2 p50 |
|---:|---|---:|---:|---:|---:|
| 3000 | "what recipe did I use for coffee" | 1622 | 340 ms | 1622 | 407 ms |
| 3000 | "When is the project deadline?" | 1661 | 358 ms | 1661 | 414 ms |
| 3000 | "typsecript compilation config" | 0 | 32 ms | 0 | 50 ms |
| 3000 | "How many weddings did I attend?" | **0** | 29 ms | **984** | 265 ms |
| 1000 | "what recipe did I use for coffee" | 552 | 103 ms | 552 | 116 ms |

- **At equal candidate counts, slice 2 costs +12–20%.** That comes from the vocabulary scan (about
  18 ms at 3,000 facts) and from normalising admitted texts in selection.
- The large increase on "weddings" is the improvement itself. Slice 1 found nothing; slice 2 admits
  the 984 facts that mention weddings, and admission is per candidate.
- The first implementation materialised every fact to build the vocabulary (p50 324 ms on the
  mixed set). It was replaced by an identity and text projection, the identity form of the same
  eligibility predicate, and a token memo keyed by fact uuid that is pruned to the live, eligible
  set on every recall.
- There is no new storage.

## Security and governance review (self-review; the independent review is at freeze)

- **Discovery vocabulary.** It is built only from current, non-tombstoned facts in the caller's
  tenant that pass the same identity eligibility predicate as the lexical route. Tests attack
  forgotten, superseded and other-scope text, including after the text was resident in the memo.
- **Expansion only widens discovery.** Every candidate crosses full governed admission, ranking is
  unchanged, and selection can only remove facts.
- **`query_expansion` reports counts, not terms.** A count can reveal that some eligible fact
  contains a variant, but the caller is already entitled to read that fact.
- Nothing here reads memory text as instructions or grants authority. The cue and frame lists are
  closed English vocabularies and name no dataset.

## Remaining gaps

- **The precision of returned sets is falling.** See the measurements above. A calibrated set
  floor, or a per-member coherence test, is a candidate for later work, and only if the holdout
  agrees.
- **Zero-overlap evidence.** 51 of 148 slice-1 losses share no informative term with the
  question. The local ONNX semantic route works but is off by default, and its candidates bypass
  selection (`non_lexical_route_evidence`), so enabling it unchanged would return every vector
  neighbour. Calibrating it inside selection is deferred: it needs its own measurement.
- The cue lists and morphology are English-only.
- Typo tolerance covers one edit, terms of five or more letters, and only short queries whose
  topic matched nothing. Longer misspelled queries are not corrected.

## Next: slice 3 (structured memory and lifecycle)

The AMB failures that remain cluster in type routing (0/6), scope disambiguation (3/12) and
supersession chains (0/3). AMB supplies scope as caller data at ingest (`tags: scope:*`). The
runtime already has isolation domains, typed propositions, `source_ref` and governed correction,
but the bridge forwards none of the ingest scope. Slice 3 asks whether caller-declared scope and
type at ingestion can be honoured generally, without inference at retrieval and without adopting
AMB's dataset-supplied retrieval filter, whose name-matching rules are benchmark logic.
