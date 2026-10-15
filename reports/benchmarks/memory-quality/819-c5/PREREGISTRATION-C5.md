# #819 C5 preregistration: recover low-overlap evidence without reintroducing noise

This file was committed before any C5 runtime change. The calibration development set and the fail-first tests were committed with it, and the sealed held-out cohort's hash was committed before the freeze (`HELDOUT-V4-SEAL.md`).

## Baseline

| Item | Value |
|---|---|
| C4 runtime (frozen, unchanged) | `bc2be6319a3eda96731fdb235f4feba882bcb9be` (selection policy 2.3.0) |
| C5 branch | `claude/eager-dirac-bftkfg-819-c5`, based on C4 evidence head `9942a8a6`; runtime tree identical to `bc2be631` |
| Immutable comparators | A `1df28f84`, C1 `4bd38e6c`, C2 `eaf60e4d`, C3 `6a2255c0`, C4 `bc2be631` |
| Stable default | `return_selection="ranked_prefix"` is untouched. `relevance_sufficient` stays opt-in. The semantic route stays off by default. |

## The defect

The independent C3 review (`claude/819-independent-evaluation-no-ci`, `REVIEW-C3.md`; aggregates only, no hidden content read) reported three failures:
- multi-evidence aggregation: 0/16 strict against A's 8/16;
- paraphrase recall: 0.25 against A's 1.0;
- empty returns where wording does not overlap.

C4 does not change this mechanism.

**Stage attribution.** This is from source, and from C4 runs on the self-authored dev set (`dev/`, 48 queries):

1. **Discovery is mostly not the cause in ordinary stores.** The lexical route proposes every fact that shares *any* token with the query, function words included (C2 docstring, `return_selection.py`). Governed admission then admits it, and A's ranked prefix returns it.
   - In large stores a fact with no shared token is not discovered unless the semantic route is on. That route proposes the top 16 by cosine similarity, above 0.30.
2. **Selection is the cause.**
   - A fact's topical BM25 must reach 0.5 × the best match (0.25 × for aggregate questions).
   - When the query's topical terms match nothing, the recall abstains (`return_selection.py`, the `reading.topical_terms` branch).
   - A paraphrase, or an aggregate member worded its own way, has zero or low topical BM25, so it is withheld, or the whole recall abstains.
3. **The existing semantic route bypasses selection.**
   - Any candidate a non-lexical route surfaced is `non_lexical_route_evidence`, sufficient with no calibration.
   - Enabling the route therefore returns every vector neighbour above 0.30. Its 0.30 discovery floor also misses weaker aggregate members (pinned model: "Which pets do we have?" → beagle 0.40, tabby 0.27, car 0.14).
4. **C4 on the dev set:**

   | Configuration | Strict | Precision | Recall | Mean returned |
   |---|---:|---:|---:|---:|
   | Semantic route off | 16/48 | 0.54 | 0.26 | 0.56 |
   | Semantic route on | 22/48 | 0.64 | 0.68 | 1.23 |

