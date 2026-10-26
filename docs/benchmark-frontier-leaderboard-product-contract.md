# PRD-002 extension: benchmark-native leaderboards and distance to frontier

**Issue:** #779. **Parents:** #696 / #700. **Evidence foundation:** #698 (PR #708, merged). **Competitor qualification:** #600, #601, #640. **Deficit ownership:** #574, #668, #719, #768.  
**Status:** IMPLEMENTED AND LOCALLY QUALIFIED as an engineering preview (projection schema 0.2.0, static viewer, browser evidence). Not a benchmark execution, not a runtime source change, not an approved public deployment. See the qualification record at the end of this document.

## Product North Star

> On every meaningful Agent Memory benchmark measurement, show the best independently evidenced competing result, the Agent Memory result, the exact gap to the leader, and the evidence or implementation work needed to close it.

Success is a *frontier across the full qualified capability space*, **not** a universal averaged number. Every meaningful metric has its own native units, direction, cutoff, evaluator protocol, population, evidence class and potential adequacy threshold. The definition of "relevant" must be explicit and extensible through the nine Coverage Atlas families and the benchmark evidence registry, not a one-time static shortlist.

## Primary experience: the frontier dashboard

```text
AGENT MEMORY  /  BENCHMARK FRONTIER                     Snapshot: accepted evidence 2026-10-07
[ All families ▼ ]  [ All benchmarks ▼ ]  [ All metrics ▼ ]   [ Behind / Leading / No peer / Unmeasured ▼ ]

   MEASURED LEADER  |  MEASURED DEFICIT  |  INADEQUATE LEADER  |  COVERAGE GAP
   [counts + denominators only, no synthetic total score / success %]

Benchmark / metric                   Best accepted same-harness     Agent Memory     Gap       Evidence / next work
LongMemEval S / session recall@5    Agent Memory 82.3%             82.3%             0 pp       accepted exact lane
LongMemEval S / turn recall@50      Mem0 OSS 89.5%                 85.9%           3.6 pp       #673
LongMemEval S / turn latest-first   Lexical control 61.4%         55.7%           5.7 pp       #673 / currentness
AMB / mean precision                Agent Memory 18%               18%             0 pp       #719 / inadequate absolute
AgentMemBench / currentness         [no qualified peer]           [see native row]  unknown      #640
SWE-ContextBench Lite external      [not qualified]               [not qualified]   unknown      #467
MemoryArena / action success        [not run]                     [not run]         unknown      #600

                  [ Expand metric / compare all systems / view evidence / see remediation ]
```

**The values above are illustrative rounded presentations of accepted v1 same-harness evidence in `reports/benchmarks/dashboard/current.md`**, not a manually maintained source table, not claims about global market leaders, and not a substitute for current runtime-v6 replay. The real projection must derive values and comparison eligibility from *one exact* accepted lane and snapshot.

### Drill-down: one metric, all systems

```text
Benchmark: LongMemEval_S / turn plane / recall_all@50       higher is better
Frozen lane: longmemeval-s-retrieval-parity-v1              Evidence: same-harness only

Rank     System                         Score         Distance to first
1        Mem0 OSS, pinned explicit      89.5%          0.0 pp
2        Agent Memory, pinned runtime   85.9%          3.6 pp
3        Lexical baseline              76.1%         13.4 pp

Leader - Agent Memory = 0.895 - 0.859 = 0.036 ratio = 3.6 percentage points.

[Why comparable?] [Exact runs] [Dataset + scorer] [Trend across eligible versions] [Issue #673]
```

If lower is better, the best system is the *minimum*; the gap for Agent Memory is `agent_memory - minimum`. For a true zero-target governance metric, the minimum must be an eligible measured value. If no suitable competitor is measured, **gap is null**, not zero, and the UI must not celebrate a one-run "victory."

## Two independent notions of success

1. **Competitive frontier:** At each native metric, Agent Memory is tied with or better than the best *comparable* evidenced system. A leader rank is certified only within the explicitly displayed competitor population, not "all products."
2. **Adequacy frontier:** The result meets a separately approved, benchmark-native usefulness threshold or conformance condition. A poor absolute score that beats two weaker products is *leading but inadequate*, not done.

