# Adversarial review: #819 C6 rank-bounded semantic proposals

- **Candidate:** `80c797d0` (branch `claude/eager-dirac-bftkfg-819-c6`). **Base:** C4 `bc2be631`.
- **Reviewer:** independent; did not write the change.
- **Worktrees (detached, reviewer-created):** `review-c6/cand` (80c797d0), `review-c6/c4` (bc2be631).
- **Not opened:** `heldout-v4-sealed/`, other cohorts, benchmark gold. Every probe and scenario below is reviewer-authored.
- All paths below are relative to `/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-c6/`.
- Real-model runs used `AGENT_MEMORY_REPRESENTATION_DIR=<scratchpad>/representation` and `<scratchpad>/sem-venv/bin/python3`.

## Verdict

**BLOCKING findings: YES (1).**

Finding 1: in explicit historical and as-of recalls, a forgotten, disputed, error-corrected or out-of-window memory takes the single proposal slot. Admission then refuses it, and the true answer is never proposed. C4 returns the answer in every case. This is a deterministic regression in the path the change says it handles ("superseded evidence stays reachable where admission allows it"), and the fix is small.

Beyond that, the evidence does not support calling C6 a **discovery** improvement.
- **Against C4 with the semantic route on:** the gains are almost entirely a precision effect, and C6 loses needed memories that C4 already reached. This holds on the candidate's own development runs and on my unseen set.
- **Against C4 default:** the gain is real, but it comes from turning on the semantic route that C4 already has, not from the new policy.
- **Manipulation:** a single question-shaped or "meta" memory captures the K_single slot and suppresses the true answer. Because the margin is relative to the best match, it can also push real answers out of the K_set window.

## Findings

### 1. BLOCKING: in historical and as-of recall, the single slot goes to a memory admission refuses, and the answer is lost

- **Mechanism.** `runtime_composition.py` (C6 hunk) restricts the dense pool with `discovery_admissible` only when the mode is `current_state`. In historical and as-of mode the pool is merely domain-eligible, so it still contains:
  - tombstoned memories;
  - memories derived from a tombstoned source;
  - disputed memories;
  - `corrected_as_false` (error-correction) originals;
  - state-changed records outside the target window.

  Historical admission refuses every one of these (`adapter._admission_refusal` / `_historical_evidence_refusal`). Under C4 a refused neighbour cost nothing, because up to 16 proposals were made. Under C6, with K_single = 1, the refused memory is the only proposal, and the true answer is never proposed. The `min_best` gate is also evaluated against the refused memory's cosine.
- **Reproduction:** `tools/probe_fake.py` (fixed-cosine fake provider, patched as in the tests).
  `<sem-venv>/bin/python3 tools/probe_fake.py cand` and `... c4`. Output is in `out-fake-cand.txt` and `out-fake-c4.txt`.

| Probe | Setup | C6 | C4 + semantic |
|---|---|---|---|
| H1 | Forgotten "Our old beagle used to hide from thunder." (cos 0.90) and live answer (0.70); `temporal_intent={"mode":"historical"}` | `historical: []`; semantic `[old 0.9 tombstoned]` | `historical: ["a"]` |
| H2 | Error-corrected original (0.90) and correction (0.70); historical | `[]`; semantic `[job-orig corrected_as_false]` | `["job-fixed"]` |
| H3 | State change Leeds → York (valid_from 2024); `as_of` 2025-06 | `[]`; semantic `[home-leeds outside_historical_validity]` | `["home-york"]` |
| H4 | Disputed memory (0.90) and answer (0.70); historical | `[]`; semantic `[bad disputed]` | `["good"]` |

The same queries in current-state mode are correct on C6, because the pool restriction applies there.

- **Why the tests miss it.** `test_c6_semantic_discovery.py` has no historical or as-of case. The superseded-statement test is current-state only.
- **Suggested fix:**
  - **Preferred.** In every mode, filter the dense pool with the mode-aware admission predicate, i.e. `adapter._admission_refusal(fact, context, mode, target_seconds) is None` or a public wrapper of it. The fact object is already in hand in `search()`. Do this before ranking and the `min_best` and margin tests.
  - **At minimum.** Always apply the mode-independent refusals: tenant, tombstone, derived-from-tombstone, dispute and domain. In historical mode, also drop `event_invalid` facts whose replacement record is an error correction or lies outside the target window.
  - **Tests.** Add H1–H4 as fail-first tests.

