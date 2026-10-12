# #775 Governed subject identity and caller-declared entity scope (evaluation-only)

| | |
|---|---|
| Branch | `validation/775-governed-subject-scope` (evaluation code only; **no runtime change**) |
| Protocol | **Pass 1** (`34795e1`): a write-time subject per logical memory, declared from memory texts only. **Pass 2** (`11a44c2`): a caller-declared entity scope per question, from question text only, plus paraphrases. Both were frozen before `scope_775.py` ran. Gold was not consulted. |
| Baseline | Unchanged v7 `9b025f9` composed served lists, via the v3 runner of the adopted evaluator `9961067`, instant `2026-10-12T12:00:00Z` |
| Rule | Remove-only, no backfill. An item is withheld **only** if its memory has a declared subject, AND the caller declared a scope, AND the subject is outside that scope. Missing identity on either side means uncertainty, never exclusion. |
| Verdict | **Promising, NOT runtime-ready.** A correct caller scope removes most distractors and no-answer context with few false negatives. But a wrong scope empties answers wholesale, and subject granularity causes real misses. Keep it evaluation-only. No keyword-frequency or capitalization rule is used or proposed. |

## Results (legitimate = grade ≥ 2 and eligible; a lost legitimate item is a FALSE NEGATIVE)

| Corpus | Variant | Irrelevant/unsafe withheld | **Legit lost** | Critical lost | answer@1 | No-answer items | Emptied, no-answer (`no_qualified_evidence`) |
|---|---|---|---|---|---|---|---|
| Northgate | **E1 caller scope** | 12 | **0** | – | 8→9/11 | 10→2 | N06, N07, N13 |
| | E1-wrong (control) | 18 | **8** | 8 cases | 8→**2** | 10→2 | – (9 answerable emptied) |
| | E1-half identity | 3 | 0 | – | 8→8 | 10→8 | – |
| | E2 lexical resolver | 11 | 0 | – | 8→9 | 10→2 | N06, N07, N13 |
| Halcyon v1.1 | **E1** | 34 | **2** (H10, H23: `inc-2207`) | H10, H23 | 13→14/21 | **9→0** | H17, H18, H19 |
| | E1-wrong | 34 | 24 | 18 cases | 13→**1** | 9→1 | – |
| | E1-half | 18 | 0 | – | 13→14 | 9→6 | – |
| | E2 | 9 | 0 | – | 13→13 | 9→3 | H18, H19 |
| Cedarline v1.1 | **E1** | 29 | **1** (C09: `uplink-512`, not critical) | – | 14→14/20 | **8→0** | C11, C21, C22, C23 |
| | E1-wrong | 33 | 25 | 14 cases | 14→**1** | 8→0 | – |
| | E1-half | 12 | 0 | – | 14→14 | 8→5 | C21 |
| | E2 | 10 | 0 | – | 14→14 | 8→8 | – |
| Brightwater v1 | **E1** | 11 | **0** | – | 4→5/10 | 4→4 | – |
| | E1-wrong | 14 | 13 | 8 cases | 4→**0** | 4→0 | – |
| Fenmoor v1 | **E1** | 16 | **0** | – | 9→9/12 | 10→3 | F12 |
| | E1-wrong | 13 | 20 | 12 cases | 9→**0** | 10→1 | – |

Full lists are in `results-775-scope.json`.

## Interpretation

1. **Subject identity separates wrong-subject candidates, which lexical relevance could not.**
   - The first #775 report found that R1 never separated "Hilltop" from "Riverside".
   - Here E1 withholds 12 Northgate distractors with 0 false negatives, and leaves 3 of 5 no-answer questions with no qualified evidence.
   - On Halcyon and Cedarline, no-answer context goes to **0**.
   - It does **not** resolve #774's B11 (the asked budget memory and the served pump chain share the subject "Kessel Road pumping station"). Subject granularity alone cannot express "same station, different attribute".
2. **The false negatives come from granularity, not wording.**
   - Halcyon H10/H23 ask about ledger schema-change process. The critical incident `inc-2207` is declared as subject "incident INC-2207".
   - A cross-subject *relation* (incident → ledger schema changes) is needed, not a broader scope. A governed typed relation should carry that link.
3. **A wrong scope is catastrophic.**
   - Replacing each caller scope with another registry subject removes nearly all answers: 2–25 legitimate items per corpus, and answer@1 falls to 0–2.
   - A runtime version must therefore fail toward uncertainty when the declared scope is not a registered subject, or matches nothing admitted. It must also report the withheld items on a separate, non-answer diagnostic channel.
4. **Missing identity is safe.** With half the memories unlabelled, E1 kept 0 false negatives and retained part of the gain.
5. **A deterministic lexical resolver (exact registry-name match) is safe but weak.**
   - Agreement with the caller scope: Northgate 10/15, Halcyon 6/23, Cedarline 7/23, Brightwater 4/12, Fenmoor 8/16.
   - **Paraphrases defeat it:** 11 of 12 paraphrases were unresolved. The one hit, F01, is not a valid paraphrase, because the reviewer's wording contained the registry name.
   - Scope must come from the caller or from a separately measured entity resolver, never from query wording rules.

## Limitations

- **Not independent:** the reviewer authored both declarations and three of the five corpora. The two-pass freeze limits but does not remove that dependence. An independent annotator and a blind corpus are required.
- **Declarations live in sidecar files:** the v7 runtime and runner do not carry typed subjects. A runtime slice would read `typed_proposition.subject` through admission-gated `write_semantics`. That surface was just found to leak deleted versions (#776), and the repair now governs it.
- **Small corpora:** one or two items are within noise.
