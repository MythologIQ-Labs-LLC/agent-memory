# Gate 2: product quality execution and remediation (real MCP consumer path)

**Verdict: Gate 2 is NOT passed, and the remediation here does not claim it.** What this directory
proves, from execution on Linux with the real stdio MCP server:

1. the committed development probe runs and its measurement tests pass (Phase 1);
2. every irrelevant evidence item on the development cohort comes from the runtime's lexical
   route matching nothing but function words ("is", "the") and from BM25 ties among such items;
   no required evidence is lost, truncated or unattributed by the MCP path (Phase 2);
3. the smallest grounded fix, selector policy **0.5.0** (opt-in `experimental_selectivity`),
   removes 30% of the irrelevant items on the development cohort and 45% on a post-freeze
   cohort with **zero loss of required evidence on every regression set** (dev probe, AMB 77,
   LongMemEval_S session and turn, LoCoMo, LoCoMo adversarial, 1k/19k synthetic) (Phases 3-4);
4. the indexed SQLite FTS5 comparator still delivers fewer irrelevant items than the opt-in
   profile at equal `k` and equal full-text capacity, because the runtime's lexical route admits
   function-word-only candidates that FTS5's stop list never retrieves, and the owner's
   zero-loss gate forbids a consumer-side rule that would drop the remaining ones (section 6);
5. a task-level harness with a small open extractive reader over the delivered evidence runs end
   to end through the real MCP tool (Phase 5); on a 22-question post-freeze cohort the reader
   answers 15/16 answerable questions from the default MCP evidence, 14/16 from the opt-in
   profile and 14/16 from FTS5, and never abstains on the 6 unanswerable questions in any arm;
   the cohort is author-written, so it is not a sealed holdout (section 7).

The **default** `memory_find` profile is unchanged (`all_returned`). Promotion of the qualified
profile to the default is an owner decision; the evidence for and against it is in section 6.

Branch `product/819-mcp-gate2-task-probe-no-ci`, starting commit
`1943c57f69df09d08daeb1947a118f2a881bd368` (contains the Gate 1 head `5584fd27`). No GitHub
Actions, no merge, no release, no frozen baseline, accepted fixture or baseline declaration touched;
every commit `[skip ci]`. `recall()` and the default `recall_context` profile are byte-identical
before and after (section 4).

## 1. Environment and execution record

| item | value |
|---|---|
| checkout | clean `1943c57f` (verified before Phase 1) |
| Python / platform | CPython 3.12.3, Linux x86_64 (`logs/gate2-venv-versions.txt`) |
| `mcp` / `mcp-types` / `pydantic` / `anyio` | 2.3.0 / 2.3.0 / 2.14.1 / 4.15.1, `agent-memory-reference` 0.2.0 editable |
| MCP runtime configuration | `AGENT_MEMORY_MCP_ROOT` fresh temp store per probe run, tenant `tenant:quality-probe`, actor `agent:quality-probe`, scope `project:quality-probe`; `memory_find(max_items=5)`, bridge caps 1,200 chars/item, 5,000 chars, 1,250 tokens |
| reader venv (Phase 5 only) | separate venv: onnxruntime 1.31.0, tokenizers 0.23.3, numpy 2.5.4, same `mcp` 2.3.0 and editable package (`logs/reader-venv-versions.txt`) |

Phase 1 commands, exactly as the brief lists them, at `1943c57f`:

| command | result | log |
|---|---|---|
| `python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_quality_probe.py" -v` | **10 OK** | `logs/test_quality_probe-1943c57f.log` |
| `python integrations/agent-memory-mcp/quality_probe.py --max-items 5 --out …` | exit 0, 14 questions | `before/am-gate2-dev-1943c57f.json`, `logs/quality_probe-1943c57f.log` |

## 2. Baseline measurement (development cohort, `k=5`)

18 fictional records, 14 questions (11 answerable, 3 no-answer). Both arms index the same texts;
every fixture text fits both arms' full-text capacity, so a key hit is full delivery in both.

