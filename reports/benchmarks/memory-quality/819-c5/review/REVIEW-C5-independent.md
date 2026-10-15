# Independent adversarial review: #819 C5 (`eaed54ee`, selection policy 2.4.0) against C4 (`bc2be631`)

## Verdict

**BLOCKING findings: no.** I found no new authority, scope or disclosure path, and claim 2 holds: with the semantic route off, `returned` equals C4's exactly.

There are four **SHOULD-FIX** findings. The candidate should not be described as recovering aggregate evidence, and it should not claim the latency budget, until they are resolved:

1. The semantic *set* channel, and with it the whole Erratum-1 `plural_answer` reading, can never fire at the shipped constants. Aggregate recall is not recovered, and on aggregate queries C5 returns fewer members than C4 with the semantic route on.
2. Memory text that raises its own similarity can suppress a legitimate semantic-only answer. C4 with the semantic route on returns that answer.
3. The extra cost is +39 ms p50 at 200 facts and +147 ms p50 at 1000 facts. That exceeds preregistered A7 (≤ 25 ms against C4+sem) from about 200 facts upward.
4. The 0.25 absolute floor sits below the route's 0.30 discovery floor. C5 therefore returns facts that C4+sem's own route rejected, and only when they happen to share a function word with the query. The fail-first abstention test does not exercise this.

All worktrees are fresh and detached under `review-c5/` (`cand` = `eaed54ee`, `c4` = `bc2be631`). The probes are in `review-c5/probes/`. The real-model runs use `sem-venv/bin/python3` with `AGENT_MEMORY_REPRESENTATION_DIR=…/scratchpad/representation`. Offline fake-provider probes use the same `OnnxSentenceEmbeddingProvider` patch as the test file (`probes/fakes.py`). Each script takes the worktree path as its first argument. I did not read the sealed v4 cohort, the earlier cohorts or any benchmark gold.

---

## Findings

### F1. SHOULD-FIX: `semantic_set_evidence` is unreachable, so `plural_answer` and the aggregate mechanism are inert

**Where:** `return_selection.py`, `semantic_basis`. The chosen constants are `SEMANTIC_ABSOLUTE_FLOOR == SEMANTIC_SET_FLOOR == 0.25` and `SEMANTIC_SINGLE_MARGIN == SEMANTIC_SET_MARGIN == 0.05`.

**Why it never fires:**
- The set branch is tested only after the single branch fails.
- With equal floors and margins, its condition is exactly the single branch's condition.
- So `semantic_set_evidence` can never be assigned. Neither `several`, which is `needs_several or plural_answer(query)`, nor Erratum 1 changes any returned list.

**What the documents claim, and what is true:**
- docs/44, the module docstring, the schema description and the erratum all describe a wider set channel for aggregate, relational and plural questions. It does not exist at the shipped point.
- The fail-first test `test_every_aggregate_member_is_returned_and_a_weak_neighbour_is_not` passes only because it puts the cat at `max(TAU_SET, 0.80 − DELTA_SET) + 0.03 = 0.78`. That is inside the *single* 0.05 margin. The test never tests the set channel.

**Repro:** `probes/repro_set_channel.py`, fake provider, dog 0.80 / cat 0.72 / fish 0.62 / car 0.10.
```
## cand
'Which pets do we have?':    returned=['m:dog']   (plural_answer=True)
'How many pets do we have?': returned=['m:dog']
'List all our pets.':        returned=['m:dog']
constants: abs 0.25 single 0.05 set 0.25 set_margin 0.05 -> set branch reachable: False
## c4 (semantic route on)
all three queries:           returned=['m:cat', 'm:dog', 'm:fish']
```

**Real model.** The `HOUSEHOLD` texts from the test file are in `probes/scen1.json`; run them with `harness.py`, then `compare.py 1`. For "Which pets do we have?" the cat scores 0.420 and the dog 0.314:

| Head | Returned |
|---|---|
| C5 | `['h:cat']` |
| C4+sem | `['h:cat', 'h:dog']` |
| C4 off | `[]` |

