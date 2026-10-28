# Amendment A3 (#732 G3b, #786): semantic template pin — re-gate record

**Status:** under independent re-gate. A3 is not accepted until a review of an exact revision returns PASS.

## What A3 is

- The historical G3b pin is a whole-file blob, `745f789c…`, of `reference/run_semantic_route_ordering_report.py`.
- That pin, the corpus, the 0.5 threshold, K1–K8, and strict historical mode (`--require-frozen-blob`) are preserved unchanged.
- A3 lets the checker accept a changed template source file only when it can prove two things: the templates the file really binds are the frozen ones, and the contamination comparison is the gate-frozen one.

## Evidence

- **`regate-evidence.json`**, produced by `python scripts/a3_regate_evidence.py` at the commit it names. It records:
  - the revision identity;
  - the independent comparison digest at 5555504, 76a9e30 and HEAD;
  - a byte-for-byte historical replay against the 76a9e30 checker;
  - strict mode;
  - the effective imported value;
  - a repository rebinding and shadowing scan;
  - the test counts and mutation sensitivity.
- **`review-1/`** — independent review of `0173adf7`: **VETO** (B1–B3), with fixes.
- **`review-2/`** — independent review of the fixed revision.

## Stated limits

- The rule is static. It cannot rule out arbitrary code that another module runs at import time.
- The repository scan covers files tracked in this repository.
- Every consumer imports the template source by name, so a changed `sys.path` order is a host decision, not a checker input.
