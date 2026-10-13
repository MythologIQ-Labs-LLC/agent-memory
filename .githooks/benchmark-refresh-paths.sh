#!/bin/sh
# Shared predicate for evidence-producing changes; invoked by both local hooks.
# Intentionally do not match generated scorecards/UI/normalized output (no loop).
benchmark_refresh_paths() {
  grep -E '^(reports/benchmarks/|data/benchmark-frontier-objectives[.]json$|reference/agentmem_ref/evaluation/(lanes/|integrations/|ui_catalog[.]py$|ui_frontier_leaderboard[.]py$|normalize[.]py$|scorecard[.]py$)|scripts/(build_benchmark_(scorecards|ui_catalog|frontier_leaderboards)|build_789_historical_ui|refresh_benchmark_pages)[.]py$|schemas/(benchmark-ui-|memory-benchmark-))' \
    | grep -Ev '^reports/benchmarks/(ui|normalized|scorecards)/'
}
