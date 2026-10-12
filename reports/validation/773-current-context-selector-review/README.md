# #773 Independent adversarial review: opt-in current-context selector

| | |
|---|---|
| Candidate | `implementation/773-explicit-current-context-selector-no-ci` @ `9c9bf4de493c76fec44b5d9c21af89849a2a9f73` (verified) |
| Frozen v7 parent | `9b025f945e7ec4a1e349e56bba251e3122413e88` (verified) |
| Validation branch | `validation/773-current-context-selector-review` (forked from the exact candidate) |
| Environment | Claude Code cloud container, Linux, Python 3.13.16, `reference/requirements.txt`, full clone; no GitHub Actions |
| Runtime blobs (`runtime/runtime_composition.py`) | v7 parent `65a39d5e…` → candidate `bbf12bf3…` → repaired `0d5c5da1…` |
| **Runtime qualification verdict** | **CHANGES REQUIRED**: two defects repaired here (D773-1 temporal correctness, D773-2 usefulness) that need adoption; no successor declaration exists; frozen-lane parity cannot be shown without one |

The frozen v7 declaration, baseline register, #770 lanes and gauntlet fixtures are byte-identical to the v7 parent (`git diff 9b025f9 HEAD -- reports/runtime reports/validation/770-v7-lane-freeze reference/fixtures/gauntlet` is empty). `runtime_composition.py` is the only protected file changed. Nothing was merged or published, and there is no PR.

## Tests

| Run | Candidate `9c9bf4d` | Repaired |
|---|---|---|
| `test_773_current_served_context.py` (10 authored) | 10/10 OK | 10/10 OK |
| 13 related temporal/admission/ranking/currentness suites | all OK (`logs/C_related_suites.log`) | all OK |
| `test_773_adversarial_review.py` (this review, 9) | **D773-1 fails, D773-2 ×2 fail**; 6 controls OK | 9/9 OK |
| Full reference suite | 2720 run, 5 failures | 2729 run, same 5 failures |
| `check_runtime_baseline_equivalence.py --candidate HEAD` | exit 1: undeclared protected change | exit 1: same |
| `verify_644_v7_replays.py --reexecute` | — | all 5 replays STALE ("runtime files differ"); not re-executed |

The 5 full-suite failures are identical on both heads:
- **4 are the intended freeze guards:** undeclared baseline change, the two v7 replay-staleness tests, and v7 runtime identity.
- **1 also fails on the v7 parent and on `main`:** `test_gauntlet_durability`, `adapter_eof`.

## Defects (failing test committed first, then repaired)

### D773-1: temporal correctness. A reference instant before a governed state change is served with the later value.

- Failing test `fcc36c2`, repair `61c6dd1`.
- **Reproduction** (`logs/C_probe_D773_1_candidate.log`): PostgreSQL 15 is replaced by PostgreSQL 16 through a governed `state_change` in 2026. `current_served_context(..., reference_time="2025-11-25T00:00:00Z")` serves `pg16` (`unknown_temporal_basis`) as current context for November 2025. `pg15`, the value that actually governed then, was refused at admission (`superseded_not_current`). With a declared `valid_from` on `pg16` the context is instead *empty*. Either way the result claims to describe an instant it cannot represent.
- **Cause:** the selector pins the reference instant into ranking applicability, but canonical current-state admission has already applied every later lifecycle transition.
- **Repair** (opt-in method only):
  - If any **domain-eligible** candidate refused as `superseded_not_current` was replaced by a **state change** whose end (declared `valid_until`, else `replaced_at`) is after the instant, raise `ValueError` and direct the caller to historical/as-of recall.
  - Error corrections never held, so they are ignored.
  - Out-of-scope candidates are ignored, so the refusal cannot reveal them (pinned by test).
- The authored tests' use of past instants with no later transitions is unaffected.

### D773-2: usefulness. Excluded evidence that answers "is it still in effect?" becomes unreachable.

- Failing tests `9c0e8e5a`, repair `8a72d9f`.
- **Reproduction** (`logs/D_probe_selector_usefulness.log`):

  | Question | v7 path with instant T | Selector |
  |---|---|---|
  | "Is the 2025 winter firmware freeze still active today?" | the ended freeze window, which is exactly the evidence for "no, it ended 1 Dec 2025" | **empty context** |
  | "Is the checkout discount promotion still running?" | ended promotion, plus `pricing` | `pricing` only |

  The selector reported only a *count*, so a consumer could not state *when* something ended without a second, unconstrained recall. Empty context is also what tends to make a downstream model guess.
