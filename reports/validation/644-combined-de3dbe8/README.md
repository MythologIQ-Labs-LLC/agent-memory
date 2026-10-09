# #644 combined safety receipt: independent integration qualification

**Verdict: CHANGES REQUIRED** for the candidate as submitted, `de3dbe8`. Formal v7 qualification is **BLOCKED** by evidence that does not exist yet. See section 11.

## 1. What was tested

| | |
|---|---|
| Candidate | `implementation/644-combined-safety-receipt-unqualified` @ **`de3dbe813683e417f73546bfbdd66976997bea76`**. This equals the expected SHA, verified after `git fetch origin`. The worktree was clean. |
| Parentage | `9f3c1ec` → `ed06df3` → `4bdb506` → `f784289` → `3e8759e` → `de3dbe8`, on main `3eebb6d`. Merge base with `origin/main` is `3eebb6d`. 24 files changed against main (+3017 / −6). |
| Validation branch | `validation/644-combined-safety-receipt-independent`, an isolated worktree. The candidate branch and main are untouched. |
| Validation commits | `836b688` adds the reproducer tests only. **`46d84adeecf7f0ec034e7ec8c356bbb3859c8e03`** adds the remediation, the sanctioned re-declaration and ledger Entry #125. |
| Comparators | Published v6 frozen `e98e6e7`. Main `3eebb6d`, whose protected surface is byte-equal to v6 (checker PASS). e002536. 3539a25 (earlier figures, quoted only). |
| Published baseline | `baseline-register.json` on main and on the candidate: the last entry is `agent-memory-runtime-baseline-v6` (published `b08cd844`). The candidate sets `declared_successor` to v7 only. There is no v7 record, boundary, qualification or publication. |
| Not done | No PR, no merge, no GitHub Actions, no v7 publication, no change to held-out cases, labels or thresholds. |

**Environment.**
- Linux 6.18 x86_64, 4 vCPU, SQLite 3.45.1, git 2.43.0.
- Tests and probes: CPython 3.13.16 venv.
- Lanes: CPython 3.12.3, matching the workflows. LongMemEval used a venv with `reference/requirements.txt` exactly pinned. AMB used a separate venv built by `scripts/amb_harness_constraints.py` from the frozen AMB `uv.lock` (uv 0.8.17). Its constraints file sha256 is `8a7f4b9b…` (295 pins), identical to the accepted v6 run. The resolved packages are identical to the accepted run: hindsight-all 0.4.17, mem0ai 1.0.5, torch 2.10.0, etc.
- Import provenance was checked in every run. The venv's editable install points at another checkout, so every run sets `PYTHONPATH=<tree>/reference` or uses `-t reference`, and the module path was printed to confirm it.

## 2. Phase A: integration tests

Every run was made from the repository root with `python -m unittest discover -s reference/tests -t reference [-p <file>]`.

| Suite | de3dbe8 | 46d84ad (remediated) |
|---|---|---|
| test_recall_observation_receipt | 14/14 OK (0.44 s) | 14/14 OK |
| test_recall_control | 29/29 OK (0.83 s) | 29/29 OK |
| test_evidence_sufficiency | 29/29 OK | 29/29 OK |
| test_governed_transition_witness | 7/7 OK | 7/7 OK |
| test_governed_transition_integration | 5/5 OK | 5/5 OK |
| test_package_layout | 8/8 OK | 8/8 OK |
| test_runtime_baseline_succession | 40/40 OK | 40/40 OK |
| **Full reference suite** | **2628 run, 1 failure**, 34 skipped, 135 s. After fetching `refs/seals/*`: 2628 run, 1 failure, 25 skipped, 156 s. | **2650 run, 0 failures**, 25 skipped, 158 s |
| Full suite, exact-pinned CPython 3.12.3 venv | 2628 run, 1 failure (the same stale declaration), 17 skipped, 152 s | **2650 run, 0 failures**, 17 skipped, 151 s |

**The single de3dbe8 failure** is `test_benchmark_integration_contract.test_evaluation_only_change_keeps_runtime_baseline_equivalence`. The sanctioned checker rejects the stale declaration:

