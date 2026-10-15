# AMB upstream main + prepared patches: Agent Memory on PrecisionMemBench single-turn (additional measurement)

**Status: candidate. This is not a replacement for the reviewed frozen-revision result (15/77 at AMB `03c1d0f`).**

- AMB `aef3702e0586a959c845cc2c61f10d5e8ff0f94a` (upstream `main`, 2026-10-14) plus the two prepared patches
  `integrations/amb-upstream/0001-add-agent-memory-provider.patch` and `0002-retrieval-mode-without-llm-credentials.patch`
  (on branch `claude/wizardly-cray-bmkfrr`), applied with `git am`: commits `16b0434`, `30e9340`.
- Upstream moved 8 commits past `03c1d0f`. None touches `dataset/precisionmembench.py`, `modes/retrieval.py`, `cli.py`, `uv.lock` or `pyproject.toml`. The `runner.py` changes affect isolation-unit datasets, sdebench fields and log text; PrecisionMemBench has no isolation unit.
- Run: the stock `amb run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval` with **no inference keys at all**. That works only because patch 0002 is applied. The environment is AMB's own lock (unchanged) with `agent-memory-reference` at runtime-identical revision `7a1ab45`. Fixtures sha256 `35659b3b…` and `09e99f08…` equal the pins.
- **Result: 15/77**, exit 0. Case by case it equals the reviewed frozen-revision rep1, with 0 differences; only timing and `raw_response` are ignored (`comparison-vs-frozen-03c1d0f.json`).

Consequence for the upstream submission: both patches apply to current upstream `main` and reproduce the same result there.
