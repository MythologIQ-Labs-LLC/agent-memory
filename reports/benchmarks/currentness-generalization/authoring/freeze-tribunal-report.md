# QOR Gate Tribunal: #732 freeze PR (PR #738) and amendment A2

- **Target:** head `76a9e30` on `claude/relaxed-knuth-q6tp8s`, diffed against the #737 merge `a283aaa`. Three commits:
  - `1c3e970`: the freeze;
  - `5e199e1`: amendment A2, with redacted transcripts;
  - `76a9e30`: the redaction test.
- **Verdict: PASS.** No blocking findings; 4 advisories.
- **Thresholds:** untouched.
- **Runner:** I did **not** run it on the frozen corpus. I found no runner output anywhere in the scratchpad.

## Verified by execution

All scratch work is in `gate732/freeze/`.

### (1) Redacted transcripts against the live unredacted files (A2, D2)

`scripts/redact_authoring_transcript.py verify <live> <committed>`:

| Transcript | Live sha256 (= manifest `original_sha256`) | Committed redacted sha256 (= manifest) | verify |
|---|---|---|---|
| attempt 2 (`agent-a35d62e5a5879eaa5.jsonl`) | `1b6f4065…d74f` | `0805692b…9873` | **PASS**, 0 problems |
| attempt 1 (`agent-a95e496b91139d3ed.jsonl`) | `8b682608…8ffa` | `7f09a8bf…e637` | **PASS** |
| dry run (`agent-abfee79b7dbf81cea.jsonl`) | `719394e0…8741` | `4f941090…dbb3` | **PASS** |

- **Sensitive strings.** Every committed file under `reports/benchmarks/currentness-generalization/` was searched for the user's email, `@gmail`, `claude.ai/code` / `session_01…` links, the organization UUID, `userEmail`, and the system-prompt opener "You are an agent for Claude Code". There were **0 matches**.
- **What survives redaction.** Only harness record metadata: `sessionId`, `cwd`, `slug`. These are local identifiers, not links.
- **Live attachments, attempt 2.** I scanned all 37 attachment records for #671/#732/G12/`cross_fact`/MESA/task-list strings and found none. There are no `system` records. The redaction therefore hides only harness context.

### (2) G1 audit on attempt 2

| Transcript | Manifest | Verdict | Violations |
|---|---|---|---|
| redacted | `scratchpad/run732-2/manifest.json` | **PASS** (exit 0) | 0 |
| redacted | committed `attempt2/manifest.json` (value files restored, see M1) | **PASS** (exit 0) | 0 |
| live | `scratchpad/run732-2/manifest.json` | **PASS** (exit 0) | 0 |
| live | committed `attempt2/manifest.json` (value files restored, see M1) | **PASS** (exit 0) | 0 |

- **Counts:** spawn 1, reminder 1, coordinator 2, tool_result 27; Read 2, Write 22, SubagentHandback 3. There is one hand-back per pass, and each has input `{"message":"done"}`.
- **Redaction is verdict-neutral.** The redacted and live transcripts give identical counts.
- **Both coordinator messages match the frozen prompts.** The audit's rule (b)(3) enforces equality to `PREFIX` + interpolated frozen prompt + `SUFFIX`:
  - Message 1 is `variants.txt` (`2e11b4e4…`) interpolated with `selection.json`. That file is byte-equal to `freeze/selection.json`.
  - Message 2 is `replace.txt` (`4741ab43…`) interpolated with `rej-v1.json`. That file is byte-equal to `authoring/attempt2/rejections-variants-r1.json`. Its parsed content equals `check-variants-r0.json`'s `rejections`: 8 `K6_variant_apostrophe`.
- **Replays of the other transcripts:**
  - **Dry run:** PASS against the pre-A1 prompts from `7b5f7a1`. Against the current prompts it is INVALID only on its two coordinator messages, as expected because `variants.txt` changed.
  - **Attempt 1 (discarded):** PASS against the pre-A1 prompts under the A1 audit.
- **Wrapper bytes (J2).** The frozen `PREFIX` and `SUFFIX` are confirmed under the **current** prompts by attempt 2's own two coordinator records.

### (3) Assembly, final check and selection

- **Assembly.** I copied `authoring/attempt2/author-files/` and ran `check_generalization_corpus.py --author-dir … --selection freeze/selection.json --assembled-out …`. Exit 0, 0 rejections.
  - The assembled `corpus.json` and `variants.json` are **byte-identical** to `freeze/corpus.json` (`cf2e7646…`) and `freeze/variants.json` (`72588822…`).
