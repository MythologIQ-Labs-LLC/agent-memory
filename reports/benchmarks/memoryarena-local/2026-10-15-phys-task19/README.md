# MemoryArena: one bounded task, memory-enabled vs memory-disabled (local, 2026-10-15)

This is a local reproduction of **one** [MemoryArena](https://github.com/ZexueHe/MemoryArena)
task: `formal_reasoning_phys`, task id 19 (paper `0000.0000`), three dependent subtasks. It was
run three times with the same model and configuration, varying only the memory system. The
harness's own `run_math.py` drove every run, and its own `eval.py` computed the metrics below.

**This is an internal bounded run, not a research result.** It covers one task, three
subtasks, and a 3B quantized local model as both agent and judge. It supports no claim about
memory systems in general, and is not comparable to the MemoryArena paper's numbers (gpt-5-mini
and others, all tasks).

## Native MemoryArena metrics (`env/env_systems/formal_reasoning_env/eval.py`)

| Arm (`memory_system_name`) | Task success (`overall_average_passrate`: last subtask correct) | Progress score (correct / subtasks) | Subtask 1 / 2 / 3 | Avg memory context (tokens) | Max memory context | Wall time |
|---|---:|---:|---|---:|---:|---:|
| `none`: memory disabled | 0 | **0.00** (0/3) | ✗ ✗ ✗ | 3 | 3 | 513 s |
| `long_context`: MemoryArena's native full-history memory | 0 | **0.33** (1/3) | ✗ ✓ ✗ | 1,237 | 1,845 | 679 s |
| `agent_memory`: Agent Memory via the public facade (added for this run) | 0 | **0.00** (0/3) | ✗ ✗ ✗ | 995 | 2,003 | 693 s |

What the runs show:

- **Subtask 1 is identical across arms where it should be.** The background text is given only
  in subtask 1, and subtasks 2–3 depend on it. At subtask 1 all memories are empty. The `none`
  and `agent_memory` prompts are therefore identical, and at temperature 0 they produced
  byte-identical answers, which checks that the arms differ only by memory.
- **Subtask 2 is where memory made the difference.** The `long_context` agent carried the
  unitarity setup from subtask 1 and answered **2**, which is the gold answer. The `none` agent
  had no background and answered the symbolic `|A| + (B+C)/2`. The `agent_memory` agent
  received three memories from its top-3 recall and answered `3 + i`, which is wrong.
- **No arm completed the task.** Subtask 3 (gold `1/2`) was wrong everywhere: `long_context`
  answered `2`.

## Configuration (identical across arms except `memory_system_name`)

| Item | Value |
|---|---|
| Harness | ZexueHe/MemoryArena `6cd9de14b71915e39ac742a20dc33785e14b6aab` plus `memoryarena-local-reproduction.patch` |
| Dataset | HF `ZexueHe/memoryarena` @ `da1a37c8b19280e18627ca01cf368195a5e1d92e`, config `formal_reasoning_phys`, split `test`, `task_ids: [19]` |
| Agent and judge model | `Qwen/Qwen2.5-3B-Instruct-GGUF` @ `7dabda4d13d513e3e842b20f0d435c732f172cbe`, file `qwen2.5-3b-instruct-q4_k_m.gguf` (sha256 `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`), served by `llama-cpp-python` 0.3.16 with the model's own chat template, `n_ctx` 16384, 4 threads, seed 0 |
| Sampling | Temperature 0 for the agent and the judge. The upstream phys config uses judge temperature 1.0, which gpt-5-mini requires; it was set to 0 here for determinism, in every arm |
| Token caps | The upstream configs: agent `max_tokens` 8192, judge 4096. The tool loop sends none, as upstream does |
| Tool loop | `MATH_AGENT_MAX_TOOL_ITERATIONS` default (3); the `reasoning` tool, as upstream |
| Memory systems | `none` (added): an empty memory, wrapped exactly like an empty `long_context`. `long_context`: upstream, 120k-token window. `agent_memory` (added): `agent-memory-reference` installed from GitHub at `7a1ab45c85b7`, one governed `remember` per chunk, `recall(prompt, budget=3)` per prompt, using the same `<memory>` formatting and `top_k=3` as the upstream `rag` system |
| Host | 4 vCPU, CPU only, about 9 generated tokens/s. 35 LLM calls in total, 12,675 completion tokens. No paid API. No external inference |

