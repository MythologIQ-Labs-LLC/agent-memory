# #819 C6 frozen candidate

**Status.** C6 is implemented, tested, independently reviewed and frozen, in that order. It is not integrated or released, and it has not been independently evaluated. Development results confer no acceptance.

## Identity

| Item | Value |
|---|---|
| Frozen commit | `171e67db041434e1144dd83a73423af6d4c267e1` |
| Tree (whole commit) | `6986b8f11c0486f05f4997b9b448e6cba8753b4a` |
| `reference/` tree | `d587e3e64f07573da7759902cebd8e88bd4bd9dd` (runtime identical to `fab09130`) |
| Branch | `claude/eager-dirac-bftkfg-819-c6`, pushed, no PR |
| Base | C4 `bc2be631` via its evidence head `9942a8a6` (runtime identical) |
| Lineage | `3d202484` preregistration (before any runtime change), `97154a4b` implementation and calibration, `80c797d0` reviewed head, `fab09130` review fixes, `171e67db` evidence and docs |
| Comparators | A `7c06468a`; C4 `bc2be631` |

## Configuration under test

- **Semantic route:** `AgentMemory.open(..., semantic_retrieval="required")`. The route is optional and **off by default**. With it off, C6 returns exactly C4's lists: 78 of 78 dev queries and 55 of 55 reviewer queries.
- **Return selection:** default, `relevance_sufficient` (policy `2.3.0`, unchanged from C4). The C6 policy applies only here. `ranked_prefix` is C4's route.
- **Proposal policy:** `rank-bounded-semantic-proposals` `1.0.0` with
  - `min_best` = 0.40;
  - `margin` = 0.20;
  - `k_single` = 1;
  - `k_set` = 3;
  - `authority_effect` = none.
- **Pool:** memories that admission would not refuse in the recall's admission mode (`GovernedMemoryAdapter.discovery_refusal`).
- **Representation (pinned local model, no network, no paid inference):**
  - `sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367`;
  - `onnx-mean-l2-f32/1.0.0`;
  - config digest `sha256:7447705443160d1ae7c1de49902b786bd3f578d06e7125c05dabaed52dd31aee`;
  - 384 dimensions;
  - located through `AGENT_MEMORY_REPRESENTATION_DIR`.
- **Interpreter and libraries:** Python 3.13.16, onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6.

## Gate (preregistered; development union, in-sample)

All seven criteria are met at `fab09130`/`171e67db` with the preregistered constants. Returned lists are identical to the `97154a4b` runs.

| Criterion | C6 | Bound |
|---|---|---|
| G1 needed recall | 0.551 | ≥ 0.482 |
| G2 strict | 40 / 78 | ≥ 33 |
| G3 extras | 23 | ≤ 36.75 |
| G4 no-answer queries returning something | 4 / 14 | ≤ 7 |
| G5 safety violations | 0 | 0 |
| G6 route off equals C4 | identical | identical |
| G7 p50 latency on a 200-memory store | 62.3 / 66.4 ms | ≤ C4+sem (69.3 / 68.1 ms) + 10 ms |

Full figures:
- `CALIBRATION-AND-RESULTS.md`, including errata and the failed preregistered expectation;
- `dev/comparison.json`;
- `PER-CASE.md`, per query, for A, C4, C4+sem and C6.

## What the evidence supports, and what it does not

- **Against C4 default (route off): more reach.** On the reviewer's 55-query set, which calibration never saw:
  - strict 11 → 16;
  - needed recall 0.276 → 0.500;
  - extras 53 → 61.
- **Against C4 with the route on: more precision, less reach.** On the same set:
  - strict 6 → 16;
  - recall 0.655 → 0.500;
  - extras 120 → 61.

  Every strict win over C4+sem is a precision win. C6 reaches no needed memory that C4+sem misses. The preregistered expectation that recall would stay level or rise against C4+sem **failed**.
- **Against A: ranked prefixes return far more extras.** Development: strict 6 → 40, extras 313 → 23. Reviewer set: strict 0 → 16, extras 362 → 61. Needed recall, A against C6: 0.526 against 0.551 on development, and 0.552 against 0.500 on the reviewer set.
- **Aggregates stay weak.** Multi-hop bridging and newer-first ordering are not addressed.

## Security invariants (tests and probes, at the frozen head)

- **Out-of-scope or retired memories never take a slot or reach the caller.** This covers memories that are:
  - forgotten;
  - derived from a forgotten source;
  - superseded or error-corrected;
  - disputed;
  - other-scope;
  - other-tenant.

  It holds in current-state, historical and as-of recall. Tests: `test_c6_semantic_discovery.py` (17 tests). Probes: reviewer H1–H4 and H8 (`review/after-fixes/c6fix-probe-fake.txt`).
- **Refused text never appears in results.** No text from a refused or other-scope memory appears in a result.
- **Proposals still pass full governed admission.** The pool filter only removes, and similarity is never authority.
- **Injected instructions gain nothing beyond their rank.**
- **Deterministic.** Two full runs gave identical lists, and an exact tie resolves stably.
- **Full suite:** 2651 passed, 31 skipped, 1 failed by design (`full-suite-171e67db.log`). The failure is `test_evaluation_only_change_keeps_runtime_baseline_equivalence`: the protected Runtime Baseline surface changed and no successor is declared. Engineering does not modify the register.

## Known limits (review findings 2, 5, 6 and 9; not changed after results)

1. **A memory phrased like the question can take the single slot.** For example, "I keep forgetting who my doctor is." can outrank the answer. Because the margin is relative to the best match, such a memory can also narrow the plural window.
   - Exposure: the writer needs write access to the same scope, and the effect is suppression of the answer, not access.
   - Reviewer's stuffing store: 0 of 6 needed memories returned, the same as C4 default.
2. **The plural reading that chooses K is a closed English grammar.** It misses some list questions ("Which animals live with us?") and flags a few non-lists.
3. **Answers whose best cosine is 0.32–0.40 are not proposed.**
4. **A provider failure at query time raises in `auto` mode.** This was already true before C6.

## Integration dependencies

- **Security stack.** The C lineage predates #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58`. Integration must rebase C6 onto that stack and re-run its security replays.
- **Protected files.** C6 touches protected Runtime Baseline files:
  - `runtime/vector_retrieval.py`;
  - `runtime/adapter.py` (additive `discovery_refusal`);
  - `runtime/runtime_composition.py`;
  - `api/surface.py`;
  - `runtime/return_selection.py` (`plural_answer`).

  A Runtime Baseline successor would have to declare them. None is proposed here.
- **Defaults.** The `ranked_prefix` default and the semantic route's default (off) are unchanged.

## Independent evaluation requested

- **Evaluator:** fresh independent evaluation of `171e67db` against A `7c06468a` and C4 `bc2be631`, with the configuration above.
- **Sealed v4 cohort:** engineering has not opened it. Its use is the evaluator's decision.
- **Suggested probes:**
  - slot capture by question-shaped memories;
  - list questions the plural reading misses;
  - historical and as-of recall with the route on;
  - recall at fixed precision against C4 with the semantic route.
