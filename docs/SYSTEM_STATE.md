# System State

## Snapshot Metadata

| Attribute | Value |
|-----------|-------|
| **Last Reconciled** | 2026-09-16 |
| **Evidence Boundary** | `main` `7d7f86aeef8a80da6fab0e93c87153c33d8f3b78` |
| **Phase** | SUBSTANTIATED THROUGH PUBLIC API 1.2.0 AND POST-1.2 AUTHORITY CLEANUP; production state and external proof remain open |
| **Latest Ledger Entry** | Entry #59 (amendment to Sprint 4c-2 import/dependency behavior) |
| **Latest Session Seal** | Entry #58 (Sprint 4c-2, contract 1.2.0, ADR-038) |
| **Reference Package** | `agent-memory-reference` 0.2.0 |
| **Public API Contract** | 1.2.0 |

This document is a current-state projection, not an additional authority source. Canonical decisions live in the ADRs and `docs/META_LEDGER.md`; unresolved work lives in `docs/BACKLOG.md` and the linked GitHub issues/PRs.

---

## Current Reality

### Shipped / substantiated

- ADR-037 fail-closed review is implemented in the Python reference runtime. Assertion alone no longer discharges `require_review`; parked proposals have an evidence/remediation path, evidence qualification and dependence grouping exist, and resumption remains evaluator-controlled.
- Public API contracts `1.0.0`, `1.1.0`, and `1.2.0` landed through PRs #394, #397, and #398.
- The Python public surface has schema-backed boundary forms for proposal, decision/approval, commit, retrieval candidate, recall admission, history, posture, action authority, and execution evidence.
- ADR-038 is Accepted. `action_execution` is a PAMA operation distinct from `authority_change`; action authority and execution evidence are bound to governed decisions.
- Package layout is layered (`core < state < contracts < runtime < memory < api < crg < harness`) with compatibility aliases for the prior flat import surface.
- Schema resolution is wheel-safe through the packaged `_schemas/` copy; the legacy `data-files` resolver path is retired.
- Ledger SESSION SEAL trees through the implemented seal-anchor work are represented under `refs/seals/` rather than left as unreachable `write-tree` objects.

### Post-1.2.0 authority consistency sweep

Three inconsistencies discovered after the public API boundary were corrected and merged:

- **#395 / PR #400**: approval, commit, and delete now use consistent attestation dispatch. An attestation that can discharge `require_external_verification` is no longer silently ignored by commit when qualified evidence is absent; ordinary `require_review` remains parked.
- **#401 / PR #402**: `domain_schema_mutation` no longer carries a duplicate pre-ADR-037 assertion discharge. Its versioned base cells flow through shared PAMA floors, evidence qualification, and bound attestation authority.
- **#403 / PR #406**: exact and semantic rejected-value reversal no longer depend on caller-set `review_satisfied` / `approval_refs`. Reversal now requires qualified correction evidence plus separate proposal-bound external authority. Re-admission authority metadata survives restart.

The inconsistency sweep did not weaken the evidence ladder or make estimator similarity authoritative.

### Latest recorded verification

PR #406 was validated against `main` immediately before merge:

- **1208 tests run, 0 failures, 19 skipped** in the full `Validate Doctrine Evidence` discovery;
- Restart-Safe Runtime green, including preservation of readmission authority across recovery;
- Runtime Configuration, Capability Behavior, Structural Mutation Governance, Write-to-Readable Visibility, and Authority Laundering Evidence green;
- Operational and Long Horizon memory benchmarks green;
- Cedar, OPA, Agent Manifest, TRACE/cMCP, and External Evidence Contract comparator workflows green;
- the complete PR workflow matrix finished successfully before merge.

These are repository-level verification claims. They do **not** establish production-memory correctness, deployment durability, or field efficacy.

---

## Dependency Manifest

`pyproject.toml` remains the current package authority:

| Dependency | Current contract | Status |
|------------|------------------|--------|
| `jsonschema` | `>=4.20,<5` | hard dependency |
| `cryptography` | `>=50,<51` | hard dependency |
| `rfc8785` | `>=0.1,<0.2` | hard dependency |
| `agent-manifest` | `==0.11.2` | optional `comparators` extra; PR #405 proposes 0.12.0 |
| `agentrust-trace` | `==0.9.0` | optional `comparators` extra; PR #404 proposes 0.10.0 |
| Graphiti / Kuzu path | non-canonical optional substrate path | production persistence unresolved under #363 |

Dependency PRs #404 and #405 are qualification work, not automatic maintenance merges. They change evidence/comparator dependencies and must preserve the repository's pinned interoperability claims.

---

## Runtime Boundaries

