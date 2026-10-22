# Derived-store filesystem trust assumptions: POSIX with a descriptor table versus hosts without one

Owner direction (PR #805): evaluate Windows and POSIX filesystem trust assumptions separately and
claim no equivalent race resistance where the implementation does not provide it. This record
states what `reference/agentmem_ref/runtime/representation_cache.py` (protected blobs at
`ef8b6cb2`) does on each class of host and what each class resists, with the tests that pin it.

## What every host gets

- `derived/` is created `0700`; its entry is refused if it is a symbolic link, not a directory, or
  (where `os.geteuid` exists) owned by another user; a directory owned by the runtime user that is
  group- or world-writable is tightened to `0700`.
- The store file is opened relative to the pinned directory descriptor with `O_NOFOLLOW` (where
  `openat` and `O_NOFOLLOW` exist), created `0600`, `fchmod`-ed through the descriptor (never
  `chmod` by path), and `fstat`-ed as a regular file.
- SQLite opens the file **by name**. `mode=rw` only prevents file creation; nothing in the SQLite
  URI or the Python binding refuses to follow a link.
- Only damaged or unreadable stores of this runtime's own format are discarded; foreign formats
  and versions are never initialised, reconciled or unlinked.

## POSIX hosts with a process descriptor table (`/proc/self/fd` on Linux, `/dev/fd` on macOS and the BSDs)

After `sqlite3.connect` the descriptor table must show a new descriptor on the pinned
`(st_dev, st_ino)`; otherwise the connection is closed and the entry is reported `unsafe`
before any statement. This refuses a link swapped in before the open **even if it is swapped
back out immediately after** (leaf or parent directory), because SQLite's descriptor then points
at another inode.

| attack | result | test |
|---|---|---|
| leaf replaced by a link to an external store between the check and the open | refused, nothing read or written outside | `test_reconcile_never_acts_through_a_symlink_swapped_in_after_the_check`, `test_active_store_open_refuses_a_leaf_link_swapped_in_around_the_open_without_chmod_or_writes` |
| parent `derived` swapped for a link and back around the open | refused (`unsafe`), external rows intact | `test_reconcile_refuses_parent_directory_swapped_in_and_back_out_around_the_open` |
| `derived` is a link when the store is constructed | refused before any I/O; `auto` degrades, `required` raises | `test_active_store_refuses_linked_derived_directory_without_touching_external_cache`, `test_symlinked_derived_directory_degrades_auto_and_refuses_required_before_external_io` |
| `derived` owned by another user | refused (`unsafe`) | `test_reconcile_and_open_refuse_a_derived_directory_owned_by_another_user` (root only) |

**Qualified mitigation, not proof.** The verification is against an attacker who can write to the
root but not act as the runtime user. A principal who can place a directory and file they own
*as the runtime user* is the runtime; a principal with write access to the root who races the
descriptor-table scan from another thread of this process is this runtime's own code. The
accepted boundary is therefore: a local root and `derived` owned by the single runtime user with
no other principal holding write access to either (docs/44 "Accepted trust boundary").

## Hosts without a descriptor table (Windows; any platform exposing neither `/proc/self/fd` nor `/dev/fd`)

The fallback re-checks the directory entry after the open (type, device, inode). It detects a
link **still in place** after the open. It does **not** detect a parent directory swapped in and
back out around the open: the leaf inode and its change time are untouched, so the re-check is
satisfied while SQLite's descriptor points at the external store.

| attack | result | test |
|---|---|---|
| leaf link still in place after the open | refused (`unsafe`) | `test_fallback_without_descriptor_table_still_refuses_a_link_left_in_place_after_the_open` |
| parent `derived` swapped in and back out | **not detected**: the reconciler acts on the external store | `test_fallback_without_descriptor_table_does_not_detect_a_parent_swap_in_and_back_out` (pins the gap exactly as documented) |

On Windows additionally: `O_NOFOLLOW`, `openat` and `fchmod` do not exist (the code degrades to
path-based open and no chmod), `os.geteuid` does not exist (no ownership check), and creating
symbolic links needs a privilege or developer mode. **These hosts are outside the adversarial
path-swap claim.** The supported statement for them is only the trust assumption: the root and
`derived` are written by the runtime user alone. No equivalent race resistance is claimed.

## What neither class claims

Erasure of rollback journals, WAL frames before checkpoint, backups, snapshots or filesystem
remnants; the canonical substrate keeps tombstones, receipts and audit events by design and does
not set `secure_delete` (#777, docs/44). A reconciliation reported `incomplete` after a committed
permanent deletion raises `DerivedCacheReconciliationError` with the canonical receipt attached
and is retried on the next open; it never claims full erasure.
