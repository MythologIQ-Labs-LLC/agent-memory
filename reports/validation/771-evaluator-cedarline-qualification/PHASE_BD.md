# Phases B and D: Cedarline and Halcyon on the reference runtime, and #773 before/after (generated)

Explicit reference instant for `-T` modes: `2026-10-12T12:00:00Z`. No composite score.

## cedarline-v1.1 (frozen at `32404f7e0c80`)

| Variant (runtime / mode) | runtime blob | P0 prohibited / stale | answer@1 | all critical | no-answer with context (items) | empty on answerable | precision@b | recall@b | nDCG@b | distractors |
|---|---|---|---|---|---|---|---|---|---|---|
| 773-candidate-9c9bf4d/composed-T | `bbf12bf390` | 0 / 0 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 35 |
| 773-candidate-9c9bf4d/composed-default | `bbf12bf390` | 0 / 1 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 34 |
| 773-candidate-9c9bf4d/selector-T | `bbf12bf390` | 0 / 0 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 35 |
| 773-repaired/composed-T | `0d5c5da1f4` | 0 / 0 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 35 |
| 773-repaired/selector-T | `0d5c5da1f4` | 0 / 0 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 35 |
| main-3eebb6d/composed-default | `65a39d5e3d` | 0 / 1 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 34 |
| v7-9b025f9/composed-T | `65a39d5e3d` | 0 / 0 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 35 |
| v7-9b025f9/composed-default | `65a39d5e3d` | 0 / 1 | 0.700 | 0.700 | 4/4 (8) | 0 | 0.475 | 0.767 | 0.765 | 34 |

**Stability** (served rows / full ranked admissions that differ):

- main-3eebb6d/composed-default vs v7-9b025f9/composed-default: served none; ranked none
- v7-9b025f9/composed-T vs 773-candidate-9c9bf4d/composed-T: served none; ranked none
- v7-9b025f9/composed-T vs 773-repaired/composed-T: served none; ranked none
- v7-9b025f9/composed-default vs 773-candidate-9c9bf4d/composed-default: served none; ranked none
- v7-9b025f9/composed-default vs v7-9b025f9/composed-T: served ['C11']; ranked ['C05', 'C06', 'C08', 'C11', 'C14', 'C17', 'C22', 'C23']

### Per question, unchanged reference runtime (v7-9b025f9/composed-default)

| Q | stratum | intent | budget | served | answer@1 | critical | failure categories |
|---|---|---|---|---|---|---|---|
| C01 | current-state | current | 3 | catalog-delta, watermark, owner-integrity | ✓ | 1/1 | – |
| C02 | history | historical | 3 | catalog-delta, why-delta, why-compress | ✗ | 0/1 | historical_target |
| C03 | historical-reason | historical | 3 | catalog-parquet, catalog-csv, why-parquet | ✗ | 1/1 | historical_target, why_target |
| C04 | historical-reason | historical | 3 | catalog-delta, why-delta, watermark | ✗ | 1/1 | historical_target, why_target |
| C05 | error-correction | current | 2 | offset-3mm-correct, heartbeat-10 | ✓ | 1/1 | – |
| C06 | current-state | current | 2 | owner-integrity, priority-new | ✓ | 1/1 | – |
| C07 | history | historical | 3 | owner-integrity, priority-new, retain-3y | ✗ | 0/1 | historical_target |
| C08 | current-state | current | 2 | heartbeat-10, priority-new | ✓ | 1/1 | – |
| C09 | explanation | timeless | 3 | why-compress, uplink-512, incident-208 | ✓ | 1/1 | – |
| C10 | compound-two-facts | timeless | 3 | why-compress, uplink-512, mission-mesa7 | ✓ | 2/2 | – |
| C11 | expired-no-answer | current | 2 | freeze-expired, mission-mesa7 | n/a | 0/0 | stale_exposure, no_answer_context |
| C12 | historical-cause | historical | 3 | incident-root, heartbeat-30, freeze-expired | ✓ | 1/1 | – |
| C13 | compound-incident | historical | 3 | incident-root, mission-mesa7, why-compress | ✓ | 1/2 | multi_fact_incomplete |
| C14 | rumor-vs-record | current | 3 | retain-7y-rumor, retain-3y, heartbeat-10 | ✗ | 1/1 | unconfirmed_first, current_top1_miss |
| C15 | history | historical | 3 | retain-1y, retain-3y, retain-7y-rumor | ✓ | 1/1 | – |
| C16 | single-fact | timeless | 2 | mission-mesa7, field-bookclub | ✓ | 1/1 | – |
| C17 | changing-policy | current | 2 | why-priority, offset-3mm-correct | ✗ | 0/1 | current_top1_miss |
| C18 | historical-reason | historical | 3 | why-priority, priority-new, offset-2mm | ✓ | 1/1 | – |
| C19 | single-fact | timeless | 2 | index-guide, offset-3mm-correct | ✓ | 1/1 | – |
| C20 | compound-why | timeless | 3 | watermark, offset-3mm-correct, why-priority | ✓ | 1/2 | multi_fact_incomplete |
| C21 | unanswerable | current | 2 | retain-3y, owner-integrity | n/a | 0/0 | no_answer_context |
| C22 | deleted-no-answer | current | 2 | offset-3mm-correct, uplink-512 | n/a | 0/0 | no_answer_context |
| C23 | cross-project-no-answer | current | 2 | offset-3mm-correct, why-compress | n/a | 0/0 | no_answer_context |
| C24 | compound-three-facts | current | 3 | offset-3mm-correct, why-compress, retain-7y-rumor | ✓ | 1/3 | multi_fact_incomplete |

