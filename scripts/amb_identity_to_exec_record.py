#!/usr/bin/env python3
"""Convert an AMB evidence ``execution-identity.json`` (scripts/run_amb_local_evidence.py) into the
exec-record shape ``reference/build_comparator_execution_manifest.py`` reads (argv, started_utc,
wall_seconds, exit_status, peak_rss_mib). Values are copied, never recomputed."""

import json
import sys
from datetime import datetime

identity = json.load(open(sys.argv[1], encoding="utf-8"))
started = datetime.fromisoformat(identity["started_utc"]).strftime("%Y-%m-%dT%H:%M:%SZ")
record = {"argv": identity["command"], "started_utc": started, "wall_seconds": identity["wall_time_s"],
          "exit_status": identity["exit_code"], "peak_rss_mib": round(identity["peak_rss_kib"] / 1024, 1),
          "source": "converted from execution-identity.json", "credentials_present_in_child": identity.get("credentials_present_in_child")}
json.dump(record, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
print(sys.argv[2])
