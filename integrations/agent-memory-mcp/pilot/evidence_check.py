"""Host-side output check for the restricted alpha pilot (deterministic, no model).

It compares an agent's final text with what the Agent Memory tools actually returned in that
session, and withholds the text from display when it finds an unsupported claim:

* ``uncited_key``: a ``memory:`` key that no tool result delivered and no tool call or user
  prompt named;
* ``unsourced_quote``: a double-quoted span of 12+ characters that is not recalled text, a tool
  argument or the user's prompt (the contract reserves double quotes for recalled text);
* ``verification_claim``: the memory or retrieval system said to have verified or validated
  something;
* ``absence_claim``: information said not to exist, rather than not found in retrieved memory
  (a statement that a failed search does *not* show absence is not one).

It is a guard against a few explicit failure shapes, not a semantic judge of the answer.
"""
from __future__ import annotations

import re
from typing import Iterable

KEY = re.compile(r"memory:[A-Za-z0-9_.:-]*[A-Za-z0-9_]")
# Quotes pair left to right; spans shorter than 12 characters are paired but not checked.
QUOTE = re.compile(r"\"([^\"\n]*)\"")
# "confirmed" is left out: agents use it for a tool's commit result ("the save was confirmed").
VERIFY = re.compile(
    r"(?<!not )(?<!never )(?<!n't )\b(?:verified|validated)\b[^.\n]{0,40}\b(?:by|in|through)\s+(?:the\s+)?"
    r"(?:memory|retrieval|agent memory|system|tool)", re.IGNORECASE)
VERIFY_SUBJECT = re.compile(
    r"\b(?:memory|retrieval|the system|the tool)s?\s+(?:has\s+|have\s+)?(?:verified|validated)\b", re.IGNORECASE)
ABSENCE = re.compile(
    r"\b(?:does not exist|doesn't exist|do not exist|don't exist|no such (?:memory|record|information)|"
    r"there is no (?:record|memory|information|such)|is not recorded anywhere|nothing exists)\b", re.IGNORECASE)
# Earlier in the same sentence: the absence is being disclaimed, not asserted.
DISCLAIMED = re.compile(
    r"\b(?:do(?:es)?n't|do(?:es)? not|is not|isn't|are not|aren't|cannot|can't)\s+(?:show|mean|prove|imply|establish|indicate)"
    r"|\bnot (?:proof|evidence)\b|\bno proof\b", re.IGNORECASE)


def _normal(text: str) -> str:
    return " ".join(text.replace("“", '"').replace("”", '"').replace("’", "'").split())


def check(final_text: str, *, delivered_contents: Iterable[str], delivered_keys: Iterable[str],
          named: Iterable[str]) -> list[dict]:
    """Flags for ``final_text``. ``named`` is the user prompt plus every tool argument value."""
    text = _normal(final_text)
    contents = [_normal(c) for c in delivered_contents]
    named_text = " ".join(_normal(n) for n in named)
    # A key quoted inside recalled text was delivered too (as content), so citing it is sourced.
    allowed_keys = set(delivered_keys) | set(KEY.findall(named_text)) | {k for c in contents for k in KEY.findall(c)}
    flags = []
    for key in sorted(set(KEY.findall(text)) - allowed_keys):
        flags.append({"flag": "uncited_key", "detail": key})
    for quoted in QUOTE.findall(text):
        q = quoted.strip()
        if len(q) >= 12 and not any(q in c for c in contents) and q not in named_text:
            flags.append({"flag": "unsourced_quote", "detail": q[:120]})
    for pattern, name in ((VERIFY, "verification_claim"), (VERIFY_SUBJECT, "verification_claim"), (ABSENCE, "absence_claim")):
        for match in pattern.finditer(text):
            sentence = re.split(r"[.!?]\s", text[:match.start()])[-1]
            if name == "absence_claim" and DISCLAIMED.search(sentence):
                continue
            flags.append({"flag": name, "detail": match.group(0)[:120]})
    return flags


def displayed(final_text: str, flags: list[dict], delivered: list[dict]) -> str:
    """What the restricted host shows: the agent's text, or a withheld notice with the evidence."""
    if not flags:
        return final_text
    lines = ["[Withheld by the host evidence check: " + ", ".join(sorted({f["flag"] for f in flags})) + "]",
             "Retrieved evidence (untrusted, unverified):"]
    lines += [f'- [key: {e.get("memory_ref")} | state: {e.get("state")} | latest for key: {e.get("latest_for_key")}] '
              f'"{e.get("content")}"' for e in delivered] or ["- (none delivered)"]
    return "\n".join(lines)
