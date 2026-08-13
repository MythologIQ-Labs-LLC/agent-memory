"""Small state helpers for maintenance-run evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from . import receipts


def digest_for(record: dict[str, Any]) -> str:
    payload = deepcopy(record)
    payload.pop("evidence_digest", None)
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def seal(record: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(record)
    result["evidence_digest"] = digest_for(result)
    receipts.validate("maintenance-run-evidence.schema.json", result)
    return result


class CursorLedger:
    def __init__(self, cursor: str | int):
        self.cursor = cursor
        self.seen: set[str] = set()

    def apply(self, record: dict[str, Any]) -> str | int:
        if record["run_id"] in self.seen:
            raise ValueError("duplicate run")
        if record["cursor_before"] != self.cursor:
            raise ValueError("cursor mismatch")
        self.seen.add(record["run_id"])
        if record["transaction_status"] == "committed":
            self.cursor = record["cursor_after"]
        return self.cursor
