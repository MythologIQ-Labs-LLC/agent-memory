# #809 legacy upgrade, amendment 1: legacy self-references (PREREGISTERED, not executed)

This amends `decision.PREREGISTERED.md`, rule 2 of section 3. It does not rewrite that record, its
fixtures (`reference/fixtures/809-legacy-stores/`) or its execution logs. Everything else in the
decision stands.

**Status:** committed with its fixture and tests before any runtime change. Executed once on the
unmodified head (`e88bced2`, the cumulative candidate containing #815 and #821 R-1) as the
fail-first baseline. The independent reviewer then compares the result with this record before
the first execution on the changed runtime.

## 1. The gap

An independent source-level challenge (issue #809 comment 6298692981, PR #815 comment 6298713281)
found that `adapter._classify_legacy_reference` decides order with `if cited > own:
return "forward_reference"`.

- A legacy fact whose `episode_uuids` contains **its own id** passes that check (`cited == own`).
- The citing fact's scope record trivially satisfies every scope gate against itself.
- So the self-reference is classified **`eligible`**, and the upgrade binds it as a canonical
  derivation dependency.

The decision's own premise excludes this. A dependency must name content that existed when the
citing fact was written, and a later reference must never bind retrospectively (section 3, rule
2, "the owner's non-retroactive ruling"). A self-reference cannot have named a previously
committed fact, even if its allocated id was guessable (ids are sequential, `ref-NNNN`).

The challenge did **not** demonstrate a leak, a deletion failure or cross-project disclosure, and
neither does this record. The defect is an edge that the decision's contract says must not exist.

## 2. Amended rule 2 (owner decision 2026-10-20: `forward_reference`, non-retroactive)

> 2. `r` minted after `F`, **or `r` is `F` itself** (id sequence `seq(r) >= seq(F)`) →
> **forward_reference**: never binds. Ids not comparable → **order_undecidable** (kept bound,
> quarantined).

- **Why `forward_reference` and not `order_undecidable`.** The ordinal identity `seq(r) == seq(F)` is
  proven from the durable id itself: one monotonic sequence per store, the same evidence rule 2
  already trusts for `>`. Nothing about it is undecidable.
- **The consequences:**
  - The self-reference is unbound.
  - Its fact is not quarantined for it.
  - The store's status is decided by its other edges.
- **The other gates come after rule 2,** so they never see a self-reference.

## 3. New-write control (unchanged behaviour, pinned)

A **new** write that cites its own predicted id never binds it: `_bound_derivation` runs before
the new fact's scope record exists (`adapter._write`), so the reference names no governed fact at
commit, and fails closed. The amendment does not touch the new-write path. A test pins the
current behaviour.

## 4. Fixture

The fixture is `reference/fixtures/809-legacy-self-reference/self-reference`.

**Provenance.** It was written by the published v7 runtime `16a248b1` (the v7 Gauntlet adapter's
`FROZEN_RUNTIME_REVISION`), with the sanctioned producer pattern (`produce/`, a discovery pass for
the deterministic ids). It has its own `MANIFEST.json`, and the frozen `809-legacy-stores`
manifest is not modified. Three producer runs gave byte-identical files. Environment: Python
3.13.16, SQLite 3.45.1.

**Contents.** Tenant `tenant:legacy`; A is `agent:legacy` in `project:a`.

| Name | Id | `episode_uuids` (as written by v7) |
|---|---|---|
| `a1` (`memory:a`) | `ref-0004` | its content placeholder; **forgotten** at the end |
| `prior` | `ref-0011` | `[a1]`: the prior-id control |
| `self` | `ref-0018` | `[ref-0018]`: **itself** |
| `mixed` | `ref-0025` | `[a1, ref-0025]`: **a1 and itself** |
| `fwd` | `ref-0032` | `[ref-0039]`: the next-id control |
| `next` | `ref-0039` | its content placeholder |
| `other` (B, `agent:other`, `project:b`) | `ref-0049` | its content placeholder: the scope-isolation control |

## 5. Expected outcomes (fail-first on `e88bced2`)

**Before any upgrade, under the current runtime:**
- the status is `legacy_pending`;
- `prior` and `mixed` are withheld in project:a (they derive from the deleted `a1`);
- `self`, `fwd` and `next` are admitted;
- project:b admits `other` and none of A's facts.

This is already true on `e88bced2`, and must stay true.

**After `upgrade_canonical_derivation()` in project:a:**

| Fact | Expected classification | Expected `bound` | On `e88bced2` (before the repair) |
|---|---|---|---|
| `self` | `{ref-0018: forward_reference}` | `[]` | `eligible`, `[ref-0018]`: **RED** |
| `mixed` | `{a1: eligible, ref-0025: forward_reference}` | `[a1]` | `ref-0025: eligible`, `[a1, ref-0025]`: **RED** |
| `prior` | `{a1: eligible}` | `[a1]` | GREEN |
| `fwd` | `{ref-0039: forward_reference}` | `[]` | GREEN |
| `a1`, `next`, `other` | the placeholder classifies `unknown_reference` | `[]` | GREEN |

- **The report** (non-zero classes): `{unknown_reference: 3, eligible: 2, forward_reference: 3}`,
  status `legacy_qualified`, `quarantined` empty. **RED** on `e88bced2`, which reports
  `eligible: 4, forward_reference: 1`.
- **Recall after the upgrade (project:a):**
  - `prior` and `mixed` stay withheld; the legitimate `a1` dependency is preserved;
  - `self`, `fwd` and `next` stay admitted.

  GREEN on both.
- **Derived deletion after the upgrade:**
  - `forget("memory:self")` commits;
  - `self` is then withheld;
  - `prior` and `mixed` stay withheld, and `fwd` and `next` stay admitted;
  - no error, and a reopen recovers (the recovery digest is verified).

  GREEN on both: the self-edge is a cycle that traversal tolerates. It is pinned as a control, not
  as a failing case.
- **Idempotence and durability:**
  - a second upgrade rewrites nothing (`facts_rewritten` 0) and returns the same classification;
  - the status and the admitted set are identical after a reopen and after a genuine new process.

  RED on `e88bced2` only where they compare the expected classification.
- **Scope isolation:**
  - project:b admits only `other`, before and after the upgrade;
  - the upgrade creates and alters no scope record, memory binding or tombstone, and adds or removes
    no fact.

  GREEN on both.
- **`NoFabrication` on this store,** with the predicate amended to the amended rule 2: a
  `forward_reference` edge has `seq(r) >= seq(F)`, and an `eligible` edge has `seq(r) < seq(F)`.
  **RED** on `e88bced2`, where an `eligible` self-edge has `seq(r) == seq(F)`. The amended predicate
  is also applied to the three frozen stores, which contain no self-reference, so their outcome is
  unchanged.
- **New-write control (section 3):** a fresh store's write citing its own predicted id records
  `bound: []`. GREEN on both.
- **The three frozen stores:** `CrossScopeStore`, `SharedMembershipStore`, `ForwardReferenceStore`,
  `Fixtures` and `LegacyOracleDemonstrated` give identical outcomes before and after the repair.

**Expected RED on `e88bced2`:** exactly the self-reference classification, report, idempotence and
`NoFabrication` assertions above. **GREEN everywhere after the repair**, with no change to any
frozen-store outcome.

## 6. The repair this authorises, and nothing more

In `runtime/adapter.py`, `_classify_legacy_reference`: `cited > own` becomes `cited >= own`, with
the docstring and vocabulary updated. No other runtime change. A failure after the repair is a
finding to investigate, never permission to weaken a line.

## 7. Re-qualification at the new revision

- `test_809_legacy_upgrade`, `test_809_legacy_upgrade_substrate`, `test_809_evidence_reference_authorization`
  and the new `test_809_legacy_self_reference`;
- the #776 deletion-propagation tests;
- `test_821_atomic_config_binding` and the #821 crash-window matrix;
- the seven security replay families, with `observations_sha256` compared with `e88bced2` and
  `e13d8c58` (expected identical: no replay family contains a legacy self-reference);
- the full suite, with and without the representation model.

The new revision replaces `e88bced2` as the Runtime Baseline candidate. Frozen #815 evidence is
never edited.

## 8. Fail-first record (`self-reference/fail-first-e88bced2.txt`)

**One harness defect** was fixed before the recorded runs, and no expectation changed.
`NoFabricationSelfReference` first raised `FileNotFoundError`, because unittest calls `setUp()`
with the inherited default store (`cross-scope`) before `_check` switches to the self-reference
store. The subclass now names its own store.

**The recorded result,** on the unmodified runtime (`reference/agentmem_ref` identical to
`e88bced2`), ×3:
- exactly the three preregistered REDs fail, each for the predicted reason:
  - `ref-0018` classifies `eligible`;
  - the report shows `eligible: 4, forward_reference: 1`;
  - `NoFabrication` finds an `eligible` edge with `seq(r) == seq(F)`;
- all seven controls pass;
- the frozen-store modules (`test_809_legacy_upgrade*`, 12 tests) pass.
