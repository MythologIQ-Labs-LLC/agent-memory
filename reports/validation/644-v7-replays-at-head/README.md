# #644 v7 replay contracts re-executed at this branch head

Candidate evidence for the integrated #776/#777/#772 head, **not** v7 acceptance and not a
replacement for `reports/validation/644-v7-replays/` (the `16a248b` packages are left intact).

- source commit: `df6d9bed53c8e0199f2f53258e340561e9602886`
- runtime tree (`HEAD:reference/agentmem_ref`): `544fb9e667712e92ce6d100b364ead98992220b8`
- produced by `python reference/run_644_v7_replays.py --all --output-dir <scratch>` on a clean tree
  (the output directory was outside the repository so the runner's dirty-tree rule held), then
  `python scripts/verify_644_v7_replays.py --reexecute --evidence-root <scratch>` (exit 0) and
  `python scripts/check_644_v7_replay_inventory.py --evidence-root <scratch>` (exit 2, BLOCKED by design).

| replay | verification | verdict | re-executed |
|---|---|---|---|
| `typed-sufficiency-noninterference-and-negative-controls-v1` | VERIFIED | PASS | True |
| `governed-persisted-typed-slot-sufficiency-admission-recheck-v1` | VERIFIED | PASS | True |
| `governed-admitted-typed-value-coherence-v1` | VERIFIED | PASS | True |
| `committed-governed-transition-witness-v1` | VERIFIED | PASS | True |
| `same-slot-safety-counterevidence-and-immutable-stop-gate-v1` | VERIFIED | PASS | True |

`evidence_verified`: True. The verifier's own wording applies: VERIFIED is
reproducible, untampered evidence for a reviewer, not acceptance.