### #773 before/after at the same instant (v7 composed-T → #773 selector-T)

| Q | intent | before | after | change | excluded as known-not-current | valid evidence excluded |
|---|---|---|---|---|---|---|
| C01 | current | catalog-delta, watermark, owner-integrity | catalog-delta, watermark, owner-integrity | unchanged | – | – |
| C05 | current | offset-3mm-correct, heartbeat-10 | offset-3mm-correct, heartbeat-10 | unchanged | freeze-expired | – |
| C06 | current | owner-integrity, priority-new | owner-integrity, priority-new | unchanged | freeze-expired | – |
| C08 | current | heartbeat-10, priority-new | heartbeat-10, priority-new | unchanged | freeze-expired | – |
| C11 | current | mission-mesa7, uplink-512 | mission-mesa7, uplink-512 | unchanged | freeze-expired | – |
| C14 | current | retain-7y-rumor, retain-3y, heartbeat-10 | retain-7y-rumor, retain-3y, heartbeat-10 | unchanged | freeze-expired | – |
| C17 | current | why-priority, offset-3mm-correct | why-priority, offset-3mm-correct | unchanged | freeze-expired | – |
| C21 | current | retain-3y, owner-integrity | retain-3y, owner-integrity | unchanged | – | – |
| C22 | current | offset-3mm-correct, uplink-512 | offset-3mm-correct, uplink-512 | unchanged | freeze-expired | – |
| C23 | current | offset-3mm-correct, why-compress | offset-3mm-correct, why-compress | unchanged | freeze-expired | – |
| C24 | current | offset-3mm-correct, why-compress, retain-7y-rumor | offset-3mm-correct, why-compress, retain-7y-rumor | unchanged | – | – |

## halcyon-v1.1 (frozen at `04543a79dbf3`)

| Variant (runtime / mode) | runtime blob | P0 prohibited / stale | answer@1 | all critical | no-answer with context (items) | empty on answerable | precision@b | recall@b | nDCG@b | distractors |
|---|---|---|---|---|---|---|---|---|---|---|
| 773-candidate-9c9bf4d/composed-T | `bbf12bf390` | 0 / 0 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 37 |
| 773-candidate-9c9bf4d/composed-default | `bbf12bf390` | 0 / 1 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 36 |
| 773-candidate-9c9bf4d/selector-T | `bbf12bf390` | 0 / 0 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 37 |
| 773-repaired/composed-T | `0d5c5da1f4` | 0 / 0 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 37 |
| 773-repaired/selector-T | `0d5c5da1f4` | 0 / 0 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 37 |
| main-3eebb6d/composed-default | `65a39d5e3d` | 0 / 1 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 36 |
| v7-9b025f9/composed-T | `65a39d5e3d` | 0 / 0 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 37 |
| v7-9b025f9/composed-default | `65a39d5e3d` | 0 / 1 | 0.619 | 0.905 | 3/3 (9) | 0 | 0.444 | 0.905 | 0.826 | 36 |

**Stability** (served rows / full ranked admissions that differ):

- main-3eebb6d/composed-default vs v7-9b025f9/composed-default: served none; ranked none
- v7-9b025f9/composed-T vs 773-candidate-9c9bf4d/composed-T: served none; ranked none
- v7-9b025f9/composed-T vs 773-repaired/composed-T: served none; ranked none
- v7-9b025f9/composed-default vs 773-candidate-9c9bf4d/composed-default: served none; ranked none
- v7-9b025f9/composed-default vs v7-9b025f9/composed-T: served ['H09']; ranked ['H01', 'H06', 'H07', 'H09', 'H13', 'H17', 'H18', 'H19', 'H20', 'H22']

### Per question, unchanged reference runtime (v7-9b025f9/composed-default)

