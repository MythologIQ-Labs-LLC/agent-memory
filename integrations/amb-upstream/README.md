# Upstream contribution to vectorize-io/agent-memory-benchmark (prepared, not submitted)

There are two independent patches against AMB `03c1d0f1d27da63034f0931121c858faba512383`. Each
applies with `git am` on a clean checkout. They follow the shape of the only third-party
provider contribution AMB has merged, Ogham ([vectorize-io/agent-memory-benchmark#9](https://github.com/vectorize-io/agent-memory-benchmark/pull/9)):

- one provider module plus one `REGISTRY` line;
- the provider's own package installed separately, as documented in the PR body, with no
  `pyproject.toml` or `uv.lock` change;
- results published as `outputs/<dataset>/<memory>/<mode>/<split>.json.gz` plus a
  `results-manifest.json` entry, which is the format `amb publish-results` writes.

AMB has no CONTRIBUTING file or written submission rules, so this shape is inferred from that
history.

| Patch | Contents | Verified |
|---|---|---|
| `0001-add-agent-memory-provider.patch` | `src/memory_bench/memory/agent_memory.py` (140 lines), its `REGISTRY` entry, `outputs/precisionmembench/agent-memory/retrieval/single-turn.json.gz`, and one added `results-manifest.json` entry | Ran from a fresh environment: AMB under its own lock, with Agent Memory installed **from GitHub** at `581557f9c81ff3626ba16708546052dfceaafff7`, through the **unmodified** AMB CLI. Result: 15/77, identical case by case (`scripts/compare_amb_runs.py`, 0 differences) to the reviewed evidence in `reports/benchmarks/amb-local-execution/2026-10-15-precisionmembench-single-turn/` |
| `0002-retrieval-mode-without-llm-credentials.patch` | `cli.py`: skip the Gemini key check and the answer client in retrieval mode. `runner.py`: build the default judge on first use | With no keys at all, `bm25` retrieval gives 8/77, identical case by case to the stock CLI with placeholder keys. `--mode rag` without a key still exits with the same error |

Patch 0002 is the upstream form of `reference/amb_retrieval_no_llm.py`. Once it is merged, that
runtime guard is no longer needed. The patches are independent: 0001 does not need 0002.

## Before submitting

1. **Re-pin.** The patch 0001 description and the result's `description` field name Agent
   Memory `581557f9c81f`, which is on this repository's
   `claude/wizardly-cray-bmkfrr` branch. Once this work is merged to `main`, re-run the
   commands below at the merged commit and regenerate the patch so the pin is a commit on
   `main`, or on a release tag.
2. **Authorship.** The commits are authored as "Claude". Amend the author to the submitting
   maintainer: `git commit --amend --reset-author`.
3. **Manifest.** Do not let `amb publish-results` rewrite `results-manifest.json` in a fresh
   clone. It rebuilds the manifest from the `.json.gz` files present locally, and published
   results that live only in AMB's blob store are dropped (this happened here: 36 entries
   became 34). Insert only the new entry, as patch 0001 does. Do not pass `--push`: the blob
   upload needs AMB's own token.

## Regenerate patch 0001's result

```bash
git clone https://github.com/vectorize-io/agent-memory-benchmark amb && cd amb
git checkout 03c1d0f1d27da63034f0931121c858faba512383 && git am <this-dir>/0001-add-agent-memory-provider.patch
python <agent-memory>/scripts/amb_harness_constraints.py --amb-root . --memory agent-memory --output /tmp/c.txt
uv venv -p python3.12 .venv && VIRTUAL_ENV=.venv uv pip install -c /tmp/c.txt -e . \
  "agent-memory-reference @ git+https://github.com/MythologIQ-Labs-LLC/agent-memory@<full-commit-sha>"
rm -rf outputs/precisionmembench/agent-memory
# with patch 0002 applied no keys are needed; without it, inert placeholders satisfy client construction:
GEMINI_API_KEY=unused GROQ_API_KEY=unused .venv/bin/amb run --dataset precisionmembench --split single-turn \
  --memory agent-memory --mode retrieval --description "Agent Memory @ <sha> ..."
.venv/bin/amb publish-results outputs/precisionmembench/agent-memory/retrieval/single-turn.json   # then restore the manifest, see above
```

## Draft PR description (patch 0001)

> **Add Agent Memory provider (+ PrecisionMemBench single-turn retrieval result)**
>
> Adds `agent-memory`, a provider for
> [Agent Memory](https://github.com/MythologIQ-Labs-LLC/agent-memory). Agent Memory is a
> governed local memory runtime: writes are policy-checked and committed to a durable SQLite
> store, and recall uses lexical and exact-identity candidate routes followed by governed
> admission and ranking. There is no LLM at ingestion or retrieval.
>
> - Each document becomes one memory through the public `AgentMemory.remember` API, in a
>   per-`user_id` hashed scope.
> - `retrieve()` is one `AgentMemory.recall(query, budget=k)`. It returns the runtime's ranked
>   prefix unchanged, and refuses to return a fact it never ingested.
> - `concurrency = 1`, because the runtime is a single-writer store. `supports_filters = False`:
>   the provider receives only the query text.
>
> Setup: `pip install "agent-memory-reference @ git+https://github.com/MythologIQ-Labs-LLC/agent-memory@<sha>"`
> Usage: `amb run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval`
>
> Result at this revision: **15/77** (active 4/43, structural 6/25, trivially-empty 5/9),
> mean precision 0.1806, mean recall 0.9535, avg retrieve 22 ms. For reference, the published
> Hindsight entry is 66/77. Hindsight receives the structured `retrieval_filter` and runs an
> extraction LLM; this provider does neither. The full evidence bundle, including an
> independent review, is in the Agent Memory repository under
> `reports/benchmarks/amb-local-execution/`.

## Claims policy

Until the AMB maintainers merge the result and it appears on their site, the only accurate
description is "a self-run result on the AMB harness". It is not an AMB leaderboard entry.