**On the authors' own dev set.** I re-ran it with the runner (`probes/dev-*.json`). The `multi` kind is 1/5 passed with recall 0.40 for **both** C4+sem and C5+sem: no aggregate gain at all. All of the +5 strict passes come from `single`, which goes from 16 to 22. `he-1` "Which medications am I on?" goes from `[med1, eye]` to `[med1]`; `med2` is still missing. The calibration grid agrees (`dev/calibration.json`, my re-analysis): every widening of the set parameters only lowers dev precision.

**Fix.** Either:
- remove the set channel and `plural_answer`, together with their docs, schema field and Erratum-1 text, and stop claiming aggregate recovery; or
- calibrate set parameters that are strictly looser, on aggregate-specific dev items.

Either way, add a test with a member *outside* the single margin and *inside* a set margin.

### F2. SHOULD-FIX: displacement, where stuffed or adversarial memory text suppresses the legitimate answer

**Where:** `best_similarity` is the maximum over *all* admitted facts, and every semantic selection must lie within 0.05 of it. Any admitted fact that reaches a higher similarity, through paraphrase or keyword stuffing, therefore withdraws the semantic sufficiency of every other fact. C4+sem returned all route candidates, so it was additive.

**What the tests miss:** `test_injected_instructions_and_stuffing_earn_nothing_special` gives the injected note a similarity of 0.15, so it never exercises this.

**Repro:** `probes/repro_displacement.py`, fake provider. `m:job` (the answer, 0.62) has no lexical overlap with the query.
```
## cand
stuffed note sim=None: returned=['m:job']
stuffed note sim=0.66: returned=['x:stuff', 'm:job']
stuffed note sim=0.7:  returned=['x:stuff']          <- answer withheld (still admitted)
stuffed note sim=0.9:  returned=['x:stuff']
## c4 (semantic route on)
0.66 / 0.7 / 0.9:      returned=['x:stuff', 'm:job']
```

**Real model** (`probes/scen2.json`, `compare.py 2`, scenario `stuffing_displacement`). For "Who pays my wages?" the stuffed note scores 0.388 and the job fact 0.326:

| Head | Returned |
|---|---|
| C5 | `['x:stuff']` |
| C4+sem | `['x:stuff', 'h:job']` |

**Severity.** This is not authority: the withheld fact stays in `admitted`. But it gives memory text a lever over what other memories are returned, which is a new integrity surface for the semantic channel. Lexical selection with C4 off already has the same class of lever through the relative BM25 floor. The preregistration lists stuffing as "can compete for selection"; suppressing the true answer goes further than that.

**Fix.** Do not let a single fact set the margin anchor. Options:
- compute `best_similarity` only over facts not already sufficient on lexical grounds;
- use an absolute floor with a capped top-k rather than a relative margin;
- or at minimum, never withdraw a semantic-route candidate whose similarity is above some high absolute bar.

Add a stuffing test in which the stuffed similarity exceeds the answer's.

### F3. SHOULD-FIX: per-recall cost exceeds A7 at modest store sizes

**Where:** `surface._select_returned` → `retriever.similarities`. It makes a **second** embedding of the query (discovery already embedded it), then for every admitted fact a `get_fact`, a sha256, an SQLite select, a row checksum, an unpack and a pure-Python 384-dimension cosine. The lexical route proposes every fact that shares any token, so the admitted set is roughly 75% of the store.

**Repro:** `probes/cost.py <worktree> <n>`. It uses the real pinned model and a warm derived-vector cache, with 30 recalls per row and budget 10, run on this 4-CPU container.

| Facts | Mean admitted | C4+sem p50 / p95 (ms) | C5+sem p50 / p95 (ms) | Δ p50 | Embeds per recall | Time in `similarities` |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | – | 18.5 / 22.2 | 29.4 / 39.3 | +10.9 | 1 → 1.9 | 8.8 ms |
| 200 | 151.9 | 70.9 / 80.0 | 109.7 / 135.7 | **+38.8** | 1 → 2 | 27.4 ms |
| 1000 | 751.8 | 351.6 / 434.7 | 498.7 / 557.9 | **+147.1** | 1 → 2 | 103.5 ms |

