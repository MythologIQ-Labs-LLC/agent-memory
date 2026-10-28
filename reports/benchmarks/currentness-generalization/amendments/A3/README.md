# Amendment A3 (#732 G3b, #786): semantic template pin — re-gate record

**Status:** under independent re-gate. A3 is not accepted until a review of an exact revision returns PASS.

## What A3 is

- The historical G3b pin is a whole-file blob, `745f789c…`, of `reference/run_semantic_route_ordering_report.py`.
- That pin, the corpus, the 0.5 threshold, K1–K8, and strict historical mode (`--require-frozen-blob`) are preserved unchanged.
- A3 lets the checker accept a changed template source file only at an **audited full blob** (`AUDITED_TEMPLATE_SOURCE_BLOBS`; currently `7cb95356…`, the #786 `run_m4` host-binding change).
- An audited blob must still pass, mechanically:
  - it decodes identically under Python and as UTF-8;
  - its `CONFLICT_TEMPLATES` literal and the 15 derived texts equal the frozen ones;
  - that literal is the file's only binding of the name, with no dynamic-namespace primitive anywhere;
  - no host file shadows it.
- The checker itself must be the audited checker (`CHECKER_AUDIT_SHA256`). Its contamination comparison (`COMPARISON_RULE_SHA256`) must equal the one at the gate-binding revisions 5555504 and 76a9e30, and its rule objects must be its own unwrapped definitions.
- A new template source blob, or any checker edit, is a new audit.

## Deliberate changes to historical behaviour

- The frozen path and strict mode compare the **full** frozen blob, not the 32-bit prefix `745f789c`. A prefix collision with an altered template was demonstrated in review 1 (A4), and the gate-frozen checker would have accepted it. The genuine frozen bytes are classified exactly as before; replays on every recorded input are byte-identical.
- The frozen path also checks the recorded template-text digest.

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
- **`review-2/`** — independent review of `656bbe4d`: **VETO** (N1), with the structural fix.
- **`review-3/`** — independent review of the fixed revision.

## Stated limits

- The checker cannot vouch for itself against edits to itself. The gate binds the checker blob, and `CHECKER_AUDIT_SHA256` only makes an unrecorded edit fail closed in band.
- The static rules cannot rule out arbitrary code that another module runs at import time. The audited-blob list bounds what is accepted, and the repository scan covers tracked files.
- The repository scan covers files tracked in this repository.
- Every consumer imports the template source by name, so a changed `sys.path` order is a host decision, not a checker input.
