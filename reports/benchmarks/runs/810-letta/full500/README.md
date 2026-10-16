# Letta 0.16.8 archival memory: LongMemEval-S full 500, both planes (#810 cycle 2)

**Status: candidate, complete, self-run; pending independent review.** It was preregistered before execution in `a47b032e` (`PREREGISTRATION.md`), and `preregistration.json` is unchanged after the run.

This run uses the same 500-question selection as the reviewed Hindsight, MemPalace and Agent Memory full-500 rows (`7d738ae5…`), the same frozen evaluator (blob `6b9c237`) and the same input (`d6f21ea9…`).

**What it measures:** Letta's archival-memory retrieval API, with fastembed bge-small and no LLM. It is not Letta's stateful agent.

## Native results (`{plane}.letta_archival_local.summary.json`)

All 500 questions completed on both planes, with 419 scored. There were 0 runtime failures, 0 ingestion failures, 0 out-of-corpus results and 0 unmapped results.

Letta refused 4 oversize items per plane (HTTP 400, above its archival token limit). The adapter counts these and never splits them. All 8 refusals fell on questions whose evidence was still fully retrieved (recall_all@50 = 1).

| Plane | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 |
|---|---:|---:|---:|---:|
| session | 0.857 | 0.940 | 1.000 | 0.882 |
| turn | 0.613 | 0.780 | 0.955 | 0.674 |

## Paired comparisons (`paired-and-overlap.json`, `scripts/letta_full500_compare.py`)

All comparisons are on the same 419 scored questions:
- **W/L** counts questions where only one side is fully correct, Letta's count first.
- **p** is exact McNemar.
- **Δ** is Letta − other, with a paired bootstrap 95% CI (10,000 resamples, seed 0).

Sources: Agent Memory comes from frozen `controls-500`; Hindsight (chunk-only) and MemPalace come from the reviewed runs at `8887bbe`.

### Letta against Agent Memory

| Plane, metric | Letta | Agent Memory | W / L | p | Δ [95% CI] |
|---|---:|---:|---|---:|---|
| session @5 | 0.857 | 0.823 | 42 / 28 | 0.12 | +0.033 [−0.005, +0.074] |
| session @10 | 0.940 | 0.893 | 38 / 18 | 0.0105 | +0.048 [+0.014, +0.084] |
| turn @5 | 0.613 | 0.601 | 58 / 53 | 0.70 | +0.012 [−0.038, +0.062] |
| turn @10 | 0.780 | 0.723 | 58 / 34 | 0.016 | +0.057 [+0.012, +0.100] |
| turn @50 | 0.955 | 0.859 | 50 / 10 | 1.6e-7 | +0.095 [+0.062, +0.131] |

### Letta against the reviewed frontier peers

| Plane, metric | Letta | Hindsight | W / L, p | MemPalace | W / L, p |
|---|---:|---:|---|---:|---|
| session @5 | 0.857 | 0.888 | 21 / 34, 0.105 | 0.881 | 22 / 32, 0.22 |
| session @10 | 0.940 | 0.964 | 10 / 20, 0.099 | 0.940 | 17 / 17, 1.0 |
| turn @5 | 0.613 | 0.706 | 24 / 63, **3.5e-5** | 0.668 | 32 / 55, **0.018** |
| turn @10 | 0.780 | 0.835 | 18 / 41, **0.0038** | 0.804 | 28 / 38, 0.27 |
| turn @50 | 0.955 | 0.957 | 14 / 15, 1.0 | 0.943 | 17 / 12, 0.46 |

**Reading:**
- **Pure dense passage retrieval (bge-small) has the depth.** At turn @50, Letta reaches what the hybrid peers reach and is far ahead of Agent Memory's 0.859. This supports Gap 2 (turn-plane reach) in `../../810-cycle2/ENGINEERING-HANDOFF.md`.
- **Its early ordering is weaker than both hybrid peers on the turn plane.** At turn @5 the deficit to Hindsight is significant, and on the session plane Letta sits between Agent Memory and the hybrid peers.
- **Hindsight remains the same-harness frontier on every cut.** Letta does not change the frontier.

## The subset50 result overstated Letta

The preregistered 50-question subset (43 scored) had Letta at session @5 **0.953**, the highest of any system. On the full 500 it is **0.857**, below both hybrid peers.

The subset rows are not wrong. The overlap check below shows they are identical to the full-500 rows on the same questions. The subset was simply too small and unrepresentative to rank peers 3–6 points apart.

Nothing in the subset results should be read as a frontier claim. `FRONTIER.md` and `ENGINEERING-HANDOFF.md` are updated accordingly.

## Subset50 overlap check (bridge 0.1.0 runs against this bridge 0.1.1 run)

Bridge 0.1.1 only adds deletion of each question's archive after search. Retrieval is unchanged, so metrics were expected to be identical.

| Plane | Subset run | Ranked lists differ (of 50) | Of those, same returned set | recall_all@5 / @10 / @50 differ (of 43) |
|---|---|---:|---:|---|
| session | rep 1 | 0 | — | 0 / 0 / 0 |
| session | rep 2 | 0 | — | 0 / 0 / 0 |
| turn | rep 1 | 7 | 6 | 0 / 0 / 0 |
| turn | rep 2 | 6 | 5 | 0 / 0 / 0 |

- **Turn-plane order differences** come from tied similarity scores with no total tie-break inside Letta's search. This is the same behaviour seen between subset rep 1 and rep 2 (`../subset50-rep2`).
- **One question in each comparison** has a different item at the top-50 boundary.
- **No metric changes** on any cut.

## Execution

| Item | Value |
|---|---|
| Stack | Letta 0.16.8 server (`1131535…`) on PostgreSQL 18.1 + pgvector, fastembed bge-small endpoint on loopback. The environment matches `letta-venv-freeze.txt`, which is identical to subset50-rep2 |
| Adapter | `reference/longmemeval_letta_bridge.py` 0.1.1-candidate (blob `2c719e1`) |
| Session plane | 2026-10-16 00:51Z → about 04:20Z, across 3 driver invocations (2 container restarts) |
| Turn plane | about 04:20Z → 21:38Z. Several short segments ended by container reclamation while the session was idle, then 14:07Z → 21:38Z under a bounded keep-alive (7.5 h, exit 0) |
| Resumption | Every resume continued from the committed rows; the driver checks the input sha and question ids. No row was rewritten |
| Logs | Per-segment stdout and exec records are in `execution/`. Killed segments have stdout but no exec record |
| Medians, indicative only | session ingest 16.3 s, recall 264 ms; turn ingest 59.5 s, recall 266 ms. The host was shared with the MemPalace repeat until 18:47Z |
| #808 manifests | `{plane}.letta_archival_local.manifest.json`, both `PASS: execution envelope validated, without conferring acceptance` |

## Limits

- Candidate only: no acceptance and no dashboard row. Leaderboard admission belongs to the delivery owner.
- Component tier only: Letta's archival API with this evaluator's local embedder. Letta's defaults are hosted embedders, and its agent tier is not measured.
- Retrieval only: no QA.
