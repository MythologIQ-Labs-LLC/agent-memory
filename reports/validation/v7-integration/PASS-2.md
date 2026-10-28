# v7 integration candidate, pass 2: #840 repair, independent review, regenerated evidence, lanes

**Status: INTEGRATION CANDIDATE, NOT QUALIFIED FOR PUBLICATION.** The pass continues from `0f90aa8e` (pass 1,
`README.md`, sealed by META_LEDGER #130). Nothing was merged, published, tagged, released or closed. No Actions were
run, and every commit is `[skip ci]`. The live register is unchanged, and no historical evidence was modified.

| Identity | Value |
|---|---|
| Runtime-final commit | `9eb723911baa5b5b05593a8bf7ecd01335969d30`: the protected runtime does not change after it |
| Protected runtime blobs | 28 declared, Runtime Baseline checker `TRANSITION` v6 → v7, delta `public_contract_version 1.6.0 -> 1.8.0` |
| `reference/agentmem_ref` tree | `975b09412b096a9eac4a92478e7d3a39700ba5d9` since `b4551edb` (lane specs under `evaluation/` re-pinned; protected surface unchanged) |
| Declaration blob | `981108866e45a46b9e96ab283517324d6349e586` (lanes pin it) |
| Lane executing revision | `6b3c154d6b50388cf8456d3b06055d5426ced330` |

## 1. #840 temporary-file staging (Priority 1)

Details are in [`840-temporary-staging/`](840-temporary-staging/): the preregistration, the fail-first logs and
`ASSESSMENT.md`.

**Finding.** Five integrated whole-file writers staged through predictable temporaries opened with truncation:

- the packaged config on first open;
- `restart_runtime`, `configured_restart` and `checkpoint_migration` records;
- journal restore.

A planted symlink redirected the write outside the store. Shared names broke concurrent writers. A failed fsync or
rename leaked the temporary. This was confirmed by preregistered tests S1–S6 and I1–I4: **26 RED at `0f90aa8e`**,
exactly as predicted, after one harness correction recorded before any runtime change.

**Repair** (`6a12e1cd`). One helper, `_exclusive_temporary` / `_stage_and_replace`:

- `O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC` under a random name;
- the temporary is unlinked on any failure before the rename;
- function names, payloads, fsync order and file modes (`0o666 & ~umask`) are unchanged.

Result: 10/10 GREEN, and the related suites pass. #840's `0o600` permission change is not carried; that is an owner
decision.

**Host-activation guard: assessed, not carried.** It is a host policy, not a runtime repair:

- #809 keeps un-upgraded legacy facts conservative;
- store-open 1.0.0 already refuses multi-project legacy stores at `open`;
- carrying it would add a protected API module.

#840's own tests on the integrated runtime gave 9 pass and 2 refused at `open`.

## 2. Independent integration review (Priority 2)

The review record and dispositions are in [`review-findings/REVIEW.md`](review-findings/REVIEW.md). There was no
critical merge defect. Two pre-existing security findings were fixed with fail-first tests (13 RED → GREEN):

| ID | Severity | Fix |
|---|---|---|
| RF1 | medium | A facade handle's identity (`tenant`, `scope`, `actor_id`, `purpose`, `task_ref`, `store_profile`, `charter_version`, `runtime`, `root`) is read-only once bound, and direct construction must name `store_profile`. Before the fix, a handle holder could re-bind a scope-distinct handle to another project's memory, or brick a single-project store with one write. |
| RF2 | low | The deleted-owner fence consults only deleted generations the writer is scope-eligible for. Another scope used to learn that a deleted owned lineage existed. |

Also fixed:

- the W4 envelope test now compares outcome for outcome;
- `unittest.main()` was placed before a test class, so running the file as a script skipped it;
- the sensitivity harness overstated its notes;
- docs/44 and the `store_contract` docstring were stale.

**Reachability.** The test-only tenant-wide opener is absent from the built wheel and referenced nowhere in the
package, `examples/` or `scripts/`. Its effect is now reachable only by host code that constructs a handle naming
its profile, or by filesystem write access to the store.

## 3. Regenerated evidence (Priority 3)

| Item | Result |
|---|---|
| **Security replays, DSL/5 on `scope_distinct_v1`.** `cross-scope-write-authority-denial-v5` (W1h, W2h, W7c-h and W8-h host-layer cases; W4/W4b identity changes refused with `ValueError`), `deleted-lineage-generations-and-restart-v4`, `public-tombstone-redaction-and-observer-separation-v4`, `evidence-reference-authorization-v2` | **Preregistration:** an independent pre-execution review (`security-replays-dsl5/PREEXECUTION_REVIEW.md`) found F-1 to F-8, all applied before first execution. **First execution at `a99f1ee7`:** 51/52. One fixture-token defect: `v1` matched inside `charter:local-v1`, not a disclosure. `-v4` was superseded by `-v5`, changing that one token. **`-v5` at `81d31ca3`:** 17/17. The other three passed 11/11, 8/8 and 16/16. Residual, recorded in the fixtures: host-layer correct, dispute and permanent deletion are not replayed by DSL/5; the tenant-wide unit suites cover them. |
| `scope-safe-graph-discovery-v2` (frozen DSL/4) | 11/11 at `da5c3487` |
| **#644 replays**, all five, at `da5c3487` | 19/19, 18/18 (admission family on the scope-distinct runner `run_644_v7_replays_sd.py`, with the frozen fixture unchanged), 16/16, 12/12, 39/39 |
| Verifiers with `--reexecute` on the new evidence and the requalified declaration | security **5/5 VERIFIED/PASS**, #644 **5/5 VERIFIED/PASS** |
| **mesa-formal-v5** | A new, unexecuted freeze for contract 1.8.0 and runtime tree `975b0941`. It supersedes the executed v4 by its exact bytes. v4 and its replay (#129) are untouched. |
| Declaration requalified | The acceptance items name the successors and `mesa-formal-v5`. `test_v7_declaration_acceptance_bindings` resolves every item kind: a `formal_replay` must bind the declared contract and the candidate tree and must be unexecuted. No validator was weakened. |
| Gauntlet, re-pinned to `9eb72391` | v2 successors QUALIFIED. v7 probe complete, 3/3, equal to #836's probe. Evidence at `e75d7da5`. |
| A3 re-gate | All checks hold at `6b3c154d` (checker `e2967b54`, template `7cb95356`) |

## 4. v7 retrieval lanes (Priority 4)

Every pinned input was available and digest-exact:

- PrecisionMemBench fixtures `35659b3b…` and `09e99f08…` (combined `caf5869b…`);
- the AMB harness at `03c1d0f1`;
- LongMemEval_S `d6f21ea9…`, 277,383,467 bytes.

The lanes ran locally from a clean worktree at `6b3c154d`, following #836's recipe. Details, environments,
comparisons, logs and failed attempts are in [`lanes-6b3c154d/`](lanes-6b3c154d/). Eight rows were imported with
the repository importers, fetch enabled.

| Lane / row | Result | vs accepted v6 |
|---|---|---|
| AMB **agent-memory (control)** | **BLOCKED.** The frozen bridge (`reference/amb_agent_memory_bridge.py`, lane-pinned blob `3d9ccb31`) ingests every user scope into one store root. The integrated default `single_project_v1` profile refuses the second user's open with `StoreIdentityError`. This is pinned by `tests/test_v7_integration_frozen_runner_profile.FrozenAmbBridgeProfileTests`. | not run |
| AMB bm25 | 8/77, precision 0.0536, recall 0.9651 | 77/77 equal |
| AMB mem0-explicit | 10/77, precision 0.1049, recall 1.0 | 77/77 equal |
| LME agent_memory session | nDCG_any@10 0.878274; complete@50 419/419; evidence 794/794 | 500/500/500 |
| LME agent_memory turn | nDCG_any@10 0.68156; recall_all@50 0.859189 | 500/500/500 |
| LME lexical_overlap session / turn | 0.792944 / 0.559738 | 500/500/500 each |
| LME mem0_explicit session | 0.841054 | 500/500/500 |
| LME mem0_explicit turn | 0.596012 | ranked_top 453/500; metrics and cross-fact 500/500. The same 47 question ids as the previous local execution: the known environment-class reorder, with no gold item moved. |

## 5. Qualification

- **Full suite at `6b3c154d`:** 3413 tests, 0 failures, 0 errors in both a fresh clone and this checkout.
- **Skips:** 27 in the fresh clone, 18 in the checkout. The 9-test difference is `tests.test_seal_anchors` only,
  because a default clone does not fetch `refs/seals/*`. After fetching it, that module runs 12/12. The exact
  reasons are in [`skip-analysis/`](skip-analysis/).
- **Final clean-clone verification:** `clean-clone-verification-pass2.txt`.

## 6. Remaining blockers and owner decisions

1. **AMB agent-memory control row (lane blocker).** The frozen bridge needs `scope_distinct_v1`, or one root per
   user. That is a bridge change, so it needs a new lane version (the lane and its bridge blob are frozen), followed
   by a fresh execution of that row. Decision: adopt store-open 1.0.0 for the AMB lane by superseding the lane, or
   restrict the bridge to one project per root.
2. **Owner decisions carried from pass 1**, still open:
   - adopt the integrated declaration behind the v7 pointer;
   - facade W4 refusal, now stated in docs/44 as the integration direction;
   - the #809 multi-project legacy upgrade path;
   - rebase #839, #840 and #841 with their own successor declarations.
3. **New owner decisions:**
   - #840's `0o600` file-mode change;
   - whether a host-activation gate ships;
   - review finding 5: a same-project non-owner's `correct` on an owned key reads `fact_not_found`.
4. **Gaps:**
   - Ownership is not durable through SQLite `commit_proposal` (review finding 6, pre-existing).
   - Host-layer correct, dispute and permanent deletion replay residual (DSL/5).
   - mesa-formal-v5 is frozen but **not executed**. It needs the pinned Python 3.11 environment, the upstream
     AgentMemBench dataset and an authorized, version-pinned judge for M2.
5. **Publication gates:**
   - independent review of this pass's runtime changes and of the regenerated evidence;
   - hosted CI and the repository Gauntlet and benchmark workflows;
   - merge, register update and the v7 publication record.

   None of these was done, by instruction.

Out of scope, noted: `reference/tests/test_security_finding.py:79` emits a `SyntaxWarning` (invalid escape `\+`).
It is pre-existing on main since #199.
