# Independent frozen-lane inventory audit: 2026-10-13

**Status: SOURCE AUDIT ONLY. Not evidence acceptance, benchmark execution, baseline publication, or release authorization.**

Source repository: `MythologIQ-Labs-LLC/agent-memory`, `main` at `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`. Dashboard JSON blob `2acc39d36b3b637a08289aa757919f55da04c54c`. Dashboard Markdown blob `9235baa5691e4fbd15d2d2f76f22b36e31c754e3`. Links: #785, #779, #768, #601.

## Independently observed registry contradiction

1. `reports/benchmarks/dashboard/current.json` contains **four** `competitive_evidence.frozen_lanes` entries (AMB and LongMemEval parity v1/v2), while its own status field says `eight_same_harness_lanes_accepted`.
2. `reports/benchmarks/dashboard/current.md` opening status says **four**, while its competitive section says **twelve** same-harness lanes through v6.
3. All **twelve** lane definition files below existed at the inspected exact main SHA. I fetched each JSON and confirmed `lane_id` matched its path, `status == "accepted"`, and `authority_effect == "none"`.
4. GitHub code search found normalized and raw evidence references for each lane. **Search result counts are discovery indicators, not complete artifacts or proof of accepted imports.** A lane definition labelled `accepted` does not independently establish that every source execution is accepted for numerical comparison.

