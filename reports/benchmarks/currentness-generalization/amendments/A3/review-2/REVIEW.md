# A3 re-gate — independent review 2: VETO

**Reviewed revision:** `656bbe4d67efaeda37154fe44760f1bbc8e77911` (tree `032ac2be…`), together with the evidence commit `49495237`. This was an independent adversarial reviewer with a fresh context, working only in scratch copies.

| file | blob |
|---|---|
| `scripts/check_generalization_corpus.py` | `cc9cf43efca1fc6c92a23fcaaa0629c0053eea58` |
| `reference/run_semantic_route_ordering_report.py` | `7cb9535695dd5bc760831eba50aefd5622fc1fa5` |
| A3 tests | `af61d985c32ef32e2424e7edf8bdea021c4370f3` |
| `reference/security_falsifiers/a3_regate_sensitivity.py` | `ea76e0cd5bb849f8c25706ded06e455cd6be7fed` |
| `scripts/a3_regate_evidence.py` | `ac0bc88f269392ae12813c705ed996f2e672daec` |

## Verdict

**VETO.** A3's deny-list of dynamic primitives was incomplete, so the effective templates could still be rewritten.

## Blocking finding

**N1.** Each of the following was accepted on the A3 basis and changed what an importer sees; for all but one, it also changed what `run_m4` sees:
- `run_m4.__globals__[<reversed key>] = ALT`
- `sys._getframe().f_globals[...]`
- `getattr(sys, 'mod' + 'ules')[__name__] = ...`
- `print.__self__.exec(...)`

## Advisory findings

- **D1.** These checker edits disabled K7 without the comparison digest noticing:
  - narrowing `templates[:]` in place;
  - a sibling `continue` before the K7 call;
  - replacing `overlap_rule` through `functools.wraps`;
  - a `float` subclass for `THRESHOLD`;
  - filtering K7 out of the rejections;
  - an `except` handler that drops K7.
- **H1.** An unchecked-hash `.pyc`, or a sibling extension module, shadowed the source.
- **H2.**
  - A CRLF working copy of the frozen bytes was refused in strict mode.
  - The prefix-collision change to strict mode should be documented.
  - An unparsable source raised `SyntaxError` on the A3 path.
- **T1.** The tests and harness covered only the defences they listed.

## What held

- Every review-1 finding is closed.
- 45 tests passed, and the harness killed 30 of 30 mutations.
- The frozen bytes and the current file are classified correctly.
- Strict mode refuses the current file with the historical message.
- The historical replay is byte-identical to 76a9e30; a 400-trial differential fuzz with 2,422 K7 rejections found 0 differences.
- `COMPARISON_RULE_SHA256` (`0bcc7365…`) was recomputed independently, and the evidence record is reproducible byte for byte.

## Disposition

The fix is in the commit that adds this file.

- **N1 — structural fix.** A3 no longer accepts any changed source that passes the static rules. It accepts only an **audited full blob**, listed in `AUDITED_TEMPLATE_SOURCE_BLOBS` and currently just `7cb95356…`. The static rules are the mechanical part of that audit, and an audited blob must still pass them. The deny-list is also broadened: every dunder attribute, frame attributes, `getattr`, `inspect`, `gc` and `ctypes` are refused.
- **D1.**
  - `CHECKER_AUDIT_SHA256` covers the checker's whole syntax tree, so any unrecorded edit to the checker refuses the A3 path.
  - `_rule_objects_intact()` refuses rule objects that are rebound, wrapped or of a subclassed type.
  - The evidence tool proves that `check()` equals 76a9e30's `check()` once exactly the three A3 lines are undone.
- **H1.** `shadowing_artifacts()` refuses:
  - sibling modules;
  - unchecked hash-based bytecode;
  - bytecode for another interpreter that would load;
  - bytecode whose code differs from the source.
- **H2.**
  - Newlines are normalised in the decode check.
  - Parse failures produce an A3 message.
  - The prefix-collision change to strict mode is documented in `../README.md`.
- **T1.**
  - Tests: `test_review_2_*` and `test_checker_audit_digest_*`.
  - The harness kills 43 of 43 must-detect mutations. Each mutant re-records its own audit digest, so every individual defence is exercised.

The reviewer's scripts are kept here as `*.py.txt` records.
