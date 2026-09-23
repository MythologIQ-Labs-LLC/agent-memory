# System State

## Snapshot Metadata

| Attribute | Value |
|-----------|-------|
| **Last Reconciled** | 2026-09-23 |
| **Evidence Boundary** | `main` `3dc11b4048e64aa7f6bf78103d664bc93d1cd1e7` |
| **Phase** | PRE-RC: usable runtime, production-substrate qualification, developer ergonomics, and release evidence |
| **Reference Package** | `agent-memory-reference` 0.2.0 |
| **Public API Contract** | 1.2.0 |
| **Production-qualified canonical substrates** | 0 |

This document is a current-state projection, not an additional authority source. Canonical architectural decisions live in the ADRs and `docs/META_LEDGER.md`. Current implementation work lives in `docs/BACKLOG.md` and live GitHub issues/PRs.

---

## Current Reality

### Architecture and authority

- ADR-035 is Accepted and the top-level architecture describes Agent Memory as one governed cognitive framework rather than adjacent memory services.
- Public API contract `1.2.0` remains the canonical versioned consumer contract.
- Issue #364 is closed completed. Shared-domain membership mutation and crossing consequences use governed authority paths; the embedding host remains the declared authenticator for `RecallContext.principal_ref` unless a future ADR changes that boundary.
- Candidate retrieval, ranking, graph/provenance relations, estimator confidence, query-anchor heuristics, and provider-native scores do not create recall or mutation authority.

### Reference persistence

The original #363 persistence audit is materially remediated and closed. The reference durability profile now includes:

- explicit state-owner checkpoint contracts instead of restart-runtime private-field scraping;
- substrate-owned identifier progress;
- compare-and-commit generation semantics;
- process locking and a hash-chained commit journal;
- fail-closed torn-write / stale-writer behavior;
- governed checkpoint/profile migration and rollback evidence;
- a public checkpoint-transaction support seam;
- owner restart contracts for projection state, write claims, telemetry, and composed epistemic state;
- atomic composition of auxiliary correctness state into one checkpoint generation.

This proves **reference persistence semantics**, not a production storage choice. Issue #427 owns qualification of the first production-credible canonical substrate.

### Multi-memory composition

- Canonical semantic memory and epistemic belief memory participate in one restart-safe composition path.
- Shared provenance can produce distinct semantic and epistemic consequences without collapsing identity, lifecycle, or authority semantics.
- Epistemic confidence cannot overwrite canonical semantic truth or bypass review.
- Procedural, predictive, Cognitive Mesh, CRG/CodeGenome, and other bounded capabilities remain implemented/evidenced surfaces; RC1 does not require productionizing every declared capability.

### Retrieval

The RC runtime now has three deterministic candidate routes behind one governed admission boundary:

1. lexical candidate retrieval;
2. exact logical-identity retrieval;
3. shared-evidence/provenance-neighbor retrieval when the substrate exposes that optional capability.

An additional **opt-in query-driven planner** now makes relational recall useful when a caller has only a natural-language question rather than a logical memory ID. It:

- starts from tenant-scoped lexical candidates;
- chooses bounded current expansion anchors using content-bearing term overlap, with raw lexical score as a tie-breaker;
- refuses stopword-only anchors and stale/superseded anchors;
- expands through retained provenance neighbors;
- sends the union through the same single governed admission boundary;
- ranks only admitted candidates;
- carries no authority effect.

The content-bearing anchor rule was added after the first LoCoMo-compatible synthetic run showed that raw lexical order could let common words such as `the` / `of` select the wrong relational seed.

### Retrieval measurement

The internal versioned retrieval-quality fixture records:

```text
lexical-only admitted recall: 3 / 7 = 0.428571
composed admitted recall:     7 / 7 = 1.0
admitted precision:           1.0 in both systems
governance failures:          0 in the bounded fixture
```

This remains synthetic internal evidence.

PR #449 also merged the **LoCoMo-compatible retrieval-evidence diagnostic**. The harness:

- consumes an externally supplied dataset path rather than vendoring LoCoMo data;
- pins a compatibility reference to `snap-research/locomo@3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`;
- records the upstream CC BY-NC 4.0 license;
- retains each dialogue turn as a distinct memory with dialogue and shared-session provenance refs;
- compares lexical-only and query-driven retrieval using evidence Recall@K, Precision@K, MRR, all-evidence-hit rate, route contribution, and category aggregates;
- binds dataset hash, runtime configuration, and Agent Memory revision;
- explicitly does **not** claim the official LoCoMo QA score, Jev-Mem answer-quality parity, or comparable paper timing.

The exact #449 merge head passed 1,313 reference tests with 19 intentional skips plus the full repository workflow matrix before merge.

### Checkpoint behavioral conformance

PR #448 harvested the useful unique work from historical branch `implementation/332-checkpoint-behavioral-assessment` into the current harness layer. The evidence-only profile now probes:

- correction precedence;
- anchor preservation;
- scope isolation at a declared recall stage;
- state-conditioned differentiation;
- exact checkpoint/config applicability and TOCTOU refusal.

All assessment output remains `authority_effect = none`. The historical branch is deletion-eligible and should not be merged or revived.

---

## Dependency Manifest

`pyproject.toml` remains the package authority:

| Dependency | Current contract | Status |
|------------|------------------|--------|
| `jsonschema` | `>=4.20,<5` | hard dependency |
| `cryptography` | `>=50,<51` | hard dependency |
| `rfc8785` | `>=0.1,<0.2` | hard dependency |
| `agent-manifest` | `==0.11.2` | optional comparator dependency; 0.12.0 queued for coordinated qualification under #440 |
| `agentrust-trace` | `==0.9.0` | optional comparator dependency; 0.10.0 queued for coordinated qualification under #440 |
| Graphiti / Kuzu path | experimental / non-canonical production choice | current Kuzu-backed adapter is not production-qualified |

Issue #440 owns the next Agent Manifest + TRACE requalification as one version-exact interoperability change. Bare Dependabot PRs #404/#405 are closed and must not be merged independently.

---

## Runtime Boundaries

| Surface | State | Notes |
|---------|-------|-------|
| Python public API | **1.2.0 / active** | schema-backed stages for proposal, approval, commit, recall, history, posture, action authority, and execution evidence |
| Python governed adapter | **active** | post-1.2 authority sweep and #364 work complete |
| Host principal authentication | **external boundary by design** | embedding host authenticates; Agent Memory records/evaluates the supplied principal |
| Restart/checkpoint runtime | **reference-qualified** | strong reference durability semantics; production canonical substrate still unqualified under #427 |
| Multi-memory composition | **implemented RC slice** | semantic + epistemic composition is restart-safe and type-preserving |
| Multi-route recall | **implemented RC slice** | lexical + exact identity + shared-evidence neighbors; one governed admission boundary |
| Query-driven recall | **implemented opt-in RC slice** | content-bearing lexical anchor selection + bounded relational expansion; default application path unchanged |
| LoCoMo evidence diagnostic | **implemented retrieval-only harness** | external dataset input; no official QA/answer score yet |
| Developer ergonomic facade | **missing RC gate** | canonical `AgentMemory.open()/remember()/recall()/...` facade has not landed |
| JS runtime adapter | **held** | prior parity port remains intentionally held rather than creating an incomplete correction path |
| DashClaw live conformance | **blocked external gate** | #361 waits on authorized live Cloudflare/DashClaw execution |
| Field efficacy | **longitudinal / not RC blocker** | #388 waits on T1/T2/T3 field evidence |

---

## Current Open Work

GitHub issue/PR state is authoritative. The active queue is intentionally small:

