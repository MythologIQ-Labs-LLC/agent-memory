# #773 Adoption confirmation (policy 0.2.0) and v8 draft governance review

| | |
|---|---|
| Adopted head | `implementation/773-explicit-current-context-selector-no-ci` @ `6e00f42f2dc2e81ec137eeecc2ca68f9d1c160e6` (verified) |
| Protected blob | `reference/agentmem_ref/runtime/runtime_composition.py` = `86b3bc292d11c9e81eccbb404cdabe2a34145567` (**matches**) |
| Policy version | `CurrentServedContext().selection_policy_version == "0.2.0"`; `"0.1.0"` is rejected |
| Environment | Claude Code cloud, Python 3.13.16, `reference/requirements.txt`; no Actions, no PR, no merge |
| **Adoption fidelity** | **PASS.** Code equals the reviewed repair `0d5c5da1` except the two-line version bump. |
| **Product retention** | **CHANGES REQUIRED / HOLD** (unchanged). |
| **v8 draft activation** | **BLOCKED as written.** See the governance findings. |

## Re-execution on the new SHA (not assumed from earlier runs)

| Suite at `6e00f42` | Result |
|---|---|
| `test_773_current_served_context.py` | 10/10 |
| `test_773_adversarial_review.py` | 9/9 |
| 13 related temporal/admission/ranking/currentness suites | all OK |
| Full reference suite | 2729 run, 5 failures: 4 protected-runtime freeze guards (undeclared change, the intended response) and 1 durability `adapter_eof` (also fails on the v7 parent and on main) |
| Served contexts with T on Halcyon v1.1 and Cedarline v1.1 | **identical** to the reviewed repair, row for row |

The v3 provenance runs (`evaluation/771-lifecycle-v3-provenance-no-ci`) record runtime `6e00f42`, protected tree `b59b1640…` and blob `86b3bc29…` **separately** from the evaluator commit.

## v8 DRAFT declaration review (`reports/runtime/proposals/773-runtime-baseline-v8-declaration.DRAFT.json`)

**Consistent:**
- It validates against `schemas/runtime-baseline-declaration.schema.json` and has exactly the v7 declaration's key set.
- Its single declared change (`runtime_composition.py` → `86b3bc29…`) matches the committed blob.
- It is the **only** protected file changed since v7 (`9b025f9`), so nothing is undeclared relative to v7.
- `baseline-register.json` and `baseline-v7-declaration.json` are byte-identical to the v7 parent.
- The register still names v6 as the last published baseline and **v7 as `declared_successor`**. Nothing was replaced.

**Blocking findings:**
1. **Chained successor is not supported by the toolchain.** In a disposable worktree (never committed), registering the draft as `declared_successor` made `check_runtime_baseline_equivalence.py` report **all eight v7 protected changes as undeclared**. The checker compares against the *published* v6 surface. So v8 cannot be activated while v7 is unpublished, unless v8 declares the **cumulative v6 → v8** change set, or the checker gains explicit support for chained declarations.
2. **4 of 5 required acceptance-evidence refs do not exist yet:**
   - `amb-precisionmembench-retrieval-v8`;
   - `longmemeval-s-retrieval-parity-v8`;
   - `current-served-context-opt-in-noninterference-v1`;
   - `reader-domain-admission-and-historical-lifecycle-v1`.

   Only `gauntlet-orchestration-retrieval-probe-v1` exists. The v7 replays are STALE under any runtime change, and nothing here claims they passed.

## Retaining the selector as a product capability: what would justify it

On Halcyon and Cedarline at the tested budgets, the selector served **identical** contexts to v7 recall given the same instant. The measured P0 gain came from passing the instant, not from the selector. To retain it as a distinct capability, require:

1. **A budget-slack evidence set**, frozen first: questions where applicable candidates are fewer than the budget, so a known-expired or future window would otherwise be served. Show stale exposure falls versus v7-with-instant and **no answering evidence is lost**.
2. **"Is it still in effect / when did it end?" questions with an answering layer**, showing that `known_inapplicable_refs` (D773-2) lets a consumer answer correctly where v7-with-instant and the 0.1.0 selector do not. Retrieval-only scoring cannot show this.
3. **A blind holdout** with declared validity windows at several reference instants, including instants before governed state changes, to exercise D773-1's fail-closed path at product scale.
4. **v8 lane replays** (AMB/LongMemEval) under a sanctioned successor declaration, demonstrating default-path parity.
5. **Consider the lower-surface alternative**: require or encourage callers of `multi_route_recall` with current intent to pass `reference_time`. That delivered the measured P0 gain with no new protected API.

Absent (1) and (2), the selector is a safety guarantee for a case not yet observed in evaluation. It should stay opt-in and unpublished.
