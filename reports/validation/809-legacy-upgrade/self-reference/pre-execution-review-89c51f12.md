# Independent pre-execution review of the self-reference preregistration at `89c51f12`

An independent agent, separate from the implementer, did this review read-only. It used its own
scratch worktrees at `89c51f12` and at v7 `16a248b1`, which it removed afterwards. It did not touch
GitHub. Below is its report.

## Verdict: YES. The preregistration at 89c51f12 can be executed on the changed runtime as committed.

Nothing blocks. Two SHOULD-FIX items (F1, F2) are cheap and are best recorded as a short addendum
before the first run on the changed runtime.

## Findings

**F1. SHOULD-FIX: the repair changes the residue audit, and the amendment does not say so.**
- `adapter.undeclared_residue(uuid)` lists every fact whose `_derivation_refs` contains `uuid`.
  That includes the fact itself when it cites its own id.
- I copied the store, forgot `memory:self` and `memory:mixed`, and called `undeclared_residue`.
  Results:
  - e88bced2, no upgrade: `self -> ['self']`, `mixed -> ['mixed']`
  - e88bced2, after upgrade: `self -> ['self']`, `mixed -> ['mixed']`
  - patched (`>=`), no upgrade: `self -> ['self']`, `mixed -> ['mixed']`
  - patched, after upgrade: `self -> []`, `mixed -> []` (still `[]` after reopen)
- So the repair has an observable deletion-audit effect that is not in section 5.
- On stores that are not upgraded, the false positive stays (each fact counts as its own
  undeclared residue). `procedural_memory` revocation reports this value.
- Recommend: state the before/after expectation for `undeclared_residue` and pin it with a control.
  Also record the non-upgraded case as an accepted residual of the legacy fallback.

**F2. SHOULD-FIX: no test covers derived deletion before the upgrade.** The challenger asked for
checks before and after. `DerivedDeletion` only checks after. My probe shows the case passes on
both runtimes:
- forgetting self and mixed commits;
- the admitted set becomes `['fwd','next']`;
- the self-edge cycle is tolerated (`_derives_from_deleted` keeps a `seen` set);
- history events are `[]`, `write_semantics` is `None`;
- a reopen recovers with status `legacy_pending`.

Add it as a control.

**F3. NOTE: the rule-order wording is slightly too broad.** Section 2 says "The other gates come
after rule 2, so they never see a self-reference."
- Rule 1 runs before rule 2. So does the `order_undecidable` branch.
- A self-citer with no scope record, or with ids that do not parse, would stay
  `scope_undecidable` / `order_undecidable`: kept bound and quarantined. That is the conservative
  side.
- These cases cannot happen on SQLite v7 stores: every fact has a scope record and ids are always
  `ref-NNNN`. A self-citer is never `unknown_reference`, because the fact is its own witness.
- A check on `ref == fact.uuid` would be more precise, but it goes beyond the authorised one-line
  repair. Clarify the sentence only.

**F4. NOTE: the new-write wording does not match the test.** Section 5 says the new write "records
`bound: []`". The test cites `(a1, predicted_self)` and asserts `bound == [a1]`, with
`uuid == predicted`. The test is stronger (it has a positive control); only the text is wrong.

**F5. NOTE: the idempotence test checks less than section 5 says.**
- It checks after reopen: the status, and that mixed is bound to a1.
- It checks after a restart: the status and the admitted set.
- It does not check the admitted set after reopen, although section 5 claims it. Minor.

**F6. NOTE: the recovery digest check is implicit.** It relies on the reopen failing if the digest
mismatched (in `DerivedDeletion`). Nothing asserts it directly.

**F7. NOTE: the report folds self-references into `forward_reference`.** No separate count exists,
so an auditor cannot tell self-edges from forward edges by the counts. This follows the owner's
choice. `docs/44-public-api-contract.md` does not mention the self case; updating it is optional.

**F8. NOTE: harmless warning.** `Upgrade.test_recall_after_the_upgrade...` emits an "unclosed
database" ResourceWarning on both runtimes. It is also in the recorded fail-first log.

## Answers to the questions

**1. Semantics: consistent with the original decision.**
- A dependency "cannot have carried content that did not exist", and when `cited == own` the
  content is being written in that same commit. The non-retroactive ruling applies a fortiori.
- `forward_reference` is the right class rather than `order_undecidable`: identity is decidable
  from the durable id.
- `cited == own` cannot be a legitimate prior dependency, on v7 (16a248b1) or on the current code:
  - one `"ref"` prefix per store;
  - the SQLite counter in `agent_memory_meta.id_counter` only increments, and
    `restore_checkpoint_value` only raises it;
  - `_write` allocates the uuid immediately before the row is written, so no earlier governed fact
    can carry that id;
  - receipts and events share the counter but have no `fact_scope`, so they never reach rule 2.
