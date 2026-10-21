#!/bin/bash
# Local OpenAI-compatible server for the MemoryArena reproduction (same model for agent and judge).
exec $SCRATCH/llm-venv/bin/python -m llama_cpp.server --model $SCRATCH/models/qwen2.5-3b-instruct-q4_k_m.gguf \
  --model_alias qwen2.5-3b-instruct-q4_k_m \
  --n_ctx 16384 --n_threads 4 --seed 0 --host 127.0.0.1 --port 8080
