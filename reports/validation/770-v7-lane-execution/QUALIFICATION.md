# #770 official v7 lane execution and evidence import

## Outcome

**All nine intended benchmark runs completed successfully, were imported by the official import workflow, and independently re-verify.** Every Agent Memory control output equals the accepted v6 evidence, question by question:

| Benchmark | Verdict counts | Unattributed |
|---|---|---|
| AMB | `EQUAL: 77` | 0 |
| LongMemEval-S (both planes) | `EQUAL: 1000` | 0 |

**One measured deviation:** in a comparator only, Mem0 on the LongMemEval-S turn plane. It changes no scored metric, and it is diagnosed but not root-caused (section 5).

- The accepted v6 evidence and v6 lanes are byte-identical to `main`.
- **This is not v7 acceptance.** Formal acceptance is left to a separate independent reviewer.
- Nothing was merged, published, or entered in META_LEDGER.

## 1. Preflight

| Check | Result |
|---|---|
| Implementation branch | `implementation/770-v7-lane-freeze-review-no-ci` @ **`9b025f945e7ec4a1e349e56bba251e3122413e88`** (exact) |
| Evidence branch, before import | `evidence/770-v7-lane-import` @ `9b025f9`, the adopted commit |
| Lane digests | AMB v7 `12acd4c7495efc906a6efcf05d33b93ff24183d63f29482619f70658daf4117d`; LongMemEval v7 `e730636fb92d23e2dc1681c5edc09f011705d97bdca7d53097d6957f52104a4c` |
| Declaration blob | `ae8012a7540d43e589a31d00161bd30a82e3b73f`; checker reports TRANSITION v6 to v7, no deltas |
| Workflows | `amb-competitive.yml`, `longmemeval-competitive.yml` and `amb-evidence-import.yml` are active. At `9b025f9` the v7 lane IDs are dispatch options. |
| `gh` CLI | Not authenticated in this environment (`GH_TOKEN` invalid). Dispatch, listing and logs went through the GitHub API tools instead. |
| Ref execution | Every run reports `head_branch` = the implementation branch and `head_sha` = `9b025f9`. Logs show `LANE_FILE=…-v7.json` and checker state TRANSITION at that SHA. |
| Default lanes | No default was used. Every dispatch passed `lane_id` explicitly, and no v6 lane executed. |

## 2. Runs (`runs.json`)

The Agent Memory controls ran first. Their identities were inspected before any comparator was dispatched:
- revision `9b025f9`;
- TRANSITION state, declaration blob `ae8012a`;
- AMB harness constraints `8a7f4b9b`, the same as v6;
- LongMemEval input `d6f21ea9`, runner blob `6b9c2373`;
- full selection, no credentials.

| Run | Row | Conclusion | Artifact zip sha256 |
|---|---|---|---|
| [38031417209](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031417209) | AMB agent-memory | success | `8f9e1ce2…` |
| [38031874405](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031874405) | AMB bm25 | success | `10b597f4…` |
| [38031876286](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031876286) | AMB mem0-explicit | success | `a8f45ce4…` |
| [38031419237](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031419237) | LongMemEval agent_memory, session | success | `9941033f…` |
| [38031420941](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031420941) | LongMemEval agent_memory, turn | success | `6636b1a6…` |
| [38031877700](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031877700) | LongMemEval lexical_overlap, session | success | `069fa1f2…` |
| [38031879634](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031879634) | LongMemEval lexical_overlap, turn | success | `13d278ed…` |
| [38031881481](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031881481) | LongMemEval mem0_explicit, session | success | `caff6aa4…` |
| [38031883040](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38031883040) | LongMemEval mem0_explicit, turn | success | `eb474261…` |

The full inputs, timestamps, artifact IDs, sizes and full digests are in `runs.json`. **There were no failures and no reruns.**

## 3. Import

| Import run | Lane | Runs | Result |
|---|---|---|---|
| [38032778567](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38032778567) | amb | the 3 AMB runs | success, commit `54e1be9` |
| [38035027175](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/38035027175) | longmemeval | the 6 LongMemEval runs | success, commit `30d22e9` |

Each import commit adds files only under its own v7 evidence root.

`scripts/verify_imported_v7.py` (output in `results/verify-imported.json`) re-verifies every committed record from the committed bytes:
- each committed file re-hashes to the run's own sha256 inventory;
- the run ID, revision `9b025f9` and lane digest are the expected ones;
- the importers' own refusal functions admit the record against the lane read at the executing revision: `check_lane_pins`, `_check_identity` and `runtime_baseline_binding`, each giving TRANSITION and `ae8012a`.

**Result: 9/9 VERIFIED.** Every record has `evidence_class` `same_harness_external_candidate` and `authority_effect` none.

## 4. Comparison with accepted v6 (`results/compare-v6-v7.json`)

**Agent Memory:**

