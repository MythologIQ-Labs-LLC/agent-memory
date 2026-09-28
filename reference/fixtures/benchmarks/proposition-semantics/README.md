# Proposition-semantics qualification corpus (#594 Phase B)

Status: **pre-gold package, draft v4, awaiting maintainer review.** Nothing in this directory is benchmark gold. No interpreter score exists or may be computed from these files. The interpreter has still not been run on any sampled item.

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
  -> maintainer review 2                  PR #595 review 5338941285: ps1-010 and ps1-252 consistency defects; keep v2, make v3
  -> rubric v3 + draft v3 + change manifest annotation-rubric-v3.md, draft-annotations-v3.json, draft-v2-to-v3-change-manifest.json
  -> maintainer review 3                  PR #595 review 5339238113: proposition-list boundary; 5 direct rulings
  -> rubric v4 + draft v4 + change manifest annotation-rubric-v4.md, draft-annotations-v4.json, draft-v3-to-v4-change-manifest.json
  -> STOP FOR MAINTAINER REVIEW           <- this package stops here
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
| `annotation-rubric-v2.md` | rubric v2 as the second maintainer review read it (kept unchanged): interpretation is not retention policy; unresolved references; supporting context; coordinated values |
| `draft-annotations-v2.json` | v2 labels as the second review read them (kept unchanged; the 15 rulings applied; pins v1) |
| `draft-v1-to-v2-changes.json` | the original v1 → v2 manifest as the second review read it (`799e44c`, kept unchanged) |
| `draft-v1-to-v2-change-manifest.json` | every v1 → v2 change: old/new status, principal, cardinality, aspect, reason, ruling class; grouped by transition, reason, ruling class, part, and stratum |
| `annotation-rubric-v3.md` | rubric v3: v2 plus attitudes/states as propositions, the coordinated-list rule limited to one governing predicate, and the second-pass rules (§10 lists every difference from v2) |
| `draft-annotations-v3.json` | all 268 items under rubric v3; same four draft labels; pins v2 by hash; per-item `v3_change_reason` |
| `annotation-rubric-v4.md` | rubric v4: `propositions` holds only asserted or legitimately presupposed propositions; a request may resolve a separate declarative; a different predicate does not by itself compete (§11) |
| `draft-annotations-v4.json` | all 268 items under rubric v4; pins v3 by hash; per-item `v4_change_reason`, `maintainer_review_3`, and `excluded_request_only_content` (content deliberately not recorded because it appears only in a question or request) |
| `draft-v3-to-v4-change-manifest.json` | every v3 → v4 change, separating the review's direct rulings from corpus-wide findings |
| `draft-v2-to-v3-change-manifest.json` | every v2 → v3 change in the same shape, plus the outcome of re-reviewing each of the 77 v1 → v2 changes |
| `build_change_manifest.py` | regenerates both manifests from the annotation files; a test pins that the committed manifests are current |

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

### Draft v2 (kept as the second review read it)

Rubric v2 applied the ruling that semantic interpretation must not decide retention worthiness. All 268 items were re-reviewed, and the 15 rulings applied.

| | v1 | v2 |
| --- | ---: | ---: |
| known | 64 | 136 |
| ambiguous | 106 | 44 |
| unknown | 98 | 88 |

77 items changed (`draft-v1-to-v2-change-manifest.json`): 67 ambiguous→known, 5 unknown→known, 5 unknown→ambiguous.

An earlier revision of this branch (`bd50e0a`) edited v2 in place with a second review pass. That pass is now in v3, and v2 is back to exactly the content the second maintainer review read (`799e44c`), as that review asked.

### Draft v3 (kept as the third review read it)

The second maintainer review found two consistency defects:

* ps1-010 was a determinate personal attitude left `ambiguous`.
* ps1-252 used the coordinated-list rule across different predicates.

Rubric v3 fixes both at the rule level (§3):

* An asserted attitude or state with a determinate value is a proposition; being an attitude is never a reason for `ambiguous`.
* The coordinated-list rule applies only when one predicate governs the list.

