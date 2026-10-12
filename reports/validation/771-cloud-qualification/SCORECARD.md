# #771 served-memory scorecard (generated)

Runtime revision measured: `b2c266c114cb5a9ffe3ffe59e19a8aa7905d3324` (runtime files identical to candidate `23321e4`).
No composite score. P0–P2 are independent; P3 is in its own section.

## halcyon-holdout

Inputs `reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-input.json`, gold `reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json`.

| Dimension | composed-multiroute | governed-lexical |
|---|---|---|
| P0 cases with prohibited exposure | 0 | 0 |
| P0 cases with stale exposure | 1 | 2 |
| P1 answerable / no-safe-answer cases | 21 / 3 | 21 / 3 |
| P1 answer (critical evidence) at rank 1 | 0.571 | 0.476 |
| P1 strong evidence (grade>=2) at rank 1 | 0.762 | 0.571 |
| P1 all critical evidence groups covered | 0.762 | 0.714 |
| P1 empty context on answerable | 0 | 0 |
| P1 no-safe-answer: empty / with context (items) | 0 / 3 (9) | 0 / 3 (9) |
| P1 answer abstention | not_measured_without_answering_layer | not_measured_without_answering_layer |
| P2 macro precision @budget | 0.381 | 0.357 |
| P2 macro recall @budget | 0.810 | 0.738 |
| P2 macro nDCG @budget | 0.732 | 0.656 |
| P2 macro critical coverage | 0.762 | 0.714 |
| P2 distractors served (total) | 40 | 38 |

### halcyon-holdout — composed-multiroute: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01 | changing-fact-current | current | 3 | bus, migration-rule, pgver-16 | ✗ | 1/1 | – | – | 2 | – | 0/5 |
| H02 | changing-fact-history | historical | 3 | pgver-16, adr-db-v2, migration-rule | support | 0/1 | – | – | 2 | – | 0/5 |
| H03 | decision-why-history | historical | 3 | oncall-lrt, room, inc-2207 | ✗ | 0/1 | – | – | 3 | – | 0/5 |
| H04 | decision-why-history | historical | 3 | bookclub, fx-fetch, fx-why | ✗ | 0/1 | – | – | 3 | adr-db-v2 | 0/5 |
| H05 | decision-why | timeless | 3 | bus-why, bus, bookclub | answer | 1/1 | – | – | 1 | – | 0/5 |
| H06 | changing-fact-current | current | 2 | oncall-lrt, deploy-days | answer | 1/1 | – | – | 1 | – | 0/5 |
| H07 | unreliable-source | current | 3 | ratelimit, ratelimit-rumor, oncall-lrt | answer | 1/1 | – | – | 1 | – | 0/5 |
| H08 | correction-current | current | 2 | authz-5s, migration-rule | answer | 1/1 | – | – | 1 | – | 0/5 |
| H09 | expired-window | current | 3 | deploy-days, region-eu-us, freeze-bf25 | answer | 1/1 | freeze-bf25 | – | 1 | – | 0/5 |
| H10 | multi-fact-why | timeless | 3 | inc-2207, migration-rule, region-draft | answer | 2/2 | – | – | 1 | – | 0/5 |
| H11 | single-fact | timeless | 2 | money-repr, bus | answer | 1/1 | – | – | 1 | – | 0/5 |
| H12 | decision-why | timeless | 3 | fx-fetch, fx-why, money-repr | support | 1/1 | – | – | 1 | – | 0/5 |
| H13 | changing-fact-current | current | 3 | region-eu-us, bus, migration-rule | answer | 1/1 | – | – | 2 | – | 0/5 |
| H14 | correction-history | historical | 3 | region-eu-us, region-draft, migration-rule | support | 0/1 | – | – | 2 | – | 0/5 |
| H15 | paraphrase | timeless | 2 | pci, authz-5s | answer | 1/1 | – | – | 1 | – | 0/5 |
| H16 | single-fact | timeless | 2 | webhook-retry, pci | answer | 1/1 | – | – | 1 | – | 0/5 |
| H17 | no-answer | current | 3 | oncall-lrt, bookclub, room | n/a (no safe answer) | 0/0 | – | – | 3 | – | 0/5 |
| H18 | no-answer-deleted | current | 3 | ratelimit, ratelimit-rumor, bookclub | n/a (no safe answer) | 0/0 | – | – | 3 | – | 0/5 |
| H19 | no-answer-cross-project | current | 3 | oncall-lrt, bookclub, room | n/a (no safe answer) | 0/0 | – | – | 2 | – | 0/5 |
| H20 | multi-fact-current | current | 4 | fx-why, ratelimit-rumor, fx-fetch, inc-2207 | ✗ | 0/3 | – | – | 3 | money-repr, authz-5s, ratelimit | 0/5 |
| H21 | unseen-terminology | timeless | 3 | bus, region-draft, ratelimit-rumor | answer | 1/1 | – | – | 2 | – | 0/5 |
| H22 | contradiction | current | 3 | ratelimit-rumor, ratelimit, fx-why | ✗ | 1/1 | – | – | 1 | – | 0/5 |
| H23 | decision-why | timeless | 3 | migration-rule, inc-2207, bookclub | support | 1/1 | – | – | 1 | – | 0/5 |
| H24 | distractor-domain | timeless | 2 | room, bookclub | answer | 1/1 | – | – | 1 | – | 0/5 |

