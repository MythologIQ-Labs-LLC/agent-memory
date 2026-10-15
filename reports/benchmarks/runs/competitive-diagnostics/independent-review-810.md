# Independent adversarial review: #810 external competitor evidence

- **Repository:** `/home/user/ext-exec`
- **Commit reviewed:** `6294f96e617e39a21f81a3b07db5563aede01157`. This is local branch `ext-exec-810`, and it equals `origin/claude/810-external-exec-no-ci`.
- **Date:** 2026-10-15
- **Reviewer stance:** independent. I had no part in producing this evidence.
- **Method:** I recomputed everything from committed files using my own stdlib Python. Scripts and intermediate outputs are in `/tmp/claude-0/-home-user-agent-memory/e3e750d6-aa32-58ce-8a57-ef081d712c0b/scratchpad/work/`.
- **Scoring:** I did not use the repository's evaluator to score. I rebuilt the corpus ids, gold, exclusion status and recall_all@k from the LongMemEval-S file at `/tmp/agent-memory-benchmark-data/longmemeval_s_cleaned.json`. Its sha256 is `d6f21ea9…a3442`, which matches the preregistrations.
- **Repository scripts:** I ran them only where the brief asked for them: the repeat comparators.
- **Read-only:** nothing in the tracked tree was modified (`git status` is clean). One failed `import run_longmemeval` did leave 44 gitignored `__pycache__/*.pyc` files under `reference/agentmem_ref/…`. They are untracked cache files. After that I used `PYTHONDONTWRITEBYTECODE=1`.

## Overall verdict

**ACCEPTABLE AS CANDIDATE EVIDENCE, with SHOULD-FIX corrections.** I found no BLOCKING issue.

- **Headline numbers:** every LongMemEval headline number reproduces exactly from the committed rows and the frozen dataset. That covers recall_all@5/@10/@50, wins/losses/ties, McNemar p and bootstrap CIs, on both planes and for both external systems.
- **Repeats:** every row-identical repeat claim reproduces.
- **AMB cohort files:** these are internally consistent.
- **Leakage:** I found no gold or benchmark-identity leakage into Hindsight, MemPalace or LangMem.
- **What needs fixing:**
  - a few factual misstatements in the repeatability prose;
  - one undisclosed input asymmetry in the AMB cohort (Agent Memory receives timestamps; the external systems do not);
  - undisclosed LangMem run-to-run nondeterminism;
  - some stale status lines;
  - a few provenance weaknesses.

---

## A. Headline numbers recomputed from rows

I rebuilt `corpus()`, gold and status from the dataset for every row of:
- `640-hindsight/full500/{session,turn}.hindsight_chunks_onnx.rows.jsonl`;
- `mempalace/full500/{session,turn}.mempalace_default_local.rows.jsonl`;
- the Agent Memory and lexical rows in `controls/full500-repeat/controls-500.json.gz`.

Every row's `gold`, `status` and `corpus_size` matches the dataset. There are 0 out-of-corpus ids and 0 runtime errors. Every row's stored `recall_all@{5,10,50}` equals my value computed from `ranked_top`. Each system has 500 rows per plane, with 419 scored on a common set.

| Plane | System | r@5 | r@10 | r@50 | vs AM @5 W/L/T, p | vs AM @10 W/L/T, p |
|---|---|---:|---:|---:|---|---|
| session | Agent Memory | 0.823389 | 0.892601 | 1.0 | — | — |
| session | Hindsight | 0.887828 | 0.964200 | 1.0 | 34/7/378, 2.53e-5 | 32/2/385, 6.94e-8 |
| session | MemPalace | 0.880668 | 0.940334 | 1.0 | 29/5/385, 3.86e-5 | 22/2/395, 3.59e-5 |
| session | lexical | 0.730310 | 0.825776 | 0.997613 | 1/40/378 | 2/30/387 |
| turn | Agent Memory | 0.601432 | 0.723150 | 0.859189 | — | — |
| turn | Hindsight | 0.706444 | 0.835322 | 0.957041 | 57/13/349, 1.03e-7 | 51/4/364, 2.05e-11 |
| turn | MemPalace | 0.668258 | 0.804296 | 0.942721 | 36/8/375, 2.54e-5 | 37/3/379, 1.95e-8 |
| turn | lexical | 0.486874 | 0.587112 | 0.761337 | 3/51/365 | 5/62/352 |

