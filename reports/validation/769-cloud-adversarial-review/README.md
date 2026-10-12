# #769 Cloud adversarial implementation review

| | |
|---|---|
| Candidate branch | `implementation/769-post-v7-competition-diagnostics-no-ci` |
| Candidate SHA (verified) | `9bbca2a4b01b60ec31da5d3148e02fe56032a6d7` |
| Contract branch / SHA | `evaluation/769-untyped-competition-contract-no-ci` @ `0c4b47060bfecc4f1d38374925f5f8d81ee89c2a` (read-only) |
| Validation branch | `claude/great-johnson-9n6b5i` (candidate + regression tests + repairs + evidence) |
| Environment | Claude Code cloud container, Python 3.13.16, deps from `reference/requirements.txt`, full (unshallowed) clone |
| Verdict | **CHANGES REQUIRED** (details below) |

No GitHub Actions were triggered. Workflows run on pushes only for `main`, and no PR was opened. Nothing was merged. `reports/runtime/baseline-v7-declaration.json`, accepted v6 evidence and the frozen #770 v7 lanes are byte-identical to the candidate (`git diff 9bbca2a HEAD -- reports/runtime` is empty).

## Verdict: CHANGES REQUIRED

The opt-in observer is well scoped. It never recommends stopping, never claims to have enumerated everything, its output carries no fact identities or text, and default recall is unaffected. But its main protection, "verify the receipt and the reader context before using any candidate IDs", can be bypassed in three ways that the author's tests don't cover. The candidate also breaks an existing repository test. Each defect has a failing regression test, committed before the repair, plus a minimal repair on this branch. The candidate itself still needs those changes, or equivalent ones.

## Defects (each regression was committed failing at `2dd3d0b`, before repair)

