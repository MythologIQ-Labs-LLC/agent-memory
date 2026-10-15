# C3 slice 1: evidence-set construction (verification record)

Base: C2 `eaf60e4d`, evidence head `3179ffa5`. The branch is `claude/eager-dirac-bftkfg-819-evidence-sets`.
C2 is left untouched.

## Architectural problem

C2 judged every admitted fact on its own, against one floor relative to the best match. Tracing
all 500 LongMemEval-S questions through the facade (`scripts/lme_trace.py`) showed 148 gold
sessions withheld, in three groups:

1. **Frame words were treated as topic.** Words such as "how *many*", "*total*", "*months*",
   "*currently*" and "*last*" describe the shape of the answer, not its subject. Sessions that
   matched only "many" ranked top and set the relevance scale, which pushed topical evidence
   below the floor. Example: for "How many magazine subscriptions do I currently have?", the top
   returned session matched only "many".
2. **The information requirement was ignored.** Aggregate questions ("how many", "total", "all")
   and relational ones ("before", "older than", "since") need several pieces of evidence. Each
   piece is a weak standalone match: median relative score 0.30, but median rank 7, so ranking
   already found them and only the floor cut them. Only 4 of 148 shared the top fact's
   strongest term, so "same-aspect siblings" was the wrong model.
3. **No lexical overlap at all.** 51 of 148 withheld gold sessions share no informative term with
   the question. No lexical rule can find these (slice 2: semantic).

## Change (selection policy 2.0.0)

- **`runtime/query_interpretation.py`.** A deterministic reading of the query that separates:
  - topical terms from frame terms (a closed vocabulary of quantity, time-unit and request
    words);
  - the information requirement (`single`, `aggregate` or `relational`, from closed English cue
    lists);
  - entity mentions, found by orthographic rules: capitalised mid-sentence, acronym, CamelCase,
    letter–digit tokens, or quoted text.
- **Evidence set.** It is built from:
  - primary evidence (topical relevance at or above half the best);
  - set evidence for aggregate and relational queries (at or above a quarter of the best);
  - ranking consistency;
  - the fact most about each named entity.
- **Frame-only queries.** A query that is all frame uses its frame words. A query that has a
  topic but nothing about that topic **abstains**; it does not fall back to frame words.
- **Unchanged:** ranking, admission and governance. `return_policy` records the interpretation.

## Tests

`reference/tests/test_evidence_set_selection.py`, 13 tests, all passing. They cover:

- the interpretation itself;
- aggregate questions keeping weaker items;
- single-answer queries not using the set floor;
- frame-only matches withheld;
- a set cue with no topical evidence abstaining;
- frame fallback;
- entity coverage choosing the fact *about* the entity, not one that mentions it in passing;
- a keyword-stuffed fact;
- determinism and ranked order;
- forgotten, superseded and other-scope facts never entering a set.

The C2 tests (24) still pass.

**Full suite** (from the repository root): 2598 tests. The failures are the Runtime Baseline
gate, which fails by design, and the layout-table entry for the new module, now fixed.

Defects found and fixed during the slice, all in my own new code:

| Defect | Fix |
|---|---|
| The first entity rule used the highest-ranked fact that merely mentioned an entity | Use the fact most about the entity |
| A passing mention counted as coverage | Coverage requires the fact most about the entity |
| "NOT" read as an acronym name | Emphasis words are never names |
| Falling back to frame words when the topic matched nothing | The recall abstains |

## Diagnostic measurements (not holdout evidence: these sets informed the diagnosis)

**LongMemEval-S session plane, 500 questions.** Scored from the facade traces with the frozen
runner's arithmetic. C2's trace reproduces its native report exactly (all@10 0.754, any@1 0.814).

| | A `1df28f84` | C2 | Slice 1 |
|---|---:|---:|---:|
| recall_any@1 | 0.809 | 0.814 | **0.831** |
| recall_all@5 | 0.823 | 0.747 | **0.842** |
| recall_all@10 | 0.893 | 0.754 | 0.871 |
| multi-session recall_all@10 | 0.827 | 0.595 | 0.777 |
| temporal-reasoning recall_all@10 | 0.895 | 0.693 | 0.874 |
| knowledge-update recall_all@10 | 0.987 | 0.903 | 0.972 |
| Mean sessions returned | 45.1 | 3.0 | 4.3 |
| Abstention questions: mean returned | 45.3 | 3.0 | 5.1 |

Paired on all@10:
- slice 1 vs C2: 50 fixed, 1 broken;
- slice 1 vs A: 5 fixed, 14 broken (at all@5, 15 fixed and 7 broken).

The one question broken against C2 is "What was my previous occupation?". Its gold session shares
only the frame word "previous"; the session never uses "occupation", so this is a low-overlap
case.

**AMB PrecisionMemBench, 77 cases** (native scorer, scratch run):

| | C2 | Slice 1 |
|---|---:|---:|
| Strict success | 39/77 | 39/77 (0 fixed, 0 broken) |
| Precision | 0.541 | 0.530 |
| Recall | 0.878 | 0.908 |

The six-entity case now returns all six expected beliefs plus one user-universal belief. That
extra belief is out of scope for the case, and the AMB bridge cannot convey scope (see slice 3).

## Cost

One extra BM25 pass per named entity over the admitted set, plus a linear scan of the query.
There is no new storage. Recall p50 on LongMemEval-S is unchanged within noise (selection is
O(admitted × entities)).

## Remaining after slice 1

- Zero-overlap evidence needs semantic matching (slice 2).
- Morphology and typos: "weddings" does not match "wedding" (slice 2).
- The cue lists are English-only.
- Set cues inside long rambling queries over-trigger ("in the last review" reads as relational).
