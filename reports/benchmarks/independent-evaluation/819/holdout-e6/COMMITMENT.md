# #819 hidden holdout e6 (evaluator cohort 6): pre-candidate commitment

This file is committed **before** any new #819 candidate is fetched, checked out, run, or its freeze record, preregistration, branch, diagnosis or engineering transcript is read. That covers the C9 discovery candidate, the C9 selection candidate and the C9 instrumentation branch. The commit that carries this file fixes the registration time.

- **Author:** the independent evaluation session `session_01RuygyrbhEukaiUBS75n8yt` (lane 4 of the 2026-10-17 five-session plan). It takes no part in any candidate's design or implementation.
- **Refs present locally at sealing (2026-10-17T17:34Z):** `main`, this branch, and the evaluator lane `claude/blissful-thompson-s17ck8` @ `f34d1e9`. Besides these, only the already-evaluated C4 `bc2be631` and C6 `171e67db` were fetched, by exact SHA. No candidate branch was listed or fetched.
- **e6 is newly authored:**
  - It reuses no case from v1–v3, e4 or e5, from the evaluator probes disclosed with the C6 and C8 reviews, or from any developer fixture. This author never saw e4 or e5 content.
  - Engineering's sealed v4 stays reserved and unopened.
  - Generic filler sentences and fresh vocabulary are used throughout.

## Hashes

| File | SHA-256 |
| --- | --- |
| `generate.py` (deterministic generator) | `3f18fa8ae72e786e039b3d09fb78a9543ae1b41021ff46d52bfe07a9feae8d45` |
| `harness.py` (new e6 scorer, public facade only) | `db8399241ecd49df0af1f4d731c392b19b2f1646885ee1a574ad8902b2b14729` |
| `cases.json` (288 cases) | `6481001d33872fbb632e793b474bbe33ee647ee42e3ba6a70d7fb98ae31ebff9` |
| `e6_analyze.py` (preregistered paired analysis) | `2fbc748c9f274f5a41b56cada34b56a6bda0ee98a68ee6f0e016595206ddc2ad` |

## Public shape

- **Size and store setup:**
  - 288 scenarios, one query each, 16 per category, 18 categories.
  - Each scenario gets a fresh store with 4–8 unrelated fillers. Fillers share no content stem with the scenario.
  - Every query runs `recall(budget=5)` through `AgentMemory` only.
- **Category families.** The exact case wording stays sealed.
  - **Answer reach** (5 categories): paraphrased evidence with zero content-stem overlap, sparse and distractor-dense multi-evidence, two-hop bridges whose answer fact shares no stem with the query, and enumeration of four items.
  - **Precision** (3 categories): lexical look-alikes, a near-miss beside the answer (order-constrained), and question-shaped notes beside the answer (order-constrained).
  - **Abstention** (2 categories): near-miss only, and absent topic. The correct return is empty.
  - **Lifecycle, temporal and isolation safety** (8 categories): governed state change with a current query; error correction; forgotten (tombstoned) memory, both as the sole match and beside a valid sibling; disputed memory, in the same two forms; another project scope, both beside an in-scope answer and as the only match; two unreconciled statements with `observed_at`, where the newer must rank first, written in mixed order; as-of recall, where the earlier state is needed and the later successor is excluded, given by explicit intent and by query language; and longitudinal multi-session use (close and reopen, a governed state change in a later session, an addition in a third session).
- **Governed operations.** Corrections and disputes carry procedural-skill verification evidence, following the repository's own facade-test convention. Without it they park at `require_review`.
- **Integrity dry run.** One run on C4 default checked construction only: 288/288 executed, 0 operation failures, 0 errors, and every labelled memory was written. Its scores were **not** inspected. After the dry run one sentence was reworded, so that an excluded term is not a substring of its replacement. The output was then deleted.

## Scoring (identical for every arm)

- **Strict pass:**
  - every needed memory is returned;
  - no excluded memory is returned and no excluded term is quoted;
  - nothing outside the needed and allowed sets is returned;
  - the order constraints hold among the returned items.
- **Per query:**
  - selected-evidence recall at budget 5;
  - discovery (needed memories among the candidates) and admission (needed memories among the admitted);
  - depth recall@{1, 3, 5, 10} over the ranked admitted list.
- **Loss stage** for each needed memory: `not_discovered`, `refused:<reason>`, `withheld_in_top_k` (admitted in the top 5 but not returned), `admitted_below_budget`, or `returned`.
- **Also recorded:**
  - false-positive inclusion (any extra returned);
  - correct abstention (no-answer queries) and false abstention (answer queries);
  - leaks (excluded memories returned or quoted);
  - order violations, recall latency and return-policy identity.

Records are text-free (labels only).

## Persistence and disclosure

- **Where the content lives.** The cohort lives only on this evaluator's container, outside the repository.
  - It is disclosed after the final verdict for the candidates registered in `PREREGISTRATION.md`, at which point e6 is spent.
  - If the container is reclaimed first, the commitment cannot be opened, and e6 is void rather than reused.
- **What is published before the verdict:** no per-case or per-category e6 result, for any arm, baselines included. Only execution receipts and result-file hashes are published.
