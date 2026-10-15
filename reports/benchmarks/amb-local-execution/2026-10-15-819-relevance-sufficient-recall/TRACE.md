# #819 Phase 1: traced AMB failures through `AgentMemory.recall`

Each of the 72 non-blank PrecisionMemBench queries was replayed through the public facade
(`scripts/trace_pmb_recall.py`), with ingestion done exactly as the AMB bridge does it: one
document per belief, `remember(logical_id, text, observed_at=created_at)` under a per-user
scope, and `recall(query, budget=maxBeliefs)` under the same scope. Gold labels are read only to
print them next to the trace and never reach the runtime. Full traces, with every admitted
candidate's rank, BM25, route, temporal tier and (candidate only) return-selection decision:
`traces/trace-A-1df28f84.json` (baseline), `traces/trace-C-4bd38e6c.json` (C1) and `traces/trace-C2-eaf60e4d.json` (C2).

## What the baseline trace shows (all 72 queries)

* **Candidate source.** One route fired for every query: lexical, whitespace tokens, *any*
  overlap. Exact-identity, relational and semantic routes were idle (the bridge passes no
  logical refs, and semantic retrieval is off by default). Median 9 candidates per query, up
  to 33. Most candidates share only function words with the query ("what", "how", "my",
  "the", "about", "should").
* **Admission.** Zero refusals in all 72 queries. Every candidate is current and in scope,
  so governance never narrows the set. Admission is working correctly: it has nothing to
  refuse.
* **Ranking.** BM25 over the admitted set, with function words counted. In 5 of the 72
  queries a fact that shares only function words with the query ranks above every on-topic
  fact (for example, `alias-reactjs-resolves` ranks `b-comm-recommendation` first because
  its text says "Shapes **how** options are presented").
* **Return.** The ranked prefix under `k`. Mean 9.5 facts returned, and 17 of 72 queries
  returned exactly 20. No stage asked whether a ranked fact was relevant enough to return,
  and nothing abstained.
* **Scope, type, lifecycle.** The bridge stores only `content`. AMB passes the belief's
  scope as a tag and the query's scope only inside `retrieval_filter`. The bridge declares
  `supports_filters=False`, so it receives neither. Type (`open_question`, `relation`),
  `superseded_by` and `resolved_at` never reach any provider; they appear only as prose
  ("Historical record only", "Not decided").
* **Temporal.** 791 of 792 admitted-candidate ranking records carry temporal applicability
  `not_evaluated` (no ordering intent was inferred). The one exception is the "these days"
  SQLAlchemy query, read as current: its single candidate has `unknown_temporal_basis`,
  because nothing declared its validity. No candidate was demoted.

## Cause taxonomy

| Code | Cause | Kind | Baseline failures it explains (of 62) |
|---|---|---|---|
| F1 | Lexical route admits on function words, and no relevance-sufficiency or abstention stage exists before the budget | faulty implementation + missing functionality | dominant: 60 of 62 failures report an unexpected belief |
| F2 | No query-time scope: both scopes' beliefs share the same name | external protocol limitation (scope reaches only filter-capable providers) | Scope disambiguation, some Persona and Type cases |
| F3 | Type and lifecycle (open question, resolved, superseded, relation) exist only as prose | absent context | Type routing 0/6, Supersession 0/3, part of Relation |
| F4 | No typo or morphology tolerance (`typsecript`, `mongod`, `moongoose`) | missing functionality | 3-4 Fuzzy/Counter-signal cases |
| F5 | Multi-entity queries with unequal per-entity evidence | faulty implementation (selection is single-threshold) | cap-stress cases (remain failures) |

## Traced failures (20)