P3 (engineering only): governed build + 24 queries in 0.337 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

### halcyon-holdout — governed-lexical: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01 | changing-fact-current | current | 3 | adr-db-v2, pgver-16, inc-2207 | ✗ | 1/1 | – | – | 1 | – | 5/5 |
| H02 | changing-fact-history | historical | 3 | adr-db-v2, pgver-16, migration-rule | ✗ | 0/1 | – | – | 2 | – | 5/5 |
| H03 | decision-why-history | historical | 3 | oncall-lrt, inc-2207, room | ✗ | 0/1 | – | – | 3 | – | 4/5 |
| H04 | decision-why-history | historical | 3 | fx-fetch, fx-why, adr-db-v2 | ✗ | 1/1 | – | – | 2 | – | 5/5 |
| H05 | decision-why | timeless | 3 | bus-why, bus, fx-why | answer | 1/1 | – | – | 1 | – | 0/5 |
| H06 | changing-fact-current | current | 2 | oncall-lrt, ratelimit | answer | 1/1 | – | – | 1 | – | 5/5 |
| H07 | unreliable-source | current | 3 | ratelimit, ratelimit-rumor, oncall-lrt | answer | 1/1 | – | – | 1 | – | 5/5 |
| H08 | correction-current | current | 2 | authz-5s, migration-rule | answer | 1/1 | – | – | 1 | – | 0/5 |
| H09 | expired-window | current | 3 | adr-db-v2, freeze-bf25, region-eu-us | ✗ | 0/1 | freeze-bf25 | – | 2 | deploy-days | 5/5 |
| H10 | multi-fact-why | timeless | 3 | inc-2207, migration-rule, adr-db-v2 | answer | 2/2 | – | – | 1 | – | 0/5 |
| H11 | single-fact | timeless | 2 | adr-db-v2, inc-2207 | ✗ | 0/1 | – | – | 2 | money-repr | 4/5 |
| H12 | decision-why | timeless | 3 | fx-fetch, fx-why, freeze-bf25 | support | 1/1 | – | – | 1 | – | 5/5 |
| H13 | changing-fact-current | current | 3 | region-eu-us, bus, oncall-lrt | answer | 1/1 | – | – | 2 | – | 5/5 |
| H14 | correction-history | historical | 3 | region-eu-us, adr-db-v2, oncall-lrt | support | 0/1 | – | – | 2 | – | 5/5 |
| H15 | paraphrase | timeless | 2 | pci, adr-db-v2 | answer | 1/1 | – | – | 1 | – | 4/5 |
| H16 | single-fact | timeless | 2 | webhook-retry, bus-why | answer | 1/1 | – | – | 1 | – | 4/5 |
| H17 | no-answer | current | 3 | oncall-lrt, ratelimit, ratelimit-rumor | n/a (no safe answer) | 0/0 | – | – | 3 | – | 5/5 |
| H18 | no-answer-deleted | current | 3 | oncall-lrt, ratelimit, ratelimit-rumor | n/a (no safe answer) | 0/0 | – | – | 3 | – | 5/5 |
| H19 | no-answer-cross-project | current | 3 | oncall-lrt, adr-db-v2, pgver-16 | n/a (no safe answer) | 0/0 | – | – | 2 | – | 5/5 |
| H20 | multi-fact-current | current | 4 | inc-2207, fx-fetch, ratelimit-rumor, freeze-bf25 | ✗ | 0/3 | freeze-bf25 | – | 2 | ratelimit, authz-5s, money-repr | 5/5 |
| H21 | unseen-terminology | timeless | 3 | adr-db-v2, bus, bus-why | ✗ | 1/1 | – | – | 1 | – | 5/5 |
| H22 | contradiction | current | 3 | ratelimit-rumor, ratelimit, oncall-lrt | ✗ | 1/1 | – | – | 1 | – | 0/5 |
| H23 | decision-why | timeless | 3 | inc-2207, migration-rule, adr-db-v2 | answer | 1/1 | – | – | 1 | – | 4/5 |
| H24 | distractor-domain | timeless | 2 | room, oncall-lrt | answer | 1/1 | – | – | 1 | – | 2/5 |

