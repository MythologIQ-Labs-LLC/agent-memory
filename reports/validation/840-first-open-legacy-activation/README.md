# PR #840 independent security qualification: first-open configuration staging and legacy host activation

Independent adversarial qualification of draft PR #840 (`review/836-first-open-atomic-temporary-no-ci`),
the remediation slice for the two P1 findings of the v7 security challenge (PR #836 comment
6333772168). Executed in this cloud container (CPython 3.12.3, 4 vCPU, Linux 6.18), no GitHub
Actions, no model inference. The frozen v7 candidate (#836, protected tree `f9b5ff9e`, declaration
`7de94f11`), the v6 register, the #809 legacy fixtures and all accepted evidence are untouched.

| Revision | Role |
|---|---|
| `ab4e549d` | PR base: unmodified frozen v7 source (protected tree `f9b5ff9e`) |
| `e3176275` | PR head as handed off: 17 commits, 7 files; protected tree `83e44f04` (`api/surface.py` `ba8924d4` → `05100c82`, new `api/host_activation.py` `c63646f0`, alias `e63a7aa3`) |
| this folder's head | + strengthened test module (test-only, protected tree unchanged `83e44f04`) and this record |

## 1. Fail-first reproduction on the unmodified base (`probes/`, `logs/committed-tests-on-base-ab4e549d.txt`)

Direct probes (`probes/base_findings_probe.py`, output `probes/base_findings_probe.base-ab4e549d.txt`):

| Finding | Unmodified `ab4e549d` | PR head `e3176275` |
|---|---|---|
| B1 planted `.runtime-config.json.tmp` symlink, then first `AgentMemory.open()` | **victim file overwritten** with the default configuration; symlink consumed by the rename | victim intact; symlink left untouched; configuration created beside it |
| B2 two writers on the same target, paused at the rename boundary | one staging name (`.runtime-config.json.tmp`), second writer `FileNotFoundError` after the first renamed the shared inode | two private staging names, no errors, complete file published |
| A `legacy_pending` fixture (`809-legacy-stores/cross-scope`, 7 legacy facts) opened through plain `AgentMemory.open()` | `recall` admits 2 ids, `remember` commits | **same**: the default facade still admits it (the gate is opt-in, §3 F1) |

The PR's 17 committed tests run unmodified against the base: the first-open module fails 4 of 6
(symlink, two-thread, two-process staging, replace failure); `fsync` failure and the complete
two-process fresh-root case pass on the base (non-discriminating, §3 F2); the host-activation module
cannot import on the base (module absent), so finding A's fail-first evidence is the probe above.

## 2. Executed at the PR head `e3176275` (`logs/`)

