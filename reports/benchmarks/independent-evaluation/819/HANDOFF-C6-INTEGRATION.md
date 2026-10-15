# #819 C6: handoff to the repository delivery lane

**Disposition: CHANGES REQUIRED. Do not integrate C6 `171e67db` as frozen.** The full rationale is in `REVIEW-C6.md`. This note says what the delivery lane may and may not do with C6, and what a successor must bring.

## What not to do

- **Do not merge, rebase-for-merge, or open an integration PR for C6.** Do not change the Runtime Baseline register for it, and do not promote any C6 number to a dashboard, feed or leaderboard.
- **Do not retune C6's frozen constants** (`min_best` 0.40, `margin` 0.20, `k_single` 1, `k_set` 3) in place. Any change makes a new candidate with its own preregistration, freeze and independent evaluation.
- **Do not use e4, the evaluator probes, or the developer's dev and reviewer fixtures as a holdout** for the successor. Engineering's sealed v4 stays reserved and unopened.

## What can be carried forward

These are the reusable parts of C6, all verified independently:

- **The pool filter, `GovernedMemoryAdapter.discovery_refusal`.** It keeps forgotten, superseded, error-corrected, disputed, out-of-window and other-scope memories out of bounded slots, in current, historical and as-of modes. Probes and replays found no leak.
- **Scoping the policy to `relevance_sufficient`.** `ranked_prefix` keeps C4's route.
- **Route-off identity.** Route-off C6 equals C4 on e4 (208/208), on the evaluator probes (57/57) and on the reviewer set (55/55).
- **Deterministic tie-breaking and no network egress.** The tie-break is (−similarity, candidate_ref). A semantic-on run makes 0 connect or sendto calls.
- **The 17 tests in `test_c6_semantic_discovery.py`.** The governance tests hold on C4 and on C6. The fail-first tests describe C6's policy and will need revising for a successor that changes it.

## What a successor must bring before independent qualification

The full list is in `REVIEW-C6.md` §9. In short:

1. **A preregistered recall non-inferiority bound against C4+sem.** The lower 95% bound of Δ recall must be ≥ −0.02, and aggregation recall must be ≥ C4+sem's. It is measured on data the developer did not author.
2. **Set sizing that does not hinge on the closed plural grammar,** or score-distribution-based K.
3. **No absolute `min_best` near 0.40** under this model. Abstain on evidence of irrelevance instead.
4. **Question-shaped and meta notes must not anchor the margin or take the only slot.**
5. **The anchor test must work after the pool filter removes the strongest memory** (`life4`).

## Integration dependencies (unchanged from `FREEZE-C6.md`; still open)

- **Security stack.** Rebase onto #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58`, and re-run the security replays.
- **Protected files.** A Runtime Baseline successor must declare them, which C6 does not:
  - `runtime/vector_retrieval.py`;
  - `runtime/adapter.py`;
  - `runtime/runtime_composition.py`;
  - `api/surface.py`;
  - `runtime/return_selection.py`.
- **LongMemEval lane.** Version the lane, because the scored list changes under `relevance_sufficient`.
- **Documentation.** Fix `FREEZE-C6.md`'s "ranked_prefix default" wording. The default is `relevance_sufficient`.

## Before the semantic route could ever be activated

These are not qualification conditions:

- **Cold first recall.** Embed at write time, or bound the cold first recall. It is 6.6 s at 1,000 memories on 4 vCPU today, because embedding happens at first recall.
- **Memory cost.** Disclose the +290 MiB resident model cost and the +36 to +46% store size.
- **AMB coverage.** Get owner approval for a semantic-on option in the AMB adapter (`amb_agent_memory_bridge.py`), so AMB can measure the route. Today it cannot without an adapter change.
- **As-of currentness.** Decide whether as-of recall should keep returning successors that become valid after the as-of date. It happens in every runtime today and is not C6-specific.

## Evidence index

| Evidence | Location |
| --- | --- |
| Review and verdict | `REVIEW-C6.md` |
| e4 aggregates (relayed, author-held cohort) | `candidates/c6-171e67d/e4/RELAYED-AGGREGATES.md` |
| LongMemEval-S 500, route on and off, both candidates | `candidates/c6-171e67d/lme500/` |
| Evaluator probes, latency and as-of probes | `candidates/c6-171e67d/probes/` |
| Cross-host determinism check | `candidates/c6-171e67d/repro/` |
| Environment, pins, model hashes, run scripts and tools | `candidates/c6-171e67d/provenance/` |
| e4 hash commitment | `holdout-e4/COMMITMENT.md` (`81b02a25`) |

**Next independent cohort.** It is authored fresh, and its hashes are committed, only when the successor is frozen and handed to the evaluator.
