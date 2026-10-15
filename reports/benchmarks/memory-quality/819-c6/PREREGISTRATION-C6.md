# #819 C6 preregistration: governed discovery reachability (rank-bounded semantic proposals)

This file is committed with `DIAGNOSIS.md`, before any C6 runtime change.

## Baseline and workspace

| Item | Value |
|---|---|
| Base | C4 `bc2be6319a3eda96731fdb235f4feba882bcb9be`, via its evidence head `9942a8a6` (runtime identical) |
| Comparators (immutable) | A `7c06468a` (runtime identical to `1df28f84`); C4 `bc2be631` (C1–C5 unchanged) |
| Branch | `claude/eager-dirac-bftkfg-819-c6` |
| Not touched | #805, #815, #816 `e13d8c58`, #821, C1–C5, evaluator branches, sealed cohorts and competitor runs |
| Defaults | `ranked_prefix` / `relevance_sufficient` defaults are unchanged. The semantic route stays off by default, so C6 is opt-in through `semantic_retrieval`. |

## Hypothesis (one mechanism, at the discovery stage)

**H.** Replace the optional semantic route's *proposal policy* with a rank-bounded one. That recovers low-overlap evidence that is never discovered or is withheld, and it does so with fewer irrelevant returns than the current route. Selection and admission are unchanged.

The current proposal policy proposes every in-scope memory with cosine > 0.30, up to 16, and C4 selection treats each proposal as sufficient (`non_lexical_route_evidence`).

**C6 proposal policy.** For each recall:
1. Rank the domain-eligible memories by cosine to the query. This uses the existing O(N) scan, derived vector cache and `eligible` prefilter.

   In current-state recalls the pool is also restricted to memories that current-state admission would not refuse on identity (`adapter.discovery_admissible`: tenant, tombstone, derived from a forgotten source, event-invalid or superseded, disputed, domain). Otherwise a forgotten or superseded memory could take one of the K slots, be refused, and push needed evidence out. Historical and as-of recalls keep the domain-eligible pool, so superseded evidence stays reachable where admission allows it.
2. Let `best` be the top cosine. If `best < τ_min`, propose **nothing**. A query with no strong semantic anchor gets no semantic candidates.
3. Otherwise propose the top **K** memories whose cosine is ≥ `best − Δ`.
   - K = `K_single` for single-answer questions.
   - K = `K_set` when the query reads as aggregate, relational or plural. This uses C4's `interpret_query` and the closed-grammar `plural_answer` reading, which is ported unchanged from C5 after that branch's review fixes.
4. Proposals cross governed admission exactly as before (tenant, scope, tombstones, currentness, privacy). C4 selection is unchanged.

Similarity only *proposes*. Admission authorises, and the bound limits how many proposals can reach the caller.

**What does not change:**
- lexical discovery;
- the relational and identity routes;
- admission;
- ranking;
- selection;
- `ranked_prefix` with the semantic route off.

**Expected observable change**, measured on the development data below, against C4 with the semantic route on:
- recall stays the same or rises;
- extra returns fall;
- strict passes rise.

Against C4 default (semantic route off): needed-memory recall rises substantially.

## Development data (self-authored; never reported as held-out evidence)

| Set | Contents |
|---|---|
| `dev/diag-scenarios.json` (C6 diagnosis) | 7 scenarios, 30 queries, 32 needed memories, about 30 memories per store, with paraphrase, aggregate, distractor, stuffing, abstention, governance and ordinary queries |
| `dev/c5-dev-scenarios.json` | The C5 calibration set, copied byte-identically from `claude/eager-dirac-bftkfg-819-c5`: 8 scenarios, 48 queries |
| **Union** | 78 queries |

Negative controls are part of both sets:
- no-answer queries;
- topically similar non-answers;
- keyword stuffing;
- an injected "SYSTEM" note;
- forgotten, other-scope and corrected memories.

## Fail-first tests (`reference/tests/test_c6_semantic_discovery.py`)

The tests use a deterministic offline representation with chosen cosines.

**Each of these must fail on C4 with the semantic route on and pass on C6:**
1. A top-ranked memory with cosine below 0.30 is discovered and returned.
2. With a weak best match, nothing semantic is proposed, so an off-topic query abstains.
3. Neighbours beyond `best − Δ` are not proposed.
4. A single-answer question proposes at most `K_single`, and a plural question up to `K_set`.

**These must hold on both heads:**
- forgotten, other-scope and superseded memories are never proposed into the result, however similar;
- an injected or stuffed memory gains nothing beyond its rank;
- a provider failure or unavailable inference leaves lexical recall working (`auto` mode) or refuses cleanly at open (`required`);
- with the semantic route off, returns are identical to C4's.

## Calibration (development union only)

**Grid:**
- `K_single` ∈ {1, 2, 3};
- `K_set` ∈ {2, 3, 4, 6};
- `Δ` ∈ {0.05, 0.10, 0.15, 0.20};
- `τ_min` ∈ {0.30, 0.35, 0.40, 0.45}.

That gives 192 points.

**Objective:** maximise dev strict pass. Ties go to higher needed-memory recall, then fewer extras, then the more conservative point (smaller K, larger `τ_min`, smaller `Δ`).

**Comparisons**, each run once per configuration on the union:
- A;
- C4 default;
- C4 with the semantic route on;
- C6 with the semantic route on, at the chosen point;
- C6 default, which must equal C4.

## Engineering gate (all required; measured on the development union at the chosen point)

- **G1.** Needed-memory recall ≥ C4 default recall + 0.20 (absolute).
- **G2.** Strict ≥ C4-semantic-on strict + 3.
- **G3.** Extra returned memories ≤ 0.75 × C4-semantic-on extras.
- **G4.** The number of no-answer queries that return anything ≤ C4-semantic-on's.
- **G5.** Zero safety violations: forgotten or other-scope returned.
- **G6.** With the semantic route off, returned lists are identical to C4's on every development query.
- **G7.** Recall p50 latency ≤ C4-semantic-on p50 + 10 ms, on a 200-memory store with the same probe as C5 (`c5-latency.py`).

**Stop condition.**
- If no grid point meets G1–G4, C6 stops and a negative-result record is published. No threshold is invented after seeing results.
- G5–G7 failures are fixed or the candidate is rejected.

## Independent review and qualification

- **Review.** A separate adversarial reviewer must challenge the candidate before any freeze. It checks discovery gain, improper accessibility, manipulation by memory text, recall bought with irrelevant results, generalisation beyond the dev data, cost, and evaluator exploitation. Blocking findings are fixed and the affected tests re-run.
- **Freeze, if the gate is met.** Freeze an immutable SHA and record the configuration: `semantic_retrieval="required"`, the pinned model `multi-qa-MiniLM-L6-cos-v1-b207367`, and `onnxruntime`/`tokenizers`/`numpy`.
- **Handoff.** The independent evaluator receives it.
- **Sealed v4 cohort.** It stays unopened by engineering. Its use is the evaluator's decision.
- **Acceptance.** Development results confer no acceptance.

## Known limits (stated in advance)

- Bi-encoder similarity does not establish answerability. Topically near non-answers can still be proposed; the bound limits how many.
- Aggregate members far from the question in embedding space stay unreachable, as do multi-hop bridges and newer-first ordering.
- English-only grammar for query shape.
- The gain needs the optional local model.
