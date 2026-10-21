# v7 lane execution on the cumulative candidate (#770, #674, #819, #410)

Independent benchmark execution and qualification of the cumulative Runtime Baseline v7 candidate
carried by PR #836. Both frozen v7 lanes were executed locally, in full, retrieval-only, with no LLM
calls, and compared question by question (LongMemEval_S) and case by case (AMB PrecisionMemBench)
with the accepted v6 evidence. **Every executed Agent Memory output equals v6 exactly.**

This is execution evidence, not acceptance. Nothing was merged, published, or promoted; the accepted
v6 records, the dashboard (`BENCHMARKS.md`, `reports/benchmarks/cross-system-posture.json`) and the
frozen lanes were not modified. No GitHub Actions run was dispatched. No paid model inference was used.

> **Two protected trees, kept apart.** Sections 1–9 describe the execution on evidence head `79172267`
> (protected runtime `07cd8692`). That tree was superseded the same day by the #836 review-follow-up
> repair (`2ad4cf23`, see `../README.md` §8), and both lanes were executed again on the repaired tree:
> section 10. The lane roots `reports/benchmarks/amb/amb-precisionmembench-retrieval-v7/` and
> `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7/` hold **only the repaired-tree
> rows** (the attribution checker and the lane tooling require exactly one record per row); the
> `79172267` rows were moved, with history, to `superseded-tree-79172267/` and are evidence for that
> tree alone. No result of one tree is attributed to the other.

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

## 10. Execution on the repaired tree (`2ad4cf23` / `9d0ba703`)

### 10.1 Identity

