# #774 follow-on: wrong-subject anchor guard and automatic predecessor routing

| | |
|---|---|
| Implementation | `implementation/774-anchor-guard-and-routing-no-ci`, from `ce1fdfc` (isolated from #773, #775 and #776). Tests `5d01df4` → guard + router `69b89b8` → test `3694707` → routing 0.2.0 `a6745a9`. |
| Measurement | `measure_774b.py` with the adopted evaluator `9961067` (v3, separated provenance), instant `2026-10-12T12:00:00Z` |
| New control corpus | **Fenmoor v1**, frozen at `de1eda5` before any execution. It contains paraphrased predecessor questions with no cue, a decoy "before", wrong-subject questions, origin/why/event/current questions, and deleted and other-project controls. |
| Verdict | **CHANGES REQUIRED (improved).** The guard is safe at no measured cost. Routing 0.2.0 never lowered answer@1 or critical coverage against v7 on any corpus, and removed every P0 exposure. Its rule was revised once after an observed failure, so it needs a blind holdout before promotion. Wrong-subject anchoring *inside* the budget remains. |

## What changed (runtime, opt-in only; default recall is byte-identical to v7 on all four corpora)

1. **Anchor guard.**
   - An automatic anchor must already be inside the served budget (`ranked[:budget]`).
   - An unrelated lineage ranked below the budget can no longer be promoted over the answer.
   - A declared `successor_ref` is not gated, so the explicit behaviour is preserved.
2. **`predecessor_routing(query)`.**
   - It uses only the frozen temporal-cue interpreter's evidence (ADR-039 lexicon); **no new keyword, frequency or capitalization rule.**
   - **Routes on** a predecessor-relation cue (`before`, `previously`, `used to`, `formerly`, `prior to`, `earlier`).
   - **Never routes** when an origin cue (`originally`, `initially`, `at first`, `first time`) or a prospective cue co-occurs.
   - Declined (quoted or metalinguistic) spans never route.
3. **`routed_historical_context(query, ctx, budget, temporal_intent)`.**
   - Routed questions use the governed selector; all others are served exactly as `multi_route_recall`.
   - **Policy 0.2.0:** only questions the caller sends with *historical* intent are routed.

## Results (P0 prohibited/stale · answer@1 · all-critical)

| Corpus | v7 composed | #774 `ce1fdfc` declared | head declared | **head auto (0.2.0)** | `ce1fdfc` over-routed | **head over-routed** |
|---|---|---|---|---|---|---|
| Halcyon v1.1 | 0/0 · 13/21 · 19/21 | 0/0 · 15 · 19 | 0/0 · 15 · 19 | **0/0 · 15 · 19** | 0/0 · 15 · 19 | 0/0 · 15 · 19 |
| Cedarline v1.1 | 0/0 · 14/20 · 14/20 | 0/0 · 16 · 16 | 0/0 · 16 · 16 | **0/0 · 16 · 16** | 0/0 · **13** · 16 | 0/0 · **14** · 16 |
| Brightwater v1 | **1**/0 · 4/10 · 8/10 | 0/0 · 8 · 9 | 0/0 · 8 · 9 | **0/0 · 7 · 8** | 0/0 · 7 · 9 | 0/0 · 8 · 9 |
| Fenmoor v1 (new) | **2**/0 · 9/12 · 12/12 | 0/0 · 12 · 12 | 0/0 · 12 · 12 | **0/0 · 11 · 12** | 0/0 · 9 · 12 | 0/0 · 9 · 12 |

- **The guard costs nothing where routing is declared.** B04 keeps its gain: its anchor is at rank 2, inside the budget.
- **It reduces over-routing harm.** Cedarline over-routed is no longer below baseline (13 → 14). The rank-4 fall-through anchors on B06, B07 and C13 are gone.
- **Automatic routing's misses are all paraphrases with no cue:** B03 ("preceded the one in use now"), F04 ("was replaced by"), F05 ("came right ahead of"), and C15 (no cue, but already rank 1).
- **There are no harmful false positives at 0.2.0.** The decoy F08 ("before first use", *timeless*) is no longer routed.
- **Fenmoor's v7 P0s (F02, F11)** are the pre-existing #776 deleted-history leak: v7 serves the deleted `chute-n`. They are withheld on the routed paths, and by the #776 repair on every path.

## Routing 0.1.0 → 0.2.0 (disclosed post-hoc revision)

0.1.0 routed on the cue alone (`results-774b-routing-v0.1.0-at-69b89b8.json`):
- **Halcyon H08** is a *current* question: "How long before a card authorization request times out?". It was routed, served the superseded `authz-8s` first, and produced **P0 stale exposure 0/1**.
- **Fenmoor F08**, a timeless decoy, was routed and promoted an unrelated `wifi-guest`.

0.2.0 applies the stale-exposure invariant: a current, timeless or unspecified question is never routed. The failing test came first (`test_only_caller_historical_questions_are_routed`). This rule was chosen *after* observing H08 and F08 on these corpora, so all four are now seen data. **A blind holdout authored by someone else is required before any promotion.**

## Remaining limitations

1. **Wrong-subject anchoring inside the budget is not solved structurally.**
   - B11, F11 and F12 (no-safe-answer questions about a deleted or other-project memory) still promote an unrelated in-budget predecessor (`pumps-3`, `fine-20`).
   - Nothing prohibited is served, but the context is noise.
   - Separating these needs governed subject identity. See #775: caller-declared typed subject scope.
2. **The predecessor of an older version (B12) is still unanswered.** It needs a declared successor or an as-of instant.
3. **Recall on paraphrases is limited by the frozen lexicon.** Answer@1 lost to router misses versus declared routing: Brightwater 1, Fenmoor 1.
4. **Merge conflicts:**
   - With #776: `memory_deleted`/`lineage_head` use memory-level tombstones and must adopt lineage semantics before combining.
   - With #773: shares `runtime_composition.py`.
   - No successor declaration exists. Full suite at `a6745a9`: 2733 run, the same 5 expected failures (4 freeze guards plus durability `adapter_eof`) and the pre-existing expected failure.