### 2. SHOULD-FIX (high): one question-shaped or meta memory captures the slot and suppresses the answer, so C6 is easier to manipulate than C4

- **Reproduction (real pinned model):** `tools/repro_stuffing.py` (`<sem-venv>/bin/python3 tools/repro_stuffing.py cand|c4`). Output is in `out-stuffing.txt`.
- **Store.** Seven ordinary memories, plus two natural-sounding meta notes: "I keep forgetting who my doctor is." and "Asked which pets we have and what the pets eat."

| Query | Store | C6 returned | C4 + semantic returned |
|---|---|---|---|
| Who is my doctor? | Without meta notes | `gp` | `gp` |
| Who is my doctor? | With meta notes | **`stuff-doc` only** (0.728; gp 0.542 not proposed) | `stuff-doc, gp` |
| Which pets do we have? (plural, K_set = 3) | With meta notes | **`stuff-pets` only** (0.704; dog 0.35 is below the 0.504 margin floor) | `stuff-pets, dog` |
| What do the pets eat? | With meta notes | **`stuff-pets` only** | `stuff-pets, petfood, dog` |

- **Impact on the full set.** In my 5-query stuffing scenario (`adv` vs `advctl` in `gen.json`), C6 returns **0 of 6** needed memories with the meta notes present and 3 of 6 without them. C4 with the semantic route returns 3 of 6 in both cases.
- **Two levers:**
  - K_single = 1 means the highest-cosine memory wins outright.
  - The margin is relative to the best match, so one very close memory raises the floor and excludes real answers even for K_set questions.
- **The preregistered test is vacuous.** "An injected or stuffed memory gains nothing beyond its rank" uses an injected memory at cosine 0.10. It never tests a stuffed memory that *has* rank 1.
- **Suggested fix:**
  - Do not let a single proposal be the only path. For example, keep K_single ≥ 2 when the second-best is within a tight margin, or compute the margin from the second-best.
  - Optionally demote question-form or self-referential memory text ("I keep forgetting…", "Asked…") as candidates for the slot. This would be a closed grammar, like `plural_answer`.
  - At minimum, add a real-rank stuffing test and state the suppression risk in docs/44.

### 3. SHOULD-FIX: the "discovery" claim is not supported; against C4 with the semantic route, the gain is a precision effect

I decomposed per-query results into needed memories newly reached and strict wins with unchanged needed-memory coverage.

| Data | Needed memories C6 reaches that C4+sem does not | Needed memories C4+sem reaches that C6 loses | Strict wins over C4+sem | …of which needed coverage is identical (pure suppression of extras) |
|---|---:|---:|---:|---:|
| Candidate's own dev runs (`dev/runs/C6-sem-*`, `C4-sem-*`) | **2** (diag health-1 med3, c5 he-1 med2) | **8** | 14 | **13** |
| Reviewer's unseen set (`gen.json`, 55 queries) | **0** | **9** | 11 | **11** |