- Ids from other stores or in non-canonical spellings (`ref-18`) have no witness in this store and
  classify `unknown_reference`.
- The one case where the rule would be imprecise is two governed facts with different prefixes but
  the same sequence number. That cannot happen on SQLite stores, and Graphiti is excluded by SF-4.

**2. Fixture provenance: genuinely produced by v7.**
- I ran the producer twice against a fresh v7 worktree at 16a248b1. The import resolved to the v7
  tree. All four files matched the committed bytes:
  - sqlite `16545dc5…`
  - configuration-binding `98f23cb8…`
  - runtime-config `a58850f0…`
  - `ids.json` (stdout, `cmp` identical)
- The same producer against the e88bced2 runtime gives a different sqlite (`b7703291…`). So the
  fixture really distinguishes v7 from the current runtime.
- The `MANIFEST.json` digests match the files. The producer script digest `2384652f…` matches.
  Python is 3.13.16 and SQLite 3.45.1, as recorded.
- The rows contain the self-citations: `ref-0018 -> ['ref-0018']`,
  `ref-0025 -> ['ref-0004','ref-0025']`. No row has a `canonical_derivation` attribute. a1 has a
  pruning tombstone.
- `git diff 09214af5 89c51f12 -- reference/fixtures/809-legacy-stores` is empty.
- The test module sha256 `9d8f1b20…` matches the one in the fail-first log.
- The `reference/agentmem_ref` tree is `4bfe33f2` at e88bced2, 09214af5 and 89c51f12, so the runtime
  is unchanged.

**3. Expectations: recomputed independently, all correct.**
- I recomputed every edge from `_fact_scope` and the tombstones (no shared keys):
  - prior: `{a1: eligible}`
  - self: `{self: forward_reference}`
  - mixed: `{a1: eligible, mixed: forward_reference}`
  - fwd: `{next: forward_reference}`
  - a1, next, other: placeholder classifies `unknown_reference`
  - totals: `{unknown: 3, eligible: 2, forward: 3}`
  - e88bced2 gives eligible 4 / forward 1, as stated.
- Admitted sets before and after the upgrade, derived deletion, scope isolation and the new-write
  control all came out as stated.
- The controls are GREEN on both runtimes. The REDs fail on the first assertion that compares the
  classification, for the stated reason.

**4. Tests**
- **Coverage:** the tests check what the amendment states, except F2 and F5.
- **Vacuity:** none passes vacuously. Admitted sets are compared for equality and must be
  non-empty, every fact's bound set is asserted exactly, and NewWriteControl asserts the predicted
  uuid.
- **Collection:** discovery over `test_809_legacy*.py` gives 22 tests with 22 unique ids.
  - `NoFabricationSelfReference` overrides the inherited test method by name, so the three frozen
    stores run only in `test_809_legacy_upgrade.NoFabrication`.
  - `_SelfStore` and `legacy._Store` have no tests.
  - The `legacy` name is a module, not a class, so nothing is re-collected.
- **The `>` to `>=` predicate change is legitimate.** It is exact for one prefix, the `eligible`
  branch keeps the strict `<`, and a prior dependency misclassified as forward would still fail
  it. None of the six SQLite stores in the repo has an equal-sequence edge except the new fixture.

**5. Fail-first: reproduced.** On the unmodified runtime: 10 run, exactly 3 failures, and the
reasons are identical to the log:
- `{'ref-0018': 'eligible'} != {…forward_reference}`;
- `{'eligible': 4, …, 'forward_reference': 1} != {…}`;
- `('ref-0018','ref-0018','eligible')`.

The frozen-store modules (`-p "test_809_legacy_upgrade*.py"`): 12 tests, OK.

**6. Gaps**
- Missing items: F1 and F2.
- Other places that read derivation refs:
  - `_deleted_lineage_reason`, `_semantics_visible` and admission use the bound set and are
    cycle-safe;
  - `evidence_neighbors` uses raw `episode_uuids`, unaffected by the change;
  - `_lineage_for_deletion` uses `fact_memory`, unaffected.
- On non-upgraded stores the only self-reference effect is the residue false positive in F1.

## Also checked
- Scratch copy with only `cited >= own` changed: the self-reference module passes 10/10 and the
  frozen-store modules 12/12.
- Same copy: `test_776*` 46 OK, `test_821*` 48 OK, `test_deletion_completeness*` 6 OK.
- `test_809_security_replay_v1` errored in that copy only because it has no `.git` (the test runs
  `git status`). It passes on the unmodified worktree. I did not run the replay comparison on the
  patched runtime; it remains part of the section 7 re-qualification.

Both scratch worktrees are removed and the main clone is clean. Nothing was edited or committed,
and GitHub was not touched.