v3 also folds in the second pass made on v2 before that review arrived. That pass covered unresolved references, notes that rested on duration, and cardinality by semantic meaning (§4 table).

Work done for v3, from item text only (the interpreter was not run and no prediction was consulted):

1. All 77 v1 → v2 changes were re-reviewed for the two defects: 71 confirmed and 6 revised (ps1-033, 055, 068, 082, 180, 252).
2. The 10 coordinated-list items were checked for one governing predicate: 8 hold and 2 do not (ps1-068, 252).
3. Every `ambiguous` item and every opinion or attitude `unknown` item was checked against the attitude rule. Six became `known` (ps1-046, 086, 102, 203, 230, 235), plus ps1-010.
4. The unchanged `known` items were spot-checked for a principal that appears only inside a question (ps1-082 revised).

| | v2 | v3 | v3 Part R (100) | v3 Part S (168) |
| --- | ---: | ---: | ---: | ---: |
| known | 136 | 141 | 52 | 89 |
| ambiguous | 44 | 42 | 15 | 27 |
| unknown | 88 | 85 | 33 | 52 |

22 items changed (`draft-v2-to-v3-change-manifest.json`): 12 of 100 in Part R and 10 of 168 in Part S.

**Status transitions v2 → v3 (rows v2, columns v3).**

| | known | ambiguous | unknown |
| --- | ---: | ---: | ---: |
| known | 132 | 4 | 0 |
| ambiguous | 8 | 36 | 0 |
| unknown | 1 | 2 | 85 |

| reason | items |
| --- | --- |
| asserted attitude or state with a determinate value | 7: ps1-010, 046, 086, 102, 203, 230, 235 |
| cardinality by semantic meaning | 5: ps1-033, 055, 180, 264, 267 |
| duration rationale removed | 3: ps1-031, 074, 200 |
| different predicates are not one list | 2: ps1-068, 252 |
| unresolved reference is not known | 2: ps1-063, 103 |
| asserted proposition with an unresolved value | 2: ps1-057, 096 |
| value inside a question is not asserted | 1: ps1-082 |

Field changes: status 15, principal proposition 15, cardinality 12, temporal aspect 5. Ruling classes:

* ps1-010 and 252 are second-review items;
* ps1-180 and 267 are ruled items whose ruled status is kept;
* the other 18 come from the corpus re-review.

### Draft v4 (current)

The third maintainer review found a proposition-list boundary defect. Some lists recorded question or request content as affirmed propositions even where the note said it was not asserted. In two cases, supporting context displaced a clear principal. Rubric v4 (§1, §3, §11) states the boundary:

* `propositions` holds only asserted or legitimately presupposed propositions;
* question or request content alone never becomes a proposition, property, or value;
* a request may resolve the referent of a separate declarative in the same turn;
* a different predicate does not by itself compete.

**Direct rulings (5).**

| item | ruling |
| --- | --- |
| ps1-063 | ambiguous → known: active hotel search in Seattle |
| ps1-068 | ambiguous → known: sale goal; the owned items are supporting |
| ps1-082 | known; the unasserted Mig proposition is removed |
| ps1-086 | known; the request-only lens search is removed |
| ps1-103 | ambiguous; the inferred Orlando destination is removed |

**Bounded corpus-wide check (12 findings).** All 268 proposition lists were checked for the two named defect classes only, not relabelled in general. Presupposed content, such as "my trip to Osprey Reef", "my job search", and "my vintage cameras", is kept.

* **Question or request content recorded as asserted (6):**
  * ps1-065: Michelin was only "heard good things" about;
  * ps1-067: literacy and education appear only in the request;
  * ps1-097: "suitable for oily skin" appears only in the request;
  * ps1-157 and 163: "wants" was inferred from "where can I find/buy";
  * ps1-222: the cuisines appear only in the request.

  All six stay `known`; only their values or properties change.
