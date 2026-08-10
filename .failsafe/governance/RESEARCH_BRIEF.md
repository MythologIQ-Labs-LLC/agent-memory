# Research Brief

**Date**: 2026-08-10T22:30:00Z
**Analyst**: The QoreLogic Analyst
**Target**: `Knapp-Kevin/agent-memory` — open issue backlog vs. repository reality
**Scope**: All 25 open issues, docs 00–29, ADRs 001–020, audit slices 02–07A, schemas, fixtures, validator, CI state
**Constraint**: Observational only. Codex is performing a structural overhaul of the repository; no code or doc mutations are proposed for immediate execution.

---

## Executive Summary

The repository is a documentation/doctrine artifact (~15.2k lines: 31 docs, 20 ADRs, 6 audit slices, 2 schemas, 8 fixtures, 1 stdlib validator) — not a code library. Research found the backlog and the repo have **drifted apart in both directions**: 9 of 25 open issues appear already delivered on `main` but were never closed, while issue bodies propose doc filenames that collide with slots the audit process has since reserved (slice 6 reserved `docs/26–32`). Three unwritten docs (30/31/32) block three Proposed ADRs (017/018/019), and ADR-020 acceptance is gated on 8 executable demonstrations, none of which exist. The critical structural risk for planning is that **doc-number-based references are the repo's primary linking mechanism and they are already stale in issues and the README** — any plan must anticipate Codex's overhaul renumbering or relocating files.

## Findings

### F1. Repository state (verified)