These values match all of the following exactly, to the stated rounding. **No mismatch was found:**
- the native summaries (`*.summary.json`);
- the four paired JSONs (`640-hindsight/full500/paired-vs-controls.{session,turn}.json`, `mempalace/full500/paired-vs-controls-and-hindsight.{session,turn}.json`);
- the README tables in both `full500/README.md` files;
- the handoff tables;
- the per-type @10 tables.

I also checked these supporting figures:
- **Manifest hashes:** the summary sha256 in each manifest matches the committed summary, and the manifest stdout/stderr sha256 values match the committed logs. For MemPalace these are segment 2 only.
- **Configuration:** all 1,000 Hindsight rows carry bank_config_sha256 `363201677244…`, which I re-derived from `EXPECTED_BANK_CONFIG`. `llm_calls` is 0 everywhere, and unmapped results are 0 everywhere.
- **Handoff O2/O3 figures:**
  - @1/@3/@30 and recall_any@1;
  - 74 Agent Memory misses at @5 on the session plane, 44 of them recovered by a peer, of which 25 are multi-session;
  - 75% have some evidence in the top 5;
  - 0.545 at @10 and 0.977 at @30;
  - 45.8 admitted of 48.0;
  - 50% need 3 or more evidence sessions, against 13.1% overall;
  - turn plane: 167 misses, 66 recovered.
- **Handoff O5 cost medians:** these match when computed over the 419 scored questions.
- **D1 attribution:** the question set is exactly my recomputed set of 44 recovered questions. Agent Memory's rank buckets for the 115 evidence sessions are 62/32/20/1, matching `summary.json` exactly.

## B. Preregistration timing and configuration

| Run | Prereg commit (UTC) | Exec started (UTC) | OK |
|---|---|---|---|
| Hindsight full 500 | `6dd104c` 13:15:42; `registered_at` 13:15:24 | 13:15:49 | yes |
| MemPalace full 500 | `16e5e0a` 14:00:55; bridge `d4a6804` 14:00:15 | 14:02:16; resume 20:40:05 | yes |
| MemPalace AMB | `de01780` 16:57:51 | refused launch 16:58:02; rep1 16:58:49; rep2 16:59:39 | yes |
| Hindsight AMB | `89931a8` 17:05:59 | rep1 17:06:12; rep2 17:07:44 | yes |
| Graphiti AMB | `2e82cbb` 16:53:43 | attempt 1 17:12:10 (from the shim log) | yes |
| LangMem AMB | `26cabc7` 17:40:53 | attempt 1 17:41:35; rep1 20:53:24 | yes |
| Determinism probe question ids | `3ed967e` 16:48:11 | 17:10:22 | yes |

Each preregistration file has exactly one commit, so none was modified after its run.

**Configuration matches the code:**
- **Evaluator:** `reference/run_longmemeval.py` is unchanged from `38f6a7d`. The blob is `6b9c237` at 38f6a7d, at HEAD, and at both control revisions.
- **LongMemEval bridges:** the Hindsight bridge blob is `a14e2eb9` at HEAD and in both manifests, including the subset50 manifest. The MemPalace LongMemEval bridge was last changed at `d4a6804`.
- **AMB bridge blobs:** the HEAD blobs equal the blobs in the preregistrations:
  - MemPalace `b60ba760`;
  - Hindsight `9e4d8b52` and worker `b7a5ebf7`;
  - LangMem `d68a3432`, worker `ef522d52` and shim `f9ed2829`;
  - Graphiti `37a538c7` and shim `e15ef8c4`.
  None of these files changed after its preregistration.
- **Guard and wrapper:** `amb_retrieval_no_llm.py` and `run_amb_local_evidence.py` are byte-identical to `1df28f8` (`git diff 1df28f8 HEAD` is empty), as claimed.
- **Prereg prose:** the Hindsight values (bank switches, `budget=mid`, `max_tokens=65536`, depth 50, no timestamp) and the MemPalace values (wing/room, uuid5 `source_file`, `limit=50`, credential refusal, model hashes) all match the bridge code.

