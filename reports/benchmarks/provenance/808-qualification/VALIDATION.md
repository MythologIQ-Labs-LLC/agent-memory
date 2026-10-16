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
| `python -m unittest discover -s tests -p 'test_benchmark_execution_manifest.py' -v` | 14/14 OK (`baseline-891b423-unittest.txt`) | **37/37 OK** on 3.12 and 3.13 (`unittest-py312.txt`, `unittest-py313.txt`) |
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
| D1 | critical | A manifest declaring itself `accepted` + `eligible_on_profile` validated on a self-declared reviewer string plus any `decision_ref` | `accepted` needs an owner-controlled `--review-authority` decision binding reviewer, https `decision_ref`, `run_id` and normalized digest, with executor ≠ reviewer |
| D2 | critical | Artifact digests were never verified. Forged or absent native and row files passed, including for `accepted` | `--evidence-root` re-hashes the normalized run and every artifact and refuses symlink escape. Acceptance requires it |
| D3 | high | `format: date-time` was not enforced in the pinned environment, so `20261014T120000Z` passed | Explicit RFC 3339 UTC check |
| D4 | high | A parsed normalized dict counted as "normalized run verification" without any digest check (API path) | Acceptance requires the hashed file. A supplied dict must equal the hashed bytes |
| D5 | high | Hosted inference could declare cost `not_applicable` (it was refused only when `accepted`) | Refused at any status |
| D6 | medium | Pointer guard missed backslash traversal, drive letters, `~`, percent-encoding, empty segments and control characters | Refused |
| D7 | medium | Credential guard missed `--token=`, `--hf-token`, `*_API_KEY=` assignments, `sk-`/`ghp_`/`AKIA`/`hf_` values, and secrets in evidence pointers or parameter values | Refused. Token counts are not flagged (tested) |
| D8 | medium | `accepted` inference with a floating model revision (`latest`) passed | Refused unless a model digest is present |

## Tests added (#808 items 3–5)

`AcceptanceGuardTests`, 22 tests:
- a verified **synthetic** accepted fixture with real files and digests, plus a placeholder independent reviewer and authority record (`reference/fixtures/benchmarks/execution-manifest-accepted/`). Its normalized run validates against `memory-benchmark-run.schema.json`;
- forged and missing normalized-run hashes, and forged and missing artifacts;
- mismatches on system revision, input digest, sample count and selection;
- paid hosted inference declared as no cost, and an unpinned model;
- a missing row-level artifact, unreconciled wall time, non-RFC 3339 timestamps, and redaction not reviewed;
- secrets in argv, pointers and parameters;
- duplicate artifacts, malicious relative paths, and symlink escape;
- a self-declared reviewer, an authority record for a different reviewer, run or digest, and reviewer = executor.

`CatalogAssociationTests` (item 5): an opt-in `execution_manifest` artifact on a normalized run is projected by the UI catalog as a pointer, with metrics, status and `authority_effect` unchanged. No schema change was made, and no frozen run was migrated.

## Not done here

- **#808 item 6** (coverage audit of historical accepted lanes): not started in this pass.
- **Designating where an owner-controlled review authority record lives** is an owner decision. Until it is made, no real manifest can validate as `accepted`. That is by design.
