# #771 Cedarline second cross-domain quality holdout, frozen v1

**Status:** FROZEN BEFORE FIRST EXECUTION. NO AGENT MEMORY SCORE, BENCHMARK IMPROVEMENT, OR PASS CLAIM.
**Base evaluation:** `73030db8498c2f94d177ab1d52bebbc91242dab6` after independent E1–E5 evaluator repairs.
**Isolation:** branch `evaluation/771-cedarline-second-holdout-frozen-no-ci`; no protected runtime files modified, no Actions triggered.

## Reason for this independent corpus

The first *Halcyon* holdout was written by Claude Code and revealed multiple
genuine quality deficits. This second, **separately authored** cross-domain
Cedarline corpus is intended to test generality outside payment ledgers, in
a 17-year river-telemetry software environment.

**Qualification caveat:** The second corpus was authored after disclosure of
Halcyon's broad failure classes. It is independent in authorship, domain and
execution history, **not a blinded hidden benchmark** and **not independently
adjudicated gold**. A separate reviewer must challenge the labels and create
additional unseen cases before any global quality claim.

## Pre-registered scope

- `cedarline-independent-v1-input.json`: **32 chronological governed lifecycle
  events** (31 fact-creating), including multiple state updates, a separate
  error correction, deletion, a time-bounded winter deployment freeze,
  conflicting rumor vs approved policy, other-project memory and an entirely
  separate tenant with the same project ID.
- `cedarline-independent-v1-gold.json`: **24 questions**, **20 answerable**
  and **4 no-safe-answer**. Scopes: current, historical and timeless.
  Graded labels for **all 31 fact IDs on each question**, explicit
  task-critical evidence groups, stale and prohibited source sets.
- `cedarline-independent-v1-strata.json`: categorization for per-stratum
  reporting, never available to runtime or candidate ranking.
- **Current (2026) temporal anchor**: A declared winter firmware freeze
  ended 2025-12-01. Label it stale for current-intent questions, not for
  genuine historical questions seeking that interval.

Corpus content covers provenance, changes of scientific data format,
separate why-explanations, calibration measurement error correction,
incident cause, operational alerts, packet compression, bounded
compound questions and time-specific source applicability.

## Frozen identity

These are committed Git blob IDs, established by reading GitHub after the
three input/gold/stratum files were persisted:

| Artifact | Git blob SHA |
|---|---|
| Execution-only input | `b08e05d3250a8fa032a8e7f5f5f0030a9c5b637a` |
| Separate relevance gold | `1da8e7eb40a84a04604bcd21a820ef9688607312` |
| Strata mapping | `93e4ddc1cf0c3c8881d8b1b29a1ffbae3568127b` |

No execution has run on these files yet. Do not edit the gold after seeing
results; if a genuine annotation inconsistency is found, retain the original
files and publish a separately named v1.1 with a tracked correction and
explanation, exactly as Halcyon's history was preserved.

## Qualification commands (local or Claude cloud, NOT GitHub Actions)

Check out an isolated clean worktree containing both this branch's corpus
and evaluator implementation, and verify the above three blob SHAs.

```bash
python -m unittest discover -s tests -p 'test_served_memory_*.py'
python -m unittest discover -s reference/tests -t reference -p 'test_771_served_memory_integration.py'

python scripts/run_served_memory_lifecycle_scenarios.py \
  --inputs reference/fixtures/evaluation/cedarline-independent-v1-input.json \
  --backend composed-multiroute \
  --lane-id cedarline-composed-v1 \
  --store /tmp/cedarline-composed-store \
  --output /tmp/cedarline-composed-run.json

python scripts/qualify_served_memory_run.py \
  --inputs reference/fixtures/evaluation/cedarline-independent-v1-input.json \
  --gold reference/fixtures/evaluation/cedarline-independent-v1-gold.json \
  --runs /tmp/cedarline-composed-run.json \
  --output /tmp/cedarline-composed-quality.json
```

Repeat for governed-lexical in a **different new store** with a separate
lane ID. Lexical historical results are descriptive, not automatically
same-harness equivalent to a temporal-intent-aware composed path.

## Ground rules

1. Never give gold/strata to any runtime, route planner, memory writer or
   model-based ranking algorithm.
2. Never adjust source logic to satisfy this 24-question set.
3. Independently inspect case labels before any P0/P1/P2 release judgment.
4. Report per-question top1_critical, critical-group coverage, budgeted
   precision/recall, stale/prohibited exposure and no-safe-answer context.
5. Report benchmark and governance identity before and after any *future*
   protected runtime slice. The frozen #770 v7 declaration and v6 history
   remain immutable.
6. This corpus alone cannot qualify G1/G2/G6. Also require original AMB
   and LongMemEval same-harness, existing holdouts and one fresh blind set.

No PR, merge, runtime policy change, declared v7 evidence repin or release.