| arm | answerable complete | required items | unexpected items | forbidden incidences | mean precision | no-answer empty | p50 / p95 ms |
|---|---|---|---|---|---|---|---|
| MCP default `all_returned` @1943c57f | 11/11 | 11/11 | 47 | 15 | 0.288 | 0/3 | 47.6 / 85.0 |
| MCP opt-in selector 0.4.1 @1943c57f (diagnostic, `before/…policy-0.4.1…`) | 11/11 | 11/11 | 42 | 13 | 0.297 | 0/3 | 40.6 / 93.9 |
| SQLite FTS5 (unicode61, bm25, OR terms) | 11/11 | 11/11 | 22 | 11 | 0.518 | 1/3 | 0.1 / 0.2 |

Every MCP evidence item was `resolved` with its full seeded text and an exact `memory_ref`; zero
unattributed, truncated or unavailable items on any question (`mcp_incomplete_text_items = 0`).
Latency is the real stdio round trip including the governed runtime open/close per call; FTS5 is an
in-process query over an already-built index and pays no governance or transport cost.

## 3. Per-question diagnosis (Phase 2)

Method: the same 18 records were loaded through the facade and every question's full admitted set was
dumped with route provenance and ranking evidence (`diagnostics/recall_admissions_dump.py`,
`diagnostics/recall-admissions-dev-cohort-1943c57f.json`).

Findings that hold for all 14 questions:

- **Every candidate comes from the lexical route only** (no exact-identity seed, no shared-evidence,
  no semantic route: `semantic_retrieval` is `off`). The route's raw score is the fraction of query
  tokens found in the fact, **function words included**: for "What color is Liora's canoe?" eleven
  of the eighteen facts are admitted, six of them (meridian-meeting, office-printer, maya-editor,
  moon-exhibit, …) on the single token "is". For "When does the lunar eclipse committee meet?" all
  eleven admitted facts match only "the".
- **Ranking** (policy `multi-route-default` 3.4.0, `bm25_admitted_set`) puts facts sharing a content
  term first; the remaining slots up to `k` are filled by function-word-only facts in BM25 tie
  order. So every answerable question is complete (the required fact always shares a content term)
  and the burden is the tail.
- **Ties among genuinely related facts are not broken by subject**: A2 "Where does Mara's parent
  work?" and A3 "Which instrument does Mara's child play?" both rank `mara-child` above
  `mara-parent` (each shares only "Mara"; "parent"/"father" and "child"/"eldest" never match). Both
  facts are delivered; the consumer must disambiguate. This is a paraphrase limit of a lexical
  runtime, identical in FTS5.
- **False exact match**: A4 "Where does Liora's brother live?" ranks `office-printer` first because
  the fact says "Brother HL-L2400D"; FTS5 does the same. The required `liora-sibling`
  ("sibling resides") is still delivered (ranked by "Liora's").
- **No-answer questions receive five items each**: N1 ("garage door access code") legitimately
  matches "code" (code-editor) and then pads; N2 pads entirely on "the"; N3 matches "Harbour
  Library" (quail-meeting, a forbidden distractor by design) and pads.
- Not a retrieval failure, a ranking failure, a delivery failure or a bridge failure in the sense of
  lost or corrupted evidence: the defect is **candidate admission on function words plus delivery of
  everything returned**. The bridge adds nothing and hides nothing.

Why the 0.4.1 selector barely helps here (42 vs 47): it grounds term absence only for
single-sentence facts; sixteen of the eighteen records are two sentences, so function-word-only
items were delivered as `undetermined_multi_statement`.

## 4. Remediation: selector policy 0.5.0 (Phase 3)

**Mechanism** (`reference/agentmem_ref/api/context_selection.py`, policy
`evidence-qualified-context-selection/0.5.0`, selector blob `e186d895`). For a lexical-only returned
fact that shares **no** folded content term with the query:

- a single statement is declined (`no_query_term_evidence`, `absence_grounding: single_statement`),
  as in 0.3.0 to 0.4.1;
