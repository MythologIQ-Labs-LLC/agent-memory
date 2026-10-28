# #840 on the integrated v7 candidate: what was carried, what was not, and why

The base is `0f90aa8e`. The preregistration is in [`PREREGISTRATION.md`](PREREGISTRATION.md). PR #840
(`review/840-checkpoint-temp-isolation-no-ci` at `360de78f`, stacked on #836 `ab4e549d`) was **not merged**.

## 1. Temporary-file staging: carried as a minimal repair

**Finding (confirmed fail-first, `logs/fail-first-corrected-0f90aa8e.txt`).** Five integrated writers staged whole-file
writes through predictable temporaries, opened with truncation:

- the packaged runtime config on first open;
- `restart_runtime` checkpoint and manifest records;
- `configured_restart` records;
- `checkpoint_migration` records;
- journal restore.

An actor that can only create directory entries in a store could plant a symlink at the predictable name (S1, I2).
The store's own write then truncated and overwrote a file outside the store. Concurrent writers sharing one name
failed or tore (S3). A failed `fsync` or rename leaked the temporary (S4, S5, I1). The integrated #786 change had made
the config name per-writer (`pid` and thread), which fixed concurrency for that one writer but not predictability or
symlink following (S2).

**Repair (one helper in `runtime/restart_runtime.py`).**

- `_exclusive_temporary` creates the temporary with `O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC` under a 64-bit random
  name, with 8 attempts.
- `_stage_and_replace` writes, flushes and fsyncs it, renames it into place, and unlinks it on any failure before
  the rename.
- All five writers call it. Their function names, payload bytes, fsync and directory-fsync order are unchanged, so
  every existing fault-injection test that patches them by name still applies.
- File modes stay `0o666 & ~umask` (S6). This is the same decision the #821 generation witness made in review R-1.
  #840's `NamedTemporaryFile` would have published every durable file as `0o600`. That is a permission change, not
  part of the repair, and is left for an owner decision.

**Controls.** The #786 identity claim (`open("x")` and then `os.link`) and the #821 witness were already exclusive (I3,
I4 GREEN before and after). A file planted at the claim's predictable name can still make that one open fail. An actor
with write access to the root can equally write a bogus identity record, so this is availability, not integrity, and
it is not changed.

**Result after the repair (`logs/after-repair.txt`).** 10/10 GREEN. The related suites
(`test_821_atomic_config_binding`, `test_transactional_checkpoint_generations`, `test_checkpoint_migration`,
`test_786_store_open_contract`, `test_786_store_identity_profile`) pass 109/109. Store profiles, facade identity
binding and envelope contract 1.8.0 are untouched: the repair changes no surface logic beyond `_atomic_write_text`'s
body.

**Declaration.** Five protected files changed. `scripts/declare_runtime_baseline_changes.py` regenerated
`declared_changes`: 28 blobs, with `runtime/checkpoint_transactions.py` newly declared.

## 2. Host-activation guard: assessed, not carried

#840 adds `agentmem_ref.api.host_activation.open_qualified_memory`, plus an alias, a `restructure_package.py` layer entry
and a packaging test. It is a host-side context manager. It opens a facade and yields it only if
`legacy_upgrade_status()` is `fresh` or `legacy_qualified` with an exact integer `legacy_facts == 0`; otherwise it
closes the facade and raises.

I ran #840's own 11 tests against the integrated runtime, with its module loaded from a scratch overlay and nothing
committed (`logs/host-activation-overlay-on-integrated.txt`). 9 pass. 2 error: `test_explicitly_qualified_migration_can_activate`
and `test_legacy_pending_store_never_reaches_consumer`. In both, `AgentMemory.open` raises `StoreIdentityError` on the
multi-project #809 fixtures (`cross-scope`) before the guard runs.

Assessment against #809 legacy-store qualification:

1. **Not a runtime security repair.** Under #809, an un-upgraded legacy fact keeps its `episode_uuids` as its deletion
   dependency set (`_derivation_refs`). Existing data is never released from deletion completeness, and
   `legacy_upgrade_status()` is explicitly reporting, not authority. The guard is an activation *policy* a host may
   choose.
2. **Overlap with store-open 1.0.0.** A multi-project legacy store is already refused at `open`, for every project,
   and left untouched. That is stronger than the guard, but it also means the "explicitly qualified migration can
   activate" path is unreachable through the facade. This is the same open owner gap already recorded: the #809
   multi-project legacy upgrade.
3. **Where it adds behaviour.** A single-project legacy store opens restricted, and the guard would keep it from
   serving until it is upgraded and `legacy_qualified`.
4. **Cost.** It adds a new public API module to the protected surface. That means a new declared blob, a layer entry
   in `scripts/restructure_package.py` (the file that conflicts with the integrated head) and an architecture-index
   entry.

**Decision: not carried into the v7 candidate.** This is an owner decision: whether a host activation gate ships, in
v7 or as a post-v7 successor rebased on this head. If it ships, its two failing tests must be re-preregistered for
store-open 1.0.0, where the multi-project case is refused at open.
