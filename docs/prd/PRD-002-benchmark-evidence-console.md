# PRD-002: Benchmark Evidence Console

Status: **Draft / Future post-RC feature**

Parent: #696  
Related: #574, #600, #601, #668, #694  
Architecture decision: proposed ADR-041

## Product intent

Build a benchmark reporting and evidence-exploration UI that lets a human understand Agent Memory's actual measured position without manually reading raw benchmark JSON, Markdown reports, workflow artifacts, and repository history.

The product is not a leaderboard. It is a **benchmark evidence console**.

It must help a user answer:

1. Where is Agent Memory strong, weak, unchanged, or unmeasured?
2. Which systems can legitimately be compared on this result?
3. What changed between Agent Memory revisions or architecture milestones?
4. Why did a score move?
5. What evidence supports the displayed claim?
6. What remains unknown?
7. What result can be shared without losing methodology context?

The console preserves the existing benchmark doctrine:

~~~text
benchmark score != authority
published vendor score != same-harness comparator
historical self-comparison != market position
blocked / not_run / unsupported / evidence_gap != zero
different benchmark planes != one aggregate score
different metric semantics != comparable percentages
no universal memory-health scalar
~~~

This feature is intentionally outside the current RC critical path.

## Problem

The repository already has native benchmark outputs, deterministic normalization, scorecards, same-harness lanes, execution identities, longitudinal evidence, published-reference evidence, and coverage metadata.

The remaining problem is human comprehension.

A simple question such as "Is Agent Memory better than Mem0 at long-memory retrieval?" can require discovering:

- which LongMemEval dataset/profile is in use;
- session versus turn plane;
- retrieval versus end-to-end QA;
- exact k;
- whether both systems ran under the same harness;
- whether input digest, selection, and budget match;
- whether a number came from a vendor publication instead;
- which Agent Memory revision generated the result;
- whether a later protocol change invalidates direct longitudinal comparison.

The UI must make that reasoning visible rather than flattening it into a convenient but false score.

## Primary users

### Technical evaluator / prospective adopter

Needs to understand competitiveness, weaknesses, scale, currentness, methodology quality, and evidence gaps quickly enough to support an architecture decision.

### Agent Memory maintainer

Needs to know whether a runtime tranche improved its target behavior, whether anything regressed, which failures dominate, and whether before/after evidence is legitimately comparable.

### Benchmark/research auditor

Needs exact benchmark, input, version, model, evaluator, execution, and provenance identity, plus an explanation of why a comparison is or is not valid.

### Contributor / benchmark integrator

Needs to see unmeasured capability areas, understand catalog/adapter requirements, and learn why a run failed comparison eligibility.

### Product or engineering decision-maker

Needs concise, defensible statements about strengths, weaknesses, progress, and remaining evidence required before strong market claims.

### Recipient of a shared result

May enter from a deep link and needs to know exactly what snapshot, comparison, methodology, and evidence they are viewing.

## Jobs to be done

### JTBD-1: Assess current position

When I open the console, I want to understand Agent Memory's current measured posture in a few minutes so I know where to investigate deeper.

### JTBD-2: Compare systems honestly

When I compare Agent Memory with another system, I want the application to prevent or clearly label invalid comparisons so I do not mistake unrelated scores for head-to-head evidence.

### JTBD-3: Understand a benchmark

When I inspect a benchmark, I want its own metrics, profile, methodology, and limitations rather than a generic normalized score.

### JTBD-4: Understand change

When Agent Memory changes, I want to see which comparable metrics moved and which comparisons became invalid so I can tell what the architecture change actually accomplished.

### JTBD-5: Diagnose failure

When a benchmark regresses or exposes a weakness, I want to move from aggregate result to failure cluster to representative cases and evidence.

### JTBD-6: Verify a claim

When I see a result, I want to trace it through normalized output, native report, execution identity, input binding, and lane/profile.

### JTBD-7: Find evidence gaps