A third **evidence frontier** tracks whether enough independent systems, profiles, difficult cases, validation quality and time spans exist to justify either claim. Never invent an adequacy number to make a card green.

## Views and hierarchy

1. **Frontier overview, first screen.** Every registered benchmark-native metric and its latest eligible comparable lane, sortable by worst native deficit, evidence status, benchmark family, capability and owner. Do not sort arbitrary percent-point and millisecond deltas on one normalized "pain" axis. A "behind" filter groups by metric but does not assert cross-metric relative magnitude.
2. **Benchmark explorer.** Choose benchmark, profile/plane and evaluator; show each native metric as a distinct ranked table, with explanation of cutoff k and higher/lower target.
3. **Competitor spectrum.** Show `same_harness` numeric rankings first, `published_reference` separately, and disabled/non-comparable rows with why-not explanations. Never render external published scores in the same ranked list as locally reproduced numbers unless exact equivalence is established.
4. **Progress.** Show valid Agent Memory revision changes and any protocol-break separators, annotated issue/PR/ADR and runtime-baseline associations. Temporal association alone is not causal proof.
5. **Coverage.** Every catalog metric and open capability objective is represented: ranked, self-only, no Agent Memory, blocked, not_run, unsupported, non_comparable, or no accepted evidence.
6. **Evidence inspection.** One click surfaces exact run ID, system revisions/configuration, immutable benchmark input and selected population, evidence hashes, judge model, metric direction/definition, scorer revision and reproducibility command. Do not display an unqualified score without evidence.

## Projection interface