- **Repair:** `CurrentServedContext.known_inapplicable_refs`. It is admitted-only, in ranked order, bounded by the budget, disjoint from `served_refs`, and validated. Expired or future evidence is still **never** represented as current.

**Recommendation:** bump `selection_policy_version` to `0.2.0` when adopting. I left it at `0.1.0` because the authors' validation pins it.

## Challenges that held on the candidate (pinned in `SelectorControls` or the probes)

**Interval boundaries:**
- Inclusive start and exclusive end are exact, including at microsecond resolution.
- Offset forms resolve to their UTC instant: `+01:00`, `-01:00`, `+05:30` straddling both window edges.

**Malformed reference times:**
- **Rejected before recall:** missing or unzoned instants, `+99:99`, month 13, hour 24, a space separator, lowercase `z`.
- **Accepted but meaningless:** `-00:00` (the RFC 3339 "unknown local offset") and year `0001`. Recommend rejecting `-00:00`.

**Caller-declared vs inferred time:**
- The instant is used only when passed explicitly. The selector never reads a clock, stored text or labels.
- Default `multi_route_recall` (no instant) is **byte-identical** across v7 parent, candidate and repaired runtime, in served rows and full ranked admissions, on both holdouts (see `phase-d-results.json` on the #771 validation branch).

**Unknown validity:**
- Undeclared memories stay `unknown_temporal_basis` and are served.
- They are counted, never upgraded to verified.

**Cross-fact limitation:**
- `limited_by_cross_fact_state_change` never fired on untyped text, so there were no false exclusions in 5 natural pairs (`logs/C_probe_cross_fact.log`).
- It also did not catch an obsolete untyped "Jenkins" deploy fact. On untyped corpora the selector acts **only** on declared validity windows.

**Privacy:**
- Served refs are a prefix-preserving subsequence of governed `ranked_admitted`.
- Hidden-project memories change neither the selection nor the counts.
- No prohibited exposure in any run.

**No authority:**
- `complete_evidence_attested=False` and `authority_effect="none"`, both enforced by validation.
- No stop or abstention field.
- An empty selection is just an empty tuple, never reported as abstention.

## Comparative measurement: v7 path vs selector (Phase D, same instant `2026-10-12T12:00:00Z`)

The full tables are in `reports/validation/771-evaluator-cedarline-qualification/PHASE_BD.md` on the #771 validation branch.

| | Halcyon v1.1 | Cedarline v1.1 |
|---|---|---|
| v7 composed, **no instant**: P0 stale cases | 1 (H09) | 1 (C11) |
| v7 composed **with instant T**: P0 stale cases | **0** | **0** |
| #773 selector with T (candidate or repaired) | **0**, served rows **identical to v7-with-T on every question** | **0**, identical |
| Answer@1 / all-critical / precision (every variant) | 0.619 / 0.905 / 0.444 | 0.700 / 0.700 / 0.475 |
| Distractors served, no instant → with T | 36 → 37 | 34 → 35 |
| Valid evidence excluded by the selector | none | none |

**Do not claim a G2 fix from this slice.**
- The holdout stale-exposure improvement comes entirely from **passing an explicit instant to the existing v7 ranking policy**. That policy already demotes known-expired windows past the budget.
- The selector's own exclusion changed **zero** served items on either holdout; it removed only already-demoted items beyond the budget.
- Its genuine contribution appears only when the budget exceeds the number of applicable candidates (the G2 minimal repro: v7-with-T still serves the expired freeze at rank 2, the selector removes it).
- In "still in effect?" questions, that same exclusion withholds the answering evidence (D773-2).
- The freed budget slot went to a distractor on both holdouts, so P1 and P2 did not improve.

## Remaining risks and recommendations

1. **Successor declaration required.** The change is protected runtime. All v7 replay evidence is STALE until a sanctioned post-v7 declaration names blob `0d5c5da1…` (or the authors' equivalent) and the v7 lanes are re-executed under it. The frozen v7 declaration must not be edited.
2. **Decide the D773-1 policy explicitly.** Fail closed (implemented) or route to as-of admission. The latter is the more useful long-term behaviour.
3. **Prefer passing the instant to `multi_route_recall` by default for current-intent callers.** That alone delivered the measured P0 improvement, with no new protected surface.
4. **The selector does not address G1 or G6** (as its own plan states).
5. **Reproducibility note:** the probe scripts (`probes/`) reference scratch paths for the runtime and evaluator checkouts; adjust the two paths at the top of `selprobe.py` to replay them.
