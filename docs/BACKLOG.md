# Project Backlog

This file is the current repository-level work queue. Historical sprint plans, research briefs, and ledger entries explain prior decisions; live GitHub issues/PRs carry detailed acceptance criteria for unresolved work.

The queue is intentionally small. Work that is blocked externally or merely interesting for later must not masquerade as active implementation.

## RC1 Critical Path

### 1. Query-driven recall and public-benchmark evidence

- [ ] **#437 / PR #438**: add opt-in query-driven relational recall and a retrieval-only LoCoMo evidence harness.
- [ ] Repair the current #438 failures and rerun the complete exact-head matrix before merge.
- [ ] Preserve default application recall behavior unless query-driven expansion is explicitly selected.
- [ ] Keep the LoCoMo dataset external; no upstream dataset redistribution in this repository.
- [ ] Do not claim an official LoCoMo QA score or Jev-Mem parity from retrieval-only evidence.

### 2. Production canonical substrate

- [ ] **#427**: qualify one production-credible canonical substrate.
- [ ] Preserve the existing `TemporalGraphPort` / governed-adapter semantics rather than reshaping Agent Memory around a provider.
- [ ] Prove retain/correct/forget restart behavior, scope/currentness/history, stale-writer/interrupted-recovery safety, exact provider/version identity, and operational limitations.

The original persistence audit issue #363 is closed. Its reference-runtime defects were remediated; #427 is the remaining production-qualification gate.

### 3. Developer facade

- [ ] Add the canonical small developer surface over public contract 1.2.0, conceptually:

```python
memory = AgentMemory.open(...)
memory.remember(...)
memory.recall(...)
memory.correct(...)
memory.forget(...)
memory.history(...)
memory.posture(...)
```

- [ ] Ordinary low-risk local use must not require callers to construct internal PAMA dataclasses manually.
- [ ] The facade must return governed results/receipts and may not bypass scope, evidence, PAMA, currentness, or recall admission.

### 4. End-to-end RC scenario

- [ ] Add one scenario that proves the usable product path as a whole:

```text
experience
  -> stable identity + evidence
  -> multiple typed memory consequences
  -> persisted governed state
  -> multi-route/query-driven candidate retrieval
  -> governed admission
  -> correction/supersession
  -> restart
  -> current recall + reconstructable history
  -> forgetting/tombstone
```

- [ ] Include at least one highly relevant/confident but inadmissible candidate and prove it cannot influence active cognition.

### 5. Release evidence package

- [ ] Bind benchmark dataset/version/config/runtime revision.
- [ ] Keep retrieval quality, answer/task quality, latency/resource measurements, and governance/safety measurements separate.
- [ ] Publish known limitations with the RC.
- [ ] Add public LoCoMo/LongMemEval evidence only after the adapters are stable and licensing/use conditions are respected.

## Implemented RC Foundations

These are no longer blockers and should not be reopened by stale backlog prose.

- [x] ADR-035 status/top-level architecture reconciliation.
- [x] #364 recall/crossing/shared-domain authority remediation.
- [x] Reference checkpoint owner contracts; no restart-runtime private-field scraping as the checkpoint contract.
- [x] Generation CAS, process locking, commit journal, stale-writer and torn-write safeguards.
- [x] Governed checkpoint/profile migration and rollback evidence.
- [x] Public transaction-support seam for persistence/migration.
- [x] Projection/write-claim/telemetry owner restart contracts.
- [x] Atomic auxiliary-state composition in the same checkpoint generation.
- [x] Restart-safe semantic + epistemic composition slice.
- [x] Candidate/admission separation for multi-route recall.
- [x] Lexical + exact logical-identity retrieval routes.
- [x] Agent Memory-native shared-evidence/provenance-neighbor retrieval.
- [x] Internal deterministic retrieval-quality benchmark and CI evidence artifact.
- [x] PR #389 reusable GitHub governance/memory efficacy operator skill.

Internal bounded benchmark evidence currently records:

```text
lexical-only admitted recall = 3/7 (0.428571)
composed admitted recall     = 7/7 (1.0)
admitted precision           = 1.0
governance failures          = 0
```

This is synthetic internal evidence, not an official public benchmark result.

## Dependency Qualification Queue

These are evidence/interoperability dependencies, not routine version bumps:

- [ ] **#440**: re-qualify `agent-manifest` 0.12.0 and `agentrust-trace` 0.10.0 together as one version-exact interoperability change.
- [ ] Re-enumerate all current package pins, source/tag/commit bindings, schemas/fixtures, comparator assertions, and qualification identities before editing.
- [ ] Prove pin/version identity tests **execute** rather than silently skip under the new pair.
- [ ] Validate the material fail-closed/security semantics from both releases at the Agent Memory boundary actually consumed.
- [ ] Run the exact-head full reference/comparator matrix before merge.

PRs #404 and #405 are closed as structurally incomplete bare Dependabot bumps. PR #375 is the precedent: these dependencies cannot be qualified safely one file at a time.

## External / Longitudinal Gates

These remain open only where an external or time-based evidence gate is real. They are not part of the active RC implementation critical path unless a reproduced Agent Memory defect emerges.

- **#361 — blocked external:** repository-side DashClaw provider work is merged; completion requires authorized live Cloudflare/DashClaw traversal and correlated evidence.
- **#388 — longitudinal:** the efficacy procedure/tooling is merged via PR #389; completion requires T1/T2/T3 field evidence.
- **#408 — longitudinal case study:** next executable gate is the frozen T0/source-system baseline and measured failure taxonomy; do not spawn speculative implementation slices before evidence exists.

## Explicit Holds / Deferred Work

- **Sprint 4b / JS PAMA parity:** held. Resume only with a complete correction/remediation route rather than a superficial evaluator port.
- **#392:** closed `not_planned` until DashClaw makes the TransitionRuleCorpus authorship/ownership decision.
- **#387:** closed `not_planned` for this cycle. Reopen when the Git/document-backed governed knowledge profile becomes an active implementation tranche.
- **#332:** closed in Agent Memory. Remaining QOR proving-ground acceptance is live host execution, not standalone Agent Memory repository work.

## Repository Hygiene Rule

An open issue/PR must have one of the following:

1. an executable next implementation/review step;
2. an explicit external/longitudinal blocker that justifies remaining open;
3. a semantic dependency-qualification reason.

Otherwise retire it from the active queue and reopen when it becomes executable. Age is not itself a reason to close work, but age without a next action is a backlog smell and must be reconciled.

Historical branches must be compared against `main` for unique commits before deletion.

---

_Last reconciled against `main` `0cb98c4d5262338886d82f3c1c6abf6e9c743d10` on 2026-09-23._
