# #819 C10: answerability-gated semantic proposals (verdict: STOPPED, P2 not met)

**Preregistration:** `PREREGISTRATION-C10.md`, pushed in `528c973e` before any runtime change.
**Candidate**
- Runtime `a2ab582d`.
- Layout registration `4ed9024c`. It changes no behaviour, and every run below used `a2ab582d`.
**Comparator:** C4+sem, i.e. `bc2be631` with `semantic_retrieval="required"`.
**Data:** the seven development sets, sha256-identical to C9-D and C9-S (298 queries, 386 needed memories). No e4, e5 or e6 data and no hidden gold was used.

## 1. Gate results (real runtime, stage harness, budget 10)

| Gate | C4+sem | C10 | Condition | Result |
|---|---:|---:|---|---|
| P1 strict | 56 | **96** (+50/−10, McNemar p=1.6e-7) | net ≥ +20 | pass |
| P2 needed returned | 241 | **228** (+27/−40) | ≥ 237 | **FAIL** |
| P3 extras (not need or may) | 552 | **298** (−46%) | ≤ 414 | pass |
| P4 no-answer queries returning nothing | 11/49 | **13/49** | ≥ 11 | pass |
| P5 safety violations / superseded returned | 2 / 0 | 2 / 0 | no new | pass |
| P5 full `reference/tests` | 4 failed | same 4 failures (see §4) | no new | pass |
| P6 LongMemEval-S (subset of 100, 85 scored) | see §3 | 1 question lost each at session @3/@5/@10 and turn @10, p = 1 | no significant loss | pass (informative) |
| P7 added p50, init, RSS | | +235–246 ms, 1.2 s, +580 MiB | ≤ 300 ms, ≤ 5 s, ≤ 700 MiB | pass |

Further detail:
- All-needed-returned queries: +17/−8 (p=0.11).
- Single-answer strict: 42 → 78. Multi-evidence strict: 3 → 4. No-answer strict: 11 → 14.

Per set (strict / needed / extras):

| Set | C4+sem | C10 |
|---|---|---|
| c6 c5-dev | 22/29/27 | 25/34/28 |
| c6 diag | 8/20/22 | 12/23/19 |
| c6 reviewer gen | 6/36/122 | 12/38/71 |
| c7 dev | 4/50/117 | 12/44/59 |
| c8 dev | 8/50/148 | 12/50/85 |
| c9d longitudinal | 5/28/51 | 14/20/13 |
| c9d merged | 3/28/65 | 9/19/23 |

With the option off, the candidate is **byte-identical to C4+sem** on all 298 rows of every set (`evidence/EQUIVALENCE-gate-off-vs-C4sem.txt`).

## 2. Diagnosis: why P2 failed

`evidence/LOSS-DIAGNOSIS.txt` and `evidence/LOSS-EXAMPLES.txt` cover the 40 needed memories that C4+sem returned and C10 lost.

- **37 of 40 are model rejections.** Each has a QNLI logit ≤ 0 and sits at dense rank 2–8, above cosine 0.30. Only 3 are slot losses: answer-bearing facts pushed out of the dense top 8 by superseded versions, the C9-D mechanism.
- **38 of 40 belong to multi-evidence enumeration questions.** Examples:
  - "Which pets do we have?" against "Biscuit, our beagle, is terrified of thunderstorms." (logit −6.8)
  - "What medications am I on?" against "I take amlodipine 5 mg each morning…" (−5.3)
  - "Whose birthdays are coming up?" against "Mum's birthday is on the 3rd of June." (−7.0)

  QNLI judges whether **one** sentence answers the question. A single member of a set reads as a non-answer.
- **The interpreter cannot route around it.** It flags only 5 of those 38 as `needs_several`.

**Exact mixtures (`evidence/MIXTURES.txt`).** The gate changes only the semantic route, and each query recalls independently over the same store. So a policy that uses C10 for some queries and C4+sem for the rest can be computed exactly from the real rows:

| Policy | Strict | Needed | Extras | Abstain |
|---|---:|---:|---:|---:|
| C4+sem | 56 | 241 | 552 | 11 |
| C10 everywhere | 96 | 228 | 298 | 13 |
| C10 unless the interpreter reads `needs_several` | 92 | 230 | 323 | 13 |
| C10 unless gold says multi-evidence (ORACLE, diagnostic only) | 95 | **251** | 366 | 13 |

The oracle row uses gold and is **not** a candidate. It shows that, given a reliable single-answer versus set-question distinction, the gate would beat C4+sem on every metric: strict +39, needed +10, extras −34%, abstentions +2.

## 3. LongMemEval-S (hash-ordered subset of 100, informative only)

