# Project Backlog

This file is the current repository-level work queue. Historical sprint plans and ledger entries explain prior decisions; open GitHub issues carry the detailed acceptance criteria for unresolved work.

## Blockers (Must Fix Before Production-Readiness Claims)

### Security / Authority Blocker
- [ ] [S1] Issue #364: close the remaining recall/scope authority legs. The embedding host remains the declared authenticator for `RecallContext.principal_ref`; shared-domain membership mutation and write-side scope expansion still need governed authority enforcement and durable consequence binding.

### Runtime / Persistence Blocker
- [ ] [D1] Issue #363: define and implement the production state profile. The current checkpoint path is in-memory-specific and private-attribute-coupled; non-toy substrate persistence, auxiliary runtime state, concurrency semantics, and migration behavior remain incomplete.

## Backlog (Planned Work)
- [ ] [B1] `runtime_core_v1` — **substantially complete at the public Python contract, incomplete at authority/persistence boundaries**. Contract `1.2.0` exposes schema-backed proposal, decision/approval, commit, recall, history, posture, action-authority, and execution-evidence stages. Remaining core work is #364, #363, and the deliberately held JS/PAMA parity slice from Sprint 4b.
- [ ] [B2] `cognitive_modules_v1` — resolve remaining first-party qualification and cognitive-plane completion work against current implementation evidence before opening new conceptual surface area.
- [ ] [B3] `production_readiness_v1` — complete external/runtime proof rather than inferring production readiness from repository tests: QOR proving ground #332, live DashClaw conformance #361, governed knowledge profile #387, and longitudinal efficacy program #388. PR #389 supports the efficacy program but must be rebased/revalidated against current `main` before merge.
- [ ] [B4] Section 4 Razor — assess/refactor legacy reference modules above the repository's size/complexity thresholds without weakening governance or evidence controls.
- [x] [B5] Repository security baseline — secret scanning, push protection, CodeQL, private vulnerability reporting, and Dependabot configuration confirmed/landed during Sprint 1.
- [ ] [B6] Issue #392: DashClaw correction discharge route. Keep parked until rule authorship/ownership for an evaluator-held `TransitionRuleCorpus` is decided; do not substitute authority or repeated agreement for evidence that the transition is correct.

## Dependency Qualification Queue

These are evidence/interoperability dependencies, not routine version bumps:

- [ ] [M1] PR #404: qualify `agentrust-trace` 0.10.0 against the current TRACE/cMCP and evidence-contract comparators before merge.
- [ ] [M2] PR #405: qualify `agent-manifest` 0.12.0 against the current Agent Manifest comparator and package/runtime expectations before merge.

## Explicit Holds
- **Sprint 4b / JS PAMA parity**: held after audit veto. The draft port matched Python policy evaluation but would have made every correction non-committable because no discharge path was ported in the same cycle. Resume only with a complete correction/remediation route.
- **DashClaw #392**: blocked on a DashClaw-side rule-authorship decision.

## Completed Since the Previous Backlog Snapshot
- Public API contracts `1.0.0`, `1.1.0`, and `1.2.0` landed through PRs #394, #397, and #398.
- ADR-037 fail-closed review/remediation path is implemented in the Python reference runtime.
- ADR-038 added `action_execution` and bound action authority/execution evidence to PAMA decisions.
- #395 / PR #400 aligned approval, commit, and deletion attestation dispatch without allowing attestation-only discharge of ordinary `require_review`.
- #401 / PR #402 removed the duplicate assertion discharge from `domain_schema_mutation` and routed the versioned evaluator through shared PAMA authority/evidence semantics.
- #403 / PR #406 replaced legacy readmission approval booleans with a two-key governed reversal: qualified correction evidence plus proposal-bound external reversal authority. Readmission authority metadata survives restart.
- Final PR #406 validation at `7d7f86ae` boundary: 1208 tests run, 0 failures, 19 skipped; complete attached workflow matrix green, including restart/runtime, benchmarks, Cedar, OPA, Agent Manifest, TRACE/cMCP, and External Evidence Contract comparators.

---
_Last reconciled against `main` `7d7f86aeef8a80da6fab0e93c87153c33d8f3b78` on 2026-09-16._