```
undeclared protected change: reference/agentmem_ref/recall_observation_receipt.py
undeclared protected change: reference/agentmem_ref/runtime/recall_observation_receipt.py
declared blob mismatch for reference/agentmem_ref/runtime/recall_control.py: declared 7d3d1410…, candidate b21d6fae…
```

The 9 extra skips at 34 are the seal-anchor tests. They run once `git fetch origin 'refs/seals/*:refs/seals/*'` has been done. `scripts/verify_seals.py` then reports 23 seals anchored and matching. The remediated suite count is 2628 + 22 new independent tests.

## 3. Phase B: independent adversarial tests

The tests are in `reference/tests/test_644_combined_independent.py`: 22 tests, with sub-tests. The before log was run on pristine de3dbe8; the after log on 46d84ad.

**Before: 9 failing assertions. After: 22/22 OK.**

| Property | de3dbe8 | 46d84ad |
|---|---|---|
| Receipt captured inside the planner before the result escapes; a defensive copy survives caller `list.clear()` | PASS | PASS |
| No false tamper on fresh results: empty query, no match, exact-identity refs, missing refs, very long query, refused candidates | PASS | PASS |
| No false tamper over all 126 original held-out scenarios (`receipt_on_heldout.py`: verified 126, false_tamper 0, crash 0) | PASS | PASS |
| Mutation detected: candidates add or drop, admitted drop, rank swap, route counts zeroed, extra route key, `routes_executed`, query, refusal reason or drop, policy, admission mode, `evaluated_at`, controller plan | 14/14 detected | 14/14 |
| Malformed counters: `None`, list, bool, negative, float, int key → `False` | PASS | PASS |
| **Hostile Mapping (raises on iteration) as route counts or refusals; plan replaced by `object()`; `recall=None`; receipt replaced by a string** | **FAIL: uncaught `RuntimeError` or `AttributeError` from `observation_unchanged()`** | PASS (`False`) |
| **`RecallObservationReceipt.matches_mutable_result` called directly with a hostile Mapping** | **FAIL: uncaught `RuntimeError`** | PASS |
| Missing or corrupt slot enumeration (non-JSON index key, `all_facts` unavailable, adapter audit missing) | raises, fails closed | same |
| Indexed census equals full-store scan, under the same admission and per-fact predicates, with the admitted list all, empty or truncated. Covers insert, state-change correction, dispute, forget, other project, restart and post-restart write/forget. | PASS | PASS |
| Cross-tenant and unregistered-scope rows written directly into the shared SQLite substrate, with a forced index rebuild | never counted (`out_of_scope` and `unknown_scope`); equals the full scan | same |
| Temporal: a future `valid_from` and an expired `valid_until` are obstacles; a past `valid_from` is clear; malformed dates are refused at write | PASS | PASS |
| No positive stop recommendation, even with mechanical coverage met and agreeing supports; `stop_attested=false`, `authority_effect=none` | PASS | PASS |
| Receipt `to_dict` claims no signature, revision, closure or authority; `replace(…, can_stop=True)` etc. raises | PASS | PASS |
| Public serialization hides refused or hidden candidate IDs (forgotten, other-project) | PASS. Only `candidate_count` is disclosed. | PASS |
| No state mutation (substrate digest and event count unchanged) by capture, verification, observer or witness; reports identical after restart | PASS | PASS |
| **Compound: observer on a result whose receipt no longer matches (route counts zeroed)** | **FAIL: reports `coverage_observed_unattested`, the same as an untampered result** | PASS: `recall_observation_unverified` |
| **Compound: observer on a result with no receipt** | **FAIL: `coverage_observed_unattested`** | PASS: `recall_observation_unverified` |
| Compound: a competitor hidden by deleting it from admitted, ranked and candidate lists | census catches it (`slot_evidence_not_admitted`) | same |