| Gate | Result |
|---|---|
| 17 committed tests (`unittest`, from the repository root) | **17/17 OK** |
| `tests.test_package_layout` | 8 tests OK (3 skipped: optional numpy modules) |
| `scripts/restructure_package.py --check` | `layout matches table` |
| security / legacy-upgrade / cross-scope / SQLite durability / deletion / restart selection (31 modules: #809, #821, #816, #802, #786, #777, #835, SQLite, restart, deletion, durable, crash, witness, binding, doctor) | **375 passed**, 1 skipped, 1 xfail |
| full reference suite (repository root) | **3172 passed, 4 failed**, 27 skipped, 1 xfail, 2189 subtests. The four are the v7 identity guards (two #770 freshness guards, the #644 Gauntlet identity guard, the baseline-equivalence contract test): this branch changes a protected file, so they fail by design until a declaration covers it |
| 13 replay families (786 v2/v3, #809, #835 DSL/4, five #644) | all PASS, `observations_sha256` **identical** to the `2ad4cf23` v7 record (`replays/digest-comparison-vs-2ad4cf23.txt`); `verify_786`/`verify_644 --reexecute` 10/10 VERIFIED |
| #821 crash-window matrix (9 kill points) | outcome-identical to the v7 record |
| wheel + sdist (`git archive` at `e3176275`, `python -m build`, fresh venvs, `python -I` from outside the checkout) | both: `agentmem_ref.host_activation` is the `api` module object; installed helper uses the exclusive temporary; `legacy_pending` fixture refused, maintenance upgrade → `legacy_qualified` then activates with recall; `shared-membership` upgrade → `legacy_unqualified` refused; fresh store activates; planted-symlink first open leaves the victim intact (mode `0o600`); blank tenant refused (`install/install-smoke-e3176275.txt`) |

## 3. Adversarial challenge (`probes/helper_and_gate_edges.py`, `probes/forced_two_creator_race.py`)

**Temporary-file writer (`_atomic_write_text`).** `NamedTemporaryFile(delete=False)` creates
`.runtime-config.json.<random>.tmp` with `O_CREAT|O_EXCL` (and `O_NOFOLLOW` where the platform has it)
and mode `0600`; a planted symlink or another writer's file at that name makes creation fail and
`tempfile` picks another name, so no planted link is followed and no other writer's inode is
truncated. Cleanup unlinks only this writer's path (C1: an orphan temporary of a crashed writer is
untouched). A failure before `os.replace` (write, flush, `fsync`: C4, committed `fsync`/replace tests)
publishes nothing and leaves no staged file; a failure of `os.replace` preserves the target. A planted
symlink at the **final** path to a foreign file is loaded as configuration and refused by validation
(C2, `DiagnosticInputError`, victim intact); a dangling one is replaced by a regular file (C3). Within
the same-user-trusted threat model those are outside this finding. The published file is now `0600`
instead of umask-derived (C5): tighter, and immaterial in the single-user profile.
Windows: **NOT EXECUTED** (Linux container). By inspection `NamedTemporaryFile(delete=False)` closes
before `os.replace`, which replaces an existing target on Windows unless it is open elsewhere; that
raises, the temporary is unlinked, and the open fails closed. No Windows first-init test exists.

**Concurrent fresh-root initialization.** The committed two-process test passes on the unmodified
base as well: at the complete `open()` boundary the two workers serialise naturally (10 instrumented
rounds: 8× both OPENED, one created and one recovered; 2× one fail-closed `RuntimeRecoveryError`). It
is a positive control of #821, not a discriminator of #840. A deterministic variant that forces both
processes past the database-exists check and into `SQLiteConfiguredCompositionRuntime.create`
(`probes/forced_two_creator_race.py`, 12 rounds) always yields exactly one `OPENED` with a committed
write and one `REFUSED: RuntimeRecoveryError("SQLite runtime state already exists; use recover()")`;
every root reopens `fresh` with exactly the survivor's fact and no staged file. The property holds
because generation 1 and its binding commit in one SQLite transaction (#821) and the witness writer
already uses an exclusive per-writer temporary; #840 removes the last predictable temporary on that
path. Added as `test_forced_two_creator_race_admits_exactly_one_initializer` (§4).

**Remaining fixed-name temporaries** (`.<name>.tmp`, truncating open) in the tree: the legacy
file-binding writer (`configured_restart._atomic_json_write`, pre-#821 file profile), the JSON
checkpoint profile (`restart_runtime._atomic_json_write`), `checkpoint_transactions`,
`memory/checkpoint_migration`, and two evaluation writers. None is on the supported single-user
SQLite profile's runtime path (binding is a DB row, witness is exclusive); they remain the #823
follow-up and are **not** fixed by #840.

**Host activation gate.** Admits only `fresh` / `legacy_qualified` with `legacy_facts` exactly `int`
`0` (`bool` excluded); refuses `legacy_pending`, `legacy_unqualified`, unknown statuses, malformed
counters and a stale `legacy_qualified` label with reappeared legacy facts; closes the handle on every
refusal and on exceptions from the status read (C8: also on `BaseException` inside the `with`).
Requires non-blank `tenant`, `actor_id`, `scope` before any runtime is opened; the runtime itself
refuses a tenant that does not match the store (C7). `legacy_facts` is recomputed from the store on
every call, so a forged persisted label cannot pass with remaining legacy facts. The yielded handle is
the full facade: a consumer may run `upgrade_canonical_derivation()` itself (C6); that is an explicit
governed operation and cannot make an unqualified store pass (`legacy_unqualified` stays refused), so
it is not a bypass of the gate's property, but the "privileged migration-only path" the challenge asked
for is not enforced by the gate.

**F1, the controlling finding: the gate is opt-in.** `AgentMemory.open()` and `recall()` are
unchanged on this path; the `legacy_pending` fixture opens and serves recall and writes through the
default facade at the PR head exactly as on the base (§1, row A; C6). The challenge's acceptance
condition was (1) a tested fail-closed activation policy, or (2) a consumer-host integration receipt
proving enforcement before any end-user recall. #840 supplies an installable gate and its tests, which
is neither by itself. It is sufficient **only** for a declared profile in which the embedding host
is required to open stores through `open_qualified_memory` (or an equivalent host check) and that
adoption is evidenced; it is **not** sufficient for an unrestricted consumer profile, and plain
`AgentMemory.open()` must not be described as protected. Making the facade fail closed by default
(refusing `legacy_pending`/`legacy_unqualified` unless a maintenance flag is passed) is a protected
behaviour change with #809 test consequences and is the owner's decision, not made here.

**Package governance.** `host_activation` is registered in the `api` layer; the generated alias
matches the mover's template byte for byte (`restructure_package.py --check`), the alias is the same
module object from source and from both installed distributions, and `test_package_layout` passes.
`examples/qualified_memory_host.py` only re-exports the packaged gate. The branch is based on
`ab4e549d` and does not carry #836's later docs-only `f4386e2a`; it merges cleanly.

## 4. Remediation on the PR branch (test-only)

- `test_fsync_failure_never_publishes_incomplete_target`: the leftover check now asserts that the
  directory holds only the target. The committed assertion globbed `.runtime-config.json.*.tmp`, which
  the base's `.runtime-config.json.tmp` never matches, so the control passed on the base (vacuous).
  Strengthened module on the base: 5 of 7 RED (`logs/strengthened-first-open-tests-on-base-ab4e549d.txt`).
- `test_forced_two_creator_race_admits_exactly_one_initializer`: the deterministic two-creator race
  of §3, asserting one `OPENED` with a committed write, one `RuntimeRecoveryError` refusal, no staged
  file, and a clean `fresh` reopen holding exactly the survivor's fact. Passes on both trees (a #821
  property), so it is a positive control, not a #840 discriminator.
- PR head after remediation: 18 tests OK (`logs/strengthened-tests-pr-head.txt`). No implementation
  defect was confirmed; no production code changed.

## 5. Disposition

**READY FOR INTEGRATION REVIEW as an isolated remediation slice**, with one explicit release
blocker and two retained risks:

- Blocker (owner decision): F1. Either declare the supported profile as "legacy stores are NO-GO
  unless the host opens through the packaged gate" and require a consumer-host adoption receipt, or
  direct a facade-level fail-closed default. Until one is recorded, the legacy finding is remediated
  for adopting hosts only.
- Retained: Windows NOT EXECUTED; the remaining fixed-name temporaries outside the SQLite profile
  (#823); same-user malicious planting at the final configuration path (threat-model exclusion).
- Not changed by this qualification: v7 remains HOLD; contract `1.8.0` stays as accepted; #839 is
  independent; nothing is merged, published or re-pinned.

**v7 or successor.** The first-open fix edits a protected file. Folding it into #836 re-opens the
frozen tree: amended declaration (new blob), regenerated committed replay roots (digests already
identical), Gauntlet re-pin, and re-import of the nine lane rows that pin `7de94f11`. Retaining it for
the next declared successor keeps v7's evidence intact but requires v7's supported profile to exclude
concurrent first initialization and pre-#809 stores without the host gate. Recommendation: retain for
the declared successor together with #839 unless the owner rejects those two v7 profile exclusions,
in which case fold in and requalify before publication; never inherit the 21-blob pins.