Propose a *new versioned read-only* projection `reports/benchmarks/ui/frontier-leaderboards.json` generated from the already committed F1 `reports/benchmarks/ui/catalog.json` (and versioned #768 objectives once qualified). A prospective per-metric record, no fabricated values:

```json
{
  "schema_version": "0.1.0",
  "snapshot_id": "<the exact F1 snapshot id>",
  "metric_key": "<benchmark profile + dimension + native metric>",
  "comparison_set_id": "<accepted F1 comparison identity>",
  "evidence_class": "same_harness",
  "direction": "higher_better",
  "unit": "ratio",
  "ranking_state": "eligible",
  "leader": {"system_id": "<id>", "value": 0.895, "rank": 1},
  "agent_memory": {"system_id": "agent-memory", "value": 0.859, "rank": 2},
  "gap_to_leader_native": 0.036,
  "adequacy": {"state": "threshold_not_established", "target": null},
  "owned_deficits": ["#673"],
  "evidence_refs": ["<accepted lane manifest and native run refs>"],
  "authority_effect": "none"
}
```

The JSON above describes the **shape**, not a populated certified row. Numeric native values and evidence refs may only come from actual accepted lane/catalog records; #768 objectives are ownership targets, not independent benchmark scores.

Fail-closed projection requirements:

- Comparator row grouping is inherited from F1 `comparison_sets`; the frontend cannot choose a matching set by label or interpolate across versions.
- A score is eligible for ranking only when `evidence_class == same_harness`, `comparison_state == exact`, `eligible_for_numeric_delta == true`, the native metric has a single versioned and directional identity, and the value is finite, measured, numeric (never boolean).
- Do not rank descriptive/nonordered states, or treat `not_run`, `blocked`, `not_measured`, `unsupported`, `not_applicable`, `absent` or `evidence_gap` as numeric zero.
- Unit/population/cutoff must agree; if denominator or configuration differs where equality matters, demand independently documented equivalence instead of assuming.
- Equal values receive deterministic shared rank, using a documented sort for display order. Prefer top-run selection per exact system/revision, never silently cherry-pick the best repeated stochastic run.
- Agent Memory itself participates in leader selection, but a **self-only** row means `no_peer`, not `best_in_class`. A competing lexical *baseline* is a measured control, and must not be represented as a commercial memory system.
- A signed deficit is distinct from raw native score difference: e.g. for `lower_better`, `gap=AgentMemory-best`. A tied/leading state gets measured 0 only when at least one comparably evidenced peer exists. Never infer 0 for omitted scores.
- Preserve score uncertainty and statistical significance where protocols supply intervals/trials; a numeric 0.01 lead without those may be an unresolved tie, not a statistically established win.
- Keep benchmark coverage complete: projected metric definition can lack a ranked comparable set. New metrics and newly proposed external benchmarks appear as typed coverage rows, not invented scores.
- Preserve arbitrary benchmark units and valid ratios. Percentage-point formatting is a UI choice **only** when native unit is a ratio.
- A verified output should show both numeric frontier delta and independent absolute adequacy gap **when that threshold exists**, with separate owners and stop conditions.
- All outputs are read-only and use the exact F1 snapshot ID. No automated task closure, ranking-driven runtime modification, or memory/governance authority.

## F2 implementation sequencing

1. Qualify ranking/projection rules with offline synthetic metamorphic tests and accepted AMB/LongMemEval same-harness replays. Freeze the calculation contract before coding the visual table.
2. Expose `frontier-leaderboards.json` and one static table with exact per-metric source inspection. Keep missing/unsupported as first-class rows.
3. Integrate benchmark-native leaderboard and gap bars into #700, with keyboard and responsive specifications from #699.
4. Link #768's 29 objectives and accepted deficit owners, but keep review state/adequacy separate from rank.
5. Extend coverage to candidate benchmarks in the capability atlas, adding benchmark adapters rather than new hard-coded UI comparisons. Add snapshot sharing via #701 and valid architecture-delta trends via #702.
6. Independent execution and falsification in Claude Code cloud/local, no GitHub Actions/CI use for this branch. Separate actual score execution under #601 and #640 governance.

**Launch acceptance:** A user can go from any benchmark and native metric to its strongest eligible measured competitor, Agent Memory rank, measurable gap, absolute adequacy target (or absent state), and immutable evidence/owner without consulting raw files. The UI prominently says what is *not* known.

## Qualification record (local, no CI)

Projection `reference/agentmem_ref/evaluation/ui_frontier_leaderboard.py` (schema `0.2.0`), builder `scripts/build_benchmark_frontier_leaderboards.py`, viewer `reports/benchmarks/ui/index.html`, generated artifact `reports/benchmarks/ui/frontier-leaderboards.json`, browser evidence `reports/benchmarks/ui/evidence/`.

Rules added beyond the original fail-closed list, each exposed by the accepted catalog or by an adversarial fixture:

- Every ranked value must resolve to a complete run record whose benchmark id, input digest, selection id, sample count, task profile and system revision equal the comparison identity; otherwise the row is non-comparable with a `provenance_missing`, `run_identity_mismatch`, `run_revision_mismatch` or `run_not_complete` reason.
- A ratio outside `[0, 1]` invalidates the row; a value whose state is not `measured` is never a score even when numeric.
- Boolean measurements are `not_rankable`, distinct from `not_measured`.
- Ties expose `leader_state: tied` and `co_leaders`; the alphabetically first system is never presented as a sole leader.
- Peers are typed as `subject`, `external_competitor` (`external_memory`) or `control` (`lexical`, `no_memory`); the competitive state distinguishes *leading vs external*, *tied*, *leads controls only*, *behind external* and *behind control*. A lead over controls alone is not a market position.
- Repeated runs are grouped into a structural lineage (benchmark, input, selection, sample, system kinds, metric metadata; labels are never parsed) and ordered by the Agent Memory run start time: `current`, `superseded`, `newer_unaccepted_evidence`, or `undetermined` when start times are absent.
- The snapshot block carries `as_of`, `evidence_revision` and `repository_is_newer` for historical identification.
- Published references and the external-competitor registry are emitted separately and never ranked; the frontier objectives registry is `absent`, `draft` or `canonical`, preserves families A–I, and links ownership only as a labelled match.
- The viewer refuses projections with an aggregate score, an authority claim or an unsupported schema, and renders any internally inconsistent row as "Invalid row, refused" without numbers.

Known evidence gaps surfaced: `reports/benchmarks/dashboard/current.json` lists four accepted frozen lanes while `current.md` describes twelve, so lane generations v3–v6 project as `same_profile` and never rank; AMB run records have no start time, so AMB v1/v2 chronology is undetermined; no machine-readable adequacy threshold exists for any metric.

