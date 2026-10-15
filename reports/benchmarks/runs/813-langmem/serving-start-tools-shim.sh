#!/bin/bash
# usage: start-tools-shim.sh LOGFILE   (port 8088; Hermes tool-call parsing for LLM-based comparators)
exec runuser -u benchrun -- env -i PATH=/usr/bin:/bin PYTHONPATH=/tmp/am-bench/graphiti-serving /tmp/am-bench/llamacpp-venv/bin/python /tmp/am-bench/graphiti-serving/llamacpp_hermes_tools_shim.py 8088 http://127.0.0.1:8090 http://127.0.0.1:8091 "$1"