P3 (engineering only): governed build + 24 queries in 0.276 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

## halcyon-holdout-v1.1

Inputs `reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1.1-input.json`, gold `reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json`.

| Dimension | composed-multiroute | governed-lexical |
|---|---|---|
| P0 cases with prohibited exposure | 0 | 0 |
| P0 cases with stale exposure | 1 | 2 |
| P1 answerable / no-safe-answer cases | 21 / 3 | 21 / 3 |
| P1 answer (critical evidence) at rank 1 | 0.619 | 0.476 |
| P1 strong evidence (grade>=2) at rank 1 | 0.810 | 0.571 |
| P1 all critical evidence groups covered | 0.905 | 0.714 |
| P1 empty context on answerable | 0 | 0 |
| P1 no-safe-answer: empty / with context (items) | 0 / 3 (9) | 0 / 3 (9) |
| P1 answer abstention | not_measured_without_answering_layer | not_measured_without_answering_layer |
| P2 macro precision @budget | 0.444 | 0.357 |
| P2 macro recall @budget | 0.905 | 0.738 |
| P2 macro nDCG @budget | 0.826 | 0.656 |
| P2 macro critical coverage | 0.905 | 0.714 |
| P2 distractors served (total) | 36 | 38 |

### halcyon-holdout-v1.1 — composed-multiroute: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01 | changing-fact-current | current | 3 | bus, migration-rule, pgver-16 | ✗ | 1/1 | – | – | 2 | – | 0/5 |
| H02 | changing-fact-history | historical | 3 | pgver-16, pgver-15, adr-db-v2 | support | 1/1 | – | – | 1 | – | 3/5 |
| H03 | decision-why-history | historical | 3 | adr-db-v1, oncall-lrt, oncall-platform | answer | 1/1 | – | – | 2 | – | 0/5 |
| H04 | decision-why-history | historical | 3 | bookclub, adr-db-v1, fx-fetch | ✗ | 0/1 | – | – | 2 | adr-db-v2 | 0/5 |
| H05 | decision-why | timeless | 3 | bus-why, bus, bookclub | answer | 1/1 | – | – | 1 | – | 0/5 |
| H06 | changing-fact-current | current | 2 | oncall-lrt, deploy-days | answer | 1/1 | – | – | 1 | – | 0/5 |
| H07 | unreliable-source | current | 3 | ratelimit, ratelimit-rumor, oncall-lrt | answer | 1/1 | – | – | 1 | – | 0/5 |
| H08 | correction-current | current | 2 | authz-5s, migration-rule | answer | 1/1 | – | – | 1 | – | 0/5 |
| H09 | expired-window | current | 3 | deploy-days, region-eu-us, freeze-bf25 | answer | 1/1 | freeze-bf25 | – | 1 | – | 0/5 |
| H10 | multi-fact-why | timeless | 3 | inc-2207, migration-rule, region-draft | answer | 2/2 | – | – | 1 | – | 0/5 |
| H11 | single-fact | timeless | 2 | money-repr, bus | answer | 1/1 | – | – | 1 | – | 0/5 |
| H12 | decision-why | timeless | 3 | fx-fetch, fx-why, money-repr | support | 1/1 | – | – | 1 | – | 0/5 |
| H13 | changing-fact-current | current | 3 | region-eu-us, bus, migration-rule | answer | 1/1 | – | – | 2 | – | 0/5 |
| H14 | correction-history | historical | 3 | region-eu-us, region-eu, region-draft | support | 1/1 | – | – | 1 | – | 0/5 |
| H15 | paraphrase | timeless | 2 | pci, authz-5s | answer | 1/1 | – | – | 1 | – | 0/5 |
| H16 | single-fact | timeless | 2 | webhook-retry, pci | answer | 1/1 | – | – | 1 | – | 0/5 |
| H17 | no-answer | current | 3 | oncall-lrt, bookclub, room | n/a (no safe answer) | 0/0 | – | – | 3 | – | 0/5 |
| H18 | no-answer-deleted | current | 3 | ratelimit, ratelimit-rumor, bookclub | n/a (no safe answer) | 0/0 | – | – | 3 | – | 0/5 |
| H19 | no-answer-cross-project | current | 3 | oncall-lrt, bookclub, room | n/a (no safe answer) | 0/0 | – | – | 2 | – | 0/5 |
| H20 | multi-fact-current | current | 4 | fx-why, ratelimit-rumor, fx-fetch, inc-2207 | ✗ | 0/3 | – | – | 3 | money-repr, authz-5s, ratelimit | 0/5 |
| H21 | unseen-terminology | timeless | 3 | bus, region-draft, ratelimit-rumor | answer | 1/1 | – | – | 2 | – | 0/5 |
| H22 | contradiction | current | 3 | ratelimit-rumor, ratelimit, fx-why | ✗ | 1/1 | – | – | 1 | – | 0/5 |
| H23 | decision-why | timeless | 3 | migration-rule, inc-2207, bookclub | support | 1/1 | – | – | 1 | – | 0/5 |
| H24 | distractor-domain | timeless | 2 | room, bookclub | answer | 1/1 | – | – | 1 | – | 0/5 |

