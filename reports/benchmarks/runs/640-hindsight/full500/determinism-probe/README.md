# Hindsight chunk-only ordering instability: cause shown (diagnostic, #640/#810)

**Diagnostic only.** This is not a score and not a benchmark row. Script:
`reference/hindsight_determinism_probe.py`.

## Setup

- Same host, same pinned Hindsight 0.10.2 configuration as the scored lane.
- Run as the unprivileged run user with a separate pg0 home, so it ran alongside the full-500
  run without touching it.
- 10 LongMemEval session-plane questions, fixed in `question-ids.txt` and committed before the
  probe ran: `ef66a6e5` (the question whose nDCG changed across hosts) plus the first 9 other
  questions whose order differed across hosts.

## What was tested

- **Query time:** recall 3 times on one bank.
- **Ingest time:** ingest the same corpus into a fresh bank and recall once.
- **Attribution:** Hindsight's own `trace` (`probe.json.gz`) supplies per-arm ranks and scores.
  Chunk text is replaced by its sha256; nothing else is changed.

## Results

| Test | Result |
|---|---|
| Same bank, 3 recalls | **10/10 identical.** Query time is deterministic |
| Fresh bank vs first bank: returned set | **10/10 identical** |
| Fresh bank vs first bank: order | **8/10 differ** (first divergence at rank 1–8) |
| Semantic-arm (e5-small) rank changes across banks | 1/10 questions (1 chunk) |
| BM25-arm rank changes across banks | **10/10 questions** (2–36 chunks each) |
| BM25-arm scores across banks | identical in 9/10, as multisets |
| BM25-arm scores within one recall | heavily tied: e.g. 40 hits with 7 distinct values, 33 tied |

## Mechanism (demonstrated)

1. With the default `text_search_extension = "native"`, Hindsight's BM25 arm is
   `ORDER BY ts_rank_cd(search_vector, to_tsquery(...)) DESC LIMIT …`
   (`hindsight_api/engine/sql/postgresql.py`, native branch). There is no secondary sort key.
2. `ts_rank_cd` produces coarse values (multiples of about 0.1 here), so most BM25 hits tie.
3. PostgreSQL returns tied rows in physical or plan order. A fresh ingestion writes new rows with
   new UUIDs, so ties come back in a different order.
4. The tie order becomes different `bm25_rank` values. RRF turns those into different fused
   scores, and so into a different final order.

## Consequences

- **The returned set is stable at Hindsight's depth.** It is not stable at a tight budget: one AMB
  case with budget 2 swapped one item (`../../amb-precisionmembench-single-turn/`).
- **recall_all@5/@10/@50 are unchanged in every repeat so far.** Shallow cutoffs and nDCG can
  move. Across hosts, nDCG changed on `ef66a6e5` and `gpt4_45189cb4`, and recall_all@3 changed on
  `gpt4_45189cb4`. On this host, `ef66a6e5`'s order was stable.
  *(Corrected after independent review.)*
- **This is product behaviour,** reproducible on any host. It is not adapter or harness noise.
  A deterministic secondary key, such as `id`, on the BM25 arm would remove it. That would be an
  upstream suggestion, not something applied here.

## Execution

`probe.exec.json`: exit 0, run as `benchrun` with an allowlisted environment and no credentials.