| Row | Per-question result | Retrieval headline | Currentness | Governance |
|---|---|---|---|---|
| AMB agent-memory | 77/77 equal on `correct`, `context` and every `meta` field. Attribution: `EQUAL: 77`. Cross-fact sidecar byte-identical (73 records, 0 limited). | 15/77 correct; active 4/43; precision 0.1806, recall 0.9535 (equal) | — | Equal |
| LongMemEval agent_memory, session | 500/500 equal on `ranked_top`, metrics, cross-fact, `admitted_count` and status | nDCG_any@10 0.878274, recall_all@10 0.892601 (equal) | `latest_gold_first` 124/158/218 (true/false/n.a.); knowledge-update recall_all@10 0.987179 (equal) | Equal |
| LongMemEval agent_memory, turn | 500/500 equal on the same fields | nDCG_any@10 0.68156, recall_all@50 0.859189 (equal) | 135/147/218; knowledge-update recall_all@10 0.935897; cross-fact refusals `relation_not_state_change` 55 and `change_evidence_not_assertive:1` 2 (equal) | Equal |

LongMemEval attribution against v6 gives `EQUAL: 1000`, with every changed rank count at 0.

**Comparators:**
- AMB bm25 and mem0-explicit: 77/77 equal.
- LongMemEval lexical_overlap, both planes: 500/500 equal.
- LongMemEval mem0_explicit, session plane: 500/500 equal.
- **LongMemEval mem0_explicit, turn plane: 45 changed `ranked_top` orderings (section 5).** Metrics, aggregates and currentness are equal.

**Efficiency** is reported only, never gated; the full figures are in `compare-v6-v7.json`.

| Row | v6 | v7 |
|---|---|---|
| AMB control, mean retrieve | 28.14 ms | 16.97 ms |
| AMB control, ingestion | 277.6 ms | 192.3 ms |
| LongMemEval control, session wall | 199.8 s | 174.6 s |
| LongMemEval control, turn wall | 418.5 s | 653.8 s (ingest 392.7 s to 612.7 s; recall max 0.055 s to 0.057 s) |
| Mem0, session wall | 1350.8 s | 1324.2 s |
| Mem0, turn wall | 2732.1 s | 2643.3 s |

These are single runs on shared hosted runners, so wall-clock times are not comparable at that precision. The turn-plane ingest slowdown has no counterpart in any recorded output; it is noted for the reviewer.

## 5. Measured deviation: mem0_explicit, turn plane (comparator)

**What changed.** 45 of 500 questions return the same item set at the same length, in a different order. In detail:
- **119** items moved: 91 by one position, 22 by two, 5 by three, 1 by four.
- **32** questions are adjacent swaps only.
- **No gold item moved.**
- **0** metric or `latest_gold_first` changes.

At v5 to v6 this row was identical on every question. `diagnosis/mem0-turn-reorder.txt` lists the question IDs.

**Ruled out:**
- **Agent Memory code.** This row does not execute it.
- **Pinned packages.** mem0ai 2.2.1, qdrant-client 1.17.0, sentence-transformers 5.2.3 and torch 2.10.0 are identical, as are the embedder revision `b207367` and the bridge blob `08366b72`.
- **The tokenizers drift (0.23.2 to 0.23.3).** Re-tokenizing all 11,214 texts of the affected questions with both versions gives identical token IDs (`diagnosis/tokenizers-0.23.2-vs-0.23.3.txt`).
- **openai 3.28.0 and posthog 7.67.0.** These are not on the embedding or search path: the LLM is guarded and telemetry is off.

**Remaining differences:**
- Python 3.12.14 to 3.12.15 on the turn runner.
- The hosted runner's CPU, which the identity does not record.

The pattern (small displacements among non-gold items) fits near-tied vector scores ordering differently under different floating-point execution.

**Not done:**
- **No root cause is confirmed.** Confirming it needs a determinism rerun of this row on the same commit, which is about 45 Actions minutes. That is an owner decision.
- **No tuning.**

**Recommendation:** record the runner CPU model and the transitive package set in the Mem0 row's execution identity.

## 6. Boundaries

| Item | Result |
|---|---|
| v6 AMB evidence tree | `cb328b54…` on `main` and on the evidence branch: identical |
| v6 LongMemEval evidence tree | `223bdb54…`: identical |
| v6 lanes | `f25355d0…` and `1c0f9b93…`: identical (`results/v6-byte-identity.txt`) |
| Lane definitions and implementation branch | Not modified |
| Replay fixtures | Untouched |
| Recall and stopping authority | Not expanded |

Nothing was merged to `main`, v7 was not published, and no META_LEDGER acceptance was made.

## 7. Remaining blockers before formal v7

1. Independent review and acceptance of this lane evidence, including a ruling on the Mem0 turn deviation and, optionally, the determinism rerun.
2. Independent acceptance of the replay evidence in META_LEDGER.
3. Runtime Baseline Step A merge, then B1 publication with the Gauntlet workflow, then B2.
4. Decisions on F6, F7 and F12.
