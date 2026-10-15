# C3 slice 4: entity bridging (rejected; negative result)

**Status: rejected. The mechanism is not in the C3 candidate.** Its full diff (selection policy
2.3.0, tests, development fixture) is preserved as `slice-4-entity-bridging.rejected.patch`, against
`4356a550`. It is not applied anywhere.

## Motivation

The independent #819 evaluation (`claude/819-independent-evaluation-no-ci`, REVIEW.md) reported at
architecture level that C1 and C2 keep the fact that names an entity but withhold the bridging fact
that carries the answer. This was the multi-hop category of its sealed holdout, 16 of 16. No case
content was shared and none was sought.

## Mechanism tried

- **Bridging.** A top primary-evidence fact names an entity the query does not ("Maya sees
  Dr. Okafor"). The admitted fact most about that entity joins ("Dr. Okafor's practice is on Elm
  Street").
- **Limits.** One hop; three sources; two names per source.
- **Gates**, added in order during development:
  - the query names no entity;
  - a topical term remains uncovered by the selected facts;
  - the query is a relational description (a possessive determiner or a possessive "'s").
- **Two general defects fixed along the way:**
  - "Dr." was read as a sentence end, which hid the name after it;
  - the substrate tokenised "Noah's" whole, so discovery missed "noah".

## Evidence

| Instrument | Result |
|---|---|
| Engineer fixture `multi-hop.json` (8; used during development, so not evidence) | C3 3/8 → 8/8 ungated → 7/8 final |
| AMB, first version | 0 fixed, 5 broken vs slice 3 (precision 0.522 → 0.465): names in entity-dense facts flood single-hop answers |
| AMB, final gated version | 38/77, 0 fixed, 0 broken, precision −0.004 |
| LongMemEval-S trace, final | all@10 unchanged (0 fixed, 0 broken); **81 bridged items returned, 0 gold**; pooled precision 0.381 → 0.370 |
| **Blind cohort** (30 scenarios, 32 queries, sealed `6acef4bf…` before the first run, authored without access to the runtime) | multi-hop strict 0/12 for C3 and slice 4; multi-hop recall 0.583 → 0.625; extra returned facts 12 → 13 |

On the blind cohort's 24 must-include multi-hop facts:

| | Never admitted (discovery) | Admitted but withheld | Extra facts returned |
|---|---:|---:|---:|
| C2 `eaf60e4d` | 8 | 5 | 5 |
| C3 `4356a550` | 5 | 5 | 12 |
| Slice 4 | 5 | 4 | 13 |

**Decision.** On unseen data, bridging recovered one fact and added noise. On LongMemEval, all 81
of its returns were non-gold. It is not shipped. Multi-hop needs two things selection cannot
provide:

1. **Bridge discovery.** Five of 24 required facts are never candidates, because they share no
   token with the question.
2. **A signal that a hop is needed** that is stronger than orthography and possession.

Both belong in a later slice: governed second-hop candidate generation (a second admitted
retrieval keyed on the first hop's entities), measured on this blind cohort's successor, not on
this cohort, which has now been seen.

## Full blind-cohort results (one run each, no runtime change after)

| | A `1df28f84` | C2 `eaf60e4d` | C3 `4356a550` | Slice 4 |
|---|---:|---:|---:|---:|
| Strict pass (32) | 2 | **15** | 12 | 11 |
| multi_hop (12) | 0 | 1 | 0 | 0 |
| multi_hop_lifecycle (8) | 1 | **5** | 3 | 3 |
| single_hop_with_names (8) | 1 | 8 | 8 | 8 |
| abstention_with_names (4) | 0 | 1 | 1 | 0 |
| Mean precision | 0.428 | **0.756** | 0.680 | 0.648 |
| Mean recall | **0.789** | 0.692 | 0.750 | 0.769 |
| Safety violations | 0 | 0 | 0 | 0 |

**This cohort ranks C3 below C2 on strict pass.** The cause is precision: C3 recovers more
required facts but returns more extras, which strict scoring penalises. It agrees with the
precision decline recorded in slices 1–2 (LongMemEval pooled precision 0.510 → 0.381) and is
reported here, not hidden. Results: `blind-multihop/result-*.json`; cohort:
`blind-multihop/scenarios.json`.
