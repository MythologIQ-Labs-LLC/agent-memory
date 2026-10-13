# Benchmark Frontier viewer (experimental)

Read-only local-first UI for [#779](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/779). This viewer consumes the derived **same-harness** frontier projection. It does not run memory benchmarks, alter accepted evidence, compare published vendor results numerically, or establish global best-in-class status.

## Build and open

From repository root, in a locally authorized environment (no GitHub Actions):

```bash
python -m unittest discover -s reference/tests -t reference -p 'test_779_metric_frontier_projection.py'
python scripts/build_benchmark_frontier_leaderboards.py --write
python scripts/build_benchmark_frontier_leaderboards.py --check
python -m http.server 8765 --directory reports/benchmarks/ui
```

Open http://localhost:8765/ in a browser. The viewer loads `frontier-leaderboards.json` beside `index.html`. Alternatively, open `index.html` directly and choose the generated JSON file through the file selector.

The command `--write` writes **only** the canonical derived JSON file under `reports/benchmarks/ui/`; the builder prohibits arbitrary overwrites inside the checkout. Run the catalog builder separately only when upstream accepted evidence legitimately changes. Do not regenerate frozen evidence merely to improve a leaderboard.

## Interpretation

- **Ranked:** Agent Memory and at least one other eligible same-harness measurement share exact comparable identity, native metric direction, unit, denominator and population. Gap is positive when Agent Memory is behind, and zero for measured ties/leads.
- **No peer:** Agent Memory has a measurement, but no comparable other system. A zero deficit is not fabricated.
- **Agent Memory missing:** Some measurements exist but no qualified Agent Memory observation; cannot report its gap.
- **Non-comparable:** The evidence class, protocol identity or native metadata is not eligible.
- **Coverage only:** Metric is registered but has no comparison row in the projection.
- **Adequacy:** No numerical threshold is implied by leadership. Adequacy is independently established and remains unknown when unqualified.

Ratios are displayed as percentage scores and percentage-**point** deficits. The bar width is relative to the within-metric leader score, not a global quality scale. Evidence inspection displays the comparison set, dataset selection, source run identity, revision, and the evidence pointers present in the generated projection.

## Outstanding qualification gates

1. Execute focused tests and browser inspection against the actual accepted catalog.
2. Confirm catalog metric keys and scorecard system identities match projection semantics across all accepted comparison sets.
3. Reject stale or incomplete run-provenance identities and establish explicit repeated-run selection policy.
4. Connect objective/deficit ownership only after validating PR #768's registry contract.
5. Add adequacy targets **only** from approved native evidence, plus immutable historical snapshot sharing.
6. Perform WCAG/keyboard/mobile behavior review and independent falsification.

The current UI is an engineering preview, **not** a qualified external leaderboard or an approved public deployment.
