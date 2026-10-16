# #808 receipt audit of completed external benchmark runs

**What was audited.** `claude/810-external-exec-no-ci` at `8649219`, a clean detached checkout that was read and never written. It holds 21 v1 execution manifests plus the bundles they point to. The cross-checks use the accepted AMB and LongMemEval lane rows that sit in the same checkout, inherited from main.

**Reproduce:**
```bash
python scripts/audit_execution_receipts.py --evidence-root <checkout of 8649219> --evidence-commit 86492194
```
- The output is `receipt-audit-8649219.json`, byte-identical on CPython 3.12.3 and 3.13.16.
- Every number below comes from that output, unless a sentence names a different source.
- Scores are not restated here; the bundles are the record.

**Verdict:** **0 results are accepted, and 0 are eligible for acceptance today.** 7 result rows are complete, intact, profile-labelled candidates that can go to independent review once the metadata fixes below are applied. None of the 7 needs a new experiment, compute or paid inference.

An independent adversarial review of an earlier draft of this audit found:
- a weakened credential guard;
- an invented input-digest rule;
- one wrong count;
- several overstated claims.

All of those are corrected here and in the checker.

## 1. Integrity of the committed receipts

| Check | Result |
|---|---|
| Evidence files re-hashed, resolving each manifest's own pointer base | **130/130 match** their recorded SHA-256 |
| v1 schema and semantic validation as committed, without re-hashing | 12 valid, 9 refused, all on representation (section 2) |
| Same, after a mechanical projection (pointer base, the lane's input digest, enum `purpose`; nothing else) | 21/21 valid |
| Same projection in the checker's **re-hash mode** (`--evidence-root`) | **0/21 valid.** 10 fail because `normalized_run` is a gzipped report, not a `memory-benchmark-run`. 11 fail because the pointed-to report has no matching `run_id`. Both are R10 below |
| Gap types across the 21 manifests | 100 metadata, 42 governance, 4 evidence |

So the receipts are intact, but **none is a complete v1 record**, because no `memory-benchmark-run` record exists for any of these rows (R10).

**Adapter blobs** (R7). Five manifests carry `adapter_revision: 0.1.0-candidate`, across four bridge files. Each file was created in one commit inside the checkout's history, checked against the shallow boundary, so its HEAD blob is the only blob that file ever had:

| Bridge | Blob |
|---|---|
| LongMemEval MemPalace (session and turn) | `ea862138` |
| AMB MemPalace | `b60ba760` |
| AMB Hindsight | `9e4d8b52` |
| AMB LangMem | `d68a3432` |

The AMB preregistrations record these blobs directly. The LongMemEval MemPalace preregistration records commit `d4a6804`, which resolves to blob `ea862138`.

**Inference settings for Graphiti and LangMem** (R8). The committed `shim-calls.jsonl.gz` holds every chat request body:
- Graphiti made 167 requests, all at `temperature=0` with `max_tokens=16384`.
- LangMem made 35 requests, at `temperature=0` with no `max_tokens`.
- Neither sends `top_p` or `seed`. Seed 0 and `n_ctx` 16384 are server start flags in the committed `serving-start-llm.sh`.

The 4 "evidence" gaps are the values that were never sent with a request: Graphiti `top_p` (×2 manifests), LangMem `top_p` and `max_tokens`.

**They are established by the pinned server source.** For `/v1/chat/completions` in llama-cpp-python **0.3.16** (pinned in `llamacpp-venv-freeze.txt`), `llama_cpp/server/types.py` defaults to:
- `top_p = 0.95`;
- `max_tokens = None`, meaning unbounded up to `n_ctx`.

The installed file's SHA-256 is `a6c5b3b8…`, which equals the wheel's RECORD entry. So the gaps are fixable without a new run, but the source must be cited.

**Prompts.** The shim logs support a per-request prompt digest. The audit prints a prompt-*set* digest only as a convenience.

## 2. Defects in the receipts

None of these changes a measured value.

| ID | Manifests | Defect | Exact fix |
|---|---|---|---|
| R1 | 4 LongMemEval full-500 (Hindsight and MemPalace) | Pointers are relative to the manifest directory, including `../` | Rebase to the repository root (the audit computes this) |
| R2 | 5 AMB | Pointers are relative to the bundle directory | Same as R1 |
| R3 | 5 AMB | `input_sha256` is `"<beliefs digest>+<cases digest>"` | Use the frozen AMB lane value **`caf5869b…`**. The lane's own rule is SHA-256 over the raw bytes of `beliefs.seed.json` then `retrieval.cases.json`, and `scripts/import_amb_lane_evidence.py` enforces it. The component digests match the lane fixtures in order. No new rule or sign-off is needed |
| R4 | Graphiti ×2, LangMem | Call `purpose` is free text | Use `generation` and keep the description in `notes` |
| R5 | all 21 | No artifact is typed `native_result` | Re-type the native report: AMB `single-turn.json`, the LongMemEval summary or report |
| R6 | all 21 | `costs.status: not_measured`, although no inference was billed | `not_applicable`. Graphiti token counts are in `ingestion-and-usage.json`: 253,829 prompt and 9,010 completion |
| R7 | 5 (4 bridge files) | `adapter_revision` is a label | Use the recovered blob (section 1) |
| R8 | Graphiti ×2, LangMem | No prompt digest. `n_ctx` should be recorded as `context_window_tokens`. `max_tokens`/`top_p` are missing | Take them from the shim logs, the serving script and the pinned server defaults (section 1) |
| R9 | **16 LongMemEval** | `task_profile` claims the frozen lane `longmemeval-s-retrieval-parity-v1`. These runs were self-run outside that lane, on a cloud sandbox, with scorer blob `6b9c2373` (lanes v5/v6), not v1's `4acdeccc` | Relabel with the runner's own profile `agent-memory-longmemeval-retrieval-currentness-v1:<plane>` plus an explicit self-run execution class. **This is public**: see section 5 |
| R10 | all 21 | `normalized_run` points at a runner or evaluator report, not a `memory-benchmark-run` record | Produce normalized records. Where they may live is an owner decision (G1), because `reports/benchmarks/normalized/` feeds the scorecards and the catalog |
| R11 | all 21 | `redaction.reviewed: true` was set by the executor | It is a self-declaration. An owner-designated reviewer must confirm it |

## 3. Adversarial verification

### Reproducibility

Everything below was recomputed from raw committed files.

**AMB-77:**
- **Hindsight, MemPalace and Graphiti rep1 vs rep2:** correctness and the retrieved-count answer are identical on 77/77 cases for each system, with 9 and 9 correct each time.
- **LangMem:** a single complete run.
- **Graphiti's LLM calls, rep1 vs rep2:**
  - request bodies identical on 167/167;
  - completion texts identical on 167/167;
  - raw responses identical on 0/167, because each carries a per-call id and timestamp.
  - The accurate term is **content-identical**, not byte-identical.

**LongMemEval full 500, Hindsight and MemPalace, both planes:**
- 500 distinct rows;
- 419 scored and 81 excluded (30 abstention, 51 no-user-target);
- 0 runtime errors, 0 ingestion failures and 0 out-of-corpus returns;
- at most 50 items returned per question, which matches the lane's k = 50.

### Harness equivalence with the accepted lanes

**LongMemEval, self-run vs the accepted lane v6 rows, per question:**

| Row | Questions | Metrics identical | Rankings identical |
|---|---:|---:|---:|
| Lexical overlap, session and turn | 500 + 500 | 500 + 500 | 500 + 500 |
| Agent Memory, session | 500 | 500 | 500 |
| Agent Memory, turn | 500 | 444 | 500 |
| Mem0, session (subset of 50) | 50 | 50 | 50 |
| Mem0, turn (subset of 50) | 50 | 50 | 44 |

- **Lexical overlap** is deterministic and profile-local, so its exact match shows the self-run harness scores like the lane.
- **The Agent Memory turn-plane differences** are all in `turn_to_session` @30/@50. The top-50 turn rankings are identical, but the self-run control (`e4e2a4be`) is not lane v6's Agent Memory (`24048d55`, return budget 50).
  - The disclosure needed: self-run paired comparisons against Agent Memory are exact at @1–@10, but at turn→session @30/@50 they compare against a deeper-returning control.
  - The accepted baseline is the lane row, which is unchanged.
- **Mem0 turn:** on the 6 differing questions, the ranked set is the same and only the order differs. Every metric is identical. The scores behind the order were not inspected.

**AMB:** all four committed cohort tables were rebuilt with the evidence branch's `scripts/paired_amb_systems.py`, from the **accepted** lane v6 rows plus the external rep1 rows. **4/4 are identical as parsed JSON**:
- Hindsight;
- MemPalace;
- LangMem;
- Graphiti.

In those tables, Agent Memory (15/77), BM25 (8/77) and Mem0 (10/77) are the accepted lane rows; only the external rows are self-run.

All four external AMB rows used:
- AMB `03c1d0f` and the pinned fixtures;
- retrieval mode;
- no oracle and no category filter;
- no answer or judge LLM;
- no `AMB_*` overrides.

**All four pass the same 9 cases**, and those 9 are *not* contained in BM25's 8 passes. So at this protocol the AMB table separates Agent Memory from the external group, not the external systems from one another.

**Cross-lane replication.** The independent Hindsight AMB replication by another lane is cited from `640-hindsight/amb-precisionmembench-single-turn/cross-lane-replication.json`. It is not recomputed here.

### Leakage of gold labels

- **No gold-key reads.** An AST scan of 15 bridge, worker and runner files found **0** reads of a gold key. The keys checked include `answer`, `answer_session_ids`, `has_answer`, `shouldOnlyInclude`, `category` and `question_type`. The bridges receive `(id, text)` items.
- **LongMemEval ids encode the gold label** (`answer_…`). By reading the bridge code, the ids that reach each product are:

  | Product | Id it receives |
  |---|---|
  | Hindsight | `sha256(id)` |
  | MemPalace | `uuid5` |
  | Graphiti | `uuid5` |
  | LangMem | text only; ids are kept in the worker for mapping |
  | Mem0 | the raw id as metadata with `infer=False`, as in the accepted lane composition. It is not embedded or searched |

- **Residual interface risk.** The LongMemEval runner still hands each bridge the full dataset row, gold included. Bridge discipline is reviewed, not enforced.

### Hidden conditioning

- **Timestamps:**
  - Agent Memory (`observed_at`) and Graphiti (`reference_time`) receive them.
  - Hindsight, MemPalace and LangMem do not.
  - Mem0 LongMemEval receives `source_date` as metadata.

  This must travel with any published row.
- **Tiers:**
  - **no model:** lexical and BM25;
  - **local embedding model only:** Hindsight chunk-only, MemPalace, Mem0 explicit, Agent Memory;
  - **local LLM at ingestion:** Graphiti and LangMem, both on Qwen2.5-3B Q4_K_M at temperature 0;
  - **hosted model:** none.

  No row crosses tiers, and none used paid inference.

## 4. Classification

Each class is assigned under the rules in force:
- **Accepted** means a frozen same-harness lane row with a reviewer's `evidence_history` entry.
- The #807 envelope is staged, not active.

| Result | Profile and tier | Class | Reason |
|---|---|---|---|
| Hindsight 0.10.2, chunk-only, LongMemEval-S full 500, session | retrieval; local embedder | **candidate** | Complete and intact. Needs R1/R5/R6/R9/R10. Not Hindsight's LLM product. Ranking order varies by host; recall is stable |
| Same, turn | " | **candidate** | " |
| MemPalace 3.11.0 default, LongMemEval-S full 500, session | retrieval; local embedder | **candidate** | Needs R1/R5/R6/R7/R9/R10. Executed in two segments. Not MemPalace's published raw-ChromaDB figure |
| Same, turn | " | **candidate** | " |
| Hindsight chunk-only, AMB-77 protocol A | selectivity; local embedder | **candidate** | Two outcome-identical runs. Timestamps withheld |
| MemPalace, AMB-77 protocol A | selectivity; local embedder | **candidate** | Two outcome-identical runs. Timestamps withheld |
| Graphiti 0.31.1, AMB-77 protocol A | selectivity; **local 3B LLM at ingestion** | **candidate** (LLM tier only) | Two outcome-identical runs, with LLM calls content-identical (167/167). The review at `8649219` is corrected. **Not Zep, not a frontier LLM** |
| LangMem 0.0.30, AMB-77 | local 3B LLM at ingestion | **not comparable** | It measures the 3B model's tool calling, not LangMem: 4 memories written from 35 documents. Single run |
| Hindsight chunk-only, LongMemEval subset 50 (×2 planes) | local embedder | **diagnostic** | Superseded by full 500. Used for the host-variance probe |
| Mem0 explicit, LongMemEval subset 50 (×2 planes) | local embedder | **diagnostic** | A reproduction check of the accepted lane row (metrics identical on 50/50). Never a Mem0 score |
| Agent Memory and lexical controls, full 500 and subset 50 (×8) | — | **diagnostic** | Harness-equivalence controls. The accepted lane rows remain the baseline, and these never replace it |
| Cognee 1.6.4 GLiNER, generation 2 | — | **incomplete** | Stopped at 3 of 50, with no score. Owned by the cycle-2 lane |
| Graphiti, LongMemEval-S | — | **blocked** | Local CPU compute |
| LangMem, LongMemEval-S, and a valid LangMem row | — | **blocked** | Needs a capable tool-calling model: a GPU host or paid inference |
| Jev-Mem | — | **blocked** | No CUDA host |
| AML service | — | **blocked** | Owner hold |

**Labels that must travel with any candidate row:**
- "Hindsight chunk-only (`llm_provider=none`); not Hindsight's LLM product".
- "Graphiti with local Qwen2.5-3B at temperature 0; not Zep; not a frontier LLM".
- The timestamp asymmetry.
- That this is a self-run execution class, not a lane row.

## 5. Findings outside this evidence branch (reported, not changed)

- **P1 (high, public).** `claude/817-jev-mem-execution-no-ci` at `38e80cde` is on the Pages run-discovery allowlist (`data/live-sources.json` on `gh-pages`). It carries 12 of these self-run manifests, controls and Mem0 subset included, with `task_profile: longmemeval-s-retrieval-parity-v1:*`.
  - The public live-runs table can therefore show self-run rows under the accepted lane's profile name.
  - Fix: relabel them per R9 on that branch. This needs that branch's owner, and this session must not push there.
- **P2 (medium).** `assets/run-discovery.js` on `gh-pages` checks `comparison_eligibility === 'accepted'`, a value the v1 enum does not contain. That guard never fires. The script also accepts `review.status` values (`reproduced`, `reviewed`) that v1 does not define.
  - Fix: refuse `eligible_on_profile` and any non-v1 status.
  - Pages is owned under #807 and is not changed here.
