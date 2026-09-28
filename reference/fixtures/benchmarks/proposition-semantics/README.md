# Proposition-semantics qualification corpus (#594 Phase B)

Status: **pre-gold package, draft v2, awaiting a second maintainer sample review.** Nothing in this directory is benchmark gold. No interpreter score exists or may be computed from these files. The interpreter has still not been run on any sampled item.

## Why this exists

#550 measured the write-time interpreter's *coverage* on LongMemEval_S user turns:

| outcome | share |
| --- | ---: |
| known proposition | 14.5% |
| ambiguous | 47.6% |
| unknown | 37.9% |

Coverage says nothing about *precision*. This corpus is built to test two things:

* whether the "known" outputs are correct;
* whether "ambiguous" and "unknown" are appropriately conservative.

## Required sequence (anti-circularity)

```text
source corpus
  -> deterministic sample selection       select_sample.py            (committed 2119372)
  -> frozen sample manifest               sample-v1.json, sample-v1.manifest.json
  -> annotation rubric                    annotation-rubric.md        (committed 1a4d012, before any label)
  -> draft human-readable annotations     draft-annotations-v1.json   (committed 6fc1114)
  -> maintainer review 1                  PR #595 ruling: interpretation != retention; 15 boundary rulings
  -> rubric v2 + draft v2 + change manifest annotation-rubric-v2.md, draft-annotations-v2.json, draft-v1-to-v2-change-manifest.json
  -> STOP FOR SECOND MAINTAINER REVIEW    <- this package stops here
  -> accepted gold later                  a new, separately versioned file with an acceptance record
  -> only then interpreter scoring        proposition_semantics_evaluator.py (refuses non-accepted gold)
```

The git history records this order.

The Agent Memory interpreter was **never run** on the sampled items to:

* select them;
* stratify them;
* order them;
* draft their labels.

The Phase A activation counts ran the interpreter over the whole corpus only *after* the drafts were committed, and they emit aggregate counts only.

## Files

| file | what it is |
| --- | --- |
| `select_sample.py` | deterministic selector; imports nothing from Agent Memory and reads no gold field |
| `sample-v1.json` | 268 frozen items: `item_id`, `part`, `stratum`, `origin`, `surface_cues`, `text_sha256`, `text` |
| `sample-v1.manifest.json` | source identity, algorithm, seed, eligibility, strata, cell counts, population counts, hashes |
| `annotation-rubric.md` | rubric v1: semantic label definitions, written independently of the runtime grammar (kept unchanged) |
| `draft-annotations-v1.json` | v1 labels (kept unchanged), marked **DRAFT / MODEL-ASSISTED / NOT ACCEPTED GOLD / NOT SCORED** |
| `annotation-rubric-v2.md` | rubric v2: interpretation is not retention policy; unresolved references; supporting context; coordinated values; cardinality by semantic meaning (§9 lists every difference from v1) |
| `draft-annotations-v2.json` | all 268 items re-reviewed under rubric v2, with the 15 maintainer rulings applied; same four draft labels; pins the v1 file by hash |
| `draft-v1-to-v2-change-manifest.json` | every changed item with old/new status, principal, cardinality, and aspect, its reason and ruling class; grouped by status transition, reason, ruling class, sample part, and stratum |
| `build_change_manifest.py` | regenerates the manifest from the two annotation files; a test pins that the committed manifest is current |

## Sample

* **Source.** LongMemEval_S cleaned:
  * `xiaowu0162/longmemeval-cleaned` @ `98d7416c24c778c2fee6e6f3006e7a073259d48f`;
  * sha256 `d6f21ea9…a442`;
  * not committed.
* **Unit and population.**
  * Unit: one unique user-turn text; there are 93,931 unique turns.
  * Eligible: 90,375 turns of 20 to 600 characters and at least 4 words, with no e-mail address, URL, or phone-like digit run.
* **Order key.** `sha256("agent-memory-594-proposition-sample-v1" || NUL || sha256(text))`.
* **Part R: 100 items.** A simple random sample of the eligible population. This is the only part that estimates population rates.
* **Part S: 168 items.** 12 strata × 2 origins × 7 items, chosen by surface cues:
  * strata: change, coexistence, employment, residence/location, preference, hedging, present/current, prospective, past-habitual, proper-noun subject, temporal-word-non-temporal, simple first-person statement;
  * origins: simulated user sessions and ShareGPT/UltraChat filler.

  Part S is reported per stratum and never pooled with R.