**Scope notes. These are accurate as documented, but must not be overstated:**
- **Unkeyed digest.** The content digest is unkeyed SHA-256. A caller who tampers with a result can re-mint a matching receipt with `capture_recall_observation`, and `observation_unchanged()` then returns `True`. It detects accidental or naive edits only. It is not attestation.
- **Unbound v6 fields.** `evidence_sufficiency_met` and `stop_reason` are not bound by the receipt, and flipping them is undetected. These are the v6 count-stop fields.
- **Count leak.** `to_dict()` discloses `candidate_count`, which is how many candidates, including refused ones, matched. IDs are not disclosed.
- **Guessable digests.** `query_digest` and `reader_digest` are unsalted, so they can be confirmed by guessing. The module docstring says so.
- **Missing docs.** No doc describes the receipt. Doc 81 is stale: it says the receipt is "staged on a different branch" and that "no passing results are claimed".

## 4. Phase C: original held-out replay

The harness is `heldout_bench.py`, sha256 **`25ce88ebdfa4ecc1377f1d60f6562f5d39f3b0e3040254854e8294eaffe75f6a`**. It was verified before every run, and cases, labels and scorer are unchanged. It has 21 categories × 6 entities: 48 safe cases (8 categories) and 78 unsafe cases (13 categories). The labels are embedded in the harness.

| Measure | published v6 `e98e6e7` (count signal) | e002536 | **de3dbe8** | 46d84ad |
|---|---|---|---|---|
| Stop recommendation on **unsafe** cases | 78/78 | 0/78 | **0/78** | 0/78 |
| Stop recommendation on **safe** cases | 48/48 | 0/48 | **0/48** | 0/48 |
| **False-clear diagnosis on unsafe cases** (`coverage_observed_unattested`) | — | 6/78 | **6/78** | 6/78 |
| Safe cases diagnosed clear | — | 37/48 | 37/48 | 37/48 |
| **F6 untyped competitor**: 6 cases | 6/6 stop | 6/6 false-clear | **6/6 false-clear** | 6/6 false-clear |
| Unsafe cases with a specific obstacle | — | 72/78 | 72/78 | 72/78 |
| Explicit competition / coexistence / change flagged | — | 6/6 · 12/12 · 6/12 | 6/6 · 12/12 · 6/12 | same |
| False conflict on case variants / support precision | — | 5/6 · 1.00 | 5/6 · 1.00 | same |

**Obstacle coverage on unsafe cases:**
- `value_coherence_unresolved` 30: conflict, multi_set, multi_one, unknown_cardinality, change_unapplied;
- `qualified_counter_evidence_unresolved` 24: extracted, negated, hedged change, attributed;
- `slot_evidence_not_admitted` 12: paraphrase and budget cap;
- `declared_temporal_boundary_unresolved` 6: expired validity;
- **unclassified 6: untyped competitor (F6).**

Safe cases not reading clear: facade correction 6 (`missing_declared_evidence`, F7) and case variant 5 (`value_coherence_unresolved`, F10).

The per-category diagnoses of de3dbe8 and 46d84ad are **identical to e002536**. The indexed audit and the receipt changed no held-out outcome.

**The 0/78 unsafe count is not evidence of useful adaptive stopping.** No tree after v6 can recommend a stop, so safe stops are 0/48 as well. The only signal is the diagnosis, and for F6 it is indistinguishable from a genuinely clear case.

## 5. Phase D: SQLite performance

All measurements are fresh, made with `perf644.py`. Each tree builds its own store, and all trees are measured sequentially on an otherwise idle machine. The query admits 8 of 8 candidates. Warm figures are 30 samples, cold 5 samples, reported as median / p95 ms. "Cold" means a fresh `AgentMemory.open`, then the first operation; the OS page cache stays warm.

