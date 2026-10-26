# #821 preregistration amendment 1 (after the independent review at `69ccd3a6`)

**Status:** preregistered before the repairs it governs. The original preregistration is
unchanged; this file adds to it. Review: `review/REVIEW-821-independent.md`.

## Why

The in-transaction binding held under every attack (no split state, no false acceptance), but
removing `configuration-binding.json` from new stores also removed the only durable witness
outside the database. Two fail-closed properties of the base regressed:

- **F1 (blocking):** a store whose database file is lost was re-created as empty memory, because
  nothing outside the database said a store had existed.
- **F2:** restoring only an older copy of the database file was accepted; the base refused it
  (incidentally, through the lagging file).

F3 found a downgrade: when the row was missing but the table existed, recovery still fell back to
the weaker legacy file check.

## Added protocol: the generation witness (`generation-witness.json`)

An advisory high-water mark `{schema, generation, journal_record_digest}` beside the database.

- **Written** by a #821 runtime only:
  - at create, with generation 0, before any database transaction;
  - after every COMMIT, with that generation's journal record digest. The write is atomic
    (temporary file, fsync, rename, directory fsync).
  - Recovery and `close()` never write it.
- **It can only refuse; it never accepts.** It is written strictly after the commit it names, so it
  can lag the database (a crash or power loss after COMMIT) but never lead it. A lagging witness is
  accepted, so it cannot reopen the #821 window.
- **Recovery refuses** when:
  - (W1) the witness names a generation above the database's;
  - (W2) the database's verified journal record at the witness generation has a different digest
    (another store's database, or a rollback that diverged);
  - (W3) the witness is unreadable or malformed.
- **`AgentMemory.open`, `create` and doctor refuse** a witness without a database (W4: never
  reinitialize).
- **No witness** (a pre-#821 store, or a deleted witness) means no detection, never a refusal.
  This is the documented residual: the witness is not a keyed or remote anchor.
- **If the post-commit witness write fails** with `OSError`, the committed generation stays
  committed and the caller is not told it failed. The handle records
  `generation_witness_current = False`, and the next generation writes the witness again. A
  lagging witness is safe by construction. An interrupt (`BaseException`) still propagates.

## Added rules

- **A4' (F3).** If the binding table exists, the row is required: an empty or ambiguous table is
  refused as corrupt, and the legacy file is consulted only when the table does not exist. Dropping
  the whole table and forging a matching legacy file is the residual of any unkeyed in-database
  binding, and is recorded as such.
- **A5' (F5).** Before replacing the row, the binder verifies it exactly as recovery would, against
  the handle's previous published or verified generation: seal, protocol, tenant, generation,
  base digests and journal-tail digest (the new journal record's `previous_record_digest`). Then
  the configuration checks. Any failure raises `RuntimeCheckpointConflict` and rolls the generation
  back, with the verifier's own diagnostic.
- **A11 (F8b).** The binder refuses to bind a generation whose visibility obligations the bound plan
  does not require (`_assert_visibility_matches_plan`). Such a generation used to commit and then
  strand the store at recovery. Now it rolls back.
- **F6.** On a failed SQLite recovery, doctor reports `configuration_binding_present` from the row
  as well as the file, read-only, and `configuration_binding_scheme: "unverified"`.
- **F9.** `SQLiteRestartSafeRuntime.create` closes its substrate if generation 1 fails. Docs
  say: "unkeyed checksum"; storage-level holders can write rows (#816 privileged layer); migration
  is one-way.

## Added matrix rows (tests in `test_821_atomic_config_binding.py`)

| # | Case | Expected |
|---|---|---|
| M22 | database file deleted, witness present | `open`, `create` and doctor refuse; nothing created |
| M23 | database file replaced by an older copy of itself | refused (W1) |
| M24 | database file replaced by another store's database at the same or higher generation | refused (W2), or by W1 if lower |
| M25 | witness lags (crash after COMMIT, before the witness write) | recovers the committed generation |
| M26 | witness corrupt | refused (W3) |
| M27 | witness write fails with `OSError` after COMMIT | operation reports success; next generation rewrites the witness; reopen recovers |
| M28 | table present, row missing; with or without a verifying legacy file | refused as corrupt; file not consulted |
| M29 | row rewritten out of band while a handle is open | next generation refused with `RuntimeCheckpointConflict`, rolled back |
| M30 | base driven directly with a visibility snapshot the plan does not require | refused and rolled back; the store stays openable |
| M11 | renamed: dropping the whole table of a migrated store reaches the legacy file, which lags and refuses | as observed |

The crash harness, the downgrade probe (M21), the full suite and fresh security replays are
re-run at the final SHA.