Weaknesses:

- **SHOULD-FIX: an execution record captures a revision that postdates the run's start.**
  - **What happened:** `813-langmem/.../rep1/execution-identity.json` records `agent_memory.revision = be5cade`, committed at 22:12:10. The run started at 20:53:24 from the live worktree `/home/user/ext-exec`, which kept receiving commits during the run.
  - **Why it matters:** `run_amb_local_evidence.py` takes `git rev-parse HEAD` after the run. Its `bridge_blobs` list does not include the LangMem bridge, worker or shim.
  - **Impact here:** git history shows those files were unchanged since `9b0ef39` (17:21), so there is no actual effect. The record is still not a trustworthy statement of what started.
  - **Same pattern elsewhere:** `controls/full500/controls-500.json.gz` records `agent_memory_revision 8f3591f` (05:18) for a run that started at 04:41, while its manifest says `e4e2a4b`. The repeat's output records `agent_memory_revision: null`.
  - **Fix:** record HEAD and all bridge blobs at launch, and fail if they change.
- **NOTE: two artifacts are not preregistrations despite their names or timing.**
  - `mem0/subset50-repeat/preregistration.json` was written by the run itself: `registered_at` 20:48:11 is 4 s after exec start at 20:48:07, and it was committed only with the results. The README does not call it a preregistration, but the file name invites that reading.
  - The #819 attribution script (`d867c2e`, 17:16:29) was committed 22 s after its execution started (17:16:07). It is a diagnostic, not a score.
- **NOTE: the resume check is narrower than the README suggests.** `run_longmemeval_resumable.py` compares only `question_ids` and the input sha256 against the frozen preregistration, not the backend or bridge. The MemPalace README says the check "refuses any other selection", which is accurate but narrow. The backend identity on resume rests on the rows filename and the argv.

## C. Bridges: leakage and identity mapping

**No gold or benchmark-identity leakage was found.**

- **LongMemEval seam:**
  - The retriever is passed `(question, items, row_index, row)`. `row` is the full dataset row, including `answer` and `has_answer`. `items[].id` encodes `answer_`/`noans_`.
  - Both bridges ignore `row` and `date`.
  - Hindsight retains `item.text` under the native id `"agent-memory-comparator-" + sha256(id)`.
  - MemPalace files `item.text` with `source_file = "lme-" + uuid5(ns, id)`. Its drawer id is the product's own content hash.
  - Neither sends an id, date or flag into product-visible text or metadata.
  - **NOTE:** the seam itself hands bridges the gold-bearing row. Safety therefore depends on review of every bridge, not on construction.
- **Identity mapping:**
  - Hindsight raises on an unknown or missing `document_id`, and there is no fallback guessing.
  - MemPalace maps only drawer ids and `source_path` pairs it filed, and counts the rest as unmapped. 0 were unmapped across 2,000 rows.
  - MemPalace maps one drawer to every id that filed identical content (`already_exists`: 625 events on the turn plane). I checked the dataset: **no gold turn shares its exact text with any other corpus item in any question.** So this fan-out can only consume slots (a slight deflation for MemPalace) and cannot inflate recall.
  - Hindsight and MemPalace collapse repeated ids. Agent Memory and lexical return duplicate session ids on 11 or 4 scored questions per plane, following upstream. Deduplicating Agent Memory's lists changes **0** outcomes at @5/@10.
- **AMB, no-LLM tier:**
  - MemPalace and Hindsight get `document.content` only, with uuid5 or sha256 opaque keys. Belief ids, scope tags, `context` (`beliefId=… scope=…`), timestamps and categories are withheld.
  - Every returned item resolved through `source_id` (MemPalace 1,371, Hindsight 1,371, LangMem 417). **None** used AMB's `marker` or `lexical` fallback.
