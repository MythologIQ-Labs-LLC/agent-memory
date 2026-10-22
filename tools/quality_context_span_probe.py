"""Offline evaluation-only span probe over authorized recall_context packages.

Does not change AgentMemory, select evidence for a consumer, or establish
relevance/abstention. It locates literal-overlap spans within content the
facade already delivered. Everything else stays uncertain; never infer
identities or text beyond what this package returned.

By default the report includes no memory text. --include-previews explicitly
opts into plaintext output, so use it only in a trusted local environment.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
_MAX_SPANS = 512
_MAX_TEXT = 1_000_000
_DELIVERED = frozenset(("resolved", "truncated"))
# Grammatical glue only, not domain/benchmark-specific words.
_IGNORED = frozenset("the and for with from into onto does which where what who whose".split())


def _terms(value: str) -> set[str]:
    """Observe literal token overlap only, NOT semantic relevance or entailment."""
    return {term.casefold() for term in _WORD.findall(value)
            if len(term) >= 3 and term.casefold() not in _IGNORED}


def _ranges(value: str) -> list[tuple[int, int]]:
    """Return a bounded, lossless span partition (offsets reconstruct the original)."""
    if not value:
        return []
    if len(value) > _MAX_TEXT:
        raise ValueError("content too long for diagnostic probe")
    out: list[tuple[int, int]] = []
    start = 0
    for boundary in _BOUNDARY.finditer(value):
        if len(out) >= _MAX_SPANS - 1:
            break
        if boundary.end() > start:
            out.append((start, boundary.end()))
            start = boundary.end()
    if start < len(value):
        out.append((start, len(value)))
    assert out and out[0][0] == 0 and out[-1][1] == len(value)
    assert all(left[1] == right[0] for left, right in zip(out, out[1:]))
    return out


def inspect_package(package: Mapping[str, Any], query: str, *,
                    include_previews: bool = False) -> dict:
    """Inspect delivered text; do not drop evidence or assign a relevance verdict."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(package, Mapping) or not isinstance(package.get("items"), list):
        raise ValueError("expected recall_context package with items list")
    raw_returned = (package.get("recall") or {}).get("returned")
    if not isinstance(raw_returned, list):
        raise ValueError("package must include recalled public identifiers")
    allowed = set(raw_returned)
    query_terms = _terms(query)
    seen: set[str] = set()
    items: list[dict] = []
    for item in package["items"]:
        if not isinstance(item, Mapping):
            raise ValueError("malformed context item")
        ref = item.get("fact_ref")
        state = item.get("state")
        if not isinstance(ref, str) or ref not in allowed or ref in seen:
            raise ValueError("item not uniquely present in authorized recall")
        seen.add(ref)
        if state not in _DELIVERED:
            # Read no content for withheld, unresolved, budget or selection omissions.
            items.append({"fact_ref": ref, "state": state,
                          "assessment": "unavailable_not_assessed"})
            continue
        value = item.get("content")
        if not isinstance(value, str):
            raise ValueError("delivered item has no string content")
        spans = []
        matched_chars = 0
        for index, (start, end) in enumerate(_ranges(value)):
            overlap = sorted(query_terms & _terms(value[start:end]))
            if overlap:
                matched_chars += end - start
            span = {
                "index": index, "start": start, "end": end,
                "assessment": "literal_overlap_only" if overlap else "uncertain_no_literal_overlap",
                "matched_terms": overlap,
            }
            if include_previews:
                span["text"] = value[start:end]
            spans.append(span)
        indices = sorted(range(len(spans)),
                         key=lambda i: (-len(spans[i]["matched_terms"]), i))
        items.append({
            "fact_ref": ref, "state": state, "total_chars": len(value),
            "source_is_partial": state == "truncated",
            "literal_overlap_chars": matched_chars,
            "uncertain_chars": len(value) - matched_chars,
            "span_count": len(spans),
            "fronting_suggestion": [i for i in indices if spans[i]["matched_terms"]],
            "spans": spans,
            "assessment": "literal_spans_found" if matched_chars else "insufficient_lexical_signal",
        })
    # Including omitted and unavailable refs is required, lest they silently
    # disappear and create a false positive "no evidence" interpretation.
    if seen != allowed or len(raw_returned) != len(allowed):
        raise ValueError("package must cover all distinct returned identifiers")
    return {
        "schema": "agent-memory-context-span-probe/0.1.0",
        "status": "observational_only_not_relevance_or_answerability",
        "query_term_count": len(query_terms),
        "returned_count": len(raw_returned),
        "delivered_count": sum(item["state"] in _DELIVERED for item in items),
        "incomplete_or_omitted_count": sum(item["state"] not in _DELIVERED for item in items),
        "items": items,
        "plaintext_included": include_previews,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path,
                        help="Authorized local recall_context JSON")
    parser.add_argument("--query", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--include-previews", action="store_true",
                        help="Intentionally emit plaintext spans locally")
    args = parser.parse_args()
    report = inspect_package(
        json.loads(args.package.read_text(encoding="utf-8")),
        args.query, include_previews=args.include_previews,
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