- **Selection.**
  - Running `select_metamorphic_bases.py` on the assembled corpus with a fresh corpus-only check (0 rejections) reproduces `freeze/selection.json` byte for byte (`6a1ae7e6…`).
  - Running it with the committed `check-corpus-r0.json` gives the same result.
- **Committed check logs:**
  - `check-corpus-r0.json`: 0 rejections (9 corpus parts);
  - `check-variants-r0.json`: 8 rejections;
  - `check-variants-r1.json`: 0 rejections;
  - `check-final.json`: 0 rejections;
  - `rejections-final.json`: `[]`.
- **Shape of the frozen data:**
  - **Corpus:** 316 cases (P 156, R 56, N 104), across 33 families, every one at its exact size (P = 12, R and N = 8).
  - **Variants:** 560 (320 must-change, 240 invariance, of which 76 are `n/a`).

### (4) Runtime unchanged; tests are synthetic

- Since the plan PASS (`7a19358`), no file under `reference/agentmem_ref` or `pyproject.toml` has changed.
- `check_runtime_baseline_equivalence.py --candidate HEAD` reports **PASS** against v5 (frozen `74c8683`).
- `reference/tests/test_currentness_generalization.py` builds only synthetic `_case(...)` fixtures in temporary directories. It never references `freeze/`.
- `pytest` on that file plus `test_benchmark_deficit_ledger.py` gives 33 passed (including `RedactionTests`).
- I found no runner stage output in the repository or the scratchpad.

### (5) No orchestrator edit to case text

- **Committed files equal the author's final writes.** I rebuilt the author's last `Write` content per file from the **live** transcript's `tool_use` inputs. All 17 committed `author-files/*.json` are byte-equal to those last writes, and no written file is missing.
- **The live author directory matches.** The files in `scratchpad/author732-2/` are byte-equal to the committed copies, and its `brief.md` is byte-equal to the frozen `prompts/brief.md`.
- **The replacement round touched only the rejected records.** Rebuilding the round-0 variant state from the first 17 writes and comparing it with `freeze/variants.json`:
  - exactly the 8 rejected ids were removed;
  - exactly 8 `…-v2` ids were added, each with the same `(base_case_id, variant_type)` pair;
  - the other 552 records are unchanged.
- **The corpus is untouched since round 0.** The round-0 corpus equals `freeze/corpus.json`.

### (6) N1 pre-flight held

- Attempt 2's attachment types are all on the allowlist: `auto_mode`, `credential_org`, `date`, `deferred_tools_delta`, `environment`, `mcp_instructions_delta`, `model`, `prompt_snapshot`, `remote_session_change`, `session_context`, `skill_listing`, `total_tokens_reminder`.
- There is no `task_reminder`, `queued_command` or `edited_text_file`, and no `system` record.

## Amendment A2 assessment

- **The redaction rule is narrow.** Only the `attachment` and `rendered` values of `type:"attachment"` lines are replaced, each with `{type, sha256 of canonical JSON}`. Every user and assistant line, which is where the G1 channels live (spawn, coordinator messages, tool inputs), stays byte-identical.
- **`verify()` is exact.** It checks line count, byte equality of every non-attachment line, and exact equality of each redacted attachment record. Its test covers a tampered non-attachment line.
- **The cost is a reliance on this container.** A future reviewer without the live file can confirm attachment *types*, which is all the audit uses, but not attachment *content*. The D2 check above is therefore the binding evidence that the hidden content is harness context only. This report records it.
- **The owner decision is respected.** No change to the plan's rules beyond Gate history.

## Advisories

- **M1 — Committed manifest names value files that are not committed.** `authoring/attempt2/manifest.json` names `selection.json` and `rej-v1.json`, which are not in that directory. Their bytes are committed under other names (`../../freeze/selection.json` and `rejections-variants-r1.json`, both verified byte-equal). Copy them under the manifest's names, or point the manifest at the committed paths, so the audit replays from the repository alone. The dry-run and attempt-1 directories already do this correctly.
- **M2 — Stale iteration in the freeze manifest.** `freeze/manifest.json` `"plan"` says "iteration 6". The plan is now iteration 7 (A2). Update it, or bind the plan's blob or sha256 instead of an iteration label.
- **M3 — The round-0 author state is not committed.** It is reconstructible from the committed transcript, because `Write` inputs are on non-redacted assistant lines; I verified this above. Committing either the round-0 parts or this tribunal's reconstruction digest would make (5) checkable without re-deriving it.
- **M4 — Record the binding evidence before the container ends.** This report is the only record of the D2 live-hash and attachment-content check. Cite it, with its sha256, in the META_LEDGER freeze entry.
