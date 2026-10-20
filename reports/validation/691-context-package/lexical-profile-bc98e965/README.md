# #819 / #691 lexical consumer profile: candidate execution

**Decision: GO for independent evaluation; BLOCKED for merge/default adoption.** This is a narrow opt-in consumer capability, not completion of #819, #691, #805/#815 or the release. No accepted score, Runtime Baseline, frozen fixture/evidence or ADR was changed. No new PR or architecture document was created.

## Source and implementation

- Existing branch: `claude/eager-dirac-bftkfg-691-context`.
- Untouched base: `585e76fb87e5c08da51020327a70d6d1807e06b4` (itself an unaccepted #691 context package on the unmerged security stack).
- Published implementation: `bc98e9657366e5e3a16f89708a7f22935442a2c4`.
- Local execution commit before connector transport: `47cde816a1c80fe9fa3d21da9d1f482d0b870c74`.
- These two commits have **identical complete Git trees**: `f78a2d2f32ea0a9cb444fa1c2b614055cbe2d65f`. Git transport lacked shell credentials, so Git Data published the same tree with a new commit identity. Target tests, native AMB diagnostics and all 44 security cases were then re-executed on the published exact head.

Files: existing `api/context_package.py`, `api/surface.py`, `schemas/api-context-package.schema.json`, owning `docs/44-public-api-contract.md`, and new `reference/tests/test_context_selection.py` (13 public workflow/negative tests).

`recall_context(..., consumer_profile="lexical_content")` returns experimental package `agent-memory-context/0.2.0`; default `all_returned` remains 0.1.0 with identical output shape. Unlike the prior rejected discovery experiment, this changes **neither candidate discovery nor admission nor ranking nor the original recall return prefix**. Inside the existing serialized, re-admitted public content-resolution boundary, it omits lexical-only matches with no content-word overlap. A closed-class English grammar vocabulary is excluded; negation and content verbs remain. Nonlexical route evidence, including requested exact identity, preserves the item. Omitted IDs/counts are recorded under an explicit no-authority policy and were already caller-visible in `recall.returned`; their text/provenance is absent. Failed resolution remains partial/unknown, not abstention.

The original ranked-prefix `return_policy` remains intact in the package's recall receipt. No claim that every admitted fact is useful context, and no claim that lexical relevance establishes truth/currentness/permission. The policy has no benchmark IDs, query patterns, answer literals, learned cutoff, model or inference cost.

## Validation

- 13 new profile tests plus 20 existing context tests: **33 pass**. Original nine tests failed on the base before implementation; replay of the final 13 against the untouched base is retained separately. Baseline reproduction after implementation is a negative control, not retroactive preregistration.
- Published exact-head targeted suite: **131 pass**. Includes context, public facade, domain eligibility, scope/isolation, temporal floor, ranking, governance, deletion and restart.
- Existing package-layout checks: **8 pass, 156 subtests**.
- Security replay DSL/2: **31/31**; DSL/3 #809: **13/13**, all on a clean exact-head source tree. Full raw observations/manifests/reports are in security-replays.json.gz. These replays establish tested behavior only, not acceptance of the inherited security stack, and do not substitute for independent adversarial profile review.
- Demo: existing real remember/correct/forget/reopen/scope workflow passes.
- Markdown API links and architecture catalog: pass (82 numbered documents, one shelf each on this inherited branch). Package layout matches its canonical table.
- Full suite at local commit 47cde816 (identical tree to published head): **3011 passed, 5 failed, 35 skipped, 1 xfailed, 2080 subtests passed**, 212.69 seconds.
- All five full-suite failures reproduce on the untouched base AND published head, same test identifiers: frozen imported-runtime identity/ancestry; two #770 replay-freshness expectations; Runtime Baseline equivalence guard; and derived-directory foreign-ownership exercise. The last raises `OSError: [Errno 22] Invalid argument` at `os.chown(...,65534,65534)` before the runtime ownership check. This Work container maps only UID 0 (`0 0 1`); that host capability remains untested here. None of these guards/tests was disabled or weakened. Exact comparison logs/XML are retained.

## Paired known AMB diagnostic (not a holdout or accepted lane)

Actual public `AgentMemory.recall_context` on the same source/store/input/budgets/host, alternating profile execution order. The raw `recall` candidate/admitted/returned/return-policy fields were asserted identical before and after both profiles for every case. The native AMB dataset and scorer run unmodified at `03c1d0f1d27da63034f0931121c858faba512383`; fixtures are `tenurehq/precisionmembench@b95d6abb471c0d591c440172283dd74e7af000df`. The full locked AMB CLI is NOT run. No inference. Original 77 cases remain known diagnostic data, never an unseen holdout.

| Axis | all_returned | lexical_content |
|---|---:|---:|
| Strict success | 15/77 | 22/77 |
| Active success | 4/43 | 9/43 |
| Native mean precision | .1806 (67 cases) | .3243 (64 cases) |
| Native mean recall | .9535 (43 cases) | .9535 (43 cases) |
| Delivered fact IDs | 686 | 236 |
| Content characters | 155770 | 55940 |
| Estimated context tokens | 39553 | 14188 |
| Must-exclude failure cases | 2 | 2 |
| Correct trivially-empty diagnostics | 5/9 | 5/9 |

Seven strict cases improve, none regress; no per-case recall decreases. Precision denominators differ because upstream excludes empty/empty cases; do not read the macro average without that qualification. Paired bootstrap over the known cases (3000 resamples, seed 691819): strict improvement 95% interval **+3.90 to +15.58 percentage points**, macro-precision difference **+.0945 to +.2028**. These describe this diagnostic sample, not generalization or unbiased selection uncertainty. Latency was measured during other local test work; it is indicative only, not an operational win. `amb-paired.json.gz` contains every package, omission receipt, original returned IDs, native assertion failure and score.

## Disjoint synthetic LongMemEval regression

After implementation freeze, exercised the existing five-question synthetic fixture through an evaluation-only adapter calling the public context API. It was not used for policy selection, but **is not independently blinded holdout qualification**. Three questions are scored; one abstention and one no-user-target case are excluded by the existing scorer. Session and turn headline recall_all@5/@10 (and turn @50) stay .666667; nDCG_any at those depths stays .833333. One no-answer diagnostic still returns content under both profiles. This does not replay the accepted external LongMemEval lane or measure answer generation.

## #825 real synthetic scale arms

Existing harness base `b33fa75e1e2339b611651cfd3abc3ff55c0504a6`, generator seed 825, 19,014 fabricated records, 14 cases (13 primary plus separate temporal diagnostic), budget 5, three repetitions. One real governed public ingestion is shared by both context profiles; SQLite FTS5 is separately built. All original corpus information and task budgets remain the same. All data are synthetic; no real Jarvis system/data was accessed.

| Axis | FTS5 | all_returned context | lexical_content context |
|---|---:|---:|---:|
| Primary strict success | 1/13 | 0/13 | 4/13 |
| Required evidence | 11/11 | 11/11 | 11/11 |
| Extra primary context | 42 | 52 | 21 |
| Forbidden items (all cases) | 2 | 2 | 2 |
| Correct no-answer | 0/2 | 0/2 | 0/2 |

The 1,014-record run has the same quality counts. Raw paired results at both sizes are included. The 19k run completed under a 180-second process timeout, with real ingestion about 100.7 seconds. FTS5 uses in-memory storage while Agent Memory pays durable/governed costs; source/trust/temporal metadata equivalence, independent labels, RSS/CPU/disk accounting, cold/warm separation and adoption-grade fairness remain unqualified. This is development evidence of selective context, **not** proof of overall superiority or an external adoption recommendation.

## Reproduction and remaining gates

Provisioning: `python -m pip install -e . pytest rich tiktoken`. This is not the AMB locked dependency environment. Profiles both use max_chars_per_item=20000/max_total_chars=1000000 to isolate selection from truncation, same budgets in both arms.

- `python replay_context_profiles.py <workspace-with-amb-and-precisionmembench> <runtime-checkout> <output-json>`
- `python replay_synthetic_longmemeval.py <runtime-checkout> all_returned <output-json>`; repeat for lexical_content.
- `python replay_scale_profiles.py <runtime-checkout> <825-harness-checkout> <output-json> 19000`; repeat with 1000.
- `PYTHONPATH=reference python -m pytest -q reference/tests/test_context_selection.py reference/tests/test_context_package.py`.
- `PYTHONPATH=reference python -m pytest -q reference/tests`.
- `PYTHONPATH=reference python reference/run_786_security_replays_dsl2.py --all --output-dir <new-dir>`; repeat with DSL/3 runner.

The reproduction adapters contain evaluator labels only through the upstream scorer or original synthetic harness after retrieval; none enters runtime selection. No baseline, scorer, gold or external dataset is edited. Raw reports retain the actual local execution SHA where applicable; the published identical source tree is recorded in the manifest.

**Open:** independent disjoint cohort authored/sealed outside candidate selection; accepted full external LongMemEval replay; profile-aware semantic/paraphrase, multi-evidence and proper-name stress; actual no-answer/must-exclude remediation; complete cost/resource accounting; inherited #691/#805/#815 release acceptance. The English lexical policy can suppress implicit/paraphrased evidence and grammatical-word proper names when no nonlexical route found them. It does not refill omitted slots beyond the original return budget, repair scope metadata discarded by bridges, infer supersession, or filter poisoned facts merely because they are untrusted. Default posture and accepted scores remain unchanged. No merge until those relevant gates receive explicit qualification.

Dataset-derived output is adapted from PrecisionMemBench by Jeffrey Flynt under MIT; the exact upstream license is included as PrecisionMemBench-LICENSE.txt. No endorsement is claimed. AMB's unchanged scorer is imported from the exact upstream checkout, not redistributed here.
