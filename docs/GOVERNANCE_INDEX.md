# Governance Index

**Last Reviewed**: 2026-09-23  
**Evidence Boundary**: `main` `0cb98c4d5262338886d82f3c1c6abf6e9c743d10`

This is the current map of Agent Memory's governance surfaces and their freshness obligations. It is intentionally **not** an exhaustive hand-maintained list of historical work. Historical plans and research briefs remain evidence; GitHub issue/PR state carries the live execution queue.

The tier model is a repository-maintenance convention. Qor-logic is development-time tooling only and is not a runtime, build, or test dependency of Agent Memory. The current package dependency contract lives in `pyproject.toml`.

## Tier 1: Current Canonical State

These surfaces MUST describe current repository reality. A wrong version, stale status, or nonexistent current path is a Tier 1 drift bug.

| Artifact | Path | Current marker |
|----------|------|----------------|
| Meta Ledger | `docs/META_LEDGER.md` | append-only historical decision/session evidence; artifact content is authoritative for ledger state |
| System State | `docs/SYSTEM_STATE.md` | reconciled 2026-09-23 against `main` `0cb98c4d`; PRE-RC composition/retrieval active, production substrate qualification open |
| Concept | `docs/CONCEPT.md` | current objective must point to live Backlog/System State/issues rather than retired plans |
| Backlog | `docs/BACKLOG.md` | active RC queue centered on #410, #427, and #437/#438; external/longitudinal work separated |
| Feature Index | `docs/FEATURE_INDEX.md` | feature inventory; lifecycle state must be reconciled when implementation changes materially |
| ADR index | `docs/adr/README.md` | ADR-001 through ADR-038; artifact status is authoritative |
| Package contract | `pyproject.toml` | `agent-memory-reference` 0.2.0; comparator pins remain `agent-manifest==0.11.2`, `agentrust-trace==0.9.0` pending qualification PRs #405/#404 |
| README | `README.md` | current pre-RC product/runtime summary, multi-memory composition, retrieval routes, benchmark limitations |
| Substrate inventory | `docs/43-substrate-inventory-and-maturity.md` | reference persistence corrected; production-qualified canonical substrates remain 0 |
| RC profile | `docs/45-agent-memory-rc1-implementation-profile.md` | bounded implementation/release candidate profile under #410 |
| Checkpoint contract | `docs/46-state-checkpoint-contract.md` | reference persistence ownership/transaction/recovery contract |
| Shadow Genome | `docs/SHADOW_GENOME.md` | append-only failure/lesson record |
| Process Shadow Genome | `docs/PROCESS_SHADOW_GENOME.md` | append-only process-remediation history |

A historical gap label embedded in an older reference document is not current merely because the prose still exists. Current issue/PR state and Tier 1 surfaces control current status.

## Tier 2: Doctrine and Contract Authority

Stable architectural rules. Changes require explicit doctrine/contract work.

| Artifact family | Path |
|-----------------|------|
| Architecture decisions | `docs/adr/README.md`, `docs/adr/ADR-001*` through `ADR-038*` |
| Cognitive-framework architecture | ADR-035 and top-level component/layer/composition documents |
| PAMA foundation and decision table | `docs/pama/README.md`, `docs/04-governance-and-pama.md`, `docs/33-pama-decision-table.md` |
| Public API contract | `docs/44-public-api-contract.md`, `reference/agentmem_ref/api/`, `schemas/api-*.schema.json` |
| Threat/security doctrine | `docs/15-memory-threat-model.md`, `docs/19-privacy-and-sensitivity-classifier.md`, `docs/29-actor-scope-consent-and-tenancy.md`, `docs/41-memory-isolation-domains-and-governed-crossing.md` |
| Evidence/provenance doctrine | `docs/16-source-trust-and-reputation.md`, `docs/30-memory-observability-and-audit-events.md`, `docs/policies/EVIDENCE_PROMOTION.md` |
| Lifecycle/correction/deletion doctrine | `docs/02-lifecycle-state-machine.md`, `docs/17-conflict-resolution-engine.md`, `docs/28-retention-deletion-and-tombstones.md`, `docs/31-recovery-rollback-and-replay.md` |
| Schema contracts | `schemas/*.schema.json`, registry doctrine in `docs/27-schema-registry-and-type-evolution.md` |
| Project governance | `GOVERNANCE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/CODEOWNERS` |

## Tier 3: Active Initiatives

A Tier 3 row must represent active implementation, a live external/longitudinal gate with an explicit blocker, or a dependency qualification. Work that is merely interesting for later should be closed/deferred and reopened when it becomes executable.

| Initiative | Tracking surface | Current state |
|------------|------------------|---------------|
| Agent Memory RC1 composition | issue #410 | **active umbrella**; architecture fixed, usable-product gates remain |
| Production canonical substrate | issue #427 | **active RC gate**; reference durability is proven, production-qualified canonical substrates = 0 |
| Query-driven retrieval + LoCoMo evidence diagnostic | issue #437 / PR #438 | **active implementation**; current PR is not yet merge-ready and must re-pass exact-head validation |
| Semantic recall/canonical-truth case study | issue #408 | active longitudinal research pressure case; not a core RC blocker |
| Live DashClaw conformance | issue #361 | **blocked external** on authorized Cloudflare/DashClaw live traversal; repository-side implementation already merged |
| Field efficacy benchmark | issue #388 | **longitudinal external evidence**; operator skill merged via PR #389; waits on T1/T2/T3 data |
| TRACE dependency qualification | PR #404 | open; `agentrust-trace` 0.10.0 requires semantic comparator/evidence qualification |
| Agent Manifest dependency qualification | PR #405 | open; `agent-manifest` 0.12.0 requires semantic comparator/evidence qualification |