| Item | Current role |
|------|--------------|
| #410 | **RC umbrella**: compose the accepted architecture into a usable release candidate |
| #427 | **RC production-durability gate**: qualify one production-credible canonical substrate |
| #440 | **Dependency qualification**: re-qualify `agent-manifest` 0.12.0 + `agentrust-trace` 0.10.0 together |
| #408 | **Longitudinal case study**: semantic-recall / canonical-truth pressure case; not an RC core blocker |
| #361 | **Blocked external**: live Cloudflare/DashClaw conformance run |
| #388 | **Longitudinal external evidence**: field-efficacy measurements; not an RC blocker |

### Recently completed / retired

- #437 closed completed through PR #449: query-driven relational recall + LoCoMo-compatible evidence diagnostic.
- #441 closed completed through PR #448: historical checkpoint behavior probes harvested into the current harness layer.
- PR #438 closed unmerged due temporary zero-diff auto-close during reconciliation; PR #449 continued the same implementation branch and landed the corrected work.
- #364 closed completed after governed crossing/shared-domain authority work.
- #363 closed completed for the original persistence audit defects; #427 is the production-substrate successor.
- #332, #387, and #392 are closed/deferred with explicit external or future activation conditions.
- PR #389 merged after its long-standing full-green state was rechecked.
- PRs #404/#405 closed as superseded by coordinated qualification issue #440.

---

## Repository Hygiene

Open work must represent one of:

1. active implementation with an executable next step;
2. a live external/longitudinal gate whose blocker is explicit;
3. a semantic dependency-qualification reason.

Future work without an executable tranche should be closed/deferred and reopened when it becomes actionable. Historical branches must be checked for unique commits before deletion. Branch age alone is not disposal evidence.

---

## Health Indicators

| Indicator | Status | Basis |
|-----------|--------|-------|
| Canonical architecture | **STRONG** | ADR-035 Accepted and reconciled across top-level architecture docs |
| Governance / PAMA boundary | **STRONG AT CURRENT RC BOUNDARY** | #364 complete; estimator/retrieval outputs remain non-authoritative |
| Python public contract | **STRONG** | contract 1.2.0 and schema-backed surface |
| Reference persistence | **STRONG REFERENCE EVIDENCE** | owner contracts, CAS/lock/journal, migration, rollback, auxiliary composition |
| Production persistence | **OPEN RC GATE** | #427; zero production-qualified canonical substrates |
| Multi-memory composition | **IMPLEMENTED RC SLICE** | semantic + epistemic restart-safe composition |
| Retrieval composition | **IMPLEMENTED RC SLICE** | lexical, exact identity, provenance neighbors, query-driven expansion, one admission boundary |
| Retrieval measurement | **IMPLEMENTED INTERNAL + EXTERNAL-COMPATIBLE HARNESS** | internal 3/7 -> 7/7 baseline; LoCoMo evidence diagnostic landed but external dataset result not yet recorded |
| Developer ergonomics | **INCOMPLETE** | canonical small facade remains missing |
| Public benchmark parity | **INCOMPLETE** | no official LoCoMo QA / LongMemEval answer-quality result yet |
| External conformance | **BLOCKED OUTSIDE REPO** | #361 live Cloudflare/DashClaw run |
| Field efficacy | **UNPROVEN LONGITUDINALLY** | #388 |

---

## Next Actions

1. **Advance #427.** Select and qualify one production-credible canonical substrate from evidence rather than preference.
2. **Implement the RC developer facade.** Wrap the existing public contract; do not create a friendlier bypass around PAMA, scope, evidence, or recall admission.
3. **Land one end-to-end RC cognitive-memory fixture** spanning retain/composition/query-driven retrieval/admission/correction/restart/forgetting/history.
4. **Run external/public benchmark evidence** through the now-stable LoCoMo retrieval harness when the dataset is available under appropriate terms; keep retrieval metrics, answer quality, performance, and governance separate.
5. **Execute #440 as one coordinated dependency qualification.** Re-enumerate every version/source binding and prove version-identity checks execute rather than skip.
6. Keep #361, #388, and #408 out of the active implementation critical path until their external/longitudinal evidence gates can move.

---

*Last reconciled against `main` `3dc11b4048e64aa7f6bf78103d664bc93d1cd1e7` on 2026-09-23.*