- **new:** a third-person statement is declined when it names its own subject (proper-noun
  possessive, or the persisted write-time proposition entity) that the query never mentions
  (`absence_grounding: fact_subject_absent`), or when the query names a subject by proper-noun
  possessive that the fact never mentions (`absence_grounding: query_subject_absent`);
- a **first-person** statement stays delivered as `undetermined_multi_statement` (uncertain): it is
  about its speaker, whom any question from the caller may concern in other words;
- a multi-statement third-person fact where **neither** side grounds a subject stays uncertain
  (nothing grounds the absence).

Why this is generalizable rather than fitted: it uses only the two subject-grounding signals the
selector already relied on (proper-noun possessives, persisted proposition entity), the same bounded
function-word list and morphology fold, and no vocabulary, question identifier or corpus-specific
case. The first-person exemption is the reason the owner's zero-loss gate holds by construction:
every required LongMemEval and LoCoMo item that the rejected 0.2.0 term-absence rule lost was
first-person text (`…/819-evidence-qualified-context/diagnostics/policy-0.2.0/LOSS_ANALYSIS.md`),
and the 0.5.0 decline set is a strict subset of the 0.2.0 decline set restricted to third-person
facts. Section 5 confirms zero loss by re-execution, not by this argument alone.

What it deliberately does **not** do: it does not decline a third-person multi-statement fact that
names no subject (e.g. "The office printer is a Brother HL-L2400D. Its toner is TN830." for a
question about Liora's canoe; the write-time interpreter records the proposition as ambiguous, so
no entity is persisted). Declining those would reproduce the rejected rule for third-person text;
it is listed as an owner option in section 6, not implemented.

**Fail-first tests**: `GroundedAbsenceForThirdPersonStatements` (6 tests) in
`reference/tests/test_819_evidence_qualified_selection.py`: 5 RED at 0.4.1
(`logs/selector-0.5.0-fail-first-RED.log`), all GREEN after. One existing test encoded the 0.3.0
decision (`test_term_absence_is_grounded_only_for_a_single_statement`: an unrelated three-sentence
fact about the moon exhibit delivered as uncertain); it is revised to the 0.5.0 contract with the
revision documented in the test, and the original file and the 0.4.1 selector are preserved in
`step3/`. Schema: `policy_version` const `0.5.0` and the `absence_grounding` decision field
(`schemas/api-context-package.schema.json` and the packaged copy, identical). The owner's product
controls (`test_819_served_context_quality_contract.py`) and independent challenges
(`test_841_…`) pass unchanged: paraphrased predicates and the owner's cello counterexample are still
delivered as uncertain, and unresolved or budget-omitted content still never yields
`no_relevant_evidence`.

**MCP consumer path**: the bridge now reports `selection_policy_version` and, for each declined fact
under `unavailable` (state `omitted_selection`), its `absence_grounding`, `fact_subjects` and
`query_subjects`; the server docstring and README say so. A new real-SDK test
(`test_selectivity_declines_are_visible_with_their_grounding`) drives this through the real server:
same question, `all_returned` delivers both memories, `experimental_selectivity` declines the
other-subject memory with `fact_subject_absent`, its text never reaches the client, the recall is
identical. The probe gained `--selectivity` so both profiles are measured over the same stdio path,
and records `mcp_omitted` per question.

