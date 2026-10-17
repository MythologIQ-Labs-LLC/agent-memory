# #819 C9-D: discovery trace, failure taxonomy, candidate and verdict

**Verdict: STOPPED at its preregistered gate (P5 not met).** C9-D fixes a real implementation defect in the optional semantic route, and it is safe:
- route off, `ranked_prefix` and every store without lifecycle history are identical to C4;
- 0 leaks;
- the fail-first tests pass.

It does **not** improve user-visible memory. On every development set, needed-memory discovery and returned needed memories equal C4+sem's. On the longitudinal sets it returns 1 and 5 more non-needed memories. It should not be integrated as a quality candidate.

The trace's main finding is the useful result. On these sets, the one bound that keeps relevant memories from being discovered is the semantic route's absolute 0.30 cosine floor, and C4 couples that floor to sufficiency. That makes it a selection question, not a discovery one (§5).

## Identity

| Item | SHA |
|---|---|
| Comparator C4 (base) | `bc2be6319a3eda96731fdb235f4feba882bcb9be` |
| C6 (studied, not modified) | `171e67db041434e1144dd83a73423af6d4c267e1` |
| C8 frozen (studied, not modified) | `24d4dd2697047fc622a6087f7005775133b60209` |
| C9-D runtime change | `868684a0f029baf5c6a58428493f305ca72503de` |
| Preregistration and longitudinal set | `819c7ae` (written after the runtime commit, before any longitudinal run) |
| Fail-first tests | `ca590e8` |
| Branch | `claude/cool-clarke-fw5xw5` (from C4; no PR, no Actions) |
| Embedding model | pinned `multi-qa-MiniLM-L6-cos-v1@b207367`, config digest `sha256:74477054…` (reproduced) |

