# Independent clean-install and consumer delivery qualification: v7 candidate at `3df781c2`

Independent release / consumer-integration engineer, 2026-10-21. Target PR #836 head
`3df781c2efbfd122b8dc29f37b09efa8037f1dd3` (refreshed at execution: unchanged), repaired runtime `2ad4cf23`,
protected tree `f9b5ff9e79a54ef053ce89eb975256b63e211714`, declaration blob `7de94f11`. Executed in an isolated,
clean, full-history worktree. No accepted v6 bytes, frozen benchmark evidence, protected runtime, register, lane or
gold changed; no Actions, no paid inference, no benchmark rerun. Raw receipts sit beside this file.

## 1. Source identity (worktree at `3df781c2`)

All **21 declared protected blobs match** `git rev-parse HEAD:<path>` (0 mismatches), including
`runtime/recall_control.py` `9fa861c3`; `check_runtime_baseline_equivalence.py --candidate HEAD` reads
`TRANSITION` (frozen `e98e6e7b` + 21 blobs, `1.6.0 -> 1.8.0`); the register's last entry is still v6
(`published_commit b08cd844`, no declared successor row); `api/contract.py` reads `CONTRACT_VERSION = "1.8.0"`
(provisional). Candidate status: open v7 transition, not accepted.

## 2. Build and install (`build.log`, `dist-sha256.txt`, `environment.txt`)

`python3 -m build` from the clean worktree produced `agent_memory_reference-0.2.0-py3-none-any.whl`
(sha256 `d5a23a68…`, 452 files: `agentmem_ref` with 74 packaged `_schemas/*.json`, `_profiles/rc1-local.json`,
20 evaluation JSON files, console entry point `agent-memory = agentmem_ref.console:main`) and
`agent_memory_reference-0.2.0.tar.gz` (sha256 `68a4c13c…`, 479 files: root `schemas/` and the `setup.py` build
hook; no tests, no `_schemas`). The tree was clean after the build (`_schemas/`, `dist/`, `egg-info` are ignored;
the egg-info was removed before any further step).

Four fresh `python -m venv` environments, no editable install, `PYTHONPATH` unset, cwd `/tmp`, scripts run with
`python -I`:

| venv | Python | distribution | import resolves to | `pip check` |
|---|---|---|---|---|
| venv-wheel | 3.13.16 | wheel | its own `site-packages/agentmem_ref` | clean |
| venv-sdist | 3.13.16 | sdist (isolated build from the tarball) | its own `site-packages/agentmem_ref` | clean |
| venv-wheel-py3.12 | 3.12.3 | wheel | its own `site-packages/agentmem_ref` | clean |
| venv-wheel-py3.11 | 3.11.17 (declared minimum) | wheel | its own `site-packages/agentmem_ref` | clean |

`direct_url.json` records `archive_info` (not editable) in every venv; `agentmem_ref` is importable nowhere on the
machine outside these venvs and the checkouts. Imports of the facade, console and runtime CLI are clean under
`-W error::DeprecationWarning`.

## 3. Installed CLI (`cli-smoke.txt`)

`agent-memory --help` (runtime commands `config`, `discover`, `doctor`), `agent-memory gauntlet list` (profiles
listed), `agent-memory benchmark --help` (evaluation commands) all run from the installed script. On a state
directory created through the facade, `config validate --json` reports the packaged profile
`rc1-local-sqlite-composition` with digest `sha256:a0ed2202…` and `doctor --state-dir … --json` reports
`configuration.status valid`, `durable_state.status recovered`, `configuration_binding_scheme sqlite_transaction`,
provider availability `not_probed` (as designed). Identical on the sdist install and on 3.11 / 3.12.
Note for consumers: the evaluation CLI is reached as `agent-memory benchmark`, not `evaluation`.

## 4. Public facade lifecycle through the installed package (`consumer_lifecycle.py`, `lifecycle/`)

Eleven steps, all OK, with byte-identical step results across wheel, sdist, 3.11, 3.12 and 3.13:

1. `AgentMemory.open` (tenant `tenant:consumer`, scope `project:alpha`), `contract_version 1.8.0`; `remember` ×2
   committed at stage `commit`; `recall` admits and returns the fact; `history` v1; `posture` stage `posture`,
   `durable_state.configuration_binding_scheme sqlite_transaction`.