When planning evaluation work, I want to see what important capability dimensions remain unmeasured.

### JTBD-8: Share a defensible snapshot

When I share a result, I want the recipient to see the same immutable evidence context I saw.

# Complete user journeys

## Journey A: "Is Agent Memory good?"

### Entry

The user enters from the project README, a public benchmark link, or the console root.

### Orientation

The page opens with a snapshot identity bar:

~~~text
Agent Memory Benchmark Evidence
Snapshot 2026-10-07.4
Agent Memory 2d852d3
Runtime Baseline vN
Evidence through 2026-10-07
Current snapshot
~~~

Below it is a North Star summary organized by capability rather than benchmark.

Example:

~~~text
Retrieval        Competitive
Currentness      Material weakness / formal baseline pending
Scale            Evidence gap
Isolation        Strong measured evidence
Deletion         Strong measured evidence
Reasoning / QA   Not yet same-harness measured
Action memory    Not measured
Coding reuse     Not measured
~~~

Each statement is a **claim card** containing:

- capability;
- current posture;
- strongest supporting metric;
- evidence class;
- comparator coverage;
- timestamp/revision;
- Inspect evidence action.

### Select a capability

Selecting Currentness opens relevant evidence across MESA, LongMemEval knowledge-update/latest-first, and longitudinal Agent Memory evidence while keeping metrics distinct.

The application does not average them.

### Ask why

A "Why this posture?" inspector explains:

- which rows support the posture;
- which evidence is same-harness;
- which is longitudinal;
- what remains unmeasured;
- what prevents a stronger claim.

## Journey B: "Compare Agent Memory with Mem0"

### Enter Compare

A persistent context bar shows selected systems, benchmark scope, evidence class, and revision.

### See valid comparison sets

Results are grouped by exact comparison identity.

Example:

~~~text
LongMemEval_S / session / retrieval parity v2
EXACT SAME-HARNESS

Metric                 Agent Memory   Mem0       Delta
Recall all @5          0.823          0.809      +0.014
Recall all @10         0.893          0.883      +0.010
nDCG any @10           0.878          0.841      +0.037
Latest gold first      0.457          0.443      +0.014
~~~

Published market references appear in a visually separate section and cannot inherit the same-harness treatment.

### Ask why comparable

A first-class "Why comparable?" action shows the fields that match:

- benchmark revision;
- input digest;
- plane/profile;
- selection and sample count;
- metric definition;
- retrieval/context budget where applicable;
- answer/judge identity where applicable.

### Attempt an invalid comparison

If the user tries to combine Agent Memory retrieval Recall@5 with Hindsight end-to-end QA accuracy, the product refuses a numeric delta and explains the semantic mismatch.

It should offer useful next actions such as "View methodology side by side" or "Find same-harness evidence".

## Journey C: "What does this benchmark actually measure?"

The Benchmarks area shows benchmark families with purpose, measured dimensions, current Agent Memory status, comparator coverage, latest accepted run, and missing surfaces.

Opening a benchmark/profile shows:

1. What this measures
2. Results
3. Methodology and evidence

Native metrics remain native.

For a profile such as LongMemEval_S session retrieval, the header explicitly names benchmark, profile, plane, lane, and accepted state.

Methodology expansion includes dataset/input identity, selection, sample count, exclusions, k/budget, answer/judge where applicable, system versions, deviations, and upstream source.

## Journey D: "Did the latest architecture change help?"

The Changes area shows a chronological architecture/evidence timeline.

The user selects Before and After revisions.

The comparison engine separates:

- comparable;
- related/adapted;
- first baseline;
- not comparable.

Example:

~~~text
Comparable changes

Metric                 Before    After     Delta
Recall all @5          .823      .901      +.078
Currentness            .200      .760      +.560
Search p95             11.9ms    18.4ms    +6.5ms regression

New evidence
BEAM 1M                first baseline

Not comparable
LongMemEval QA         evaluator changed
~~~