- **LangMem provenance (`langmem_amb_worker.py`):**
  - **Rule:** every memory created or changed during a document's `invoke` is attributed to that document, and attributions accumulate. In rep1, memory 1 is attributed to `b-comm-response-length`, `b-comm-pushback` and `b-kubernetes-entity`.
  - **Effect:** a single retrieved memory therefore fans out to several belief ids. That can inflate recall, by crediting beliefs whose content the memory may no longer hold. It deflates precision and `shouldOnlyInclude`.
  - **Net:** 0/43 active passes, so the correct count is not inflated. The reported recall of 0.093 may be slightly inflated by fan-out, and the precision of 0.017 deflated.
  - **Labelling:** "Mean memories returned 5.5" is really mean attributed belief documents, from AMB's "N memories retrieved".
- **Graphiti (no result yet):**
  - It maps `edge.episodes` to the episode uuid and then the document. It fans out one document per supporting episode.
  - **Potential inflation path:** unmapped edges are passed to AMB's own resolver, whose `_lexical_match` credits a belief when an LLM-written fact names its canonical name or alias, or when Jaccard is at least 0.6. That rule applies to every provider, but only Graphiti produces unmapped free-text items. Report `resolution` method counts with its result.
  - Graphiti is given `reference_time = document.timestamp`. The Graphiti preregistration discloses this, and its withheld list correctly omits timestamps.

## D. Protocol parity

- **LongMemEval:**
  - The input sha256 is identical across the Hindsight, MemPalace and control manifests and the controls output.
  - The selection is identical: all 500, ids sha `7d738ae5…`.
  - Exclusions are identical (30 abstention + 51 no-user-target), verified per row.
  - Depth is 50 for all.
  - No system receives dates: Agent Memory has `temporal_metadata: none`, and the external bridges send none.
  - Parity is good.
- **SHOULD-FIX: an undisclosed AMB input asymmetry.**
  - `reference/amb_agent_memory_bridge.py` calls `memory.remember(…, observed_at=document.timestamp)`, so Agent Memory receives document timestamps. MemPalace, Hindsight and LangMem have timestamps withheld (`not_supplied: timestamps`).
  - The comparability statements ("Same harness, inputs, budgets, scorer…", in each AMB preregistration and README) do not mention this.
  - Agent Memory's whole lead is in Alias and Fuzzy matching, and Supersession is 0/3 for all systems, so the headline is unlikely to be affected. But "same inputs" is inaccurate.
  - **Fix:** disclose the asymmetry, or justify it, for example by arguing the products expose no timestamp-free equivalent. Hindsight's `retain` does accept a timestamp.
- **Capability tiers:**
  - LangMem's README and the handoff keep it in a separate LLM-at-ingestion tier.
  - **NOTE:** `813-langmem/.../paired-vs-cohort.json` and the LangMem README still report a cross-tier paired McNemar against Agent Memory (+0/−6, p=0.031). This was preregistered as an outcome and is not a ranking, but it sits awkwardly with "not ranked with the no-LLM rows".
- **Hindsight's description:** it is consistently described as chunk-only, `llm_provider=none`, and not its LLM product or the published 66/77 or LongMemEval figures. This holds in the preregistrations, READMEs, manifests and handoff.
- **NOTE: different Python versions across the "cross-host" repeat.** The Hindsight subset50 run, the left side of the cross-host comparison, ran on Python 3.12.3 (`subset50/hindsight-50.exec.json`). Full 500 ran on 3.13.16. The PREREGISTRATION says the freeze is "byte-identical", which is true of the packages, not the interpreter. Disclose this.
- **NOTE: manifest lock hash.** The AMB manifests for MemPalace and Hindsight put the **AMB process** freeze hash (`67062a7c…`, graphiti-amb-venv) in `dependency_lock_sha256`, not the product's environment. The product freeze is named in the preregistration instead.

## E. Repeat claims, re-run

