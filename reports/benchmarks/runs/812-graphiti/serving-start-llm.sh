#!/bin/bash
# Local LLM server for the Graphiti comparator (#812): the model's own chat template, 16k context, seed 0.
exec nice -n 10 runuser -u benchrun -- env -i PATH=/usr/bin:/bin HOME=/home/benchrun /tmp/am-bench/llamacpp-venv/bin/python -m llama_cpp.server --model /tmp/am-bench/models/qwen2.5-3b-gguf/qwen2.5-3b-instruct-q4_k_m.gguf --model_alias qwen2.5-3b-instruct-q4_k_m --n_ctx 16384 --n_threads 4 --seed 0 --host 127.0.0.1 --port 8090
