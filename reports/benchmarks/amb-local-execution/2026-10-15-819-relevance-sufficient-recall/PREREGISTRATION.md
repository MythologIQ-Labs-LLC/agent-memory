# #819 preregistration: relevance-sufficient recall selection

Written and committed **before** any candidate runtime was executed on AMB, LongMemEval or the
held-out cohort. The baseline (A) had already been executed and traced, so the diagnostic AMB
run is not blind; the held-out cohort below is.

## Diagnosis this responds to (from the baseline trace, `AgentMemory.recall` at 1df28f84)

1. The lexical candidate route admits any fact sharing **any** whitespace token with the query,
   function words included ("what", "how", "my", "the", "about"). Most AMB false positives share
   only function words with the query.
2. Nothing between ranking and the return budget asks whether a ranked candidate carries
   enough evidence to be returned. `returned` is the ranked prefix up to `k`, so a query returns
   `min(k, admitted)` facts however weak the match (several return the configured 20).
3. BM25 over the admitted set counts function-word matches, so a fact matching only "how"/"should"
   can outrank the fact that matches the query's subject.

## Fixed design (no parameter will be changed after the candidate is first executed)

* New post-ranking **return selection** stage in `AgentMemory.recall`, applied after governed
  admission and ranking, before the budget. It never changes candidates, admission, `admitted`,
  or ranking order. It is policy, never authority.
* Informative query terms = the ranking tokenizer's terms minus a fixed closed-class English
  function-word list (determiners, pronouns, auxiliaries/modals, prepositions, conjunctions,
  wh-words, negation/particles, contraction fragments, single characters). No domain words.
* Content relevance of a lexical candidate = Okapi BM25 (k1=1.2, b=0.75) over the same
  admitted-set statistics the ranking stage uses, restricted to informative query terms, with the
  same #583 anti-laundering term masks.
* A candidate is **sufficient** when it is an exact-identity hit, or is surfaced by a non-lexical
  route (relational / semantic: this stage cannot calibrate them and does not withhold them), or
  its content relevance is > 0 and >= **rho = 0.5** x the best content relevance in the recall.
* **Abstention**: if no candidate is sufficient, `returned` is empty.
* `returned` = sufficient candidates in ranked order, then the budget `k`.
* `recall(..., return_policy="ranked_prefix")` reproduces the contract 1.4.0 ranked prefix
  exactly (for rank-depth consumers such as recall@k evaluations).
* The default changes, so the public contract version changes. The v8 security stack has
  adopted 1.7.0 and 1.8.0 on unmerged branches; this candidate uses **1.9.0** so the numbers
  cannot collide, and must be renumbered/reconciled at integration.

rho = 0.5 is an a-priori round value ("at least half the best match's evidence"); it was not
searched. A sensitivity table may be reported as a diagnostic but will not be used to pick rho.

## Evaluation plan

* **A** (baseline): AMB native scorer, frozen AMB `03c1d0f`, Agent Memory `1df28f84`
  (runtime-identical to the PR #818 revision `7c06468`), query-only bridge. Reproduced locally
  with 0 case differences against the PR #818 evidence file.
* **B** (structured filter): not run. The bridge declares `supports_filters = False`; AMB's
  `retrieval_filter` is built from tags an extraction LLM writes at ingest (`name:*`,
  `state:*`). Agent Memory has no neutral tag store to evaluate it against, so B would
  require new bridge capability equally furnished to peers; recorded as not supported.
* **C** (candidate): same AMB revision, same bridge blob, same budget, candidate runtime.
* Paired per-case deltas (fixed/broken), per-category pass counts, precision, recall.
* LongMemEval-S retrieval (`reference/run_longmemeval.py`) at baseline and candidate, plus the
  candidate with `return_policy="ranked_prefix"`, which must equal baseline exactly.
* Held-out: a cohort authored by a separate agent that was instructed not to read this
  repository's code or fixtures; its sha256 is recorded in `HELDOUT-SEAL.md` before it is
  first read or executed. Scored with the unmodified AMB PrecisionMemBench scorer through
  `PRECISIONMEMBENCH_DATA_PATH`, A vs C.
* Correctness/safety: full `reference/tests` unittest suite plus focused currentness,
  correction, forgetting, isolation and contract tests.

## Acceptance (stated in advance)

C must improve AMB strict case success and mean precision over A; mean recall must not fall
by more than 0.10; no isolation/forgetting/correction test may fail; `ranked_prefix` must
reproduce A's LongMemEval ranking exactly. The held-out result is reported whatever it is.
