# #770 v7 lane freeze: validation evidence

This bundle validates `implementation/770-v7-lane-freeze-review-no-ci` @ `f6c0fa5` and its repair on `validation/770-v7-lane-freeze-independent`.

The verdict is in [`QUALIFICATION.md`](QUALIFICATION.md).

**This is not lane acceptance, v7 qualification or publication.**

## Layout

| Path | Content |
|---|---|
| `logs/*-f6c0fa5.*` | The branch as submitted: `validate-lane`, `benchmark lanes`, the focused and full suites, the checker, the workflow probe and the reproducers. |
| `logs/*-9d1fda0.*` | Intermediate results after the lane and guard repairs. They show the L6 STALE replays and the guard negative controls. |
| `logs/*-9b025f9.*` | The final SHA: full suites (3.13 and 3.12), focused tests, `validate-lane`, the checker, the Gauntlet run, replay verification and inventory, and the workflow probe. |
| `logs/superseded/` | Full-suite runs at `9d1fda0`, stopped or superseded by `9b025f9`. |
| `lane-field-diff-<rev>.json` | Every differing leaf, v6 (read as frozen) against v7, classified as listed identity or UNLISTED. |
| `gauntlet-run/` | The `gauntlet-orchestration-retrieval-probe-v1` output at `9b025f9`. |
| `scripts/rebuild_v7_lanes.py` | Regenerates both v7 lanes from the v6 lanes, which is how the committed v7 lanes were made. |
| `scripts/lane_field_diff.py` | The field-by-field comparison. |
| `scripts/workflow_gate_probe.py` | Runs the workflows' own lane-precondition code locally, and compares permissions and secrets with a base revision. |

## Reproduce

Run from the repository root, in a venv with `agent-memory` installed, with `PYTHONPATH=$PWD/reference`:

```
agent-memory benchmark validate-lane reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v7.json --json
agent-memory benchmark validate-lane reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v7.json --json
python -m unittest discover -s reference/tests -t reference -p 'test_770_*.py'
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD
python reports/validation/770-v7-lane-freeze/scripts/lane_field_diff.py . HEAD
python reports/validation/770-v7-lane-freeze/scripts/workflow_gate_probe.py . f92ea422dcf2d61cad51ef1f427df352baef4cbb
python scripts/verify_644_v7_replays.py --reexecute
```

The workflow probe needs network access for the AMB fixture URLs. It needs no credentials and no GitHub Actions.