| Item | Value |
|---|---|
| Protected runtime tree | `git rev-parse <rev>:reference/agentmem_ref` = `f9b5ff9e79a54ef053ce89eb975256b63e211714` for every executing revision below; `runtime/recall_control.py` blob `9fa861c3…` (the #836 follow-up repair, `../README.md` §8); all other protected blobs as at `07cd8692` |
| Executing revisions | `2ad4cf23d366fc784a486b0245550230e64bfa25` (LongMemEval agent_memory session and turn, lexical_overlap session) and `9d0ba703c98cabb94933545a553c8c6ae1ab578b` (AMB agent-memory, bm25, mem0-explicit; LongMemEval lexical_overlap turn, re-run because an evidence commit landed while its first run was in flight and the runner's own revision stamp no longer matched the identity, which the importer refused). The commits between them add files under `reports/` only |
| Declaration blob (lane pins) | `7de94f11d7d521f07d2fe22317662ac6f92f89fa`; checker `TRANSITION`; lane digests AMB `53456345c1be2c0fa9679182f0c5dbf7bcd1ff25ccb8a1ddff61892cd175c1ad`, LongMemEval `9a1dab91f13a7652a181f01c35ac85c941e8be2b2538f783bc3d41c2c4ad4f6d` |
| Harness, fixtures, dataset, bridges, environments | unchanged from §1–2 (same checkouts, digests, blobs and virtual environments; `tiktoken` note of §2 applies) |

### 10.2 Results (every row paired case by case / question by question with accepted v6)

| Lane | Row | Executing revision | Parity with v6 | Headline (= v6) | Latency, this container |
|---|---|---|---|---|---|
| AMB | agent-memory | `9d0ba703` | **77/77 L1-equal**; cross-fact sidecar byte-identical (73 records, 0 limited); no flips, no lost required memories | 15/77, active 4/43, precision 0.1806, recall 0.9535, 542.2 context tokens | mean retrieve 35.7 ms (p50 35.7, p95 50.9; v6 28.1) |
| AMB | bm25 | `9d0ba703` | **77/77** | 8/77, precision 0.0536, recall 0.9651 | 4.3 ms (v6 4.1) |
| AMB | mem0-explicit | `9d0ba703` | **77/77** | 10/77, precision 0.1049, recall 1.0 | 20.2 ms (v6 12.0) |
| LongMemEval | agent_memory, session | `2ad4cf23` | **500/500/500** (ranked_top / metrics / cross-fact); complete recall@50 419/419; required evidence 794/794 | nDCG_any@10 0.878274 | wall 281 s, ingest 241 s, recall 11.0 s total / 53 ms max |
| LongMemEval | agent_memory, turn | `2ad4cf23` | **500/500/500**; complete recall@50 360/419; required evidence 746/832 | nDCG_any@10 0.68156, recall_all@50 0.859189 | wall 1050 s, ingest 993 s, recall 27.3 s total / 123 ms max |
| LongMemEval | lexical_overlap, session | `2ad4cf23` | **500/500/500**; 418/419; 793/794 | nDCG_any@10 0.792944 | wall 3.9 s |
| LongMemEval | lexical_overlap, turn | `9d0ba703` | **500/500/500**; 319/419; 680/832 | nDCG_any@10 0.559738 | wall 5.1 s |
| LongMemEval | mem0_explicit, turn | `5ed105d7` | ranked_top **453/500**, metrics 500/500, cross-fact 500/500; complete recall@50 375/419 (= v6); required evidence 776/832 (= v6); 47 questions reorder, see below | nDCG/recall metrics all = v6 | wall 3223 s, ingest 2507 s, recall 713 s total / 3.5 s max |
| LongMemEval | mem0_explicit, session | `77c06a29` | **500/500/500**; complete recall@50 378/419 (= v6); required evidence 746/794 (= v6) | all = v6 | wall 1155 s, ingest 1031 s, recall 122 s total / 0.7 s max |

Aggregates, by-question-type, currentness and governance blocks equal to v6 in every executed row; lost
complete recall: none; lost required evidence: none; runtime errors: none. The LongMemEval rows ran with
nothing else executing on the container (the AMB rows too), unlike the `79172267` rows of §3.3; the
turn-plane ingest is simply slow here.

Phase E scenario G, alternating runs on the idle container against a fresh `origin/main` worktree
(`../phase-e/main-7d4c9be6-G-r{1,2}.json`, `../phase-e/candidate-f75ecf7b-G-r{1,2}.json`, protected tree
`f9b5ff9e`): facade recall p50 61.9 / 63.4 ms (`main`) vs 84.9 / 80.5 ms (repaired tree; 73.4 / 74.1 at
`07cd8692`); `remember` p50 6.1 / 7.0 vs 7.4 / 7.1 ms; 400-neighbour hub graph recall p50 1.6 / 1.5 ms
with 4 eligible slots filled (`main`) vs 3.6 / 2.5 ms with **8** filled. The facade's default planner has
no typed-graph route, so the repair (which touches only the typed-graph retriever) cannot act on the
facade recall figure; the spread between `07cd8692` and the repaired tree on that figure is container
variance between sessions, reported as measured and not gated.

**The Mem0 turn-plane reorders (comparator row, no Agent Memory code on its path).** 47 of 500
questions return the same 50 items in a different order: 124 items move, the largest move is 5 positions,
32 questions are adjacent swaps only, **no gold item moves**, every per-question metric and every
aggregate is equal to v6 (`repaired-head/compare-lme-mem0_explicit-turn-b.json`). By type: multi-session
17, knowledge-update 10, single-session-user 8, temporal-reasoning 6, single-session-assistant 5,
single-session-preference 1. This is the same pattern the official hosted execution recorded on #770
(45 questions, 119 moves, max 4, no gold moved) and the environment-finding class the lane already allows
for this row: near-tied vector scores ordering differently under different floating-point execution
(here: numpy 2.4.3 / tokenizers 0.22.2 / openai 2.26.0 under the AMB lock vs numpy 2.5.3 / tokenizers
0.23.2 / openai 3.26.0 on the hosted runner; mem0ai, qdrant-client, sentence-transformers, torch and the
embedder revision identical). Not tuned, not root-caused here; a counterexample for nothing in the
candidate. The first session-plane run of this row (500/500 equal to v6) was refused by the importer
because an evidence commit landed while it ran and the runner's own revision stamp no longer matched its
identity; the re-run was refused for a dirty worktree stamp (files edited mid-run); the third run, with nothing touched, is the imported `77c06a29` row above (500/500 equal to v6, as were the two refused runs).

### 10.3 Checks on the repaired-tree rows

| Check | Result | Record |
|---|---|---|
| Importers, fetch enabled | 9 rows admitted (fixtures and dataset re-fetched and re-hashed); checker TRANSITION; declaration blob `7de94f11` equals the lane pin | lane roots |
| Cross-fact attribution (E1), lane roots as committed | AMB `EQUAL: 77`; LongMemEval `EQUAL: 1000`; 0 unattributed | `repaired-head/cross-fact-*-repaired.json` |
| Import re-verification (`scripts/verify_imports.py`, now keyed by executing revision) | 9/9 VERIFIED (and the 7 superseded rows re-verify under their own revision) | `checks/import-verification.txt` |
| Lane guard / importer tests after the move | 145 passed; the same two pre-existing `ReplayEvidenceFreshness` guards fail | `logs/lane-guard-tests-venv312-lme.txt` (same outcome as §4) |
| Per-row comparison records, driver logs, raw identities | | `repaired-head/` |

### 10.4 Per-lane verdict for the repaired tree

| Lane | Verdict |
|---|---|
| `amb-precisionmembench-retrieval-v7` | **QUALIFIED** (exact parity with accepted v6 in all three frozen rows at `9d0ba703`) |
| `longmemeval-s-retrieval-parity-v7` | **QUALIFIED** for the control and baseline rows on both planes (500/500 equal to v6); all six frozen rows executed. Comparator finding, not a candidate finding: the `mem0_explicit` turn row reorders 47/500 questions with no gold movement and every metric equal (§10.2), the environment class the lane allows for that row and the pattern the hosted execution already recorded |

As in §7: execution evidence, not acceptance; `TRANSITION` is not `PASS`; v6 remains the published baseline.
