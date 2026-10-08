# Canonical Agent Memory benchmark dashboard

Status: **current accepted evidence through #594, plus four accepted same-harness lanes (#640, two lane generations), plus the formal AgentMemBench/MESA baseline (#694, 2026-10-07)**, and current pre-1.0 comparator/runtime-qualification state as of 2026-10-07.

Current merged `main`: `ca0f9a748b3b7296c5a99c7e81cca35a570609fd`.

No universal aggregate score exists. `blocked`, `not_run`, `unsupported`, and `evidence_gap` are states, never numeric zero.

## How to read this dashboard

Four evidence classes are intentionally separate:

1. **Agent Memory longitudinal** — current accepted Agent Memory evidence versus an earlier accepted Agent Memory signal under a sufficiently comparable profile.
2. **Same-harness systems** — multiple memory systems executed against the same frozen input, evaluator, retrieval/context budget, and model/judge configuration.
3. **Published reference** — vendor/research results useful for market context but not numerically comparable unless methodology is proven equivalent.
4. **Runtime qualification** — implementation-profile evidence such as Python/Rust parity. This is not a memory-quality score.

A new metric having no prior Agent Memory baseline is normal. A missing controlled competitor is a **competitive evidence gap**.

## Executive view — Agent Memory longitudinal

| track | current accepted signal | previous accepted signal | delta / disposition | evidence class |
| --- | --- | --- | --- | --- |
| AgentMemBench retrieval | exact-source@5 **0.899** | 0.889 | +0.010 | external efficacy |
| LongMemEval_S session retrieval | recall_all@5 **0.823389** | 0.675 | +0.148389 | external efficacy |
| LongMemEval_S turn retrieval | recall_all@10 **0.723** | 0.525 | +0.198 | external efficacy |
| LongMemEval_M | session@5 **0.708831**, turn@5 **0.532220** | not available | first accepted M baseline | external efficacy |
| AgentMemBench currentness | new-fact **0.20**, staleness **0.80** | 0.00 / 1.00 | +0.20 / -0.20 | external efficacy |
| LongMemEval_S latest-gold-first | session **0.457**, turn **0.557** | 0.343 / 0.486 | +0.114 / +0.071 | external efficacy |
| #580 self-description currentness | **0.273** | 0.091 | +0.182 | repository-owned conformance |
| #591 search performance | p50 **7.7 ms**, p95 **11.9 ms**, wall **38.6 s** | 17.9 / 31.4 / 54.6 | -10.2 / -19.5 / -16.0 | repository-owned performance |
| #594 adapted self-validity efficacy | **EVIDENCE GAP** | not run | C=P1=P2; 0 changed rows | adapted external evidence |
| #594 proposition known precision | **0.800** | not run | first accepted natural-data baseline | repository-owned conformance |
| #594 proposition known recall | **0.148** | not run | first baseline; remediation #596 | repository-owned conformance |
| #594 unknown precision / recall | **1.000 / 0.848** | not run | first baseline | repository-owned conformance |
| #594 strict slot/value conformance | **0.000** | not run | exact-label diagnostic only; #597 | repository-owned conformance |

The strict slot/value result uses zero aliases frozen before scoring. It is exact-label conformance, not semantic-synonym precision.

## Competitive view — same-harness systems

