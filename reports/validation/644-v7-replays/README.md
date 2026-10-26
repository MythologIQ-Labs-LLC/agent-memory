# #644 v7 replay evidence

This is the machine-readable evidence for the five replays that `reports/runtime/baseline-v7-declaration.json` requires.

The complete report is [`QUALIFICATION.md`](QUALIFICATION.md).

**This is not v7 acceptance.**

## Layout

| Path | Content |
|---|---|
| `<replay_id>/report.json` | Every case's observations, checks and outcome, invariant roll-ups, provenance, and the verdict. |
| `<replay_id>/manifest.json` | sha256 bindings of fixture, runner, report, observations digest, source commit and runtime tree. |
| `tamper_challenge.py`, `tamper-challenge.json` | Adversarial mutations of copies of this evidence, with the verifier's response to each. |
| `verify-reexecute.json` | `scripts/verify_644_v7_replays.py --reexecute` output at the evidence commit. |
| `inventory.json` | `scripts/check_644_v7_replay_inventory.py` output. It is deliberately BLOCKED. |

The frozen fixtures live in `reference/fixtures/644-v7-replays/`, frozen in commit `7530378`. The runner is `reference/run_644_v7_replays.py`, and the tests are `reference/tests/test_644_v7_replays.py`.

## Reproduce from the repository root

Run every command from the repository root:

```
python reference/run_644_v7_replays.py --all                     # writes this directory; exit 0 only if all PASS
python scripts/verify_644_v7_replays.py --reexecute              # independent recomputation plus re-execution
python scripts/check_644_v7_replay_inventory.py                  # inventory: stays BLOCKED by design (exit 2)
python reports/validation/644-v7-replays/tamper_challenge.py     # adversarial mutations; exit 0 if all detected as expected
python -m unittest discover -s reference/tests -t reference -p 'test_644_v7_replays.py'
```

The runner refuses to report PASS from a dirty source tree. The only exception is this output directory. A rerun at the same commit reproduces every `report.json` byte for byte.

## Authority boundary

The sha256 values bind contents for review. They are not signatures.

A consistent forgery of unasserted observations, with every unkeyed digest recomputed, passes static verification. Only `--reexecute` exposes it, as `tamper-challenge.json` demonstrates. A reviewer must therefore re-execute.

A VERIFIED, PASS replay is reproducible evidence, not v7 acceptance, publication or stop authority.