A protocol change creates a visible break in a longitudinal chart rather than a false continuous trend.

An architecture context inspector shows related issue/PR/ADR, declared intent, runtime baseline change, replayed lanes, and explicit accepted regressions if any.

The UI labels these as associated transition evidence and does not infer causality merely from chronology.

## Journey E: "Why did currentness fail?"

A weak metric or regression exposes an "Explore failures" action.

If row-level failure attribution exists, the Failure Explorer can group by stage/category such as:

- ranking/fusion;
- temporal applicability/currentness;
- identity/slot resolution;
- candidate generation;
- admission;
- runtime;
- unclassified.

If attribution is absent, rows are "not classified", not silently placed in "other".

Filters include benchmark, system, revision, metric/outcome, failure stage, case type, currentness/update category, runtime failure, and admission/refusal state.

Case detail shows only evidence that actually exists, such as:

- case id;
- expected target;
- retrieved candidates;
- rank;
- route provenance;
- admission decision;
- currentness evidence;
- outcome;
- failure classification;
- native evidence pointer.

Filter state survives case drill-down and return.

## Journey F: "Can I verify this claim?"

Every score/state exposes Inspect evidence.

The inspector shows:

~~~text
Displayed metric
  -> normalized run manifest
  -> native benchmark report
  -> execution identity
  -> lane/profile
  -> input digest
  -> system revision/configuration
  -> workflow/run evidence
~~~

For a comparison, it also explains which comparison-identity fields matched.

The user can follow repository evidence links from the inspector.

## Journey G: "What should we measure next?"

Coverage presents capability dimensions against benchmark/evidence families.

Cell states include:

- measured;
- partial;
- not_measured;
- evidence_gap;
- blocked;
- unsupported;
- not_applicable.

Selecting a gap explains what is missing, whether a benchmark is already planned, whether the gap is protocol/access/implementation/evidence, and the related issue where available.

Coverage is a planning aid, not an automatic priority engine.

## Journey H: "Share exactly what I am seeing"

Share creates or resolves a URL bound to an immutable generated snapshot identity plus selected systems/profile/revisions/filter state needed for interpretation.

A recipient sees a clear historical-snapshot banner if newer evidence exists.

Future export may include:

- copy link;
- CSV for a valid visible table;
- JSON snapshot metadata;
- print/PDF-friendly report.

Exports must preserve evidence/comparability metadata rather than emitting naked numbers alone.

# Information architecture

The user-journey review changes the information architecture from technical pages to user intent.

## Overview

Purpose: assess current position.

Primary actions: inspect capability, compare systems, inspect a gap, open a material weakness.

## Compare

Purpose: answer system-versus-system questions under fail-closed comparability.

Primary actions: select systems, select benchmark/profile, inspect why comparable/not comparable, open evidence.

## Benchmarks

Purpose: understand one benchmark/profile in native semantics.

Primary actions: browse benchmark families, select profile/plane, inspect methodology, inspect runs.

## Changes

Purpose: understand revision-to-revision and architecture impact.

Primary actions: select before/after, inspect valid deltas, identify regressions/new evidence/non-comparability, inspect architecture transition.

## Failures

Purpose: diagnose aggregate weaknesses.

Primary actions: filter failure cases, inspect clusters, drill into case evidence.

## Coverage

Purpose: understand what remains unknown.

Primary actions: inspect evidence gap, identify planned benchmark, inspect related issue.

## Evidence

Purpose: browse/search runs and inspect provenance directly.

Primary actions: find a run, inspect evidence chain, inspect configuration, open canonical source artifact.

Short nouns are suitable for navigation. Entry-page actions should use user-language verbs such as "Compare systems", "Track changes", and "Explore failures".

# Persistent application frame

## Header

Always show:

- product name;
- snapshot/current-state label;
- Agent Memory revision;
- evidence as-of date;
- runtime baseline identity when available.

Global actions:

- snapshot selector/current;
- share;
- methodology/glossary.

## Context bar

Pages with selectable comparison context keep important filters visible.

Example:

~~~text
Systems [Agent Memory] [Mem0]
Benchmark [LongMemEval_S]
Profile [Retrieval parity]
Plane [Session]
Evidence [Same-harness only]
~~~

## Main content

Use a data-dense desktop layout with responsive collapse.

Avoid one oversized vanity metric per screen.

## Evidence inspector

Use a side drawer/panel for provenance, definitions, and comparability explanations when possible so the user does not lose position in a matrix.

A full-page Run Detail remains available for deep evidence inspection.

# Visual design specification

## Character

The console should feel like a serious engineering observability product:

- precise;
- calm;
- data-dense;
- low decoration;
- strong tabular comparison;
- readable methodology;
- explicit evidence state.

It should not resemble a marketing leaderboard or a collection of giant score cards.

## Three visual layers

### Layer 1: posture

Fast summary: strong/weak/unknown, ahead/behind/tied when valid, regression/improvement when valid.

### Layer 2: measurement

Exact values, distributions, deltas, and native benchmark interpretation.

### Layer 3: evidence

Methodology, provenance, revisions, input binding, and comparison identity.

Every important result must allow movement from posture to evidence.

## Orthogonal badge systems

Outcome/status and evidence/comparability must be separate.

Outcome examples:

- Ahead
- Behind
- Tie
- Improved
- Regressed
- Mixed
- Unknown

Evidence examples:

- Same harness
- Longitudinal
- Published reference
- Adapted diagnostic
- Not comparable
- Evidence gap
- Not measured
- Blocked
- Unsupported

A result may therefore be "Ahead · Same harness" or "High published score · Not comparable" without conflating the concepts.

## Chart grammar

Good fits:

- grouped bars for one metric within one exact comparison set;
- line/slope charts for valid longitudinal runs under unchanged protocol;
- scatter plots for compatible quality/latency tradeoffs;
- distributions where native evidence supports them;
- labeled coverage heatmaps;
- failure-category bars.

Avoid:

- radar charts mixing unrelated scales;
- pie charts for benchmark quality;
- combined same-harness/published-reference bars as peers;
- longitudinal lines through protocol changes;
- normalized universal score charts.

## Tables

Tables are first-class.

Support:

- sticky metric/system labels;
- sorting within valid groups;
- metric definitions;
- evidence badge;
- directional delta;
- row expansion;
- keyboard navigation.

## Accessibility

Minimum requirements:

- WCAG AA contrast;
- keyboard-operable tables, filters, drawers, and tabs;
- no color-only status;
- chart summaries;
- focus preservation during drill-down;
- reduced-motion support;
- semantic tables;
- explicit units.

# Core interaction requirements

## R1. Fail-closed comparison

The frontend does not decide comparability from labels or values.

The catalog/shared comparison contract provides explicit comparison state.

No valid comparison state means no numeric delta.

## R2. Native metric preservation

Every normalized dimension retains a path to native metric name and definition.

The UI may group by capability but may not inflate semantics, such as turning retrieval recall into "memory accuracy".

## R3. Explicit missing states

At least:

- not_run;
- not_measured;
- evidence_gap;
- blocked;
- unsupported;
- not_applicable;
- non_comparable;
- absent.

Do not render these as 0, NaN, empty string, or silent omission where absence matters.

## R4. No automatic best-in-class verdict

The UI may state that Agent Memory is ahead/behind on a particular valid comparison and may surface incomplete capability evidence.

It may not synthesize a universal winner.

## R5. Snapshot identity

Every shareable evidence state binds a deterministic snapshot/catalog identity.

A current mutable route may exist; historical share links must remain immutable.

## R6. Protocol discontinuities are visible

Invalid longitudinal transitions produce a visual break.

## R7. Evidence inspection is contextual

Opening evidence from a matrix preserves benchmark/system/metric context.