| ID | Severity | Defect | Regression test | Repair |
|---|---|---|---|---|
| D1 | High (privacy contract) | **Context re-read (time-of-check/time-of-use).** `observe_competition_diagnostic` reads `context` once for `matches_reader_context`, then the governed reads read it again. A `RecallContext` subclass that answers differently the second time passes the check and then reads with a wider authority. With a typed memory in a hidden project, the diagnosis changed from `scope_enumeration_unattested` to `typed_slot_obstacles_observed`, so the hidden memory influenced the output. | `DefectRegressions.test_context_object_cannot_widen_reader_authority_after_receipt_check` | Copy the context once into an exact `RecallContext` (`_reader_snapshot`). That copy is used for the check and for every read; a hostile context object fails closed. |
| D2a | Medium-High (integrity) | **Forged receipts are accepted.** The receipt is an unkeyed SHA-256 over caller-visible data, and `capture_recall_observation` is public. A caller can add a never-recalled reference and recompute a matching receipt. The observer then reports `mutable_receipt_match` and counts that reference. | `test_forged_receipt_from_public_helper_is_not_a_receipt_match` | The planner records the content digests of receipts it issued (bounded to 4096, in-process, behind a lock). The observer refuses any receipt this planner did not issue. |
| D2b | Medium-High (tenant isolation / ID collision) | **Cross-store replay with colliding IDs.** Fact IDs are deterministic per store (`ref-0004`, ...). Store A's result passed to store B's planner, with domain names that look the same, is accepted. The diagnostic then reports on unrelated facts in B that B never recalled (B's `ref-0004` was "Weather in Lisbon"). | `test_cross_store_replay_with_colliding_identifiers_is_unverified` | Same issuer registry as D2a. |
| D4 | Medium (fails frozen contract case C16) | **A stale observation produces a cleaner diagnosis.** If an admitted competitor is deleted (or disputed) through governance after recall, the receipt still matches. The diagnosis drops from `typed_values_unresolved` to `scope_enumeration_unattested`, the cleanest possible diagnosis. The frozen contract requires a stale receipt to yield `observation_integrity_unknown`. | `test_governed_deletion_after_recall_is_stale_not_a_cleaner_diagnosis` (+ `RepairCoverage.test_dispute_after_recall_is_stale`) | If any admitted reference is no longer admitted when re-checked, return `recall_observation_unverified` with no counts. |
| D3 | Low (CI-breaking) | **Package layout.** The candidate turns `tests.test_package_layout ... test_check_reports_layout_matches_table` red: `runtime/competition_diagnostics.py` is not in the layout table of `scripts/restructure_package.py` and has no compatibility alias. | existing repository test | Register the module and add the alias generated from `alias_source()`. |

Repair commit: `892bcb4`. It changes `recall_control.py` (blob `77e6ba27…`), adds the alias `reference/agentmem_ref/competition_diagnostics.py`, and changes `scripts/restructure_package.py`. The only change to `recall()` is one bounded bookkeeping insert per call; its return values are unchanged (see equivalence below). Results from a different planner instance, or from before a restart, now fail closed. That is intentional.

## Adversarial cases that already held on the candidate (no change needed)

These are in `reference/tests/test_769_adversarial_validation.py`. They run against the real SQLite-backed `ConfiguredCompositionRuntime` and the real `ControlledRecallPlanner`, not against copies of the helpers.

- Swapping in a different `task_ref` is rejected before any read. The authored tests only covered principal, project, purpose and domains.
- Domain order carries no authority (it is a sorted set in the digest).
- **Seeded metamorphic property** (6 random corpora): adding any mix of hidden memories (in a foreign project, deleted, disputed, or written by a foreign tenant to the same substrate) never changes `to_dict()`.
- Lexical twin: an untyped "Aster service endpoint is /v2" next to a typed "/v1" counts only as untyped presence (`identity_unverified`) and never as a typed conflict.
- A near-identical slot (`Aster services|endpoint`) is not treated as a competitor. Lexical similarity is never taken as identity.
- Pipe-ambiguous slots: `typed_slot("a|b","c") == typed_slot("a","b|c")` collide in `typed_proposition` (this predates #769). The observer rejects such needs with `ValueError`, so the collision cannot merge two propositions here.
- A truncated route budget (limit 1, 6 typed facts) still abstains and never claims complete enumeration. The census reports `typed_slot_obstacles_observed`.
- The projection has a closed key set and never echoes fact IDs, values, subject text, tenant, project or principal.
- An authoritative `CompetitionDiagnostic` (stop / attested / bool count / negative count) cannot be constructed.
- Default recall gives identical output (admitted, ranked, refusals, receipt digest, stop reason, route counts) whether or not the observer ran in between.

## Test execution (exact SHAs)

| Suite | Candidate `9bbca2a` | Repaired head |
|---|---|---|
| 9 authored #769 integration tests | 9/9 OK | 9/9 OK |
| `test_recall_control.py` | 29/29 OK | 29/29 OK |
| Adversarial suite (this review) | 4 FAIL (D1, D2a, D2b, D4), 10 OK | 17/17 OK |
| Full reference suite | 2719 run; 8 FAIL in the shallow container clone (log). After unshallowing, the 2 register-pin failures pass, leaving 6 | 2733 run (before the 3 `RepairCoverage` tests were added; full 26-test #769 run passes); 5 FAIL |

How the remaining full-suite failures break down (identical classification on both heads unless noted):

- **Expected protected-freeze guards (4):** `test_benchmark_integration_contract…runtime_baseline_equivalence` ("undeclared protected change"), the 2 `test_770_v7_lane_freeze_independent.ReplayEvidenceFreshness` tests (v7 replay evidence becomes STALE), and `test_644_v7_gauntlet_identity…own_checkout` (`runtime_identity_unverified`). These are the intended response to an undeclared post-v7 runtime change.
- **Predates #769 / environment (1):** `test_gauntlet_durability…first_durability_slice` fails with `adapter_eof` identically on the #770 base `9b025f9`.
- **Introduced by the candidate and repaired (1):** `test_package_layout` (D3).

Protected-runtime checker (`scripts/check_runtime_baseline_equivalence.py --candidate HEAD`): exit 1 on both heads.

- Candidate: undeclared `runtime/competition_diagnostics.py`; declared-blob mismatches for `recall_control.py` (`ac7a3ef8…`) and `recall_observation_receipt.py` (`5331fe9e…`).
- Repaired: additionally lists the alias `agentmem_ref/competition_diagnostics.py`, and `recall_control.py` is now `77e6ba27…`.

The frozen v7 declaration was **not** modified. A sanctioned successor declaration is still required, and `reports/runtime/proposals/769-post-v7-observer-overlay.json` needs its blob for `recall_control.py` updated and the alias added once a repair is accepted.

## Frozen 32-case contract

`evaluate_contract_against_runtime.py` reads the contract fixture (sha256 `801bc1c7b51b4495…`) and evaluator with `git show` at `0c4b470`, so its inputs and expected outcomes are untouched. It runs the frozen evaluator's self-check (32 cases, 0 positive stops). It then builds a live store for each case, runs the observer, and maps the runtime result back into contract vocabulary.

| | Candidate | Repaired |
|---|---|---|
| Cases passing (safety, receipt, facet, state) | 31/32, **C16 fails** (stale receipt reported as `mutable_receipt_match`) | **32/32** |
| Positive stops / reviewable signals | 0 / 0 | 0 / 0 |
| Conservative divergences | C02, C03, C12, C13 | same |

Facets the runtime cannot express are recorded per case and checked for a stricter outcome instead: `attested_complete`, `partial`, admission `unverified`, and `controller_estimate` (the runtime ignores the controller's target, as required).

Conservative divergences: the runtime reports `typed_values_unresolved` for values that differ only in whitespace or case (`/health` vs ` /health `, `/HEALTH`), and `typed_value_posture_unresolved` for multi-cardinality or null-cardinality values. The contract labels these non-conflicts. This is safe (it errs toward abstaining) but costs usefulness.

**Contract branch defect:** `reference/tests/test_769_untyped_competition_contract.py` on `0c4b470` errors on every assertion (33/33). It stores `assess` as a class attribute, so `self.evaluate(x)` passes `self` as the first argument. The branch was never executed ("no-ci"). In a scratch copy, wrapping it in `staticmethod(...)` makes all 6 tests pass. The branch was not modified.

## Observer overhead (durable SQLite, `benchmark_observer_overhead.py`)

Corpus (scales 1k and 3k; 10k not reached, see below) written through governed `retain`:

- 0.4 % typed facts in the target slot, 0.4 % untyped mentions of the target, 33 % typed facts in other slots (about N/4 distinct subjects), 5 % hidden-project facts, the rest filler.
- Each store is then recovered from disk.
- Cold = first call after recovery, with a fresh SQLite connection and empty in-process caches. The OS page cache was not dropped, so cold numbers are a lower bound.
- Warm = median of 15 calls.

| Memories | Head | Store build (governed `retain`) | Default recall cold / warm median (ms) | Observer cold / warm median / p90 (ms) | Observer `get_fact` rows per call | Full-table scans per call (cold / warm) | Rows read per admitted ref (warm) |
|---|---|---|---|---|---|---|---|
| 1,000 | candidate `9bbca2a` | 45.4 s | 8.95 / 7.04 | 4.05 / 1.80 / 3.04 | 88 | 1 (1,000 rows) / 0 | 4.4 |
| 1,000 | repaired | 46.3 s | 5.33 / 4.57 | 4.53 / 1.79 / 1.91 | 88 | 1 (1,000 rows) / 0 | 4.4 |
| 3,000 | candidate `9bbca2a` | 390.7 s | 11.9 / 12.95 | 13.17 / 4.75 / 5.02 | 104 | 1 (3,000 rows) / 0 | 5.2 |
| 3,000 | repaired | 389.2 s | 19.06 / 18.34 | 14.36 / 4.97 / 5.10 | 104 | 1 (3,000 rows) / 0 | 5.2 |
| 10,000 | both | **not reached**: stopped after more than 60 CPU-minutes, still inside store construction | – | – | – | – | – |

The two heads ran at the same time on 4 shared vCPUs, so the default-recall columns are noisy between heads. The observer's read counts are identical, as expected: the repair adds no reads. The 10k point was abandoned deliberately. Governed `retain` is roughly quadratic (3× the memories cost about 8.5× the build time), so a 10k store would take more than an hour to build before any observer measurement. That build cost is a separate scalability finding. The observer data available show **no full-store scan per warm call** and a row count that is almost flat (88 to 104 for 3× the store). Warm latency still grows roughly in proportion to the number of distinct slots (1.8 ms to 5.0 ms), because of the O(slots) key walk described below. Extrapolating that key walk to about 2,500 slots at 10k suggests roughly 15 ms warm. That is an estimate, not a measurement. Raw per-scale JSON lines are in `logs/benchmark_*.log`.

**Read amplification:**

- Each warm observer call reads about 4–5 `get_fact` rows per admitted reference: `current_governed_typed_claim` reads the fact twice, and every admitted reference is visited twice (once in `observe_persisted_typed_coverage`, once in the untyped loop), plus the slot census.
- There is **no** full-store scan per call.
- The first observation after a restart materialises the whole tenant once (`all_facts()`, N rows) to build the semantic slot index. Writes then maintain that index incrementally.
- Warm latency still grows with store size even though row reads stay almost flat. `current_typed_slot_obstacles` walks every key of the semantic index and `json.loads` each one on every call, so CPU cost is O(number of distinct slots). This predates #769 (it comes from #644) but is inherited.
- Default recall equivalence (5 queries, observer-touched store vs independently recovered twin): identical at every scale.
- Separately, building the store is roughly **quadratic** in governed `retain` (about 46 s for 1k, about 390 s for 3k), which deserves its own issue.

## Architectural notes (not blocking this slice)

1. The receipt stays a change detector, not an attestation. The issuer registry only stops forged and foreign receipts from reaching *this* diagnostic. `observe_persisted_typed_coverage` and other receipt consumers from #644 still accept recomputed receipts.
2. New writes after recall are invisible to staleness detection: there is no read revision. The diagnostic correctly never attests completeness, but it is a read-time view, not a snapshot.
3. Pipe-ambiguous typed slots collide in `typed_proposition.typed_slot`. This predates #769 and should be fixed by escaping or rejecting `|` in subject/attribute.
4. Exact-string comparison of typed values makes whitespace and case variants look like conflicts (C02/C03).
5. Reuse a single visibility pass in the observer to halve `get_fact` reads, and index the semantic slot map by slot to remove the O(slots) key walk.

## Reproduce

```bash
git checkout claude/great-johnson-9n6b5i
python -m pip install -r reference/requirements.txt
python -m unittest discover -s reference/tests -t reference -p "test_769_*.py"
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD      # expected: exit 1, undeclared
python reports/validation/769-cloud-adversarial-review/evaluate_contract_against_runtime.py --repo . --out /tmp/contract.json
python reports/validation/769-cloud-adversarial-review/benchmark_observer_overhead.py --repo . --out /tmp/bench.json
```

To reproduce the failing regressions on the candidate, check out `9bbca2a` and copy `reference/tests/test_769_adversarial_validation.py` from `2dd3d0b`.