**Status: twelve same-harness lanes accepted (#640, #669, #644, #671, #732; lane generations v1 on 2026-10-05 and 2026-10-06, the budgeted `-v2` generation on 2026-10-06, the `-v3`, `-v4` and `-v5` generations under the declared transitions to Runtime Baselines v3, v4 and v5 on 2026-10-07, and the `-v6` generation under the declared transition to Runtime Baseline v6 on 2026-10-08).**

#601 now has executable independent-harness infrastructure:

- AMB bridge merged in PR #604;
- frozen external harness revision `03c1d0f1d27da63034f0931121c858faba512383`;
- credential-free AMB retrieval lane merged in PR #606;
- manual competitive workflow at `.github/workflows/amb-competitive.yml`;
- first same-harness lane `amb-precisionmembench-retrieval-v1` (#640), **frozen before any score and now accepted**: Agent Memory (control), BM25 (baseline), and Mem0 OSS 2.2.1 explicit-memory (comparator, `reference/amb_mem0_explicit_bridge.py`); Hindsight deferred until a benchmark-agnostic provider configuration is frozen. Lane file: `reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v1.json`; see `docs/65-independent-amb-competitive-profile.md`.

The first credential-free profile is:

```text
dataset: precisionmembench
split: single-turn
mode: retrieval
providers: agent-memory, bm25, mem0-explicit
```

Frozen AMB `RetrievalMode` makes no LLM calls and scores returned belief/document IDs directly.

**Accepted same-harness rows (lane v1, 2026-10-05).** Each row was executed deliberately with the full 77-case selection on the lock-constrained harness install, its raw AMB artifact and execution identity were imported byte for byte and bound under `reports/benchmarks/amb/amb-precisionmembench-retrieval-v1/`, and an `evidence_history` entry binds it:

| row | role | system revision | run | active passes | total passes | mean precision | mean recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-memory | control | Agent Memory `703be5b` | 37349431401 | 4/43 | 15/77 | 0.18 | 0.95 |
| bm25 | baseline | AMB `03c1d0f` built-in | 37349435243 | 0/43 | 8/77 | 0.05 | 0.97 |
| mem0-explicit | comparator | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37351804149 | 0/43 | 10/77 | 0.10 | 1.00 |

`active passes/43` is the only number comparable to upstream's Active passes column; total passes include structural and trivially-empty cases a provider returning nothing can satisfy. The three rows are normalized into `reports/benchmarks/normalized/amb-precisionmembench-amb-precisionmembench-retrieval-v1-single-turn-*.json` (retrieval, efficiency and reproducibility mapped; currentness and reasoning not applicable; governance and evaluator integrity not measured) and share one scorecard with BM25 as the lexical baseline. There is still no overall score. BM25 is a baseline comparator and Agent Memory the control, not a market-position claim; every row returned nearly everything relevant and failed on precision. Hindsight remains deferred.

**Accepted same-harness rows (lane v2, `longmemeval-s-retrieval-parity-v1`, 2026-10-06).** Frozen before any score (PR #666) and executed the same day, one `.github/workflows/longmemeval-competitive.yml` dispatch per row and plane on `main` `0b0449a`, full 500-question selection of the frozen LongMemEval_S input (`d6f21ea9…a442`, the input the accepted longitudinal Agent Memory evidence used). Raw native reports and execution identities were imported by `scripts/import_longmemeval_lane_evidence.py` under `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v1/` and bound by six `evidence_history` entries. 419 scored questions per row after the upstream abstention and no-user-target exclusions; zero runtime, ingestion or out-of-corpus failures on every row.

| row | role | plane | system revision | run | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 | knowledge-update recall_all@5 | latest gold first |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent-memory | control | session | Agent Memory `0b0449a` | 37421243051 | 0.823 | 0.893 | n/a | 0.878 | 0.972 | 0.457 |
| lexical_overlap | baseline | session | runner blob `4acdecc` built-in | 37421248307 | 0.730 | 0.826 | n/a | 0.793 | 0.917 | 0.457 |
| mem0_explicit | comparator | session | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37421253480 | 0.809 | 0.883 | n/a | 0.841 | 0.903 | 0.443 |
| agent-memory | control | turn | Agent Memory `0b0449a` | 37421245382 | 0.601 | 0.723 | 0.859 | 0.682 | 0.792 | 0.557 |
| lexical_overlap | baseline | turn | runner blob `4acdecc` built-in | 37421251326 | 0.487 | 0.587 | 0.761 | 0.560 | 0.681 | 0.614 |
| mem0_explicit | comparator | turn | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37421255904 | 0.499 | 0.673 | 0.895 | 0.596 | 0.611 | 0.486 |

Session and turn are separate planes (separate scorecards) and are never averaged. `recall_all@50` exists on the turn plane only. The Agent Memory control reproduces the accepted longitudinal LongMemEval_S numbers exactly at this revision (session `recall_all@5` 0.823389, turn `recall_all@10` 0.723). The Mem0 row is the lane v1 configuration (mem0ai 2.2.1 explicit memory, pinned local embedder, local Qdrant, no fastembed/spaCy) entering through the runner's external-backend seam with `top_k=50`; it is now accepted on two frozen benchmarks. `lexical_overlap` is the profile's token-overlap baseline, not upstream's BM25 or dense retrievers. The six rows are normalized into `reports/benchmarks/normalized/longmemeval-longmemeval-s-retrieval-parity-v1-*.json` with the lane as task profile, so they share two cards (session, turn) with `lexical_overlap` as the lexical baseline and never a card with the longitudinal profile runs. There is still no overall score and no market claim. Hindsight remains deferred under both lanes.

**Accepted same-harness rows (third lane generation, `amb-precisionmembench-retrieval-v2` and `longmemeval-s-retrieval-parity-v2`, 2026-10-06).** Both lanes were frozen before any score (PR #679) and re-execute every row of their predecessors with one change: the Agent Memory control runs under the declared transition to Runtime Baseline v2 (contract 1.4.0, PR #678) and reads the facade's `returned` prefix at a declared budget (the case budget under AMB through bridge 0.2.0; 50 under LongMemEval through `--agent-memory-budget`). Nine dispatches on `main` `ca0f9a7` (full selections; the checker recorded `TRANSITION` against declaration blob `6a35746` on every row, which the importers bound); raw artifacts under `reports/benchmarks/amb/amb-precisionmembench-retrieval-v2/` and `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v2/`, nine `evidence_history` entries. The BM25, lexical-overlap and Mem0 rows are unchanged compositions re-run under the new lane ids. A `-v2` row is not comparable row-for-row with its `-v1` row (the control's return shape and the executing runtime differ); the two generations are reported side by side, never merged.

| row | role | system revision | run | active passes | total passes | mean precision | mean recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-memory | control | Agent Memory `ca0f9a7` | 37543540355 | 4/43 | 15/77 | 0.18 | 0.95 |
| bm25 | baseline | AMB `03c1d0f` built-in | 37543543416 | 0/43 | 8/77 | 0.05 | 0.97 |
| mem0-explicit | comparator | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37543546255 | 0/43 | 10/77 | 0.10 | 1.00 |

| row | role | plane | system revision | run | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 | knowledge-update recall_all@5 | latest gold first |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent-memory | control | session | Agent Memory `ca0f9a7` | 37543549261 | 0.823 | 0.893 | n/a | 0.878 | 0.972 | 0.457 |
| lexical_overlap | baseline | session | runner blob `757d593` built-in | 37543556285 | 0.730 | 0.826 | n/a | 0.793 | 0.917 | 0.457 |
| mem0_explicit | comparator | session | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37543562462 | 0.809 | 0.883 | n/a | 0.841 | 0.903 | 0.443 |
| agent-memory | control | turn | Agent Memory `ca0f9a7` | 37543552664 | 0.601 | 0.723 | 0.859 | 0.682 | 0.792 | 0.557 |
| lexical_overlap | baseline | turn | runner blob `757d593` built-in | 37543559580 | 0.487 | 0.587 | 0.761 | 0.560 | 0.681 | 0.614 |
| mem0_explicit | comparator | turn | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37543565695 | 0.499 | 0.673 | 0.895 | 0.596 | 0.611 | 0.486 |

Reading the generation change: the LongMemEval control's `unmapped_admitted_count_total` is 0 on both planes and every scored metric equals the v1 control's at every k, with the return budget applied on 39 of 500 session questions and 500 of 500 turn questions (the ranked prefix at 50 is the full ranking's prefix, exactly as #670 predicted). The AMB control's active passes, total passes, mean precision and mean recall equal the v1 control's: the only difference between the generations, mapped-among-top-k instead of skip-then-count, changed no case on this 77-case split. Neither equality is authority; both are what the frozen harnesses measured. Same-plane rule, no overall score, no market claim; Hindsight remains deferred under all four lanes.

**Accepted same-harness rows (seventh lane generation, `amb-precisionmembench-retrieval-v6` and `longmemeval-s-retrieval-parity-v6`, 2026-10-08).**
- **Freeze.** Both lanes were frozen before any score (PR #743, plan `docs/plan-732-evidence-v6.md`). They re-execute the `-v5` control and comparator rows at a runtime in the declared transition to Runtime Baseline v6: ranking policy 3.4.0, assertion filter 6.1.0 and contract 1.6.0. The proposition extractor is off by default and no lane input declares a typed proposition, so the rule is equality with `-v5`, not attribution.
- **Runs.** Nine dispatches on `main` `24048d5`, all full selections. The checker recorded `TRANSITION` toward v6 on every row. The shadow and semantic rows stay deferred.
- **Equality (V6-E1).**
  - LongMemEval: all 1000 questions across both planes are EQUAL to `-v5` (ranked output and metrics).
  - AMB: all 77 cases are EQUAL.
  - The cross-fact records equal `-v5` row by row, with 0 limited, as at `-v5`.
  - Every number in the `-v4` tables below therefore holds for `-v6`.
- **Comparators (V6-E2).** Lexical overlap and BM25 equal `-v5` exactly. Mem0 equals `-v5` on every LongMemEval question's ranked output and metrics and on every AMB case; unlike `-v5`, no near-tie reorder was observed.
- **MESA (V6-E5).** `mesa-formal-v3` (extractor off, executed at `d7b2974`) reproduces `mesa-formal-v2`: M4 new-fact 250/250, `dual_version_rate` 0.0, all wins credited to `currentness_mechanism`, no unmet stage, upstream consistent; every other phase's non-latency fields equal v2.
- **Reading.** The typed proposition and extractor path is **unaccepted** until the remediation R6 acceptance (`docs/plan-732-remediation.md`); these lanes measure the extractor-off default only. Generalization of currentness semantics remains tracked as `cross-fact-currentness-generalization-2026-10-07` (#732/#733).

**Accepted same-harness rows (sixth lane generation, `amb-precisionmembench-retrieval-v5` and `longmemeval-s-retrieval-parity-v5`, 2026-10-07).**
- **Freeze.** Both lanes were frozen before any score (PR #729, plan `docs/plan-671-evidence-v5.md`). They re-execute the control and comparator rows at a runtime in the declared transition to Runtime Baseline v5: ranking policy 3.3.0, with read-path cross-fact currentness under explicit-current recall.
- **Runs.** Nine dispatches on `main` `e6f9db7`, all full selections. The checker recorded `TRANSITION` toward v5 on every row. The shadow rows are deferred (measured at `-v4`).
- **Causal attribution (E1).**
  - LongMemEval: all 1000 questions across both planes are EQUAL to `-v4`.
  - AMB: all 77 cases are EQUAL.
  - No candidate was limited on either lane, and none is UNATTRIBUTED.
  - On the LongMemEval turn plane, the mechanism evaluated 57 pairs under explicit-current intent and refused all of them. 55 had no state-change relation, and 2 failed the G12 assertion filter.
  - Every number in the `-v4` tables below therefore holds for `-v5`.
- **Comparators (E3).** Lexical overlap and BM25 equal `-v4` exactly. Mem0 equals `-v4` on every metric. Its turn row reorders near-tied non-gold items on 45 of 500 questions (4 at `-v4`) under the same pins, which is an environment finding.
- **Reading.** The `mesa-formal-v2` M4 result (new-fact 1.000, all wins credited to `currentness_mechanism`) holds under that frozen protocol only. On these natural-language lanes the mechanism is inert. Generalization of currentness semantics is not measured; it is tracked as `cross-fact-currentness-generalization-2026-10-07` (#732/#733).

**Accepted same-harness rows (fifth lane generation, `amb-precisionmembench-retrieval-v4` and `longmemeval-s-retrieval-parity-v4`, 2026-10-07).**
- **Freeze.** Both lanes were frozen before any score (PR #716, plan `docs/plan-644-lanes-v4.md`). They re-execute every executed `-v3` row at a runtime in the declared transition to Runtime Baseline v4: public contract 1.5.0 and opt-in shadow recall control, with ranking policy 3.2.0 unchanged.
- **Runs.** Twelve dispatches on `main` `f5a79d2`, all full selections. The checker recorded `TRANSITION` toward v4 on every row, and the importers bound it. The raw artifacts are under `reports/benchmarks/amb/amb-precisionmembench-retrieval-v4/` and `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v4/`.
- **Default rows (L1).** With `recall_control` off, the control equals the `-v3` control on every scored metric. It also equals it on every LongMemEval question's ranked output, and on every AMB case's context and beliefs. The BM25, lexical-overlap and Mem0 rows equal `-v3` too, so every number in the `-v3` tables below holds for `-v4`.
- **Shadow rows (L2).** Each lane adds `agent-memory` with `recall_control="shadow"`. It equals that lane's control exactly and stays outside the scorecards. Its controller telemetry is reported but carries no authority:
  - LongMemEval: all 500 questions on each plane report `frontier_exhausted` with status `complete`, and lexical `would_truncate` on all 500, as stated before any score;
  - AMB: 68 `frontier_exhausted` and 5 `no_evidence`, with the 4 blank-query cases reported as `no_recall_executed`.
- **Mem0 environment finding.** The Mem0 turn row equals `-v3` on every metric. On 4 of 500 questions it reorders near-tied non-gold items within its own vector ranking, under the same package pins.

**Accepted same-harness rows (fourth lane generation, `amb-precisionmembench-retrieval-v3` and `longmemeval-s-retrieval-parity-v3`, 2026-10-07).** Both lanes were frozen before any score (PR #709, plan `docs/plan-669-lanes-v3.md`) and re-execute every row of their `-v2` predecessors at a runtime in the declared transition to Runtime Baseline v3 (ranking policy 3.2.0: the semantic vector route is reachable and ordering-subordinate, default off). Eleven dispatches on `main` `04bb286` (full selections; the checker recorded `TRANSITION` toward v3 on every row, which the importers bound); raw artifacts under `reports/benchmarks/amb/amb-precisionmembench-retrieval-v3/` and `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v3/`, eleven complete `evidence_history` entries. LongMemEval_S adds one measured row, `agent_memory_semantic`: the same facade with `semantic_retrieval="required"` under the pinned local MiniLM ONNX representation (config digest `sha256:7447705…`). It is a variant of the control, not a separate system, so it stays outside the scorecards, which hold one row per system. Under AMB that row is deferred: the harness's own uv.lock conflicts with the pinned semantic numerics.

| row | role | system revision | run | active passes | total passes | mean precision | mean recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-memory | control | Agent Memory `04bb286` | 37601531946 | 4/43 | 15/77 | 0.18 | 0.95 |
| bm25 | baseline | AMB `03c1d0f` built-in | 37601535521 | 0/43 | 8/77 | 0.05 | 0.97 |
| mem0-explicit | comparator | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37601539010 | 0/43 | 10/77 | 0.10 | 1.00 |

| row | role | plane | system revision | run | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 | knowledge-update recall_all@5 | latest gold first |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent-memory | control | session | Agent Memory `04bb286` | 37601498295 | 0.823 | 0.893 | n/a | 0.878 | 0.972 | 0.457 |
| agent_memory_semantic | comparator (semantic route required) | session | Agent Memory `04bb286`, MiniLM ONNX `7447705` | 37601507396 | 0.823 | 0.893 | n/a | 0.878 | 0.972 | 0.457 |
| lexical_overlap | baseline | session | runner blob `eaa7ca9` built-in | 37601515167 | 0.730 | 0.826 | n/a | 0.793 | 0.917 | 0.457 |
| mem0_explicit | comparator | session | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37601522990 | 0.809 | 0.883 | n/a | 0.841 | 0.903 | 0.443 |
| agent-memory | control | turn | Agent Memory `04bb286` | 37601502623 | 0.601 | 0.723 | 0.859 | 0.682 | 0.792 | 0.557 |
| agent_memory_semantic | comparator (semantic route required) | turn | Agent Memory `04bb286`, MiniLM ONNX `7447705` | 37601511653 | 0.601 | 0.723 | 0.859 | 0.682 | 0.792 | 0.557 |
| lexical_overlap | baseline | turn | runner blob `eaa7ca9` built-in | 37601519437 | 0.487 | 0.587 | 0.761 | 0.560 | 0.681 | 0.614 |
| mem0_explicit | comparator | turn | mem0ai 2.2.1 `94c3fe9`, no fastembed/spaCy | 37601527643 | 0.499 | 0.673 | 0.895 | 0.596 | 0.611 | 0.486 |

Reading the generation change: the shipped-default control equals the `-v2` control on every scored metric of both benchmarks and both planes (plan D1), as do the BM25, lexical-overlap and Mem0 rows. That is the acceptance evidence `reports/runtime/baseline-v3-declaration.json` names. The semantic row changes no scored metric and no per-question `recall_all@k` on either plane, which matches its pre-registered prediction (plan D2). The route admitted 2 semantic-only candidates on the session plane (22,633 admitted in total) and 123 on the turn plane (103,479 in total). One gold turn was reached only through the semantic route, and it ranked 116th of 116 admitted: policy 3.2.0 orders every semantic-only candidate after every lexical one, and the lexical route already admits at least 113 candidates per turn question. #669's movement gate therefore transfers to #673 (fusion). Same-plane rule, no overall score, no market claim; Hindsight remains deferred.

The LLM-judged AMB profile is frozen to `gemini:gemini-2.5-flash-lite` for answer and judge, but remains **blocked pending authorized evaluation credentials**.

First-wave market targets remain:

1. Mem0 OSS;
2. Hindsight;
3. Zep / Graphiti;
4. Letta;
5. Cognee;
6. LangMem.

Unsupported lifecycle or benchmark surfaces are `unsupported`, never zero.

## Formal AgentMemBench / MESA baseline (#694) — pre-major-runtime baseline

Protocol, gate history and full results: `docs/69-agentmembench-mesa-formal-baseline.md`. The run uses the upstream `mazaiying/AgentMemBench@186c9a5` harness's own phase functions at upstream defaults (seed 2027, MemDialogue v2). Agent Memory `7b041a7` takes part through the public facade with no temporal enrichment. Comparator values are **published reference under the identical frozen protocol**: they were not reproduced here, they come from a different environment, and their recall@5 is LLM-judged.

| axis | Agent Memory | Naive RAG | Mem0 | LangMem | Graphiti | Letta | class |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M2 recall@5 (judged) | **blocked** | 0.966 | 0.818 | 0.286 | 0.687 | 0.982 | blocked (no authorized judge) |
| M2 answer-substring@5 (diagnostic) | 0.728 | 0.794 | 0.421 | 0.162 | 0.222 | 0.626 | adapted; favours verbatim stores |
| M4 new-fact / staleness | **0.200 / 0.800** | 1.000 / 0.000 | 0.900 / 0.024 | 0.680 / 0.104 | 0.004 / 0.984 | 0.996 / 0.000 | exact |
| M5 leak / audited deletion | **0.000 / 1.000** | 0.000 / 1.000 | 0.000 / 1.000 | 0.000 / 0.500 | 0.000 / 1.000 | 0.000 / 1.000 | exact |
| M3 recall@3 @1,000 | **1.000** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | exact |
| M1 write success / concurrency@16 success | **1.000 / 1.000** | 1.000 / 1.000 | 0.797 / 1.000 | 0.475 / 1.000 | 0.841 / 1.000 | 1.000 / 1.000 | exact |
| M1 write mean (ms) | 6.2 | 44.6 | 1,078.7 | 4,986.6 | 8,302.6 | 4,735.4 | environment-bound |
| M6 LLM portability | not comparable | — | — | — | — | — | no executable upstream protocol |

M4 failure taxonomy (250 pairs):

- The write-time `state_change_candidate` relation was detected in all 250 pairs.
- Read-path currentness separated **0** pairs.
- BM25 decided all 250.
- Of the 50 new-fact wins, every one is `lexical_ordering`.

The adapted 0.20 / 0.80 signal is therefore confirmed under the formal protocol. It is a runtime composition gap between write-time semantics and read-path currentness (#671), not an interpretation or identity gap.

## Market context — published reference only

These rows answer “what are leading systems currently publishing?” They do **not** answer “is Agent Memory better or worse?”

| system | published signal | methodology distinction | comparability here | source |
| --- | --- | --- | --- | --- |
| **Hindsight v0.4.19** | LongMemEval **94.6%**; LoCoMo **92.0%** | single-query end-to-end accuracy in Hindsight AMB; open pluggable harness | `published_reference` until reproduced | [Hindsight AMB](https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark) |
| **Mem0 managed platform** | LongMemEval **94.4%**; LoCoMo **92.5%**; BEAM-1M avg **0.641** | managed end-to-end QA; published retrieval budgets differ | `published_reference` | [Mem0 evaluation](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-evaluation.mdx) |
| **Zep** | LongMemEval **90.2%**; LoCoMo **94.7%** | end-to-end accuracy; published retrieval p50/p95 **104/162 ms**, median context **4,408 tokens** | `published_reference` | [Zep research](https://www.getzep.com/research/) |
| **Supermemory** | LongMemEval-S **97% Recall@20** with aggregation | retrieval Recall@20, not Agent Memory recall_all@5/@10 | `published_reference` | [Supermemory research](https://supermemory.ai/research/) |
| **Cognee** | BEAM 100K **0.79**, BEAM 10M **0.67** | different benchmark family | `published_reference` | [Cognee results](https://www.cognee.ai/research-and-evaluation-results) |

Independent multi-system suites may be recorded as `external_cross_system_reference`, but they do not replace local same-harness reproduction.

## Runtime qualification — Python vs Rust

**Status: deterministic Rust shadow primitives qualified; runtime promotion not established.**

ADR-028 remains controlling: the normative core is language-neutral.

Merged PR #605 added an evaluation-only, dependency-free Rust shadow crate and shared frozen Python/Rust fixtures.

Accepted evidence:

- workflow `36457677348`: exact relevance-token vectors and every admitted-set BM25 IEEE-754 score bit reproduced on Ubuntu CI, including an exact tie;
- workflow `36458112635`: BM25 parity retained and UTF-8 SHA-256 vectors reproduced exactly.

This supports continuing the Rust qualification program. It does **not** establish:

- canonical serialization parity;
- cross-platform floating-math identity;
- lifecycle/state parity;
- matched performance advantage;
- FFI or native-Rust runtime promotion.

Current decision candidates remain:

```text
A. Python preferred runtime
B. Python facade + Rust kernel
C. native Rust runtime + Python bindings
D. parallel conformant Python and Rust profiles
```

## Architecture progression

| milestone | architectural move | evidence outcome |
| --- | --- | --- |
| frozen pre-remediation `f73b872` | baseline external retrieval/currentness | LME-S session recall@5 0.675; latest-first 0.343 / 0.486 |
| #538 | explicit ranking policy / admitted-set BM25 | retrieval improved; currentness trade-offs exposed |
| #530 | runtime-owned serialization | concurrency failure -> operation/materialization success 1.0 |
| #522 / #548 | incremental attestation + domain prefilter | major state/candidate costs removed without authority change |
| #576 | deterministic BM25 accumulation | score bits/order stable across hash seeds |
| #550 | typed proposition/cardinality/aspect/self-validity evidence | four #580 targets improved; policy 3.1.0 |
| #591 | identity-first materialization | p50 17.9 -> 7.7 ms; p95 31.4 -> 11.9 ms; rankings identical |
| #594 A | source-anchored external profile | interpreted-demotion efficacy remains evidence gap |
| #594 B | independently frozen natural-data gold | severe under-recognition exposed; #596-#598 split out |
| #600 / #601 | pre-1.0 competitive maturity program | independent AMB infrastructure now merged; result pending |
| #602 / #605 | Rust deterministic shadow | BM25/tokenization/SHA exact parity passes on qualified CI |

## #594 Phase B — unbiased Part R

| gold status | predicted known | predicted ambiguous | predicted unknown |
| --- | ---: | ---: | ---: |
| known (54) | 8 | **46** | 0 |
| ambiguous (13) | 0 | 13 | 0 |
| unknown (33) | 2 | 3 | 28 |

Largest measured weakness: **over-ambiguity / under-recognition**. Known precision is 0.80, but known recall is only 0.148. Unknown precision is 1.0.

Other Part R counters: wrong slot 8, unknown->known 2, aspect mismatch 4, aspect over-classification 1, over-eager single-valued 0.

## Governance posture

Still true:

```text
interpretation != authority
semantic interpretation != retention/lifecycle policy
classifier output != truth
classifier confidence != permission
proposal != application
ranking != admission
ranking != truth
relevance != currentness
recency != authority
newer != superseding
benchmark score != memory authority
published vendor score != same-harness comparator
implementation language != doctrine
```

Active state:

- #591 complete;
- #594 **QUALIFIED**;
- #600 pre-1.0 maturity program active;
- #601 competitive infrastructure merged; #640 first same-harness lane accepted (three rows, 2026-10-05);
- #602 Rust shadow deterministic primitive parity **PASS**, runtime not promoted;
- ADR-028 **Accepted**;
- ADR-039 **Proposed**;
- #583 / PR #587 remains **DRAFT / HOLD**;
- #585 remains next query-side RC step;
- #598 remains prerequisite before redesigned #583;
- #596/#597 remain high-priority nonautomatic RC blockers;
- #586 remains post-RC unless evidence pulls it forward.

## Next paths

```text
RC temporal path
#585
  -> #598
  -> redesigned #583
  -> final #580 replay
  -> #584
  -> RC1 declaration decision

pre-1.0 maturity path
#600
  +-> #601 first independent retrieval result
  |      -> controlled market systems
  |      -> accepted dashboard competitor rows
  |
  +-> #602 canonical bytes
         -> hot-path/state parity
         -> lifecycle shadow
         -> matched performance
         -> A/B/C/D runtime decision
```

A later 1.0 decision should require both a defensible RC disposition and a defensible maturity position. Beating one product on one benchmark is insufficient. So is merely beating our former selves.

Machine-readable form: `current.json`.
