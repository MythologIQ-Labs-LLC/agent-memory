# Precision retrieval Work execution, 2026-10-20 UTC

Evidence only. Architecture Index and #771/#554 retain authority. No accepted score, frozen corpus, ADR or baseline register changed.

## Integration decisions

- GO: #828 qualified at 81b6d6cb3d5ca118a81a4fd59b99d354ca7e9302, merged as 1f5f34d49c2baebe74dd11a31aa7022169a569eb. Markdown links (178 files), architecture catalog (78 numbered documents), 20 validator tests, diff whitespace check and five-question primary-source navigation review passed. Detailed answers and commands are in its PR body.
- GO: #829 repaired at 38003674765a16c418b6644ea68a198946cc40b2, merged as ae2fcac0427da8df159bc82972b1e9b20eb61845. Original test exposed a test defect, not a runtime leak: it expected a foreign-project identifier after mandatory prefiltering. The repair verifies foreign identifier/provenance absence, visible superseded refusal, deterministic tracing and defensive container copies. 129 selected tests plus 46 pytest subtests, then 62 additional public facade/governance/ranking/temporal/restart tests passed. The same 129 also passed under unittest. No public API change or selection change.
- CHANGES REQUIRED: experimental lexical content-term candidate 7554d2a010fe483f7e992cc6fe4ed896af8dd9ca. Local only, not merged. Patch is retained here. Fail-first public camera/printer test failed on baseline and passed after correction. 70/71 selected tests passed; the protected temporal monotonicity test failed on five required assertions. Do not promote this candidate or rewrite gold to pass it.
- CHANGES REQUIRED: #825 adoption claim. Real 19k Agent Memory arm executed, but this workload does not demonstrate quality superiority over FTS5. No independent qualification or real Jarvis access.

## Known diagnostic suite, not a holdout

Exact upstream AMB dataset and native scorer at 03c1d0f1d27da63034f0931121c858faba512383; fixture repository tenurehq/precisionmembench at b95d6abb471c0d591c440172283dd74e7af000df (MIT). Original upstream copyright/license remains with its authors. This bundle contains adapted diagnostic outputs, not endorsement.

The replay loads the upstream module without unrelated provider registries, drives real AgentMemory.open/remember/recall, and invokes the unchanged native score_retrieval. It does NOT execute the full AMB CLI or its locked dependency environment. Thus it is diagnostic reproduction, not accepted same-harness lane qualification. Native scorer blob: 47432e9c1bc8119cfc11f00c68620314c6692f9c. No model calls. Default semantic retrieval remains off. Caller budgets, inputs and host are identical; timings include handle reopen and are not native AMB retrieval timings.

| Axis | Baseline 38003674 | Experimental 7554d2a0 |
|---|---:|---:|
| Strict success | 15/77 | 22/77 |
| Mean precision | 0.1806 | 0.3180 |
| Mean recall | 0.9535 | 0.9535 |
| Active success | 4/43 | 9/43 |
| Raw returned fact identities | 686 | 270 |
| Improved/regressed strict cases | reference | 7/0 |

All 77 cases were executed and traced, exceeding the requested 12. Inspect these representative families/cases: happy-stack-repository-layer (type routing), happy-alias-match-kubernetes (alias/related context), alias-kube-resolves (generic-word noise), long-query-rambling-kubernetes (task-context noise), out-of-scope-coin-collecting (no-answer/scope), happy-writing-scope (scope), conflict-scope-disambiguation-redis-writing (scope collision), conflict-scope-disambiguation-redis-code (scope collision), conflict-mongodb-supersedes-sqlalchemy (historical exclusion), questions-pinned-active-only (type routing), multi-hop-supersession-chain-all-excluded (lifecycle), relation-type-expands-participants (relations), negative-guidance-mongoose (counter-signal), score-boundary-weak-match-filtered (abstention).

Baseline: 792 caller-visible candidate hits, all lexical; 62 failed cases, 60 with unexpected beliefs. Common extraneous overlap tokens include the (103), for (90), to (82), and (76), a (53), in (51), how (14). Grammatical overlap is a real source of candidate noise, but not the entire deficit.

Other causes are separate: the AMB bridge stores scope tags/context in its sidecar but passes only content and observed_at into remember, with per-user hashed runtime scope. It does not implement dataset retrieval_filter. Runtime therefore cannot apply dataset domain filters it never receives. Baseline typed scope capability is not a neutral arbitrary tag-filter API. Supersession/open-question metadata is not converted into governed lifecycle operations. Automatic lifecycle mutation inferred from benchmark metadata would require its own authority contract. Hindsight's filter/extraction conditioning is a protocol difference, not proof of architecture superiority. Relation expansion in the upstream scorer is also distinct from native runtime graph traversal.