* **False ambiguity from supporting context (6), ambiguous → known:**
  * ps1-095: the car serves the road trip;
  * ps1-124: the contest is "a nice bonus" to the IPMS plan;
  * ps1-125: the ROAS plan is the only asserted plan, and the business is presupposed;
  * ps1-154: "this recipe" is unresolved and supporting, as in ps1-203;
  * ps1-156 and 209: "by the way" asides, as in ps1-042 and 222.

  The v3 lists for ps1-124 and ps1-125 had omitted the principal plan.

| | v3 | v4 | v4 Part R (100) | v4 Part S (168) |
| --- | ---: | ---: | ---: | ---: |
| known | 141 | 149 | 55 | 94 |
| ambiguous | 42 | 34 | 12 | 22 |
| unknown | 85 | 85 | 33 | 52 |

17 items changed (`draft-v3-to-v4-change-manifest.json`): 8 of 100 in Part R and 9 of 168 in Part S.

* Transitions: 8 ambiguous→known, 8 known with a changed proposition list, 1 ambiguous with a changed list.
* Field changes: status 8, principal proposition 14, cardinality 3, temporal aspect 4.
* Of the kept ambiguous items, ps1-014, 035, 039, 050, 109, 128, 131, 169, 178, 207, 237, and 250 have genuinely competing candidates. ps1-089 and 234 have hypothetical guesses about another party, which rubric §3 keeps as ambiguous.

### What the next review should sample first

* The six false-ambiguity findings (ps1-095, 124, 125, 154, 156, 209), especially ps1-095 and ps1-156, where the supporting reading is least certain.
* The kept ambiguous items listed above, as the complement of the same check.
* ps1-097, where the request resolves "their" (the ps1-063 pattern) but its "oily skin" constraint is not recorded.

### Items adjudicated in review 1 (v1 text kept for the record)

* **15 `boundary_case` items.** These are momentary intentions or choices ("I'll try the Moscato", "I'm thinking of packing…") versus lasting plans. The rubric's "durable or lasting state" line is least certain here, and the drafts are not fully consistent across that line.
* **Residence or job changes with no value.** For example, "I moved into my new apartment a month ago". These are drafted `ambiguous` because the value (a location or employer) is missing.
* **Multi-proposition turns.** These are drafted `ambiguous`. An alternative rubric reading would score the most salient proposition as `known`.
* **Self-corrections.** "I meant to say X, not Y" is drafted as `self_authority_claim = yes`. The rubric could instead treat these as ordinary change language.

### Disclosure

The drafting model had read `proposition_semantics.py` in earlier sessions (#550). Labels follow the rubric's semantic definitions, not runtime rules, but that exposure cannot be ruled out as an influence. That is why these labels are only drafts and require independent maintainer acceptance.

## Evaluator

`reference/proposition_semantics_evaluator.py` is the evaluator contract. `reference/tests/test_proposition_evaluator.py` holds 26 tests: evaluator tests on synthetic evaluator-only fixtures, plus integrity tests on the frozen files. They prove the evaluator detects each of these, each with its own counter and no aggregate:

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
* each draft pins its predecessor by hash (v2 → v1, v3 → v2, v4 → v3);
* each change manifest lists exactly the changed items with every required field, and both regenerate byte-identically from the annotation files;
* the v2 → v3 manifest accounts for every v1 → v2 change;
* the frozen v1–v3 files match pinned sha256 values;
* no content listed in `excluded_request_only_content` survives in any v4 proposition list;
* no prediction or accepted-gold file exists, and no draft consulted interpreter output;
* no file under `reference/agentmem_ref` differs from the #594 base (skipped only in a shallow clone);
* v4 labels are internally consistent, carry the 15 ruled statuses and every second- and third-review outcome, and no note gives duration as a reason.

The fixtures are not Agent Memory performance evidence.

## Next step (not taken here)

The maintainer reviews the drafts, then freezes or corrects each item. Accepted gold goes into a new file, `accepted-gold-v1.json`, with an `acceptance` record, a property alias table frozen with it, and a rationale for each correction. Only after that does a separate step run the interpreter over the sample and score it with the evaluator.
