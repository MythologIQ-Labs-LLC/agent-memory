# Governance Index

**Last Reviewed**: 2026-09-02

A single authoritative map of every governance artifact in this project, organized
into six freshness tiers with explicit drift contracts. A stale entry here is
itself a Tier 1 drift bug, so the index is self-policing. See
`qor/references/doctrine-governance-index.md` for the model and contracts.

## Tier 1 — Canonical Source

MUST be current at every cycle close. Drift signal: wrong version / wrong state / missing recent entries.

| Artifact | Path | Freshness marker |
|----------|------|------------------|
| Meta Ledger | `docs/META_LEDGER.md` | Entries #1-#7; Sprint 1 seal Entry #8 (2026-09-02) |
| System State | `docs/SYSTEM_STATE.md` | Sprint 1 snapshot, iteration 1 |
| Concept | `docs/CONCEPT.md` | stable; hashed into genesis; owner decision: "supported runtime" is the 1.0 objective |
| Architecture Plan | `docs/ARCHITECTURE_PLAN.md` | Dependencies table and file tree synced at Sprint 1; risk grade L3 |
| Backlog | `docs/BACKLOG.md` | B1-B4 open; B5 complete |
| Feature Index | `docs/FEATURE_INDEX.md` | 3 entries, 3 verified (FX001-FX003) |
| Shadow Genome | `docs/SHADOW_GENOME.md` | 5 entries, 4 resolved |
| Process Shadow Genome | `docs/PROCESS_SHADOW_GENOME.md` | append-only JSONL of process events (capability shortfalls, gate skips, overrides) |
| Changelog | `CHANGELOG.md` | **absent** (GAP-REL-01, Sprint 8); register here when created |
| README | `README.md` | Conformance badge reworded to spec-scoped at Sprint 1 |
| Roadmap events | `.qor/roadmaps/agent-memory-1_0-completion/events.jsonl` | 32 events; 7 frontier nodes open |

## Tier 2 — Doctrine & Policy

Stable; changes are explicit doctrine events. Drift signal: rules contradict each other or operator memory.

| Artifact | Path |
|----------|------|
| ADR index (canonical status) | `docs/adr/README.md` (29 Accepted, 6 Proposed) |
| ADRs | `docs/adr/ADR-001` through `ADR-035` |
| PAMA foundation | `docs/pama/README.md`, `docs/04-governance-and-pama.md`, `docs/33-pama-decision-table.md` |
| Memory threat model | `docs/15-memory-threat-model.md` |
| Source rights policy | `docs/SOURCE_RIGHTS_POLICY.md` |
| Evidence promotion policy | `docs/policies/EVIDENCE_PROMOTION.md` |
| Project governance | `GOVERNANCE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/CODEOWNERS` |
| Schemas (contracts) | `schemas/*.schema.json` (58); registry at `docs/27-schema-registry-and-type-evolution.md` (8 listed, GAP-SC-04) |

## Tier 3 — Active Initiative

Live until close; ages out at substantiate. Drift signal: shipped feature still tracked as pending.

| Artifact | Path | Opened |
|----------|------|--------|
| Deep-audit research brief | `docs/RESEARCH_BRIEF.md` | 2026-09-01 |
| Agent Memory 1.0 roadmap | `.qor/roadmaps/agent-memory-1_0-completion/` | 2026-09-01 |
| QOR Agent proving ground | GitHub issue #332 | 2026-08-22 |
| Genesis branch | `feat/agent-memory-genesis` | 2026-09-01 |

## Tier 4 — Per-Plan Artifact

Live for plan duration; archived at substantiate. Drift signal: plan shipped but artifact still presents as open.

| Artifact | Path | Plan |
|----------|------|------|
| Sprint 1 plan (sealed) | `docs/plan-sprint1-install-correctness.md` | sprint1-install-correctness |
| Sprint 1 research brief | `docs/research-brief-sprint1-install-correctness-2026-09-01.md` | sprint1-install-correctness |

## Tier 5 — Reference Material

Informational, slow-drift. Drift signal: factual claims diverge from current code.

| Artifact | Path |
|----------|------|
| Numbered doctrine docs | `docs/00-glossary.md` through `docs/42-governed-mutable-memory-fabric.md`, including `docs/38-human-correction-ux-contract.md`, `docs/40-aligned-projects-and-intellectual-lineage.md`, `docs/41-memory-isolation-domains-and-governed-crossing.md` |
| Canonical architecture synthesis | `docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md` |
| Documentation map | `docs/README.md` (reachability gaps: GAP-DOC-04) |
| Implementation maps | `docs/05-repo-implementation-map.md`, `docs/39-implementation-ownership-map.md` (stale: GAP-DOC-05) |
| Profiles | `docs/profiles/` (29) |
| Programs | `docs/programs/` (runtime-evidence, memory-modules, hermes-integration, atlas-research) |
| PRD / RFC | `docs/prd/PRD-001`, `docs/rfcs/RFC-001` (gates stale: GAP-DOC-07) |
| Reference runtime README | `reference/README.md` (41 modules undocumented: GAP-DOC-03) |
| Configuration guide | `docs/CONFIGURATION.md` (phantom CLI subcommands: GAP-DOC-13) |
| Wiki source | `wiki-src/` (two weeks behind: GAP-DOC-06) |
| Research bibliography and explorations | `docs/23-research-bibliography.md`, `docs/research/`, `docs/explorations/` |

## Tier 6 — Archived

Frozen historical record. Drift signal: none (frozen).

| Archive | Path |
|---------|------|
| Audit records | `docs/audits/` (isolation, temporal-commitments) |
| Generated reports | `reports/` |
| Committed provider evidence fixtures | `reference/fixtures/component-qualification/*.json` |

## How to add a governance artifact

1. Create the file in the same commit that registers it here.
2. Add a row to the tier whose freshness contract matches the file's lifecycle.
3. Refresh **Last Reviewed** above.

## How to retire a governance artifact

1. Move the file to the Tier 6 archive path.
2. Move its row from its live tier to Tier 6 (or delete it if superseded).
3. Refresh **Last Reviewed** above.
