#!/bin/bash
# usage: start-shim.sh LOGFILE
exec runuser -u benchrun -- env -i PATH=/usr/bin:/bin /tmp/am-bench/llamacpp-venv/bin/python /tmp/am-bench/graphiti-serving/graphiti_llamacpp_shim.py 8089 http://127.0.0.1:8090 http://127.0.0.1:8091 "$1"