| 10,000 facts | v6 `e98e6e7` | e002536 | de3dbe8 | 46d84ad |
|---|---|---|---|---|
| Governed recall (includes receipt capture where present) | 285.3 / 345.2 | 262.0 / 365.3 | 286.0 / 343.3 | 279.6 / 343.8 |
| Receipt capture alone | — | — | 0.20 / 0.26 | 0.19 / 0.23 |
| Receipt verification | — | — | 0.06 / 0.10 | 0.05 / 0.07 |
| Slot audit (e002536: full-store scan) | — | 617.7 / 686.6 | **12.3 / 19.2** | 12.3 / 13.5 |
| Combined observer | — | 661.3 / 760.1 | **15.8 / 23.5** | 15.3 / 17.2 |
| Index rebuild, warm process | — | 232.4 / 284.5 | 272.9 / 290.1 | 228.0 / 294.4 |
| Cold open | 1734.6 / 2456.3 | 1577.5 / 1604.5 | 1538.7 / 1606.2 | 1574.2 / 1717.6 |
| Cold first recall | 265.9 / 307.5 | 321.1 / 408.3 | 356.8 / 415.3 | 397.7 / 496.8 |
| Cold first index build | — | 250.8 / 292.8 | 257.2 / 343.5 | 222.6 / 298.3 |
| Cold first observer, index already built | — | 614.0 / 683.7 | 17.2 / 18.8 | 16.5 / 19.2 |

| Facts | slot audit, de3dbe8 | slot audit, e002536 | recall, v6 | recall, de3dbe8 | index build, cold |
|---|---|---|---|---|---|
| 1,000 | 1.57 / 2.58 | 62.0 / 80.9 | 27.0 / 33.0 | 28.4 / 43.0 | 17.0 / 25.6 |
| 3,000 | 4.39 / 6.79 | 184.1 / 244.9 | 81.2 / 103.0 | 84.0 / 122.0 | 87.0 / 94.5 |
| 10,000 | 12.27 / 19.15 | 617.7 / 686.6 | 285.3 / 345.2 | 286.0 / 343.3 | 257.2 / 343.5 |

Readings:
- **Receipt cost** is about 0.2 ms to capture and about 0.05 ms to verify. Recall differences between trees are within run-to-run noise.
- **The indexed audit is about 50× cheaper than e002536's full scan at 10k.**
- **It still grows linearly:** it walks and `json.loads` every index key, and the first observation in each process pays an index build comparable to one recall (about 250 ms at 10k).
- **The remediation adds no measurable cost** (46d84ad versus de3dbe8).

**Prior reported figures, not re-measured here:**
- earlier qualification: observer 608 ms at 10k on e002536 and 12.5 ms on 3539a25; held-out observer medians 1.27 ms on 14ea8a6 and 1.64 ms on 3539a25;
- this run's held-out medians are 2.18 ms on e002536, 2.17 ms on de3dbe8 and 2.22 ms on 46d84ad, against 3.8–4.3 ms for recall.

## 6. Isolation, restart and noninterference

- **Noninterference.** The original 31-section scenario (44 audit events) is byte-identical after normalisation, sha256 **`1a6b90a9…`**, the same digest as in all earlier qualifications. This holds on:
  - published v6 `e98e6e7`;
  - de3dbe8 with and without the observer;
  - de3dbe8 with the observer plus the transition witness plus receipt verification;
  - 46d84ad.
- **Planner benchmark.** The in-repo `run_retrieval_quality_benchmark.py`, which drives `ControlledRecallPlanner`, is identical on v6 and de3dbe8 except for the revision label.
- **Restart.** The observer, witness and receipt leave the substrate digest and event count unchanged, and reports are identical after reopen.
- **F12 reproduces unchanged on published v6 and the candidate.** A `ControlledRecallPlanner.recall` outside `run_governed_read` leaves the store unopenable ("SQLite canonical substrate digest mismatch"). This is pre-existing and not addressed.
- **Isolation.** See Phase B: other project, other tenant in a shared SQLite store, unregistered rows, forgotten, disputed and superseded facts. No count or ID leaks were found.

## 7. Phase E: governance

**On de3dbe8:**
- `check_runtime_baseline_equivalence.py --candidate de3dbe8…` exits 1 with the three errors in section 2. The declaration is **stale**: it pins 6 blobs and omits the receipt module and its alias.
- `validate_runtime_baseline_source.py` reports "declared successor … v7 (issue #644) is open", rc 0. `render_runtime_baseline.py --check` gives rc 0.
- META_LEDGER Entry #124 recomputes correctly: content `2a02395c…`, chain `092b151b…`, previous hash equal to #123's `f4e71a5f…`. It names a different branch (`644-indexed-safety-fix-no-ci`) and "six protected blobs", so it does not describe de3dbe8.

