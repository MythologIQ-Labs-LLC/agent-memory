# A3 re-gate — independent review 4 (delta confirmation): PASS

**Reviewed revision:** `a2014386abeed4b01e554eacf998dfe69688cae4` (tree `da134345…`): the review-3 advisory fixes on top of the review-3 PASS at `98a84041`, together with the evidence commit `17ad1033`. This was an independent adversarial reviewer with a fresh context, working only in clones.

Blobs (`git hash-object --no-filters`):

| file | blob |
|---|---|
| checker | `e2967b54` |
| template source | `7cb95356` (frozen `745f789c01b7…`) |
| `run_cross_fact_currentness_report.py` | `a69e42ba` |
| A3 tests | `d5abcbc4` |
| `test_currentness_generalization.py` | `cf5c4311` |
| harness | `89b955a6` |
| `a3_regate_evidence.py` | `f035a998` |
| README | `54405ffb` |
| `regate-evidence.json` | `ab275805` |

## Verdict

**PASS for `a2014386`**, with three advisories, none blocking.

## Verified by execution

- **R3-1, R3-2 and R3-3 are fixed.** Every review-3 host attack (H-a1, H-a2, H-b1, H-b2, H-c) is refused in A3 and in strict mode. The 76a9e30 checker accepts H-a1, H-b1 and H-b2.
- **`source_blob` agrees with what Python imports.** This held over 600 random CRLF variants. Replace refs, symlinks and FIFOs give no new acceptance path.
- **Historical results are unchanged.** On the freeze and attempt-2 inputs, the frozen and audited bytes, LF and CRLF, in normal and strict modes, all match 76a9e30 byte for byte apart from `template_basis`. `rejections-final.json` is reproduced. Strict mode on the current source gives the historical message byte for byte.
- **Genuine inputs are accepted** with no `.pyc`, with a timestamp `.pyc`, with a checked-hash `.pyc`, and after `cp -a`.
- **The delta only adds refusals.**
- **Counts and digests:** 54 tests OK; 49 of 49 mutations killed; `CHECKER_AUDIT_SHA256` (`ac622bc3…`) recomputed. The evidence record reproduces byte for byte in a fresh clone.

## Advisories and disposition

- **A4-1 (test gap).** These mutations survived the tests: dropping the CRLF normalisation; normalising lone CR; stripping every `\r` (dangerous, because a lone CR is a Python newline); using `git hash-object --no-filters`; and a frozen path that refuses only package shadows.
  - Added `test_review_4_line_endings_at_the_template_level`: CRLF copies of the frozen and audited bytes are accepted; a leading lone CR (which parses), a lone CR in place of LF, and an extra CR inside a comment are refused in both modes.
  - Added `test_review_4_frozen_path_refuses_sibling_and_bytecode_shadows`.
  - The harness gained four mutations and now kills 53 of 53.
  - `git hash-object --no-filters` is an equally safe implementation, so that mutation is not counted.
- **A4-2.** A stale checked-hash `.pyc` is now refused on both paths, where 76a9e30 accepted it on the frozen path. This fails closed and is intended by R3-3. It is documented in `../README.md`.
- **A4-3.** The evidence record's identity blobs now use `git hash-object --no-filters`.

The checker code is unchanged since `a2014386`, so this PASS applies to checker blob `e2967b54`. The reviewer's scripts are kept here as `*.txt` records.