- Branch `claude/agent-memory-dev-plan-oz24pw` is identical to `origin/main` at `bf0baa6` ("Contracts slice 7A"). No open PRs. 25 open issues, **0 closed issues** (number gaps 1, 2, 9, 16, 20 are PRs, e.g. issue #3 cites "PR #2").
- No QoreLogic governance state existed prior to this brief (no `.failsafe/`, no META_LEDGER) — this brief's ledger entry is the genesis entry.
- `scripts/validate_fixtures.py` runs and passes: `Validated 8 fixture(s).`, exit 0. It is stdlib-only but **does not read the JSON Schema files** — it duplicates constraints as Python constants (`REQUIRED_MEMORY_UNIT` at `scripts/validate_fixtures.py:25-34`, `VALID_STATES` at `:40-54`), so schema and validator can drift silently.
- **No CI exists.** `.github/` contains only `ISSUE_TEMPLATE/doctrine-consolidation-task.md`. Nothing runs the validator automatically.

### F2. Issue backlog triage (all 25 open issues, verified against tree)

**Group A — Already delivered on `main`, issue still open (9):**

| Issue | Delivered as |
|---|---|
| #10 threat model | `docs/15-memory-threat-model.md` + ADR-008 (Accepted) |
| #11 source trust | `docs/16-source-trust-and-reputation.md` + ADR-009 (Accepted) |
| #12 conflict resolution | `docs/17-conflict-resolution-engine.md` + ADR-010 (Accepted) |
| #13 temporal causality | `docs/18-temporal-causality-layer.md` + ADR-011 (Accepted) |
| #14 privacy classifier | `docs/19-privacy-and-sensitivity-classifier.md` + ADR-012 (Accepted) |
| #15 governed recall planner | `docs/26-governed-recall-planner.md` + ADR-013 (Proposed) |
| #17 schema registry | `docs/27-schema-registry-and-type-evolution.md` + ADR-014 (Proposed) |
| #21 retention/tombstones | `docs/28-retention-deletion-and-tombstones.md` + ADR-015 (Proposed) |
| #22 actor scope/tenancy | `docs/29-actor-scope-consent-and-tenancy.md` + ADR-016 (Proposed) |

Each needs a verification pass against its acceptance criteria (some criteria — e.g. fixture recommendations — may be partially met), then closure with a comment linking the delivering doc/commit.

**Group B — Doc exists as ADR only; companion doc reserved but unwritten (3):**

| Issue | ADR (Proposed) | Reserved doc slot (audit slice 6) |
|---|---|---|
| #23 observability/audit events | ADR-017 | `docs/30-memory-observability-and-audit-events.md` (cited at ADR-017:60) |
| #24 recovery/rollback/replay | ADR-018 | `docs/31-recovery-rollback-and-replay.md` (ADR-018:65) |
| #25 quality metrics/scorecard | ADR-019 | `docs/32-memory-quality-metrics.md` (ADR-019:64) |

These are the clearest next authoring unit: three docs unblock three ADR acceptance decisions.

**Group C — Tooling/automation, unblocked and cheap (2):** #3 CI gate for fixture validation (single workflow file, stdlib-only requirement already satisfied); #4 calibration report generator (`scripts/generate_calibration_report.py` + example report per `docs/09-calibration-protocol.md`).

**Group D — Doctrine authoring, not yet started (7):** #6 PAMA decision table; #7 adapter contracts (10 adapters enumerated); #18 interoperability profiles (6 profiles); #26 policy-as-memory; #27 memory economics/budget policy; #28 human correction UX contract; #30 durable decision memory profile (first entry of a new `docs/profiles/` family).

**Group E — Cross-repo, blocked on external repos (2):** #5 doctrine backlinks into `MythologIQ-Labs-LLC/{EvolveAI,CodeGenome,COREFORGE}` (outside this repo's write scope); #8 implementation ownership map (authorable here, but its content is claims about external repos that `docs/05-repo-implementation-map.md` currently names only abstractly — no URLs, versions, or code references).

**Group F — Deliberately deferred trackers (2):** #19 memory compiler (self-gated on #10, #11, #12, #17, #18); #29 multi-agent shared memory (self-gated on actor scope, privacy, interop profiles). Both request only a `docs/future/` note once gates clear.

### F3. Drift inventory (blueprint vs. reality)

There is no formal ARCHITECTURE_PLAN.md; the de-facto blueprint is `docs/07-integration-roadmap.md` + `docs/14-expanded-scope-recommendations.md` + the issue backlog. Cross-referencing:

| Claim (blueprint/issues) | Actual finding | Status |
|---|---|---|
| Issue #27 cites `docs/20-governed-recall-planner.md`, `docs/27-memory-quality-metrics.md` | Recall planner is `docs/26`; `docs/20` is memory-foundations; `docs/27` is schema registry | **DRIFT** — stale doc numbers in issue bodies |
| Issue #18 proposes `docs/22-interoperability-profiles.md` | `docs/22` is agentic-memory-theory | **DRIFT** — filename collision |
| Issues #23/#24/#25/#26/#28 propose `docs/25/26/27/28/30` respectively | Slots 25–29 consumed by audit rubric + slice 7A docs; slice 6 reserved 30/31/32 for observability/recovery/quality | **DRIFT** — issue-proposed numbering conflicts with reserved slots |
| Issues #10–#15, #17, #21, #22 request new docs | All nine delivered on `main` | **DRIFT** — issues not closed after delivery |
| README repository map (README:728-777) | Omits docs 15–19, 24–29, ADR-020; README:779 says "Numbers 15-19 remain intentionally available" though all five exist | **DRIFT** — stale README |
| `docs/07:140` deliverable `scripts/validate-fixtures.*` | Actual file `scripts/validate_fixtures.py` | DRIFT (cosmetic) |
| Schemas cover docs 26–29 concepts | `memory-unit.schema.json` has no sensitivity, scope/tenancy, consent, estimator-version, uncertainty, or tombstone fields | **DRIFT** — schemas predate the contracts slice |
| Roadmap Phase 5 lists 10 governed-uncertainty fixtures; README:846-857 lists 10 backlog fixtures | Lists overlap but are not identical; neither set exists in `fixtures/` | **DRIFT** — two unreconciled fixture backlogs |
| ADR-020 acceptance checklist (docs/07:285-298) requires 8 executable demonstrations | None exist | MATCH (gate correctly holding) |
| Audit queue (`docs/25:288-296`) items 6–7: schemas+fixtures, README/cross-doc consistency | Both unaddressed; slice 7A's "next evidence slice" (:64-72) enumerates the de-facto 7B scope | MATCH (queue accurate) |

### F4. Structural risk relevant to Codex's overhaul

The repo's linking convention is **positional doc numbers**, and they are already the dominant source of drift (issues, README, cross-doc references). If Codex's overhaul renumbers or relocates files, every issue body and cross-reference degrades further. Whatever structure Codex lands, the plan should treat **stable slugs/anchors (or a link-check gate)** as a prerequisite for resuming doctrine authoring, and should re-verify this brief's file:line citations after the overhaul merges.

## Recommendations (advisory, sequenced — for post-overhaul execution)

1. **P0 — Backlog hygiene (no repo changes):** verify and close Group A's 9 issues with delivery links; re-title/renumber the proposed filenames in Groups B and D issue bodies to match the slice-6 reservation (30/31/32) and whatever structure Codex lands.
2. **P0 — CI gate (#3):** one workflow running `validate_fixtures.py`; cheapest guard against drift during the overhaul. Coordinate timing with Codex.
3. **P1 — Docs 30/31/32 (#23, #24, #25):** unblocks ADR-017/018/019 reconsideration; matches the audit queue's own sequencing.
4. **P1 — Evidence slice 7B:** reconcile both schemas with docs 26–29, add decision-receipt and audit-event schemas, reconcile the two fixture backlogs into one list, add governed-uncertainty fixtures; make the validator read the JSON Schemas instead of duplicating constants.
5. **P2 — Doctrine authoring wave (#6, #7, #18, #26, #27, #28, #30):** ordered by dependency — adapter contracts (#7) before interop profiles (#18); policy-as-memory (#26) and economics (#27) before decision profile (#30).
6. **P2 — Calibration generator (#4)** after fixture/schema reconciliation so the report consumes stable shapes.
7. **P3 — Cross-repo (#5, #8)** when external repos are in scope; **#19 and #29 remain gated** per their own criteria (gates for #19 are now partially cleared: #10–#12 and #17 delivered, #18 outstanding).

## Updated Knowledge

`memory/failsafe-bridge.md` does not exist in this project and is not applicable (no bridge component). This brief and the META_LEDGER genesis entry are the persistent knowledge artifacts.

---

_Research complete. Findings are advisory — implementation decisions remain with the Governor._
