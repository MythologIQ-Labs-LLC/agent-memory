# A3 re-gate — independent review 3: PASS, with advisories

**Reviewed revision:** `98a84041c872d035d0f256a638b092739991b41f` (tree `333f08fa…`), together with the evidence commit `163b4604` (tree `e2e51911…`). This was an independent adversarial reviewer with a fresh context, working only in clones.

| file | blob |
|---|---|
| `scripts/check_generalization_corpus.py` | `167da637` |
| `reference/run_semantic_route_ordering_report.py` | `7cb95356` (frozen `745f789c01b7…`) |
| `reference/run_cross_fact_currentness_report.py` | `c0a1b247` |
| A3 tests | `7bbc6b55` |
| `test_currentness_generalization.py` | `cf5c4311` |
| mutation harness | `eb3be0a9` |
| `a3_regate_evidence.py` | `f035a998` |
| README | `9da35532` |
| `regate-evidence.json` | `961fd5cc` |

## Verdict

**PASS, with advisories.** Nothing in the repository itself — file content, tracked attributes, or the checker unmodified — gets a changed template source accepted. Every bypass found needs host state.

## What was verified by execution

- Every review-1 and review-2 attack is refused.
- **The reviewer's own audit of the audited blob `7cb95356`:**
  - it differs from the frozen blob only inside `run_m4`;
  - the `CONFLICT_TEMPLATES` literal is identical, an immutable tuple of tuples of strings, and is only read;
  - the 15 texts hash to `bb4d4da3`;
  - nothing in the runtime refers to the module.
- **Historical replay** (76a9e30 checker against 98a84041, on the freeze and attempt-2 inputs):
  - byte-identical in normal and frozen-bytes modes, both normal and strict;
  - `rejections-final.json` is reproduced;
  - a 400-trial differential fuzz with 2,558 K7 and 6 K8 rejections found 0 differences.
- **Digests and `check()`:**
  - `COMPARISON_RULE_SHA256` (`0bcc7365…`) was recomputed without importing the checker;
  - `CHECKER_AUDIT_SHA256` recomputes;
  - `check()` differs from 76a9e30 by exactly the three A3 lines.
- **Tests, harness and evidence:** 50 tests OK, 43 of 43 mutations killed, and the evidence record reproduces byte for byte.

## Advisories

- **R3-1 (the most important).** `git hash-object` applies clean filters. Untracked `.git/info/attributes` plus `.git/config`, or `GIT_CONFIG_*` environment variables alone, could make it report the frozen or the audited blob for any bytes. This defeats the audited-blob binding. The reviewer recommended fixing it, or stating it as a limit, before acceptance.
- **R3-2.** The frozen path did not run the host-shadowing check. 76a9e30 behaves the same.
- **R3-3.** A checked-hash `.pyc` whose hash does not match the source was skipped as stale, but `--check-hash-based-pycs never` loads it.
- **Deny-list gaps.** `operator.attrgetter` with a constructed dunder string, and `from sys import modules`, still passed the static rule (they were refused only by the audited-blob check).

## Disposition

All four advisories are fixed in the commit that adds this file.

- **R3-1.** `source_blob()` computes the blob from the raw bytes in Python, with one normalisation (the repository's `eol=lf`); `git hash-object` is no longer consulted. A test reproduces the environment-variable attack: `git hash-object` reports the frozen blob for the altered bytes, and the checker still refuses them.
- **R3-2.** The frozen path, including strict mode, refuses host shadowing.
- **R3-3.** A hash-based `.pyc` whose hash does not match the source is refused.
- **Deny-list.** `operator`, `attrgetter`, `methodcaller` and `itemgetter` are refused, as are imports of dynamic attributes by name and imports from dynamic modules, dotted or not.

Tests: `test_review_3_*`. The harness now kills 49 of 49 must-detect mutations.