| Claim | Command or check | Result |
|---|---|---|
| Controls full 500: 2,000/2,000 identical | `scripts/compare_longmemeval_rows.py controls/full500/… controls/full500-repeat/… --scope exact`, 4 plane×backend pairs | all exit 0, `equal: true`. My own field comparison agrees, and full rows minus timing are identical |
| Mem0 subset50 repeat: 100/100 identical | same script, with `mem0/subset50/mem0-50.json.gz` vs `subset50-repeat/{plane}.mem0_explicit.rows.jsonl` | both exit 0, 50/50 compared, 0 differences. The selection hash `5266568e…` is equal |
| MemPalace AMB rep1 = rep2 | `scripts/compare_amb_runs.py` | exit 0, 0 differences |
| Hindsight AMB: outcomes identical, order varies | `scripts/compare_amb_runs.py` | exit 1, 78 differences. `correct` is the same on all 77 cases; summaries are equal |
| Hindsight cross-host subset50 vs full500 | my comparison of the committed files | same returned set 50/50, order differs 40/50 |

**SHOULD-FIX: the stability prose is wrong in two places.**

- **nDCG changed on 2 questions, not 1.**
  - `640-hindsight/full500/README.md` (lines 53–54) says "the same recall@k … nDCG changed on 1". Commit `a3b1372` says "recall_all@k identical … nDCG differs on 1".
  - The committed diff `subset50-vs-full500.session.differences.txt` shows metric differences on **2** scored questions: `ef66a6e5` and `gpt4_45189cb4`.
  - On `gpt4_45189cb4`, **recall_all@3 changes 1.0 → 0.0**, and ndcg@3 changes 1.0 → 0.620.
  - So recall_all@k is not identical at all k. It is identical at the reported headline depths 5, 10 and 50.
- **"recall_all@k is unchanged in every repeat so far" is false at k=3.** The same claim appears in `determinism-probe/README.md` (lines 49–50) and is echoed in the handoff (O6). The determinism-probe selection rule was built on "the one cross-host nDCG change". Restate both claims as "recall_all@{5,10,50} unchanged".

**NOTE:**
- `640-hindsight/amb-…/README.md` says "27 of 77 cases return the same set in a different order", and separately that one set changed. The JSON and my count give 26 same-set reorders + 1 set change = 27 order differences.
- The same README still says the determinism probe "is prepared". It has since completed (`22e2eae`).

**SHOULD-FIX: undisclosed LangMem nondeterminism.**
- The same configuration (temperature 0) produced different ingestion trajectories in all three attempts. Per-document `memories_changed` over the first documents:
  - attempt 1: `1 0 0 0 0 1 0 1 1 0 …`
  - attempt 2: `1 1 0 0 0 1 1 0 1 1 …` (10 of the first 19 changed)
  - rep1: `1 1 0 0 0 0 0 0 0 0 0 1 …` (7/35 in total)
- Plausible causes are the shared, concurrent llama.cpp server (it was serving Graphiti at the same time) or batching nondeterminism.
- The README's "Very few memories were stored … 7 of 35" is therefore one draw from a visibly variable process, and no rep 2 exists. The preregistration said "rep 2 if host time allows". Disclose the variability, citing the aborted-attempt logs that are already committed.
- The README's "on the other 7 of the 35 calls, the model answered without any tool call" is also incomplete. The shim log shows 5 `Memory` and 23 `PatchDoc` tool calls, and 21 of the PatchDoc calls changed nothing.

## F. Statistics spot-checks

- **Exact McNemar:** I computed it independently for all 16 pairs in A. Every value matches the JSON and the README:
  - session @5 Hindsight: 34/7 → 2.53e-5;
  - turn @10 MemPalace: 37/3 → 1.95e-8 (README "2e-8");
  - turn @10 Hindsight: 51/4 → 2.05e-11 (README "<1e-8").
- **AMB McNemar:** 0/6 → 0.03125, 0/7 → 0.015625, 1/6 → 0.125. All correct.
- **Bootstrap CIs:** I used an independent bootstrap (different RNG and seed, 20,000 resamples, percentile). It agrees with every committed CI to within Monte-Carlo error:
  - session @5 Hindsight: committed [+0.0358, +0.0931], mine [+0.0358, +0.0931];
  - turn @10 Hindsight: committed [+0.0811, +0.1456], mine [+0.0788, +0.1456];
  - turn @5 MemPalace: committed [+0.0382, +0.0979], mine [+0.0358, +0.0979].
