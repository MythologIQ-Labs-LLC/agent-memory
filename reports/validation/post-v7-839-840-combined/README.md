# Combined post-v7 preview (#839 + #840): independent integration and security qualification

Branch `integration/post-v7-839-840-combined-preview-no-ci`, exact head
**`f3bc36540b556e618d9c1e4b878ade95d4f260a1`**, protected runtime tree **`02d1e3e01f4e378647ed4263ac1679cfceaaba01`**
(v7 `f9b5ff9e`; #839 `83f0ff99`; #840 `83e44f04`). Executed in this cloud container (CPython 3.12.3,
4 vCPU, Linux), no GitHub Actions, no model inference. Neither parent's acceptance or results are
inherited; everything below ran at this head. Frozen #836 (`f4386e2a`), the v6 register, the #809
fixtures and the accepted benchmark evidence are untouched; no successor is declared, nothing is
re-pinned, merged or published. v7 itself follows the restricted fresh-store-only profile and stays
HOLD; this branch is successor development.

## 1. Composition verified against both parents (`logs/protected-blobs-f3bc3654.txt`)

- Ancestry: descends from #840 `6ace22f6` (and `ab4e549d`, `72d6a903`); #839 `d2d32d2a` is **not** an
  ancestor (its files were transplanted) and #836's docs-only `f4386e2a` is not either, but its accepted
  `docs/44` blob `d2a187f7` is carried verbatim.
- Every #839 non-evidence file (12 of 13) and every #840 non-evidence file (6 of 7) is **blob-identical**
  to its parent: `api/context_package.py` `6ae5bc41`, `context_package.py` `5e1ee201`,
  `runtime/adapter.py` `85da3030`, `api/host_activation.py` `c63646f0`, `host_activation.py` `e63a7aa3`,
  the schema, the demo, the example and all eight test modules.
- The two reconciled files: `api/surface.py` (`abd8bb06`) is **byte-identical** to #839's `66b1ee45`
  with #840's writer patch (`ab4e549d`→`6ace22f6` diff of `_atomic_write_text` plus `import tempfile`)
  applied; `scripts/restructure_package.py` registers both `context_package` and `host_activation` in
  the `api` layer. Nothing from either PR is lost. `recall()` remains AST-identical to the v7 base;
  `open()` is unchanged; `_recall_document` differs only as in #839.

## 2. Executed at `f3bc3654` (`logs/`, `replays/`, `install/`)

| Gate | Result |
|---|---|
| focused #839 + #840 modules + `test_post_v7_839_840_integration_preview.py` (3 new) + DoD-20 | **84 passed** (pytest); the three new cases also 3/3 under `unittest` |
| `test_package_layout`, `restructure_package.py --check` | OK (3 optional numpy skips); `layout matches table` |
| validators: schemas (75), fixtures (64), architecture index (84), doctrine boundaries, wiki links | all OK |
| #777 / #786 / #809 / #816 / #821 / #823-adjacent / #802 / #835, SQLite, restart, deletion, durability, crash, witness, binding, doctor, #691, #839, #836, preview (36 modules) | **415 passed**, 1 skipped, 1 xfail |
| full reference suite, repository root | **3232 passed, 4 failed**, 27 skipped, 1 xfail, 2190 subtests, 332 s. The four are the v7 identity guards (two #770 freshness guards, the #644 Gauntlet identity guard, the baseline-equivalence contract test), failing by design until a successor declaration covers this tree. The #786 thread-race test passed |
| `check_runtime_baseline_equivalence --candidate HEAD` | exits 1 **by design**: four undeclared protected files, two declared blobs moved (`logs/checker-f3bc3654.txt`) |
| 13 replay families (786 v2/v3, #809, #835 DSL/4, five #644) | all PASS, `observations_sha256` **identical** to the `2ad4cf23` v7 record; `verify_786`/`verify_644 --reexecute` 10/10 VERIFIED |
| #821 crash-window matrix (9 kill points) | outcome-identical to the v7 record |
| wheel + sdist (`git archive`, `python -m build`, fresh venvs, `python -I` from outside the checkout) | both: both aliases are the `api` module objects; installed writer exclusive; packaged context schema present; guarded `recall_context` delivers with a bound receipt; faulted final validation and faulted recall linkage leave the receipt count unchanged; a colleague gets text without `memory_ref`/`source_ref`; `legacy_pending` fixture refused by the gate, qualified after maintenance upgrade, `legacy_unqualified` refused; planted-symlink first open leaves the victim intact (`0600`); `demo_context_package.py` ALL CHECKS PASSED (wheel and source) |

## 3. Adversarial challenge of the composed seam (`probes/`)

`combined_seam_probe.py` and `deleted_id_receipt_order.*` at this head:

- **Cross-actor provenance privacy through the gate:** the writer sees its `memory_ref`/`source_ref`;
  a same-project colleague gets the text, no private references, and its receipt carries neither the
  private source, the text nor the logical name; another project gets an `empty` package and a receipt
  naming no identifier; another tenant is refused by the runtime (`RuntimeRecoveryError`); a handle that
  merely **declares** the writer's `actor_id` receives the writer's provenance: the documented
  host-binding limit, the gate does not authenticate.
- **Audit atomicity:** a generation-persistence failure inside the seam leaves the receipt count
  unchanged, the store usable and the reopened log consistent with unique ids; faulted final validation
  and a missing recall event record nothing (installed smoke and the #839 `FailClosed` matrix, 19 tests).
- **Deletion and restart:** after `forget`, the deleted text is never redelivered on the same handle or
  after reopen; receipts recorded **after** the deletion never name the deleted id or text (0 of 2);
  receipts recorded before it legitimately do (historical audit), exactly as the #839 design states.
- **Legacy activation × context delivery:** the gate refuses the `legacy_pending` fixture before any
  `recall_context` can run; the plain facade still opens it and delivers a `complete` package with a
  receipt: the **opt-in limit** carried from #840 is unchanged in the combination. Fresh roots opened
  through the gate with a planted temp symlink leave the victim intact and read `fresh`.
- No defect was found; nothing was changed on this branch beyond this record.

## 4. Disposition

**READY FOR INDEPENDENT REVIEW** as a composed successor preview. It is not a successor qualification:

1. **Successor declaration (docs/67 Step A)** must cover six protected blobs beyond `7de94f11`:
   `api/surface.py` `abd8bb06`, `runtime/adapter.py` `85da3030`, `api/context_package.py` `6ae5bc41`,
   `context_package.py` `5e1ee201`, `api/host_activation.py` `c63646f0`, `host_activation.py`
   `e63a7aa3` (tree `02d1e3e0`); then regenerated committed replay roots (digests already identical),
   Gauntlet re-pin, new lane ids and rows, and the four identity guards clear. Only after v7's own
   acceptance/publication sequencing permits.
2. **Owner rulings still open** (unchanged from the parents): audit-digest policy and package version
   (#839 §9.6), the host-gate profile and a consumer-host adoption receipt (#840 §5): plain
   `AgentMemory.open()` is not protected and must not be described as such.
3. **Retained limits:** Windows NOT EXECUTED; #823 fixed-name temporaries outside the SQLite profile;
   same-user planting at the final configuration path; identity is host-declared.
4. v7 (#836) stays HOLD on its restricted profile; contract `1.8.0` as accepted; no merge, declaration,
   re-pin, publication or Actions from this record.
