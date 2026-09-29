from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import rfc8785


PROFILE = "agent-memory-canonical-json-v2"


class CanonicalJsonV2Error(ValueError):
    """Candidate-profile refusal with a stable conformance reason."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


def _validate_unicode_scalar_string(value: str) -> None:
    for ch in value:
        codepoint = ord(ch)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise CanonicalJsonV2Error("invalid_unicode_scalar")


def _write_string(value: str) -> bytes:
    _validate_unicode_scalar_string(value)
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _write_float(value: float) -> bytes:
    if not math.isfinite(value):
        raise CanonicalJsonV2Error("non_finite_binary64")
    if value == 0.0:
        return b"-0.0" if math.copysign(1.0, value) < 0.0 else b"0.0"

    token = rfc8785.dumps(value).decode("ascii")
    if "." not in token and "e" not in token:
        token += ".0"
    return token.encode("ascii")


def canonical_bytes_v2(value: Any) -> bytes:
    """Serialize one typed value under the accepted #609 candidate byte profile.

    This function is qualification-only. It is not wired into persistence, restart,
    bmerkle, gsect, or any existing identity surface.
    """

    if value is None:
        return b"null"
    if isinstance(value, bool):
        return b"true" if value else b"false"
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, float):
        return _write_float(value)
    if isinstance(value, str):
        return _write_string(value)
    if isinstance(value, Mapping):
        keys = list(value.keys())
        if any(not isinstance(key, str) for key in keys):
            raise CanonicalJsonV2Error("non_string_object_key")
        for key in keys:
            _validate_unicode_scalar_string(key)
        parts: list[bytes] = []
        for key in sorted(keys):
            parts.append(_write_string(key) + b":" + canonical_bytes_v2(value[key]))
        return b"{" + b",".join(parts) + b"}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return b"[" + b",".join(canonical_bytes_v2(item) for item in value) + b"]"
    raise CanonicalJsonV2Error("unsupported_value", f"unsupported canonical value type: {type(value).__name__}")


def canonicalize_json_text_v2(text: str) -> bytes:
    """Strict JSON-text boundary used only for parse-boundary conformance checks.

    Duplicate object names and non-finite JSON constants are refused before bytes.
    Typed runtime values should call ``canonical_bytes_v2`` directly.
    """

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalJsonV2Error("duplicate_object_key")
            result[key] = value
        return result

    def reject_constant(_: str) -> Any:
        raise CanonicalJsonV2Error("non_finite_binary64")

    try:
        value = json.loads(text, object_pairs_hook=object_pairs, parse_constant=reject_constant)
    except CanonicalJsonV2Error:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CanonicalJsonV2Error("invalid_json_text", str(exc)) from exc
    return canonical_bytes_v2(value)