- A repeat run gave 200 facts: 71.5 → 108.8 ms and 1000 facts: 336.0 → 477.8 ms.
- The query embedding itself costs about 7.5 ms per recall. The rest grows linearly with the admitted count.
- On the small dev set the runner's p50 moves only from 554 to 568 ms (the runner reopens the handle for every query), which hides this.

**Fix.** Discovery's O(N) scan already computes the query vector and the cosine against every eligible fact. Return or retain that map, or at least the query vector, from `search` for this recall, and reuse it in selection. That also removes F5.

### F4. SHOULD-FIX (test gap) / NOTE (design): the 0.25 absolute floor is below the 0.30 discovery floor

**Effect on abstention:**
- Any semantic-route candidate has similarity above 0.30, which is at least 0.25. So C5+sem never abstains when the route surfaces an admitted fact.
- The 0.25 floor only matters for facts that the **lexical** route proposed, often through function words alone, with similarity in [0.25, 0.30). C4+sem's own route rejected exactly these facts.

**Effect on consistency.** Whether such a fact is scored at all depends on incidental stop-word overlap. Two facts with the same similarity get different outcomes.

**What the tests miss:** `test_a_query_far_from_every_memory_abstains` uses `TAU_ABS − 0.04 = 0.21`. That is below the route floor and below τ, so it passes trivially and never tests the floor where it binds.

**Repro:** `probes/repro_subfloor.py`, fake provider.
```
## cand
Who is my dentist?: sims boss 0.27, cat 0.26 (lexical-only candidates) -> returned=['m:boss', 'm:cat']
Which automobile do we own? vs 'We drive a grey Corolla.' (shares 'we', 0.28)   -> ['m:car']
Which automobile do we own? vs 'Grey Corolla parked outside.' (no shared token, 0.28) -> []
## c4 (semantic route on): all three -> []
```

**Real model:**
- `scen1`: "Which hamster do we have?" → C5 `['h:car', 'h:cat']` (0.274 / 0.271). C4+sem and C4 off both return `[]`.
- `scen3`, which has 20 unanswerable and 15 answerable paraphrase queries over one 15-fact store (`gen_scen3.py`, `score3.py`):

| Configuration | Abstained (of 20 unanswerable) | Exact (of 15 answerable) | Recall | Precision |
|---|---:|---:|---:|---:|
| C4 off | 16 | 4 | 4/17 | 4/5 |
| C4+sem | 10 | 6 | 12/17 | 12/20 |
| C5+sem | 9 | 11 | 13/17 | 13/16 |

C5 is clearly better than C4+sem on answerable queries. It is slightly worse on abstention, for example "Who is my dentist?" → boss and cat at 0.266 / 0.258.

**How the floor was chosen:** the switch to τ_abs = 0.25 came from Erratum 2 (see F7). The conservative first pick was τ_abs = 0.40.

**Fix:**
- Add a test where an admitted lexical-only fact sits in [τ_abs, 0.30) for an unanswerable query, and decide the intended outcome explicitly.
- Consider τ_abs ≥ the route floor, or apply the floor only to route-surfaced candidates, so that whether a fact is selected does not depend on stop-word overlap.

### F5. NOTE: a second provider call means a provider failure after discovery aborts the recall

**Repro:** `probes/repro_failures.py`. The provider raises, returns NaN, or returns a wrong-dimension vector on the *second* embedding of the query.

| Head | Outcome |
|---|---|
| C5 | `RAISED RuntimeError / ValueError` (non-finite / dimension mismatch) |
| C4+sem | `returned=['m:cat', 'm:dog']` |

The recall fails closed: an exception, with no partial or unauthorised output. Provider failure during discovery was already fatal in C4. The difference is that C5 doubles the exposure and the cost.

