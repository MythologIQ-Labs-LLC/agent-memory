# Governance Index

**Last Reviewed**: 2026-10-14  
**Evidence Boundary**: `main` `38f6a7dcc358e8ee50a38d703b0addb9d8e660d7`; exact-version source and #797/#798/#803 states rechecked 2026-10-14. This is a revision-bound snapshot, not a continuously updated status feed.

This is the current map of Agent Memory's governance surfaces and their freshness obligations. It is intentionally **not** an exhaustive hand-maintained list of historical work. Historical plans and research briefs remain evidence; GitHub issue/PR state carries the live execution queue.

The tier model is a repository-maintenance convention. Qor-logic is development-time tooling only and is not a runtime, build, or test dependency of Agent Memory. The current package dependency contract lives in `pyproject.toml`.

## Tier 1: Current Canonical State

These surfaces MUST describe current repository reality. A wrong version, stale status, or nonexistent current path is a Tier 1 drift bug.

| Artifact | Path | Current marker |
|----------|------|----------------|
| Meta Ledger | `docs/META_LEDGER.md` | append-only historical decision/session evidence; artifact content is authoritative for ledger state |
| System State | `docs/SYSTEM_STATE.md` | compact revision-bound factual projection; follow code, baseline register, substrate inventory and live GitHub issue/PR state for newer changes |
| Concept | `docs/CONCEPT.md` | current objective must point to live Backlog/System State/issues rather than retired plans |
| Backlog | `docs/BACKLOG.md` | roadmap and queue inventory; use the live issue/PR state before executing and preserve historical owner rulings |
| Feature Index | `docs/FEATURE_INDEX.md` | feature inventory; lifecycle state must be reconciled when implementation changes materially |
| ADR index | `docs/adr/README.md` | ADR-001 through ADR-043, with each source ADR owning its own proposal/acceptance status |
| Package contract | `pyproject.toml` and `reference/agentmem_ref/api/contract.py` | Read package version and optional comparator pins from `pyproject.toml`, public API `CONTRACT_VERSION` from `api/contract.py`. Historical dependency qualification is recorded under #440. This index does not duplicate volatile version strings |
| README | `README.md` | three-audience entry points and canonical-current-state routing merged by #798; actual feature and qualification status belongs to the linked subject owners |
| Substrate inventory | `docs/43-substrate-inventory-and-maturity.md` | SQLite single-host canonical substrate RC-qualified under closed #427; PostgreSQL, Markdown, distributed and Graphiti are not qualified equivalent canonical profiles |
| RC profile | `docs/45-agent-memory-rc1-implementation-profile.md` | bounded implementation/release candidate profile under #410 |
| Checkpoint contract | `docs/46-state-checkpoint-contract.md` | reference persistence ownership/transaction/recovery contract |
| Checkpoint behavior profile | `docs/profiles/checkpoint-behavioral-assessment-profile.md` | current evidence-only behavioral conformance profile; no authority effect |
| Shadow Genome | `docs/SHADOW_GENOME.md` | append-only failure/lesson record |
| Process Shadow Genome | `docs/PROCESS_SHADOW_GENOME.md` | append-only process-remediation history |

A historical gap label embedded in an older reference document is not current merely because the prose still exists. Current issue/PR state and Tier 1 surfaces control current status.

## Tier 2: Doctrine and Contract Authority

Stable architectural rules. Changes require explicit doctrine/contract work.

