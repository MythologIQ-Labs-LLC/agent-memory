# #819 hidden holdout e5 (evaluator cohort 5): pre-candidate commitment, for C8 onwards

This file is committed **before** C8 (`24d4dd26`) is fetched, checked out or run, and before any of C8's freeze record, development evidence, diagnosis or engineering transcript is read. The commit that carries it fixes the registration time.

- **Author:** the independent evaluation session `session_011h1ADQyj3ZTu9UHgBAhocF`. It took no part in C8.
- **e5 is not a copy of an earlier cohort:**
  - e4 is spent and was never seen by this author.
  - The evaluator probes disclosed with the C6 review are development-visible and are not reused.
  - None of the developer's fixtures are used.
  - Engineering's sealed v4 stays reserved and unopened.

## Hashes

| File | SHA-256 |
| --- | --- |
| `generate.py` | `809ca7223cb420f877c5627cba3785cb98c0c8ddc3aabd0263f1a52e99bf58f2` |
| `harness.py` (new e5 scorer; not the v1–e4 scorer) | `e69db42ebf4f955069934f7aa062f615370ece9f50cd20658df51adc9ccdc6d6` |
| `cases.json` | `c7dc488abdfc399ad57d1489082c9b2216c6e41577e5cca9722c77c051682c14` |

## Public shape

- **Size:** 208 scenarios, one query each, 16 per category. Each scenario has a fresh store with 4–8 unrelated fillers. Queries use `recall(budget=5)` through the public facade.
- **Categories:**
  - multi-evidence, sparse;
  - multi-evidence with topical distractors;
  - rank depth (one answer among lexical look-alikes);
  - paraphrase;
  - temporal current state (governed state change);
  - temporal ordering (two unreconciled statements, newer must rank first);
  - temporal as-of (the earlier state must be returned and ranked first);
  - question-shaped memory interference;
  - near-miss with no answer (must abstain);
  - near-miss beside the answer (the answer must outrank it);
  - fusion boundary (partial lexical and moderate semantic match, with lexical decoys);
  - cross-scope exclusion;
  - forgotten, disputed and error-corrected memories.
- **Scoring:**
  - **Strict pass:** every needed memory is returned, nothing excluded is returned, nothing outside the needed and allowed sets is returned, and the order constraints hold among returned items.
  - **Also reported:** needed recall at the budget, depth recall@{1, 3, 5, 10} over the full ranked admitted list, precision, extras, excluded memories returned or quoted, order violations, route provenance and latency.
- **Configuration:** facade options such as `semantic_retrieval` are passed explicitly to `AgentMemory.open` by command-line flag. The scorer is identical for every arm.

## Integrity dry run

One dry run on baseline A (`7c06468a`) checked case construction only. It found 0 operation failures and 0 evaluation failures. No case was changed afterwards.

## Planned arms (fixed before C8 is examined)

- C4 `bc2be631`, default;
- C4 with `semantic_retrieval="required"` (the essential comparator, because C6's verdict is CHANGES REQUIRED);
- C6 `171e67db` with `semantic_retrieval="required"`;
- C8 `24d4dd26` with its applicable semantic configuration, as its freeze record states;
- C8 with the route off, for an equivalence check against its declared default lineage.

The pinned model is `multi-qa-MiniLM-L6-cos-v1@b207367`, config digest `sha256:74477054…`, unless C8's freeze record declares otherwise. Paired comparisons use exact McNemar on strict pass and bootstrap 95% CIs (10,000 resamples, seed 819).

## Content

The cohort content stays private until its results are published. After publication, e5 is spent.
