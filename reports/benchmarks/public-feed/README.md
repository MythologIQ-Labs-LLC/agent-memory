# Public measurement feed (data only)

This branch is the read-only public measurement source for Agent Memory's existing GitHub Pages leaderboard.

**Website shape is frozen.** Updating a benchmark measurement requires a change to `reports/benchmarks/public-feed/v1.json`, not to the Pages HTML, CSS, leaderboard components, `main`, or `data/snapshot.json`.

## Contract

- Append a new profile when the **cohort, input selection, evaluator revision, protocol, metric, or runtime revision** changes. Never merge incompatible populations or quietly overwrite a historical score.
- Append a new competitor to an existing profile only when the evaluator protocol and cohort are genuinely comparable. Missing values remain missing, never zero.
- Every row identifies the source **40-character immutable Git SHA**, artifact path, **SHA-256** of the original raw report file, an exact scoring extractor, status, and source-derived expected score. For native LongMemEval reports, preserve input/selection identity, zero-error counters and scored/excluded denominator. Preserve engine revision bindings when supplied by the summary.
- `candidate` and `reviewed_self_run_unofficial` do **not** become accepted by appearing here. The site retrieves the original artifact, hashes its exact bytes using WebCrypto, recomputes the metric, compares it to the declared result, and refuses invalid rows.
- Runtime #819 C2 is a **self-measured candidate** pending an independent held-out assessment. It is compared to its prior runtime revision in separate diagnostic profiles; do not treat its revision rank as a product market rank. AMB improves while LongMemEval depth recall regresses. Neither direction may be hidden.
- Never expose a private dataset or user-specific memory record. Link evidence already intentionally committed to a public repository.
- Do not start hosted GitHub Actions or open a PR to publish updated data. Push only to this unprotected publication branch after independent source checking, checking that the ref hasn't moved; respect branch concurrency and record source SHA in the commit description.

## How an executor publishes

1. Commit the original run and manifest to its execution branch; freeze and report exact source SHA and SHA-256. Do not mutate those artifacts in place.
2. Add a candidate profile or a competitor row to `v1.json`. Preserve older results, including unfavorable numbers. Update `feed_revision` and commit message to reflect the run/revision.
3. Run the offline feed contract tests and independently inspect the source and metric denominators. Browser-side verification is additional protection, not a substitute for human review.
4. Push only this branch if the existing head has not drifted. The GitHub Pages site reads the new branch commit on refresh/visible-tab polling without a Pages deployment.

Accepted measurements still require the independent governance path and separate canonical accepted snapshot update. Do not infer acceptance from this feed. If source evidence fails, retain the previous score as explicitly historical or show no score rather than fabricating one.