## R8. Material filters are visible

Interpretation-changing filters remain in the context bar/header.

## R9. URL-addressable state

Important selections should be linkable, including systems, benchmark/profile, run, revision pair, failure filter, and snapshot.

# Data requirements

The UI consumes a generated versioned catalog rather than arbitrary repository files.

Conceptual artifact:

reports/benchmarks/ui/catalog.json

Required domains:

- snapshot identity;
- benchmark registry;
- metric registry;
- system registry;
- runs;
- comparison sets;
- published references;
- longitudinal transitions;
- architecture milestones;
- coverage;
- evidence index;
- optional row-level chunk manifest.

## Benchmark registry

Each benchmark/profile declares stable id, display name, source/revision, purpose, task profile/plane, selection/sample semantics, metric ids, upstream source, and methodology summary.

## Metric registry

Each metric declares stable id, display/native label, unit, value type, direction, capability category, profile scope, whether delta is meaningful, and definition/help text.

## System registry

Each system declares stable id, display name, role/class, exact run revision, adapter/provider configuration identity, source/reference metadata, and evidence availability.

## Comparison sets

The builder records membership and rationale.

Identity may include benchmark, dataset revision, input digest, profile/plane, selection, sample count, budget, evaluator identity, and metric semantics.

## Evidence index

Every rendered value/state resolves to committed evidence or an explicitly defined deterministic derivation.

## Row-level chunks

Large per-case evidence remains outside the main catalog and is loaded through deterministic indexes.

# Empty, blocked, and degraded states

## No comparator

Show that no same-harness comparator is accepted. Published context may appear separately.

## Blocked benchmark

Show blocker and owning issue where known.

## Unsupported benchmark

Explain whether the limitation belongs to Agent Memory, comparator, or protocol mismatch.

## Failed attempted run

Do not silently replace the previous accepted run. Show previous accepted evidence and failed attempt separately.

## Stale catalog

If known, show that evidence is older than the repository/runtime revision.

## Partial row evidence

Failure Explorer declares available fields/coverage instead of presenting incomplete attribution as complete.

# Responsive behavior

Desktop is the primary deep-analysis target.

Tablet/mobile must support Overview, claim inspection, basic result tables, evidence inspection, and shared snapshot consumption.

Wide matrices may switch to selected-pair comparison, horizontal accessible tables, or stacked metric rows.

# User-story acceptance scenarios

## US-01 First-time evaluator

Within one screen, a new evaluator can distinguish strengths, weaknesses, unmeasured areas, same-harness evidence, and published references.

## US-02 Valid system comparison

Agent Memory and Mem0 same-harness rows display shared metrics/deltas and can explain why the comparison is valid.

## US-03 Invalid metric comparison

Agent Memory retrieval recall and published Hindsight QA accuracy cannot produce a numeric delta and the UI explains why.

## US-04 Longitudinal protocol break

A profile/evaluator change creates a visible discontinuity and blocks invalid delta/trend calculation.

## US-05 Regression diagnosis

A regressed metric with classified row evidence can be explored by failure cluster and case.

## US-06 No failure classification

Unclassified rows remain explicitly unclassified.

## US-07 Evidence trace

Any displayed same-harness score can identify normalized manifest, native report, execution identity, profile/lane, input binding, and system revision.

## US-08 Evidence-gap planning

An unmeasured capability appears as an evidence state rather than failed score.

## US-09 Immutable share

A historical share link remains bound to original evidence after newer evidence exists.

## US-10 Published-reference isolation

Published vendor scores and same-harness results are visibly and structurally distinct.

## US-11 Native semantics

Benchmark Explorer preserves native metric name/definition.

## US-12 New comparator integration

A run that fails eligibility remains inspectable but is excluded from invalid deltas and carries the reason.

# Success criteria

A competent user can answer without repository archaeology:

1. Where is Agent Memory strong, weak, mixed, or unmeasured?
2. Which competitive claims are same-harness?
3. Which are published references?
4. What benchmark/profile produced a result?
5. What changed between comparable revisions?
6. Why is a result comparable or non-comparable?
7. What evidence supports a displayed value?
8. What capabilities remain unmeasured?
9. What failure class dominates a weakness when classification exists?
10. Can this exact evidence state be shared reproducibly?

Hard integrity criteria:

- zero UI-computed deltas across non-comparable rows;
- zero missing-state-to-zero coercions;
- zero automatic universal aggregate score;
- every displayed numeric result has an evidence pointer;
- every head-to-head claim exposes comparison identity;
- every shareable historical snapshot is revision-bound.

# Non-goals

The first implementation does not:

- execute benchmarks;
- mutate benchmark evidence;
- edit or approve runtime governance decisions;
- create authority from benchmark results;
- automatically declare a universal winner;
- replace native benchmark artifacts;
- replace canonical dashboard/scorecard generation;
- participate in Agent Memory runtime availability;
- require a database or authentication;
- become an RC gate.

# Delivery plan

## F0 Product/architecture definition

PRD-002, ADR-041, #696, and implementation issues.

## F1 Projection contract

Deliver versioned UI catalog schema, benchmark/metric/system registries, comparison-set projection, evidence index, snapshot identity, deterministic builder, and stale-output check.

No frontend required.

## F2 Core static console

Deliver application shell, Overview, Compare, Benchmarks, Evidence Inspector, Coverage, shareable URL state, accessible desktop and basic responsive behavior.

## F3 Change intelligence

Deliver architecture milestone registry, revision-pair selection, valid longitudinal deltas, protocol-discontinuity handling, and architecture-impact view.

## F4 Failure intelligence

Deliver row-level chunk/index contract, Failure Explorer, filter persistence, case detail, and attribution display.

## F5 Optional hosted evolution

Only if later requirements justify private evidence, remote aggregation, very large row stores, or multi-repository views.

F1-F4 must not assume F5.

# Open product questions

1. Should public deployment live under GitHub Pages, the MythologIQ site, or both?
2. Should architecture milestones be derived from repository records or a small generated registry?
3. What minimum row-level schema is useful across benchmark families?
4. Which published references should be committed as source metadata versus refreshed externally?
5. Should PDF/static report generation become a first-class export?
6. Should a future public console hide some engineering diagnostics while sharing the same catalog?

These questions must not create separate sources of benchmark truth.

# Relationship to active work

This feature is downstream of the benchmark/evidence program.

Current RC/runtime work remains higher priority.

The benchmark program must not wait for this UI. The UI must consume the evidence contracts established by that program rather than reshape benchmark design around frontend convenience.


# Reference wireframes

These are structural wireframes, not final visual design. They establish hierarchy and interaction density for #699.

## Overview

~~~text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Agent Memory Benchmark Evidence    CURRENT · snapshot 2026-10-07.4        │
│ AM 2d852d3 · Runtime Baseline vN · Evidence through Oct 7       [Share]    │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Overview     │ North Star                                                   │
│ Compare      │ ┌────────────┬────────────┬────────────┬───────────────┐    │
│ Benchmarks   │ │ Retrieval  │ Currentness│ Scale      │ Reasoning / QA│    │
│ Changes      │ │ Competitive│ Weak       │ Gap        │ Not measured  │    │
│ Failures     │ │ LME .823   │ AMB .200   │ BEAM —     │ Same-harness —│    │
│ Coverage     │ │ Same harness│ Diagnostic │ Evidence gap│ Not measured │    │
│ Evidence     │ └────────────┴────────────┴────────────┴───────────────┘    │
│              │                                                              │
│              │ Material findings                                            │
│              │ Currentness needs attention        [Why?] [Explore failures] │
│              │ LME session retrieval competitive [Compare systems]          │
│              │ BEAM scale not measured            [View coverage gap]        │
│              │                                                              │
│              │ Recent architecture/evidence changes                          │
│              │ 2d852d3  Baseline-first posture                              │
│              │ ca0f9a7  Runtime Baseline v2                                 │
└──────────────┴──────────────────────────────────────────────────────────────┘
~~~