**Data used.** Only development and public data:
- the five inherited development sets (C6 diag, C5 dev, the C6 reviewer's gen set, C7 dev, C8 dev), read from `24d4dd26`;
- the self-authored longitudinal set added here;
- a 40-question deterministic LongMemEval-S subset.

**Not used.** e4, e5 or e6, any hidden gold, and AMB cases.

## 1. Discovery path (C4)

`AgentMemory.recall` → `DeterministicMultiRouteRecallPlanner.recall` (`runtime/runtime_composition.py`):

| Route | Bound | Prefilter | Notes |
|---|---|---|---|
| Lexical (`eligible_search` → `substrate.search`) | **None**: every tenant fact with ≥ 1 shared whitespace token | domain eligibility | Tokens are whitespace-split with `.,;:!?` stripped, so function words match too. Under `relevance_sufficient`, C3 adds morphological and one-edit variants from the vocabulary of admissible facts (`_discovery_query`) |
| Exact identity | refs the caller names | — | |
| Shared evidence | neighbours of exact-identity seeds only | — | |
| Semantic (`NativeVectorCandidateRetriever.search`, opt-in) | **top 16 with cosine > 0.30** (`SEMANTIC_CANDIDATE_LIMIT`, `SEMANTIC_MINIMUM_SIMILARITY`) | domain eligibility **only** | O(N) scan |

The deduplicated union crosses `admit_preselected_candidates` once. Admission is per fact, using `_admission_refusal`. Ranking policy 3.4.0 follows, then selection 2.3.0. In selection, any non-lexical route makes a fact `non_lexical_route_evidence`, which counts as sufficient. A semantic proposal is therefore returned if it is within budget.

**C6/C8.** They replace the semantic route's floor and limit, under `relevance_sufficient`, with a rank-bounded policy:
- nothing is proposed when the best cosine is below 0.40;
- otherwise K = 1 (3 for set questions) within 0.20 of the best;
- the pool is mode-aware and admission-filtered.

C8 changes ranking only.

## 2. Failure taxonomy (338 needed memories, 6 development sets, budget 10)

| Arm | Never discovered | Proposed, refused by admission | Admitted, withheld by selection | Selected, below budget | Returned |
|---|---:|---:|---:|---:|---:|
| C4 default | 125 | 0 | 104 | 0 | 109 |
| C4+sem | 75 | 0 | 50 | 0 | 213 |

**C6+sem against C4+sem.** It loses 53 needed memories that C4+sem returns:
- 28 become *never discovered*, because the K = 1 or 3 cap and `min_best` 0.40 propose nothing;
- 25 become *admitted, withheld*: the lexical route still finds them, but they are no longer semantically proposed, so they are insufficient.

None is a governance refusal or a budget cut. This is the C8 review's "discovery below C4+sem, C6 losses retained", traced to stages.

**Why C4+sem never discovers 75.** Dense cosine and rank were computed per needed memory (`tools/dense_probe.py`):
- **73 of 75 are below the 0.30 floor.** On the five inherited sets, 17 of the 66 are dense rank 1–3 in their store.
- **None is cut by the 16-slot limit.**
- The other 2 are a ref-naming artifact of the gen set, described below.

**Lexical tokenisation is not a cause.** Discovery splits on whitespace, but ranking and selection score `[a-z0-9]+` normal forms. Only 3 of 125 C4-default misses overlap the query under the selection tokenisation, and only on function words. The rest share no vocabulary at all.

**The gen set's "violations" (1 or 2 in every arm, C4 included) are not leaks.** The fixture names a corrected memory's expected ref `…-new`, while the runner maps the current version to the original ref.

## 3. Defect and change (C9-D)

**Defect.** The semantic route ranks superseded, forgotten and disputed facts too, because its prefilter is domain eligibility only. Those facts take some of the 16 slots, and admission refuses them afterwards. Each correction leaves a near-duplicate superseded version, so a living memory corrected n times can take n + 1 slots. The lexical route is unbounded, so it does not have this defect.

**Change.** Under `relevance_sufficient`, the route's prefilter adds `adapter.discovery_refusal(fact, context, mode, target) is None`.
- `discovery_refusal` is exactly `_admission_refusal`, in the recall's admission mode, so historical and as-of recall keep in-window state changes.
- 2 files, +26/−1: `runtime/adapter.py`, `runtime/runtime_composition.py`.
- `discovery_refusal` has the same name and signature as C6's.
- The floor, the limit, ranking and selection are unchanged. `ranked_prefix` is unchanged.

**Properties.**
- Discovery is monotone against C4+sem, because admission is per fact and the change only removes refused facts.
- No authority is added.
- Refused text is not embedded on these recalls.

## 4. Results against predictions (paired, per query)

| ID | Prediction | Result |
|---|---|---|
| P1 | Route off = C4 | **Met.** Identical returned and admitted lists on all 7 sets (30–57 queries each) |
| P2 | `ranked_prefix` with the route on = C4+sem | **Met.** Identical on merged, longitudinal and gen (115 queries) |
| P3 | Five inherited sets, route on = C4+sem | **Met.** Identical returned lists on 238/238 queries (observed before preregistration; disclosed) |
| P4 | LongMemEval-S, route on = C4+sem | **Met.** 40-question turn-plane subset identical apart from timing; 0 refusable candidates (§4.1) |
| P5 | Longitudinal: discovery gain, returned needed ≥, 0 leaks | **Not met.** Discovery 41/48 = 41/48, returned 28 = 28, strict 0 W / 0 L, 0 leaks. Extras +1 (51 → 52) |
| P6 | p50 ≤ C4+sem + 10 ms at ~200 memories | **Met.** 71.3 ms against 75.7 ms (§4.2) |

| Set | Arm | Strict | Needed discovered | Admitted, withheld | Returned needed | Returned, not needed | Leaks |
|---|---|---:|---:|---:|---:|---:|---:|
| Longitudinal (prereg; 6 stores, each 37 memories with 15 corrections and 2 forgets) | C4 | 13/30 | 34/48 | 21 | 13 | 9 | 0 |
| | C4+sem | 5/30 | 41/48 | 13 | 28 | 51 | 0 |
| | C6+sem | 15/30 | 36/48 | 17 | 19 | 12 | 0 |
| | **C9-D+sem** | 5/30 | 41/48 | 13 | 28 | **52** | 0 |
| Merged (post-hoc exploratory: one store, 180 facts, 90 superseded) | C4 | 9/30 | 34/48 | 21 | 13 | 20 | 0 |
| | C4+sem | 3/30 | 41/48 | 13 | 28 | 65 | 0 |
| | C6+sem | 10/30 | 36/48 | 17 | 19 | 23 | 0 |
| | **C9-D+sem** | 3/30 | 41/48 | 13 | 28 | **70** | 0 |

**Why P5 failed.** The defect is real:
- C4+sem spends 121 of 191 semantic slots on refused versions on the longitudinal set, and 155 of 231 on the merged set.
- But the needed memories always rank above the refused versions that squat.
- The slots C9-D frees go to lower-ranked admissible neighbours, and C4's selection returns them as sufficient.

The full per-set table for all five arms is in `evidence/TABLE.md`.

### 4.1 LongMemEval-S (P4)

The runner only `remember`s unique refs, so no fact is refusable and C9-D cannot differ by construction. Empirical check: a deterministic 40-question subset (`--subset-size 40`, default seed), turn plane, semantic required, input sha256 `d6f21ea9…`. **Result: identical** apart from timing fields. recall_all@5/@10/@50 = 0.667/0.788/0.879 in both arms, with `refused_candidate_count_total` 0. See `evidence/LME-PARITY.md`.

### 4.2 Cost (P6): met

Merged store (180 facts), 3 alternating rounds, 90 recalls per arm:

| Arm | p50 ms | p95 ms |
|---|---:|---:|
| C4+sem | 75.7 | 170.1 |
| C9-D+sem | 71.3 | 124.5 |

The added work is one O(1) refusal check per eligible fact, and it removes refused facts before their vector is looked up. Details, including the shared-CPU caveat, are in `evidence/LATENCY.md`.

### 4.3 Tests

**New tests.** The 7 new tests in `reference/tests/test_c9d_semantic_slots.py`, run on C4 `bc2be631`:
- 3 fail first (forgotten squatters, superseded squatters, historical state change);
- 2 error, because `discovery_refusal` does not exist on C4;
- 2 hold.

On C9-D all 7 pass (`evidence/fail-first.txt`).

**Full reference suite.** C9-D `ca590e8` ran 2661 tests and C4 ran 2654. Both have the **same 5 failures**, all pre-existing and none in recall (`evidence/full-suite-*.txt`):
- the Runtime Baseline register declares no successor for the C lineage's protected files;
- a fixture file `harvest-closeout-wave2.json` is missing;
- three gauntlet probes report `blocked` in this environment.

C9-D touches two protected files (`runtime/adapter.py`, `runtime/runtime_composition.py`). Integration would need a successor declaration, as for C4 and C6.

## 5. Rejected alternative and handoff

The floor is the binding bound, so it was the obvious candidate. Offline, on the five inherited sets with C4+sem, guaranteeing the top-r dense neighbours past the floor gives:

| r | Needed memories gained | Extras added | No-answer queries that now return something |
|---:|---:|---:|---:|
| 1 | 8 | 23 | 10 |
| 2 | 16 | 104 | 10 |
| 3 | 24 | 226 | 10 |

It was not implemented. In C4, a semantic proposal is sufficient, so a lower discovery floor is a lower sufficiency floor. That decision belongs to selection.

**Handoff to the selection lane (concrete).** Decouple the semantic route's two roles:
- **Discovery:** for example, the dense top-r regardless of the floor, entering admission.
- **Sufficiency:** credit `non_lexical_route_evidence` only above a sufficiency threshold, or with lexical corroboration.

That is the only path found here that reaches the 73 below-floor memories without the flood. C9-D's slot fix composes with it unchanged. With a wider candidate pool the 16-slot limit becomes binding, and the squatting fix then matters.

## 6. Reproduction

Tools are in `tools/`; outputs are in `evidence/`.

**Paths.** The tools were run from git worktrees of each SHA under `/tmp/claude-0/wt/<arm>`, with a Python 3.13 venv built from `reference/requirements.txt` and `reference/requirements-semantic.txt`. `runall.sh` and `floor_feas.py` hard-code those paths; adjust them locally.

**Development sets.** They are read from `24d4dd26`:
- `reports/benchmarks/memory-quality/819-c6/dev/diag-scenarios.json`
- `…/819-c6/dev/c5-dev-scenarios.json`
- `…/819-c6/review/gen.json`
- `…/819-c7/dev/c7-scenarios.json`
- `…/819-c8/dev/c8-scenarios.json`

Their sha256 values are in `evidence/fixtures.sha256`. The merged set is `tools/build_merged.py dev/longitudinal-scenarios.json`, which reproduces it byte for byte.

**Harness.** The harness memoises the verified ONNX provider per process. This affects load time only; the numerics are unchanged.
- `harness.py <root> <set> <out> --sem off|required [--rs ranked_prefix]` uses the runner's operations and scoring (budget 10), plus a per-needed-memory stage classification read after recall.
- `pair.py`, `table.py`, `dense_probe.py`, `floor_feas.py` and `tok_probe.py` produce the comparisons above.