- **The new reach mechanism rarely fires.** The mechanism is "a top-ranked neighbour below 0.30 becomes reachable". It accounts for 2 memories on dev, both on medication queries that were classified plural only by `plural_answer`, and for none on my set.
- **Recall against C4 with the semantic route falls on both sets:** 0.628 → 0.551 on dev, 0.655 → 0.500 on mine. The preregistration's own expected observable ("against C4 with the semantic route on, recall stays the same or rises") is falsified. CALIBRATION-AND-RESULTS presents this as a trade-off and does not record it as a failed prediction.
- **Against C4 default the gain is real.** On my set: strict 16 vs 11, needed recall 0.500 vs 0.276, extras 61 vs 53. It is reached entirely through the semantic route that C4 already ships (C4+sem reaches a superset of C6's needed memories). G1 (recall vs C4 default) therefore measures "semantic route on vs off", not C6.
- **Suggested fix:**
  - Re-describe C6 as a precision or bounding control for the semantic route.
  - Report "needed recall vs C4+sem" and the decomposition above as headline numbers.
  - Record the failed preregistered expectation explicitly.

### 4. SHOULD-FIX: the policy also changes `ranked_prefix` when the semantic route is on, and the semantic posture still reports the old floor and cap

- **The policy reaches `ranked_prefix`.** The policy is applied in the shared planner, so `recall(..., return_selection="ranked_prefix")` with the semantic route on gets at most 1–3 semantic candidates instead of up to 16.
  - Fake provider (`probe_fake.py` H6): five semantic-only facts give C4 `ranked_prefix = [h0..h4]` and C6 `[h0,h1,h2]`.
  - Real model on my set: recall@10 under `ranked_prefix` falls from 0.707 (C4+sem) to 0.621 (C6+sem). Runs: `runs-gen-{cand,c4}-rp.json`.
  - docs/44 describes `ranked_prefix` as "exactly the 1.4.0 ranked prefix" for rank-depth consumers.
- **The posture is stale.**
  - `semantic_retrieval_posture()` still reports `minimum_similarity: 0.3` and `candidate_limit: 16`. Neither is applied any more (with a policy, the floor is skipped and the effective cap is 1 or 3).
  - The deferred LongMemEval `agent-memory-semantic-route` row (`longmemeval-s-retrieval-parity-v4.json`) declares `minimum_similarity 0.3, candidate_limit 16`, recalls at `budget=50` with the ranked prefix, and the importer checks posture equality.
  - So a C6 run would pass the posture check while its recall@50 semantic depth had been cut from 16 to 1–3.
- **Suggested fix:**
  - Either apply the policy only under `relevance_sufficient` (gate it the way `discovery_expansion` is gated), or declare the `ranked_prefix` change in docs/44 and the lane.
  - Have the posture report the effective floor (none) and cap (policy K), or make the importer check `proposal_policy`.

### 5. SHOULD-FIX: `plural_answer` decides K but misreads common aggregate phrasings, including the diagnosis's own headline example

**Reproduction** (inline, cand tree): `python3 -c "from agentmem_ref.runtime.vector_retrieval import RankBoundedProposalPolicy as P; print(P().limit('Which animals live with us?'))"` prints `1`.

**Gets K = 1 although several answers are wanted:**
- "Which animals live with us?" (the DIAGNOSIS example, and dev queries diag pets-1 and c5 hh-2);
- "Who do I work with?";
- "Which people did I meet at the conference?";
- "Which of my friends live in Berlin?";
- "What did we buy for the house?";
- "Remind me of the things I need to pack.";
- "What do I take for my allergies and my blood pressure?";
- "Any allergies I should know about?".

**Gets K = 3 for non-aggregates:** "Who are you?", "What are the odds?", "What are my dog's name?".

**Dev-set dependence.** The only two dev needed memories that C6 newly reaches (finding 3) come from queries classified plural by `plural_answer` alone. `plural_answer` was authored on the C5 calibration set, which is half of the C6 development union.

**Suggested fix:** treat K as a recall-safety parameter, not a precision one. Use K_set as the default and K_single only for queries positively read as single-answer (copula singular, "what is my X"). Or accept and document the coverage gap.

### 6. SHOULD-FIX: the `min_best` = 0.40 gate drops genuine answers that sit in the model's normal 0.32–0.40 band

On my set, these answers were returned by C4+sem and dropped by C6 because the best cosine was below 0.40:
- knee for "Do I have any injuries?" (0.323);
- sleep for "Why am I so tired lately?" (0.396);
- commute for "How do I get to work?" (0.331);
- dog for "Which pets do we have?" (0.35);
- sub-news (0.400).

**Calibration is knife-edged.** On the dev grid, the best strict at `min_best` 0.35, 0.40 and 0.45 is 38, 40 and 36.

**On my set the constants roughly transfer** (`tools/sens.py`, `sens-*.json`):

| min_best | K_single | Strict | Needed recall | Extras |
|---|---|---|---|---|
| 0.30 | 1 | 15 | 0.569 | 70 |
| 0.35 | 1 | 16 | 0.534 | 66 |
| 0.40 | 1 (chosen) | 16 | 0.500 | 61 |
| 0.40 | 2 | 11 | 0.517 | 70 |
| 0.45 | 1 | 15 | 0.431 | 57 |

The strict objective is flat, and recall is what pays.

**Suggested fix:** report recall loss against `min_best` alongside strict, and consider gating on best-minus-median contrast rather than an absolute cosine.

### 7. NOTE: shadow recall-control now labels almost every semantic recall a resource stop

- `_shadow_recall_control` sets the host cap to `policy.limit(query)`. For a single-answer query with one proposal, `route_counts[semantic] = 1 >= cap = 1`, so the report says `max_candidates` / `resource`.
- C4 said `frontier_exhausted` / `search_space` for the same retrieval (`probe_fake.py` H9).
- The policy's choice is not a resource bound, so this telemetry change misleads.
- **Suggested fix:** keep the cap at `SEMANTIC_CANDIDATE_LIMIT` and report the policy separately. Or add a `policy_bound` stop reason.

### 8. NOTE: calibration record details

- **Grid size.** The preregistered grid is 3 × 4 × 4 × 4 = 192 points. `calibrate.py` silently drops the 16 points with K_set < K_single and runs 176. This is benign, but it was not preregistered.
- **Objective and tie-break** were applied as preregistered. (1, 3, 0.20, 0.40), (1, 4, 0.20, 0.40) and (1, 6, 0.20, 0.40) tie on strict, recall and extras, and the smallest K_set is chosen. Calibration and gate use the same 78 queries, which the record states.
- **Weak abstention bound.** G4 ("no-answer queries returning anything ≤ C4+sem") is weak, because C4+sem fails 7 of 8. Against C4 default, C6 is worse (4 vs 3).
- **Stale file name.** The code comment in `vector_retrieval.py` cites `CALIBRATION.md`. The file is `CALIBRATION-AND-RESULTS.md`.

### 9. NOTE (pre-existing on both heads): a provider failure at query time is not degraded in `auto` mode

- `tools/probe_failure.py`: a provider that opens fine and then raises `RepresentationUnavailable` during `recall` propagates the exception in both `auto` and `required`, on C6 and on C4.
- The preregistration says "a provider failure or unavailable inference leaves lexical recall working (auto mode)". The test only covers failure at open.
- This is not a C6 regression, but the preregistered claim is broader than its test.

## Reviewer generalisation scenarios (unseen by calibration)

**Set.** `tools/build_gen.py` → `gen.json`: 7 stores of 28–33 memories each, with 55 queries. Domains are finance, school and family, car and commute, kitchen, fitness and health, plus a stuffing store and its control.

**Query kinds:**
- paraphrase;
- aggregate and list;
- distractor;
- no-answer;
- governance (superseded by correction, forgotten);
- historical (`temporal_intent`);
- stuffing.

**Harness.** `tools/harness.py <tree> gen.json <off|required> out.json`, through the public facade, with budget 10.

**Scoring.** A query passes when every `must_include` is returned, no `must_exclude` is returned, and returned ⊆ must ∪ may.

| Configuration | Strict (of 55) | Needed recall | Extras | No-answer queries returning something (of 11) | Safety violations |
|---|---:|---:|---:|---:|---:|
| C4 default (route off) | 11 | 0.276 | 53 | 8 | 0 |
| C4 + semantic | 6 | 0.655 | 120 | 10 | 0 |
| **C6 + semantic** | **16** | 0.500 | 61 | 8 | 0 |
| C6, route off | 11 | 0.276 | 53 | 8 | 0 (returned lists identical to C4 on all 55) |
| C6 + semantic, second run | 16 | 0.500 | 61 | 8 | 0 (identical lists and proposals: deterministic) |
| C6 + semantic, `ranked_prefix` | 1 | 0.621 | 369 | 11 | 0 |
| C4 + semantic, `ranked_prefix` | 1 | 0.707 | 386 | 11 | 0 |

**Paired strict:**
- C6 vs C4 + semantic: +11 / −1 (regression: fit-4).
- C6 vs C4 default: +6 / −1 (regression: fit-2).

### Per case

Cell format is `P` (pass) or `-` (fail), then needed returned / needed, then `x` and the number of extras. The last column lists what C6 returned, with each item's route: (s) for semantic, (l) for lexical only.

| id | kind | query | C6+sem | C4+sem | C4 default | C6 returned (route) |
|---|---|---|---|---|---|---|
| fin-1 | aggregate | What subscriptions am I paying for? | - 0/4 x0 | - 1/4 x1 | - 0/4 x0 | (none) |
| fin-2 | aggregate | What do we spend money on every month? | - 1/4 x1 | - 1/4 x1 | - 0/4 x0 | groceries(s), fin-n15(s), isa(s) |
| fin-3 | paraphrase | Who does our taxes? | - 0/1 x0 | - 0/1 x0 | - 0/1 x0 | (none) |
| fin-4 | paraphrase | When does the fixed rate on the house loan end? | P 1/1 x0 | - 1/1 x3 | P 1/1 x0 | mortgage(s) |
| fin-5 | paraphrase | How much does my employer put into my retirement savings? | - 1/1 x1 | - 1/1 x1 | - 1/1 x1 | pension(s), isa(l) |
| fin-6 | no-answer | What is my credit card limit? | P 0/0 x0 | - 0/0 x1 | P 0/0 x0 | (none) |
| fin-7 | no-answer | How much did the kitchen extension cost? | - 0/0 x1 | - 0/0 x1 | - 0/0 x1 | sub-news(l) |
| fin-8 | aggregate | Which insurance policies do we have? | - 1/2 x1 | - 1/2 x0 | - 1/2 x0 | home-ins(s), sub-cloud(s) |
| fin-9 | distractor | Are the bikes insured? | - 1/1 x1 | - 1/1 x1 | - 1/1 x1 | home-ins(s), mia-bike(l) |
| fam-1 | governance | Who teaches Mia? | - 1/1 x5 | - 1/1 x6 | - 1/1 x5 | mia-pickup(l), mia-gym(l), mia-school(l), mia-friend(l), mia-teacher-new(s), mia-allergy(l) |
| fam-2 | paraphrase | What instruments does Leo play? | - 1/1 x1 | - 1/1 x5 | - 1/1 x3 | leo-school(l), leo-band(s) |
| fam-3 | aggregate | What after-school activities do the kids do? | - 0/2 x0 | - 0/2 x0 | - 0/2 x0 | (none) |
| fam-4 | paraphrase | Is there any food Mia must avoid? | - 1/1 x5 | - 1/1 x5 | - 1/1 x5 | mia-school(l), mia-friend(l), mia-pickup(l), mia-gym(l), mia-allergy(s), mia-teacher-new(l) |
| fam-5 | paraphrase | How does Leo get to school? | - 0/1 x2 | - 1/1 x5 | - 0/1 x1 | fam-n0(l), leo-school(l), leo-tutor(s) |
| fam-6 | paraphrase | Who are Leo's friends? | - 1/1 x4 | - 1/1 x6 | - 0/1 x2 | blazer(l), mia-friend(l), leo-friends(s), leo-school(s), leo-band(s) |
| fam-7 | no-answer | What did Mia get on her spelling test? | - 0/0 x2 | - 0/0 x7 | - 0/0 x2 | fam-n0(l), mia-teacher-new(s) |
| fam-8 | no-answer | When is the school trip to the zoo? | - 0/0 x1 | - 0/0 x7 | - 0/0 x1 | fam-n13(l) |
| fam-9 | governance (forgotten) | Does Leo have a mobile? | - 0/0 x6 | - 0/0 x6 | - 0/0 x6 | leo-tutor(l), leo-school(s), leo-bus(l), leo-band(l), leo-friends(l), blazer(l) |
| car-1 | governance (superseded) | What vehicle do we own? | P 1/1 x0 | - 1/1 x2 | - 0/1 x0 | car-model-new(s) |
| car-2 | paraphrase | Who services the car? | - 1/1 x3 | - 1/1 x4 | - 0/1 x3 | car-ins(l), parking(l), garage(s), car-n0(l) |
| car-3 | paraphrase | What happens if we break down on the motorway? | - 0/1 x1 | - 0/1 x1 | - 0/1 x1 | mpg(s) |
| car-4 | paraphrase | How do I get to work? | - 0/1 x2 | - 1/1 x2 | - 0/1 x2 | car-n4(l), charger(l) |
| car-5 | lexical | How much is parking at the station? | P 1/1 x0 | - 1/1 x3 | P 1/1 x0 | parking(s) |
| car-6 | no-answer | What is the car's registration number? | - 0/0 x2 | - 0/0 x3 | - 0/0 x2 | car-ins(l), parking(l) |
| car-7 | no-answer | How much did the Brompton cost? | - 0/0 x2 | - 0/0 x2 | - 0/0 x2 | bike(l), parking(l) |
| car-8 | historical | Which car did we have before? | - 1/1 x2 | - 1/1 x2 | - 0/1 x2 | car-ins(s), parking(l), car-model(s), car-model-new(s) |
| car-9 | aggregate | What do we pay to cover the car? | P 2/2 x0 | - 2/2 x2 | P 2/2 x0 | breakdown(l), car-ins(s) |
| adv-1 | stuffing | Who is my employer? | - 0/1 x2 | - 0/1 x3 | - 0/1 x2 | stuff-work(s), stuff-work2(l) |
| adv-2 | stuffing | Where do I work? | - 0/1 x2 | - 0/1 x3 | - 0/1 x2 | stuff-work(s), stuff-work2(l) |
| adv-3 | stuffing | Which pets do we have? | - 0/2 x1 | - 1/2 x2 | - 0/2 x1 | stuff-pets(s) |
| adv-4 | stuffing | Who is my doctor? | - 0/1 x1 | - 1/1 x3 | - 0/1 x1 | stuff-doc(s) |
| adv-5 | stuffing | What do the pets eat? | - 0/1 x1 | - 1/1 x3 | - 0/1 x1 | stuff-pets(s) |
| advctl-1 | control | Who is my employer? | - 0/1 x0 | - 0/1 x1 | - 0/1 x0 | (none) |
| advctl-2 | control | Where do I work? | - 0/1 x0 | - 0/1 x1 | - 0/1 x0 | (none) |
| advctl-3 | control | Which pets do we have? | - 1/2 x1 | - 1/2 x1 | - 0/2 x0 | advctl-n16(s), dog(s) |
| advctl-4 | control | Who is my doctor? | P 1/1 x0 | - 1/1 x1 | - 0/1 x0 | gp(s) |
| advctl-5 | control | What do the pets eat? | P 1/1 x0 | - 1/1 x2 | P 1/1 x0 | petfood(s) |
| home-1 | aggregate | What dietary restrictions should I plan for at the dinner party? | - 1/3 x2 | - 1/3 x2 | - 0/3 x1 | party(s), home-n13(l), home-n0(s), ines-veg(s) |
| home-2 | paraphrase | Does anyone avoid meat? | P 1/1 x0 | P 1/1 x0 | - 0/1 x0 | ines-veg(s) |
| home-3 | lexical | What's the name of the bread starter? | P 1/1 x0 | P 1/1 x0 | P 1/1 x0 | starter(s) |
| home-4 | paraphrase | Is the oven accurate? | P 1/1 x0 | - 1/1 x1 | P 1/1 x0 | oven(s) |
| home-5 | paraphrase | What should I cook that everyone loves? | - 0/1 x2 | - 1/1 x5 | - 0/1 x1 | starter(l), knife(s) |
| home-6 | no-answer | What is Sam's favourite dessert? | - 0/0 x2 | - 0/0 x5 | - 0/0 x1 | fav-dish(l), sam-spice(s) |
| home-7 | no-answer | When was the fridge bought? | - 0/0 x1 | - 0/0 x3 | - 0/0 x1 | starter(s) |
| home-8 | paraphrase | Who gave us the knife? | P 1/1 x0 | - 1/1 x1 | P 1/1 x0 | knife(s) |
| home-9 | paraphrase | What drinks do people like? | - 1/1 x1 | - 1/1 x2 | - 1/1 x1 | wine(l), party(l) |
| fit-1 | aggregate | What medications am I on? | - 1/2 x0 | - 1/2 x0 | - 0/2 x0 | med-bp(s), vit-d(s) |
| fit-2 | aggregate | What do I take every day? | - 1/1 x1 | - 1/1 x1 | P 1/1 x0 | med-bp(s), vit-d(s), physio(s) |
| fit-3 | paraphrase | Which race am I preparing for? | P 1/1 x0 | P 1/1 x0 | - 0/1 x0 | race(s) |
| fit-4 | paraphrase | Do I have any injuries? | - 0/1 x0 | P 1/1 x0 | - 0/1 x0 | (none) |
| fit-5 | paraphrase | When do I see the physiotherapist? | P 1/1 x0 | - 1/1 x1 | - 0/1 x0 | physio(s) |
| fit-6 | no-answer | What is my resting heart rate? | P 0/0 x0 | - 0/0 x1 | P 0/0 x0 | (none) |
| fit-7 | no-answer | How much do I weigh? | P 0/0 x0 | P 0/0 x0 | P 0/0 x0 | (none) |
| fit-8 | paraphrase | Who is my doctor? | P 1/1 x0 | P 1/1 x0 | - 0/1 x0 | gp(s) |
| fit-9 | paraphrase | Why am I so tired lately? | - 0/1 x1 | - 1/1 x1 | - 0/1 x1 | fit-n18(l) |

**Reading.**
- **C6 is the best of the three on strict.** On no-answer queries it matches C4 default (8 of 11 return something) and beats C4+sem (10 of 11).
- **Against C4+sem, every strict gain is precision.** C6 reaches no needed memory that C4+sem misses, and it loses 9.
- **Against C4 default:** C6 adds 13 needed memories for 8 more extras.
- **Abstention.** C6 returns a semantic non-answer on 4 no-answer queries: fam-7, fam-9, home-6 and home-7.
- **Aggregates stay weak under all three:** 1 of 8, 0 of 8 and 2 of 8.

## Performance (`tools/perf.py`, real model, 30 queries, OMP_NUM_THREADS = 2, two runs each)

| Store | C6 + semantic p50 / p95 (CPU p50), ms | C4 + semantic p50 / p95 (CPU p50), ms |
|---|---|---|
| 200 memories | 61.1 / 67.6 (59.8); 57.5 / 72.2 (55.0) | 53.1 / 66.1 (51.9); 57.3 / 68.7 (56.5) |
| 1,000 memories | 271.2 / 347.2 (269.3); 244.5 / 310.7 (241.2) | 271.3 / 327.9 (264.7); 231.0 / 279.8 (229.7) |

C6 now builds a `VectorCandidateHit` for every in-scope fact, because no floor is applied before the sort. It adds 0–14 ms at p50, which is within run-to-run noise. Recall stays O(N), at about 0.25 ms per memory, the same as C4. G7 holds.

## What I tried that held

- **Current-state governance:**
  - forgotten, superseded (corrected), disputed, other-scope and other-tenant memories at the top cosine never reach the caller, and never take the slot (`probe_fake.py` H1–H4 current, H8; gen fam-9, car-1, fit-1);
  - no text from refused memories appears in the result;
  - C6 also stops listing tombstoned memories as refused semantic candidates (C4 did, for example `leo-phone` in fam-5).
- **No admission bypass.** Proposals still enter `admit_preselected_candidates`, and the pool restriction only removes. Admission, ranking and selection code are untouched.
- **Route off:** returned lists are identical to C4 on all 55 reviewer queries. The candidate reports the same on its 78 dev queries.
- **Determinism:** two full runs gave identical returned lists and identical semantic proposals. An exact cosine tie (H5) resolved identically across 8 fresh stores.
- **Empty and forgotten-only stores:** recall returns `[]` without error in current and historical mode (H7).
- **Provider unavailable at open:** `auto` falls back to lexical and `required` refuses at open, as before (C6 tests). Query-time failure is the pre-existing gap in finding 9.
- **Test suite on the candidate (one full run, real model provisioned):** 2,641 passed, 5 failed, 31 skipped. All C6 tests pass (12 of 12), and 5 of them fail on C4 as preregistered.
  - **Same failures on C4.** I re-ran the five failing tests on C4 and they fail the same way:
    - the gauntlet golden path, durability and external-example tests stop at "adapter process exited / closed stdout";
    - the keyed-rebinding test reports a missing `reference/fixtures/harvest-closeout-wave2.json`;
    - `test_evaluation_only_change_keeps_runtime_baseline_equivalence` reports that the protected Runtime Baseline surface is changed with no declared successor.
  - **Environmental or lineage-level.** None of these is caused by C6.
  - **Integration note.** On C6 the baseline-equivalence failure also lists `runtime/vector_retrieval.py`, so the integration handoff must cover it.
- **Calibration bookkeeping:** the chosen point and tie-break are reproduced from `dev/calibration.json`. The C4-semantic reference (strict 30) matches the separate C4 run.

## Reproduction index

| File (under `review-c6/`) | Purpose |
|---|---|
| `tools/probe_fake.py <tree>` | Fixed-cosine probes H1–H9 (historical, as-of, disputed, ties, `ranked_prefix`, empty store, cross-scope, shadow stop) |
| `tools/repro_stuffing.py <tree>` | Real-model meta-note slot capture |
| `tools/build_gen.py`, `gen.json` | Reviewer scenario set |
| `tools/harness.py <tree> gen.json <off\|required> out [--selection ranked_prefix]` | Facade runner with route provenance |
| `tools/decompose.py`, `tools/table.py` | Discovery-vs-suppression decomposition and the per-case table |
| `tools/sens.py` | Policy-constant sensitivity on the reviewer set |
| `tools/perf.py <tree> <N>` | Latency and CPU |
| `tools/probe_failure.py <tree>` | Query-time provider failure |
| `out-*.txt`, `runs-gen-*.json`, `sens-*.json`, `perf-*.txt` | Observed outputs |
