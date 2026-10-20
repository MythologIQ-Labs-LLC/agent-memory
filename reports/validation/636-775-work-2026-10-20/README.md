# Work integration validation: #636, #775 and #830

**Development validation, not independent runtime qualification.** No runtime/API/schema, accepted ADR, frozen benchmark, accepted score, baseline record or register changed. The Architecture Index still routes claims; this report records execution, not architecture ownership. No merge, new PR, hosted Actions dispatch, paid inference, or private Jarvis access.

## Exact identities and decisions

| Surface | Reviewed original head | Published repair | Decision |
|---|---|---|---|
| #636 `evaluation/636-observed-route-attribution-no-ci` | `a3756edb9a8e60f877381a81c396ce36678d20de` | `e12a819060a2570e6c44d6da77235d4ba4e13234` | GO for evaluation review; heterogeneous product qualification remains BLOCKED |
| #775 `evaluation/775-independent-relevance-challenge-no-ci` | `9bb09b474298531d93e137a6f10910a80c9d4816` | `18dd0a200564f3e0e7144abcd457bfc5d9f6576f` | GO for evaluation review; production selection remains BLOCKED |
| PR #830 `docs/819-precision-experiment-governance-no-ci` | `17dc8cc3b36dd1b0b3418ccb23cd8f5856c4e508` | `ca6e7d80209150a2fd1093b418344e59e18a6a36` | GO for normal review readiness, not a merge ruling |
| main | `ae2fcac0427da8df159bc82972b1e9b20eb61845` | unchanged | inherited baseline-equivalence test CHANGES REQUIRED at its owner |