| Artifact family | Path |
|-----------------|------|
| Architecture decisions | `docs/adr/README.md`, `docs/adr/ADR-001*` through `ADR-043*` |
| Cognitive-framework architecture | ADR-035 and top-level component/layer/composition documents |
| PAMA foundation and decision table | `docs/pama/README.md`, `docs/04-governance-and-pama.md`, `docs/33-pama-decision-table.md` |
| Public API contract | `docs/44-public-api-contract.md`, `reference/agentmem_ref/api/`, `schemas/api-*.schema.json` |
| Threat/security doctrine | `docs/15-memory-threat-model.md`, `docs/19-privacy-and-sensitivity-classifier.md`, `docs/29-actor-scope-consent-and-tenancy.md`, `docs/41-memory-isolation-domains-and-governed-crossing.md` |
| Evidence/provenance doctrine | `docs/16-source-trust-and-reputation.md`, `docs/30-memory-observability-and-audit-events.md`, `docs/policies/EVIDENCE_PROMOTION.md` |
| Lifecycle/correction/deletion doctrine | `docs/02-lifecycle-state-machine.md`, `docs/17-conflict-resolution-engine.md`, `docs/28-retention-deletion-and-tombstones.md`, `docs/31-recovery-rollback-and-replay.md` |
| Schema contracts | `schemas/*.schema.json`, registry doctrine in `docs/27-schema-registry-and-type-evolution.md` |
| Runtime Baseline succession | `docs/67-runtime-baseline-succession.md`, `reports/runtime/baseline-register.json` (authoritative published-version selector), version-specific `reports/runtime/baseline-v*.json`, `schemas/runtime-baseline-declaration.schema.json`, `scripts/check_runtime_baseline_equivalence.py` |
| Baseline-first execution posture | `docs/68-baseline-first-complete-architecture-execution.md`, `docs/BACKLOG.md`, `.qor/roadmaps/north-star-best-in-class/events.jsonl` (owner rulings seq 47-51) |
| Project governance | `GOVERNANCE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/CODEOWNERS` |

## Tier 3: Active Initiatives

**Live GitHub issues and PRs own current execution state.** This index records durable responsibilities, not a second manually maintained issue backlog.

| Responsibility | Primary owner | Posture at this evidence boundary |
|---|---|---|
| Working governed runtime and bounded release qualification | [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410) | Open; SQLite and the developer facade exist, but production 1.0 and heterogeneous multi-substrate qualification are not claimed |
| Public Gauntlet and runtime baseline convergence | [#635](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/635) | Open; exact benchmark-admission and successor-baseline requirements remain separately governed |
| Hierarchical/heterogeneous multi-representation composition | [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) | Open; defining product architecture, with an existing activation gate whose sequencing needs explicit review, not silent removal |
| Product/runtime/benchmark/architecture North Star | [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668) | Open; source of the accepted product-intent clarification |
| Competitive peer breadth | [#789](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/789) | Open; independent same-harness evidence, not vendor headline scores |
| Documentation discoverability and consolidation | [#797](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/797), merged [PR #798](https://github.com/MythologIQ-Labs-LLC/agent-memory/pull/798), merged [PR #803](https://github.com/MythologIQ-Labs-LLC/agent-memory/pull/803) | Catalog, filing validator and pruning are on `main`; remaining closure requires independently executed exact-head validation and repository-wide contradiction review |
| External / longitudinal evidence | [#361](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/361), [#388](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/388), [#408](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/408) | Independently gated; not substitutes for current executable runtime work |

**Closed gates no longer on the active critical path:** [#427](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/427) (SQLite canonical-substrate qualification, closed 2026-09-23) and [#440](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/440) (comparator dependency-pair qualification, closed 2026-09-24). Do not revive their old pending instructions. Historical resolution remains in the original issues and associated evidence.

## Tier 4: Active or Held Plan Artifacts

An active plan is authoritative **only within its explicitly pinned issue, source revision and approval boundary**; a completed plan is historical evidence, even if stored alongside current material. Do not maintain a second table of every completed sprint here.

- **Held:** `docs/plan-sprint4b-js-pama.md` and its accompanying research brief remain intentionally held until a correct remediation/discharge path is available.
- **Current execution:** derive the next accepted work package from [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410), [#635](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/635), [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) and [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668), checking live dependencies first.
- **Historical plans:** `docs/plan-*.md` and `docs/research-brief-*.md` preserve decisions and frozen evidence; use `docs/META_LEDGER.md` and `docs/BACKLOG.md` for their provenance and outcomes. Do not relocate these files merely to shorten directory listings.

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

Do not restate a date-sensitive, manually maintained list of already closed prerequisites here. At this snapshot:

1. **Finish security, deletion/correction, and runtime-succession safety work** under its live issue/PR owners. Correctness remains a prerequisite for any release.
2. **Prove useful integrated runtime behavior**, including governed composition across appropriate memory representations. [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) contains the experiment contract; review its broad #635/external-peer sequencing gate explicitly rather than treating it as an unchangeable product requirement.
3. **Qualify rather than assume:** use [#635](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/635), [#601](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/601) and the canonical benchmark dashboard for reproducible evaluation, with no benchmark-derived mutation authority.
4. **Reduce documentation drift** under [#797](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/797): code owns current runtime contracts, actual ADR files own decision status, the substrate inventory owns persistence maturity, and the generated dashboard owns numeric results.

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