The runs use the runner's hash-ordered subset of 100 questions, 85 of them scored. Both arms run at `a2ab582d` with budget 50, on input sha256 `d6f21ea9…`. The base arm is C4+sem (gate off, byte-identical to C4); the other is the gate (`tools/lme_with_answerability.py`). Source: `evidence/lme/PAIRED.txt`.

| Plane | recall_all@3 | @5 | @10 |
|---|---|---|---|
| session | 0.800 → 0.788 (+0/−1) | 0.906 → 0.894 (+0/−1) | 0.976 → 0.965 (+0/−1) |
| turn | 0.576 → 0.576 (+0/−0) | 0.671 → 0.671 (+0/−0) | 0.800 → 0.788 (+0/−1) |

No difference is significant (every McNemar p = 1). The gate neither helps nor hurts LongMemEval retrieval at this size: lexical evidence dominates there, and the semantic route is subordinate in ranking.

Total recall time:
- session: 296 → 883 s;
- turn: 385 → 540 s.

Session texts run to 512 tokens.

## 4. Cost, safety and reproducibility

**Cost** (`evidence/latency/`): recall-only, one open, each query 3× warm, 1 thread, this 4-vCPU AVX-512 container.

| Set | C4+sem p50 / p95 | C10 p50 / p95 |
|---|---|---|
| c8 dev (171 recalls) | 13.6 / 16.1 ms | 248.5 / 310.7 ms |
| merged longitudinal (90 recalls) | 29.9 / 39.4 ms | 275.5 / 333.9 ms |

- Scorer init: 1.17 s. Peak RSS: 224 → about 805 MiB.
- Four threads score bit-identically on a 320-pair sample at about 2.7× lower cost (`feasibility/evidence/latency-bench.txt`), but that is not claimed in general.
- int8 exports lose the signal (`feasibility/evidence/quantized-and-distilled.txt`).
- e6 gate G5 (p95 ≤ 1.15× C6+sem) would not be met.

**Safety and governance**
- Safety violations and superseded returns are unchanged.
- Tests show that a gated proposal is still refused by admission once its fact is forgotten or superseded, or when it lives in another scope.
- Missing or tampered model files refuse `open`.
- The logit appears in route provenance only when the gate is on, with `authority_effect="none"`.

**Full suite**
- C4: 4 failures. C10 at `4ed9024c`: the same 4 failures (`evidence/full-suite-*.txt`).
- At `a2ab582d` the layout test also failed, because the new module was missing from the layer table; `4ed9024c` repairs that.

**Fail-first:** 12 of 13 new tests fail on C4 and all 13 pass on C10 (`evidence/fail-first.txt`). The one test that passes on C4 asserts that the gate-off arm behaves as C4.

**Reproduction**
1. `pip install -r reference/requirements.txt -r reference/requirements-semantic.txt`
2. `python -m agentmem_ref.runtime.representation_onnx fetch`
3. `python -m agentmem_ref.runtime.answerability_onnx fetch`
4. `tools/harness_c10.py <worktree> <fixture> <out> --sem required --answerability qnli-electra-base --dump`
5. `tools/paired.py base/c4-required cand/c10-gate fx`

Fixtures are rebuilt from the branches listed in `feasibility/evidence/fixtures.sha256`, as in C9-D.

## 5. What this taught us

1. **Similarity is not the missing signal; calibration is.** QNLI and MiniLM cosine have the same AUC (0.906). The gain comes from a query-independent decision boundary that cosine lacks. A gate with no fitted threshold cut extras by 46% and lifted single-answer strict success from 42 to 78.
2. **"Answerability" is a single-answer concept.** A pair classifier rejects individual members of an answer set. This explains the loss, and it matches the evaluator's standing finding that every arm scores 0/16 on multi-evidence aggregation.
3. **The offline simulator over-predicted reach.** It predicted 239 needed returned; the runtime gave 228. It models neither superseded versions occupying dense slots nor selection's handling of facts that both routes surface.

**Verdict: STOPPED.** C10 is not frozen and not handed to the evaluator. The opt-in code stays on this branch as a diagnostic instrument with its default off.

## 6. Next smallest action

Build a **single-answer versus set-question reading** for the query interpreter and evaluate it on its own first. The target is recall on the 38 enumeration queries above ("Which pets do we have?", "What medications am I on?") without misreading single-answer questions. It must be preregistered against a fresh development cohort, not against these 298 queries.

Then apply the C10 gate only to single-answer readings. The oracle mixture bounds the gain at strict +39 / needed +10 / extras −34% against C4+sem.

The cost problem is separate. It needs a smaller answerability model with the same calibrated boundary, such as a distilled QNLI-style pair model, measured against the 0.906 AUC and logit-0 behaviour here, since int8 quantization and `qnli-distilroberta` both failed.
