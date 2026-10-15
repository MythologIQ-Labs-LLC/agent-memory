# C6 review disposition

**Review.** `REVIEW-C6.md` is an independent adversarial review of `80c797d0`, written by a reviewer who did not author the change. Its paths refer to `review-c6/` in the engineering scratchpad, which is this directory:
- `tools/`: the reviewer's scripts;
- `gen.json` and `gen-table.md`: the reviewer's own 55-query scenario set, unseen by calibration;
- `outputs/`: the reviewer's observed outputs.

The reviewer did not open the sealed v4 cohort, other cohorts or benchmark gold.

**Fixes.** All fixes are in `fab09130`. The policy constants are unchanged, and nothing was recalibrated.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Blocking** | Historical and as-of recall: a forgotten, disputed, error-corrected or out-of-window memory takes the single slot, and the answer is lost | **Fixed.** The bounded pool is filtered with `GovernedMemoryAdapter.discovery_refusal`, which is exactly `_admission_refusal` in this recall's admission mode and target instant. Four new tests fail on `80c797d0`, pass on C4 `bc2be631` and pass on `fab09130` (`../fail-first-review-fixes.log`). Reviewer probes H1–H4 now return the answer (`after-fixes/c6fix-probe-fake.txt`). |
| 2 | Should-fix (high) | A question-shaped or meta memory captures the K_single slot. A relative margin also lets one close memory push answers out of the K_set window | **Not changed; recorded as a limit** (docs/44, `../FREEZE-C6.md`). Remedies such as K_single ≥ 2, margin from the second-best, or a meta-text grammar are new mechanisms or new constants chosen after seeing results; the preregistration rules both out. The reviewer measured K_single = 2 on its own set and found it worse: strict 11 against 16. Exposure: the writer needs write access to the same scope, and the effect is suppression of the answer, not access. Under a C4 default configuration the same store returns 0 of 6 needed memories too. Raised to the evaluator as a targeted probe. |
| 3 | Should-fix | The discovery claim against C4 with the semantic route is not supported; the gain is a precision effect | **Accepted.** The claim is restated (`../CALIBRATION-AND-RESULTS.md`, "Review outcome", and `../FREEZE-C6.md`). The preregistered expected observable "against C4-semantic-on, recall stays the same or rises" is recorded as **failed**. C6 is a bounding control that makes the existing semantic discovery route net-positive under relevance-sufficient selection. Against C4 default (the route off) it adds reach. Against C4 with the route on it trades reach for precision. |
| 4 | Should-fix | The policy also changed `ranked_prefix`, and the posture was stale | **Fixed.** The policy is gated to relevance-sufficient selection, like C3's vocabulary-variant discovery, so `ranked_prefix` keeps C4's route (floor 0.30, at most 16, domain-eligible pool). New test `test_ranked_prefix_keeps_the_unbounded_route`. On the reviewer's set, `ranked_prefix` lists at `fab09130` are identical to C4's on all 55 queries (`after-fixes/c6fix-gen-rp.json`). The posture's `proposal_policy` now states `applies_to_return_selection` and the settings it `replaces`; `minimum_similarity` and `candidate_limit` are again accurate for `ranked_prefix` consumers such as the deferred LongMemEval semantic lane. |
| 5 | Should-fix | `plural_answer` misreads common list questions | **Not changed; recorded as a limit.** Changing the reading or the K default is a post-result change to the preregistered mechanism. |
| 6 | Should-fix | `min_best` = 0.40 drops genuine answers at 0.32–0.40 | **Not changed; recorded as a limit,** with the reviewer's sensitivity table. On the reviewer's set, strict is flat over 0.35–0.40 and recall falls with the threshold. |
| 7 | Note | Shadow recall control labels the bounded route a resource stop | **Fixed.** The host cap is `SEMANTIC_CANDIDATE_LIMIT` again. New test `test_bounded_semantic_route_is_not_reported_as_a_resource_stop`. The `ranked_prefix` cap tests keep C4's assertions. Probe H9 now reports `frontier_exhausted`. |
| 8 | Note | 176 of 192 grid points; weak G4; stale file name | **Recorded** as errata in `../CALIBRATION-AND-RESULTS.md`. The code comment now cites `CALIBRATION-AND-RESULTS.md`. |
| 9 | Note (pre-existing) | A provider failure at query time is not degraded in `auto` mode | **Not changed** (pre-existing in C4 and A's lineage). The preregistered claim is narrowed to failure at open, and the evaluator is told. |

**Unchanged by the fixes,** checked against the reviewer's and my earlier runs:
- **Development union:** relevance-sufficient returned lists on all 78 queries, so the gate metrics are identical.
- **Reviewer's set:** relevance-sufficient returned lists on all 55 queries (`after-fixes/c6fix-gen-required.json`). Its one historical query, car-8, is unchanged.