## Changes to the harness (`memoryarena-local-reproduction.patch`)

1. `memory/memory_systems/__init__.py`: each memory system's import is optional, so a system
   whose third-party package is absent (mirix, letta, mem0 and others) no longer stops the
   memory server.
2. `memory/memory_systems/none.py` adds the memory-disabled baseline. `run_math.py` cannot run
   without a memory server, and the server rejects unknown names.
3. `memory/memory_systems/agent_memory.py` adds the `agent_memory` system.
4. `run_math.py` gains an optional `task_ids` filter. The patch also removes a duplicated
   `main(json_config)` call that ran every task twice.
5. Three configs, `configs/formal_reasoning_configs/phys_task19_{none,long_context,agent_memory}_local.json`.

The serving setup is in `serving/`:

- **`hermes_proxy.py`.** Qwen2.5 emits Hermes-style `<tool_call>` text. The proxy converts it
  into OpenAI `tool_calls`, which is what vLLM's `--tool-call-parser hermes` does. It also
  forwards the client's `max_completion_tokens` as `max_tokens`, which llama.cpp would otherwise
  ignore. It logs every call to `logs/llm-calls.jsonl`.
- **`llm-server.sh`** and **`memoryarena-servers.sh`** start the LLM server and the
  MemoryArena env and memory servers.

## Failures and caveats, recorded rather than hidden

- **A first attempt was invalid and is not reported above.** It used llama.cpp's
  `chatml-function-calling` handler, which leaked its own format prefix: several final answers
  were the literal string `functions.reasoning:`. Separately, a stale memory server made the
  `agent_memory` arm fail with HTTP 400. **MemoryArena's `run_math.py` caught that exception,
  printed `!!!error!` and exited 0.** That is a failure-handling weakness in the harness. This
  run's status file counts swallowed errors per arm: all are 0 (`logs/run-status.txt`).
- **The model sometimes left a tool call unclosed.** In 3 of the 35 calls, the model wrote prose
  with an inline `<tool_call>` that it never closed, so no parser can recover it. One of those
  is the `none` arm's subtask 3 answer.
- **The judge is MemoryArena's own.** It is a substring check for "yes", called without the
  question, as upstream. With a 3B judge the verdicts are noisy. Every verdict is in the
  `result.jsonl` files and can be checked by hand against the gold answers. Here the single
  "yes" (`long_context` subtask 2, answer `2`, gold `2`) is correct.
- **License.** The MemoryArena repository and dataset declare no license. The result files
  contain the task's questions and gold answers in MemoryArena's native output format, and are
  kept for audit only.

## Reproduce

```bash
git clone https://github.com/ZexueHe/MemoryArena && cd MemoryArena && git checkout 6cd9de14b71915e39ac742a20dc33785e14b6aab
git apply <this-dir>/memoryarena-local-reproduction.patch
pip install fastapi uvicorn pydantic requests openai datasets tiktoken numpy python-dotenv \
  "agent-memory-reference @ git+https://github.com/MythologIQ-Labs-LLC/agent-memory@<sha>"   # see environment/
pip install "llama-cpp-python[server]==0.3.16"   # separate env; download the GGUF above
serving/llm-server.sh &                                   # :8080
python serving/hermes_proxy.py 8081 llm-calls.jsonl &     # :8081
serving/memoryarena-servers.sh                            # env :8001, memory :8000 (OPENAI_BASE_URL=http://127.0.0.1:8081/v1)
for arm in none long_context agent_memory; do
  OPENAI_BASE_URL=http://127.0.0.1:8081/v1 OPENAI_API_KEY=placeholder \
    python run_math.py -c configs/formal_reasoning_configs/phys_task19_${arm}_local.json
done
python env/env_systems/formal_reasoning_env/eval.py configs/formal_reasoning_configs/phys_task19_none_local.json
```

If `openaipublic.blob.core.windows.net` is unreachable, `tiktoken` needs `o200k_base` in
`TIKTOKEN_CACHE_DIR`. The file bundled in `litellm` as `fb374d419588a4632f3f557e76b4b70aebbca790`
has sha256 `446a9538…1a2d`, equal to tiktoken's pinned hash.
