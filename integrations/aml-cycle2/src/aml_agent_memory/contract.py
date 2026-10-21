"""AML Cycle 2 Add/Search wire contract: request validation and response shapes.

Strict on declared fields, tolerant of undeclared ones: every field the contract marks
required is type-checked without coercion (a silently coerced value would be worse than a
422 because the platform fails a whole phase on malformed output), and every undeclared
field is ignored.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

MAX_TOP_K = 200
MAX_MESSAGES_PER_ADD = 1000
MAX_CONTENT_CHARS = 200_000


class ContractError(ValueError):
    """A request that violates the contract; mapped to HTTP 422."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def _nonblank_str(body: dict, key: str, errors: list[str]) -> str | None:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} must be a non-empty string")
        return None
    return value


def _timestamp_ms(value: Any, where: str, errors: list[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{where}.timestamp must be integer Unix milliseconds")
        return None
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            errors.append(f"{where}.timestamp must be integer Unix milliseconds")
            return None
        value = int(value)
    if value < 0:
        errors.append(f"{where}.timestamp must be non-negative")
        return None
    return value


def validate_add(body: Any) -> dict:
    if not isinstance(body, dict):
        raise ContractError(["body must be a JSON object"])
    errors: list[str] = []
    request_id = _nonblank_str(body, "request_id", errors)
    user_id = _nonblank_str(body, "user_id", errors)
    session_id = _nonblank_str(body, "session_id", errors)
    raw_messages = body.get("messages")
    messages: list[dict] = []
    if not isinstance(raw_messages, list) or not raw_messages:
        errors.append("messages must be a non-empty array")
    elif len(raw_messages) > MAX_MESSAGES_PER_ADD:
        errors.append(f"messages must hold at most {MAX_MESSAGES_PER_ADD} items")
    else:
        for index, item in enumerate(raw_messages):
            where = f"messages[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{where} must be an object")
                continue
            role = item.get("role")
            content = item.get("content")
            if not isinstance(role, str) or not role.strip():
                errors.append(f"{where}.role must be a non-empty string")
            if not isinstance(content, str) or not content.strip():
                errors.append(f"{where}.content must be a non-empty string")
            elif len(content) > MAX_CONTENT_CHARS:
                errors.append(f"{where}.content exceeds {MAX_CONTENT_CHARS} characters")
            timestamp = _timestamp_ms(item.get("timestamp"), where, errors)
            messages.append({"role": role, "content": content, "timestamp": timestamp})
    if errors:
        raise ContractError(errors)
    return {"request_id": request_id, "user_id": user_id, "session_id": session_id, "messages": messages}


def validate_search(body: Any) -> dict:
    if not isinstance(body, dict):
        raise ContractError(["body must be a JSON object"])
    errors: list[str] = []
    query = _nonblank_str(body, "query", errors)
    user_id = _nonblank_str(body, "user_id", errors)
    top_k = body.get("top_k")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        errors.append("top_k must be an integer")
    elif top_k < 0:
        errors.append("top_k must be non-negative")
    options = body.get("options")
    if options is not None and (not isinstance(options, list) or not all(isinstance(item, str) for item in options)):
        errors.append("options must be an array of strings")
    if errors:
        raise ContractError(errors)
    return {"query": query, "user_id": user_id, "top_k": min(top_k, MAX_TOP_K), "options": options or []}


def add_payload_digest(add: dict) -> str:
    """Idempotency fingerprint of everything an Add stores (request_id/user_id are the key)."""

    material = {"session_id": add["session_id"], "messages": add["messages"]}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def add_response(add: dict) -> dict:
    return {"success": True, "request_id": add["request_id"], "user_id": add["user_id"], "session_id": add["session_id"]}


def error_body(reason: str, errors: list[str] | None = None) -> dict:
    detail: dict[str, Any] = {"reason": reason}
    if errors:
        detail["errors"] = errors
    return {"detail": detail}
