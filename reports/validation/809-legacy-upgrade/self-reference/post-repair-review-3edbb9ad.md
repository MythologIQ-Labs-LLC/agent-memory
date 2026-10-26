# Independent post-repair review of `3edbb9ad`

An independent agent, separate from the implementer, did this review read-only. It used its own
scratch worktrees at `3edbb9ad` and `406b74d3`, which it removed afterwards, plus its own probes. It
ran no full suite and did not touch GitHub. Below is its report.

**Verdict: PASS.** I found nothing blocking and nothing should-fix. There are four notes.

## Findings
1. **NOTE: docstring.** Section 6 says the repair comes "with the docstring and vocabulary updated".
   `_classify_legacy_reference`'s docstring never described the order rule, and `LEGACY_CLASSES`
   is a bare tuple, so there was nothing stale to update. The commit adds an inline comment on the
   changed line instead (`# minted after F, or F itself: never a prior dependency (#809 amendment
   1)`). That is acceptable, but it is not literally a "docstring update".
2. **NOTE: the fix also removes a spurious quarantine.** My probe (item 5 below) shows it. On
   `e88bced2`, a legacy self-citer in a shared domain had its own self-edge classified
   `membership_undecidable`. That self-edge alone was kept bound and quarantined, which forced
   `legacy_unqualified`. At `3edbb9ad` the self-edge is `forward_reference`, and only the genuine
   shared edge stays quarantined. This is correct under amended rule 2, but no test pins it.
   Section 9 F3 covers only the scope gates before rule 2, not this.
3. **NOTE: pre-existing residue output, unchanged by the repair.** In the frozen self-reference
   store, `undeclared_residue(a1)` lists `[prior, mixed]`. My probe shows the same pattern: after
   deleting `x` and then `e`, the residue of `e` is `[x]`. Both runtimes give identical output,
   before and after the upgrade. It comes from the tombstone's `declared_derived_refs` and is
   outside this change.
4. **NOTE: permanent deletion not probed.** `forget(..., permanent=True)` refuses on these stores
   under the default facade evidence. On an already-forgotten memory it returns `fact_not_found`.
   Both runtimes behave the same. The preregistration does not cover permanent deletion of
   self-citers, so I did not pursue it.

## What I confirmed
**1. Scope.**
- `git diff 406b74d3 3edbb9ad` touches exactly two lines:
  - `adapter.py:846`: `cited > own` becomes `cited >= own`, plus the comment;
  - one clause in `docs/44-public-api-contract.md:190`: "(a reference minted after the citing fact,
    or naming the citing fact itself: amendment 1)".
- Nothing under `reference/tests` or `reports/` changed. A `diff -r` of the two worktrees finds
  `reference/tests`, `reports` and `reference/fixtures` identical. The test files and the
  preregistration are byte-identical (`cmp`).
- `reference/agentmem_ref` is identical between `e88bced2` and `406b74d3`, so the fail-first ran on
  the frozen runtime.
- No test or report pins the old `adapter.py` blob id or its sha256.

**2. Execution as preregistered.**
- At `3edbb9ad`:
  - `test_809_legacy_self_reference.py` ran twice: 13/13 OK both times, including the 4 tests
    marked FAIL-FIRST;
  - `test_809_legacy_upgrade*.py`: 12/12 OK.
- At `406b74d3`, exactly the 4 preregistered tests fail, with the assertion messages recorded in
  `fail-first-addendum-e88bced2.txt`:
  - `{'ref-0018': 'eligible'} != {... 'forward_reference'}`;
  - edges `eligible: 4, forward_reference: 1` against `2/3`;
  - NoFabrication `('ref-0018','ref-0018','eligible')`;
  - residue `{'self': ['ref-0018'], 'mixed': ['ref-0025']} != {[], []}`.
- The other 9 tests and the 12 frozen-store tests pass at `406b74d3`.

**3. Correctness of `>=`.**
- **Can it misclassify a genuine prior dependency? No.**
  - Fact ids come from one sequence per substrate with one prefix (`ref`): SQLite `id_counter` in
    `agent_memory_meta`, the in-memory substrate's counter (GAP-SEC-08), and the adapter's fallback
    `DeterministicIds("ref")`.
  - `_governance_witness` and the scope records match the exact id string. So two governed ids with
    the same sequence number must be the same id.
  - Collisions between adapters with separate counters were fixed in `fe7724e9`, which is an
    ancestor of v7 `16a248b1`. No v7-origin store can hold a colliding id.
  - Rule 2 runs after `unknown_reference`, `scope_undecidable` and `order_undecidable`, so ids that
    do not parse never reach it.
- **The fixtures.** I ran the upgrade on copies at both revisions and diffed every fact's
  `classification`, `bound`, report and quarantine:
  - `cross-scope`, `shared-membership` and `forward-reference` are identical;
  - only `self-reference` differs, and exactly as section 5 of the preregistration expects (`self`
    and `mixed` self-edges become `forward_reference`, `bound` `[]` and `[a1]`, `legacy_qualified`).
- **Callers.** `_classify_legacy_reference` and `_id_sequence` have one call site each, inside
  `upgrade_canonical_derivation`. The new-write path (`_bound_derivation`) does not use order. No
  other code compares legacy id order: deletion lineage uses `created_at`.

**4. Residue and deletion traversal** on copies of the self-reference store, at both revisions,
before and after the upgrade:
- Forgetting `self`, `mixed` and `prior` commits. Admitted is `{fwd, next}`, and the reopen is the
  same (`legacy_pending` or `legacy_qualified`).
- The residue of `self` and `mixed`:
  - not upgraded, both runtimes: `[self]`, `[mixed]` (the accepted fallback residual);
  - upgraded, `e88bced2`: `[self]`, `[mixed]`;
  - upgraded, `3edbb9ad`: `[]`, `[]`, also after a reopen.
- Nothing loops or errors: the traversal in `_derives_from_deleted` keeps a `seen` set, and every
  run finished well inside its timeout.

**5. My own probe** (in-memory substrate written by this runtime, derivation records stripped with
`rewrite_fact_attributes`, deterministic ids from a discovery pass):
- `x` cites earlier `e`, itself and later `l`:
  - `3edbb9ad`: `{e: eligible, x: forward_reference, l: forward_reference}`, `bound [e]`;
  - `e88bced2`: `x: eligible`, `bound [e, x]`.
- `y` is a shared-domain self-citer citing `s`, which sits behind the membership gate: see note 2.
- Recorded at write time (before stripping), the bound sets were `[e]` and `[s]`. A new write never
  binds its own id or a later one, as section 3 requires.
- After deleting `x`, its residue is `[]` (it was `[x]` on `e88bced2`). There were no surprises.

**6. Docs.**
- The `docs/44` clause is accurate.
- Grep found no other doc or runtime docstring that describes `forward_reference` as only "minted
  after":
  - `test_809_legacy_upgrade.py` already says "or the citing fact itself";
  - `docs/15` does not define the class;
  - the frozen `decision.PREREGISTERED.md` keeps its original wording, which is correct because the
    amendment explicitly amends it rather than rewriting it.

Both review worktrees have been removed, and nothing in the repository was modified.