A query vector that jitters between the two calls (a non-deterministic provider) makes discovery and selection disagree slightly. In the jitter probe the outcome was unchanged.

**Fix:** reuse the discovery query vector (F3).

### F6. NOTE: `plural_answer` false positives and negatives (inert today because of F1; risky if F1 is "fixed" by widening the set margin)

**Repro:** `probes/plural_probe.py ../cand`.

**False positives** (`True` on single-answer questions):
- "Which does Alice prefer, tea or coffee?" ("does" → "doe")
- "Which goes first?" / "Which comes first?"
- "What news did Mom share?"
- "What series am I watching?"
- "Which lens do I use…?"
- "What species is our fish?"
- "Which canvas did I buy?"
- "What are you doing on Friday?"
- "What hours does the gym open?"
- "Which means of transport do I use?"
- "Which glasses case is mine?"

The unit test's "Which bus goes downtown?" passes only because "bus" ends in -us.

**False negatives** (`False` on list questions):
- "Who is in my family?"
- "What do my children like?"
- "Which of my friends live in Paris?"
- "What kind of dogs do I have?"
- "What children/people did I meet…?" and other irregular plurals ("mice", "data")
- "Where are my keys?"
- "Name my siblings." / "Tell me my allergies."
- "Who attended the meeting?"
- "what're my dogs' names?" (the contraction is not expanded here)

**Risk.** It is low today: the reading changes only the `return_policy.semantic_channel.plural_answer` diagnostic, which is therefore misleading. If the set margin is ever widened, each false positive would widen a single-answer question's returned set by the set margin.

**Fix.** Either delete the reading with F1, or require the plural head to be a noun: exclude auxiliaries and verbs after "which", and handle "which of …" and irregular plurals.

### F7. NOTE: calibration honesty. It reproduces exactly and uses dev data only, but Erratum 2 is a post-hoc choice of the most consequential parameter

**What held:**
- `dev/dev-scenarios.json` is byte-identical to the preregistration commit `3509a48a` and regenerates byte-identically from `build_dev_set.py` (sha256 `a1fdb065…`).
- `calibrate.py` reads only that file and reuses the runner's `score`. It contains no references to held-out, LongMemEval or AMB.
- Re-running it from scratch reproduces `calibration.json` exactly (`probes/calibration-rerun.json`: chosen, grid and reference all equal).
- The replay is faithful: the C4-equivalent replay equals my independent runner result for C4+sem (22/48, P 0.6397, R 0.675). The chosen point equals my runner result for C5+sem (27/48, P 0.7149, R 0.775). All four committed dev runs match mine query by query.

**The concern:**
- The preregistration specified no tie-break.
- Erratum 2 changed the tie-break after the first grid result was seen. That moved τ_abs from 0.40 (recall 0.575, mean returned 0.83) to 0.25 (recall 0.775, mean returned 1.21). This is the parameter behind F4.
- Erratum 2 is disclosed in `CALIBRATION.md` and in the `calibrate.py` docstring, but **not** in the PREREGISTRATION errata. The first run's output is not committed.
- Everything stayed on dev data, so there is no leakage. It is a disclosed researcher degree of freedom.

**Fix:** add Erratum 2 to `PREREGISTRATION-C5.md`, state the 0.40 → 0.25 consequence, and commit the first run's chosen point.

**Not verified.** I did not check whether the dev items overlap earlier cohorts, because I was told not to read them.

### F8. NOTE: smaller inconsistencies

