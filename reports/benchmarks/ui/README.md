# Benchmark Frontier viewer

Read-only local-first UI for [#779](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/779) (parents #696, #699, #700). The viewer consumes the derived **same-harness** frontier projection `frontier-leaderboards.json`, generated from the committed F1 catalog `catalog.json`. It does not run memory benchmarks, alter accepted evidence, compare published vendor results numerically, or establish global best-in-class status.

## Build, check and open

From the repository root, in a locally authorized environment (no GitHub Actions):

```bash
python -m unittest discover -s reference/tests -t reference -p 'test_779_*.py'
python scripts/build_benchmark_frontier_leaderboards.py --write
python scripts/build_benchmark_frontier_leaderboards.py --check
python -m http.server 8765 --directory reports/benchmarks/ui
```

Open http://localhost:8765/ in a browser. The page is static (no build step, no external script or font) and loads `frontier-leaderboards.json` beside `index.html`. Alternatively open `index.html` directly and choose a generated JSON file through the file selector.

`--write` writes **only** the canonical derived `frontier-leaderboards.json`; the builder refuses any other path inside the checkout. `--check` fails when the committed projection is stale for the committed catalog; `reference/tests/test_779_frontier_real_catalog.py` enforces the same currency. Regenerate the F1 catalog separately only when upstream accepted evidence legitimately changes. Never regenerate frozen evidence to improve a leaderboard.

### Frontier objectives registry (optional)

```bash
# draft registry from an unmerged source: labelled DRAFT, ownership context only
python scripts/build_benchmark_frontier_leaderboards.py \
  --objectives /path/to/benchmark-frontier-objectives.json --output /tmp/frontier-draft.json
```

The committed artifact never embeds an explicitly supplied registry (`--write`/`--check` refuse `--objectives`). When `data/benchmark-frontier-objectives.json` exists in the checkout (PR #768 merged) the builder reads it automatically as `canonical`; otherwise the projection reports `absent` and still lists all nine Coverage Atlas families A–I. A registry is rejected unless it declares exactly families A–I, a read-only claims policy, issue owners on every objective and no numeric claims. Objective linkage to metric rows is a labelled `label_match` restricted to ledger-backed objectives with an exact native metric id; it never changes a rank, gap or eligibility.

## Reading the leaderboard

Every row is one native metric inside one F1 comparison set. States:

- **Ranked:** `same_harness`, `exact`, eligible for numeric delta; every ranked value has a complete run record whose benchmark, input digest, selection, sample count, task profile and system revision match the comparison identity; all systems share direction, unit, denominator and population. Rank is competition ranking (ties share a rank). Gap is `leader − Agent Memory` (higher is better) or `Agent Memory − leader` (lower is better), never negative; ratios are shown as percentage points.
- **Competitive position (ranked rows only):** *Leading vs external peer*, *Tied for lead*, *Leads controls only* (no external memory system measured; not a market position), *Behind external peer*, *Behind a control* (a lexical or no-memory baseline leads).
- **No comparable peer / Agent Memory not measured:** no gap is fabricated.
- **Non-comparable:** evidence class, protocol identity, provenance or native metadata is not eligible; the details panel lists every reason ("Why no numeric gap?").
- **Not measured / Not rankable:** no measured value, or only booleans/descriptive values.
- **Coverage only:** metric registered in the catalog without any comparison row.
- **Evidence currency:** *Current*, *Superseded* (a later accepted same-harness run of the same structural lineage exists), *Newer unaccepted evidence* (later Agent Memory runs exist but are not accepted same-harness lanes), *Chronology undetermined* (repeated runs without recorded start times). Lineage is structural (benchmark, input, selection, sample, system kinds, metric metadata), never parsed from lane labels.
- **Adequacy:** no numeric threshold exists in the catalog; every row says "Adequacy unknown". A lead is not adequacy.

Published references render in a separate section, are never ranked, and are listed under `external_competitors.published_only`; same-harness external systems appear under `external_competitors.same_harness_measured`.

Filters are URL-addressable through the location hash (`#benchmark=…&metric=…&state=ranked`). The page supports light and dark colour schemes, stacks table cells below 760 px, exposes every control to the keyboard, and conveys status with text and glyphs, not colour alone.

## Qualification evidence

`reference/tests/test_779_frontier_ui_browser.py` drives the page in headless Chromium (Playwright) against the projection built from the real catalog and against adversarial projections; it skips when Playwright or Chromium is absent. Screenshots from the last local run are in `evidence/` (see `evidence/README.md`).

Current snapshot facts (`as_of` 2026-10-07, evidence revision `ca0f9a74`): six accepted same-harness sets (AMB PrecisionMemBench v1/v2, LongMemEval_S parity v1/v2 session and turn), 58 ranked metric rows, one external same-harness competitor (`mem0-oss`), five published-only references. Lane generations v3–v6 are present in the catalog as `same_profile` only, because `reports/benchmarks/dashboard/current.json` lists only four accepted frozen lanes; they are flagged as newer unaccepted evidence and never ranked.

## Known limitations

- AMB run records carry no `started_at`, so AMB v1/v2 chronology is reported as undetermined rather than guessed.
- Adequacy targets remain unestablished; the deficit ledger's textual targets are not machine-readable thresholds and are not projected.
- The viewer is an engineering preview qualified locally, not an approved public deployment.
