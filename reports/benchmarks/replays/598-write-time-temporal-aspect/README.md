# #598 write-time temporal aspect: interpreter 1.1.0 evidence

Base: `main` `0103b9f3ba0ab90c4914837dcb98a9cdad7c4c2a`. Write interpreter
`agent-memory-deterministic-write-semantics` 1.0.0 → **1.1.0**. `CLASSIFIER_VERSION` stays **1.0.0**:
same-slot classification and proposals are unchanged. The accepted #594 gold, rubric, sample, Part R
membership and evaluator (0.2.0) are unchanged. Ranking policy 3.1.0, BM25, query temporal intent
(#585), #549 admission, #583 and #584 are untouched. ADR-039 remains **Proposed**.

Aspect is evidence only. It grants no currentness, authority, validity window, or ranking effect, and
`markers.aspect` has no ranking or admission reader.

## Order of work

| step | commit | artifact |
| --- | --- | --- |
| failure inventory, before any runtime change | `4dc38de` | `failure-inventory-v1.json` (40 accepted aspect failures across all 268 items, one mechanism each) |
| frozen adversarial contract, before any runtime change | `04bc06e` | `reference/fixtures/runtime/write-temporal-aspect-v1.1-adversarial.json`, `reference/tests/test_write_temporal_aspect_contract.py` (36 cases, classes A–H) |
| implementation | `ab21ca8` | `reference/agentmem_ref/runtime/proposition_semantics.py`, `reference/tests/test_write_temporal_aspect_v1_1.py` |

## Defect mechanism (1.0.0)

`interpret_write` computed aspect over the whole normalized write before any clause or principal
scope: `{name: [cue for cue in cues if _contains(lowered, cue)]}`. Every cue anywhere in the text
counted, so questions ("which bills are being debated right now?"), requests, relative and causal
clauses, discourse "Now,", passive "used to", and motion "going to" set the memory's aspect. Several
regimes could co-occur, and the evaluator then scored the alphabetically first.

## Scoping algorithm (1.1.0)

The cue lexicon is unchanged. Per clause piece (the existing `_split_clauses` pieces, unchanged),
cues are matched leftmost-longest ("right now" is one cue, not also "now"). Each match is declined,
in this order, with a typed reason:

1. `discourse_marker`: "now," opening the clause after fillers ("so", "okay", "honestly").
2. `question_or_request`: the cue lies in the interrogative part of a `?` sentence, or in a clause
   opened by a request. The interrogative part starts at the first comma or conjunction segment that
   opens a question or request ("do you have…", "I was wondering if…"). A declarative lead-in before it
   stays asserted. With no such segment, the whole sentence is the question.
3. `subordinate_clause`: a relative, causal, conditional or concessive subordinator ("that", "which",
   "who", "because", "since", "if", "although", …) precedes the cue in its own comma segment.
   "when" and "while" are deliberately excluded.
4. `passive_or_accustomed`: "used to" after be/get/become, skipping -ly and degree adverbs.
5. `motion_or_habitual`: "going to" after an aspectual or habitual verb, or before a destination.
6. `non_principal_clause`: when the write has exactly one known proposition, a cue outside that
   proposition's own affirmed clauses.

What survives sets the aspect:

* one surviving regime → `markers.aspect`, with status `resolved_principal` or `resolved_write`;
* more than one → `mixed_regimes`, and aspect is omitted;
* none → `none`.

The diagnostic `aspect_scope = {status, declined[]}` is on the interpretation only and is not
persisted, the same as clause parses.

This is not a parser. The rules decline and never add, so 1.1.0 reports a subset of 1.0.0's regimes
for every write.

## Persistence and compatibility

* The stored version string is `1.1.0/1.0.0` for new writes. Facts written under 1.0.0 keep
  `1.0.0/1.0.0` and their stored markers, including multi-regime aspect. `expanded_form` reads the
  version from storage, so nothing is silently reinterpreted. Tested across close and reopen.
* `markers.aspect` keeps its shape (`{regime: [cues]}`), now with at most one regime. When "right now"
  is present, the nested "now" is no longer listed.
* `proposal_id` hashes the interpreter version, so ids for proposals created by new writes differ from
  ids a 1.0.0 write would have produced. Stored proposals keep their ids. No fixture pins such an id.

## Re-score on accepted #594 gold (`rescore-comparison-v1.json`)

| | aspect_mismatch | aspect_over_classification | correct non-none aspect |
| --- | ---: | ---: | ---: |
| Part R (100), 1.0.0 | 4 | 1 | 10 (present 6, prospective 4) |
| Part R (100), 1.1.0 | **2** | **0** | **10** (present 6, prospective 4) |
| all 268 (diagnostic, not a population estimate), 1.0.0 | 17 | 23 | 38 (present 16, prospective 22) |
| all 268 (diagnostic), 1.1.0 | **7** | **5** | **33** (present 14, prospective 19) |

The evaluator never penalizes abstention, so correct-aspect retention is reported beside the failure
classes.

* **Fixed, Part R (3):** ps1-010, ps1-015, ps1-045.
* **Fixed, all 268 (28):**
  * mismatch: ps1-010, 045, 101, 114, 125, 132, 189, 190, 203, 226;
  * over-classification: ps1-015, 111, 129, 185, 186, 187, 188, 199, 202, 204, 214, 215, 216, 242, 245, 246, 248, 254.
* **Newly regressed into either failure class: 0.**
* **Non-aspect prediction drift: 0 of 268.** Non-aspect failure counts are identical:
  * Part R: wrong_slot 8, unknown_promoted_to_known 2;
  * all 268: wrong_slot 27, unknown_promoted_to_known 22, coexistence_as_replacement 1.
* **Correct aspect withheld (5, none in Part R):** in each case 1.0.0 was right for a reason 1.1.0
  no longer accepts:
  * ps1-123: the only cue is a habitual "been going to the trail";
  * ps1-165: the cue is "won't" inside a relative clause;
  * ps1-211: the cue is "going to" after "especially since";
  * ps1-130 and ps1-258: present and prospective both survive, so the result is mixed_regimes.

Aspect pairs (gold → predicted, all 268):

| pair | 1.0.0 | 1.1.0 |
| --- | ---: | ---: |
| none_unknown → none_unknown | 73 | 91 |
| none_unknown → past_habitual / present / prospective | 6 / 10 / 7 | 1 / 1 / 3 |
| past_habitual → none_unknown | 2 | 2 |
| present → none_unknown / past_habitual / present / prospective | 63 / 3 / 16 / 7 | 70 / 1 / 14 / 4 |
| prospective → none_unknown / past_habitual / present / prospective | 52 / 3 / 4 / 22 | 60 / 1 / 1 / 19 |

Part R pairs: present→present 6→6, prospective→prospective 4→4,
present→prospective 3→1, none→prospective 1→0, present→none 27→29, none→none 36→37;
prospective→present 1 and prospective→none 22 are unchanged.

### Unresolved (12), with mechanism

| item | class | gold → 1.1.0 | mechanism |
| --- | --- | --- | --- |
| ps1-031 (R) | mismatch | prospective → present | the annotated principal (the trip) appears only in a question; the asserted "feeling much better now" survives |
| ps1-035 (R) | mismatch | present → prospective | multi-sentence write; the principal (snacking habit) has no cue and the asserted "going to try" survives |
| ps1-122 | mismatch | prospective → past_habitual | the principal ("thinking about taking up swimming") has no lexicon cue; the asserted "used to swim" survives |
| ps1-128 | mismatch | present → prospective | principal selection: "hoping to find" has no cue, "return them soon" survives |
| ps1-201 | mismatch | present → prospective | "I'm just going to live my life" is a present-disposition "going to" with a known proposition; bounded rules cannot separate it from intention |
| ps1-224 | mismatch | present → past_habitual | contrast ("used to …, but I've been having trouble … lately"): the present regime carries no cue |
| ps1-225 | mismatch | present → prospective | principal selection across four sentences |
| ps1-223 | over-classification | none → prospective | "a couple getting married soon": a participial noun modifier with no subordinator (needs NP parsing) |
| ps1-104 | over-classification | none → prospective | role-play instruction ("You are now … I am going to interview you") |
| ps1-105 | over-classification | none → prospective | pasted document content ("Management team will be reviewed") |
| ps1-107 | over-classification | none → past_habitual | pasted document content ("it no longer intends to be bound") |
| ps1-233 | over-classification | none → present | fiction prompt narration ("stronger now") |

The twelve fall into four groups:

* six (031, 035, 122, 128, 224, 225) need principal-proposition selection across multi-sentence
  ambiguous writes;
* one (223) needs NP-level parsing;
* both of those groups are #596/#597 territory, which the stop conditions exclude;
* one (201) is a contextual present-disposition "going to";
* four (104, 105, 107, 233) need detection of non-speaker or task content. No bounded lexical rule found
separates these from genuine speaker statements without new contamination. They remain
visible failures, and the evaluator can still fail Agent Memory on them.

## Collateral drift (`interpreter_drift.py`)

The script compares the full `interpret_write` output and the persisted form, with aspect removed,
between 1.0.0 (loaded from `0103b9f` with `git show`) and 1.1.0:

* #594 sample (268 writes): 0 interpretation drift, 0 persisted drift, 0 regimes introduced.
  `interpreter-drift-594-v1.0.0-vs-v1.1.0.json` pins per-item hashes of the 1.0.0 non-aspect
  interpretation, and `test_write_temporal_aspect_v1_1` asserts them.
* LongMemEval_S unique haystack turns: see `interpreter-drift-lme-s-v1.0.0-vs-v1.1.0.json`.

## External retrieval regression (LongMemEval_S)

See `lme-s-retrieval-regression-v1.json`.

## Reproduce

```bash
PYTHONPATH=reference python3 reference/run_proposition_semantics_score.py --output-dir OUT   # at base and at branch
PYTHONPATH=reference python3 reports/benchmarks/replays/598-write-time-temporal-aspect/rescore_compare.py
PYTHONPATH=reference python3 reports/benchmarks/replays/598-write-time-temporal-aspect/interpreter_drift.py 594 OUT.json
PYTHONPATH=reference python3 -m unittest reference.tests.test_write_temporal_aspect_contract \
    reference.tests.test_write_temporal_aspect_v1_1 reference.tests.test_write_time_proposition_semantics
```
