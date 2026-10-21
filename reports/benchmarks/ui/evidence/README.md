# Frontier viewer browser evidence

Screenshots produced by `reference/tests/test_779_frontier_ui_browser.py` in headless Chromium against the projection built from the committed F1 catalog (snapshot `as_of` 2026-10-07). Regenerate with:

```bash
FRONTIER_UI_EVIDENCE_DIR=$PWD/reports/benchmarks/ui/evidence \
python -m unittest discover -s reference/tests -t reference -p 'test_779_frontier_ui_browser.py'
```

| File | Viewport | What it shows |
| --- | --- | --- |
| `desktop-known-row-behind-external.png` | 1366×900, full page | LongMemEval_S parity-v2 turn `recall_all@50`: Mem0 OSS 89.50 %, Agent Memory 85.92 % rank 2 of 3, 3.58 pp gap bar with text label, "Behind external peer", "Newer unaccepted evidence", "Adequacy unknown". |
| `desktop-behind-control.png` | 1366×900, full page | parity-v2 turn `latest_gold_ranked_first`: lexical control leads (61.43 %), Agent Memory 5.71 pp behind, labelled "Behind a control". |
| `desktop-details-expanded-keyboard.png` | 1366×900, full page | Details opened with the keyboard: per-metric ranked table with roles, "Why comparable?", provenance (runs, revisions, evidence URIs with digests), chronology, ownership. |
| `desktop-non-comparable-why-not.png` | 1366×900, full page | parity-v6 turn row: non-comparable, "No numeric gap", "Why no numeric gap?" explanation. |
| `desktop-overview.png` | 1366×900, viewport | Unfiltered overview with coverage counts and filters. |
| `desktop-draft-objectives.png` | 1366×900, full page | Synthetic draft registry attached: "registry: DRAFT" label, family B objective, ownership shown in details with the DRAFT marker. |
| `desktop-refused-aggregate-score.png` | 1366×900, viewport | A projection carrying an aggregate score, an unsupported schema, an authority claim or a missing shape is refused with a visible error. |
| `desktop-tampered-rows-refused.png` | 1366×900, full page | Eight tampered rows (string leader, negative gap, ratio above one, empty ranking, unknown state, leader without ranking, descriptive direction, missing leader) render as "Invalid row, refused" with no number, no bar and no win. |
| `mobile-details.png` | 390×844, full page | Stacked cells with labels, no horizontal page scroll, details open. |