Remote heads were verified, not assumed. Each branch was checked out in a clean worktree. Git Data publication preserves the complete tested tree. Full final discovery ran on local commits `b716388f47eceb5fb21271d71a536884a84f26b4` (#636) and `caaa1d47` (#775); their complete trees equal the respective published repairs (`413c447ced2f6e8f9a0e6ad2ba547bbdc71ff8ba`, `d23432022c58cdb5e742dfa8d6df3c5db40363d8`). Focused tests and the paired profile run were repeated on clean published SHA worktrees.

## Defects and repairs

1. Both #636 evaluators and the #775 public-content probe checked receipt existence but not an `admit` decision. Contradictory/missing decisions could be scored as admitted. New negative tests failed first: six subtest failures on #636 and four on #775. Both now refuse any returned receipt without `outcome: admit`. #775 validates the entire returned set before any supplied content lookup, including when a later reference has an invalid receipt. Positive synthetic receipts now faithfully include the public outcome field.
2. The first new profile runner incorrectly demanded identical fresh admission decision IDs/clocks across repeated recalls. The first attempt failed before comparative results. Inspection identified `decision_id` and `evaluated_at` as expected fresh audit metadata. The repaired runner compares every other public field, preserves all original repeat receipts, and leaves the workload, labels, budget and configuration unchanged. No score-based tuning occurred.
3. #830's ASCII intent drawing was replaced by a compact representation/purpose table. Its intent warning, qualification limits and canonical owner links are retained. The PR still changes only five existing documentation files.

These are evaluator consistency checks, not authentication of arbitrary caller-owned dictionaries. A fabricated `admit` string is not independently verified runtime authority. Integration tests use actual public facade receipts; evaluators never fetch private content or touch the substrate.

## Actual tests

| Run | Result |
|---|---|
| Original #636 targeted suite | 22 passed |
| Original #775 targeted suite | 27 passed |
| Repaired focused suites | 24 and 29 passed |
| Exact published #636, including mandatory real pinned ONNX provider, package/API/scope/governance, shared evidence and vector correction | 79 passed |
| Exact published #775, including package/API/scope/governance | 69 passed |
| Final #636 full reference discovery | 2,597 run: 2,580 passed, 16 skipped, 1 inherited failure |
| Final #775 full reference discovery | 2,602 run: 2,580 passed, 21 skipped, 1 inherited failure |
| Exact #830 applicable reference tests | 32 passed |
| Exact #830 architecture catalog tests | 20 passed |
| Markdown links | changed 5 files and all 180 top-level docs/Markdown files passed |
| Architecture catalog | 78 numbered docs, one shelf each |
| Doctrine boundaries and whitespace | passed |
| Installed README public example | executed: one returned reference, history and posture stages correct |

The inherited failure is `BenchmarkIntegrationContractTests.test_evaluation_only_change_keeps_runtime_baseline_equivalence`. It expects equivalence to frozen `e98e6e7b776aa2dd680e84f3ed4773ad2afa4ae1`, while main already differs in `reference/agentmem_ref/runtime/runtime_composition.py`. The identical failure was reproduced on unchanged main. It was not skipped, rewritten, or repaired by mutating accepted baseline evidence. Final full logs are included. The earlier exact trees have no production source changes relative to main; evaluation modules are the declared non-runtime exception. The first pytest invocation could not start because pytest was absent; supported unittest discovery was used instead.

## Real supported comparison, frozen before results

The committed `reference/fixtures/evaluation/636-supported-profiles-v1.json` and `reference/run_636_supported_profiles.py` define eight author-visible cases, seven facts, k=3, three identical-input repetitions, seed 636 randomized arm order, common scope/permissions and the existing pinned local model. Run identity records exact source, driver/workload hashes and model configuration. The fixture was committed before first execution. The audit-normalization correction above followed a failed attempt, is fully disclosed, and changed no retrieval or scoring criterion.

The arms are **default composed recall with semantic off** and **the same composed recall with semantic required**. This is a real supported vector-route off/on comparison, not a fabricated-vector experiment, a pure lexical/vector comparison, or a controlled disabling of every other backend. The required mode verified the pinned model; failure would stop rather than silently fall back. Source fixture ID: `636-supported-semantic-toggle-development-v1`, SHA-256 `7c20825699e08c822c501fc6cab2ee75fd63ca2d3b5d001a093828e4228ca0c7`.

| Axis | Off | Required |
|---|---:|---:|
| Required evidence returned | 6/7 | 6/7 |
| Explicitly forbidden evidence | 1 | 1 |
| Unlabelled returned references | 10 | 10 |
| Evidence-complete answerable cases with no explicit forbidden item | 5/7 | 5/7 |
| Empty no-answer context | 0/1 | 0/1 |
| Delivered characters, all 8 cases | 606 | 606 |
| Bytes on disk after close | 414,042 | 450,906 |
| Open, one sample (ms) | 35.602 | 414.310 |
| Seven-write ingestion, one sample (ms) | 33.033 | 44.708 |

**No measured returned-evidence benefit on this diagnostic.** All eight returned lists are identical. Semantic provenance is present on several returned items, but that does not prove marginal retrieval value. Case 04 misses required evidence in both arms. Case 08 serves an explicitly requested identity that the task rubric marks forbidden; admission/exact identity is not task relevance. Unlabelled memories are not called false positives or added to a precision denominator. No independent downstream strict task scorer, QA generation or abstention judge ran. No currentness/historical score is manufactured.

Both arms pass real deletion, recall reopen, and foreign-domain-empty controls; the derived semantic store is explicitly verified. Existing shared-evidence-neighbor and vector-correction tests pass. Latency, cold first call, two warm samples per case, CPU, ingestion, storage and character/token estimates are reported separately in raw results. Timings overlap other local tests, share one process and one seed-fixed arm order (required first), and are descriptive only. No speed superiority or scalable cost claim is justified. Model files are not republished.

## Reachability and provenance review

| Capability | Current public reachability and limits |
|---|---|
| Exact logical identity | `recall(logical_memory_refs=...)`; resolves a governed target identity, not natural-language subject equivalence |
| Lexical | Default SQLite candidate route; no independent public disable switch |
| Shared evidence neighbors | Default planner expands explicit identity seeds through shared retained evidence references; not semantic relationship proof; no independent public disable switch |
| Semantic/vector | `open(semantic_retrieval="off" or "required")`; real pinned optional provider, derived store and full admission; subordinate ranking remains unchanged |
| Typed graph | Persistence and bounded traversal modules exist; the default public planner in `runtime/runtime_composition.py` has no typed-graph route/configuration. Shadow controller planning does not execute a replacement planner. A graph-only public arm is unsupported here. |

Four distinct relationship postures must survive the next implementation:

- Governed canonical target identity and explicit lifecycle links have durable runtime records. They do not automatically authenticate textual entity identities or arbitrary semantic relations.
- Derived `write_semantics`/typed-link and shared-evidence signals are traceable bounded evidence; their basis, cited refs and guards must remain visible. They are not truth/permission.
- `typed_proposition.basis=caller_declared`, arbitrary `TypedRelation.relation_type`/attributes, and #775 `identity_binding_checked`/subject/property/relation annotations are caller claims. An extracted proposition records extractor provenance but still is not canonical verification.
- Missing, contradictory, stale or unverified bindings remain unknown/contested. The #775 challenge never authorizes withholding. A correct missing relation cannot be inferred negative just because metadata is absent.

No closed natural subject/causal ontology or authenticated relationship evidence source was found in the supported facade. That gap belongs with #688 and #775, not a new parallel framework. #673 owns fusion; #691 owns consumer packages. This work changes none of them or the rejected #691 candidate. The #635/#636 runtime-expansion gate is not declared satisfied.

## Cold-start documentation review

The reviewer independently followed the README and primary sources, rather than treating validators as semantic approval.

| Cold-start question | Answer and source |
|---|---|
| Product objective and heterogeneous scope? | Opening paragraph and intent section route to `docs/CONCEPT.md` and #636. The table is explicitly direction, not shipped capability. |
| Why combine forms? | Different task/lifecycle needs; each additional representation must demonstrate value. No presumed universal hybrid superiority. |
| Which doctrine/consequences are permitted? | Theory links route to Architecture Index, individual ADR status, PAMA and docs/13; contribution/governance text preserves proposal/authority separation. |
| What runs today? | Present-capability table, Runtime section, docs/44 and docs/43 identify Python public facade and qualified single-host SQLite. The installed example actually ran. |
| What is absent or experimental? | Parallel maturity column names distributed, Postgres/Markdown, graph reasoning and cross-store composition limits; #691 rejection and #775 evaluation-only status are explicit. |
| What evidence supports maturity? | Dashboard/evidence links and docs/43; #825 described as executed but unqualified development comparison. No copied accepted score table or new authority owner. |
| What changes next, and where? | Backlog, live #819/#775/#691/#636 and #410; Architecture Index remains filing/ownership rule. |

All five Architecture Index cold-start questions and all six handoff README questions are covered. This is an independent documentation/source review of the original PR author's work, not a blinded evaluation of the new code written in this integration session. No accepted ADR was altered.

## Commands and next action

```bash
python -m pip install -r reference/requirements.txt
python -m pip install -r reference/requirements-semantic.txt
PYTHONPATH=reference python -m agentmem_ref.runtime.representation_onnx fetch --dir /tmp/636-pinned-model
PYTHONPATH=reference python -m unittest -v tests.test_636_route_attribution tests.test_636_paired_recall tests.test_636_route_attribution_integration
PYTHONPATH=reference python -m unittest -v tests.test_775_subject_relevance_challenge tests.test_775_relevance_tradeoffs tests.test_775_public_recall_probe tests.test_775_public_recall_integration
AGENT_MEMORY_REPRESENTATION_DIR=/tmp/636-pinned-model AGENT_MEMORY_REQUIRE_REPRESENTATION=1 PYTHONPATH=reference python -m unittest discover -s reference/tests -q
PYTHONPATH=reference python reference/run_636_supported_profiles.py --model-dir /tmp/636-pinned-model --output /tmp/636-published-supported-results.json
python scripts/validate_markdown_links.py README.md GOVERNANCE.md CONTRIBUTING.md docs/README.md docs/BACKLOG.md
python scripts/validate_architecture_index.py
python scripts/validate_doctrine_boundaries.py
python -m unittest discover -s tests -p 'test_architecture_index_validator.py' -v
git diff origin/main...HEAD --check
```

Exact focused module lists are the first lines of the verbose logs; full discover logs preserve counts and failure traces. The initial dependency installs and model fetch succeeded. The model is used locally without paid inference. The raw JSON has source/runtime identity and actual public receipts, not only summarized assertions.

Next: independent code/evaluator review of these repaired branches, then a #636 experiment with independently frozen task labels and operational controls where supported. Pure single-route experiments require a separately reviewed evaluation seam or supported runtime prerequisite; do not patch internal planners and call it public qualification. Under #775/#688, establish how legitimate subject/relation bindings are evidenced before proposing any production exclusion rule. Keep #819/#691 rejected-selector evidence intact. #410 has no new release-acceptance ruling from this work. PR #830 can advance to normal review, not automatic merge.
