# #808 G1: the self-run candidate evidence class (preparation; admission on HOLD)

This acts on the [delivery direction](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/808#issuecomment-6222382032). It prepares a separately labelled class only. **It accepts nothing, signs nothing, and grants no leaderboard status.**

There was no hosted CI, no paid inference, no model run, and no change to the acceptance register, lanes, `main` or Pages.

## 1. The extension: smallest change

In `schemas/benchmark-execution-manifest.schema.json`, there is one new optional top-level block, `candidate_class`. `schema_version` stays `1.0.0`, and every existing manifest validates as before, except for the masquerade rule below.

| Field | Purpose |
|---|---|
| `class` | `self_run_candidate`, `self_run_diagnostic` (a check, never a score) or `self_run_not_comparable` |
| `tier` | `no_model`, `local_embedding_model`, `local_llm_ingestion` or `hosted_model`. It must agree with `inference.calls` |
| `system_variant`, `not_equivalent_to` | Keep variants apart: Hindsight chunk-only from Hindsight's LLM product; Graphiti-3B from Zep and from Graphiti with a frontier LLM; and every self-run record from frozen lane rows |
| `metric_record` | `native_report`: no `memory-benchmark-run` exists |
| `supersedes` | Exactly one superseded manifest, by path and SHA-256 |
| `corrections` | One entry per changed field: JSON pointer, original value, corrected value (`"<absent>"` if removed) and basis |

## 2. Guarantees, enforced by `scripts/validate_benchmark_execution_manifest.py`

| Guarantee | Rule |
|---|---|
| Never enters the accepted comparator set | A self-run record cannot point into `reports/benchmarks/normalized/`, either by URI or by resolved path, so symlinks are covered. That directory is the scorecard builder's output and the UI catalog's only input. With `--evidence-root`, the record must be a file inside the root and live under `reports/benchmarks/self-run-candidates/`. The scorecard builder reads an explicit lane allowlist, and the catalog reads only `normalized/`; a test asserts neither names a self-run or `runs/` path. `build_benchmark_scorecards.py --check` and `build_benchmark_ui_catalog.py --check` stay current |
| Never acceptance or eligibility | `accepted` is refused. `eligible_on_profile` is refused. Diagnostic and not-comparable records must say `not_comparable` |
| Cannot masquerade as a frozen lane | Lane ids are matched in `task_profile` **and** `run_id` after NFKC normalisation, case folding and removal of whitespace and invisible format characters, so `LongMemEval-…-V1`, padded and zero-width variants are caught. A self-run record carries the `self-run:` prefix and may name no frozen lane id. Conversely, **any** manifest naming a frozen lane must have its `normalized_run` in that lane's imported evidence or in `normalized/`, **and** a `native_result` artifact in that lane's imported evidence; an unrelated file in the lane directory is not enough. All 16 mislabelled originals are refused. Boundary: lane ids are versioned (`…-vN`). An unversioned family name such as `amb-precisionmembench-retrieval` is a benchmark id, not a lane, and is allowed |
| Tier honesty | `no_model` means no calls. `local_embedding_model` means every call is on a `local` endpoint and is embedding or rerank. `local_llm_ingestion` means every call is `local` and at least one is generation. `hosted_model` means at least one hosted call. A `self_hosted` endpoint, or a local run with only judge or `other` calls, fits no tier and is refused until the owner defines one |
| Auditable supersession | The schema requires exactly one superseded manifest and at least one correction, even without an evidence root. With `--evidence-root`, the superseded bytes are re-hashed, and every correction's original and corrected value is verified **type-exactly**, so `0`, `0.0`, `false` and `"0"` differ. Any difference no correction declares is refused; lists are compared element-wise when their length is unchanged. The literal `"<absent>"` is reserved for removed fields and refused as a real value |

**Tests:** `tests/test_benchmark_execution_manifest.py` grew from 44 to **59** tests, all passing on CPython 3.12.3 and 3.13.16. The new `SelfRunCandidateTests` class is hermetic: it builds a temporary evidence root. Mutation checks confirm that the type-exact comparison and the resolved-path guard are each what makes their tests fail when removed.

## 3. Corrected records: 21 of 21

The records are on `claude/810-external-exec-no-ci`, under `reports/benchmarks/self-run-candidates/`. They are additive: no file under `reports/benchmarks/runs/` changed. `scripts/build_self_run_candidate_records.py` generates them; `--check` reproduces the bytes, and every record validates in re-hash mode.

| Class | Records |
|---|---:|
| `self_run_candidate` | 8: 7 result rows, with Graphiti as rep1 and rep2 |
| `self_run_diagnostic` | 12 |
| `self_run_not_comparable` | 1 |

**Correction totals:** 212 corrections across the 21 records. Basis codes refer to `../808-qualification/RECEIPT-AUDIT.md`:

| Code | Corrections | What changed |
|---|---:|---|
| R1/R2 | 58 | Pointer rebasing |
| R9 | 42 | Self-run identity |
| R6 | 27 | Cost |
| R5 | 21 | `native_result` typing |
| R11 | 21 | Redaction honesty |
| R8 | 15 | LLM settings |
| class rule | 13 | Eligibility |
| R3 | 5 | AMB lane input digest `caf5869b…` |
| R7 | 5 | Adapter blobs |
| R4 | 3 | Call `purpose` |
| content-identical wording | 2 | Graphiti wording |

R10 is recorded explicitly as `metric_record: native_report`.

**Two values were not measured by the run.** They come from the pinned server source. `top_p = 0.95` is applied to Graphiti and LangMem. `max_tokens = None` applies to LangMem. Both come from llama-cpp-python 0.3.16 `llama_cpp/server/types.py`, whose sha256 `a6c5b3b8…` equals the wheel's RECORD.

**Token counts** are chat-completion usage summed from the committed shim logs; embedding usage is excluded. Graphiti's sum equals its recorded 253,829 prompt and 9,010 completion tokens. LangMem's is 72,366 and 4,422.

**`prompt_sha256` for an LLM call record** is a prompt-*set* digest:

```text
sha256( json.dumps([request["messages"] for each chat request in log order],
                   sort_keys=True, separators=(",", ":")) )
```

It is computed over `shim-calls.jsonl.gz`, and the record's `count` is the number of requests.

**Records are under the viewer's 16,000-byte cap** (the largest is 12,389 bytes), because corrections are field-level.

## 4. The 12 mislabelled manifests on `claude/817-jev-mem-execution-no-ci` (P1)

- **Same bytes.** At `38e80cde`, all 12 are **byte-identical** to audited originals: same git blobs and SHA-256.
- **Records apply there.** All 72 evidence pointers of the corresponding 12 superseding records, plus their 12 superseded-manifest pointers, resolve to identical blobs on that branch, so the records validate there verbatim.
- **Not changed here.** The branch was not touched. The coordination request is in `COORDINATION-817.md`.

## 5. Public discovery viewer (G4b): qualified locally, not deployed

The viewer is `gh-pages` at `4cf72d1f` (`assets/run-discovery.js`).

**Base behaviour, using real bytes offline** (`pages-discovery/real-records-base-817-only.json`). The 12 mislabelled manifests validate and display **numeric scores** labelled only "candidate". These include self-run Agent Memory controls and Mem0 subset rows, which the measured-leaderboard fallback can rank.

**Defects:**

| ID | Defect | Severity |
|---|---|---|
| V1 | `review.status` allowlist includes the non-v1 values `reproduced` and `reviewed` | high |
| V2 | The eligibility guard compares with `'accepted'`, which is not a v1 value. `eligible_on_profile`, any string, or a missing field all pass | high |
| V3 | No frozen-lane check on `task_profile` | high, public |
| V4 | `cohort()` labels `all-500:` selections "preregistered subset" | low |
| V5 | Size tracking covers only the source prefix, so records pointing at raw evidence elsewhere in the same commit are refused | blocks self-run display |

**Patch:** `pages-discovery/run-discovery-fail-closed.patch` (+124/−9 across 3 files). It applies cleanly to `4cf72d1f`. It:
- allows only v1 `candidate`;
- allows only `not_assessed` or `not_comparable` eligibility;
- refuses a frozen lane id anywhere in `task_profile` or `run_id`, after NFKC, case folding and removal of whitespace and format characters;
- validates `candidate_class`, including its tier against `inference.calls`, and requires it under the self-run prefix;
- withholds scores for diagnostic and not-comparable records;
- labels each row with class and tier;
- accepts the isolated `reports/benchmarks/self-run-candidates/` source prefix;
- tracks sizes of every safe blob in the pinned tree;
- fixes V4.

**Patched behaviour on the real bytes** (`pages-discovery/real-records-patched.json`):
- **Legacy manifests:** all 12 are refused for claiming a frozen lane.
- **Self-run records:** 16 LongMemEval records display with class and tier.
  - 12 diagnostics: scores withheld.
  - 4 full-500 candidates: scores withheld, because their native report has no `input` binding.
  - That is provenance only, as directed.
- **AMB records** are not discovered; the viewer's naming scheme is LongMemEval-only.

**Node tests** (`pages-discovery/node-tests-*.txt`):
- `test-run-discovery.cjs`: its fixture moved off the lane label, plus an assertion that the lane label is refused.
- `test-run-discovery-refresh.cjs`, `test-measured-leaderboard.cjs`, `test-live-evidence.cjs`, `test-external-evaluations.cjs`, `test-leaderboard-feed-authority.cjs` and `test-public-feed-atomic.cjs`: pass.
- New `test-run-discovery-self-run.cjs`: passes.

**Pre-existing failures, identical on base and patched trees (for the Pages owner):**
- `test-public-measurement-feed.cjs` needs a materialized feed argument.
- `test-evidence-transparency.mjs` has an assertion that no longer matches its code.
- `test-site-data.mjs` has a syntax error in the test.

**Deployment order matters.** Discovery adopts a source atomically, so after this patch the 12 refused manifests would also withhold that branch's Cognee and Jev-Mem progress rows. The Jev-Mem branch's owner should act first (`COORDINATION-817.md`).

## 6. Unresolved owner decisions

| ID | Decision | Owner |
|---|---|---|
| D1 | Adopt the self-run class proposal (schema block, location, validator rules) | #808 owner |
| D2 | Apply the 817 relabelling | Owner of `claude/817-jev-mem-execution-no-ci` |
| D3 | Review, apply and deploy the viewer patch, and allowlist the self-run prefix on `claude/810-external-exec-no-ci` if self-run provenance should be public | Pages owner (#807) |
| D4 | Independent reviewer and review-authority record | #808 owner; G2 HOLD unchanged |

## 7. Independent review

An adversarial review of `6fe8ad8a` (`independent-review-self-run.md`) returned "changes required, small". Like the earlier reviews, it was launched by the executing session, so it is not independent in the G2 sense.

Every must-fix and should-fix item is fixed in the commit that adds that file, and each of the reviewer's attack scripts is now refused, apart from the documented unversioned-family boundary.