| Family | Lane | Frozen lane Git blob | Normalized search hits | Raw/artifact search hits | JSON registry |
| --- | --- | --- | ---: | ---: | --- |
| AMB | `amb-precisionmembench-retrieval-v1` | `9a6182c461a852a16d371fc00cdd13268d9cbfde` | 3 | 30 | yes |
| AMB | `amb-precisionmembench-retrieval-v2` | `c9ee1ee94ac699ff31384e1664d9f6e6ba06ffc1` | 3 | 6 | yes |
| AMB | `amb-precisionmembench-retrieval-v3` | `7d3d48ff249add9eacc44acca010b811d227fd49` | 3 | 6 | no |
| AMB | `amb-precisionmembench-retrieval-v4` | `15b0bc55e047c4872810aab86ae3e040088815c7` | 3 | 8 | no |
| AMB | `amb-precisionmembench-retrieval-v5` | `1cc19f3c053fe5b1e41564a647fdb1ff799b62d6` | 3 | 6 | no |
| AMB | `amb-precisionmembench-retrieval-v6` | `f25355d0c0f3462c148d40da1dfb7812943f90e5` | 3 | 6 | no |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v1` | `16f66db8ea19c8ce9361b017077063c5bd92fa35` | 6 | 41 | yes |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v2` | `561e994e4353560350ef56653a2ff47ddda13eec` | 6 | 26 | yes |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v3` | `e122c3818af8fe2dce84d9c38cdc13afada19d2e` | 6 | 32 | no |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v4` | `e1dfaf1a20c4d1f3b773a40b78cf2915bdbb3559` | 6 | 30 | no |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v5` | `3bc8137cf2d0afd556ffe41cae6806a417db03d3` | 6 | 24 | no |
| LongMemEval_S | `longmemeval-s-retrieval-parity-v6` | `1c0f9b93d451a43e032c9e2fd09bf45c451699e6` | 6 | 18 | no |

## Reconciliation protocol for the canonical registry

- Verify **accepted `evidence_history` importer records** for each of the eight additional v3–v6 lane IDs. Bind raw SHA-256, normalized run, execution identity, tool/runner revision, full selection, exact input, comparator configuration and frozen lane blob. Do not trust either Markdown prose or `lane.status` alone.
- Treat AMB subject/BM25/Mem0 separately and LongMemEval **session and turn** separately. Measured extra Agent Memory configurations (semantic required, shadow control) must not become independent external market competitors.
- Confirm freeze predates scoring and evidence binds the declared runtime successor. Keep v1–v6 comparisons as separate identities and their immutable run artifacts unchanged. Avoid mixing metric rows across different budgets or inference/adapter configs.
- For each lane independently record `verified_acceptance`, `incomplete_provenance`, or `no_accepted_import`, including the evidence pointer and reviewer decision. Do **not** coerce unknown to failed/zero.
- Once independently verified, use a **different, explicitly reviewed reconciliation change** to update both the machine-readable `frozen_lanes` and contradictory status strings and the Markdown executive text, with tests checking inventory consistency.
- Rebuild only derived F1 catalog and #785 frontier projection after authoritative acceptance. Until then #785's fail-closed v3–v6 `same_profile` posture is the correct conservative response, despite a stale rank view.
- Do not perform new benchmarks, overwrite frozen evidence, use GitHub Actions, or merge/publish a runtime baseline as part of this audit.

## Owner decision boundaries

**Verified now:** three contradictory published counts; twelve lane source definitions marked accepted; normalized/raw evidence search references exist across v1–v6.

**Not verified now:** the full chain of authenticated imports and exact same-harness comparability for v3–v6. No numeric ranking or dashboard-currency promotion is justified solely by this report.

**Engineering impact:** The current 58 qualified leaderboard rows represent historical v1/v2 evidence. This should be disclosed prominently until the canonical dashboard and source evidence are reconciled, even though newer runtime measurements appear present.

This artifact is intentionally separate from Claude's runtime and leaderboard implementation branches, so it can be independently reviewed or discarded without affecting either.


## Follow-up: verified integration-descriptor report bindings

This follow-up is materially stronger than mere lane-file discovery. Using authenticated GitHub contents reads against **the same exact main SHA** above, the audit loaded both registered integration descriptors:

- AMB: `reference/agentmem_ref/evaluation/integrations/amb-precisionmembench-retrieval-v1.json` at blob `8caa765175192e87aca6875b9282fac46d6d6865` (descriptor admission state `evidence_partial` because unexecuted variants remain blocked).
- LongMemEval: `reference/agentmem_ref/evaluation/integrations/agent-memory-longmemeval-retrieval-currentness-v1.json` at blob `888708408d96a2f3bf5d4ad527961530fe4d6137` (also `evidence_partial`).

**Every one of 41 `status: complete` records in v3–v6 was followed to its actual committed `report` JSON**, parsed, and checked against the descriptor's `variant`, `input_sha256`, and `system_revision`. All 41 passed. Additional checks: exact report `lane_id`, `authority_effect: none`, full selection (AMB `execution.full_selection: true`; LongMemEval `execution.subset_size: "0"`), and correct session/turn plane for LongMemEval. Each record's Git blob SHA and workflow run ID was captured below, not inferred from filenames.

| Frozen generation | AMB complete | LongMemEval complete | Subject/control/comparator ordinary runs | Extra Agent Memory variant runs |
| --- | ---: | ---: | ---: | ---: |
| v3 | 3 | 8 | 9 | 2 semantic variants |
| v4 | 4 | 8 | 9 | 3 shadow variants |
| v5 | 3 | 6 | 9 | 0 |
| v6 | 3 | 6 | 9 | 0 |
| **v3–v6 total** | **13** | **28** | **36** | **5** |

Three exact-source machine-readable inventories are included in this PR:

- [AMB v3–v6 bindings](2026-10-13-amb-v3-v6-source-bindings.json): 13 report identities.
- [LongMemEval v3–v4 bindings](2026-10-13-longmemeval-v3-v4-source-bindings.json): 16 report identities.
- [LongMemEval v5–v6 bindings](2026-10-13-longmemeval-v5-v6-source-bindings.json): 12 report identities.

These identities are sufficient to establish that later accepted integration-descriptor entries **exist** and bind to concrete same-lane, same-input, same-revision, full-selection source reports. They are stronger than a Markdown claim or a lane `status` string. The original four-record `frozen_lanes` inventory plainly has an unreflected acceptance history.

**Still not independently verified:** source `files` SHA-256 bytes against the repository objects, full importer/normalizer re-execution, exact declaration blob validity and freeze-before-scoring chronology for every row, and resulting derived F1 catalog scorecard equivalence. The raw reports continue to describe their own evidence class as `same_harness_external_candidate`; the integration descriptor's completed acceptance is a separate governance event. Do not collapse those statuses.

**Recommendation:** approve a distinct, gated *canonical evidence registry reconciliation* for the eight omitted lanes after the four residual checks above. Keep historical generations separated, include the five diagnostic variants solely as measured reference rows rather than extra independent competitors, and only then rebuild `catalog.json`, `frontier-leaderboards.json`, and the static viewer snapshot. Do not alter PR #785 itself merely to force an optimistic newer leaderboard.

This follow-up is read-only. Its checks were performed through GitHub source reads and parsed metadata comparisons; **no Python test suite, importer replay, independent external scorer, or CI execution is claimed**.

## Normalizer and freeze cross-check (additional source checks)

`scripts/build_benchmark_scorecards.py` at source blob `f49ed14b79cfb12e4c46bc2f1019e44a9f47c602` lists **36 distinct v3–v6 raw report sources**, exactly nine per lane generation (3 AMB + 6 LongMemEval session/turn). Comparing these literal source paths against the 41 `status: complete` integration history entries gives **36/36 matched and zero unbound scorecard sources**. The five completed and deliberately omitted variants are:

1. AMB v4 `agent-memory-shadow`;
2. LongMemEval v3 `agent_memory_semantic` session and turn;
3. LongMemEval v4 `agent_memory_shadow` session and turn.

Thus the normalizer source selection follows the intended **subject + lexical control + external competitor** population and does not count Agent Memory's semantic/shadow variants as separate market competitors. The existence of normalizer source configuration does not, on its own, prove its last derived JSON was regenerated and validated.

Each of the eight v3–v6 frozen lane files also declares `frozen_before_any_score: true` and supplies `frozen_on` dates (v3–v5: 2026-10-07; v6: 2026-10-08), with accepted row `status_reason` fields citing the same date and respective run ID. These are self-declared chronology records; independent immutable freeze-commit timing relative to external workflow execution was **not** yet cross-verified.

**Narrowed remaining checks before canonical 12-lane registration:** (a) immutable freeze-before-execution commit/timestamp evidence; (b) raw artifact SHA-256 bytes, importer manifest and normalized output reproduction; (c) runtime successor declaration and exact bridge/scorer configuration per generation; (d) deterministic `current.json` -> F1 catalog -> #785 projection regeneration with fail-closed tests. No independent rank update has been authorized.


## Byte-level integrity and exact freeze ancestry (follow-up)

**Completed 2026-10-13, independently using authenticated GitHub source reads, a SHA-256 implementation self-tested against the known `abc` vector, and stored source reports.**

**All 36/36 ordinary v3–v6 primary result JSON artifacts independently re-hash to the exact 64-hex SHA-256 in each accepted source report's `files` inventory:**

| Generation | AMB `single-turn.json` | LongMemEval `report.json` | Total |
| --- | ---: | ---: | ---: |
| v3 | 3/3 | 6/6 | 9/9 |
| v4 | 3/3 | 6/6 | 9/9 |
| v5 | 3/3 | 6/6 | 9/9 |
| v6 | 3/3 | 6/6 | 9/9 |
| **Total** | **12/12** | **24/24** | **36/36** |

Source paths, computed hashes, expected hashes and exact Git blob identities are recorded in eight `2026-10-13-{amb,longmemeval}-vN-primary-byte-digests.json` manifests plus `2026-10-13-primary-artifact-integrity-rollup.json`. **No original normalized run, evidence blob, or frozen source was changed.**

**Freeze and declaration ancestry verified across all four later generations:** The exact Agent Memory runtime source revision recorded in the accepted AMB control evidence is the **Git merge commit that introduced that generation's frozen lane definitions**. At that same commit, `reports/runtime/baseline-vN-declaration.json` has the **same Git blob SHA** recorded in the accepted control evidence as `system.runtime_baseline.declaration_blob`, and its recorded successor is vN with `state: TRANSITION`:

| Generation | Freeze PR | Merge/execution revision | Frozen successor declaration Git blob |
| --- | --- | --- | --- |
| v3 | #709 | `04bb286f90f1` | `593fee135b8f` |
| v4 | #716 | `f5a79d230a31` | `ac1e498c6690` |
| v5 | #729 | `e6f9db7f1db5` | `e93f4a2d245d` |
| v6 | #743 | `24048d55e26d` | `1ac4d7d87b6b` |

This proves the **frozen lane and relevant declaration existed in the exact executing repository revision**, rather than being inferred from a later Markdown statement. GitHub workflow job records were also retrieved for one AMB and one LongMemEval control run per generation; these were `completed/success`, but the connector does not expose job start timestamps. We therefore do **not** claim independent wall-clock chronology outside what the frozen source revision proves.

**Important residual limitations:** Full SHA-256 checks of compressed LongMemEval `report.rows.json.gz` data and all auxiliary files, independent scorecard/normalizer rebuild, executable same-harness comparison acceptance checks, and explicit owner approval of canonical `current.json` amendments are still not complete. The current dashboard must stay unchanged until these remaining gates are resolved.

**Recommendation strengthened:** Reconciliation of all eight missing v3–v6 lanes is now supported by *completed integration acceptance entries, 41/41 matched binding reports, 36/36 exact normalizer sources, 36/36 byte-verified primary result artifacts, and 4/4 freeze/declaration ancestry proofs*. The highest-value remaining work is verifying compressed/auxiliary bytes and running the deterministic rebuild/acceptance checks, not creating additional synthetic leaderboard examples. Keep each version/plane and comparator identity distinct.