| Case | Cause | Classification | Baseline: candidates / returned | Candidate returned | Trace note |
|---|---|---|---|---|---|
| `happy-alias-match-kubernetes` | F1+F5 | faulty implementation | 2 / 2 (top: b-kubernetes-entity 0.72, b-ci-gha-entity 0.67) | ['b-kubernetes-entity', 'b-ci-gha-entity'] | Two candidates: kubernetes (k8s) and GHA (deploy). Both share one informative term; BM25 near-tie (0.720 vs 0.668). Selection cannot separate an alias hit from a content hit without typed name metadata. |
| `alias-kube-resolves` | F1 | faulty implementation | 4 / 4 (top: b-ci-gha-entity 3.37, b-comm-recommendation 1.32, b-protagonist-entity 1.21) | ['b-ci-gha-entity'] | GHA ranks 1 (CI pipeline); two facts matched only on function words ('how', 'our', 'across') outrank kubernetes (kube). |
| `long-query-rambling-kubernetes` | F1 | missing functionality (no sufficiency stage) | 33 / 20 (top: b-kubernetes-entity 14.54, b-auth-open-q 11.69, b-comm-pushback 9.27) | ['b-kubernetes-entity', 'b-auth-open-q', 'b-auth-depends-redis'] | 33 candidates, 20 returned; nearly every fact shares a function word with a 90-word query. |
| `out-of-scope-coin-collecting` | F1 | missing functionality (no abstention) | 18 / 18 (top: b-comm-response-length 2.20, b-auth-depends-redis 1.83, b-dead-letter-queue 1.60) | [] (abstained) | 18 candidates admitted on 'what', 'a', 'to', 'it'; no fact is about coins; nothing abstains. |
| `happy-writing-scope` | F1+F2 | faulty implementation + protocol limitation | 22 / 20 (top: b-comm-recommendation 5.41, b-pov-shift-entity 4.09, b-protagonist-entity 3.85) | ['b-comm-recommendation', 'b-pov-shift-entity', 'b-protagonist-entity', 'b-chapter-structure-q', 'b-redis-writing', 'b-auth-depends-redis'] | 22 candidates; the pinned Mara belief is expected via the harness tier; the rest match 'how', 'should', 'with', 'chapter'. |
| `conflict-scope-disambiguation-redis-code` | F2 | external protocol limitation (no scope at query time) | 14 / 14 (top: b-auth-depends-redis 4.31, b-redis-code 2.42, b-redis-writing 2.42) | ['b-auth-depends-redis', 'b-redis-code', 'b-redis-writing'] | Both Redis beliefs carry alias 'Redis'; the query states no scope and the bridge receives none (supports_filters=False). |
| `conflict-mongodb-supersedes-sqlalchemy` | F3 | absent context (supersession only in text) | 1 / 1 (top: b-sqlalchemy-superseded 0.49) | ['b-sqlalchemy-superseded'] | Single candidate is the superseded belief; supersession is stated in prose ('Historical record only'), not as a canonical correction. |
| `questions-pinned-active-only` | F1+F3 | faulty implementation + absent type | 3 / 3 (top: b-auth-depends-redis 0.88, b-ts-pref 0.70, b-protagonist-entity 0.47) | ['b-auth-depends-redis'] | 'any open questions?' matches 'any'/'open'; open-question type is not visible to the runtime. |
| `alias-reactjs-resolves` | F1 | faulty implementation (ranking) | 5 / 5 (top: b-comm-recommendation 1.45, b-react-entity 1.41, b-chapter-structure-q 1.36) | ['b-react-entity', 'b-chapter-structure-q', 'b-zero-reinforcement-fresh'] | b-comm-recommendation ranks 1 on the function word 'how' (its why_it_matters says 'Shapes how options'), above the ReactJS entity. |
| `filter-resolved-at-excluded` | F3 | absent context (resolution only in text) | 25 / 20 (top: b-hosting-resolved 17.98, b-prose-style-user-edited 3.63, b-error-handling 3.62) | ['b-hosting-resolved'] | The resolved hosting question is the right topic (BM25 17.99) but resolved_at is not an ingested field. |
| `score-boundary-weak-match-filtered` | F1 | missing functionality (no abstention) | 22 / 20 (top: b-chapter-structure-q 2.82, b-zero-reinforcement-fresh 0.04, b-linting-current 0.04) | [] (abstained) | 22 candidates, top matched on 'about'; nothing in memory is about observability. |
| `messy-filler-heavy-extraction` | F1 | faulty implementation (ranking) | 33 / 20 (top: b-redis-code 8.97, b-redis-writing 8.59, b-error-handling 8.22) | ['b-error-handling'] | Two Redis beliefs outrank error-handling on filler words; 20 returned. |
| `fuzzy-two-edit-transposition-blocked` | F4 | missing functionality (typo tolerance) | 0 / 0 (top: ) | [] | 'typsecript' shares no token with any fact; zero candidates. |
| `type-isolation-open-question-not-in-relevant` | F3 | absent context (type not ingested) | 1 / 1 (top: b-auth-open-q 1.32) | ['b-auth-open-q'] | The only candidate is the JWT open question; the harness routes open questions to a separate tier, the runtime cannot know its type. |
| `multi-hop-supersession-chain-all-excluded` | F1+F3 | absent context + missing sufficiency | 24 / 20 (top: b-linting-v0 9.04, b-linting-v1 5.83, b-linting-current 5.00) | ['b-linting-v0', 'b-linting-v1', 'b-linting-current'] | 24 candidates; the TSLint/ESLint superseded beliefs are on-topic but superseded only in prose. |
| `cap-stress-compound-six-entities` | F5 | faulty implementation (multi-aspect selection) | 29 / 20 (top: b-error-handling 11.89, b-ci-gha-entity 11.10, b-react-entity 9.49) | ['b-error-handling', 'b-ci-gha-entity', 'b-react-entity', 'b-kubernetes-entity'] | Six entities with unequal evidence; relative selection keeps the four strongest and drops MongoDB/TypeScript. |
| `counter-signal-jest-surfaces-vitest` | F1 | faulty implementation | 13 / 13 (top: b-narrator-voice 4.68, b-vitest-pref 3.92, b-prose-style-user-edited 2.18) | ['b-narrator-voice', 'b-vitest-pref'] | narrator-voice outranks vitest on 'for', 'this', 'project'. |
| `relation-type-expands-participants` | F1+F3 | absent type | 30 / 20 (top: b-auth-depends-redis 11.92, b-auth-open-q 7.97, b-hosting-resolved 4.93) | ['b-auth-depends-redis', 'b-auth-open-q'] | Relation belief ranks 1; the auth open question also matches 'auth service' strongly and cannot be routed away without type. |
| `subtype-expertise-retrieval` | F2 | external protocol limitation (scope) | 25 / 20 (top: b-react-expertise 14.25, b-react-entity 7.34, b-prose-style-user-edited 2.82) | ['b-react-expertise'] | b-react-expertise (user:universal) carries the alias 'react depth' and is out of the case's code scope. |
| `negative-guidance-mongoose` | F1+F4 | faulty implementation + morphology | 20 / 20 (top: b-authorship-mode 4.29, b-mongo-raw-driver 2.66, b-comm-recommendation 1.48) | ['b-authorship-mode', 'b-mongo-raw-driver'] | authorship-mode ranks 1 on 'suggest'/'my'/'user'; the MongoDB belief's alias is spelled 'moongoose'. |

The candidate column is C1's (`4bd38e6c`). Across all 72 queries C2 returns the same set as C1 except `long-query-rambling-kubernetes`, where ranking consistency also keeps `b-comm-pushback` (the case fails under both). It is the runtime's `returned` for the same trace (before the
harness's local pinned/question tiers). "Abstained" means the runtime admitted candidates and
returned none.