## Candidate stop line

The generic grammatical-term experiment changes candidate discovery, never admission or authority. It includes no fixture IDs/query patterns/answers or score thresholds in runtime code. Its apparent AMB gain does not qualify it: required temporal assertions regress at A3-two-valid-relevance-decides/current-inferred/current_demoted_as_stale_rate and four F30-memory-text-claims-authority-and-currentness/current-address axes (authority_or_scope_violation_count, coexistence_preservation_rate, current_demoted_as_stale_rate, temporal_self_claim_rank_influence_count). These failures reflect removal of candidates that the frozen conformance observations expect; they are not evidence that authority was granted. Regardless, the protected floor fails. No disjoint independent holdout or full accepted external LongMemEval replay was performed. Those remain NOT RUN, not passed.

## #825 synthetic comparison

Harness source 1d0de74cc2c52c6c19645f99b367205afecbc637. Runtime source at launch e06e9096b5cbb1bcd1bc7412eb4038d60532de6b; runtime code identical to 38003674, whose differences are tests. Corpus hash 44e6ab69482359dcd79d27741f9094a8bccd3d92ff9b9bbe3af53b8b5dd66879. 19,014 fabricated records, 14 cases (13 primary plus temporal diagnostic), budget 5, 3 repetitions, same process/host, indexed then Agent Memory.

| Axis | SQLite FTS5 | Agent Memory |
|---|---:|---:|
| Primary strict | 1/13 | 0/13 |
| Required returned | 11/11 | 11/11 |
| Primary extras | 42 | 52 |
| Forbidden returned | 2 | 2 |
| Correct abstention | 0/2 | 0/2 |
| Ingest/index ms | 75.253 | 123886.646 |
| Retrieval p50 ms | 0.110 | 173.279 |
| Retrieval p95 ms | 4.325 | 3960.213 |

The source/trust metadata is not equivalently wired. Temporal labels do not supply a governed supersession relation. FTS5 is in-memory, while Agent Memory pays durable governance/persistence costs. No RSS/CPU/disk accounting or cold/warm split, independent cohort, corrected-fact/restart comparison, or #771 served-memory scorer qualification. Hence no adoption winner or broad scaling conclusion. The experiment's seven tests passed. Raw outputs include every paired case.

## Commands and next action

Dependency provisioning: python -m pip install -e .; python -m pip install rich tiktoken pytest. Dependencies were not installed under AMB uv.lock, another reason this is diagnostic only.

Replay: python replay.py <workspace-containing-amb-and-precisionmembench> <runtime-checkout> <output-json>. Both upstream checkouts must be at the exact revisions above. No paid inference is used; the native scorer runs after runtime retrieval and never supplies gold to it.

#825: PYTHONPATH=<runtime>/reference timeout 180s python tools/jarvis_scale/experiment.py --size 19000 --seed 825 --budget 5 --repeats 3 --arms indexed,agent-memory --out <output>. Exit 0. PYTHONPATH=reference python -m pytest -q tools/jarvis_scale/test_experiment.py: 7 pass.

Protected candidate command: PYTHONPATH=reference python -m pytest -q reference/tests/test_lexical_query_conditioning.py reference/tests/test_multi_route_recall.py reference/tests/test_developer_facade.py reference/tests/test_domain_eligibility_prefilter.py reference/tests/test_post_admission_ranking_policy.py reference/tests/test_temporal_currentness_gauntlet.py reference/tests/test_governance_gauntlet.py reference/tests/test_substrate_identity_restart.py reference/tests/test_auxiliary_state_restart.py: 1 failed, 70 passed. Baseline counterparts passed.

Next implementation action: separate candidate discovery from explicitly versioned consumer-context selection under docs/44 and #691/#819. Preserve full governed admission/currentness evidence; design a declared relevance-selection policy with fail-first tests for generic-word distractors, required context completeness and abstention. Do not silently change contract 1.4's ranked-prefix semantics. Then freeze code/config and obtain an independent, disjoint evaluation plus accepted LongMemEval replay before merge. Existing #823 independent evidence remains its own lane, not duplicated or accepted here. #818 stays draft under its separate service/security/license gates. No other PR closure is justified by this work.
