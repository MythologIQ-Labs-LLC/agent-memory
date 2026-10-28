# v7 integration (#674 cumulative runtime × #786 store profiles): preregistered cross-branch regression

Written before the integrated tree's suite results were inspected.

**Branch:** `integration/v7-786-836-reconciliation-no-ci`

**Sources:**
- #836 `claude/cool-meitner-0q368g` at `f4386e2aad5f60a4a08e0d7faf9ec65dd1f6df8e`, the base;
- the security branch `engineering/786-procedural-revocation-host-binding-20261027-no-ci` at `f3acce3bfaf9882c5e6517ecc53a23c8ae87f01d`, merged in.

Merge base: `7d4c9be6`.

## Reconciliation rules (decided against the contracts, not by file age)

| Area | Integrated rule | Basis |
|---|---|---|
| Envelope contract | `1.8.0` (#836) | owner ruling 2026-10-22: 1.8.0 accepted. `1.0.0`-`1.8.0` envelopes, including v6's `1.6.0`, stay `current` |
| Store-open contract | `agent-memory-store-open` `1.0.0` (security branch), independent of the envelope version | owner decision: store-open versioned separately; 2.0.0 not promoted |
| Store identity profiles | `single_project_v1` default and `scope_distinct_v1`; legacy stores restricted to a single project and never migrated | owner decisions 1, 2 and 7 |
| Retrieval scope gates (`recall_control`, `runtime_composition`, `query_driven_recall`) | #836 verbatim | #433/#835 scope-safe discovery is a strict superset of the security branch's prefilters, with independent review and 13 replay families |
| Write-target authority, non-disclosing refusals, generations, #776/#777/#809 deletion and derivation | #836 verbatim | contract 1.8.0. A deleted id is re-created as a fresh generation, so the security branch's refusal to reuse a deleted key and its whole-lineage admission fence are not carried, because they contradict 1.8.0 |
| Refusal vocabulary | 1.8.0 tokens (`target_unavailable`, `fact_not_found`); the security branch's `write_target_unavailable` maps to `target_unavailable` | contract 1.8.0 |
| Vetoed-target decision composition | #836: the PAMA outcome is kept, the selected action is blocked, and receipts read `v0 -> v0` | 1.8.0 replay-pinned; equally fail-closed |
| Procedural revocation | host-bound `revocation_context` is authoritative (security branch, `e848449d`); #836's per-call scope keywords may only restate it; #836's `_visible_version` is kept | caller-declared authority is not authority |
| Creator-principal ownership | ported, opt-in; refusals use `target_unavailable`; an owned lineage stays owned across generations (only a prior owner re-creates a deleted owned id) | owner decision 6 (opt-in) |
| Facade `overrides` / recall keywords | bound to the handle's host identity (store-open 1.0.0); #836's malformed-scope refusal is checked first | owner decision 2: no multi-project access through one handle. The module-level envelope surface keeps the exact 1.8.0 semantics |
| A3 template source, checker, C7 harness, formal runner | security branch (A3-audited template blob `7cb95356`, checker `e2967b54`) | #836 never touched them; store profiles require the migrated `run_m4` |

## Expected outcomes

1. **Security-branch suites on the integrated tree** (`test_786_*`, `test_776_deleted_lineage_sqlite`, oracle v2, the three sensitivity harnesses) pass. The only edits allowed are the reconciliations above: contract-version literals, refusal tokens, decision composition, `run_governed_read` wrapping for envelope calls on a #816 store, and generation re-creation in place of reuse refusal. Each edit is listed in the integration record.
2. **#836 suites on the integrated tree** pass, except tests whose premise is caller-declared cross-scope authority through a facade handle or procedural `revoke_skill`. Those must be reconciled to the host-bound rule, each listed with the security reason. No other #836 expectation may change.
3. **#786 security replay families** (`verify_786_security_replays.py --reexecute`): every family except the facade-level W4 cases reproduces its recorded observations. W4's facade cases are expected to change (refused) and are re-preregistered. Any other difference is a regression.
4. **#644 replays** (`verify_644_v7_replays.py`) reproduce their recorded observations; no #644 code changed.
5. **Gauntlet:** the orchestration probe and both v2 successors (durability and governance) run green after a candidate-only re-pin to the integrated revision. The v1 public-facade contestants stay refused, as historical results.
6. **Full reference suite:** failures are limited to the two historical v1 contestant tests, plus identity guards that need a re-pin to the integrated revision. Each is named.
