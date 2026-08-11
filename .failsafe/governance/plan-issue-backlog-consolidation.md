# Plan: Issue Backlog Consolidation — agent-memory end-to-end development plan

**Status**: ADVISORY / OBSERVATIONAL. Codex is performing a structural overhaul
of this repository. Nothing in this plan executes until that overhaul lands and
Milestone 0's re-baseline gate passes. Grounded in
`.failsafe/governance/RESEARCH_BRIEF.md` (ledger entry #1).

**Design stance (Simple Made Easy)**: the backlog's dysfunction is complecting —
four independent concerns are braided together and must be planned apart:

1. **Tracker state** (which issues are open) is braided with **delivery state**
   (which docs exist): 9 delivered issues remain open.
2. **Document identity** is braided with **ordering**: positional doc numbers
   (`docs/26-…`) are the linking mechanism, and every renumbering breaks issues,
   README, and cross-references. Identity should be a stable slug; order is a
   presentation concern.
3. **Schema truth** is braided with **validator code**:
   `scripts/validate_fixtures.py` re-states schema constraints as Python
   constants instead of reading `schemas/*.json`. One source of truth should
   drive both.
4. **Doctrine maturity** (ADR status) is correctly separated from
   implementation maturity (`docs/adr/README.md`) — the plan preserves that
   separation and never advances an ADR by fiat.

Each milestone removes one braid before adding new material.

---

## Open Questions (Governor decisions — flagged, with recommended defaults)

1. **Doc identity after the overhaul**: does Codex's new structure keep
   positional numbering, or can the repo adopt stable slugs (number-free
   filenames or permanent anchors) with ordering held in a single index?
   *Recommended*: stable slugs + generated index; positional numbers are the
   root cause of most observed drift. If Codex keeps numbers, substitute a CI
   link-check for renaming.
2. **CI timing**: may the fixture-validation workflow (#3) land during the
   overhaul (it guards Codex's own changes) or only after? *Recommended*:
   during, coordinated with Codex — it is one additive file and validates
   whatever tree exists.
3. **Group A closure policy**: close the 9 delivered issues immediately with
   delivery links, or only after a per-issue acceptance-criteria verification
   pass? *Recommended*: verify-then-close; several criteria (e.g. "conformance
   fixture recommendations") may be only partially met and should spawn small
   follow-up issues rather than silently closing.
4. **ADR-020 demonstration venue**: the 8 executable demonstrations gating
   ADR-020 acceptance (`docs/07-integration-roadmap.md:285-298`) — built as an
   in-repo reference harness, or delegated to implementation repos (EvolveAI,
   CodeGenome)? *Recommended*: minimal in-repo harness (stdlib Python, same
   discipline as the validator); external repos are outside this repo's write
   scope and cadence.
5. **`docs/profiles/` family**: issue #30 introduces a new document family.
   Confirm the overhaul's structure has a place for profiles before authoring.

---

## Milestone 0: Post-overhaul re-baseline (gate — no authoring past it until green)

### Affected Files

- `.failsafe/governance/RESEARCH_BRIEF.md` — re-verify all file:line citations
  against the post-overhaul tree; append a delta section
- `.failsafe/governance/META_LEDGER.md` — ledger entry recording the re-baseline

### Changes

- Map every artifact named in this plan (docs 00–29, ADRs, schemas, fixtures,
  validator) to its post-overhaul path. Produce a two-column old→new table in
  the brief's delta section.
- Re-run `python3 scripts/validate_fixtures.py` (or its successor) to confirm
  the baseline still passes.
- Re-triage the 25 issues against the new tree: confirm Group A (delivered) is
  still 9, and that Codex's overhaul did not itself deliver or invalidate
  further issues.

### Verification (gate criteria, checked first)

- Old→new path map covers 100% of plan-referenced artifacts; zero unresolved.
- Validator exit 0 on the post-overhaul tree.
- Issue triage delta reviewed and appended to the brief.

## Milestone 1: Stabilize — tracker truth and drift guards

Resolves: #3, plus closure of #10, #11, #12, #13, #14, #15, #17, #21, #22.

### Affected Files

- `.github/workflows/fixtures.yml` — new; runs the fixture validator
- GitHub issue bodies/comments (no repo files) — Group A closures, Group B/D
  renumbering corrections

### Changes

- **CI gate (#3)**: single workflow, PRs + pushes to `main`, Python stdlib
  only, runs the validator and (if Milestone 3's schema-driven validation has
  not yet landed) nothing else. Document the command in the workflow summary
  per the issue's acceptance criteria.
- **Group A verify-then-close**: for each of the 9 delivered issues, check its
  acceptance criteria against the delivering doc; close with a comment linking
  doc + commit; spawn one follow-up issue per genuinely unmet criterion
  (expected: fixture-recommendation criteria on #15/#17/#21/#22 fold into
  Milestone 3's fixture work rather than new issues).
- **Reference repair**: edit remaining open issue bodies (#18, #23, #24, #25,
  #26, #27, #28) to reference post-overhaul paths / reserved slots
  (observability, recovery, quality-metrics docs) instead of stale numbers.
- **Link guard**: per Open Question 1 — either adopt stable slugs or add a
  markdown link-check job so positional drift cannot recur silently.

### Verification

- Workflow green on an unmodified tree before merge (issue #3 criterion).
- Every closed issue's closing comment names the delivering artifact.
- Zero open-issue bodies referencing nonexistent paths (link-check or manual
  sweep recorded in ledger).

## Milestone 2: Evidence — unblock Proposed ADRs and reconcile schemas/fixtures

Resolves: #23, #24, #25, #4; positions ADR-013–019 for reconsideration.
Order follows the repo's own audit queue (`docs/25:288-296`) and slice 7A's
declared next-evidence list (`docs/audits/governed-uncertainty/07a:64-72`).

### Affected Files

- `docs/30-memory-observability-and-audit-events.md` — new (slot reserved by
  audit slice 6; satisfies #23 with `schemas/memory-audit-event.schema.json`)
- `docs/31-recovery-rollback-and-replay.md` — new (#24)
- `docs/32-memory-quality-metrics.md` — new (#25)
- `docs/audits/governed-uncertainty/07b-evidence-and-schemas.md` — new audit
  slice recording baseline → remediation, same format as slices 2–7A
- `schemas/memory-unit.schema.json` — add sensitivity, scope/tenancy, consent,
  estimator-version, uncertainty, tombstone fields (reconcile with docs 26–29)
- `schemas/conformance-report.schema.json` — add estimator/policy-version and
  receipt fields (roadmap Phase 8 alignment)
- `schemas/memory-audit-event.schema.json` — new (#23)
- `schemas/decision-receipt.schema.json` — new (roadmap Phase 8, 16-field
  receipt)
- `fixtures/` — one reconciled backlog: merge README:846-857's 10 cases with
  roadmap Phase 5's 10 governed-uncertainty cases into a single deduplicated
  list; author the union incrementally, governed-uncertainty set first
- `scripts/validate_fixtures.py` — read constraints from `schemas/*.json`
  instead of Python constants (removes braid #3); keep stdlib-only
- `scripts/generate_calibration_report.py` + example report — new (#4),
  consuming the reconciled schemas
- `docs/adr/ADR-013…019` — status changes only if their audit-slice evidence
  supports Accepted; recorded per ADR in slice 7B

### Changes

- Author docs 30/31/32 to the same rubric as docs 26–29 (governed-uncertainty
  conformance sections included), each linking its ADR.
- Schema reconciliation is **values-first**: schemas are the immutable
  contract; the validator becomes a thin interpreter of them. Fixture
  `expected_behavior` semantics remain out of validator scope (doctrine
  conformance is the conformance harness's job, not shape validation's).
- Calibration generator (#4) emits Markdown, distinguishes
  PERSIST/EVAPORATE/TRAP, flags trap-class crystallization as failure, includes
  `scope_of_validity`.

### Verification (listed first per phase discipline; TDD-equivalent here is fixtures-before-features)

- New/changed schemas ship with at least one fixture exercising every new
  required field; validator (schema-driven) passes the full fixture set in CI.
- `python3 scripts/validate_fixtures.py` and
  `python3 scripts/generate_calibration_report.py --help` both exit 0 in CI.
- Slice 7B checklist complete, including the three process boxes prior slices
  left unticked (branch diff reviewed, mergeability verified, merge by exact
  head SHA).
- Each ADR status change cites its evidence section; ADR-020 stays Proposed
  (its 8-demonstration gate is Milestone 3+ scope, per Open Question 4).

## Milestone 3: Doctrine and ecosystem — authoring wave, cross-repo, gated futures

Resolves: #6, #7, #18, #26, #27, #28, #30; then #5, #8; leaves #19, #29 as
correctly-gated trackers until their own criteria clear.

### Affected Files

- `docs/` (post-overhaul paths; slugs per Open Question 1):
  - PAMA decision table (#6) — mutation type × risk × evidence × reversibility
    → authority outcome; before/after + ledger requirement per example;
    links ADR-004
  - Adapter contracts (#7) — 10 adapters, each: input, output, guarantees,
    failure modes; one common handoff-record shape (a value, not a protocol);
    worked examples for identity, scoring, PAMA, certification
  - Interoperability profiles (#18) — 6 profiles; depends on #7's contracts,
    so authored after
  - Policy-as-memory (#26); memory economics/budget policy (#27) — both feed
    #30
  - Human correction UX contract (#28)
  - `docs/profiles/durable-decision-memory-profile.md` (#30) — first profile;
    authored last in the wave, consuming #26/#27 and Milestone 2's receipt
    schema
- `fixtures/` — conformance fixture recommendations required by #26 (stale
  policy retention) and #30 (decision memory), added alongside their docs
- External repos (#5 backlinks, out of this repo's write scope) and ownership
  map (#8) — authorable here only for the map document; every external claim
  marked verified/unverified, since `docs/05` currently names all 10 systems
  abstractly with no URLs or code references

### Changes

- Authoring order inside the wave (dependency, not preference):
  #6, #7 → #18 → #26, #27 → #28 → #30.
- #8's ownership map: primary owner, secondary consumers, implementation
  status per component; uncertain ownership marked explicitly (issue's own
  criterion — keep claims and evidence unbraided).
- #19 (memory compiler) and #29 (multi-agent shared memory): when their listed
  gates clear (for #19: #18 is the last outstanding gate; for #29: #18 plus
  delivered actor-scope and privacy docs), add the `docs/future/` note each
  issue requests — nothing more; both stay out of core components.

### Verification

- Each authored doc satisfies its issue's acceptance-criteria checklist
  verbatim; the closing comment quotes the checklist with links.
- New fixtures pass CI; fixture count and classes recorded in the conformance
  test plan.
- #18 not started before #7 merged; #30 not started before #26/#27 merged
  (enforced by issue dependencies, not memory).
- Wave concludes with a cross-document consistency pass (audit queue item 7):
  README map regenerated, zero dangling references.

---

**CI commands validating this plan** (current names; remap in Milestone 0):

```
python3 scripts/validate_fixtures.py
python3 scripts/generate_calibration_report.py --help   # exists after Milestone 2
```
