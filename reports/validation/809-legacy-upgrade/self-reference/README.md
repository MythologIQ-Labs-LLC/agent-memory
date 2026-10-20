# #809 legacy upgrade, amendment 1: legacy self-references never bind

**Frozen runtime:** `3edbb9ada2cac07acfefe2976cb3a6004525a15b` (runtime tree `3386ec0f…`). It
is a strict fast-forward of the cumulative candidate `e88bced2` (#821 R-1), whose evidence head is
`09214af5`. **It replaces `e88bced2` as the Runtime Baseline candidate.**

**Branch:** `claude/eager-dirac-bftkfg-809-selfcite`. Every commit is `[skip ci]`. No PR, no
Actions, no merge, no Runtime Baseline or register change. Frozen #815 evidence and the
`809-legacy-stores` fixtures are untouched.

| Commit | Content |
|---|---|
| `89c51f12` | Preregistered amendment, v7 fixture, tests, and the fail-first run (3 REDs). No runtime change. |
| `406b74d3` | Addendum after the independent pre-execution review (YES), and the fail-first re-run (4 REDs). No runtime change. |
| `3edbb9ad` | Runtime repair, `cited > own` → `cited >= own`, plus the `docs/44` clause (**frozen runtime**) |
| evidence commit after `3edbb9ad` | This folder only |

## The gap and the owner decision

- **The gap.** Raised in issue #809 comment 6298692981 and PR #815 comment 6298713281.
  `_classify_legacy_reference` ordered references with `cited > own`. A legacy fact citing its own
  id therefore reached the scope gates and **bound as `eligible`**, contrary to the preregistered
  non-retroactive rule.
- **The owner's decision (2026-10-20):**
  - a full fix on a new revision;
  - a self-reference is `forward_reference`.
- **Records:**
  - `../AMENDMENT-1-self-reference.PREREGISTERED.md`: sections 1–8, plus the section 9 addendum;
  - `pre-execution-review-89c51f12.md`: the independent review, YES;
  - `post-repair-review-3edbb9ad.md`: the independent review, PASS.

## Fixture (`reference/fixtures/809-legacy-self-reference/`)

- **Provenance.** Written by the published v7 runtime `16a248b1`, using the sanctioned producer
  pattern. Its own `MANIFEST.json`. Python 3.13.16, SQLite 3.45.1.
- **Reproducibility.** Three implementer runs and two reviewer runs gave byte-identical files. The
  same producer run on the current runtime gives a different database, so the fixture genuinely
  distinguishes v7 from the current runtime.
- **Contents:**
  - a self-citer (`ref-0018` → itself);
  - a mixed citer (`ref-0025` → `a1` and itself);
  - a prior-id control and a next-id control;
  - a project:b control;
  - the source `a1`, forgotten.

## Fail-first and repair

| Test (`test_809_legacy_self_reference`, 13) | `e88bced2` (×3) | `3edbb9ad` |
|---|---|---|
| `Upgrade.test_self_references_are_forward_and_unbound_…` | **FAIL**: `{'ref-0018': 'eligible'}` | ok |
| `IdempotentAndDurable.test_a_second_run_…` | **FAIL**: `eligible: 4, forward_reference: 1` | ok |
| `NoFabricationSelfReference` | **FAIL**: `('ref-0018','ref-0018','eligible')` | ok |
| `ResidueAudit.test_after_the_upgrade_…` (addendum F1) | **FAIL**: residue `[self]`, `[mixed]` | ok |
| 9 controls: fixture identity and v7 rows, status and admitted sets before the upgrade, recall after the upgrade, derived deletion before and after the upgrade (with reopen), scope isolation, pending-store residue (accepted residual), new-write control | ok | ok |

The frozen-store modules `test_809_legacy_upgrade*` (12 tests) pass on both revisions with
identical outcomes. The post-repair reviewer diffed every fact's classification and `bound` on the
three frozen stores at both revisions: identical. Only the self-reference store differs, exactly as
preregistered.

## Re-qualification at `3edbb9ad` (clean detached worktree; `runs/validation-ladder-3edbb9ad.log`)

| Gate | Result |
|---|---|
| `test_809_legacy*` | 25 OK |
| `test_809_evidence_reference_authorization*` | 25 OK |
| `test_809_security_replay*` | 8 OK |
| `test_776*` (deletion propagation) | 46 OK |
| `test_deletion_completeness*` | 6 OK |
| `test_821*` | 48 OK |
| `test_816*` | 25 OK |
| #821 crash-window matrix (9 points) | Outcomes **identical** to `crash-window-d0d2a97.json`, timing excluded |
| 7 security replay families | **All PASS.** `observations_sha256` is **identical to `e13d8c58` and to `e88bced2`** for every family (`security-replays-3edbb9ad/`). The manifests bind `source_commit 3edbb9ad`. |
| Full suite without the model | 3094 tests (3081 + 13 new), 4 failures, 35 skipped, 1 expected failure |
| Full suite with the pinned model | 3094 tests, 4 failures, 30 skipped, 1 expected failure |
| The 4 failures | The same baseline-freeze guards as at `e88bced2`. The assertion text hashes identically (`fd1ae14c…`) in both modes and at `e88bced2`. |

## Observed effects of the repair

- **Classification.** Self-edges become `forward_reference` and are unbound. A store whose only
  quarantine came from a self-edge no longer reads `legacy_unqualified` (post-repair review note
  2: a shared-domain self-citer's own edge was `membership_undecidable` before the repair). This
  is correct under amended rule 2. **It is not pinned by a test; that is a follow-up.**
- **Residue audit.** On an upgraded store, a self-citer is no longer reported as its own
  undeclared residue.
- **Nothing else changes.** No replay observation, crash-window outcome or frozen-store outcome
  changes, and nothing changes for new writes (they never bound their own id).

## Residuals

- **Stores that have not been upgraded.** The legacy fallback (`episode_uuids`) still reports a
  self-citer as its own residue. This is accepted; `upgrade_canonical_derivation()` is the remedy.
- **Report counts.** Self-edges are counted inside `forward_reference`, with no separate count.
  This follows the owner's choice.
- **Edge cases.** A self-citer with no scope record, or with ids that do not parse, would stay
  `scope_undecidable` or `order_undecidable` (quarantined, the conservative side). This cannot
  occur on SQLite v7 stores.
- **Pre-existing and unchanged:** `undeclared_residue(a1)` lists the derived facts that the v7
  tombstone did not declare (`[prior, mixed]`). The output is identical on both runtimes.
- **Not covered:** permanent deletion of self-citers. The default facade evidence refuses it on
  these stores.

## For the integrator

- The single Runtime Baseline successor must bind **`3edbb9ad`'s** protected blobs:
  `runtime/adapter.py` changes again, and `sqlite_runtime.py` is as at `e88bced2`.
- The integration strategy is unchanged: one cumulative #805 vehicle, now fast-forwarded to this
  branch, landed with a merge commit.
- Whether to declare the successor, whether to bundle #691, and the CI budget remain owner
  decisions.
