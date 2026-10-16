#!/usr/bin/env python3
"""Check that the one Agent Memory architecture catalog files every numbered doc once.

Stdlib-only, no inference or network, no governance/ADR status mutation.
The existing Markdown validator handles ordinary link targets; this validator
enforces the library's *filing* invariant that a link validator cannot test.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

SHELVES = ("F", "G", "L", "R", "S", "I", "E", "X")
NUMBERED_PATH = re.compile(r"^docs/[0-9]{2}-[^/]+\.md$")
SHELF_HEADING = re.compile(r"^### ([A-Z]) · ")
REGISTER = re.compile(r"^\*\*Numbered-document register \(([0-9]+)\):\*\* (.*)$")
# A register entry may carry an optional #fragment or "title"; the registered path is the .md target only.
DOCUMENT_LINK = re.compile(r"\[[^\]]+\]\(([0-9]{2}-[^)#\s]+\.md)(?:#[^)\s]*)?(?:\s+\"[^\"]*\")?\)")


CLAIM_START = "<!-- BEGIN CLAIM OWNERS -->"
CLAIM_END = "<!-- END CLAIM OWNERS -->"
# Owner is either a governing GitHub issue (live delivery decisions only) or a tracked
# repository path; a path ending in "/" names a collection whose members each own their own entry.
CLAIM_ROW = re.compile(
    r"^\|\s*([a-z][a-z0-9-]*)\s*\|\s*([a-z]+)\s*\|\s*"
    r"(#[1-9][0-9]*|(?:docs|reports|reference|schemas)/[^|\s]+)\s*\|$"
)
CLAIM_CLASSES = {"contract", "qualification", "baseline", "evidence", "doctrine", "roadmap", "delivery"}
ISSUE_CLASSES = {"delivery"}
# A document that labels itself historical, revision-bound or superseded is a projection, never an owner.
DEMOTION_LABEL = re.compile(r"^\W*(status|purpose)\b", re.IGNORECASE)
DEMOTION_TERM = re.compile(r"\b(historical|revision-bound|superseded|archived)\b", re.IGNORECASE)
HEAD_LINES = 12


def _demoted(head: str) -> bool:
    for line in head.splitlines()[:HEAD_LINES]:
        if (line.startswith("#") or DEMOTION_LABEL.match(line)) and DEMOTION_TERM.search(line):
            return True
    return False


def validate_claim_owners(
    text: str, tracked_paths: set[str], heads: Mapping[str, str] | None = None
) -> list[str]:
    """Check explicit claim routing without inferring which prose is true.

    ``heads`` maps a Markdown owner path to its opening lines so a revision-bound or
    historical document cannot be promoted to owner; ``main`` always supplies it.
    """
    errors: list[str] = []
    if text.count(CLAIM_START) != 1 or text.count(CLAIM_END) != 1:
        return ["claim owner declarations require one start and one end marker"]
    if text.index(CLAIM_END) < text.index(CLAIM_START):
        return ["claim owner end marker precedes start marker"]
    section = text.split(CLAIM_START, 1)[1].split(CLAIM_END, 1)[0]
    seen: set[str] = set()
    count = 0
    for line in section.splitlines():
        if not line.strip() or line.startswith("| Claim ID") or line.startswith("|---"):
            continue
        match = CLAIM_ROW.fullmatch(line.strip())
        if not match:
            errors.append(f"invalid claim owner declaration: {line.strip()}")
            continue
        claim, kind, owner = match.groups()
        count += 1
        if claim in seen:
            errors.append(f"duplicate claim owner: {claim}")
        seen.add(claim)
        if kind not in CLAIM_CLASSES:
            errors.append(f"{claim}: unknown claim class {kind}")
        if owner.startswith("#"):
            if kind not in ISSUE_CLASSES:
                errors.append(f"{claim}: issue owner {owner} only allowed for live delivery claims")
            continue
        if kind in ISSUE_CLASSES:
            errors.append(f"{claim}: {kind} claims must be owned by the governing issue, not {owner}")
        if ".." in owner.split("/"):
            errors.append(f"{claim}: owner path escapes repository: {owner}")
        elif owner.endswith("/"):
            if not any(path.startswith(owner) for path in tracked_paths):
                errors.append(f"{claim}: owner collection has no tracked files: {owner}")
        elif owner not in tracked_paths:
            errors.append(f"{claim}: owner path not tracked: {owner}")
        elif heads is not None and owner.endswith(".md") and _demoted(heads.get(owner, "")):
            errors.append(f"{claim}: owner is historical or revision-bound: {owner}")
    if not count:
        errors.append("claim owner declarations are empty")
    return errors

def validate_catalog(text: str, tracked_paths: set[str]) -> list[str]:
    """Return actionable discrepancies without reading source metadata as authority."""

    errors: list[str] = []
    current_shelf: str | None = None
    current_registers: set[str] = set()
    seen_shelves: set[str] = set()
    registrations: list[tuple[str, str]] = []
    in_catalog = False

    for line_no, line in enumerate(text.splitlines(), 1):
        if line == "## 2. Architecture shelf catalog":
            in_catalog = True
            continue
        if in_catalog and line.startswith("## ") and not line.startswith("## 2."):
            in_catalog = False
            current_shelf = None
            continue
        if not in_catalog:
            continue

        heading = SHELF_HEADING.match(line)
        if heading:
            shelf = heading.group(1)
            if shelf not in SHELVES:
                errors.append(f"line {line_no}: unknown architecture shelf {shelf!r}")
            if shelf in seen_shelves:
                errors.append(f"line {line_no}: duplicate architecture shelf {shelf}")
            seen_shelves.add(shelf)
            current_shelf = shelf
            continue

        if not line.startswith("**Numbered-document register "):
            continue

        match = REGISTER.fullmatch(line)
        if not match:
            errors.append(f"line {line_no}: malformed numbered-document register")
            continue
        if current_shelf is None:
            errors.append(f"line {line_no}: numbered register without shelf heading")
            continue
        if current_shelf in current_registers:
            errors.append(f"line {line_no}: more than one numbered register in {current_shelf}")
        current_registers.add(current_shelf)
        declared = int(match.group(1))
        linked_paths = ["docs/" + link for link in DOCUMENT_LINK.findall(match.group(2))]
        if len(linked_paths) != declared:
            errors.append(
                f"line {line_no}: shelf {current_shelf} declares {declared}, "
                f"but links {len(linked_paths)} numbered docs"
            )
        registrations.extend((current_shelf, path) for path in linked_paths)

    if not seen_shelves:
        errors.append("missing Architecture shelf catalog section / shelf headings")
    for shelf in SHELVES:
        if shelf not in seen_shelves:
            errors.append(f"missing shelf {shelf}")
        if shelf not in current_registers:
            errors.append(f"missing numbered-document register for shelf {shelf}")

    counts = Counter(path for _shelf, path in registrations)
    for path, count in sorted(counts.items()):
        if count != 1:
            errors.append(f"{path}: indexed {count} times; expected exactly once")
        if path not in tracked_paths:
            errors.append(f"{path}: registered but not tracked in git")
    expected = {path for path in tracked_paths if NUMBERED_PATH.fullmatch(path)}
    for path in sorted(expected - set(counts)):
        errors.append(f"{path}: tracked numbered architecture doc has no shelf")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = root / "docs" / "ARCHITECTURE_INDEX.md"
    if not catalog.is_file():
        print("Missing canonical architecture library index: docs/ARCHITECTURE_INDEX.md", file=sys.stderr)
        return 1
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        print(f"Cannot inventory tracked files: {exc}", file=sys.stderr)
        return 2

    text = catalog.read_text(encoding="utf-8")
    tracked_paths = {path for path in tracked if path}
    heads = {}
    for path in tracked_paths:
        if path.endswith(".md") and path in text:
            with (root / path).open(encoding="utf-8") as handle:
                heads[path] = "".join(handle.readline() for _ in range(HEAD_LINES))
    errors = validate_catalog(text, tracked_paths) + validate_claim_owners(text, tracked_paths, heads)
    if errors:
        for error in errors:
            print(f"Architecture catalog drift: {error}", file=sys.stderr)
        return 1
    numbered = sum(bool(NUMBERED_PATH.fullmatch(path)) for path in tracked)
    print(f"Architecture catalog valid: {numbered} numbered docs, exactly one shelf each.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
