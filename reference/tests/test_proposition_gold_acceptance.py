"""#594 accepted-gold integrity tests, separate from draft provenance tests."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import proposition_semantics_evaluator as E  # noqa: E402

FIXTURES = REFERENCE / "fixtures" / "benchmarks" / "proposition-semantics"


class AcceptedGoldTests(unittest.TestCase):
    def test_gold_v1_materializes_exact_frozen_v5_items(self) -> None:
        manifest = json.loads((FIXTURES / "gold-v1.json").read_text(encoding="utf-8"))
        v5_bytes = (FIXTURES / "draft-annotations-v5.json").read_bytes()
        v5 = json.loads(v5_bytes)
        self.assertEqual(hashlib.sha256(v5_bytes).hexdigest(), manifest["source"]["sha256"])
        gold = E.load_gold(FIXTURES / "gold-v1.json")
        self.assertEqual(gold["items"], v5["items"])
        self.assertEqual(gold["accepted_source"]["sha256"], manifest["source"]["sha256"])
        self.assertEqual(gold["acceptance"]["item_count"], 268)

    def test_v1_through_v5_still_refuse_direct_loading(self) -> None:
        for version in range(1, 6):
            with self.assertRaises(E.GoldNotAccepted):
                E.load_gold(FIXTURES / f"draft-annotations-v{version}.json")

    def test_gold_v1_refuses_source_digest_drift(self) -> None:
        manifest = json.loads((FIXTURES / "gold-v1.json").read_text(encoding="utf-8"))
        source = (FIXTURES / "draft-annotations-v5.json").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = dict(manifest)
            bad["source"] = dict(manifest["source"])
            (root / bad["source"]["file"]).write_text(source + "\n", encoding="utf-8")
            (root / "gold-v1.json").write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(E.GoldNotAccepted):
                E.load_gold(root / "gold-v1.json")

    def test_property_aliases_are_frozen_empty_before_scoring(self) -> None:
        aliases = json.loads((FIXTURES / "property-aliases-gold-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(aliases["aliases"], {})
        self.assertIn("never fitted", aliases["policy"])


if __name__ == "__main__":
    unittest.main()
