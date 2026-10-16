# #808 item 6: v1 envelope coverage of the historical normalized runs (proposed)

**Reproduce:** `python scripts/audit_historical_provenance_coverage.py`. It writes `historical-coverage.json`, which is deterministic on CPython 3.12 and 3.13.

**Inputs:** the 69 committed `reports/benchmarks/normalized/*.json` runs and their committed `execution_identity` artifacts.

**What this is not.** Nothing was backfilled or changed. Lane-level declarations, such as an embedder revision pinned in a lane file, do **not** count as per-run capture.

**States:**
- `recorded`: a machine-captured value is committed for that run.
- `not_recorded`: the value was not captured, and it stays absent.
- `evidence_gap`: v1 acceptance would need the value, and nothing committed can supply it.
- `not_applicable`: model identity for lexical or no-memory systems.

| Field family | recorded | not_recorded | evidence_gap | not_applicable |
|---|---:|---:|---:|---:|
| input SHA-256, system revision, adapter revision, OS/runner | 69 | — | — | — |
| dataset revision | 27 | 42 | — | — |
| configuration digest | 33 | 36 | — | — |
| start time + elapsed | 51 | 18 (all AMB lanes) | — | — |
| finish time | — | 69 | — | — |
| runtime version | 51 | 18 | — | — |
| dependency lock or resolved packages | 54 | 15 | — | — |
| source blobs | 36 (LongMemEval lanes) | 33 | — | — |
| workflow run id | 54 | 15 | — | — |
| peak memory | 51 | 18 | — | — |
| seed | 3 | 66 | — | — |
| container digest | — | 69 | — | — |
| native result with SHA-256 | 54 | 15 | — | — |
| row-level file with SHA-256 | 36 | 33 | — | — |
| CPU / RAM / GPU | — | — | **69** | — |
| stdout/stderr digests | — | — | **69** | — |
| per-run model identity | — | — | **41** | 28 |
| cost | — | — | **69** | — |

## Reading notes

- **AMB lane rows hold their per-case records inside the native `single-turn.json`**, which is hashed. So "row-level file not recorded" for AMB means there is no *separate* row file. The per-case records are not missing.
- **Every historical accepted lane row would fail v1 acceptance** on CPU/RAM/GPU, stdout/stderr digests, cost and, for systems with models, per-run model identity. That is expected:
  - the envelope is supplementary and is **not imposed retroactively** (`docs/benchmark-evidence-console-catalog.md`);
  - these rows stay accepted under their lane `evidence_history`.
- **The gaps are not zeros.** A UI must show them as `not_recorded` / `evidence_gap`, never as numeric zero.
- **Cost could become `not_applicable`** for lanes that use no billed inference, but only by an explicit owner declaration, never by default.
