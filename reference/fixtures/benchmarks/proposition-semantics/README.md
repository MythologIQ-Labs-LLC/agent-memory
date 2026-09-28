# Proposition-semantics qualification corpus (#594 Phase B)

Status: **pre-gold package, awaiting maintainer review.** Nothing in this directory is benchmark gold. No interpreter score exists or may be computed from these files.

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
| `annotation-rubric.md` | semantic label definitions, written independently of the runtime grammar |
| `draft-annotations-v1.json` | labels marked **DRAFT / MODEL-ASSISTED / NOT ACCEPTED GOLD / NOT SCORED** |

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

### Items the maintainer should adjudicate first

* **15 `boundary_case` items.** These are momentary intentions or choices ("I'll try the Moscato", "I'm thinking of packing…") versus lasting plans. The rubric's "durable or lasting state" line is least certain here, and the drafts are not fully consistent across that line.
* **Residence or job changes with no value.** For example, "I moved into my new apartment a month ago". These are drafted `ambiguous` because the value (a location or employer) is missing.
* **Multi-proposition turns.** These are drafted `ambiguous`. An alternative rubric reading would score the most salient proposition as `known`.
* **Self-corrections.** "I meant to say X, not Y" is drafted as `self_authority_claim = yes`. The rubric could instead treat these as ordinary change language.

### Disclosure

The drafting model had read `proposition_semantics.py` in earlier sessions (#550). Labels follow the rubric's semantic definitions, not runtime rules, but that exposure cannot be ruled out as an influence. That is why these labels are only drafts and require independent maintainer acceptance.

## Evaluator

`reference/proposition_semantics_evaluator.py` is the evaluator contract. `reference/tests/test_proposition_evaluator.py` holds 17 tests on synthetic evaluator-only fixtures. They prove the evaluator detects each of these, each with its own counter and no aggregate:

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
* the drafts cover exactly the frozen sample and stay marked draft.

The fixtures are not Agent Memory performance evidence.

## Next step (not taken here)

The maintainer reviews the drafts, then freezes or corrects each item. Accepted gold goes into a new file, `accepted-gold-v1.json`, with an `acceptance` record, a property alias table frozen with it, and a rationale for each correction. Only after that does a separate step run the interpreter over the sample and score it with the evaluator.
