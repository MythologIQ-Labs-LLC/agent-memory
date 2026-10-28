# A3 re-gate — independent review 1: VETO

**Reviewed revision:** `0173adf78bd734b122fd9d8bfbd33e0e263742bb`
**Reviewer:** an independent adversarial reviewer with a fresh context. It was given the code and the gate plan, not the author's conclusions, and worked only in scratch copies.

| file | blob |
|---|---|
| `scripts/check_generalization_corpus.py` | `c089a149c0e47aa4e291e0b17e431cadbb72661b` |
| `reference/run_semantic_route_ordering_report.py` | `7cb9535695dd5bc760831eba50aefd5622fc1fa5` (frozen `745f789c01b7a542f906a9034ae63ebdd6776f7c`) |
| `reference/tests/test_currentness_generalization_amendment_a3.py` | `bf8d84975e14ef180ced11c29c04985f17516d71` |
| `reference/tests/test_currentness_generalization.py` | `cf5c4311f6b364e2e51a13034a13ea686f9c179a` |

## Verdict

**VETO.** A3 accepted template source files whose effective `CONFLICT_TEMPLATES` value differs from the frozen templates, including the value seen through the real consumer `run_cross_fact_currentness_report.py`. These were cases A3 claimed to close, not limits it stated.

## Blocking findings

| id | construction | why A3 missed it |
|---|---|---|
| B1 | a `# -*- coding: utf-7 -*-` cookie, with an assignment hidden in a "comment" through `+AAo-` | the checker decoded the file as UTF-8 while Python decodes it as UTF-7 |
| B2 | `globals().update(CONFLICT_TEMPLATES=...)` and `vars().update(...)` | the keyword name is not a string constant |
| B3 | `def run_m4(pairs: int = 50, CONFLICT_TEMPLATES=...)` | function parameters were not checked |

## Advisory findings

- **A1** — a constructed `globals()` key, `setattr` through `sys.modules`, and `exec` of a bytes literal.
- **A2** — swapping the module's `__class__` to one with a custom `__getattribute__`.
- **A3** — a package directory shadowing the `.py` file.
- **A4** — the frozen path trusted only the 32-bit blob prefix. A brute force (`prefix-collision-brute.c`, nonce `00000000e3b201de`) found a file with an altered template and blob `745f789c7e01ea42…` in 4 min 35 s. The gate-frozen checker has the same hole, so this is not a regression.
- **Digest gaps** — the digest did not cover `TOKEN` flags (`re.I`), dropping K7 for variants, or narrowing the references (`templates[:3]`).
- **Untested clauses** — the `ClassDef`/`AsyncFunctionDef`, `MatchStar` and `MatchMapping` rest clauses had no tests.
- **Strict-mode ordering** — strict mode parsed the file before checking its blob, so the error message differed for some inputs; the exit code did not.

## What held

- `COMPARISON_RULE_SHA256` (`b41d71c8…`), independently recomputed from git sources.
- Strict-mode outcomes.
- Historical outputs, byte-identical against the 76a9e30 checker on the freeze and attempt-2 inputs. A 300-trial differential fuzz exercising 1,725 K7 rejections found 0 differences.
- The test suites: 38 OK.

The reviewer's reproduction scripts are kept here as `*.py.txt`. They name the reviewer's scratch paths and are records, not tests.

## Disposition

Every blocking finding and every advisory except A2 and A3's out-of-file limits is fixed in the commit that adds this file. That commit also closes those two cases as far as one file's syntax and the checker's own path allow. Regression tests: `reference/tests/test_currentness_generalization_amendment_a3.py` (`test_review_1_*`). Mutation sensitivity: `reference/security_falsifiers/a3_regate_sensitivity.py`.
