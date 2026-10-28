# Superseded v7 lane rows: #836 protected tree `f9b5ff9e` (declaration `7de94f11`)

These rows were executed and imported on #836's repaired cumulative tree, protected tree `f9b5ff9e79a54ef053ce89eb975256b63e211714`, under declaration blob `7de94f11d7d521f07d2fe22317662ac6f92f89fa`:

- AMB PrecisionMemBench, 77/77 equal to accepted v6;
- LongMemEval_S, 500/500 per plane equal to accepted v6.

They were moved here unchanged, with `git mv`, so their bytes and history are preserved.

The integration branch `integration/v7-786-836-reconciliation-no-ci` changes the protected tree, because it adds the #786 store identity profiles, the store-open contract and host-bound identity binding. It also changes the declaration, so both v7 lane specs are re-pinned to the integrated declaration blob, following #836's own procedure (`2ad4cf23`, `07cd8692`, `2d83db0e`, `e656776f`). The lane tooling holds exactly one record per row and refuses a row whose executed declaration blob differs from the lane's pin. So, as at #836's commit `5ed105d7` (`superseded-tree-79172267/`), these rows are evidence for the `f9b5ff9e` tree only. They are not attributed to the integrated tree, and both lanes must be re-executed there.