- **NOTE: p-values rounded to zero.** The paired JSONs round p to 8 decimals, so several are stored as `0.0` (for example turn @10 Hindsight and lexical). The READMEs correctly say "<1e-8", but the JSON should not show p = 0.

## G. Misleading, overstated, selective or missing

- **SHOULD-FIX: the handoff is stale.**
  - `competitive-diagnostics/2026-10-15-819-handoff.md` still lists LangMem as "(running)" in its cohort table and status table. The LangMem result (9/77) was committed in `6294f96`.
  - The Graphiti AMB run was relaunched after the container restart (`296c917`, about 20:54), but no outcome, progress or abort record for that third attempt is on the branch. Its status must be recorded either way: completed, failed or still running.
- **SHOULD-FIX: the handoff omits the one LongMemEval competitor that trails Agent Memory.**
  - The handoff is framed as "where external memory systems beat or trail Agent Memory". It cites the Mem0 repeat (100/100 identical) but not Mem0's LongMemEval scores.
  - On the subset50 turn plane, Mem0 explicit **trails** Agent Memory:
    - r@5 0.512 vs 0.628;
    - r@10 0.651 vs 0.721;
    - 43 scored questions.
  - On the session plane it is roughly at parity (0.884 vs 0.837 @5; 0.907 vs 0.907 @10).
  - It is a different (subset) cohort, but omitting the only trailing LongMemEval peer makes O1 read as "every peer wins". Add one line.
  - Cognee (stopped at 3/50, no score) and Jev-Mem (blocked) are also unmentioned in the handoff. They are disclosed in their own directories.
- **NOTE: wording.** The Hindsight full500 README per-type table is captioned "recall_all@k" but the values are @10 (verified). Say @10.
- **NOTE: what AMB's 9/77 means.** The 9 correct cases for MemPalace, Hindsight and LangMem are the **identical** 9 cases (6 structural + 3 trivially-empty). LangMem reaches them with recall 0.09 and 4 stored memories, so 9/77 is effectively a floor that needs no retrieval skill. AMB's correct count therefore does not discriminate among the external systems, and Agent Memory's +6 is the whole signal. The READMEs say "0/43 active", which is adequate, but stating the floor explicitly would help readers.
- **NOTE: missing repeat for MemPalace on LongMemEval.** There is no MemPalace LongMemEval repeat. Its determinism rests on the AMB repeat (77 cases). Its LongMemEval nDCG and order stability are unverified.
- **NOTE: missing records for MemPalace segment 1.** Segment 1 of the MemPalace full 500 has no exec record and no peak RSS. Its log hashes are not in the manifests, which hash only segment 2's stdout and stderr. This is disclosed, and I verified the resume integrity:
  - session rows are byte-identical to `f81681d`, committed before the restart;
  - the turn rows' `finished_at` values are monotone, with a gap between rows 349 and 350 (20:36:54 → 20:40:59);
  - 849 rows predate the restart;
  - the combined wall time is 23,678.07 + 5,285.51 = 28,963.58 s.
- **Failed and aborted attempts:** all are disclosed except the third Graphiti attempt (above). That covers:
  - the MemPalace AMB launch refused for AWS keys;
  - LangMem and Graphiti attempts 1 (tool timeout) and 2 (container restart);
  - three failed Mem0 repeat launches;
  - the superseded Hindsight v0.1.0 run;
  - the MemPalace restart.

## Findings summary

