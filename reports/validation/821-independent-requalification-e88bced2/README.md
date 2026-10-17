# Independent re-qualification of the #821 R-1 repair

- **Candidate:** `e88bced24157d668179882f63e921ea569df1d51`.
- **Comparators:** the original #821 freeze `d0d2a97c63b50700001da06b9df7fe81b580fc09`, and #816 `e13d8c58c3d5521be50c8d32feacf2710c7fc6c5`.
- **Reviewer:** session `session_011h1ADQyj3ZTu9UHgBAhocF`. It has no commits in the #805 → #821 lineage and did not author R-1. The candidate was implemented by `01HEDDT…`, and #821 by `012Ju6w8…`.
- **Record:** the verdict and the full record are in #821.

## Environment

- **Interpreter:** a neutral venv (Python 3.12.3) with the pinned dependencies and **no agent-memory package installed**.
- **Paths:** `PYTHONPATH=<tree>/reference`, with the venv first on `PATH`, so that external-process adapters use it too.
- **Clone:** a full (unshallowed) clone.
- **Earlier confounds:** an editable package leaking into imports, a shallow clone, and a system `python` without `rfc8785`. Together they produced 3 spurious failures in early comparator runs, and those runs are discarded.

## Contents

| Path | What |
| --- | --- |
| `adv821.py` | Independent adversarial suite (v2): A1–A3 R-1 race, B, C, D, E1/E2, G |
| `orphans.py` | RES-W2 orphan accumulation probe |
| `perf.py` | Small performance comparison |
| `qualify.sh` | The pipeline |
| `runs/q-*/` | Per-tree identity, summary, adversarial JSON, crash-window JSON, suite failure sets and replay manifests |
| `runs/out-am-816-*.json`, `runs/full-816-nomodel.failures` | #816 comparator outputs |