* **Hashes.**
  * sample file sha256 `b1957ca4ff95c3b8a227b8b75f74327911172305cf770c927d56091e7fedd8d3`;
  * item text-hash list sha256 `3dceb7cde08abf45af3ea1d4dc12d117c390a3441eed38b3ca2273e04f986b88`.

  The sample reproduces byte-identically.

Some requested categories are thin in the natural corpus:

| category | eligible turns (simulated / filler) |
| --- | ---: |
| explicit change language | 483 / 129 |
| simple first-person statements | 111 / 84 |
| multiple simultaneous employers | no dedicated cue |

The strata are not forced to be equal beyond seven per cell. No synthetic text was added.

## Draft annotations (not gold)

| | all | Part R | Part S |
| --- | ---: | ---: | ---: |
| known | 64 | 23 | 41 |
| ambiguous | 106 | 39 | 67 |
| unknown | 98 | 38 | 60 |

Among the 64 drafts labelled known:

| | values |
| --- | --- |
| cardinality | multi_valued 55, single_valued 8, hierarchical 1 |
| aspect | present 39, prospective 21, none/unknown 3, past-habitual 1 |

Across all 268 items:

| marker | count |
| --- | --- |
| change | 14 yes, 3 ambiguous |
| coexistence | 24 yes |
| hedged | 61 |
| self-authority | 2, both self-corrections ("I meant to say…") |
| temporal language used non-temporally | 13 |

### Draft v2 (current)

Rubric v2 applies the maintainer ruling that semantic interpretation must not decide retention worthiness. A short-term plan, choice, search constraint, or state is a proposition whenever its entity, property, and value are determinable from the turn alone. An unresolved reference is never `known`, and several propositions make a turn `ambiguous` only when no principal is uniquely determinable. All 268 items were re-reviewed twice from their text alone. The interpreter was not run and no prediction was consulted.

* **Pass 1 (`799e44c`).** The 15 rulings, plus the supporting-context, coordinated-list, attitude, and short-lived-plan rules.
* **Pass 2 (this revision).**
  * Two `known` items whose value rested on an unresolved reference, or on a value stated only inside a request, became `ambiguous` (ps1-063, 103).
  * Two `unknown` items with an asserted but unresolved proposition became `ambiguous` (ps1-057, 096).
  * Three notes still gave duration as the reason and were re-decided on semantics (ps1-031, 074, 200).
  * ps1-010 is an asserted habitual worry with a stated object.
  * Cardinality was re-reviewed against the new §4 table. Four items changed away from single_valued-by-one-value or an unknown stance: ps1-055, 264 and 267 became multi_valued, and ps1-033 became single_valued. ps1-180's property was narrowed to the luggage plan for one trip.

| | v1 | v2 | v2 Part R (100) | v2 Part S (168) |
| --- | ---: | ---: | ---: | ---: |
| known | 64 | 137 | 51 | 86 |
| ambiguous | 106 | 45 | 16 | 29 |
| unknown | 98 | 86 | 33 | 53 |

87 items changed (`draft-v1-to-v2-change-manifest.json`): 33 of 100 in Part R and 54 of 168 in Part S.

**Status transitions (rows v1, columns v2).**

| | known | ambiguous | unknown |
| --- | ---: | ---: | ---: |
| known | 62 | 2 | 0 |
| ambiguous | 70 | 36 | 0 |
| unknown | 5 | 7 | 86 |

**Changes by reason.**

| reason | items | ruling class |
| --- | ---: | --- |
| principal proposition with supporting context | 42 | corpus re-review |
| maintainer boundary ruling | 11 | ruling (4 more KEEP rulings left status unchanged) |
| coordinated value list is one proposition | 10 | corpus re-review |
| asserted attitude or state with a determinate value | 7 | corpus re-review |
| short-lived plan or choice is a proposition | 4 | corpus re-review |
| duration rationale removed | 3 | corpus re-review |
| unresolved reference is not known | 2 | corpus re-review |
| asserted proposition with an unresolved value | 2 | corpus re-review |
| cardinality by semantic meaning | 2 | 1 corpus re-review, 1 KEEP ruling item (ps1-267, status kept) |
| search constraint or goal is a proposition | 2 | corpus re-review |
| determinate value on a different property | 1 | corpus re-review |
| reference resolvable within the turn | 1 | corpus re-review |