### Recently retired from the active queue

- #364: closed completed after recall/crossing/shared-domain authority remediation.
- #363: closed completed for the original private-scraping/unlocked-generation persistence audit scope; #427 owns production substrate qualification.
- #332: closed `not_planned` in Agent Memory because remaining work is live QOR proving-ground execution, not repository implementation.
- #387: closed `not_planned` for the current cycle; reopen when the Git/document knowledge-profile work becomes executable.
- #392: closed `not_planned` until DashClaw establishes TransitionRuleCorpus authorship/ownership.
- PR #389: merged after rechecking its long-standing full-green evidence.

## Tier 4: Active or Held Plan Artifacts

Only plans whose lifecycle is still active/held belong here. Completed plans are historical evidence.

| Artifact | Path | State |
|----------|------|-------|
| Sprint 4b JS PAMA plan | `docs/plan-sprint4b-js-pama.md` | **HELD**; direct parity port remains inappropriate without a complete correction/remediation route |
| Sprint 4b research brief | `docs/research-brief-sprint4b-js-pama-2026-09-07.md` | supporting research for the held plan |
| RC1 implementation profile | `docs/45-agent-memory-rc1-implementation-profile.md` | **ACTIVE** under #410 |

Implemented sprint plans remain in `docs/` as historical evidence. Their continued existence does not mean the work is pending.

## Tier 5: Reference Material

Informational and slower-drift. Factual claims should be corrected when they materially diverge from current code, while historical measurements should remain labeled as historical.

| Family | Path |
|--------|------|
| Numbered doctrine / architecture references | `docs/00-*.md` through `docs/46-*.md` |
| Canonical architecture synthesis | `docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md` |
| Documentation map | `docs/README.md` |
| Implementation maps | `docs/05-repo-implementation-map.md`, `docs/39-implementation-ownership-map.md` |
| Profiles | `docs/profiles/` |
| Programs | `docs/programs/` |
| PRD / RFC | `docs/prd/`, `docs/rfcs/` |
| Reference runtime guide | `reference/README.md` |
| Configuration guide | `docs/CONFIGURATION.md` |
| Wiki source | `wiki-src/` |
| Research bibliography / explorations | `docs/23-research-bibliography.md`, `docs/research/`, `docs/explorations/` |

## Tier 6: Historical Governance Evidence

Frozen/provenance-oriented artifacts preserve what was decided, measured, or planned at the time rather than impersonating current state.

| Historical family | Path / source |
|-------------------|---------------|
| Genesis architecture blueprint | `docs/ARCHITECTURE_PLAN.md` |
| Deep-audit snapshot | `docs/RESEARCH_BRIEF.md` |
| Completed implementation plans | `docs/plan-*.md` except active/held Tier 4 entries |
| Completed research briefs | `docs/research-brief-*.md` except active/held Tier 4 entries |
| Audit records | `docs/audits/` |
| Generated reports | `reports/` |
| Committed provider evidence fixtures | `reference/fixtures/component-qualification/*.json` |
| Historical branch state | old branches; compare for unique commits before deletion, but do not use them as current-state authority |

`docs/META_LEDGER.md` remains Tier 1 because its chain must stay current even though the decisions it records are historical evidence.

## Current Development Sequence

Tier 1 surfaces should agree on this order:

1. **#437 / PR #438:** repair query-driven relational recall and the LoCoMo evidence-retrieval harness until the exact final head is fully green.
2. **#427:** qualify one production-credible canonical substrate without changing Agent Memory semantics to match a provider.
3. **RC developer facade:** implement a small ergonomic surface over the existing 1.2.0 contract.
4. **RC end-to-end fixture:** prove retain/composition/retrieval/admission/correction/restart/forgetting/history as one usable scenario.
5. **Public benchmark evidence:** run licensed external datasets through stable benchmark adapters; keep retrieval, answer quality, performance, and governance metrics separate.
6. **#404 / #405:** qualify comparator dependency updates independently.
7. Keep #361 and #388 out of the active implementation critical path until their external evidence can move.

## Drift Contract

When reconciling current state:

1. Read `main`, the ADR index, open issues/PRs, and package metadata before editing status prose.
2. Do not update historical plan/research claims merely because later work changed reality; label them historical instead.
3. Do not duplicate volatile counts unless the count adds operational value.
4. Any current path named here must exist on `main`, or be explicitly labeled absent/held/external.
5. `SYSTEM_STATE.md`, `BACKLOG.md`, `CONCEPT.md`, and this index must agree on the active objective and blockers before a new implementation tranche begins.
6. An old open issue/PR is not self-justifying. It must have an active next action, an explicit blocker, or be retired from the active queue.

## How to Add or Retire a Governance Surface

- Add a surface to the tier matching its freshness contract in the same change that makes it authoritative.
- When active work closes, remove it from Tier 3/4 rather than preserving a false pending state for nostalgia.
- Preserve historical evidence unless there is a separate reason to remove it.
- Refresh **Last Reviewed** and the evidence boundary whenever Tier 1 state changes materially.
