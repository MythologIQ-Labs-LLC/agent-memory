| Metric | Before | After | After - before (95% paired bootstrap CI) |
|---|---:|---:|---|
| Strict case success | 15/77 | 39/77 | +0.3117 [+0.2078, +0.4156] |
| Mean precision | 0.1806 | 0.5407 | +0.3601 [+0.2663, +0.4568] |
| Mean recall | 0.9535 | 0.8782 | -0.0753 [-0.1485, -0.0163] |
| Mean documents returned | 8.922 | 1.377 | |

Paired: **24 fixed, 0 broken**; exact McNemar p = 1.19e-07.

| Category | Cases | Before | After |
|---|---:|---:|---:|
| Alias resolution | 23 | 3 | 14 |
| Budget eviction and capacity | 5 | 3 | 5 |
| Cold start behavior | 1 | 1 | 1 |
| Counter-signal retrieval | 2 | 0 | 0 |
| Cross-user isolation | 1 | 1 | 1 |
| Design boundary cases | 6 | 2 | 3 |
| Fuzzy matching and prefix guards | 7 | 3 | 5 |
| Persona prelude content | 4 | 1 | 3 |
| Ranking stability | 3 | 1 | 3 |
| Relation expansion | 4 | 0 | 1 |
| Scope disambiguation | 12 | 0 | 3 |
| Supersession chain exclusion | 3 | 0 | 0 |
| Type routing and open questions | 6 | 0 | 0 |

Fixed: `alias-base-class-retrieves-composition`, `alias-dlq-abbreviation-resolves`, `alias-exceptions-retrieves-error-handling`, `alias-mongo-resolves`, `alias-pov-shift-resolves`, `alias-protagonist-resolves`, `alias-ts-resolves`, `alias-two-word-shingle-dead-letter`, `canonical-name-match-mara`, `fuzzy-single-edit-fires-non-pinned`, `messy-filler-heavy-extraction`, `messy-negation-surfaces-topic`, `messy-typo-blind-spot`, `multi-scope-prelude-uses-primary-scope-only`, `out-of-scope-coin-collecting`, `preference-flood-relevant-entity-survives`, `ranking-canonical-name-over-content`, `ranking-orderedbefore-alias-beats-content`, `relation-expansion-respects-scope-filter`, `score-boundary-weak-match-filtered`, `universal-scope-belief-content-in-persona-prelude`, `universal-scope-explicit-query-no-relevant`, `user-edited-cross-scope-surfaces`, `zero-reinforcement-fresh-belief-surfaces`

Broken: none