**On the validation branch at 46d84ad:**
- `declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v7-declaration.json` regenerated the pins. A second run is a no-op.
- **8 protected blobs**, each checked with `git rev-parse 46d84ad:<path>` against the declaration, and equal to the full changed protected set:

| Path | Blob |
|---|---|
| `evidence_sufficiency.py` (alias) | `55edbc61` |
| `governed_transition_witness.py` (alias) | `c6382106` |
| **`recall_observation_receipt.py` (alias)** | **`cfeeb694`** |
| `runtime/adapter.py` | `36be4dec` |
| `runtime/evidence_sufficiency.py` | `9008fb21` |
| `runtime/governed_transition_witness.py` | `6deb6908` |
| `runtime/recall_control.py` | `5136922f` |
| **`runtime/recall_observation_receipt.py`** | **`f80d3145`** |

- `check_runtime_baseline_equivalence.py --candidate 46d84adeecf7f0ec034e7ec8c356bbb3859c8e03` reports **TRANSITION**: baseline v6, declared successor v7 (issue #644), protected surface = frozen `e98e6e7` + 8 declared blobs, deltas none. The protected-file checks were not loosened.
- The register still has v6 as its last published entry. There is **no v7 record or publication**.
- **META_LEDGER Entry #125** (candidate-only, VALIDATE) is appended and chained to #124. Content hash `481a7c4a…`, chain hash `a44d073f…`. It adds 28 lines, deletes none, and preserves #124 and the CHANGES REQUIRED history. It states "not a PASS, publication, qualification, merge approval, or benchmark claim."

## 8. Phase F: replays and lanes

| Required evidence | Outcome |
|---|---|
| Public gauntlet `gauntlet-orchestration-retrieval-probe-v1` | **Probe ran, but it is not qualification evidence for v7.** `agent-memory gauntlet run --system examples/gauntlet/agent-memory-runtime-baseline-v6.json --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset`. Main `3eebb6d` (checker PASS against v6) and 46d84ad both pass every assertion of the workflow's validation step: complete, stdio, public facade only, 3 samples, **exact_top1 1.0 (3/3)**, authority none. **Blocker:** the repository runs this gauntlet only when the checker reports PASS. No v7 adapter or manifest exists. On 46d84ad the manifest's `system.revision` label still names `e98e6e7`, which is false for that run. |
| AMB `amb-precisionmembench-retrieval-v6`, agent-memory row | **Ran locally, credential-free.** Frozen AMB `03c1d0f`; fixtures and `input_sha256` verified; upstream self-check 77/77, matching the accepted v6 self-check. Published v6 and 46d84ad are **per-query identical to the accepted v6 evidence**, including retrieved context: 15/77 correct, active 4/43, mean precision 0.1806, mean recall 0.9535, ID resolution source_id 686. The cross-fact sidecar is identical (73 lines). *Environment note:* the proxy denies `openaipublic.blob.core.windows.net`, so tiktoken's `cl100k_base` was rebuilt from a public Hugging Face vocab and **accepted only after matching tiktoken's pinned sha256 `223921b7…`**. It is used only to count context tokens. |
| LongMemEval-S `longmemeval-s-retrieval-parity-v6`, agent_memory rows | **Ran locally**, all 500 questions in source order, input sha256 `d6f21ea9…` verified, `--agent-memory-budget 50`, frozen scorer blob `6b9c2373`. **Session:** v6 and 46d84ad give identical per-question rankings and metrics across 500 rows; headline recall_all@5 0.823389, ndcg_any@5 0.863142, recall_all@10 0.892601, ndcg_any@10 0.878274; governance totals equal to the accepted v6 evidence. **Turn:** v6 and 46d84ad give identical per-question rankings and metrics across 500 rows, with recall_all@5 0.601432, ndcg_any@5 0.648611, recall_all@50 0.859189, ndcg_any@50 0.711426, and governance totals (103,356 admitted, 0 refused, 0 failures) equal to the accepted v6 evidence. Each row took about 264 s (session) or 800 s (turn) of wall time. |
| Five replays: `typed-sufficiency-noninterference-and-negative-controls-v1`, `governed-persisted-typed-slot-sufficiency-admission-recheck-v1`, `governed-admitted-typed-value-coherence-v1`, `committed-governed-transition-witness-v1`, `same-slot-safety-counterevidence-and-immutable-stop-gate-v1` | **BLOCKED: no executable definitions exist.** These IDs appear only in `baseline-v7-declaration.json` and docs 77 and 78, on every one of the 25 `origin/*644*` branches. The v6 precedent `mesa-formal-v3` had a frozen fixture, test and report; these have none. Phases B, C and the noninterference scenario cover some of the same ground, but they are **not** these replays and must not stand in for them. |

These lane runs are local, unsigned reproductions. They are not importable workflow evidence: there is no workflow run ID, and the lane rows pin the v6 declaration blob. They establish behavioural equivalence to published v6, not v7 acceptance.

## 9. Remaining limitations

- **F6:** untyped same-slot competitors are invisible to the typed census. 6/6 held-out cases read `coverage_observed_unattested`.
- **F7:** a public `correct()` cannot carry a typed write. 6/6 facade corrections read `missing_declared_evidence`.
- **F10:** values are compared by literal equality. 5/6 case variants read as conflicts.
- **F12:** a SQLite planner read outside `run_governed_read` breaks the next open. This is pre-existing in v6.
- **Receipt trust:**
  - unkeyed content hash, re-mintable by the caller;
  - no state revision, no snapshot or slot-closure attestation;
  - v6 stop fields unbound;
  - `candidate_count` disclosed;
  - query and reader digests guessable.

  The code says all of this correctly. Nothing in it represents the receipt as signed, revision-bound, complete or stop-authorizing.
- **Census cost:** linear in the number of index keys, plus a per-process index build.

## 10. Remediation (46d84ad, isolated)

Each change was preceded by a recorded reproducer (`836b688`) and the invariant it enforces.
1. **Invariant: receipt verification is total and fails closed.** `observation_unchanged()` rejects a non-receipt and wraps verification, and `matches_mutable_result` catches any exception. Both return `False` instead of raising.
2. **Invariant: an unverified recall never reads as clean coverage.** `observe_persisted_typed_coverage` reports `recall_observation_unverified` in place of `coverage_observed_unattested` when the receipt is missing or mismatched. Obstacle diagnoses keep precedence, and no stop is ever proposed. All 29 candidate `test_recall_control` assertions are unchanged and pass. The held-out diagnoses and noninterference digest are unchanged.
3. The declaration was regenerated by the sanctioned tool (8 blobs), and ledger Entry #125 was added.

## 11. Verdict and minimal recommendations

**de3dbe8: CHANGES REQUIRED.**
- Its own full suite fails because the v7 declaration is stale.
- The sufficiency observer ignores the receipt the same tranche introduces, so a tampered or receipt-less result reads as clean coverage. The commit "reconcile immutable receipt capture with indexed governed audit" (`ed06df3`) only captures the receipt.
- Receipt verification raises on malformed input.

The indexed audit itself is sound: it equals the full scan, holds isolation, is about 50× faster at 10k, and leaves default recall, AMB and LongMemEval identical to v6.

**46d84ad (validation): all local checks pass**, with TRANSITION, but **formal v7 qualification is BLOCKED by missing evidence:**
- the five replays have no definitions;
- no v7 public-gauntlet adapter or manifest exists;
- the lane runs are local, not workflow-imported.

Minimal next steps:
1. Adopt the two narrow fixes in 46d84ad, or equivalents, and re-declare with the sanctioned tool.
2. Implement and freeze the five declared replays: fixture, runner, test and report, following the `mesa-formal-v3` pattern.
3. Add a v7 public-gauntlet manifest and adapter after acceptance.
4. Key the semantic index by slot so the audit stops scanning every key.
5. Bind `evidence_sufficiency_met` and `stop_reason` into the receipt, or document them as unbound.
6. Decide the F6 policy before any stop authority is considered.
7. Update doc 81, and add a receipt doc that states the non-attestation boundary.

This is not a production-readiness, release or benchmark-leadership claim.