| Surface | State | Notes |
|---------|-------|-------|
| Python public API | **1.2.0 / active** | Nine classified surface functions; schema-backed envelopes; #362 closed as complete |
| Python governed adapter | **active / authority sweep complete** | #395, #401, and #403 closed; remaining recall/scope authority work is #364 |
| Recall / scope crossing | **incomplete** | embedding host authentication remains the declared principal boundary; shared-domain membership mutation and durable scope-widening consequence binding remain under #364 |
| Restart/checkpoint runtime | **reference-only** | in-memory-specific/private-state coupling remains; #363 is the production-state blocker |
| JS runtime adapter | **held** | separate contract, no PAMA parity; Sprint 4b vetoed because a direct port would make corrections non-committable without a discharge route |
| DashClaw correction path | **parked by design** | #392 requires an evaluator-held transition rule corpus and a rule-authorship decision |
| External proving | **incomplete** | #332 and #361 remain open |
| Field efficacy | **designed, not measured** | #387/#388 define the profile/case-study path; PR #389 is supporting tooling, not efficacy evidence |

---

## Current Open Work

GitHub issue/PR state is authoritative. The active program currently consists of:

| Item | Role in current program |
|------|-------------------------|
| #364 | **Active development front**: govern shared-domain membership mutation and bind authorized scope expansion to the exact durable consequence |
| #363 | **Next major runtime tranche**: explicit production state/persistence contract and non-toy durable implementation boundary |
| #392 | DashClaw correction discharge route / transition-rule authority; held pending rule-authorship decision |
| #361 | Live DashClaw conformance through a minimal Cloudflare provider |
| #332 | QOR Agent / Cloudflare governed-memory proving ground |
| #387 | Governed canonical knowledge artifact profile and Git/document adapter |
| #388 | Longitudinal governed-memory field efficacy benchmark |
| PR #389 | Governance-memory efficacy review skill; must be rebased/revalidated against current `main` |
| PR #404 | Qualify `agentrust-trace` 0.10.0 against the current comparator/evidence contract |
| PR #405 | Qualify `agent-manifest` 0.12.0 against the current comparator/evidence contract |

The `RecallContext.principal_ref` caller field is **not** itself an unresolved local-auth bug under the current architecture. The embedding host is the declared authenticator and the adapter records/evaluates the supplied principal. Changing that trust boundary would require an explicit architecture decision rather than quietly growing an identity system inside the memory adapter.

---

## Branch / Worktree Hygiene

Current work branches should be judged by divergence, not age. In particular, historical branches such as `feat/agent-memory-genesis`, `implementation/332-checkpoint-behavioral-assessment`, and `research/275-code-reality-runtime` must be compared against `main` for unique commits before deletion.

The current documentation reconciliation branch and open feature/dependency branches are work surfaces, not current-state authority. `main`, Tier 1 docs, ADRs, ledger, and live GitHub issue/PR state remain authoritative.

---

## Health Indicators

| Indicator | Status | Basis |
|-----------|--------|-------|
| Governance decision model | **STRONG** | ADR-037 implemented; evidence/authority separation explicit |
| Python public contract | **STRONG** | Contract 1.2.0, schema-backed surface, #362 closed |
| Post-1.2 semantic consistency | **STRONG AT CURRENT BOUNDARY** | #395, #401, #403 closed with full validation |
| Reference test/evidence corpus | **STRONG AT RECORDED BOUNDARY** | 1208 run / 0 fail / 19 skip on PR #406 final head; full workflow matrix green |
| Recall/scope authority | **INCOMPLETE** | #364 |
| Production persistence | **BLOCKING PRODUCTION CLAIM** | #363 |
| JS parity | **HELD INTENTIONALLY** | Sprint 4b audit veto |
| External conformance | **INCOMPLETE** | #332, #361 |
| Field efficacy | **UNPROVEN** | #387, #388 |
| Dependency interoperability | **QUALIFICATION PENDING** | PRs #404, #405 |
| Control-plane documentation | **RECONCILED ON BRANCH** | this documentation-only cleanup must still merge |

---

## Next Actions

Sequence work in this order:

1. **Close #364 scope-authority defects without changing the declared host-authentication boundary.** First bind a successful governed crossing decision to the exact durable scope mutation; then replace raw shared-domain membership mutation with a governed transition and auditable persistence.
2. **Take #363 as the next major runtime tranche.** Define an explicit persistence/checkpoint/state-provider contract before selecting or wiring a production database. Eliminate private-attribute scraping as the runtime state interface, define transactional generation semantics, persist required auxiliary state, and make migration/version behavior explicit.
3. **Qualify dependency PRs #404 and #405 separately.** Re-run the relevant external/comparator evidence rather than treating Dependabot green-ness as semantic compatibility.
4. **Resume external proving after the state boundary is credible.** #332 and #361 provide the live host/provider proof; keep #392 parked until rule authorship is explicit.
5. **Rebase/revalidate PR #389 and execute #387/#388** to move from conformance evidence toward field efficacy. Do not infer efficacy from repository tests alone.
6. **Inspect historical branches for unique commits before cleanup/deletion.** Branch age is not evidence that work is disposable.

---

*Last reconciled against `main` `7d7f86aeef8a80da6fab0e93c87153c33d8f3b78` on 2026-09-16.*