2. `correct` without evidence parks (`require_review`, state unchanged); with qualified evidence
   (`procedural_memory.SkillArtifact` → `evidence_for`, the same construction the source facade test uses) commits
   `allow_with_ledger`, history v2, recall admits the new fact and not the old.
3. Reversible `forget` with evidence: `allow_with_ledger`, history `tombstoned`, public events empty, no deleted
   identifier in the public history projection, recall admits nothing for that id.
4. `forget(permanent=True)` without evidence: not committed (`require_external_verification`); the memory stays current.
5. `close` then reopen in-process: the live memory is admitted, the deleted one stays tombstoned and unadmitted.
6. **Process restart** (separate interpreter, cwd `/tmp`): same results; posture binding `sqlite_transaction`.
7. Re-creating the deleted logical id as a fresh generation commits (v1); the old generation's identifiers appear in
   neither `admitted` nor `candidates`.

## 5. Negative tests (`lifecycle/report-*.json`, step `interrupted_recovery_and_integrity_negatives` and the two scope steps)

| Case | Outcome |
|---|---|
| Cross-tenant: open the same state with `tenant:other` | refused before any read: `RuntimeRecoveryError: requested tenant 'tenant:other' does not match recovered runtime tenant 'tenant:consumer'` |
| Cross-project: same tenant, scope `project:beta` | recall: `admitted []`, `candidates []`; `correct` of the alpha memory refused `fact_not_found`; history reads version 0 with no current fact (no existence oracle); alpha's memory unchanged (v1) when reopened in its own scope |
| Deleted-content reappearance after restart and after id re-creation | none (steps 5–7) |
| Binding file present, no database (interrupted first open) | refused `incomplete durable state: configuration binding exists without SQLite runtime database`; no database created |
| `runtime-config.json` deleted from a populated state | opens: the file is regenerated **byte-identical** (same sha256) from the packaged profile and the existing state is recovered, not replaced |
| Database truncated to half | refused, `sqlite3.DatabaseError: database disk image is malformed` (fail closed; raw driver error, not a typed `RuntimeRecoveryError`) |
| Fact row text edited directly in SQLite | refused, `RuntimeRecoveryError: SQLite canonical substrate digest mismatch` |
| Extra key written into `generation-witness.json` | opens: by #821 design the legacy file is not consulted while the SQLite binding table exists (`sqlite_transaction`); the row-level checks above are the live integrity boundary |

## 6. Package data and resource loading

Packaged profile loads through `importlib.resources`; schema validation of every envelope above ran from the packaged
`_schemas` (the source `schemas/` directory does not exist relative to an installed package:
`receipts._SOURCE_SCHEMAS` absent, 74 packaged schemas present). No missing-resource failure occurred in any step.
Optional extras (`semantic`, `comparators`) were not installed; nothing in the consumer path required them.

## 7. Installed behaviour versus the source-tree test suite

Both runs use the same test tree at `3df781c2` (`fullsuite-source-3df781c2.txt`, `fullsuite-installed-wheel.txt`,
`installed-failures-classified.txt`, `installed-failure-classes.txt`).

**Source tree** (worktree, system Python 3.13.16, `reference/requirements.txt` pins): 3161 tests, 6 failures + 1 error,
22 skipped. Five are the candidate's known environment failures (Gauntlet external example and durability adapters
blocked in this container, the benchmark-author golden path, the missing wave-2 harvest fixture, the two #770 freshness
guards). **One is new on the #836 head:** `test_809_legacy_upgrade.Fixtures.test_the_v7_gauntlet_adapter_pins_the_same_revision`
asserts the v7 Gauntlet adapter still pins `16a248b1`; the re-pin to `2ad4cf23` folded in by merge `4fb11a59` makes that
coupling stale (the fixture stores remain produced by `16a248b1`, which is an ancestor of `2ad4cf23`). It is a test-only
regression of the fold-in, not a runtime defect; this branch carries the minimal correction (assert the producer revision
is an ancestor of the adapter pin; 23/23 in the module afterwards). With full history the register-pin tests pass, and the
Gauntlet identity test passes after the re-pin.

**Installed wheel** (checkout copy with `reference/agentmem_ref` removed, no `.git`, venv without optional extras): 3084
tests, 14 failures + 219 errors, 43 skipped, 2807 passed. Every failure and error is checkout-bound, none is a behavioural
difference of the installed runtime:

