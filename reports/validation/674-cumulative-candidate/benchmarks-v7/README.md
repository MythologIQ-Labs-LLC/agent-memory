# v7 lane execution on the cumulative candidate (#770, #674, #819, #410)

Independent benchmark execution and qualification of the cumulative Runtime Baseline v7 candidate
carried by PR #836. Both frozen v7 lanes were executed locally, in full, retrieval-only, with no LLM
calls, and compared question by question (LongMemEval_S) and case by case (AMB PrecisionMemBench)
with the accepted v6 evidence. **Every executed Agent Memory output equals v6 exactly.**

This is execution evidence, not acceptance. Nothing was merged, published, or promoted; the accepted
v6 records, the dashboard (`BENCHMARKS.md`, `reports/benchmarks/cross-system-posture.json`) and the
frozen lanes were not modified. No GitHub Actions run was dispatched. No paid model inference was used.

## 1. Which tree was measured

The 2026-10-21 handoff on #770 named runtime head `2d83db0e` and evidence head `3d28a5ec` with the
declaration blob `e6620e68…`. By the time execution started, the branch had moved to the amended head
produced by the #836 owner review. **All results below are for the newer protected tree, never for
`2d83db0e`.**

| Item | Value |
|---|---|
| Executed revision (evidence head) | `7917226712c4bb83e70bf95a9093ea96667fddc8` on `claude/cool-meitner-0q368g` |
| Protected runtime head | `07cd8692bcf26fd677c71f805f04f73a6332ed91` (`79172267` adds evidence only) |
| Difference from the handoff tree `2d83db0e` | protected source differs only in `reference/agentmem_ref/runtime/recall_control.py` (#836 review repair: `opaque` predicate; blob `c16452ef…`) |
| Runtime Baseline checker at HEAD | `TRANSITION` (frozen `e98e6e7b`, 21 declared blobs, no undeclared delta) |
| Declaration blob (lanes' control-row pin) | `a78797cbfca0e017e99c7e3e00823ded3ef1653b` (`reports/runtime/baseline-v7-declaration.json`) |
| AMB lane | `amb-precisionmembench-retrieval-v7`, frozen, digest `387da8fd5959e653126c800b75a6ea03f272f4666f86cdd64e7443515d554913` |
| LongMemEval lane | `longmemeval-s-retrieval-parity-v7`, frozen, digest `66990765dffe59fe3e7b663c0c484634484caff650fb856777c2233687418b93` |
| AMB harness | `vectorize-io/agent-memory-benchmark@03c1d0f1d27da63034f0931121c858faba512383` (verified by `verify_amb_checkout`) |
| PrecisionMemBench fixtures | `beliefs.seed.json` `35659b3b…`, `retrieval.cases.json` `09e99f08…`, combined `input_sha256` `caf5869b…` (all equal to the lane) |
| LongMemEval dataset | `longmemeval_s_cleaned.json` sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, selection `all-500` |
| Bridge / runner blobs | `reference/amb_agent_memory_bridge.py` `3d9ccb31…`, `reference/amb_mem0_explicit_bridge.py` `ce41b1f5…`, `reference/run_longmemeval.py` `6b9c2373…`, `reference/longmemeval_mem0_explicit_bridge.py` `08366b72…` (all equal to the lane pins) |
| Blob/lane/digest checks | performed by the run scripts before each row (`logs/*.run.log`, first lines of `logs/amb-*.log`, `logs/lme-*.log`) |

Declaration blob history on the branch, for the record: `1f86397f` (`e656776f`) → `e6620e68` (`2d83db0e`,
the handoff) → `a78797cb` (`07cd8692`, re-pinned after the #836 review; the lanes carry this pin).

## 2. Execution environment

| Item | Value |
|---|---|
| Host | this Claude Code cloud container, `Linux-6.18.44-fc-v139-x86_64-with-glibc2.39`, 4 vCPU, 15 GiB RAM, **not a GitHub-hosted runner** |
| Python | CPython 3.12.3 (the workflows pin 3.12) in three virtual environments (`manifests/pip-freeze-*.txt`) |
| `venv312` (AMB agent-memory, bm25) | frozen harness installed under its own `uv.lock` as pip constraints: `amb-constraints.txt` sha256 `8a7f4b9b…` — byte-identical to the file committed with the v6 rows; derived with `uv 0.11.32` instead of the workflow's `uv 0.8.17` (the derived constraint set is identical, so the tool version is immaterial) |
| `venv312-mem0` (AMB mem0-explicit) | hard-link clone of `venv312` with the lane row pins applied by `scripts/amb_harness_constraints.py --memory mem0-explicit`: `mem0ai==2.2.1`, posthog lifted, `fastembed` removed (`amb-constraints-mem0.txt` sha256 `4a95a4d3…`, byte-identical to the v6 mem0 row's); posthog resolved to 7.73.3 (v6 row: 7.64.1; not on the embedding path) |
| `venv312-lme` (LongMemEval agent_memory, lexical_overlap) | `pip install -e . -r reference/requirements.txt` exactly as the workflow does |
| Answer/judge client env | `OMB_ANSWER_LLM=gemini`, `GEMINI_API_KEY=retrieval-only-unused` as the workflow sets for retrieval mode: the frozen harness constructs the client and never calls it (`answer_model`/`judge_model` recorded as null) |
| Network | `huggingface.co`, `github.com`, PyPI reachable. `openaipublic.blob.core.windows.net` is **denied** by the session policy; see §6 |
| Credentials | none; the single inert placeholder above |

**tiktoken encoding.** The frozen harness counts context tokens with `tiktoken.get_encoding("cl100k_base")`,
which downloads `cl100k_base.tiktoken` from the denied host. `litellm==1.82.1`, a locked dependency of
the harness installed from its own `uv.lock`, vendors that exact file and itself sets
`TIKTOKEN_CACHE_DIR` to its copy whenever imported. The AMB run script points `TIKTOKEN_CACHE_DIR` at that
directory; tiktoken verifies the file's pinned sha256 (`223921b7…`) before use, so the token counts are
the ones a hosted runner would compute (`avg_context_tokens` equals v6 in every row). This is recorded in
each AMB row's `execution-identity.json` under `local_execution_notes`.

## 3. Results

### 3.1 AMB PrecisionMemBench, single-turn, retrieval-only (77/77 cases every row)

Per-case pairing by `query_id`; "L1 equal" = `correct`, `context` and all nine frozen `meta` fields equal.

| Row | L1 equal | Correct | Strict (active) | Precision | Recall | Avg retrieve ms v6 → v7 | p95 ms v6 → v7 |
|---|---|---|---|---|---|---|---|
| agent-memory (control) | **77/77** | 15/77 (= v6) | 4/43 (= v6) | 0.1806 (= v6) | 0.9535 (= v6) | 28.1 → 33.2 | 33.0 → 44.5 |
| bm25 (baseline) | **77/77** | 8/77 (= v6) | 0/43 | 0.0536 | 0.9651 | 4.1 → 4.6 | 5.9 → 6.9 |
| mem0-explicit (comparator) | **77/77** | 10/77 (= v6) | 0/43 | 0.1049 | 1.0 | 12.0 → 19.6 | 16.7 → 28.5 |

Agent Memory cross-fact sidecar: 73 records, 0 limited, **byte-identical to v6**. `avg_context_tokens`
542.2 (= v6). Flips: none. Lost required memories: none (per-case `retrieval_recall` equal in all 77).

Category results, agent-memory v7 (= v6): Alias resolution 3/23, Budget eviction and capacity 3/5,
Cold start 1/1, Counter-signal 0/2, Cross-user isolation 1/1, Design boundary 2/6, Fuzzy matching and
prefix guards 3/7, Persona prelude 1/4, Ranking stability 1/3, Relation expansion 0/4, Scope
disambiguation 0/12, Supersession chain exclusion 0/3, Type routing and open questions 0/6.

### 3.2 LongMemEval_S, top-50 retrieval, both planes (500/500 questions every row)

Per-question pairing by `question_id`; 419 scored, 51 excluded (no user target), 30 excluded (abstention),
identical to v6. "Complete recall@50" = `recall_all@50 == 1` over scored questions; "required evidence" =
gold items present in the top-50 ranking, summed over scored questions.

| Row | Plane | ranked_top / metrics / cross-fact equal | Complete recall@50 | Required evidence | Headline (= v6) |
|---|---|---|---|---|---|
| agent_memory (control) | session | **500 / 500 / 500** | 419/419 (= v6) | 794/794 (= v6) | nDCG_any@10 0.878274, recall_all@10 0.892601 |
| agent_memory (control) | turn | **500 / 500 / 500** | 360/419 (= v6) | 746/832 (= v6) | nDCG_any@10 0.68156, recall_all@50 0.859189 |
| lexical_overlap (baseline) | session | **500 / 500 / 500** | 418/419 (= v6) | 793/794 (= v6) | nDCG_any@10 0.792944 |
| lexical_overlap (baseline) | turn | **500 / 500 / 500** | 319/419 (= v6) | 680/832 (= v6) | nDCG_any@10 0.559738 |
| mem0_explicit (comparator) | session | pending | | | see §6 |
| mem0_explicit (comparator) | turn | pending | | | see §6 |

Aggregates, `by_question_type`, currentness (`latest_gold_ranked_first`), governance blocks and cross-fact
summaries are equal to v6 in all four executed rows. Lost complete recall: none. Lost required evidence:
none. Runtime errors: none.

### 3.3 Latency (reported, not gated)

| Row | v6 (hosted runner) | v7 (this container) |
|---|---|---|
| AMB agent-memory mean retrieve | 28.1 ms | 33.2 ms (p50 34.0, p95 44.5) |
| LongMemEval agent_memory session | wall 197 s, ingest 171 s, recall 7.8 s total / 29 ms max | wall 262 s, ingest 225 s, recall 10.5 s total / 180 ms max |
| LongMemEval agent_memory turn | wall 417 s, ingest 393 s, recall 11.1 s total / 55 ms max | wall 985 s, ingest 930 s, recall 26.2 s total / 983 ms max |

These are single runs on a 4-vCPU container, and the LongMemEval agent_memory rows ran **concurrently with
the AMB harness installation** (a 916 MB torch wheel download and install), so the wall, ingest and
max-recall figures are not latency-clean and must not be read as a regression measurement. The AMB rows
ran with nothing else executing. The latency comparison that was run in a controlled setting is the Phase E
record in `../README.md` §5/§7 (facade recall p50 ≈ 73–82 ms at this head vs 60–65 ms on `main`).

## 4. Independent checks

| Check | Result | Record |
|---|---|---|
| Importers (`scripts/import_amb_lane_evidence.py`, `scripts/import_longmemeval_lane_evidence.py`), fetch enabled | all 7 rows admitted; fixtures and the 277 MB dataset re-downloaded and re-hashed at import (`evidence.json: input.verified_by`); checker state TRANSITION and declaration blob `a78797cb` equal to the lane pin | `reports/benchmarks/amb/amb-precisionmembench-retrieval-v7/`, `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7/` |
| Cross-fact attribution (E1 rule), AMB v6 → v7 | `EQUAL: 77`, 0 unattributed | `checks/cross-fact-amb-v6-v7.json` |
| Cross-fact attribution, LongMemEval v6 → v7 | `EQUAL: 1000` (500 × 2 planes), 0 unattributed | `checks/cross-fact-longmemeval-v6-v7.json` |
| Import re-verification (`scripts/verify_imports.py`) | 7/7 VERIFIED: every committed file re-hashes to `evidence.files`; identities byte-identical to the raw runs; AMB `single-turn.json` and `cross-fact.jsonl` byte-identical to the raw harness output; LongMemEval `report.json` + `report.rows.json.gz` recompose exactly to the raw runner report | `checks/import-verification.txt` |
| Lane guard / importer tests (`reference/tests`, `-k "770 or lane_evidence or longmemeval_lane or import_longmemeval or import_amb"`) | 34 passed, 2 failed: the two pre-existing `ReplayEvidenceFreshness` guards in `test_770_v7_lane_freeze_independent.py`, already failing at this head before any benchmark file existed (see `../README.md` §4, §7) | `logs/lane-guard-tests-venv312-lme.txt` |
| Accepted v6 evidence unchanged | tree `cb328b54…` (AMB v6) and `223bdb54…` (LongMemEval v6) identical to `origin/main`; no tracked file modified by this work | `git diff --stat` empty before commit |
| Dashboard unchanged | `BENCHMARKS.md`, `reports/benchmarks/cross-system-posture.json` untouched | idem |
| Stable pairing / sample completeness | 77 `query_id`s and 500 `question_id`s identical to v6 in every row; statuses identical | `comparisons/*.json` |
| No gold leakage | retrieval-only (`--mode retrieval`, `corpus-class external_frozen`); the bridges pinned by the lane receive documents and queries only; `answer_model`/`judge_model` null; no credential present | run scripts |
| Same-harness determinism (Agent Memory) | zero differing cases/questions across 2 independent environments and hosts (v6 hosted runner vs this container) | §3 |

Replay, crash-window, security and full-suite evidence for this exact head is in `../README.md` §7 and
`../security-replays-07cd8692…/`, `../644-v7-replays-07cd8692…/`.

## 5. Importer contract notes (read before citing a row)

- The rows were produced locally, not by the two dispatch workflows. The run scripts
  (`scripts/run_amb_row.sh`, `scripts/run_lme_row.sh`) mirror the workflows' precondition, execution and
  identity steps and lay the artifact out as `gh run download` would, so the importers bind them unchanged.
- `workflow_run_id` is the local run label (`local-amb-v7-am`, `local-lme-v7-turn-am`, …). The importers
  synthesise `workflow_run.url` from it; **those URLs do not resolve to an Actions run.** The authoritative
  identity is `execution-identity.json` (`runner` says "local cloud container … not a GitHub-hosted runner").
- The committed AMB rows do not carry the per-row store directories (`_store/…`, `history.db`, Qdrant
  files) or `run.log`; the importer never commits them. The raw `run.log` of every row is in `logs/`.

## 6. Not executed, blocked, or pending

| Item | State | Reason |
|---|---|---|
| LongMemEval `mem0_explicit`, session and turn | **pending** at this commit | started after the control rows in `venv312-mem0` (which carries the workflow's exact `MEM0_PINS`: `mem0ai==2.2.1 qdrant-client==1.17.0 sentence-transformers==5.2.3 torch==2.10.0`, no `fastembed`, no spaCy); v6 wall time was 22 min (session) and 45 min (turn) on a hosted runner. Results land in a follow-up commit; if they are absent, the rows were not completed in this session |
| `agent_memory_shadow`, `agent_memory_semantic`, `hindsight` rows (both lanes) | not run | `deferred` in the frozen lanes; the workflows refuse them |
| GitHub Actions dispatch and `amb-evidence-import.yml` | not used | assignment constraint |
| `openaipublic.blob.core.windows.net` | denied by the session's network policy | only consumer is the tiktoken encoding download; satisfied from the harness's own locked `litellm` copy with hash verification (§2). To run the harness without that substitution, add the host to the environment's allowed domains |
| mem0 posthog version (7.73.3 vs v6 7.64.1) | immaterial | telemetry package, `MEM0_TELEMETRY=false`; not on the retrieval path; AMB mem0 row is 77/77 equal |

## 7. Per-lane verdict

| Lane | Verdict | Basis |
|---|---|---|
| `amb-precisionmembench-retrieval-v7` | **QUALIFIED** (parity with accepted v6, all three frozen rows) | 77/77 L1-equal in every row; cross-fact `EQUAL: 77`; importer admitted; inventories re-verified |
| `longmemeval-s-retrieval-parity-v7` | **QUALIFIED for the control and baseline rows** (4/6 frozen rows executed); the `mem0_explicit` comparator rows are pending (§6) | 500/500 equal on both planes for `agent_memory` and `lexical_overlap`; cross-fact `EQUAL: 1000`; importer admitted; inventories re-verified |

Neither verdict is acceptance, publication, or a change to the v6 baseline. `TRANSITION` is not `PASS`;
the successor remains a candidate until the docs/67 owner steps (independent review, META_LEDGER
acceptance, publication) are taken.

## 8. Reproduction

```
# environments (python3.12), from the repository root at 79172267
python3.12 -m venv venv312 && venv312/bin/python -m pip install uv==0.8.17
venv312/bin/python scripts/amb_harness_constraints.py --amb-root <amb@03c1d0f1> --memory agent-memory \
    --output amb-constraints.txt --provenance amb-constraints-provenance.json --removals amb-row-removals.txt
venv312/bin/python -m pip install -c amb-constraints.txt -e . -e <amb@03c1d0f1>
python3.12 -m venv venv312-lme && venv312-lme/bin/python -m pip install -e . -r reference/requirements.txt

# rows (scripts in ./scripts; each verifies the checkout, lane, blobs, fixtures/dataset digests, checker posture)
bash scripts/run_amb_row.sh agent-memory local-amb-v7-am
bash scripts/run_amb_row.sh bm25 local-amb-v7-bm25
AMB_VENV=venv312-mem0 AMB_CONSTRAINTS=amb-constraints-mem0.txt AMB_CONSTRAINTS_PROVENANCE=amb-constraints-mem0-provenance.json \
    bash scripts/run_amb_row.sh mem0-explicit local-amb-v7-mem0
bash scripts/run_lme_row.sh agent_memory session local-lme-v7-session-am     # and: turn; lexical_overlap × 2
LME_VENV=venv312-mem0 bash scripts/run_lme_row.sh mem0_explicit session local-lme-v7-session-mem0   # and: turn

# comparison, import, checks
python3 scripts/compare_amb.py reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/agent-memory-24048d55e26d <run>/precisionmembench/*/retrieval/single-turn.json <run>/cross-fact.jsonl comparisons/compare-amb-agent-memory.json
python3 scripts/compare_lme.py reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6/agent_memory-turn-24048d55e26d <run>/turn-agent_memory.json turn agent_memory comparisons/compare-lme-agent_memory-turn.json
venv312-lme/bin/python scripts/import_amb_lane_evidence.py --runs-dir <runs>/amb
venv312-lme/bin/python scripts/import_longmemeval_lane_evidence.py --runs-dir <runs>/lme
python3 scripts/check_cross_fact_attribution.py --benchmark amb --v4-dir reports/benchmarks/amb/amb-precisionmembench-retrieval-v6 --v5-dir reports/benchmarks/amb/amb-precisionmembench-retrieval-v7 --output checks/cross-fact-amb-v6-v7.json
python3 scripts/check_cross_fact_attribution.py --benchmark longmemeval --v4-dir reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6 --v5-dir reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7 --output checks/cross-fact-longmemeval-v6-v7.json
python3 scripts/verify_imports.py . <runs>
```

## 9. Folder contents

- `scripts/` — the row runners, the two comparison scripts and the import re-verifier used here.
- `logs/` — the driver log of every row (`amb-*.log`, `lme-*.log`), each row's raw `run.log`, the harness
  install summary, and the lane guard test output.
- `comparisons/` — per-case / per-question v6 ↔ v7 comparison records (full differing lists; all empty).
- `checks/` — cross-fact attribution outputs and the import re-verification record.
- `manifests/` — `pip freeze` of the three environments, OS/kernel/CPU facts, the constraint provenance
  sidecars and the row removal lists.
- `raw-identities/` — the raw `execution-identity.json` of every row, as written before import.
