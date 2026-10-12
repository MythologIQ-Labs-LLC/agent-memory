# #774 research: natural-language successor resolution (evaluation-only)

| | |
|---|---|
| Strategies | preregistered at `04e6d6d` **before** the corpus existed (`resolve_774.py`) |
| Blind corpus | mountain rescue team, independent agent author with no repository access (a model, not a human); frozen at `ce35a1a`. 35 questions, 29 predecessor questions (19 unique, 5 ambiguous, 3 no-history, 2 not-visible), with 4 wrong-subject trap pairs and an A→B→A→C chain. |
| Runtime | strict #774 `4088823` (selection 0.2.0); resolved successors are passed as `successor_ref` |
| Verdict | **No NL resolver is promotable. Keep strict caller-targeted retrieval.** |

## Resolution accuracy (29 predecessor questions)
| Strategy | Correct (of 19 unique) | Wrong successor | Asserted on ambiguous/no-history/not-visible (of 10) | Abstained on unique |
|---|---|---|---|---|
| R0 never resolve | 0 | 0 | 0 | 19 |
| R1 legacy implicit (current head of top lineage) | 15 | **4** | **10** | 0 |
| R2 distinctive value mention | 11 | **2** | **4** | 6 |
| R3 R2 plus single-lineage guard | 8 | **2** | **2** | 9 |
| Oracle (gold successor) | 19 | 0 | 0 | 0 |

## Served quality (P0 · answer@1 · all-critical; 25 answerable)
| Strategy | P0 | answer@1 | all-critical |
|---|---|---|---|
| R0 | 0 | 9/25 | 9/25 |
| R1 | 0 | 21/25 | 21/25 |
| R2 | 0 | 19/25 | 19/25 |
| R3 | 0 | 16/25 | 16/25 |
| Oracle | 0 | **25/25** | 25/25 |

## Failures that block promotion
- **Q03 (older value named):** every resolver anchors on the latest version (`heli-v4` instead of `heli-v2`) and **loses rank 1** versus no resolution.
- **Q10 (paraphrased value):** all resolvers pick the latest version (`radio-v5` instead of `radio-v3`).
- **Q21 (deleted memory) and Q29 (other-project memory):** all resolvers attach the question to a *different visible memory* (`pager-v2`, `radio-v5`). That asserts an unrelated predecessor for a subject the reader cannot see. Nothing prohibited is served, but the answer is wrong-subject.
- **Ambiguous questions:** R1 asserts a predecessor on all 10 non-unique questions. Q04 is the repeated value A→B→A, Q12/Q16 have an unnamed subject, and Q26 has a value shared by two memories.

## Conclusion
- **The gap is real:** caller-identified targets give 25/25, unresolved gives 9/25.
- **Lexical resolution is the wrong tool:** every lexical strategy that closes part of the gap also produces wrong or unsupported predecessor assertions.
- **What a resolver would need:** governed subject identity (#775) **and** value-level reference resolution (named older values, paraphrases, repeated values) with an explicit ambiguity output. Each must be measured separately on fresh blind data.
- Until then, only caller-identified successors may promote.
