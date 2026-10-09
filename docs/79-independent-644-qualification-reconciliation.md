# #644 — Independent qualification reconciliation and stop-safety gate

**Disposition:** CHANGES REQUIRED remains in force. Work is staged on `implementation/644-safety-reconciliation-no-ci`. There is **no accepted v7 baseline, no executable sufficiency stop, and no merge authority**. This responds to the independent qualification posted to #644 on 2026-10-09, based on candidate `14ea8a6` and its independent 126-case holdout.

## What the independent review proved

- **F1:** A support-eligibility filter dropped extracted, hedged, negated or attributed same-slot claims from *counter-evidence*. One remaining eligible claim could lead to an unsound `review_stop`.
- **F2:** A report over only retrieved/admitted results did not observe competing same-slot facts excluded by search, budget, or a mutated result list.
- **F3:** Declared end-of-validity was not considered before recommending completeness.
- **Packaging and process:** The runtime module was missing a package-layout table entry/alias, one negative test used a literal backslash followed by `n` instead of a newline, and a v7 declaration existed without the register's successor slot.
- **Open semantic problems:** Untyped same-subject competitors, independent source corroboration, full text-to-proposition grounding, typed updates through public correction, exact-string equivalence, mutable recall membership, durable context/revision attestation and default-SQLite access through the correct governed-read wrapper.

## Implemented correction: do not confuse visibility with support

`GovernedMemoryAdapter.current_typed_slot_obstacles(slots, admitted_refs, context)` audits every **currently admissible** persisted typed fact in the requested slots, **including** those excluded from the query's admitted list. A weaker same-slot proposition is not allowed to support an answer, but now remains visible as a `qualified_counter_evidence` obstacle. Separately, the audit reports `eligible_unretrieved` and `declared_temporal_boundary` counts. Authorization is rechecked before reading semantics; no raw values, unadmitted fact identities or cross-scope facts are exported. The adapter explicitly raises when it cannot enumerate the substrate, rather than interpreting an incomplete audit as complete.

This is an observation, not a closed-world guarantee. Untyped competitors cannot reliably be discovered from a typed index without a separately qualified extraction, linkage and scope policy. A mutable caller-controlled admitted list cannot attest query membership, query-time identity, cutoff or original search budget. **Consequently `ControlledRecallPlanner.observe_persisted_typed_coverage` now always returns `continuation_proposal=continue_if_permitted`.** Even when no typed obstacles are found and mechanical coverage is met, it reports `coverage_observed_unattested`, not a completeness certificate. Qualified competitors, omitted typed evidence and temporal boundaries produce more specific diagnoses, but never authorize or recommend stopping.

This intentionally sacrifices earlier positive stopping recommendations until a trustworthy admission/coverage receipt and untyped-competitor policy exist. Improving a held-out score by granting speculative stopping authority is **not** an acceptable alternative. The pure mechanical classification helper retains its independent `review_stop` proposal semantics for unit-level diagnostics; the governed runtime boundary suppresses it. All such reports retain `stop_attested=false`, `can_admit=false`, `can_mutate=false`, `answer_quality_verified=false`, `authority_effect=none`.

## Packaging, limits, and baseline succession

- Added `evidence_sufficiency` and `governed_transition_witness` to `scripts/restructure_package.py`'s authoritative layout table and created their old-path compatibility aliases.
- Corrected the control-character test to use the actual `\\n` escape in Python source (a runtime newline), and added long canonical typed-slot coverage up to 512 characters without relaxing fact-ID limits.
- Added regression cases for weak same-slot evidence, truncated admitted lists, unattested apparent completeness, an untyped competitor and past declared validity.
- On the **quiet candidate branch only**, `reports/runtime/baseline-register.json` now sets `declared_successor` to v7 while its **last published entry remains v6**. The declaration explicitly pins **all six** protected runtime/alias blobs currently changed relative to `main` and names an additional independent replay gate. Declaring a transition does not publish a successor. The sanctioned local `declare_runtime_baseline_changes.py` and equivalence checker must still be run against the final exact checkout; manual GitHub blob pin matching is a static prerequisite, not a passing baseline checker.

## Verified and outstanding

**Verified on this turn:** the current exact `runtime/evidence_sufficiency.py` Git blob `9008fb216fcea7f97fd1db11cfed8b7db3a60fc3` was reconstructed locally from the previous exact source, verified with `git hash-object`, and passed **18/18** previously available focused unit tests. Static compare confirms the declaration's six paths equal the changed protected surface. Those checks do not replace runtime integration.

**Not yet verified:** the current branch's new/expanded test file, the adapter/census and planner changes, complete package layout tests, local v6-to-v7 TRANSITION checker, 126-case independent holdout, SQL restart behavior and full benchmark lanes. The report's earlier 42/78 and 6/78 outcomes belong to the independent tested revisions only; no new rate is claimed.

**Before any PR:** run local focused and full reference suites, the sanctioned baseline declaration/checkers, the independent held-out suite and live restart/integration tests on this exact candidate. Independently validate no default recall changes and that the new census does not leak hidden facts or exceed reasonable time/memory budgets. Preserve frozen #732 R6, AMB/LongMemEval scorer definitions and original holdout cases. No iterative GitHub Actions runs.

**Follow-on design decisions:** build an immutable, revision-bound governed-read receipt and qualified slot closure with an explicit untyped evidence policy; adopt source-dependence grouping for multiple supports; add typed correction evidence through the public API without weakening PAMA; distinguish complete known-state coverage from open-world recall. Only an independently qualified successor policy may ever authorize stopping.