P3 (engineering only): governed build + 24 queries in 0.271 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

### halcyon-holdout-v1.1 — governed-lexical: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01 | changing-fact-current | current | 3 | adr-db-v2, pgver-16, inc-2207 | ✗ | 1/1 | – | – | 1 | – | 5/5 |
| H02 | changing-fact-history | historical | 3 | adr-db-v2, pgver-16, migration-rule | ✗ | 0/1 | – | – | 2 | – | 5/5 |
| H03 | decision-why-history | historical | 3 | oncall-lrt, inc-2207, room | ✗ | 0/1 | – | – | 3 | – | 4/5 |
| H04 | decision-why-history | historical | 3 | fx-fetch, fx-why, adr-db-v2 | ✗ | 1/1 | – | – | 2 | – | 5/5 |
| H05 | decision-why | timeless | 3 | bus-why, bus, fx-why | answer | 1/1 | – | – | 1 | – | 0/5 |
| H06 | changing-fact-current | current | 2 | oncall-lrt, ratelimit | answer | 1/1 | – | – | 1 | – | 5/5 |
| H07 | unreliable-source | current | 3 | ratelimit, ratelimit-rumor, oncall-lrt | answer | 1/1 | – | – | 1 | – | 5/5 |
| H08 | correction-current | current | 2 | authz-5s, migration-rule | answer | 1/1 | – | – | 1 | – | 0/5 |
| H09 | expired-window | current | 3 | adr-db-v2, freeze-bf25, region-eu-us | ✗ | 0/1 | freeze-bf25 | – | 2 | deploy-days | 5/5 |
| H10 | multi-fact-why | timeless | 3 | inc-2207, migration-rule, adr-db-v2 | answer | 2/2 | – | – | 1 | – | 0/5 |
| H11 | single-fact | timeless | 2 | adr-db-v2, inc-2207 | ✗ | 0/1 | – | – | 2 | money-repr | 4/5 |
| H12 | decision-why | timeless | 3 | fx-fetch, fx-why, freeze-bf25 | support | 1/1 | – | – | 1 | – | 5/5 |
| H13 | changing-fact-current | current | 3 | region-eu-us, bus, oncall-lrt | answer | 1/1 | – | – | 2 | – | 5/5 |
| H14 | correction-history | historical | 3 | region-eu-us, adr-db-v2, oncall-lrt | support | 0/1 | – | – | 2 | – | 5/5 |
| H15 | paraphrase | timeless | 2 | pci, adr-db-v2 | answer | 1/1 | – | – | 1 | – | 4/5 |
| H16 | single-fact | timeless | 2 | webhook-retry, bus-why | answer | 1/1 | – | – | 1 | – | 4/5 |
| H17 | no-answer | current | 3 | oncall-lrt, ratelimit, ratelimit-rumor | n/a (no safe answer) | 0/0 | – | – | 3 | – | 5/5 |
| H18 | no-answer-deleted | current | 3 | oncall-lrt, ratelimit, ratelimit-rumor | n/a (no safe answer) | 0/0 | – | – | 3 | – | 5/5 |
| H19 | no-answer-cross-project | current | 3 | oncall-lrt, adr-db-v2, pgver-16 | n/a (no safe answer) | 0/0 | – | – | 2 | – | 5/5 |
| H20 | multi-fact-current | current | 4 | inc-2207, fx-fetch, ratelimit-rumor, freeze-bf25 | ✗ | 0/3 | freeze-bf25 | – | 2 | ratelimit, authz-5s, money-repr | 5/5 |
| H21 | unseen-terminology | timeless | 3 | adr-db-v2, bus, bus-why | ✗ | 1/1 | – | – | 1 | – | 5/5 |
| H22 | contradiction | current | 3 | ratelimit-rumor, ratelimit, oncall-lrt | ✗ | 1/1 | – | – | 1 | – | 0/5 |
| H23 | decision-why | timeless | 3 | inc-2207, migration-rule, adr-db-v2 | answer | 1/1 | – | – | 1 | – | 4/5 |
| H24 | distractor-domain | timeless | 2 | room, oncall-lrt | answer | 1/1 | – | – | 1 | – | 2/5 |

