# 67. Runtime Baseline succession

**Status:** active (#674, P0 of the North Star program #668)
**Governs:** how a deliberate runtime change passes the Runtime Baseline mechanism without editing a published record.

Runtime Baseline v1 (#638) froze the runtime at `f2aef57` and made every protected byte a gated fact. It did not say how the next baseline comes to exist. This document is that procedure. It changes nothing about v1: the v1 record, boundary, rendering, Gauntlet manifest and adapter are byte-pinned and stay as they are.

## Terms

- **baseline register** — `reports/runtime/baseline-register.json`, the only place that says which baseline is current. Entries are ordered by publication; the last entry is current. Each entry names its record, source boundary and qualification file and pins their git blobs; a published entry also names the commit on `main`'s first-parent history whose tree holds the record and boundary bytes (`published_commit`).
- **declared successor** — the register's one `declared_successor` slot, naming the next baseline id and its declaration file `reports/runtime/baseline-v<N>-declaration.json` (schema `schemas/runtime-baseline-declaration.schema.json`). A declaration lists the protected paths a tranche changes with the exact git blob each carries, the identity values that change (`from` → `to`), whether `pyproject.toml` changes and why, and the acceptance evidence the successor's publication must bind. It is a claim the checker verifies in both directions; it grants nothing.
- **transition** — the interval between the merge of a declared runtime change and the publication of its successor. During a transition the protected surface is still pinned: it must equal the frozen surface plus exactly the declared blobs. The checker prints `TRANSITION` and workflows whose evidence would claim an exact revision skip that evidence.
- **pinned** — a state in which the candidate's protected tree is a function of the register alone: `PASS` (equal to the frozen revision) or `TRANSITION` (frozen revision plus declaration). A path allowlist is never a pin and never exists here.

## The checker's three outcomes

`python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` reads the register, resolves the current entry's boundary, and diffs the candidate against the frozen revision over the protected paths minus the explicit exclusions.

| Outcome | Exit | Line printed | Meaning |
| --- | --- | --- | --- |
| `PASS` | 0 | `Runtime Baseline equivalence: PASS; baseline=…; frozen=…; candidate=…; explicit non-runtime exclusions=…` | no protected byte differs from the frozen revision |
| `TRANSITION` | 0 (1 with `--pinned-only`) | `Runtime Baseline equivalence: TRANSITION; baseline=…; declared_successor=… (issue #…); protected surface = frozen … + k declared blobs; deltas=…; candidate=…` | the changed paths equal the declared paths, every declared blob matches the candidate, every declared identity delta holds at the frozen and candidate ends, no undeclared identity moved, and `pyproject.toml` is declared exactly when it changes |
| failure | 1 | the first failing check, e.g. `undeclared protected change: <path>`, `declared blob mismatch for <path>: declared …, candidate …`, `undeclared identity <path> changed: frozen=…, candidate=…` | anything else |

The identity table that "identity delta" and "undeclared identity" refer to is `scripts/runtime_baseline_identity.py` (`IDENTITY_SOURCES`): one row per value a baseline record pins to a constant or profile field in the protected source. The register validator (`scripts/validate_runtime_baseline_source.py`) uses the same table to check every record against its frozen revision.

`--pinned-only` is for callers whose evidence claims an exact revision and must refuse to run during a transition. The three workflows that do claim one (`runtime-baseline.yml`, `agmi-agent-memory-qualification.yml`, `gauntlet-durability-recovery.yml`) instead classify first (`id: classify`) and skip their evidence-producing steps unless the state is `PASS`, printing a transition notice otherwise. `benchmark-integration-contract.yml` runs the plain checker: its contract tests claim no revision, so a transition is a green state there.

## The procedure

### Step A — the tranche PR declares its successor

1. Make the runtime change on a branch. It is a runtime change, so the checker now fails.
2. Add `reports/runtime/baseline-v<N>-declaration.json` with the successor id, the predecessor id (the register's last entry), the issue, the identity deltas, `pyproject_change` (`null` or `{"reason": …}`), and the acceptance evidence the publication must bind.
3. Set the register's `declared_successor` to `{"baseline_id": …, "declaration": …}`.
4. After the last protected edit, run `python scripts/declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v<N>-declaration.json`. It rewrites `declared_changes` from `git diff --name-only <frozen> -- <protected> <exclusions>` and `git hash-object` of each working-tree file; nothing else in the file changes. Any later protected edit needs another run, or the checker reports `declared blob mismatch`.
5. The checker prints `TRANSITION`. Merge with a merge commit; the merge keeps the PR's blob for every file `main` did not touch, and `main` cannot touch a protected file without a declaration, so the pin stays true after the merge. A conflicted or squashed merge that changes a declared blob fails the next PR's checker as `declared blob mismatch`; it never passes silently.
6. A second tranche that merges during the transition amends the open declaration (its `declared_changes` and `identity_deltas`, same `baseline_id`); the register has one `declared_successor` slot by construction. A declaration cannot open while the current entry's qualification is `pending` or its `published_commit` is `null`.

Lane and replay evidence for the new runtime binds the exact commits it ran at. The v1 lanes (`amb-precisionmembench-retrieval-v1`, `longmemeval-s-retrieval-parity-v1`) carry "frozen at Runtime Baseline v1 `f2aef57`" in their `revision_rule`; those sentences are frozen lane facts and are not edited. A successor needs new lane ids (roadmap prerequisite `prereq-lane-v3-ids`).

### Step B1 — publication (no runtime change)

A baseline is published against the merge commit of its last declared tranche, after that merge, exactly as v1 was published against `f2aef57` after PR #646. A publication PR carries:

- `reports/runtime/baseline-v<N>.json`: the record, with `runtime_revision.commit` set to that merge commit, a `predecessor` block `{baseline_id, identity_deltas, declared_changes}` copied from the declaration, a dogfood block pointing at the `#637` evidence, and the identities the declaration said would change;
- `reports/runtime/baseline-v<N>-source-boundary.json` with that `frozen_revision` (the protected and excluded sets are inherited unless a reviewed boundary revision says otherwise);
- `reports/runtime/baseline-v<N>-qualification.json` with `{"status": "pending", "profile_id": "gauntlet-orchestration-retrieval-probe-v1", "transport": "stdio"}`;
- `reports/runtime/baseline-v<N>.md`, rendered by `python scripts/render_runtime_baseline.py`;
- `examples/gauntlet/agent-memory-runtime-baseline-v<N>.json` whose `transport.startup` names a copied adapter `examples/gauntlet/agent_memory_runtime_baseline_v<N>_stdio.py` with its `FROZEN_RUNTIME_REVISION`, `PUBLIC_CONTRACT_VERSION`, tenant, actor, scope and purpose constants updated to the successor (the v1 adapter keeps its constants: `examples/gauntlet/agent_memory_runtime_baseline_stdio.py` lines 26-34);
- the register: a new last entry with the three blobs, `qualification.pointer` empty, `published_commit: null`; `declared_successor: null`;
- every contestant or profile file that names the predecessor's revision, retired by its workflow condition: `fixtures/gauntlet/agent-memory-public-durability-adapter.json` (`system.revision`) and `reports/gauntlet/agmi-agent-memory-v1/qualification.json` plus `accepted-result.json` (`runtime_baseline_revision`). The durability and agmi workflows assert those pins against the register and refuse a stale contestant truthfully; re-pinning either is a later two-step of its own, because a re-pinned agmi profile fails its own identity validation until `accepted-result.json` carries a real successor run.

On this PR the checker prints `PASS` again (the candidate equals the new frozen revision on the protected surface), the validator accepts the `pending` last entry, and `runtime-baseline.yml` runs the orchestration probe with the new manifest and uploads the artifact `<baseline_id>-public-gauntlet`. The probe's `sample_count == 3` and `exact_top1 == 1.0` assertions are the publication acceptance gate for that probe, not authority and not a score. A red B1 run is not merged: the register is unchanged, the transition stays open, and the defect is fixed in a tranche that amends the declaration.

### Step B2 — evidence binding

A second PR makes the qualification file complete (workflow run, artifact id and digest, `verified_head` = B1's PR head, `system_revision`, adapter blob, the three-query sample and its bounded `exact_top1`), sets the register entry's `published_commit` to B1's merge commit (whose tree holds the record and boundary bytes B1 pinned; the qualification file is not checked there) and its `qualification.blob` to the new bytes. The record itself is untouched; from here on its blob never changes. The successor's lane rows execute at a revision whose protected surface the checker reports as the frozen predecessor plus the same declaration blob that `runtime_revision.commit` carries (the inference of equivalence rests on that blob at both ends; the lane pins it and the importer binds it), and the publication cites them by evidence id and executing revision.

## Invariants

- A published record is blob-pinned to a commit in `main`'s first-parent history; the validator refuses a record whose working-tree bytes differ from the pin, and a pin whose commit holds other bytes.
- A transition pins the protected surface to the frozen bytes plus the declared blobs; the diff is never relaxed to a path allowlist.
- One declared successor at a time, and none while the current baseline is `pending` or unpinned.
- A declaration is a claim verified in both directions: every declared delta must hold at the frozen and candidate ends, and nothing undeclared may move.
- The v1 record, boundary, rendering, manifest and adapter are never edited; a successor is new files and a new register entry.
- Benchmark output is never authority; the orchestration probe gates publication of a baseline, not the meaning of any memory operation.
