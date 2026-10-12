# #776 adoption qualification at `cc13930`, plus remaining deletion surfaces

| | |
|---|---|
| Adopted | `implementation/776-logical-deletion-historical-admission-no-ci` @ `cc13930f3a41b08b19ced02ecece7905a87ad3af` (verified) |
| Independent review | `validation/776-deletion-safety-review` @ `6b58dce` (repair `24bbef1`) |
| This branch | `validation/776-adoption-qualification`: failing test `7093c3a` → repair `42c218a` (adapter blob `6823eeaf…`) |
| Environment | Claude Code cloud, Python 3.13, evaluator `9961067` (v3). No Actions, no PR, no merge, v7 declaration unchanged. |

## Fidelity: PASS
| File | `cc13930` | Reviewed `24bbef1` |
|---|---|---|
| `runtime/adapter.py` | `251972b0f85a…` | identical |
| `tests/test_776_adversarial_review.py` | `412b0e51…` | identical |
| `tests/test_776_logical_deletion_admission.py` | `8c7314e8…` | identical |

Besides these, `c34a340..cc13930` changes only the plan doc and the overlay JSON (which pins the same blobs).

## Execution at `cc13930`
| Suite | Result |
|---|---|
| 23 #776 tests | 23/23 OK (`logs/776_23_tests_at_cc13930.log`) |
| Full reference suite | 2733 run, 5 failures = 4 protected-runtime freeze guards (undeclared `adapter.py` change) plus the pre-existing durability `adapter_eof`. Identical to the independent review. |

## Remaining deletion surfaces: counterexamples recorded before any code change (`probes/`)

| # | Surface | Result at `cc13930` | Class |
|---|---|---|---|
| C1 | Recall diagnostics (`candidates`, `admissions`) and `ControlledRecallResult.graph_candidate_hits` | **Deleted fact IDs (`ref-0004`, `ref-0011`) are listed** as refused candidates, with reason `logical_memory_deleted`. No deleted text appears outside `admitted`. Pre-existing for head tombstones on v7 (`tombstoned`). | Identifier/metadata exposure, **not content**. Needs a policy decision (see below). |
| C2 | Relations on surviving facts | `write_semantics(b)["relations"]` names the deleted fact ID and memory id (`ref-0032`, `memory:ra`). The only value present is the survivor's own declared `replaces_value`. `semantic_proposals()` is empty. | Identifier/metadata |
| **C3** | **Transitive derivation** | **Content exposure.** `d2` ("Digest two: earlier the gateway region was Oslo") has `evidence_refs` → `d1` → the deleted version. It is **admitted by public `recall`** and readable via `write_semantics`, and this survives reopen. Only one hop was refused. | **P0 (content)**. Repaired. |
| C4 | Restart and legacy checkpoints | After reopen, `write_semantics(old)` is None and the one-hop derivation stays refused. The legacy no-lineage-field tombstone tests pass (part of the 23). | PASS |
| C5 | Permanent erasure vs pruning (SQLite facade, `secure_delete=1`) | `forget(permanent=True)` with qualified evidence: no byte of the deleted head **or** earlier value remains in any file under the state directory. Pruning keeps text recoverable on disk while it stays inadmissible, as declared. | PASS |
| C6 | Tombstone checkpoint cost | SQLite facade: `forget` is flat at about 4 ms from 10 to 2000 tombstones, same as v7. Recall growth with 2000 refused lexical candidates (6 → 140 ms) matches v7 (5 → 174 ms). JSON checkpoint runtime: prune is O(T) on both (v7 239 ms, `cc13930` 187 ms at 2000), and state grows 7.37 → 7.44 MB from the lineage field. | No regression. The JSON O(T) checkpoint write is pre-existing. |

## Repair of C3 (failing tests first)
- `7093c3a`: `reference/tests/test_776_adoption_transitive.py`, 3 tests (2- and 3-hop refusal, restart, live-source control). **Fails at `cc13930`.**
- `42c218a`: `_derives_from_deleted` follows canonical fact provenance (`episode_uuids`) transitively, memoised per deletion-index state. Refs that are not facts carry no deletion state.
- **Results:** 26/26 #776 tests pass. Full suite: 2736 run, the same 5 expected failures.

## Same-harness quality (v3, instant `2026-10-12T12:00:00Z`; `runs/`)
| Corpus | v7 P0 | `42c218a` P0 | answer@1 / all-critical (both) | Changed served lists |
|---|---|---|---|---|
| Halcyon v1.1 | 0 | 0 | 13/21 · 19/21 | none |
| Cedarline v1.1 | 0 | 0 | 14/20 · 14/20 | none |
| Brightwater v1 | 1 | 0 | 4/10 · 8/10 | B05 only |
| Fenmoor v1 | 2 | 0 | 9/12 · 12/12 | F02, F11 only |
| **Blind theatre v1** (independent author, frozen at `af09d61`/`e560be6`) | **1** (Q15 serves deleted `fee-900`) | 0 | 9/21 · 11/21 | Q15 only |

## Gates (#776)
1. **Zero confirmed deleted-memory exposure on public read surfaces: CHANGES REQUIRED at `cc13930`.**
   - C3 is a confirmed content exposure. It is repaired at `42c218a`; adoption of that blob and an independent replay are needed.
   - C1 and C2 expose **identifiers only**. Whether refused deleted IDs may appear in candidate and refusal diagnostics is an API policy decision.
     - Either remove deleted lineage from `candidates`, `admissions`, `graph_candidate_hits` and survivors' `relations` on read,
     - or accept them as non-content audit metadata.
   - I did not change this API on my own.
2. **Lineage under deletion, re-creation and traversal: PASS for #776 alone.** See the #774 integration report for the combination.
3. **Preserved legitimate quality: PASS.** Only served lists containing deleted content changed.
4. **Independent baseline and same harness: PASS for the measurement.** The protected change is still undeclared; the baseline checker and freeze guards fail as intended.
5. **Performance: PASS** (no regression). The pre-existing JSON O(T) checkpoint write and O(candidates) refused-candidate evaluation remain.