P3 (engineering only): governed build + 24 queries in 0.237 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

## v1-integration

Inputs `reference/fixtures/evaluation/served-memory-integration-v1-input.json`, gold `reference/fixtures/evaluation/served-memory-integration-v1-gold.json`.

| Dimension | composed-multiroute | governed-lexical |
|---|---|---|
| P0 cases with prohibited exposure | 0 | 0 |
| P0 cases with stale exposure | 1 | 1 |
| P1 answerable / no-safe-answer cases | 4 / 1 | 4 / 1 |
| P1 answer (critical evidence) at rank 1 | 1.000 | 0.750 |
| P1 strong evidence (grade>=2) at rank 1 | 1.000 | 0.750 |
| P1 all critical evidence groups covered | 1.000 | 1.000 |
| P1 empty context on answerable | 0 | 0 |
| P1 no-safe-answer: empty / with context (items) | 0 / 1 (2) | 0 / 1 (2) |
| P1 answer abstention | not_measured_without_answering_layer | not_measured_without_answering_layer |
| P2 macro precision @budget | 0.500 | 0.500 |
| P2 macro recall @budget | 1.000 | 1.000 |
| P2 macro nDCG @budget | 0.974 | 0.882 |
| P2 macro critical coverage | 1.000 | 1.000 |
| P2 distractors served (total) | 6 | 6 |

### v1-integration — composed-multiroute: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q-current-endpoint |  | current | 3 | endpoint, quota, boreal-quota | answer | 1/1 | – | – | 1 | – | 0/5 |
| Q-compound |  | current | 3 | endpoint, quota, boreal-quota | answer | 2/2 | – | – | 1 | – | 0/5 |
| Q-release-history |  | historical | 3 | release-old, release-current, endpoint | answer | 1/1 | – | – | 1 | – | 0/5 |
| Q-no-owner |  | current | 2 | endpoint, quota | n/a (no safe answer) | 0/0 | – | – | 2 | – | 0/5 |
| Q-release-current |  | current | 3 | release-current, endpoint, release-old | answer | 1/1 | release-old | – | 1 | – | 0/5 |

P3 (engineering only): governed build + 5 queries in 0.068 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

### v1-integration — governed-lexical: per query

| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q-current-endpoint |  | current | 3 | endpoint, quota, release-old | answer | 1/1 | – | – | 1 | – | 4/5 |
| Q-compound |  | current | 3 | endpoint, quota, release-old | answer | 2/2 | – | – | 1 | – | 4/5 |
| Q-release-history |  | historical | 3 | release-old, release-current, endpoint | answer | 1/1 | – | – | 1 | – | 3/5 |
| Q-no-owner |  | current | 2 | release-old, release-current | n/a (no safe answer) | 0/0 | – | – | 2 | – | 5/5 |
| Q-release-current |  | current | 3 | release-old, release-current, endpoint | ✗ | 1/1 | release-old | – | 1 | – | 5/5 |

P3 (engineering only): governed build + 5 queries in 0.067 s on a fresh store. single cold run incl. governed writes; tiny corpora, not a scalability result.