The overview prioritizes conclusions plus evidence state. It does not begin with a wall of benchmark names.

## Compare

~~~text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Compare systems                                                             │
│ Systems [Agent Memory ×] [Mem0 ×]  Evidence [Same-harness only ▾]          │
│ Benchmark [LongMemEval_S ▾] Profile [Retrieval parity ▾] Plane [Session ▾] │
├──────────────┬───────────────────────────────────────────────┬──────────────┤
│ Comparison   │ EXACT SAME-HARNESS                            │ Evidence     │
│ sets         │ Why comparable? ✓                             │ inspector    │
│              │                                               │              │
│ LME Session  │ Metric             AM       Mem0     Δ         │ Input digest │
│ LME Turn     │ Recall all @5      .823     .809    +.014     │ same ✓       │
│ AMB Precision│ Recall all @10     .893     .883    +.010     │ Selection ✓  │
│              │ nDCG any @10       .878     .841    +.037     │ Budget ✓     │
│              │ Latest gold first  .457     .443    +.014     │ Metric ✓     │
│              │                                               │ Revisions    │
│              │ [Inspect run] [Share snapshot]                │ AM …         │
│              │                                               │ Mem0 …       │
│              ├───────────────────────────────────────────────┤              │
│              │ PUBLISHED MARKET CONTEXT · NOT HEAD-TO-HEAD   │              │
│              │ Hindsight LME QA 94.6%  [Why not comparable?] │              │
└──────────────┴───────────────────────────────────────────────┴──────────────┘
~~~

The evidence inspector can remain open while the user changes metrics or comparison sets.

## Changes to failures

~~~text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Changes                                                                     │
│ Before [Baseline v2 · ca0f9a7 ▾]   After [future baseline · abc1234 ▾]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Comparable                                                                  │
│ Currentness   .200 ───────────────────────────────▶ .760   +.560           │
│ Recall @5     .823 ───────────────────────────────▶ .901   +.078           │
│ Search p95    11.9ms ─────────────────────────────▶ 18.4ms  REGRESSION      │
│                                                                             │
│ New evidence: BEAM 1M first baseline                                       │
│ Not comparable: LongMemEval QA evaluator changed                           │
│                                                                             │
│ Currentness +.560   [Architecture context] [Explore changed failures]       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      v
┌─────────────────────────────────────────────────────────────────────────────┐
│ Failure Explorer · Currentness · After abc1234                              │
│ Filters [Stage ▾] [Case type ▾] [Outcome ▾] [Search cases]                 │
│                                                                             │
│ Ranking/fusion          ███████████████████ 41%                             │
│ Temporal applicability ████████████        27%                             │
│ Identity/slot          ████████            18%                             │
│ Candidate generation   ████                 9%                             │
│ Unclassified           ██                   5%                             │
│                                                                             │
│ Cases                                                                       │
│ MESA-00418  ranking/fusion     stale fact first   [Inspect evidence]        │
│ MESA-00602  unclassified       wrong target       [Inspect evidence]        │
└─────────────────────────────────────────────────────────────────────────────┘
~~~

The key flow is aggregate change -> affected metric -> failure population -> individual evidence, without losing revision/filter context.

# Implementation issue map

The future work is decomposed as:

- #698 — F1 versioned evidence-console catalog and projection contract
- #699 — UX visual system and interaction prototype
- #700 — F2 core static evidence console
- #701 — F2 immutable snapshot sharing and evidence-safe export
- #702 — F3 longitudinal architecture-impact and regression workflow
- #703 — F4 row-level failure explorer and case diagnostics

These issues remain future/post-RC work. Their existence does not promote #696 onto the active RC/runtime critical path.