| Q | stratum | intent | budget | served | answer@1 | critical | failure categories |
|---|---|---|---|---|---|---|---|
| H01 | changing-fact-current | current | 3 | bus, migration-rule, pgver-16 | ✗ | 1/1 | current_top1_miss |
| H02 | changing-fact-history | historical | 3 | pgver-16, pgver-15, adr-db-v2 | ✗ | 1/1 | historical_target |
| H03 | decision-why-history | historical | 3 | adr-db-v1, oncall-lrt, oncall-platform | ✓ | 1/1 | – |
| H04 | decision-why-history | historical | 3 | bookclub, adr-db-v1, fx-fetch | ✗ | 0/1 | historical_target, why_target |
| H05 | decision-why | timeless | 3 | bus-why, bus, bookclub | ✓ | 1/1 | – |
| H06 | changing-fact-current | current | 2 | oncall-lrt, deploy-days | ✓ | 1/1 | – |
| H07 | unreliable-source | current | 3 | ratelimit, ratelimit-rumor, oncall-lrt | ✓ | 1/1 | – |
| H08 | correction-current | current | 2 | authz-5s, migration-rule | ✓ | 1/1 | – |
| H09 | expired-window | current | 3 | deploy-days, region-eu-us, freeze-bf25 | ✓ | 1/1 | stale_exposure |
| H10 | multi-fact-why | timeless | 3 | inc-2207, migration-rule, region-draft | ✓ | 2/2 | – |
| H11 | single-fact | timeless | 2 | money-repr, bus | ✓ | 1/1 | – |
| H12 | decision-why | timeless | 3 | fx-fetch, fx-why, money-repr | ✗ | 1/1 | why_target |
| H13 | changing-fact-current | current | 3 | region-eu-us, bus, migration-rule | ✓ | 1/1 | – |
| H14 | correction-history | historical | 3 | region-eu-us, region-eu, region-draft | ✗ | 1/1 | historical_target |
| H15 | paraphrase | timeless | 2 | pci, authz-5s | ✓ | 1/1 | – |
| H16 | single-fact | timeless | 2 | webhook-retry, pci | ✓ | 1/1 | – |
| H17 | no-answer | current | 3 | oncall-lrt, bookclub, room | n/a | 0/0 | no_answer_context |
| H18 | no-answer-deleted | current | 3 | ratelimit, ratelimit-rumor, bookclub | n/a | 0/0 | no_answer_context |
| H19 | no-answer-cross-project | current | 3 | oncall-lrt, bookclub, room | n/a | 0/0 | no_answer_context |
| H20 | multi-fact-current | current | 4 | fx-why, ratelimit-rumor, fx-fetch, inc-2207 | ✗ | 0/3 | multi_fact_incomplete, current_top1_miss |
| H21 | unseen-terminology | timeless | 3 | bus, region-draft, ratelimit-rumor | ✓ | 1/1 | – |
| H22 | contradiction | current | 3 | ratelimit-rumor, ratelimit, fx-why | ✗ | 1/1 | unconfirmed_first, current_top1_miss |
| H23 | decision-why | timeless | 3 | migration-rule, inc-2207, bookclub | ✗ | 1/1 | why_target |
| H24 | distractor-domain | timeless | 2 | room, bookclub | ✓ | 1/1 | – |

### #773 before/after at the same instant (v7 composed-T → #773 selector-T)

| Q | intent | before | after | change | excluded as known-not-current | valid evidence excluded |
|---|---|---|---|---|---|---|
| H01 | current | bus, migration-rule, pgver-16 | bus, migration-rule, pgver-16 | unchanged | freeze-bf25 | – |
| H06 | current | oncall-lrt, deploy-days | oncall-lrt, deploy-days | unchanged | freeze-bf25 | – |
| H07 | current | ratelimit, ratelimit-rumor, oncall-lrt | ratelimit, ratelimit-rumor, oncall-lrt | unchanged | freeze-bf25 | – |
| H08 | current | authz-5s, migration-rule | authz-5s, migration-rule | unchanged | – | – |
| H09 | current | deploy-days, region-eu-us, adr-db-v2 | deploy-days, region-eu-us, adr-db-v2 | unchanged | freeze-bf25 | – |
| H13 | current | region-eu-us, bus, migration-rule | region-eu-us, bus, migration-rule | unchanged | freeze-bf25 | – |
| H17 | current | oncall-lrt, bookclub, room | oncall-lrt, bookclub, room | unchanged | freeze-bf25 | – |
| H18 | current | ratelimit, ratelimit-rumor, bookclub | ratelimit, ratelimit-rumor, bookclub | unchanged | freeze-bf25 | – |
| H19 | current | oncall-lrt, bookclub, room | oncall-lrt, bookclub, room | unchanged | freeze-bf25 | – |
| H20 | current | fx-why, ratelimit-rumor, fx-fetch, inc-2207 | fx-why, ratelimit-rumor, fx-fetch, inc-2207 | unchanged | freeze-bf25 | – |
| H22 | current | ratelimit-rumor, ratelimit, fx-why | ratelimit-rumor, ratelimit, fx-why | unchanged | freeze-bf25 | – |

## Failure categories across corpora (unchanged runtime, composed-default)

| Category | Halcyon v1.1 | Cedarline v1.1 |
|---|---|---|
| stale_exposure | H09 | C11 |
| no_answer_context | H17, H18, H19 | C11, C21, C22, C23 |
| historical_target | H02, H04, H14 | C02, C03, C04, C07 |
| why_target | H04, H12, H23 | C03, C04 |
| multi_fact_incomplete | H20 | C13, C20, C24 |
| unconfirmed_first | H22 | C14 |
| current_top1_miss | H01, H20, H22 | C14, C17 |