Field changes among the 87 items:

| field | items changed |
| --- | ---: |
| status | 84 |
| principal proposition (including null ↔ a proposition) | 77 |
| cardinality | 30 |
| temporal aspect | 36 |

75 of the 87 changes are to items outside the 15 flagged boundary cases, all from the corpus-wide re-review. Of the other 12, 11 are CHANGE rulings, and ps1-267 kept its ruled status but changed cardinality.

### What the second review should sample first

* **"Principal with supporting context" (42 items).** This is the largest source of change and my own generalization of the rulings on ps1-166, 180, 181, and 197: episodic anecdotes, reasons, and background ownership do not compete with the plan, goal, or state that the turn is about. The line between a *supporting* second proposition and a *competing* one remains the least certain call. The items kept `ambiguous` under the competing reading include ps1-014, 035, 039, 045, 047, 050, 086, 095, 124, 125, 128, 131, 154, 156, 169, 178, 203, 207, 209, 234, 237, 239, and 250.
* **Coordinated values (10 items)** such as "UF and ASU" or "a PS5 or an Xbox Series X" are now one proposition with a list value. ps1-252 is an undecided choice between two named values; it is labelled `known` under this rule, but it could equally be read as competing.
* **Attitudes as propositions (7 items):** ps1-010, 143, 157, 162, 163, 201, 258. ps1-200 (gym attitude) follows the same reading.
* **Cardinality (§4 table).** The table is new in this revision and has had no maintainer review. The items most exposed to it are ps1-055, 264, and 267 (single_valued → multi_valued), plus the single_valued items that remain: ps1-072, 076, 135, 151, 165, 168, 171, 180, 192, 200, 201, 223, 224, 232, 251, and 258.

### Items adjudicated in review 1 (v1 text kept for the record)

* **15 `boundary_case` items.** These are momentary intentions or choices ("I'll try the Moscato", "I'm thinking of packing…") versus lasting plans. The rubric's "durable or lasting state" line is least certain here, and the drafts are not fully consistent across that line.
* **Residence or job changes with no value.** For example, "I moved into my new apartment a month ago". These are drafted `ambiguous` because the value (a location or employer) is missing.
* **Multi-proposition turns.** These are drafted `ambiguous`. An alternative rubric reading would score the most salient proposition as `known`.
* **Self-corrections.** "I meant to say X, not Y" is drafted as `self_authority_claim = yes`. The rubric could instead treat these as ordinary change language.

### Disclosure

The drafting model had read `proposition_semantics.py` in earlier sessions (#550). Labels follow the rubric's semantic definitions, not runtime rules, but that exposure cannot be ruled out as an influence. That is why these labels are only drafts and require independent maintainer acceptance.

## Evaluator

`reference/proposition_semantics_evaluator.py` is the evaluator contract. `reference/tests/test_proposition_evaluator.py` holds 20 tests: evaluator tests on synthetic evaluator-only fixtures, plus integrity tests on the frozen files. They prove the evaluator detects each of these, each with its own counter and no aggregate:

* wrong proposition slot;
* wrong value;
* over-eager single-valued cardinality;
* coexistence misclassified as replacement;
* temporal-aspect over-classification or mismatch;
* unknown or ambiguous promoted to known;
* benchmark timestamp leakage.

The tests also pin that:

* draft annotations are refused by `load_gold`;
* only a set with an explicit acceptance record loads;
* the frozen sample matches its manifest;
* the drafts cover exactly the frozen sample and stay marked draft;
* v2 pins v1 by hash, the change manifest lists exactly the changed items with every required field, and it regenerates byte-identically from the annotation files;
* v2 labels are internally consistent, carry the 15 ruled statuses, and no note gives duration as a reason.

The fixtures are not Agent Memory performance evidence.

## Next step (not taken here)

The maintainer reviews the drafts, then freezes or corrects each item. Accepted gold goes into a new file, `accepted-gold-v1.json`, with an `acceptance` record, a property alias table frozen with it, and a rationale for each correction. Only after that does a separate step run the interpreter over the sample and score it with the evaluator.
