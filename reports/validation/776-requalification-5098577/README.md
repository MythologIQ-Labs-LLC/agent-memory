# #776 requalification at `5098577` (after the cache repair)

| | |
|---|---|
| Adopted | `implementation/776-logical-deletion-historical-admission-no-ci` @ `50985774c1f8a890931ea04bfe315f549f9a41ba` (verified) |
| Protected blob | `reference/agentmem_ref/runtime/adapter.py` = `fe25923f70ae03830d1036ad959af62e25fd4b59` (verified; identical to the reviewed `bd16a7e`; `bd16a7e..5098577` changes only the overlay JSON) |
| This branch | `validation/776-requalification-5098577` @ property test `d393bff` |
| Verdict | **PASS for deletion correctness and quality. Baseline qualification BLOCKED / not claimed** (undeclared protected change; see the #777 integration report for the integrated path). |

## Execution
| Suite | Result |
|---|---|
| 33 deletion-security tests | 33/33 at `5098577` (`logs/776_33_tests_at_5098577.log`) |
| **New property test** `test_776_deletion_decision_properties.py` | 40 random interleavings (28 steps each) of writes with provenance to existing **and not-yet-existing** facts, state changes, governed deletions, **re-creation of deleted memory ids** and recalls. Every fact's deletion decision equals an independent from-scratch graph oracle at **every step** (warm caches, arbitrary query order, later writes), with **cold caches**, and after **checkpoint recovery**. **PASS at `5098577`; FAILS at `5d90965`** (seed 4, step 21: warm cache admits a forward-cited fact that the oracle refuses), so the test discriminates the repaired defect. |
| Full reference suite | 2744 run, 5 failures = 4 protected-runtime freeze guards plus the pre-existing durability failure |

## Served quality (v3 harness; no tuning; `runs/`)
| Corpus | v7 P0 | `5098577` P0 | answer@1 · all-critical (v7 = `5098577`) | Changed vs v7 |
|---|---|---|---|---|
| Halcyon v1.1 | 0 | 0 | 13/21 · 19/21 | none |
| Cedarline v1.1 | 0 | 0 | 14/20 · 14/20 | none |
| Brightwater v1 | 1 | 0 | 4/10 · 8/10 | B05: deleted `meter-arq` removed |
| Fenmoor v1 | 2 | 0 | 9/12 · 12/12 | F02/F11: deleted `chute-n` removed |
| Blind theatre v1 | 1 | 0 | 9/21 · 11/21 | Q15: deleted `fee-900` removed |

Served lists are byte-identical to the previously reviewed `5d90965` and `bd16a7e`.

## Outstanding risks
- **JSON checkpoint cost:** writes are O(tombstones), as on v7. Refused-candidate evaluation is O(candidates), as on v7.
- **Derivation depth:** derivation taint follows declared `evidence_refs` only. Content copied without provenance is not tracked; this is out of scope by design.
- **Metadata privacy:** handled by #777.
