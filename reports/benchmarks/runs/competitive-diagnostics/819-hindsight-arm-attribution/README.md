# Which Hindsight arm surfaces the evidence Agent Memory ranks too low? (#819 diagnostic)

**Diagnostic only: an attribution inside Hindsight, not an intervention on Agent Memory.**
Script: `reference/hindsight_arm_attribution.py`. Execution: `attribution.exec.json` (exit 0,
1,644 s, run as `benchrun` with no credentials, on a separate pg0 home).

## Setup

- **Questions:** the 44 LongMemEval-S session-plane questions where frozen Agent Memory misses
  at @5 and a peer gets full recall (`question-ids.txt`, from
  `scripts/paired_longmemeval_systems.py`). Together they have 115 evidence sessions.
- **Hindsight run:** same pinned chunk-only configuration as the lane, one fresh bank per
  question, one recall with `trace=True`.
- **What is recorded:** for each evidence session, its best chunk rank in the semantic arm (local
  e5-small) and in the BM25 arm, its final document rank after RRF, and Agent Memory's document
  rank from the frozen controls.
- **Disclosure:** `summary.json` is aggregate-only. Per-question detail names evidence sessions
  and is not committed.

## Results

| Places the evidence session in its top 5 | All 115 evidence sessions |
|---|---:|
| Hindsight semantic arm alone | **109 (95%)** |
| Hindsight BM25 arm alone | 83 (72%) |
| Hindsight final (RRF) | 106 (92%) |
| Agent Memory | 62 (54%) |

45 evidence sessions are in Hindsight's top 5 but below Agent Memory's top 5. For those 45:

| Measure | Result |
|---|---|
| Semantic arm rank | top 5 for **44**; median rank 3 |
| BM25 arm rank | top 5 for 29; ranks 6–10 for 13; ranks 11–30 for 3 |
| Arm ranking the session higher | semantic 26, BM25 11, tie 8 |
| Agent Memory's rank | 6–10 for **30**; 11–30 for 14; >30 for 1 |

## What this shows and does not show

**Shown, as an attribution within Hindsight:**
- On the questions where Agent Memory loses, a dense embedding ranking alone puts nearly every
  piece of evidence (95%) in the top 5.
- Hindsight's own BM25 arm alone does better than Agent Memory's ordering, at 72% against 54%.
  So the deficit is not only the missing dense signal; Agent Memory's lexical ordering also trails
  a plain BM25 arm on this evidence.
- Agent Memory's misses are near misses: two thirds are at ranks 6–10.

**Not shown:**
- That adding a dense arm to Agent Memory would close the gap. Only an intervention on Agent
  Memory, run by the runtime owner, can test that.
- Anything about the turn plane.