Unchanged: `recall()`, admission, ranking, the `all_returned` profile and its package 0.1.0 (the
owner's byte-identity test passes), write semantics, correction/deletion/restart behaviour, the
default of `experimental_selectivity` (False).

## 5. Regression and before/after (Phase 4)

### 5.1 Development cohort through the real MCP server (`after/`)

| arm | answerable complete | required items | unexpected items | forbidden incidences | mean precision | no-answer empty | p50 / p95 ms |
|---|---|---|---|---|---|---|---|
| MCP default `all_returned` (after; identical keys to before) | 11/11 | 11/11 | 47 | 15 | 0.288 | 0/3 | see log |
| **MCP opt-in selector 0.5.0** | **11/11** | **11/11** | **33** | **12** | **0.336** | 0/3 | 47.7 / 186.6 |
| SQLite FTS5 | 11/11 | 11/11 | 22 | 11 | 0.518 | 1/3 | 0.1 / 0.2 |

Per question (items delivered: default → 0.4.1 → 0.5.0; FTS5; 0.5.0 assessment and declines):

| q | default | 0.4.1 | 0.5.0 delivered | FTS5 | assessment | declines (reason/grounding) |
|---|---|---|---|---|---|---|
| A1 | 5 | 4 | 3 (liora-canoe, liora-bicycle, liora-sibling) | 4 | evidence_delivered | subject_mismatch; no_query_term_evidence/fact_subject_absent |
| A2 | 2 | 2 | 2 (mara-child, mara-parent) | 2 | undetermined | |
| A3 | 2 | 2 | 2 (mara-child, mara-parent) | 2 | undetermined | |
| A4 | 4 | 4 | 4 (office-printer, liora-bicycle, liora-canoe, liora-sibling) | 4 | undetermined | |
| A5 | 5 | 5 | 2 (office-printer, moon-exhibit) | 1 | evidence_delivered | 3 × fact_subject_absent |
| A6 | 5 | 4 | 4 (office-printer, quail-owner, code-editor, moon-exhibit) | 1 | evidence_delivered | single_statement |
| A7 | 3 | 3 | 3 (maya-editor, quail-owner, code-editor) | 1 | evidence_delivered | |
| A8 | 5 | 5 | 5 | 5 | evidence_delivered | |
| A9 | 4 | 4 | 4 | 4 | evidence_delivered | |
| A10 | 5 | 5 | 4 | 4 | evidence_delivered | fact_subject_absent |
| A11 | 3 | 3 | 3 | 2 | evidence_delivered | |
| N1 | 5 | 5 | 4 (code-editor, omar-editor, office-printer, moon-exhibit) | 2 | evidence_delivered | fact_subject_absent |
| N2 | 5 | 3 | 1 (moon-exhibit) | 0 | **undetermined** | 2 × single_statement; 2 × fact_subject_absent |
| N3 | 5 | 4 | 3 (quail-meeting, office-printer, moon-exhibit) | 1 | evidence_delivered | single_statement; fact_subject_absent |

No question lost a required item (`required_hits` 11/11 before and after, per question). The
residual gap to FTS5 is exactly the class the policy leaves uncertain: multi-statement third-person
facts with no grounded subject (`office-printer`, `moon-exhibit`, whose propositions are ambiguous)
and content-word false matches that FTS5 shares or that only its stop list removes ("use", "next",
"code", "Brother", "project … review"). The remaining A2/A3/A4 `undetermined` assessments are honest:
the delivered facts share only the subject with the question.

Latency: the selector adds no measurable median cost (p50 47.6 → 47.7 ms); the p95 moved from 85 to
187 ms in this run (14 samples, process start included; descriptive only).

### 5.2 Required-evidence gate on the #819 regression sets (zero loss required)

Re-executed with the same paired drivers as the #819 qualification (`…/819-evidence-qualified-context/tools/`),
same inputs, `k=50` (LongMemEval), `k=10` (LoCoMo), AMB's per-case `k`, on the working tree at `1943c57f`
with the 0.5.0 selector blob `e186d895`, which is byte-identical to the blob committed at `9456708c`
(`lanes/lanes-run.log` records the blob; the summaries record it as `selector_blob`). Arms: default `all_returned`, `eq` (selector), rejected
lexical rule (post hoc replay), FTS5. Outputs in `lanes/`.

| set | default complete | **eq 0.5.0 complete** | required items default → eq | eq questions losing vs default | delivered items default / eq 0.4.1 / **eq 0.5.0** / FTS5 |
|---|---|---|---|---|---|
| LongMemEval_S session, 500 q | 428/428 | **428/428** | 803 → 803 | **none** | 19,187 / 18,399 / **18,122** / 8,891 |
| LongMemEval_S turn, 500 q | 369/428 | **369/428** | 756 → 756 (of 842) | **none** | 21,400 / 19,319 / **19,203** / 13,819 |
| LoCoMo, 1,540 q | 1278/1531 | **1278/1531** | 1734 → 1734 | **none** | 15,310 / 15,310 / **15,310** / 15,269 |
| LoCoMo adversarial cat. 5, 446 no-answer q | | identical to 0.4.1 | | | 0 declines (all first person) |
| AMB 77 (native scorer) | strict 15 | **strict 16** (+`canonical-name-match-mara`, 0 regressed) | 0 missing-expected changes | **none** | returned 686 / 686 / **678** / 254 |
| 19k synthetic (#825 harness, 14 cases, single-sentence facts) | needed 11/11, strict 0, extras 52 | **needed 11/11**, strict 4, extras 21 (identical to 0.4.1) | 11 → 11 | **none** | FTS5: needed 11/11, strict 1, extras 42 |
| 1k synthetic (#825 harness, 14 cases, single-sentence facts) | needed 11/11, strict 0, extras 52 | **needed 11/11**, strict 4, extras 21 (identical to 0.4.1) | 11 → 11 | **none** | FTS5: needed 11/11, strict 1, extras 42 |

LoCoMo and the adversarial set are first-person dialogue throughout, so 0.5.0 behaves exactly like
0.4.1 there (by design). The LongMemEval gain is small (first-person turns dominate); the gain
concentrates on third-person notes, which is what an agent writes through `memory_remember`.

### 5.3 Suites

| suite | result | log |
|---|---|---|
| selector, owner controls, independent challenges, context package, #691 audit and authorization suites (6 files) | **93 passed** | `logs/selector-0.5.0-GREEN.log` |
| `integrations/agent-memory-mcp/tests` (bridge 12, real SDK 7, quality probe 10, task eval 6) | **35 OK**, no skips | `logs/mcp-suites-final.log` |
| full reference suite at `9456708c` | result recorded in the follow-up evidence commit (`logs/full-suite.log`) | `logs/full-suite.log` |
| Gate 1 workflow driver at committed head `9456708c` (26 checks: save, exact get, find, restart, cross-scope, wrong key, same-key rewrite, bad input, no host config) | **26/26** | `logs/gate1-workflow-rerun-9456708c.log`, transcript `logs/gate1-workflow-9456708c.json` |

## 6. What this does and does not establish; owner decisions

- **Not established**: Gate 2. The product does not yet beat the indexed FTS5 baseline on irrelevant
  context at equal budget (33 vs 22 on the dev cohort; 46 vs 45 post-freeze), and no arm abstains
  on unanswerable questions beyond what empty retrieval gives.
- **Root cause is in candidate admission, not the consumer**: the lexical route admits
  function-word-only candidates. Fixing it there (a stop list or content-term requirement in the
  substrate search) changes `recall()` and the frozen v7 lanes, and was out of scope here; the
  consumer-side selector can only decline what it can ground.
- **Owner option A (not implemented)**: ground term absence for every third-person statement
  regardless of subject (first-person stays uncertain). By the 0.2.0 loss analysis this is also
  zero-loss on LongMemEval/LoCoMo (all lost items were first person) and would recover 0.2.0's AMB
  strict gain (30/77), but it is the rejected rule minus a carve-out; it needs the owner's call and a
  full re-run.
- **Owner option B (not implemented)**: promote the qualified profile to the `memory_find` default.
  For: zero loss on every set, 30-45% less irrelevant context on agent-style notes, declines are
  visible with reasons, `experimental_selectivity=false` would restore `all_returned`. Against: the
  task-level probe (section 7) shows one question (T16) where the reader answered correctly from the
  default evidence and wrongly from the leaner evidence, which is the brief's own warning that a
  shorter context alone is not success; the owner's README states the selector must be opted into.
- Function words: "use/uses" and "next" count as content terms in the selector's bounded list and
  produce false matches (A6, A7, A8); FTS5's stop list removes "use". Adding them is a vocabulary
  change the brief forbids making for the visible cases; flagged, not done.
- Third-person notes about the caller: an agent often writes "The owner writes Python in Neovim"
  rather than "I …". Such a note names "owner" as its subject (persisted proposition entity), so a
  question that shares no content term with it ("Which editor do I use?") is now declined with
  `fact_subject_absent`, visibly, exactly as FTS5 would never retrieve it. Treating "owner"/"user"
  as speaker markers would be a vocabulary change and is left to the owner.
- Stale information: T16 shows both the current and the former heating fuel delivered; nothing in
  the write path lets an agent retire the former fact (no `correct`/`forget` in the bridge, as
  Gate 1 recorded).

## 7. Task-level evaluation (Phase 5)

`integrations/agent-memory-mcp/task_eval.py` drives the real stdio server, calls `memory_find` per
question, hands **only the delivered evidence text** to a reader, and scores the reader's answer
against gold joined afterwards; the same reader runs over the FTS5 arm's texts at equal `k`.
Readers: `extractive` (deterministic plumbing reader) and `onnx-squad` (DistilBERT fine-tuned on
SQuAD 1.1, pinned quantized ONNX export `Xenova/distilbert-base-cased-distilled-squad`
@`bdbb0a5e`, CPU, no paid inference; file digests in `phase5/reader-model-SHA256SUMS.txt`). The
reader abstains only on empty evidence or span confidence below a threshold declared before the
first run (0.20) and never tuned. Its measurement tests: `tests/test_task_eval.py` (6 OK).

Cohort `phase5/task_cases_postfreeze.json`: 22 records, 16 answerable + 6 unanswerable questions,
written **after** the 0.5.0 selector was frozen, disjoint from the dev cohort in entities, memories
and questions. **It is not a sealed holdout**: its author also wrote the implementation. A legitimate
sealed evaluation needs a cohort author who has not seen `context_selection.py`; the harness and
schema are ready for that (gold is joined after answering; the reader never sees keys or gold).

| reader | arm | answerable correct / abstained / wrong (of 16) | unanswerable abstained / false answer (of 6) | required evidence complete | unexpected items | delivered chars |
|---|---|---|---|---|---|---|
| onnx-squad | MCP default | **15** / 0 / 1 | 0 / 6 | 16/16 | 83 | 8,241 |
| onnx-squad | MCP opt-in 0.5.0 | 14 / 0 / 2 | 0 / 6 | 16/16 | 46 | 5,261 |
| onnx-squad | FTS5 | 14 / 0 / 2 | 0 / 6 | 16/16 | 45 | 5,098 |
| extractive | MCP default | 11 / 0 / 5 | 0 / 6 | 16/16 | 83 | 8,241 |
| extractive | MCP opt-in 0.5.0 | 11 / 0 / 5 | 0 / 6 | 16/16 | 46 | 5,261 |
| extractive | FTS5 | 9 / 0 / 7 | 0 / 6 | 16/16 | 45 | 5,098 |

Reading: with full evidence delivered in every arm, answer correctness is a reader property. The
one divergence (T16, "current heating fuel, not the former one") is answered "propane" from the
default evidence and "paraffin" from the leaner opt-in and FTS5 evidence, with both facts present in
all three; the extractive reader shows MCP's ranking (required fact first) helps it over FTS5's.
Abstention: a SQuAD 1.1 reader cannot say "no answer", so the only abstention path is empty
evidence; no arm produced empty evidence on U1-U6, though the opt-in profile labelled U4/U5
`undetermined` (only subject-sharing facts delivered) and declined the wrong-subject facts
("Rohan's dog" no longer receives Tamsin's dog). An agent that reads `selection_assessment` has a
signal; a bare reader does not.

## 8. Files

- `before/`: Phase 1 raw probe output at `1943c57f` (default profile) and the 0.4.1 opt-in
  diagnostic; `after/`: both profiles at the remediated tree.
- `diagnostics/`: admitted-set dump with routes and scores for every dev question, and the script.
- `step3/`: the original test file and the 0.4.1 selector as superseded evidence.
- `lanes/`: regression-set summaries and rows (gzipped) for the 0.5.0 selector.
- `phase5/`: post-freeze cohort, reader digests, `results/` (four task-eval reports and logs).
- `logs/`: every test and probe execution named above.
