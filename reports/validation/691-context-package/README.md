# #691 context package: first vertical slice (verification record)

| Item | Value |
|---|---|
| Branch | `claude/eager-dirac-bftkfg-691-context` |
| Implementation commit | `f6184d22` |
| Base | #815's head `77c472e6`: the security stack #783 → #784 → #788 → #804 (#805), plus #809. This base carries #786 write authority, #777 deleted-lineage redaction and contract 1.8.0 |
| Package | Candidate `agent-memory-context/0.1.0`, separately versioned (`schemas/api-context-package.schema.json`) |
| Contract | Unchanged at 1.8.0. **No acceptance, no successor, no PR, no hosted CI.** |

## What works through the public API

`AgentMemory.recall_context()` resolves the authorized content of exactly the facts one public
recall returned. The recall and the resolution run under the runtime-owned lock, and each fact
is re-checked before its text is read. The result is bounded and carries provenance receipts,
explicit item and package states, and an untrusted-evidence policy. `recall()` is unchanged.
See docs/44, "Context package".

## Executed

1. **`reference/tests/test_context_package.py`: 14 tests, all passing.** They cover:
   - the workflow: remember → recall_context → correct → recall_context → forget → restart →
     recall_context;
   - an empty result;
   - unchanged ID-based recall;
   - budgets: per-item truncation, total and token limits, invalid budgets refused;
   - another project cannot resolve content;
   - another tenant cannot even open the store;
   - only returned facts are resolved;
   - deleted-lineage identifiers and text are not disclosed;
   - untrusted memory text is labelled and grants nothing;
   - a failure during resolution fails closed and releases the lock;
   - concurrent correct/forget while reading never yields two versions or stale content;
   - schema validity and determinism across reopen.
2. **Demo: `python scripts/demo_context_package.py --json demo-run.json`.** All checks passed
   (`demo-run.json`). Steps: remember three memories (one is an injected "SYSTEM:" instruction);
   recall the car; correct it and see only the corrected content; see the injected text delivered
   as untrusted evidence; forget the car; restart and confirm the content stays inaccessible;
   another project reads nothing.
3. **Security replays re-executed at `f6184d22` on a clean tree.** All PASS (`security-replays/`):
   - #786 v2: 28/28 cases;
   - #786 v3: 31/31 cases;
   - #809 evidence-reference authorization: 13/13 cases.
4. **Full suite** (`python3 -m unittest discover -s reference/tests -t reference`): 3022 tests.
   The failures are of three kinds, all identified:
   - **Also failing on the untouched base `77c472e6`, in this environment:**
     - `test_evaluation_only_change_keeps_runtime_baseline_equivalence` (by design);
     - two `test_770_v7_lane_freeze_independent` replay-freshness tests;
     - `test_644_v7_gauntlet_identity` (detached-worktree ancestry).
   - **Evidence-staleness guards, by design:** three `test_644_v7_replays` evidence checks and one
     `test_786_security_replays_v3` check. Committed replay evidence is `STALE` whenever runtime
     files differ from its source commit, so it is not re-executed. Regenerating that evidence
     belongs at the integrated landing head. Fresh execution of the security replays passes (item 3).
   - **Fixed:** the package-layout table entry for `api/context_package.py`.

## Dependencies and limitations

- **Security stack.** This needs the security stack (#805 + #815) for #786 write authority and
  #777 redaction, so it must land with or after that stack. It is independent of the #819 C4
  selection candidate: the package wraps whatever `recall()` returns.
- **Not yet decided:**
  - acceptance of the package version or contract numbering;
  - a lane for content and token metrics;
  - an adoption path for the AMB bridge, which could drop its plaintext index.
- **Concurrency boundary.** The boundary is the in-process lock. The store already refuses a
  second open handle (generation conflict), so cross-process interleaving is not possible through
  the facade.
- **Token budget.** It is an estimate, `ceil(chars / 4)`, not a model tokenizer.
- **Semantic sidecar residue.** Physical residue in the semantic vector sidecar is #802's and is
  not touched here.
