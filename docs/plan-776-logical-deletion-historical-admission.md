# #776 P0 canonical logical-deletion admission repair

**Maturity:** isolated implementation candidate, **not independently tested**, not
qualified, no release.  
**Base:** frozen v7 implementation `9b025f945e7ec4a1e349e56bba251e3122413e88`.  
**Boundary:** Only the canonical protected adapter's admission procedure changes,
not a downstream retrieval ranking policy or #774 predecessor selector.

## Source-verified defect

A governed `pruning` or `permanent_deletion` operation sets
`_tombstones[current_fact_uuid]` and clears the logical memory's
`_current_fact_by_memory` binding. Previously superseded versions of
the same logical memory keep separate fact UUIDs and their own
`replacement_records`. Before this candidate, `_admission_refusal`
checked whether the candidate fact itself was tombstoned, and then
admitted superseded `state_change` facts when the caller explicitly
requested historical evidence. It did not test whether the candidate
belonged to a **logically deleted memory**.

This is a P0 governed-admission defect: published historical context can
reveal information from a memory the owner already deleted. The independent
Brightwater test from #774 reproduces it as an `expectedFailure` on v7.

## Implementation

`runtime/adapter.py:_admission_refusal` now:

1. Preserves existing tenant, exact fact tombstone and derived-from-tombstone
   checks.
2. When tombstones exist, uses the **durable, already canonical**
   `_fact_memory` fact-to-logical-memory binding and the tombstone record's
   `memory_id` to detect that an earlier fact belongs to a deleted
   logical memory.
3. Returns a fail-closed `logical_memory_deleted` refusal **before**
   any historical evidence admission can override it. The reason is
   emitted only after evaluating the caller's project/scope eligibility,
   so out-of-domain candidates are not disclosed by this new reason.
4. Checks recorded episode/source identities that resolve to a canonical
   fact belonging to a deleted memory, returning
   `derived_from_deleted_logical_memory` after domain filtering.

No authority is introduced. Stored historical versions remain in the
governed substrate where retention policy permits; **being physically
recoverable does not mean being readable** by historical recall after
governed deletion. No natural-language matching or model inference can
assert which facts share logical memory identity.

## Tests committed *before* source change

`reference/tests/test_776_logical_deletion_admission.py` has five focused
tests covering two- and three-version histories, canonical pruning,
unrelated legitimate history, errors corrected as never true and
cross-project noninterference. The fixture uses governed
`ConfiguredCompositionRuntime.retain/correct/delete_current`
operations and host-adjudicated correction evidence. Tests must be run on
the exact candidate. This session cannot execute Python against a
complete trusted repository checkout and **does not claim they pass**.

### Mandatory security and quality follow-on

- Independently validate the durable `_fact_memory` mapping and
  `_tombstones` across restart, checkpoint recovery and actual
  permanent deletion, including the difference between pruning and
  recoverable retained history.
- Confirm canonical admission in lexical, vector, exact identity,
  relational and historical/as-of routes consistently rejects the
  older deleted versions; do not rely on one route's filtering.
- Audit references in `Fact.episode_uuids` and other derived
  provenance structures. The first-stage guard covers **resolvable
  fact bindings**, not unresolvable episode IDs; this is a
  qualification blocker if any derived path leaks source content.
- Test large deleted-memory populations: the current code computes a
  set of tombstoned memory identities per admission call. That is
  clear and conservative for security, but may need an independently
  tested, durable indexed membership optimization before production.
  Avoid changing deletion correctness to pass a speed benchmark.
- Reproduce #774's original `PreExistingDeletionLeak` without its
  `expectedFailure` decorator and independently authored random
  multi-version delete cases.
- Confirm no legitimate historical answer is suppressed for a different,
  still-admitted logical memory, even when text/IDs/scope overlap.
- Verify no out-of-scope refusal details leak through returned metadata,
  diagnostic counts, or timing at scale.
- Run full reference tests and the original #770 replay gates, then
  score P0 exposure and P1 historical recall on Halcyon, Cedarline
  and Brightwater under explicit, pinned evaluation time.

## Baseline governance

Source blob and initial tests are pinned at
`reports/runtime/proposals/776-deleted-memory-history-admission-overlay.json`.
The protected runtime change is intentionally **outside** the currently
frozen and unqualified v7 declaration. Do **not** activate or repin
v7, merge to main, run GitHub Actions or claim qualification.

There are other *competing* post-v7 protected runtime candidates under
#773 and #774. Do not give each an independently active "v8"
declaration or combine them without a sanctioned integration/replay plan.

## Execution

```bash
python -m unittest discover -s reference/tests -t reference \
  -p test_776_logical_deletion_admission.py
python -m unittest discover -s reference/tests -t reference \
  -p test_runtime_composition.py
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD
```

As a protected change after frozen v7, the final baseline check is
**expected to fail on undeclared identity**; that is a gate doing its job,
not evidence the candidate's behavior failed. The rest of the suite
must be executed and its exact results recorded by an independent
trusted runner. P0 historical-deletion exposure must be **zero**.