| # | Severity | Finding | Files |
|---|---|---|---|
| 1 | SHOULD-FIX | Cross-host Hindsight claims are wrong: nDCG changed on 2 questions, not 1, and recall_all@3 changed on `gpt4_45189cb4`. "recall_all@k unchanged in every repeat" holds only at k = 5, 10 and 50 | `640-hindsight/full500/README.md:53-54`, `determinism-probe/README.md:49-50`, handoff O6 |
| 2 | SHOULD-FIX | Agent Memory gets AMB document timestamps (`observed_at`); the external systems have them withheld; "same inputs" does not disclose this | `reference/amb_agent_memory_bridge.py:270`; AMB `PREREGISTRATION.md` and README comparability lines |
| 3 | SHOULD-FIX | LangMem's ingestion is nondeterministic across attempts at temperature 0 (shared LLM server); this is undisclosed, and there is no rep 2 | `813-langmem/amb-…/README.md`; `aborted-attempt*/stderr.txt.gz` vs `rep1/stderr.txt.gz` |
| 4 | SHOULD-FIX | Handoff is stale: LangMem is listed as "running"; Graphiti attempt 3 has no outcome or status recorded | `competitive-diagnostics/2026-10-15-819-handoff.md`; `812-graphiti/amb-…/` |
| 5 | SHOULD-FIX | Handoff omits Mem0's LongMemEval subset50 result, where Mem0 trails Agent Memory on the turn plane | handoff O1 and cohort table |
| 6 | SHOULD-FIX | Execution identities record a post-run HEAD from a worktree that was committed to during the run; the LangMem identity omits the LangMem bridge, worker and shim blobs; the baseline revision is inconsistent or null | `813-langmem/.../rep1/execution-identity.json`, `controls/full500{,-repeat}/controls-500.json.gz`, `scripts/run_amb_local_evidence.py:179` |
| 7 | NOTE | The LangMem fan-out attribution can inflate recall and deflate precision; "memories returned" means attributed documents | `reference/langmem_amb_worker.py` |
| 8 | NOTE | Graphiti's unmapped edges fall through to AMB's lexical resolver; report resolution counts with its result | `reference/amb_graphiti_bridge.py` |
| 9 | NOTE | The LongMemEval seam passes the full gold-bearing row to bridges; current bridges ignore it | `reference/run_longmemeval_resumable.py`, `reference/run_longmemeval.py` |
| 10 | NOTE | p-values are stored as 0.0 in the paired JSONs | `paired-vs-controls*.json` |
| 11 | NOTE | The cross-host Hindsight repeat also crossed Python 3.12 → 3.13 | `640-hindsight/subset50/hindsight-50.exec.json` |
| 12 | NOTE | Smaller wording issues: "27 same-set reorders" is 26 + 1; "probe is prepared" is stale; the per-type table does not state k; `preregistration.json` in the Mem0 repeat is not a preregistration; the attribution script was committed after its run started; the resume check verifies selection only | various |
| 13 | NOTE | AMB 9/77 is a no-skill floor shared by all external systems, including the near-empty LangMem store | `*/amb-…/paired-vs-cohort.json` |
| 14 | NOTE | Manifest weaknesses: MemPalace `adapter_revision` is a version label, not a git blob; AMB manifests' lock hash is the AMB process environment | manifests |

## What I could not verify

- **The Agent Memory, BM25 and Mem0 AMB reference results** (15/77, 8/77, 10/77, "reviewed at `1df28f8`"). Their `single-turn.json` files are not on this branch. I checked only that these rows are identical across the three cohort JSONs, and that their W/L counts are arithmetically consistent with the correct counts (wins − losses = Δcorrect).
- **Agent Memory's AMB "avg context tokens 542"** and its "AMB repeats identical (reviewed)".
- **Anything that needs the product installs or the network.** I did not re-run Hindsight, MemPalace, LangMem or Graphiti, so these rest on the committed rows and logs:
  - product-internal behaviour, such as MemPalace's rerank defaults, chunk size and max_distance;
  - the Hindsight `ts_rank_cd` tie mechanism, beyond the committed `arm-analysis.txt` and `probe.json.gz` summary, which agree with the README;
  - model and package hashes.
- **Whether preregistration commits were pushed before the runs.** I verified commit timestamps against exec start times only. Push times are not visible locally.
- **The Hindsight in-run rank distributions in D1.** These come from a fresh attribution run that is not committed, with per-question detail withheld. I verified only the question set and Agent Memory's ranks. Hindsight's top-5 count in the committed full500 rows is 105, against 106 in the attribution run. That difference is consistent with D2's fresh-ingestion reordering.
- **Graphiti's AMB outcome:** no result exists on the branch.
- **Timing and RSS:** I accepted the exec records' timing and RSS values as recorded.
