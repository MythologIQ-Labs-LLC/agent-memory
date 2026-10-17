# #819 C9-D preregistration: admission-aware semantic slots

**Lane.** Discovery engineer (#819, 2026-10-17 coordination comment). The candidate is isolated and derives from C4. Selection, ranking, accepted results and production defaults are not touched. C6 `171e67db` and frozen C8 `24d4dd26` were studied and not modified. No access to e4/e5/e6.

**Base.** C4 `bc2be6319a3eda96731fdb235f4feba882bcb9be`. Candidate commit `868684a0`. That commit was written before this file and before any run on the longitudinal set below.

## Defect

The optional semantic route (`NativeVectorCandidateRetriever.search`) keeps its top `SEMANTIC_CANDIDATE_LIMIT = 16` hits above cosine 0.30. Its `eligible` prefilter is domain eligibility only, so the route ranks every superseded, forgotten and disputed version too. Those versions fill slots, and governed admission then refuses them. Each correction leaves one superseded version, worded almost exactly like the current memory, so a memory corrected n times can take up to n + 1 slots for one admissible answer. Admissible evidence ranked below them is never discovered.

The lexical route has no limit, so it does not have this defect.

C6 fixed the same squatting only inside its capped proposal policy (`fab09130`), and that policy is what lost reach against C4+sem. C9-D keeps C4's proposal policy exactly: floor 0.30, limit 16, every proposal treated as before. It changes only which facts compete for the 16 slots.

## Mechanism (one change)

Under `relevance_sufficient`, the semantic route's prefilter becomes domain eligibility AND `discovery_refusal(fact, context, mode, target) is None`. The refusal is admission's own `_admission_refusal`, evaluated in the recall's admission mode (`admission_mode_for_intent(resolve_intent(...))`):
- Current state: superseded, tombstoned, derived from a tombstoned source, disputed, and out of domain are excluded.
- Historical and as-of recall: superseded state changes inside the window stay eligible.

`ranked_prefix` keeps the pre-C9 route, like C3's vocabulary expansion.

## Properties claimed by construction

1. **Discovery is monotone against C4+sem.** Admission is per fact. The candidate's semantic top 16 is the top 16 of C4's eligible pool with only admission-refused facts removed. Every fact C4+sem admits through the route is still in the candidate's top 16 and is still admitted.
2. **No new authority.** The change only removes facts, using the same predicate admission applies. Refused text is not even embedded on these recalls.
3. **Identity where nothing is refusable.** If a store has no superseded, forgotten or disputed facts, every recall is identical to C4+sem. Route off is identical to C4. `ranked_prefix` is identical to C4.

## Predictions (written before the longitudinal run)

| ID | Prediction |
|---|---|
| P1 | Route off: C9 = C4 on every query of every fixture |
| P2 | `ranked_prefix` with the route on: C9 = C4+sem |
| P3 | The five inherited development fixtures (C6 diag, C5 dev, C6 reviewer gen, C7, C8), route on: C9 = C4+sem. They contain at most two corrections and forgets per scenario. *Already observed on returned sets before this file was written; disclosed.* |
| P4 | LongMemEval-S, route on: C9 = C4+sem on every question. The runner only `remember`s unique refs, so nothing is refusable |
| P5 | Longitudinal set (`dev/longitudinal-scenarios.json`, sha256 `c356c66b…`, self-authored, committed with this file), route on: discovery of needed memories C9 ≥ C4+sem on every query, with a strict gain in total. Returned needed memories C9 ≥ C4+sem in total. 0 safety violations and 0 superseded versions returned in both |
| P6 | Cost: recall p50 within C4+sem + 10 ms at 200 memories. The refusal check is O(1) dictionary reads per fact |

**Stop condition.** If P5 shows no discovery gain, the defect does not bind on longitudinal data at this scale. Then the candidate is a correctness fix with no measured quality effect, and the verdict says so. If any of P1–P4 fails, or a leak appears, the candidate is rejected.

**Rejected alternative (measured offline on the five development fixtures, C4+sem).**
- 66 of 68 needed memories that C4+sem never discovers lie below the 0.30 floor, and 17 of those are dense rank 1–3.
- Guaranteeing the top-r dense neighbours past the floor gains 8, 16 or 24 needed memories for r = 1, 2 or 3. It also adds 23, 104 or 226 extras, and makes 10 no-answer queries return something.
- The cause is C4's selection, which treats every semantic proposal as sufficient. Relaxing the floor is therefore a selection question, and it belongs to the selection lane.
