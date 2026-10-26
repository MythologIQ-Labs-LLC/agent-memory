# #776 + #777: integrated deletion and public-projection candidate

**Branch:** `implementation/776-777-integrated-contract-1-7-no-ci`  
**Parent:** `ada418c8e72da031e3900c1a4b252aacdcabb904` (#777 contract 1.7 alternative).  
**Status:** **IMPLEMENTED, EXECUTION PENDING, NOT QUALIFIED.** No PR, main merge, benchmark repin, or GitHub Actions.

## What this integration actually changes

Claude Code's independent #777 review ([#777](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/777)) found that the new public deleted-ID projection inherited #776's stale negative taint-cache decision from the earlier adapter. A later write can bind previously unknown provenance to deleted lineage without a new deletion; caching only on tombstone/index state falsely continues treating the derived fact as safe.

The reviewed three-way reconciliation is now adopted **byte-for-byte** into `reference/agentmem_ref/runtime/adapter.py`, Git blob `6567bdd695c81a0f3f08c4b72b3ce70ce7d33263`, exactly matching the independent scratch integration tested by Claude. The cache key includes the fact-binding table identity and its current size as well as the deletion index. No new memory facts, policy authorizations, or acceptance claims arise from the cache key.

Tests-first commit `02641b553dcf4551b8cfdcfc4b54c116ce52bd9b`:
- imports the reviewed 40-seed deletion decision oracle, comparing warm, cold and checkpoint-recovered decisions after provenance/deletion/recreation interleavings;
- imports the independent seven-case transitive traversal tests (deep chains, cycles, source lineage, query order and legacy checkpoints);
- imports four independent API 1.7 compatibility/schema tests;
- updates six tests that still assumed contract 1.6 or used 1.7 as the unsupported future version. Existing pre-1.7 consumers remain compatible, and 1.8 must require migration.

The six API envelope schemas remain **non-protected source** and are unchanged from the #777 1.7 branch. The public surface is not a privileged audit interface. Detailed tombstone records remain internal; separately authenticated audit access is tracked under #778.

## Draft governance correction, not activation

`reports/runtime/proposals/777-contract-1-7-v8-alternative.DRAFT.json` now pins the *integrated* protected adapter blob and declares **only** the four changed files in `reference/agentmem_ref`. The six `schemas/*.json` compatibility updates are contract/evaluation evidence, not protected-baseline file deltas.

**Do not register this draft.** The active published baseline is still v6 and the currently declared successor is frozen v7 (#770). The draft's v7 predecessor would be a chained-successor error until v7 is formally published or the successor registrar/validator explicitly supports a complete cumulative v6-to-next declaration. The required new lane/replay records do not yet exist. The separate #773/#774/#769 proposals are **not combined** by this change.

## Independent Claude Code cloud qualification, without GitHub Actions

Use a clean full clone and detach at the **actual new integration head**, not the earlier `ada418c` or scratch `345a778`:

```bash
python -m pip install -r reference/requirements.txt
python -m unittest discover -s reference/tests -t reference -p "test_776_*.py"
python -m unittest discover -s reference/tests -t reference -p "test_777_*.py"
python -m unittest discover -s reference/tests -t reference -p "test_api_*.py"
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD
```

For the last command, an **undeclared protected source** verdict is expected on an unregistered post-v7 experiment. It is NOT equivalent to accepted qualification. The full suite previously showed four protected-freeze failures plus a preexisting durable-gauntlet `adapter_eof` failure on the **independently tested scratch integration**, not on this exact new commit.

Independently challenge:
1. Forward-cited provenance becoming deleted after an unrelated later write, on both **admission and public redaction**; compare warm, cold and restart.
2. Real duplicate-generation memory IDs, state-change history, error-corrected facts, multihop derived lineage, unknown provenance and unrelated live memory.
3. Deleted identifiers, refusal reasons, graph paths and history on all ordinary read surfaces, including cross-tenant/project indistinguishability.
4. API negotiation for historical 1.0 through current 1.7 and unsupported 1.8; verify audit history cannot be reached through a debug flag.
5. Served-memory replay on Halcyon, Cedarline, Brightwater, Fenmoor and blind Theatre with original frozen labels; report P0 exposure and P1 answer/critical-group differences, separately.
6. Protected successor cumulative declaration, immutable v6/v7 lanes, and independent exact-run evidence before considering a merge/release.

**Previous cloud evidence**: [Claude's #777 1.7 review](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/777#issuecomment-6133863119) reported a local-only trial with #776 34/34, #777 23/23, contract 12/12, 2767 full-suite run with the same five expected failures, and byte-identical five-corpus served lists. That evidence is ancestry, **not** a test verdict for this new branch head.
