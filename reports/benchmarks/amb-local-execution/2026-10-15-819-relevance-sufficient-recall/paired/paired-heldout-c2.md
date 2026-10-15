| Metric | Before | After | After - before (95% paired bootstrap CI) |
|---|---:|---:|---|
| Strict case success | 0/70 | 14/70 | +0.2000 [+0.1143, +0.3000] |
| Mean precision | 0.0453 | 0.2744 | +0.2291 [+0.1464, +0.3209] |
| Mean recall | 0.7752 | 0.6376 | -0.1376 [-0.2390, -0.0519] |
| Mean documents returned | 17.971 | 2.986 | |

Paired: **14 fixed, 0 broken**; exact McNemar p = 1.22e-04.

| Category | Cases | Before | After |
|---|---:|---:|---:|
| direct | 2 | 0 | 1 |
| distractor-overlap | 5 | 0 | 0 |
| exploratory | 1 | 0 | 1 |
| general-knowledge | 3 | 0 | 3 |
| isolation | 2 | 0 | 0 |
| multi-belief | 4 | 0 | 0 |
| name-collision | 5 | 0 | 0 |
| negation | 2 | 0 | 0 |
| open-question-only | 3 | 0 | 0 |
| out-of-scope | 6 | 0 | 0 |
| paraphrase | 13 | 0 | 5 |
| pinned-only | 4 | 0 | 1 |
| relation | 3 | 0 | 0 |
| resolved-question | 3 | 0 | 0 |
| supersession | 4 | 0 | 1 |
| terse | 3 | 0 | 0 |
| typo | 2 | 0 | 1 |
| universal | 3 | 0 | 0 |
| unrelated | 2 | 0 | 1 |

Fixed: `fin-airline-card`, `fin-apr-general`, `fin-dentist-hsa`, `fin-expense-ratio-typo`, `fin-food-bank-december`, `hl-early-alarm-superseded`, `hl-hand-bones`, `hl-lab-followup-visit`, `hl-missed-pill`, `home-bathroom-paint`, `home-furnace-leaning`, `home-lukewarm-water`, `home-unrelated-trivia`, `uni-name-pinned`

Broken: none
