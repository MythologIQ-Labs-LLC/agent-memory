# Repository discoverability and documentation inventory (#797)

**Date:** 2026-10-13  
**Evidence boundary:** `main` `3eebb6d` (`evaluation(#757): schema-backed cross-write property identity candidates`)  
**Owner issue:** [#797](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/797); controlling reconciliation [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565)  
**Authority effect:** none. This is a point-in-time audit under `docs/audits/`. It proposes; it does not move, delete, or archive anything.

Companion: [`797-engineering-cleanup-candidates.md`](797-engineering-cleanup-candidates.md) (Phase 4 refactor candidates).

## 0. Method and scope

Everything below was derived from the working tree at the boundary above, not from the issue's estimates.

- Word and file counts: `find docs -name '*.md' | xargs wc -w`.
- Incoming-link analysis: a throwaway script that resolves every relative Markdown link, every backticked `docs/...md` path in Markdown, and every `docs/...md` string in `.py`, `.yml`, `.json`, `.toml` files, then lists `docs/**/*.md` files with no incoming reference from any other file.
- Link integrity: `python scripts/validate_markdown_links.py` over every Markdown file in the repository (369 files at the boundary; 371 after this PR).
- Staleness: each claim was checked against the code or ledger that owns it (`reference/agentmem_ref/api/contract.py`, `reference/agentmem_ref/runtime/temporal_order_constraints.py`, `reports/runtime/baseline-register.json`, `docs/adr/`, issue state on GitHub).

Scope follows the owner triage on #797: the first PR edits only `README.md`, `docs/README.md`, navigation paragraphs in `BENCHMARKS.md`, `docs/REPOSITORY_OPERATING_MODEL.md` (roles/navigation only), `docs/AGENT_MEMORY_PROJECT_MODEL.md` section 12 (the #565 completion item), one new proposed roadmap under `docs/future/`, and this audit. No `docs/adr/`, `schemas/`, `reports/`, `sources/`, fixtures, workflows, tests, or package files were touched. Nothing was deleted or relocated.

## 1. Size of the corpus (measured)

| Scope | Files | Words |
|---|---:|---:|
| `docs/**/*.md` | 363 | 558,688 |
| `docs/*.md` (immediate) | 186 entries incl. 14 directories | 348,784 |
| `docs/adr/` | 45 | 53,552 |
| `docs/profiles/` | 32 | 32,775 |
| `docs/prd/` | 4 | 11,386 |
| `docs/research/` | 6 | 7,860 |
| root `*.md` | 8 | 6,942 |

The external review's "~349K words" matches `docs/*.md` at the immediate level only; the tree is 559K words. Three files alone are 51K words and are append-only ledgers or ADRs that must not be trimmed by length: `docs/META_LEDGER.md` (38,570), `docs/adr/ADR-039-*.md` (7,391), `docs/56-benchmark-gauntlet-remediation-evidence.md` (7,375, immutable before/after evidence).

Length is therefore not the discoverability problem. The problems found were: (a) no audience-named on-ramps above the fold, (b) current-state facts restated in five places and drifting at different speeds, (c) 99 documents with no incoming link, and (d) several maintenance ledgers whose "current" rows are three weeks behind `main`.

## 2. Canonical / historical / proposed / superseded (entry documents)

| Document | Class | Basis | Disposition |
|---|---|---|---|
| `README.md` | canonical front door | pyproject `readme`; CODEOWNERS | **KEEP**, restructured in this PR |
| `docs/README.md` | canonical documentation index | linked from README, CONTRIBUTING, CI link check | **KEEP**, extended in this PR |
| `docs/REPOSITORY_OPERATING_MODEL.md` | canonical operating guidance (three roles) | self-declared canonical; cited by README/docs index/BENCHMARKS/GOVERNANCE | **KEEP**; roles-vs-layers subsection added |
| `docs/AGENT_MEMORY_PROJECT_MODEL.md` | proposed project model (five layers) under #554/#556 | self-declared "Proposed… authority effect: none" | **KEEP**; section 12 now records the #565 reconciliation instead of calling it pending |
| `BENCHMARKS.md` | canonical evaluation entry point, but its numbers are historical | self-declares the dashboard as current authority | **KEEP**; start-here block added; numbers left untouched and labelled revision-bound |
| `reports/benchmarks/dashboard/current.md` / `.json` | canonical current evidence | docs/64 "Documentation authority" | **KEEP**; owned by #785/#794/#796 pipeline, not edited |
| `docs/64-current-governance-and-benchmark-dashboard.md` | historical reconciliation at the #591/#594 boundary (`691251c`); its own status line now says HISTORICAL (owner commit `c9eb258`, merged) | self-declared; owner review on PR #798 | **KEEP as historical evidence; SUPERSEDE as a "current" pointer**: README and docs index label it historical and point current-state readers at code constants, BACKLOG, docs/43, the baseline register, and SYSTEM_STATE |
| `docs/66-pre-1.0-maturity-and-runtime-qualification.md` | addendum at the #600-#602 boundary (`b50d6d1`) | self-declared "canonical current-state addendum" | **KEEP**, indexed with its boundary named; same era-bound caveat as docs/64 |
| `docs/43-substrate-inventory-and-maturity.md` | canonical substrate maturity | section 12 maintenance rule | **KEEP**; the README substrate table now defers to it |
| `docs/BENCHMARK_COVERAGE_ATLAS.md` | governance artifact under #554 | vocabulary bound to `schemas/memory-benchmark-integration.schema.json` | **KEEP** |
| `docs/CONTRIBUTOR_ARCHITECTURE.md` | canonical contributor contract v1 (#652) | self-declared; CI-backed | **KEEP** |
| `docs/adr/README.md` | canonical doctrine-status ledger | GOVERNANCE | **KEEP**; extended to ADR-043 by the owner's reconciliation branch, merged into PR #798 |
| `docs/ARCHITECTURE_INDEX.md` | single architecture catalog and filing policy (owner branch `docs/797-single-architecture-index-no-ci`, `41893a2`, merged into PR #798) | self-declared; README and docs index Theory entry point now start there | **KEEP**; docs index no longer carries a second per-domain architecture inventory |
| `docs/GOVERNANCE_INDEX.md`, `docs/SYSTEM_STATE.md`, `docs/FEATURE_INDEX.md`, `docs/CONCEPT.md`, `docs/ARCHITECTURE_PLAN.md`, `docs/BACKLOG.md` | Qor-logic maintenance ledgers | each carries its own "last reconciled" boundary | **KEEP**; `BACKLOG.md` is current (2026-10-08); the others are 2026-09-12 to 09-24 and have Tier 1 drift (section 3) |
| `docs/META_LEDGER.md`, `docs/SHADOW_GENOME.md`, `docs/PROCESS_SHADOW_GENOME.md` | append-only ledgers | hash-chained / event log | **KEEP**, never trim |
| `docs/49-rc1-evidence-closeout.md` | historical (earlier RC closeout) | docs index says "earlier" | **KEEP** as historical evidence |
| `docs/65-independent-amb-competitive-profile.md` | profile whose status line is superseded by the dashboard | status says "NO ROW EXECUTED OR ACCEPTED"; dashboard records accepted rows since 2026-10-05 | **KEEP**; docs index now says the status line is historical; a one-line status refresh is an owner follow-up (benchmark lane, out of this PR's scope) |
| `docs/plan-*.md` (43 files), `docs/research-brief-*.md` (26 files) | historical working artifacts | GOVERNANCE_INDEX Tier 4/6 convention | **KEEP**; now classified in the docs index "Plans, research briefs, and audits" table; see section 5 for the ARCHIVE CANDIDATE question |
| `docs/future/*.md` | proposed only | self-declared | **KEEP**; new distributed-runtime roadmap added with the same convention |
| `wiki-src/` | published GitHub Wiki source | `publish-wiki.yml` | **KEEP**; framing stale (section 3) |

## 3. Stale references, paths, and claims (source-backed)

Fixed in this PR are marked ✅. Everything else is listed with its owner so nobody re-discovers it.

| Where | Claim | Reality at boundary | Status |
|---|---|---|---|
| `README.md` (before) | "Policy is **3.1.0**" | `temporal_order_constraints.py` declares `POLICY_VERSION = "3.4.0"` (#732) | ✅ removed; README now points to docs/64 and the code |
| `README.md` (before) | headline score table and #594 narrative | duplicated `reports/benchmarks/dashboard/current.md` and the #594 closeout, both canonical | ✅ removed; links only |
| `README.md` (before) | "Active RC sequence" block | duplicated docs/64, BENCHMARKS.md, #410 | ✅ removed; links only |
| `docs/README.md` (before) | "policy 3.1.0 is active" | 3.4.0 | ✅ section replaced with pointers to the owning sources |
| `docs/AGENT_MEMORY_PROJECT_MODEL.md` §12 | reconciliation "should be" done | #565 ruling exists; README/docs index/operating model now carry it | ✅ recorded |
| `docs/REPOSITORY_OPERATING_MODEL.md` | no mention of entry points or five layers | README now uses Theory/Benchmarks/Runtime | ✅ subsection added |
| `docs/adr/README.md` | "Current doctrine state" lists ADR-001 through ADR-039 | `docs/adr/` holds ADR-040 (Accepted), ADR-041, ADR-042, ADR-043 (Proposed); none are linked from any file | **Owned by the owner's branch `docs/797-canonical-state-reconciliation-no-ci`**, which extends the index to ADR-043; out of scope for this lane |
| `docs/GOVERNANCE_INDEX.md` Tier 1/3 | "#427 active RC gate; production-qualified canonical substrates = 0"; "ADR-001 through ADR-038"; "#440 active" | #427 closed 2026-09-23 (PR #452); SQLite qualified; ADR-043 exists; #440 closed 2026-09-24 per BACKLOG | **Owned by the owner's branch `docs/797-canonical-state-reconciliation-no-ci` (`ed9c48f`)**, which rewrites Tier 1/3 against `3eebb6d`; not duplicated here |
| `docs/SYSTEM_STATE.md` | "Public API Contract 1.2.0"; "Production-qualified canonical substrates 0"; reconciled 2026-09-23 | contract 1.6.0; SQLite qualified; Runtime Baseline v6 current | same owner branch: replaced by a compact revision-bound projection that carries the #636 product intent; README and docs index link it as a current-state owner |
| `docs/FEATURE_INDEX.md` | "current contract 1.4.0"; reconciled 2026-09-12 | 1.6.0 | same owner branch: relabelled as a bounded historical inventory |
| `docs/45-agent-memory-rc1-implementation-profile.md`, `docs/47-developer-facade-and-local-open-path.md` | "public contract 1.2.0" | 1.6.0 | **KEEP as published-state wording**; docs index now explains the convention and names the code as the version source. A one-line "current contract: see `api/contract.py`" note is a safe follow-up |
| `reference/README.md` | "contract `1.2.0`"; "seven subpackages" | 1.6.0; nine subpackages (`harness`, `evaluation` added) and the layout block omits `evaluation/` | **CONSOLIDATE** (reference/ is the runtime lane; propose with the Phase 4 candidates, see companion file) |
| `CONTRIBUTING.md` line 3, `wiki-src/Home.md` line 7 | "Agent Memory is a reference architecture and research-driven doctrine" | repository also ships a usable runtime and an evaluation lab (README, GOVERNANCE line 3) | **REQUIRES OWNER DECISION**: both are CODEOWNER / published-wiki surfaces; a one-sentence update to match GOVERNANCE.md line 3 is safe but outside the allowed first-PR file list |
| `docs/65-independent-amb-competitive-profile.md` status line | "NO ROW EXECUTED OR ACCEPTED" | twelve accepted lanes on the dashboard | **KEEP**, labelled historical in the docs index; refresh is a benchmark-lane edit |
| `reports/benchmarks/dashboard/current.md` | "Current merged `main`: `ca0f9a7`", "as of 2026-10-07" | main is `3eebb6d`; freshness is exactly what #795 / PR #796 automate | owned by #795 / #796; **not touched** |
| `BENCHMARKS.md` portfolio sections | LongMemEval_M "Status: complete bounded external run" while the Atlas §8 table says LongMemEval_M "not run" | the Atlas registry table reflects integration-descriptor admission state, BENCHMARKS reflects accepted dashboard rows; both are true in their own vocabulary but read as a contradiction | **REQUIRES OWNER DECISION**: add an "admission state ≠ evidence state" sentence to Atlas §8, or regenerate §8 from the registry; benchmark-lane edit |

All 369 pre-existing Markdown files pass the local link validator; no broken relative link was found at the boundary. The validator in CI only covers 30 named files (`validate-doctrine-evidence.yml` lines 187-218); see section 7.

## 4. Duplicate content map

| Content | Copies at boundary | Canonical home | Action |
|---|---|---|---|
| Three-role description | README, docs/README, REPOSITORY_OPERATING_MODEL, GOVERNANCE.md, AGENT_MEMORY_PROJECT_MODEL §12 | `docs/REPOSITORY_OPERATING_MODEL.md` | ✅ README/docs index now summarise and link; GOVERNANCE.md copy retained (governance surface, out of scope) |
| Write/read architecture diagram | README, docs/64, issue #410 | docs/64 | ✅ removed from README |
| Full invariant list (~20 lines) | README, docs/64, #410, CONTRIBUTOR_ARCHITECTURE (subset) | docs/64 | ✅ README keeps a nine-line excerpt and links |
| Headline benchmark numbers | README, BENCHMARKS.md, dashboard, docs/64, docs/61 | dashboard | ✅ README no longer carries numbers; BENCHMARKS.md labelled revision-bound (numbers not edited) |
| Active RC sequence | README, BENCHMARKS.md, docs/64, #410 | docs/64 + #410 | ✅ README dropped; BENCHMARKS.md copy retained (navigation-only edits allowed there) — **CONSOLIDATE** candidate: replace the "Active RC evaluation path" section with a link to docs/64 |
| Implemented product surface table | README, docs/45, REPOSITORY_OPERATING_MODEL §1 | docs/45 | ✅ README replaced it with the substrate maturity table (docs/43 summary) |
| Known limitations list | README, docs/64, #410 | docs/64 / #410 | ✅ README keeps the two unconditional boundaries and links |
| Evidence-class taxonomy | README, docs/README, REPOSITORY_OPERATING_MODEL, AGENT_MEMORY_PROJECT_MODEL §9, BENCHMARK_COVERAGE_ATLAS §4, CONTRIBUTOR_ARCHITECTURE §5 | REPOSITORY_OPERATING_MODEL (repository classes) and Atlas §4 (benchmark provenance classes) | README reduced to one sentence; the rest are vocabulary definitions in their own contexts, **KEEP** |
| Same-number documents | `47-developer-facade…` / `47-transactional-checkpoint-generations`; `50-keyed-rebinding…` / `50-swe-contextbench…`; `52-governed-cognitive-classification` / `52-harvest-closeout-final`; `66-pre-1.0-maturity…` / `66-rust-runtime-qualification…` | n/a | **REQUIRES OWNER DECISION**: renumbering breaks incoming links (47-transactional has 2, 66-pre-1.0 now 2); recommended: leave filenames, add a one-line disambiguation to the docs index (done for 66 pair), never renumber ADR-style evidence |

## 5. Unlinked documents (99 at boundary; 80 after this PR including the merged owner branches)

Full list produced by the method in section 0. Dispositions:

| Group | Count | Disposition |
|---|---:|---|
| Current-state docs that should be reachable: `65`, `66` ×2, `67`, `68`, `69`, `72`, `73`, `GAUNTLET_EXECUTION_ROADMAP`, `GAUNTLET_EXTERNAL_BENCHMARK_QUALIFICATION_2026-09-26`, `benchmark-evidence-console-catalog`, `CONFIGURATION`, `RUNTIME_IDENTITY_NAMING_BRIEF`, `prd/README`, `rfcs/README`, `explorations/*/README`, `programs/*/README`, `future/*`, `47-transactional…`, `50-keyed…`, `52-governed…`, `07`, `10`, `12`, `14` | 19 | ✅ **KEEP**, now linked from `docs/README.md` (the `07`/`14` status-line question in the row below remains an owner decision; linking them is navigation, not a status change) |
| ADR-003, ADR-007, ADR-028 Rust note | 3 | **REQUIRES OWNER DECISION**: ADR-003/007 are Accepted doctrine that the index's family narrative never cites; ADR-040 … ADR-043 are now listed by the owner's refreshed ADR index (merged) |
| `docs/audits/**` (13 files at boundary) | 13 | **KEEP** as point-in-time evidence; reachable via the docs index "audits/" directory row; the doctrine validator deliberately excludes this directory |
| `docs/profiles/*` (14 unlinked of 32) | 14 | **KEEP**: profiles are referenced by workflows/runners, not prose; a generated `docs/profiles/README.md` index is a CONSOLIDATE candidate for the evaluation lane |
| `docs/programs/**` leaf pages (18) | 18 | **KEEP**; their program READMEs are linked from the docs index; leaf pages are reachable one hop down |
| `docs/explorations/memory-architectures/*` leaf pages (6) | 6 | **KEEP**; README now linked |
| `docs/plan-sprint2a…2n` (14), `plan-sprint3a`, `plan-sprint3d`, `plan-669-semantic-vector-route`, `research-brief-sprint3b/3c/3d/4/4c`, plus three plans whose only link was the retired GOVERNANCE_INDEX Tier 4 table | 24 | **ARCHIVE CANDIDATE** (see migration proposal A). Every one is referenced from `docs/META_LEDGER.md` entries by name, so they are provenance, not dead weight; `ARCHITECTURE_INDEX.md` §3 files the whole `plan-*` / `research-brief-*` family as a collection |
| `docs/07-integration-roadmap.md`, `14-expanded-scope-recommendations.md` | 2 | **REQUIRES OWNER DECISION** on their status lines: both read as early-phase roadmap/recommendations whose execution posture now lives in docs/68 and BACKLOG. Linked from the spine section with that wording; no status line was edited |
| `docs/50-keyed-rebinding-currentness-benchmark.md`, `52-governed-cognitive-classification.md` | 2 | **KEEP**: implementation profiles for #483 and #490/#500 whose runners (`reference/run_keyed_rebinding_benchmark.py`, `contracts/cognitive_classification.py`) do not cite the document path; ✅ now indexed with same-number disambiguation |

The 80 files still unlinked on the merged tree are exactly the ADR (3), audit (13), exploration-leaf (6), plan/brief (24), profile (14), program-leaf (18), and `docs/research/` leaf (2 of 6; the directory is linked) rows above, all intentionally left for owner decision or generated-index work. `ARCHITECTURE_INDEX.md` §3 registers every one of those directories as a collection with a retention rule, so each is reachable one hop from the catalog even where no page links the individual file. A directory link counts as reachable for humans but not for this script, which only follows file links.

## 6. Migration proposals (before / after, with incoming links verified)

No proposal below is executed in this PR.

### Proposal A: historical plan and research-brief artifacts

- **Before:** 69 `docs/plan-*.md` and `docs/research-brief-*.md` files sit beside canonical numbered docs in `docs/`, inflating the immediate listing to 186 entries.
- **After (option 1, recommended):** leave files in place; the docs index now classifies them (done). Zero link churn, zero ledger impact.
- **After (option 2):** move to `docs/history/plans/` and `docs/history/research-briefs/`. Incoming references that would need rewriting (measured): 55 distinct referrer files outside `META_LEDGER.md`, led by `docs/GOVERNANCE_INDEX.md` (15 references), `docs/44-public-api-contract.md` (7), `reports/benchmarks/dashboard/current.md` (5, a generated projection owned by #795/#796), `docs/65-*` (5), `docs/README.md` (4), `docs/adr/ADR-038` (2), `reports/runtime/baseline-v6.md` (1, a byte-pinned Runtime Baseline record that must not be edited), plus 99 mention lines in `docs/META_LEDGER.md`, whose entries are hash-chained (a path edit there is a ledger amendment, not a silent rewrite). Recommendation: do not take option 2. A move touches a byte-pinned baseline record, a generated dashboard, an Accepted ADR, and the hash-chained ledger; the listing-size benefit does not justify that.

### Proposal B: BENCHMARKS.md portfolio sections

- **Before:** per-benchmark status prose with frozen highlight numbers.
- **After:** keep "Governing benchmark rules", "Start here", "Contributor contracts", "Rules for benchmark-driven changes", "Evaluator integrity"; replace "Current portfolio" and "Active RC evaluation path" with one paragraph per benchmark naming its profile id, provenance class, and dashboard section. Incoming links to BENCHMARKS.md: README, docs/README, REPOSITORY_OPERATING_MODEL, CONTRIBUTOR_ARCHITECTURE (no anchors), so the section removal breaks nothing. Owner decision because it touches benchmark narrative.

### Proposal C: maintenance ledgers Tier 1 refresh (in progress on the owner's branch)

- **Before:** GOVERNANCE_INDEX, SYSTEM_STATE, FEATURE_INDEX carry contradictions listed in section 3.
- **After:** the owner's branch `docs/797-canonical-state-reconciliation-no-ci` (`ed9c48f`, four files, no overlap with PR #798) replaces SYSTEM_STATE with a compact revision-bound projection, relabels FEATURE_INDEX as historical, and rewrites GOVERNANCE_INDEX Tier 1/3 against `3eebb6d`. PR #798's pointers were written to be correct against both the current and the refreshed files; the two should land together so the front door is current.

### Proposal D: ADR index completeness (in progress on the owner's branch)

- **Before:** index narrative stops at ADR-039.
- **After:** the same owner branch extends the index to ADR-043. No other file references change.

## 6a. Cross-branch reconciliation and merge order

Three docs-only branches touch the #797 front door. Measured at `3eebb6d`:

| Branch | Head | Files | Overlap with the others |
|---|---|---|---|
| `claude/happy-mayer-q1l40c` (PR #798) | this PR | `README.md`, `BENCHMARKS.md`, `docs/README.md`, `docs/REPOSITORY_OPERATING_MODEL.md`, `docs/AGENT_MEMORY_PROJECT_MODEL.md`, `docs/future/distributed-runtime-roadmap.md`, two audits | none |
| `docs/797-canonical-state-reconciliation-no-ci` (owner) | `c9eb258` | `docs/SYSTEM_STATE.md`, `docs/GOVERNANCE_INDEX.md`, `docs/FEATURE_INDEX.md`, `docs/adr/README.md`, `docs/CONCEPT.md`, `docs/64`, `docs/65` | none |
| `docs/797-single-architecture-index-no-ci` (owner) | `41893a2` | `docs/ARCHITECTURE_INDEX.md` (new), one pointer in `docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md` | none |

Both owner branches were merged into PR #798 with ordinary merge commits (no rebase, no rewrite of owner commits) so the three could be validated as one tree: the front door now links `ARCHITECTURE_INDEX.md`, which only exists on the index branch, and the "current state" pointers resolve to the refreshed `SYSTEM_STATE.md`. Any of these landing orders is clean:

1. Land PR #798 as is; it carries both owner branches as merge commits with their authorship intact. Simplest, one review.
2. Land the two owner branches first (either order, they do not touch each other), then PR #798; its merge commits become no-ops.

What must not happen: landing PR #798 without the index branch, which would leave the Theory entry point pointing at a missing file.

## 7. Validation performed and what CI does not cover

Local, no CI, no paid inference:

```bash
python scripts/validate_markdown_links.py $(git ls-files '*.md' | grep -v '^wiki-src/')   # all repository Markdown
python scripts/validate_wiki_links.py wiki-src                                              # wiki pages use extensionless links
python scripts/validate_doctrine_boundaries.py
python -m unittest reference.tests.test_package_layout reference.tests.test_test_import_convention reference.tests.test_packaged_schema_resolution
git diff --stat origin/main -- reference schemas reports sources fixtures .github   # must be empty
```

Gap worth owning: CI's `validate-doctrine-evidence.yml` link-checks 30 named Markdown files. Running the same script over every tracked `.md` is cheap (sub-second) and found zero failures at the boundary, so widening the invocation to `git ls-files '*.md'` is a low-risk workflow change. It is **not** made here because workflow files are out of scope; recorded as a candidate in the companion engineering file.

## 8. Three operational roles versus five project layers (verified explanation)

Verified against `docs/REPOSITORY_OPERATING_MODEL.md`, `docs/AGENT_MEMORY_PROJECT_MODEL.md` §2, and the #565 ruling:

| Three roles (what the repository does today) | Five layers (how the project is partitioned) | README entry point |
|---|---|---|
| Architecture / governance laboratory | 1. Architecture / Doctrine / Research Commons | Theory |
| Evaluation / benchmark laboratory | 2. Memory Evaluation (measurement machinery) + 3. Agent Memory Gauntlet (public qualification program) | Benchmarks |
| Product / runtime | 4. Reference / Conformance Implementation (exists: `agent-memory-reference` 0.2.0, contract 1.6.0, Runtime Baseline v6, `sqlite_single_host_v1`) + 5. future Distinct Production Runtime Product (does not exist; identity/licensing owned by #556) | Runtime |

Neither formulation supersedes the other. The layers refine the roles; the roles are the operational vocabulary for PR classification, CODEOWNERS, and the docs index. The entry points are audience names for the roles, not a third model. This is now stated consistently in README, docs/README, the operating model, and project-model §12.

## 9. Product-truth alignment (Phase 5)

| Substrate / claim | Documented state now | Source |
|---|---|---|
| `SQLiteTemporalGraph` / `sqlite_single_host_v1` | RC-qualified single-host; only production-credible profile | docs/43 §2.2, #427 closed via PR #452 |
| `InMemoryTemporalGraph` | reference; checkpoint correctness proven | docs/43 §2.1 |
| `GraphitiSubstrate` | experimental; deprecated upstream driver path | docs/43 §2.3 |
| Rust kernel | shadow only; Python qualified | docs/66-rust |
| Postgres / graph DBs / Markdown / object stores | storage technologies, not substrates | docs/43 §8 |
| Distributed / multi-host | not established; **proposed** roadmap only | `docs/future/distributed-runtime-roadmap.md` (new) |
| Product intent vs qualification | README and docs index state the #636 heterogeneous multi-system composition intent above the role navigation and name single-host SQLite as the only qualified canonical persistence profile | README "What Agent Memory is", docs/README intro, #636 |
| "Current state" pointers | code-declared `POLICY_VERSION` / `CONTRACT_VERSION`, docs/43, baseline register, BACKLOG, SYSTEM_STATE, live issues; docs/64 and docs/66 labelled by their boundary | README "Where the runtime stands", docs/README "Current semantic/temporal state" |
| Benchmark scores in README | none; dashboard is canonical | README "Benchmarks" |
| Leaderboard / freshness | linked to #779 / #789 / #795 as in-progress work | README, BENCHMARKS.md |

## 10. Owner decisions requested

1. ~~ADR index: add ADR-040 … ADR-043 (Proposal D).~~ Done on `docs/797-canonical-state-reconciliation-no-ci`, merged into PR #798.
2. ~~Maintenance ledgers: one Tier 1 reconciliation commit (Proposal C).~~ Done on the same branch, merged into PR #798.
3. `CONTRIBUTING.md` line 3 and `wiki-src/Home.md` line 7 framing sentence (now also out of step with the #636 product-intent sentence the README and `CONCEPT.md` carry).
4. Whether to open a tracking issue for the distributed-runtime roadmap, or leave it as a `docs/future/` proposal until a stage is funded.
5. Same-number documents: accept index disambiguation instead of renumbering.
6. `docs/07` and `docs/14` status lines: mark historical or keep as spine.
7. Atlas §8 vs BENCHMARKS.md LongMemEval_M wording.
8. Widen CI link validation to all tracked Markdown (workflow edit).

## 11. Disposition addendum (2026-10-16, `main` `38f6a7d`)

Sections 1 to 10 are the point-in-time record at `3eebb6d` and are left as written. This addendum records what landed afterwards so the open-items list above is not read as current.

| Item above | Disposition | Where |
|---|---|---|
| Owner decision 1 (ADR index to ADR-043) | closed | owner commit `ed9c48f`, landed via PR #798 (`2ef717e`) |
| Owner decision 2 (Tier 1 ledger reconciliation) | closed | owner commits `ed9c48f`, `c9eb258`, landed via PR #798 |
| Owner decision 3 (`CONTRIBUTING.md` line 3; `wiki-src/Home.md` line 7) | closed | `c744cb9` via PR #803 (`7fa9c36`); `a392b11` |
| Owner decision 4 (tracking issue for the distributed roadmap) | still open | the roadmap remains a `docs/future/` proposal |
| Owner decision 5 (same-number documents) | closed as "do not rename" | catalog rule in `docs/ARCHITECTURE_INDEX.md` §2 (`41893a2`) |
| Owner decision 6 (`docs/07`, `docs/14` status lines) | closed | retired as historical stubs with pinned original revisions, `a392b11` |
| Owner decision 7 (Atlas §8 vs BENCHMARKS.md LongMemEval_M wording) | closed | duplicate registry status table removed from the Atlas, `38f6a7d`; BENCHMARKS.md copied scores and RC schedule removed, `a392b11` |
| Owner decision 8 (widen CI link validation) | closed | `validate-doctrine-evidence.yml` now checks all non-wiki Markdown and runs the catalog guard, `a392b11` |
| Section 3: `docs/64` and `docs/65` status lines | closed | `c9eb258` |
| Section 3: `docs/66` "canonical current-state addendum" self-description | closed | `a392b11` |
| Section 3: `docs/45` / `docs/47` contract `1.2.0` lines | closed with publication-boundary banners, numbers left as published | `cdf172d` |
| Section 3: `reference/README.md` contract and "seven subpackages" | closed | `a392b11` |
| Section 3: `BACKLOG.md` v4 contradiction (lines 69 and 100) | closed | `a392b11` |
| Section 5: catalog shelf E historical markers for `docs/64` / `docs/66` | closed | `cdf172d` |
| Section 5: `docs/ARCHITECTURE_PLAN.md` self-status | closed | this branch (status line added; original text preserved) |
| Section 6 Proposal A (move historical plans) | not taken, as recommended | no moves; collections registered in the catalog §3 |
| Section 6 Proposal B (BENCHMARKS.md portfolio sections) | taken by the owner | `a392b11` |
| Drift guard for the catalog | landed | PR #803 (`25bc149`), wired into CI by `a392b11` |