Lexical evidence alone cannot tell "nothing relevant" from "relevant but worded differently". Any lexical-only fallback either keeps abstaining or returns noise. The generalised fix therefore needs a semantic signal. The repository already has one: the local, pinned, offline ONNX sentence-embedding route (#669), which is governed (candidates still pass admission), optional and off by default.

## Hypothesis and mechanism (selection policy 2.4.0, opt-in)

**H1.** Use a calibrated semantic-relevance channel *inside* selection. Do not admit vector neighbours unconditionally, and do not lower the lexical floor. This recovers paraphrased and aggregate evidence while keeping C4's precision on everything else.

Mechanism:

1. **Semantic relevance (only when the handle's semantic route is enabled and healthy).** Selection receives the cosine similarity between the query and each *ranked admitted* candidate's text.
   - The vectors come from the existing derived vector store (`vector_for`; derived data, never authority).
   - No candidate is added, admission is unchanged, and refused, withheld and other-scope facts are never embedded or scored.
2. **Semantic-route candidates lose unconditional sufficiency.** A fact the semantic route surfaced is sufficient only through the semantic floors below. Relational and exact-identity routes keep C4's treatment.
3. **Primary semantic evidence:** `sim ≥ τ_abs` and `sim ≥ best_sim − δ_single`.
4. **Set evidence (aggregate or relational reading only):** `sim ≥ τ_set` and `sim ≥ best_sim − δ_set`.
5. **Abstention rests on positive evidence of irrelevance.**
   - With the channel available, a recall with no lexical primary evidence abstains only when `best_sim < τ_abs`.
   - Lexical abstention ("the topic matched nothing") no longer decides alone.
6. **Everything else is C4.** Lexical primary and set evidence, ranking consistency, entity coverage and lifecycle closure are unchanged.
7. **Semantic route off or unavailable:** returns are byte-identical to C4 (policy 2.3.0 behaviour). Only the recorded policy version differs.
8. **Diagnostics.** Each admitted fact's record adds `semantic_similarity` and the bases `semantic_relevance` and `semantic_set_evidence`. Only admitted facts are named.

**Calibration.** `τ_abs`, `τ_set`, `δ_single` and `δ_set` are chosen on the self-authored dev set (`dev/dev-scenarios.json`, committed here before calibration):
- by grid search that maximises dev strict pass;
- subject to dev precision ≥ C4-semantic-on dev precision − 0.05;
- within the grid τ ∈ {0.20, 0.25, …, 0.50} and δ ∈ {0.05, 0.10, …, 0.30}.

The chosen values and the full grid are recorded before the freeze. No LongMemEval, AMB or sealed-cohort label is used.

## Fail-first tests (`reference/tests/test_c5_low_overlap_selection.py`)

These are newly authored synthetic examples. A deterministic offline representation fixes the geometry, so they test selection logic, not the model. They must fail on C4 and pass on C5:

1. a zero-overlap paraphrase is returned, not abstained;
2. every aggregate member above the set floor is returned, and a same-store distractor is not;
3. a single-answer topical distractor below the margin is withheld;
4. a query semantically far from everything abstains;
5. a semantic-route neighbour below the floors is withheld (C4 returned it);
6. with the semantic route off, returns equal C4's on the same stores.

Plus governance, which must hold on both C4 and C5:
- forgotten, other-scope and corrected-away text is never returned, however similar;
- injected "SYSTEM" text and keyword stuffing earn no special treatment;
- diagnostics never name a non-admitted fact.

## Sealed held-out cohort (v4)

- **Author.** A separate agent that sees only the runner's input format (`scripts/run_memory_quality_scenarios.py`, lines 1–140). It does not see runtime code, tests, reports, the dev set or earlier cohorts.
- **Categories.** paraphrase, aggregate_list, low_overlap_support, topical_distractor, abstention, adversarial_text, correction_currentness, forgetting_scope, ordinary.
- **Seal.** The hash is committed before the C5 freeze. The cohort is read and run once per candidate only after the freeze.
- **Evaluation-only runner change, made before the seal.** `--semantic-retrieval {off,auto,required}`, the same file for every system, and acceptance of a bare scenario list.

## Comparisons (one run each on v4, after the freeze)

| Label | Revision | Semantic route |
|---|---|---|
| A | `1df28f84` | off |
| C2 | `eaf60e4d` | off |
| C4 | `bc2be631` | off |
| C4+sem | `bc2be631` | `required` (pinned MiniLM, the same model directory) |
| C5 | frozen C5 | off (must equal C4) |
| C5+sem | frozen C5 | `required` |

**Measured:**
- strict pass, precision, recall and mean returned count;
- by category: paraphrase reachability (paraphrase recall), aggregate completeness (aggregate_list recall and strict), correction and currentness, abstention, forgetting and scope;
- safety violations;
- recall latency p50/p95 and CPU per recall;
- paired exact McNemar with bootstrap 95% CIs (10,000 resamples, seed 819).

## Acceptance (C5+sem against C4 default, with C4+sem as the ablation)

- **A1.** Paraphrase recall and aggregate_list recall each improve by at least +0.15 absolute.
- **A2.** Overall strict pass improves, paired McNemar p < 0.05.
- **A3.** Mean precision drops by at most 0.05, and mean returned count is at most 1.5× C4's.
- **A4.** The abstention and topical_distractor categories each lose at most 2 strict passes.
- **A5.** Zero safety violations.
- **A6.** C5 with the semantic route off returns the same lists as C4 on every v4 query and on both LongMemEval planes.
- **A7.** Recall latency p50 overhead is at most 25 ms against C4+sem.

**Recommendation rule:**
- All met → **opt-in qualified** (the semantic route plus `relevance_sufficient`, explicitly enabled).
- A5 or A6 fails → **reject**.
- Otherwise → **changes required**, with the failing criteria named.

An improvement that comes from returning many unrelated facts (A3) or from unauthorised evidence (A5) is a rejection, whatever the strict score.

## Stop conditions

- **Calibration stop.** If no grid point reaches dev paraphrase-and-aggregate recall ≥ 0.70 while keeping dev precision ≥ C4+sem − 0.05, implementation stops. The negative result is recorded, and nothing is frozen as C5.
- **Review stop.** If adversarial review finds an authority, scope or disclosure path, the candidate is not frozen until it is fixed.

## Failure boundaries (expected limits, recorded in advance)

- The model's similarity ranges for "paraphrase" and "same-topic distractor" overlap, so single-answer precision on topic-dense stores may fall.
- Multi-hop bridging and zero-overlap facts outside the vector route's discovery reach are not addressed.
- English-only cue lists, and the pinned model's language coverage.
- Keyword or paraphrase stuffing by memory text can raise similarity just as it raises BM25; text grants no authority, but it can compete for selection.
- Gains need the optional model files (`agent_memory.runtime.representation_onnx fetch`, an explicit network step) and `onnxruntime`, `tokenizers` and `numpy`.

## Diagnostic sets (not pristine)

LongMemEval-S (native runner, both planes) and AMB are diagnostic regression checks only. Their gold is never used for calibration or selection rules.
