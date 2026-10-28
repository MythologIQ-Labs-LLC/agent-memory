# Independent integration review of the v7 candidate: findings and dispositions

- **Reviewed commit:** `6a12e1cd` (integration merge `3b778a3a` plus the #840 staging repair).
- **Scope:** the three hand-combined files (`api/surface.py`, `runtime/adapter.py`, `memory/procedural_memory.py`),
  the oracle v2 repair, the test-fixture adaptations, and whether the test-only tenant-wide opener can be reached.
- **Method:** the reviewer was given the code, the preregistered reconciliation rules and the contract. The
  integrator's write-up was withheld until the reviewer had formed findings. Every probe the reviewer wrote is a
  scratch script; nothing in the repository was modified by the review.

The review found **no critical defect in the merge itself**. Findings 1 and 2 are pre-existing in both parents, not
merge regressions.

| # | Severity | Finding (reviewer, condensed) | Confirmed | Disposition |
|---|---|---|---|---|
| 1 | medium | A handle's identity fields (`scope`, `tenant`, `task_ref`, `store_profile`, `runtime`, ...) were writable attributes, and every binding check compares against them. Assigning `b.scope = "project:a"` on a `scope_distinct_v1` handle reached project A's memory. On a `single_project_v1` store, one write through a re-bound handle made every later open refuse, for every project. `AgentMemory.__init__` defaulted to the legacy profile, which passes keys through unmapped. | yes, by probe | **Fixed.** The identity fields are read-only properties, and direct construction must name `store_profile`. Fail-first `tests/test_v7_review_findings.py` RF1a–d: 12 RED → GREEN. |
| 2 | low | The deleted-owner fence consulted deleted generations by `actor_id` before any scope check. A writer in another project learned that a deleted, owned lineage existed, and that id was locked for it. | yes, by probe | **Fixed.** `_deleted_generation_owners` consults only deleted generations the writer is scope-eligible for, at both call sites (refusal and inherited owner). RF2: RED → GREEN. The same-project non-owner control stays refused. |
| 3 | low | Two of the three re-targeted oracle v2 sensitivity regressions are not equivalents: a token rename, and the history half only. The harness's coverage note named a suite that does not catch receipt-state hiding. | yes, by probe | **Fixed (documentation).** The harness docstring and notes now state which re-target is exact and name the suites that do catch it (`test_786_cross_scope_write_authority`, `_write_guard`, `_procedural_ownership`). Both are still not-must-detect; the 8 must-detect regressions are all detected. |
| 4a | low | `test_the_envelope_surface_keeps_w4_host_declaration` asserted only "not a target refusal". The write parks for review with `before_state` `v1`. | yes, by probe | **Fixed.** The test now compares the host-declared envelope with the owner's own identical envelope, outcome for outcome, and pins `before_state == "v1"`. |
| 4b | low | `FacadeIdentityBindingTests` sat after `unittest.main()`, so running the file as a script skipped it. | yes | **Fixed.** `unittest.main()` moved to the end of the file. |
| 4c | info | `test_developer_facade` foreign-context recall now expects `ValueError`, so the facade path drops its candidate-policy assertions. Two ownership tests relax `outcome == "block"` to the selected action. | — | **Kept, by rule.** These follow the preregistered rules: the facade identity binding, and #836's decision composition. They are listed here as coverage given up on the facade path, which is still covered at the canonical layer. |
| 5 | info | A non-owner `correct` on an owned key reads `fact_not_found` at the facade, because `_visible_head` treats the owner refusal as invisible, while `history` shows the head. | plausible (not probed) | **Owner decision.** Ownership is opt-in procedural. Whether a same-project non-owner should read `target_unavailable` rather than `fact_not_found` on correction is a contract question, recorded in the integration README. |
| 6 | info | Ownership is not durable through SQLite. The SQLite runtime's `commit_proposal` does not forward `ownership=`, and procedural memory calls the raw adapter outside `run_governed_read`. | — | **Pre-existing gap, recorded.** The security branch already marked this "pending durable SQLite qualification". It is a v7 publication gate for opt-in ownership, not part of this integration. |
| 7 | info | Stale or contradictory docs: the `store_contract` docstring still said 1.6.0; docs/44 described facade overrides as re-declaring scope; "restate or narrow" did not match code that requires an exact restatement. `_canonical_history` skips `_target()`, as an in-process-only helper. | yes | **Fixed.** `store_contract` docstring corrected. docs/44 is aligned with the code: overrides restate exactly, and recall may narrow its domains. The W4 envelope declaration is stated as an envelope-surface behaviour. `_canonical_history` is unchanged, being documented as in-process evaluation only. |

## Reachability of the test-only tenant-wide opener (reviewer's result)

- **Not in the package.** A wheel built from a clean export contains only `agentmem_ref/**` and dist-info.
  `_tenant_wide_fixture`, `HostDeclaredScopeMemory` and `FrozenRunnerOpener` are absent, and nothing in
  `agentmem_ref/**`, `examples/` or `scripts/` references them. The console entry point is
  `agent-memory = agentmem_ref.console:main`.
- **Its effect could be reproduced without it,** through the paths below. The fix to finding 1 closes the
  attribute route; the other two are outside the handle-holder threat model:
  - in-process re-binding of a handle (finding 1, now refused);
  - direct construction of `AgentMemory` with another runtime. This needs host code, and must now name its
    profile;
  - deleting `store-identity.json`. This needs filesystem write access to the store, the documented host trust
    boundary.
- **Refused opens leave the store untouched.** A refused open (multi-project legacy, wrong project on a
  single-project store, wrong tenant) leaves every file in the root byte-identical.

## Checked and found correct (reviewer)

- **Open and identity logic.** The security branch's logic is intact, with #821's witness guard in the
  interrupted-creation fallback.
- **Facade checks.** `_check_overrides` runs before any target is resolved, and the malformed check comes before
  the identity check. Recall keywords are bound, and `logical_memory_refs`, `history`, `forget`, `correct` and
  `dispute` all map keys. `dispute(fact_uuid=foreign)` reads `fact_not_found`.
- **Ownership.**
  - `owner_principal_ref` cannot be injected.
  - A same-project non-owner, or a runtime with ownership off, cannot re-create a deleted owned id.
  - The owner re-creates it and stays owner.
  - The ownership check runs after the scope check in `_delete_refusal`.
- **Procedural revocation.** `revoke_skill` requires the host binding, refuses a differing restatement before
  lookup, and gives foreign and absent skills the same error.
- **Oracle v2.** The repaired probe is non-vacuous: 18/0/0, and 8/8 must-detect regressions detected.
- **Staging and claims.** The #840 helper keeps directory creation. The identity claim's predictable `.claim` name
  can only make an open fail, never redirect a write.

## Logs

- `logs/fail-first-4d807b89.txt`: RF1/RF2 before the fix (13 failures, control GREEN).
- `logs/after-fix.txt`: after the fix.
