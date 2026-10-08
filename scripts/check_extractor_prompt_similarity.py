#!/usr/bin/env python3
"""S6 check for the #732 remediation extractor (docs/plan-732-remediation.md R2).

Every text in the frozen extractor prompt, the frozen output schema and the typed-proposition
test stubs must have similarity below 0.5 against every write text and query of the frozen
measurement corpus (``corpus.json`` and ``variants.json``). Similarity is the G3b function of
``scripts/check_generalization_corpus.py``, imported, not copied.

Checked texts:

* each non-empty line of ``FROZEN_PROMPT`` and every string (keys included) of
  ``FROZEN_OUTPUT_SCHEMA`` (``proposition_extraction.frozen_texts``);
* every string in the JSON files under ``reference/testdata/typed_proposition/`` (strings that
  are themselves JSON documents are decoded and walked);
* every string constant in ``reference/tests/test_typed_propositions.py``.

The script only compares texts. It never runs the runtime, and it prints only the checked
texts that fail with their score, never a corpus text. Exit 0 when every text passes, 1 when
any fails, 2 when an input is missing. ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "reference"))

from check_generalization_corpus import THRESHOLD, record_texts, similarity  # noqa: E402
from agentmem_ref.runtime.proposition_extraction import frozen_texts  # noqa: E402

FREEZE = ROOT / "reports" / "benchmarks" / "currentness-generalization" / "freeze"
STUB_DIR = ROOT / "reference" / "testdata" / "typed_proposition"
TEST_MODULE = ROOT / "reference" / "tests" / "test_typed_propositions.py"


def _json_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        decoded = None
        if value[:1] in "{[":
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                decoded = None
        if decoded is None:
            yield value
        else:
            yield from _json_strings(decoded)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)


def checked_texts(stub_dir: Path = STUB_DIR, test_module: Path = TEST_MODULE) -> dict[str, list[str]]:
    groups = {"frozen_prompt_and_schema": frozen_texts(), "test_stubs": []}
    for path in sorted(stub_dir.glob("*.json")):
        groups["test_stubs"] += list(_json_strings(json.loads(path.read_text(encoding="utf-8"))))
    tree = ast.parse(test_module.read_text(encoding="utf-8"))
    groups["test_stubs"] += [node.value for node in ast.walk(tree)
                             if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    return {name: sorted({text for text in texts if text.strip()}) for name, texts in groups.items()}


def corpus_texts(freeze: Path = FREEZE) -> list[str]:
    texts: list[str] = []
    for name in ("corpus.json", "variants.json"):
        for record in json.loads((freeze / name).read_text(encoding="utf-8")):
            if isinstance(record, dict) and "writes" in record:
                texts += [text for text in record_texts(record) if text]
    return texts


def check(checked: dict[str, list[str]], references: list[str]) -> dict[str, Any]:
    failures, maximum, count = [], 0.0, 0
    for group, texts in checked.items():
        for text in texts:
            count += 1
            score = max((similarity(text, reference) for reference in references), default=0.0)
            maximum = max(maximum, score)
            if score >= THRESHOLD:
                failures.append({"group": group, "text": text, "similarity": round(score, 4)})
    return {"threshold": THRESHOLD, "checked_texts": count, "reference_texts": len(references),
            "max_similarity": round(maximum, 4), "failures": failures, "authority_effect": "none"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--freeze", type=Path, default=FREEZE)
    args = parser.parse_args(argv)
    if not (args.freeze / "corpus.json").exists() or not (args.freeze / "variants.json").exists():
        sys.stderr.write(f"missing frozen corpus under {args.freeze}\n")
        return 2
    report = check(checked_texts(), corpus_texts(args.freeze))
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
