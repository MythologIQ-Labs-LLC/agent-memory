# #808 offline qualification of the v1 execution manifest

**Scope.** Schema `schemas/benchmark-execution-manifest.schema.json`, checker `scripts/validate_benchmark_execution_manifest.py`, synthetic fixtures and tests, as staged on `implementation/807-benchmark-execution-envelope-no-ci` at `891b4234e8877ec1c92bab311b9c5788f16b5b0c`.

**Branch.** `claude/808-provenance-qualification-no-ci`, an isolated branch with no PR. Hosted CI used: **0**. No paid inference, and no model runs.

## Environment

- Two isolated venvs, each with only `reference/requirements.txt` (pinned) plus an editable install of this package:
  - CPython **3.12.3**, the lane's interpreter: `venv-py312-freeze.txt`;
  - CPython **3.13.16**: `venv-py313-freeze.txt`.
- `jsonschema==4.26.0`, using `Draft202012Validator` with `format_checker=FormatChecker()`.
- `rfc3339-validator` is **not** installed by the pinned profile. As a result, the active format checkers do not include `date-time`, and the schema's `format: date-time` was a no-op. See defect D3.

## Prescribed commands (#808 item 2)

| Command | At `891b423` (baseline) | After fixes |
|---|---|---|
| `python -m unittest discover -s tests -p 'test_benchmark_execution_manifest.py' -v` | 14/14 OK (`baseline-891b423-unittest.txt`) | **44/44 OK** on 3.12 and 3.13 (`unittest-py312.txt`, `unittest-py313.txt`) |
| `python scripts/validate_benchmark_execution_manifest.py reference/fixtures/benchmarks/benchmark-execution-manifest-example.json` | PASS | PASS (candidate; no acceptance conferred) |
| `python scripts/validate_schemas.py` | 75 schemas, 64 fixtures, 5 audit events, 2 projections, 19 rights records | identical |

Adjacent checks after the fixes:
- `python -m unittest discover -s tests`: 55/55 OK.
- `reference` UI catalog tests: 11/11 OK.
- `scripts/build_benchmark_ui_catalog.py --check`: current.

No existing test was weakened. All 14 original tests are unchanged and pass. One check now refuses the original `test_accepted_hosted_model_requires_cost` scenario earlier, and its message still contains the phrase that test asserts.

## Defects found and fixed

`defect-probe.json` is the output of `scripts/probe_execution_manifest_defects.py <validator at 891b423>`. It is identical on 3.12 and 3.13. Every probe below **PASSED on `891b423`** and is **REFUSED** after the fix.

| ID | Severity | Defect at `891b423` | Fix |
|---|---|---|---|
| D1 | critical | A manifest declaring itself `accepted` + `eligible_on_profile` validated on a self-declared reviewer string plus any `decision_ref` | `accepted` needs a `--review-authority` decision binding reviewer, an https `decision_ref` with a host, `run_id` and normalized digest, with executor ≠ reviewer after normalisation and type checks. **The record's SHA-256 must equal an owner-published digest (`--review-authority-sha256`)**: the checker cannot otherwise tell an owner's record from one the manifest author wrote |
| D2 | critical | Artifact digests were never verified. Forged or absent native and row files passed, including for `accepted` | `--evidence-root` re-hashes the normalized run and every artifact and refuses symlink escape. Acceptance requires it |
| D3 | high | `format: date-time` was not enforced in the pinned environment, so `20261014T120000Z` passed | Explicit RFC 3339 UTC check |
| D4 | high | A parsed normalized dict counted as "normalized run verification" without any digest check (API path) | Acceptance requires the hashed file. A supplied dict must equal the hashed bytes |
| D5 | high | Hosted inference could declare cost `not_applicable` (it was refused only when `accepted`) | Refused at any status |
| D6 | medium | Pointer guard missed backslash traversal, drive letters, `~`, percent-encoding, empty segments and control characters | Refused |
| D7 | medium | Credential guard missed `--token=`, `--hf-token`, `--openai-api-key=`, `*_API_KEY=` assignments, `sk-`/`ghp_`/`AKIA`/`hf_` values, and secrets in evidence pointers or parameter values | Refused. The original substring checks are kept verbatim, so nothing the first revision refused now passes (re-checked against the reviewer's attack set). Only exact token-count parameter names (`max_tokens`, `max_output_tokens`, …) are exempt |
| D8 | medium | `accepted` inference with a floating model revision (`latest`) passed | Refused unless a model digest is present |

## Tests added (#808 items 3–5)

`AcceptanceGuardTests`, 29 tests:
- a verified **synthetic** accepted fixture with real files and digests, plus a placeholder independent reviewer and authority record (`reference/fixtures/benchmarks/execution-manifest-accepted/`). Its normalized run validates against `memory-benchmark-run.schema.json`;
- forged and missing normalized-run hashes, and forged and missing artifacts;
- mismatches on system revision, input digest, sample count and selection;
- paid hosted inference declared as no cost, and an unpinned model;
- a missing row-level artifact, unreconciled wall time, non-RFC 3339 timestamps, and redaction not reviewed;
- secrets in argv, pointers and parameters;
- duplicate artifacts, malicious relative paths, and symlink escape;
- a self-declared reviewer, an authority record for a different reviewer, run or digest, and reviewer = executor.

`CatalogAssociationTests` (item 5): an opt-in `execution_manifest` artifact on a normalized run is projected by the UI catalog as a pointer, with metrics, status and `authority_effect` unchanged. No schema change was made, and no frozen run was migrated.

## Independent review

An adversarial review of the first commit (`5a86518e`) returned "changes required". These fixes were made after it:

- **The credential guard had regressed** for embedded or suffixed flags, and for keys containing "tokens". It is now a superset of the original.
- **The authority record was not bound to the owner.** It now needs an owner-published digest. Identity checks are normalised and type-checked, and a malformed record is a `BLOCKED`, not a traceback.
- **A bare `https://` was accepted as a decision reference.** It is now refused.
- **DEL and Unicode separators passed the pointer guard.** They are now refused.
- **A gzipped normalized run failed** with a decode error. It is now a clear refusal.
- **One branch could not be reached.** It is simplified.
- **The audit had invented a composite input-digest rule.** It now uses the AMB lane's existing rule.
- **The audit had one wrong count** and several overstated claims (see `RECEIPT-AUDIT.md`).

`AcceptanceGuardTests` gained 7 regression tests for these findings.

## Also in this pass

- **#808 item 6:** the historical coverage proposal is in `HISTORICAL-COVERAGE.md`.
- **Receipt audit of the real external runs:** `RECEIPT-AUDIT.md`.
- **Integration handoff:** `INTEGRATION-HANDOFF.md`.
- **Owner decision still needed:** where an owner-controlled review authority record lives. Until that is decided, no real manifest can validate as `accepted`, by design.
