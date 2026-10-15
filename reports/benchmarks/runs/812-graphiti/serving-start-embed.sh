#!/bin/bash
exec nice -n 10 runuser -u benchrun -- env -i PATH=/usr/bin:/bin HOME=/home/benchrun /tmp/am-bench/llamacpp-venv/bin/python -m llama_cpp.server --model /tmp/am-bench/models/nomic-embed-gguf/nomic-embed-text-v1.5.f16.gguf --model_alias nomic-embed-text --embedding true --n_ctx 2048 --n_batch 2048 --n_ubatch 2048 --n_threads 2 --host 127.0.0.1 --port 8091