| Class | Count | Nature |
|---|---|---|
| tests that hash or execute source files under `reference/agentmem_ref/…` | 33 | source removed by design of the experiment |
| evaluation / harvest / benchmark tests resolving `fixtures/`, `docs/explorations/`, `examples/`, `reports/` relative to the package parent | 34 (+ dependents) | the evaluation tooling expects a repository checkout; outside the consumer runtime surface |
| git-dependent evidence verification (`test_644_v7_replays`, `test_786_*`, `test_809_security_replay_v1`, `test_835_*`, `test_770_*`) | ~25 | `git` refuses outside a repository (`CalledProcessError`) |
| `test_644_v7_gauntlet_identity` | 2 | the adapter refuses a package that is not its checkout (`system_error`), exactly the fail-closed behaviour #838 qualified |
| optional or repository dependencies absent in the venv (`numpy`, `yaml`, `scripts/check_runtime_baseline_equivalence`) | 4 modules (incl. 40 in `test_runtime_baseline_succession`) | not runtime dependencies; declared extras or repository scripts |
| source-tree path expectations (`test_packaged_schema_resolution`, `test_receipts_schema_location`, `test_package_layout`) | 3 | they assert the resolved schema directory is the checkout's `schemas/`; the installed package resolved its packaged `_schemas`, which is the designed fallback consumers get |
| `test_809_legacy_upgrade` stale adapter pin | 1 | the same fold-in regression as in the source run |

Installed evaluation CLI outside a checkout: `benchmark list` (6 integrations) and `benchmark lanes` (14 lanes) read the
packaged evaluation JSON and exit 0; running a benchmark or verifying evidence needs the repository, as their listings say.
No facade, runtime, governance, recall, deletion, restart or replay-semantics test that can run without checkout resources
behaved differently against the installed wheel.

## 8. Secondary: #837 and #838 incorporation

At `3df781c2` neither `reference/tests/test_836_opaque_budget_repair_controls.py` nor
`reports/validation/644-v7-gauntlet-2ad4cf23/` exists; `92eecd6` (#837) and `baeb5a76` (#838) are not ancestors of
the head, while the four Gauntlet re-pin commits (`0cd11caa`…`97368d67`) are (merge `4fb11a59`). Both PRs merge
cleanly onto the head by `git merge-tree`. Their content is uniquely additive: #837's twelve control tests and clean-tree
replay/suite receipts, #838's seven-arm fail-closed matrix and independent probe record (the owner's own folded-head
run lives separately under `gauntlet-4fb11a59/`). Neither should be merged by anyone without re-checking blob identity
at integration time; nothing here merges them.

## 9. Disposition

**PASS for clean-install qualification of the consumer runtime path** (wheel and sdist; Python 3.11, 3.12, 3.13):
a developer can install `agent-memory-reference` from either distribution into a fresh environment and, with no
repository checkout, open, remember, recall, correct with qualified evidence, forget, reopen, restart and inspect with
`agent-memory doctor`, with isolation and recovery guards holding. This is package delivery evidence for the candidate
runtime; it is not Runtime Baseline v7 acceptance, security sign-off, acceptance of contract `1.8.0`, or a benchmark claim.

Minimum changes to make the candidate deliverable (none alters protected runtime code):

1. **CHANGES REQUIRED on the #836 head (test-only):** repair the `test_809_legacy_upgrade` adapter-pin coupling broken by
   the Gauntlet fold-in; the correction is on this branch (#837).
2. **Before publishing a v7 distribution:** the package version is still `0.2.0`, identical to the v6-published
   distribution, while the public contract moves `1.6.0 -> 1.8.0`; the declaration records `pyproject_change: null`.
   An installed `0.2.0` cannot be told from v6 by `pip`. A version bump recorded through the declaration is needed at
   publication time (owner decision; not required for this install qualification).
3. Non-blocking observations: a truncated database surfaces as a raw `sqlite3.DatabaseError` rather than a typed recovery
   error (fail-closed either way); the evaluation CLI is reached as `agent-memory benchmark` and its execution paths are
   checkout-bound, which consumer docs could state; the Gauntlet orchestrator artifacts do not carry the adapter's runtime
   identity (already noted on #838).

Integration disposition for the review PRs: #837 (twelve control tests, clean-tree replay/suite receipts, this record, the
test correction) and #838 (independent probe and seven-arm fail-closed matrix) are uniquely additive at `3df781c2`, merge
cleanly, and change no protected blob; integration remains the owner's call after blob identity is rechecked at that time.
