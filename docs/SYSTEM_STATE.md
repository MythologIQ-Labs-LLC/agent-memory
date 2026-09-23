# System State

## Snapshot Metadata

| Attribute | Value |
|-----------|-------|
| **Last Reconciled** | 2026-09-23 |
| **Evidence Boundary** | `main` `0cb98c4d5262338886d82f3c1c6abf6e9c743d10` |
| **Phase** | PRE-RC: usable-runtime composition, retrieval evidence, and production-substrate qualification |
| **Reference Package** | `agent-memory-reference` 0.2.0 |
| **Public API Contract** | 1.2.0 |
| **Production-qualified canonical substrates** | 0 |

This document is a current-state projection, not an additional authority source. Canonical architectural decisions live in the ADRs and `docs/META_LEDGER.md`. Current implementation work lives in `docs/BACKLOG.md` and live GitHub issues/PRs.

---

## Current Reality

### Architecture and authority

- ADR-035 is Accepted and the top-level architecture documents now describe Agent Memory as one governed cognitive framework rather than a collection of adjacent memory services.
- Public API contract `1.2.0` remains the canonical versioned consumer contract.
- Issue #364 is closed as completed. Shared-domain membership mutation and crossing consequences now use governed authority paths; the embedding host remains the declared authenticator for `RecallContext.principal_ref` unless a future ADR changes that trust boundary.
- Candidate retrieval, ranking, graph/provenance relations, estimator confidence, and provider-native scores do not create recall or mutation authority.

### Reference persistence

The original persistence audit tracked by #363 has been materially remediated and #363 is closed. The reference durability profile now includes:

- explicit state-owner checkpoint contracts rather than restart-runtime private-field scraping;
- substrate-owned identifier progress;
- compare-and-commit generation semantics;
- process locking and a hash-chained commit journal;
- fail-closed torn-write / stale-writer behavior;
- governed checkpoint/profile migration and rollback evidence;
- a public checkpoint-transaction support seam;
- owner restart contracts for projection state, write claims, and telemetry;
- atomic composition of auxiliary correctness state into the same checkpoint generation;
- restart-safe composed epistemic state.

This proves the **reference persistence semantics**. It does not establish a production storage choice. Issue #427 owns qualification of the first production-credible canonical substrate.

### Multi-memory composition

The RC composition work is no longer limited to isolated reference modules.

- Canonical semantic memory and epistemic belief memory participate in one restart-safe composition path.
- Shared source/evidence provenance can produce distinct semantic and epistemic consequences without collapsing their identity, lifecycle, or authority semantics.
- Epistemic confidence cannot overwrite canonical semantic truth or bypass review.
- Procedural, predictive, Cognitive Mesh, CRG/CodeGenome, and other bounded capabilities remain implemented/evidenced surfaces, but not every declared capability is required to be productionized for RC1.

### Retrieval

The current RC runtime has three deterministic candidate routes behind one governed admission boundary:

1. lexical candidate retrieval;
2. exact logical-identity retrieval;
3. shared-evidence/provenance-neighbor retrieval when the substrate exposes that optional capability.

Per-route provenance is retained, candidates are deduplicated, and deterministic ranking occurs only among admitted candidates. A score of `1.0`, relational reachability, or multi-route agreement cannot repair a scope/currentness refusal.

The internal versioned retrieval-quality fixture records a bounded baseline:

```text
lexical-only admitted recall: 3 / 7 = 0.428571
composed admitted recall:     7 / 7 = 1.0
admitted precision:           1.0 in both systems
governance failures:          0 in the bounded fixture
```

This is internal synthetic evidence, not a LoCoMo or LongMemEval result.

### Public benchmark work

Issue #437 / PR #438 is the current retrieval-benchmark implementation front. It adds an opt-in query-driven relational baseline and a retrieval-only LoCoMo evidence harness so natural-language questions do not depend on caller-supplied memory IDs.

PR #438 is **not yet merge-ready**. Its first exact-head matrix exposed failures in the new query-driven/benchmark slice and must be corrected and revalidated before merge. No LoCoMo answer-quality or Jev-Mem parity claim exists yet.

### Repository/operator tooling

PR #389 merged on 2026-09-23 as `0cb98c4d5262338886d82f3c1c6abf6e9c743d10`, adding the reusable GitHub governance + memory efficacy review skill and workbook template.

---

## Dependency Manifest

`pyproject.toml` remains the current package authority:

| Dependency | Current contract | Status |
|------------|------------------|--------|
| `jsonschema` | `>=4.20,<5` | hard dependency |
| `cryptography` | `>=50,<51` | hard dependency |
| `rfc8785` | `>=0.1,<0.2` | hard dependency |
| `agent-manifest` | `==0.11.2` | optional comparator dependency; PR #405 proposes 0.12.0 and remains unmerged |
| `agentrust-trace` | `==0.9.0` | optional comparator dependency; PR #404 proposes 0.10.0 and remains unmerged |
| Graphiti / Kuzu path | experimental / non-canonical production choice | current Kuzu-backed adapter is not production-qualified |

