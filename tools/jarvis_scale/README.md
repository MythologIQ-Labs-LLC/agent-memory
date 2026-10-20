# #825 Jarvis-scale synthetic adoption challenge: executable Phase 1

**Status:** local development smoke; not an accepted benchmark, not independent, not run against Jarvis, and **not an Agent Memory superiority claim**.

Read `docs/ARCHITECTURE_INDEX.md` and use #771's quality-axis contract and #554's system-neutral adapter posture before using these results for product decisions. This standalone standard-library probe deliberately doesn't redefine either authority.

## Reproduce

From this directory:

```bash
python -m unittest -v test_experiment.py
python experiment.py --size 19000 --seed 825 --budget 5 --repeats 3 --arms scan,indexed --out scale19000.json
```

The generator creates **19,000 synthetic episodic notes** plus 14 controlled synthetic facts/traps (19,014 total), independently generated task labels, fixed seed, separate scope, conflicting versions, an untrusted email, and no-answer cases. Neither the generator nor scorer reads retrieval outputs to build labels. All records are fabricated. The real developer's Jarvis installation and private memories were not accessed.

Arms:

- `scan`: Python token-overlap and full scan, diagnostic only.
- `indexed`: SQLite FTS5 with BM25, scoped query, parameterized SQL; the **primary optimized local baseline**. Index construction time is recorded separately.
- `agent-memory`: **optional**, uses `agentmem_ref.AgentMemory.open/remember/recall` on a fresh synthetic SQLite runtime state; no fake implementation. Run only from a checkout or environment where the real package is installed. This arm has now been **executed as a synthetic development diagnostic**, but remains **unqualified**; see the [2026-10-20 execution report](../../reports/benchmarks/precision-selectivity/2026-10-20-work/README.md). Any import/ingest failure is an error, never a zero score. A 19k-record ingest may be expensive.

`scan` and `indexed` use distinct ranking policies; speed comparisons are informative but they are not an ablation of indexing alone. No fair adoption winner can be declared until the actual Agent Memory arm has been executed with compatible budgets and capabilities, on the same hardware, and a stronger test cohort has been independently authored and frozen.

## Historical scan/indexed smoke (not qualified)

Run environment: Linux x86_64 (6.18.55), Python 3.13.5, SQLite 3.46.1 with FTS5, 5 vCPUs shown by the container on AMD EPYC 9V74, 19,014 records, 14 task cases, budget 5, three repetitions per case. Corpus SHA-256: `44e6ab69482359dcd79d27741f9094a8bccd3d92ff9b9bbe3af53b8b5dd66879`.

| Arm | Strict primary cases | Needed facts returned | Irrelevant returned | Forbidden returned | Correct no-answer abstentions | p50 warm query | p95 warm query | Ingest/index |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Python full scan | 1/13 | 11/11 | 42 | 2 | 0/2 | 55.746 ms | 64.382 ms | ~0.004 ms |
| SQLite FTS5 BM25 | 1/13 | 11/11 | 42 | 2 | 0/2 | 0.083 ms | 3.807 ms | 78.497 ms |
| Agent Memory | **not run** | not run | not run | not run | not run | not run | not run | not run |

These figures are single-machine smoke measurements, not multiple-host confidence intervals or a representative production workload. The corpus is mostly routine filler, and the task suite is deliberately small. Strict success is exact returned evidence with no extras, not end-to-end answer generation. Scope metadata is applied by baseline query routing and by the Agent Memory public scope, but the synthetic `source` and `trust` tags are **not** passed through both runtimes as equivalent authoritative metadata. The temporal test is reported separately because the corpus has no universally applied typed supersession relation.

## Next executable gates

1. **Executed, not qualified:** the real Agent Memory arm ran on the same 19k workload and host as FTS5. The [2026-10-20 report](../../reports/benchmarks/precision-selectivity/2026-10-20-work/README.md) records raw paired results and the CHANGES REQUIRED disposition; no superiority was demonstrated. Complete independent capability-equivalent qualification before an adoption decision.
2. Use #771's served-context scorer, if available, rather than accepting these preliminary summary metrics as a second canonical scoring system.
3. Independently author and freeze a larger, harder cohort before adjusting any runtime parameters. Test correction, provenance and multi-hop with explicit capability-aware metadata.
4. Measure ingestion incrementality, model cold-start, memory/disk use, repeatability and crash/restart on each arm.
5. Seek developer opt-in before any real Jarvis comparison. The real workload stays on the developer's machine. Compare against the indexed Jarvis baseline, not the old Python scan.

No hosted CI or paid inference was used for this smoke. 
