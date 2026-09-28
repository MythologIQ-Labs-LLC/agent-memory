# #580 gauntlet replay at #550 head `eb44c34` (policy 3.1.0)

Repository-owned conformance and falsification evidence, not external validation. The frozen gold is unchanged (sha256 `394be82e…4492`), and the frozen pre-#550 baseline stays at `../baseline-0bace49/`.

* `baseline.json`, `baseline-seed1.json`, the ablations, the mutants, and `summary.json`: the full matrix (`run_temporal_currentness_gauntlet.py --matrix`), generated at `eb44c34` with a clean runtime tree.
* `main-550abf0-pre-550.json`: the same evaluator at `main` `550abf0` (policy 3.0.1, includes #582), so #550 is attributed against the current base as well as the frozen one.
* `proposal-application-counterfactual.json` (`proposal_application_counterfactual.py`): an evaluation-only reviewing caller applies every write-time proposal through the governed correction.

Result vs `main`: 4 target units go `honest_unknown -> pass` (F26 after-interval, F27 before-start). No required unit regresses and no target unit worsens; only those two probes' digests change. Restart and cross-process reproduction are both 1.0, every ablation and mutant still regresses, and the F25 control is still detected. Interpretation and the full table are in [docs/61](../../../../docs/61-write-time-proposition-semantics.md).
