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
