#!/bin/bash
export OPENAI_BASE_URL=http://127.0.0.1:8081/v1 OPENAI_API_KEY=local-placeholder-not-a-key TIKTOKEN_CACHE_DIR=$SCRATCH/amb-env/tiktoken-cache
cd $SCRATCH/marena/MemoryArena/env && setsid $SCRATCH/marena-venv/bin/python env_server.py > $SCRATCH/marena/env-server.log 2>&1 &
cd $SCRATCH/marena/MemoryArena/memory && setsid $SCRATCH/marena-venv/bin/python server.py > $SCRATCH/marena/memory-server.log 2>&1 &
