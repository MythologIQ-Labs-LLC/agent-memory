# #819 C10: answerability-gated semantic proposals (preregistration)

**Status:** preregistered before any runtime change. Base is C4 `bc2be6319a3eda96731fdb235f4feba882bcb9be`. The comparator is C4+sem, i.e. C4 with `semantic_retrieval="required"`.

**Lane:** a discovery and proposal change. Admission, ranking, return selection and governance are untouched. This lane does not touch the e6 evaluator, the lane-5 typed-replacement qualification, or any frozen candidate branch.

## 1. Problem being addressed

C9-S showed that every rule over dense cosine, dense rank, relative cosine and topical overlap trades needed evidence for precision. On the seven development sets, no rule in that family Pareto-improves C4+sem (`5bca7ff7`, `REFUTATION-C9S.md`).

In C4, every semantic-route hit is sufficient for return. A hit is any fact with cosine > 0.30 among the dense top 16; its selection basis is `non_lexical_route_evidence`. That rule produces most of C4+sem's 558 simulated extras.

## 2. Feasibility check (offline, before implementation)

**Data and method**
- `feasibility/` holds the tools and the evidence.
- The data is the same seven development sets as C9-S. All fixtures are byte-identical (`evidence/fixtures.sha256`): 298 queries, 384 needed memories and 9,587 query/memory pairs.
- No e4, e5 or e6 data was used, and no hidden gold.
- The lexical and selection fields come from this session's C4+sem harness run (`--dump`).
- The simulator is the C9-S simulator. It reproduces C4+sem exactly at strict 56/298 and 241/384 needed memories returned.

**Models scored.** Six local ONNX models were scored at pinned Hugging Face revisions (`evidence/models.sha256`):
- four MS MARCO or BGE rerankers;
- `mxbai-rerank-xsmall`;
- `qnli-electra-base`, trained on "does this sentence answer this question";
- `bge-small` embeddings.

Findings:

1. **Ranking quality is not the gain.** AUC for needed against other memories is 0.906 for MiniLM cosine and 0.906 for QNLI. What QNLI adds is a **query-independent decision boundary**: its logit 0 corresponds to P(answers) = 0.5. Cosine has no such boundary. On the 143 C4+sem misses against their own negatives, QNLI has the best AUC (0.843, against cosine 0.777).
2. **The other rerankers fail at their own boundary.** At logit > 0, the MS MARCO and BGE rerankers reject almost all conversational memories, returning 128 needed memories.
3. **Quantization destroys the signal.** int8 QNLI drops to AUC 0.77 and returns 170 needed memories. The distilled `qnli-distilroberta` model is weaker at its boundary. Only fp32 `qnli-electra-base` is used.
4. **No fitted threshold beats the intrinsic boundary.** A leave-one-set-out fitted threshold gives 95/238/377. The intrinsic logit-0 boundary gives 100/232/335 at K=16. The design uses logit > 0 and fits no threshold.
5. **The hybrid design.** The gate alone loses needed memories that C4's dense top-1 above the floor returns: 48 of them, mostly dense rank 1–3 paraphrases with low QNLI. Keeping C4's top-1 rule unchanged and gating only the rest gives:

   | Rule (simulated) | Strict | Needed | Extras | No-answer abstentions |
   |---|---:|---:|---:|---:|
   | C4+sem | 56 | 241 | 558 | 11/51 |
   | **C10, K=8** | **92** (+48/−12) | **239** | **313** | **11/51** |
   | C10, K=16 | 87 | 245 | 375 | 10/51 |

**Disclosure.** K, the hybrid shape and the model were chosen after inspecting these seven development sets. The independent cohort is the out-of-sample test.

## 3. Mechanism (fixed before implementation)

**Opt-in.** The option is `AgentMemory.open(..., semantic_retrieval="required", semantic_answerability="qnli-electra-base")`. The default `"off"` leaves recall byte-identical to C4.

**Semantic route with the gate on**
- The route takes the dense top **8** domain-eligible facts with **no cosine floor**. This is the same eligibility prefilter as C4, and validity is still left to admission.
- It **proposes** the facts that meet either condition:
  - (a) dense rank 1 with cosine > 0.30, which is exactly C4's best-match rule; or
  - (b) the answerability cross-encoder logit for (query, fact text) is > 0.
- Nothing else changes. Admission, temporal and lifecycle handling, ranking (where the semantic route stays subordinate) and return selection 2.3.0 are untouched.

**Model**
- `cross-encoder/qnli-electra-base` at revision `c7dea87c98b2269a935686c31336e97e837cbbeb`.
- `onnx/model.onnx` sha256 `595b37541289472b7b784ed2af05bcad6000991a2657aeee4f92f68b42ae61d9`. Every file is sha256-pinned.
- fp32, `ORT_ENABLE_BASIC`, CPU, intra-op threads 1 by default, truncation 512.
- The configuration digest binds the files, numerics and library versions, as with the #669 representation provider.
- Fetching is an explicit command. No network I/O happens on open or recall.

**Fail closed.** If the option is on and the model is missing or fails verification, `open` raises. It never silently falls back to ungated C4+sem.

**Authority.** The score is candidate-proposal evidence only, with `authority_effect="none"`. The per-hit answerability logit is recorded in route provenance only when the gate is on.

## 4. Predictions and gates

All gates use the real runtime, through the C9-S stage harness at budget 10, against C4+sem at `bc2be631`. Comparisons are paired per query.

| Gate | Metric | Pass condition |
|---|---|---|
| P1 | strict success, 7 development sets | net ≥ +20 against C4+sem |
| P2 | needed memories returned | ≥ 0.98 × C4+sem (no more than a 2% loss) |
| P3 | extras returned (not need or may) | ≤ 0.75 × C4+sem |
| P4 | no-answer queries returning nothing | ≥ C4+sem |
| P5 | safety | 0 new safety violations, superseded or cross-scope returns; full `reference/tests` suite with no new failures against C4 |
| P6 | LongMemEval-S retrieval (session and turn, recall_all@3/@5/@10) | no significant paired loss (exact McNemar p < 0.05) against C4+sem on a hash-ordered subset; full 500 if cost allows |
| P7 | cost, recorded and bounded | added p50 recall latency ≤ 300 ms (1 thread, development scale); model init ≤ 5 s; added RSS ≤ 700 MiB |

**Secondary measures (reported, not gated)**
- Per-set results and pipeline stages (discovered, admitted, withheld).
- The longitudinal and merged sets.
- p95 latency.
- 4-thread latency.

**Expected outcome on e6.** G5 requires p95 ≤ 1.15× C6+sem, and this cost profile is unlikely to meet it. If it does not, C10 can at most qualify as an **experimental opt-in**, not a default.

**Stop conditions**
- Failing P2, P5 or P6 means STOPPED, with a diagnosis recorded.
- Failing P1 or P3 means STOPPED.
- Failing only P7 means CHANGES REQUIRED, for cost.
- If everything passes, freeze the SHA and hand it to the independent evaluator.

No tuning against e4, e5, e6, the AMB 77-case output or evaluator feedback is allowed.