Dependency PRs #404 and #405 are semantic/interoperability qualification work, not routine green-button upgrades.

---

## Runtime Boundaries

| Surface | State | Notes |
|---------|-------|-------|
| Python public API | **1.2.0 / active** | schema-backed stages for proposal, approval, commit, recall, history, posture, action authority, and execution evidence |
| Python governed adapter | **active** | post-1.2 authority sweep and #364 work complete |
| Host principal authentication | **external boundary by design** | embedding host authenticates; Agent Memory records/evaluates the supplied principal |
| Restart/checkpoint runtime | **reference-qualified** | strong reference durability semantics; production canonical substrate still unqualified under #427 |
| Multi-memory composition | **RC reference slice active** | semantic + epistemic composition is restart-safe and type-preserving |
| Multi-route recall | **RC reference slice active** | lexical + exact identity + shared-evidence neighbors; one governed admission boundary |
| Query-driven public-benchmark recall | **in development** | #437 / PR #438; not yet merge-ready |
| Developer ergonomic facade | **missing RC gate** | canonical `AgentMemory.open()/remember()/recall()/...` facade has not landed |
| JS runtime adapter | **held** | prior parity port remains intentionally held rather than creating an incomplete correction path |
| DashClaw live conformance | **blocked external gate** | #361 waits on authorized live Cloudflare/DashClaw execution; repository-side implementation is already on `main` |
| Field efficacy | **longitudinal / not RC blocker** | #388 waits on T1/T2/T3 field evidence; #389 tooling is merged |

---

## Current Open Work

GitHub issue/PR state is authoritative. The live work surfaces are now intentionally smaller:

| Item | Current role |
|------|--------------|
| #410 | **RC umbrella**: compose the accepted architecture into a usable release candidate |
| #427 | **RC production-durability gate**: qualify one production-credible canonical substrate |
| #437 / PR #438 | **Active retrieval front**: query-driven relational recall + LoCoMo evidence-retrieval diagnostic |
| #408 | Longitudinal anonymized semantic-recall / canonical-truth case study; research pressure case, not an RC core blocker |
| #361 | **Blocked external**: live Cloudflare/DashClaw conformance run |
| #388 | **Longitudinal external evidence**: field-efficacy measurements; not an RC blocker |
| PR #404 | Dependency qualification: `agentrust-trace` 0.10.0 |
| PR #405 | Dependency qualification: `agent-manifest` 0.12.0 |

### Recently retired stale work

- #364 closed completed after governed crossing/shared-domain authority work.
- #363 closed completed for the original persistence audit defects; #427 is the production-substrate successor.
- #332 closed `not_planned` in this repository because remaining work is live QOR proving-ground execution, not Agent Memory implementation.
- #387 closed `not_planned` for the current cycle; reopen when the Git/document knowledge profile is actively resumed.
- #392 closed `not_planned` until DashClaw establishes TransitionRuleCorpus authorship/ownership.
- PR #389 merged after its long-standing full-green state was rechecked.

---

## Repository Hygiene

Open work must represent one of three things:

1. active implementation with an executable next step;
2. a live external/longitudinal gate whose blocker is explicit;
3. a dependency qualification that cannot be treated as a routine version bump.

Future work without a scheduled tranche should be closed/deferred and reopened when it becomes executable rather than accumulating indefinitely in the active queue.

Historical branches must still be checked for unique commits before deletion. Branch age alone is not disposal evidence.

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
| Retrieval composition | **IMPLEMENTED RC SLICE** | three deterministic routes, single governed admission boundary |
| Retrieval measurement | **IMPROVING** | internal 3/7 -> 7/7 bounded baseline; LoCoMo evidence diagnostic in #438 |
| Developer ergonomics | **INCOMPLETE** | canonical small facade remains missing |
| Public benchmark parity | **INCOMPLETE** | no official LoCoMo QA / LongMemEval result yet |
| External conformance | **BLOCKED OUTSIDE REPO** | #361 live Cloudflare/DashClaw run |
| Field efficacy | **UNPROVEN LONGITUDINALLY** | #388 |

---

## Next Actions

Sequence the current implementation work as follows:

1. **Repair and revalidate #438.** Preserve the default recall behavior while proving the opt-in query-driven relational path and LoCoMo evidence harness.
2. **Advance #427.** Select and qualify one production-credible canonical substrate from evidence rather than preference.
3. **Implement the RC developer facade.** Wrap the existing public contract; do not create a friendlier bypass around PAMA, scope, evidence, or recall admission.
4. **Land one end-to-end RC cognitive-memory fixture** spanning retain/composition/retrieval/admission/correction/restart/forgetting/history.
5. **Run external/public benchmark evidence** only after the benchmark adapter is stable; keep retrieval metrics, answer quality, performance, and governance measurements separate.
6. **Handle #404/#405 independently** as comparator/evidence dependency qualifications.
7. Keep #361 and #388 out of the active implementation critical path until their external evidence gates can actually move.

---

*Last reconciled against `main` `0cb98c4d5262338886d82f3c1c6abf6e9c743d10` on 2026-09-23.*