- **Missing `semantic_channel`.** `return_policy.semantic_channel` is absent when the semantic route is enabled but nothing was admitted (`repro_failures.py`, "empty store"). The schema description says it is "present only when the optional semantic route is enabled", so consumers cannot tell "route off" from "route on, nothing admitted".
- **Stale docstring.** The `select_relevance_sufficient` docstring still lists "facts a non-lexical route surfaced" as primary evidence and does not mention the semantic bases.
- **Similarities without the route.** `_select_returned` computes similarities whenever a retriever exists, even if `retriever.available_for(substrate)` is false and the route never ran.
- **Topic-dense margin is noise-level.** This boundary was preregistered. `probes/scen4.json` (40 near-identical meeting facts), "When is the next sync about money?" → C5 returns 8, against 6 for C4+sem. The 0.05 cut falls between budget meetings at 0.299 and 0.295, includes vendor-contract meetings and a one-to-one, and leaves out other budget meetings. Small cross-CPU differences in ONNX output can flip such boundary decisions.

---

## What I tried that held

- **Claim 1** (opt-in; only admitted facts are scored; no candidates are added; admission, refusals and ranking are unchanged; route candidates are no longer unconditional):
  - The code path runs only when `self._semantic["retriever"]` is set. `similarities` receives only `result.ranked_admitted` texts. The only caller is `_select_returned`.
  - In every probe set (`scen1`–`scen4`, both modes), C4 and C5 have identical `admitted` lists and order and identical per-candidate route provenance.
  - `records` exist only for admitted refs.
  - The C4+sem bike/cat neighbours are withheld as intended.
- **Claim 2** (route off equals C4):
  - The two code paths are equivalent by construction: reordering the `score <= 0` branch is a no-op when `semantic` is false.
  - Returned lists are identical across all 81 probe queries and all 48 dev queries (my runner re-runs).
  - Focused and selection suites pass: `test_c5_low_overlap_selection`, `test_c4_selection_precision`, `test_evidence_set_selection` and `test_relevance_sufficient_return_selection`, 70 tests OK.
  - `ranked_prefix` with the semantic route on is identical on both heads.
- **Claim 3** (no authority, scope or disclosure path):
  - Forgotten text ("Rex"), corrected-away text ("Corolla"), and other-scope text ("tabby kitten named Rex", "interviewing at Contoso") never appear anywhere in the C5+sem envelopes, with the real model and highly similar queries (`scen2` `governance`, raw JSON scanned).
  - An injected "SYSTEM OVERRIDE" note is returned only where C4 also returns it lexically, and gets no precedence.
  - C5 envelopes validate against `schemas/api-result-envelope.schema.json` (jsonschema Draft 2020-12, 0 errors).
- **Claim 4** (determinism):
  - Two fresh real-model runs produce identical returned lists and records.
  - NaN or wrong-dimension vectors are rejected by `_validated_vector`.
  - A zero query vector abstains on both heads. A zero fact vector gives cosine 0. An empty store gives `[]`.
  - `budget=1` truncates in ranked order on both heads.
  - The derived store keys vectors by (uuid, sha256(text)), so a corrected text never reuses the stale vector.
- **Fail-first tests:**
  - On C4 they fail as preregistered: 5 failures, plus 13 errors because `plural_answer` is absent.
  - The tests were not weakened after preregistration. The only change is the added `PluralAnswerReading` class.
- **Where C5 is better than C4+sem**, on precision against the route-on baseline:
  - "Which medicine do I take each morning?" drops the allergy fact.
  - "Who is my physician?" drops the dentist and the statin.
  - "Who is my heart doctor?" drops the statin.
  - `scen3` answerable precision rises from 12/20 to 13/16, and exact passes from 6/15 to 11/15.
- **Full suite** (`python3 -m unittest discover -s reference/tests -t reference` on `cand`, log in `probes/full-suite-cand.log`):
  - 2665 tests, 36 skipped, **1 failure**: `test_benchmark_integration_contract.test_evaluation_only_change_keeps_runtime_baseline_equivalence`.
  - The failing test reports that the "protected Runtime Baseline source surface" changed since `e98e6e7b` with no successor declared in the register.
  - **This failure is not caused by C5.** The same test fails identically on C4 `bc2be631`, because files changed by earlier candidates are protected too.
  - C5 does add `vector_retrieval.py` to that list. Whoever integrates the candidate stack must declare a register successor.
