# Evidence-driven benchmark refresh governance

**Status:** local implementation candidate, not a claim of a hosted always-on service.
**Owner:** benchmark evidence #601 / competitive expansion #789 / viewer #779.
**Operating rule:** no GitHub Actions, no automatic benchmark runs, no silent evidence acceptance.

## Invariant

Whenever source evidence, a lane identity, dashboard admission or objective registry changes, the *recording operation* is incomplete until all read-only projections match exactly that source revision and are included in the repository change. This is a delivery obligation, not a discretionary dashboard cleanup.

There are separate states:
- **Recorded:** immutable raw artifact + exact provenance; it may appear as a pending evidence source even if not normalized.
- **Qualified:** source registry/protocol validated; may appear in scorecards but is not automatically ranked.
- **Accepted:** reviewer-authorized dashboard acceptance *and* same-harness identity, comparability and complete evidence; only this category can affect leaderboard ranks.
- **Blocked/unregistered:** retain visibility and an owner; never turn missing sources into zero scores.

## One deterministic local command

After making the evidence-bearing commit:

\`\`\`bash
python scripts/refresh_benchmark_pages.py --write
python scripts/refresh_benchmark_pages.py --check
git add reports/benchmarks/normalized reports/benchmarks/scorecards reports/benchmarks/ui
git commit -m "chore(benchmarks): refresh recorded evidence projections [skip ci]"
\`\`\`

The refresh runs four **existing** generators in strict order: scorecards/normalized, F1 catalog, F2 frontier leaderboard, and the separate historical-v6 diagnostic. The manifest \`reports/benchmarks/ui/refresh-status.json\` fingerprints all discovered source JSONs and derived outputs. \`--check\` is read-only and fails if any projection, source hash or manifest changes. No generic source glob is promoted into rankings: scorecard source registration and dashboard admission remain explicit reviewer decisions.

The manifest exposes **unregistered \`evidence.json\` candidates** under AMB/LongMemEval as paths, not competitor wins. This is intentional: new results must become visible as pending even when protocol qualification is incomplete. Raw \`single-turn.json\` files also affect its source digest. The static page reads the manifest for evidence coverage; it does not confuse an updated repository projection with confirmed deployment freshness.

## Opt-in per-workspace automatic Git hooks

\`\`\`bash
python scripts/install_benchmark_refresh_hooks.py --install
git config --local --get core.hooksPath
\`\`\`

- \`.githooks/post-commit\` detects new committed benchmark source evidence, lane definition, dashboard decisions or source registration; if the workspace is clean, it invokes the refresh and writes **one companion projection commit** without running any benchmark. It will not stage unrelated work or rewrite frozen raw evidence.
- \`.githooks/pre-push\` requires \`--check\` to pass before local pushes. It rejects stale output even when the post-commit hook could not execute.
- The installer refuses to override any existing \`core.hooksPath\`. Git for Windows supports shell hooks when using the included Git shell. Each Claude/local workspace must install hooks separately.
- Commit messages include \`[skip ci]\`; this is not a guarantee that arbitrary repository workflows will ignore pushes. Avoid pushing repeatedly and explicitly inspect the project's workflows and Pages publishing configuration.

**Failure behavior:** If validation, packaging dependencies, an existing dirty tree or generated output disagrees, the hook reports a blocker. Post-commit cannot undo the already written source commit, so pre-push blocks publication until a clean, separately recorded repair. No fallback to bypass gates or publish partially regenerated outputs.

## Architectural limitation requiring an independent executor

Git hooks **do not run on GitHub's remote server**, API commits, PR merge endpoints, or on other machines without installing them. Therefore this implementation provides automatic updates on configured local/Claude workspaces, with fail-closed push governance, **not** a universal remote event guarantee. A GitHub webhook plus an independently authorized always-on non-Actions executor would be needed for fully automatic remote/API updates and public website publication. Until a publisher is deployed, repository artifact freshness is not proof that the GitHub Pages URL has refreshed.

## Validation gate

\`\`\`bash
python -m unittest discover -s reference/tests -t reference -p test_benchmark_refresh_governance.py -v
python scripts/refresh_benchmark_pages.py --write
python scripts/refresh_benchmark_pages.py --check
\`\`\`

Check source tampering, duplicate case detection in native builder, unregistered candidate flagging, rejected stale projection, idempotent second run, accepted-versus-unaccepted rankings unchanged, exact head, browser manifest read and zero Actions consumption. This governance is not accepted until the complete checkout passes these tests and the installer is run on every authorized evidence-recording workspace.
