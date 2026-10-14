"""Offline contract tests for the single architecture filing policy (#797)."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_architecture_index.py"
spec = importlib.util.spec_from_file_location("catalog_validation", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def catalog(*, duplicate=False, count_delta=0, omit=None):
    content = ["# Architecture", "## 2. Architecture shelf catalog"]
    files = set()
    for shelf in module.SHELVES:
        doc = "docs/00-" + shelf.lower() + ".md"
        files.add(doc)
        content.append(f"### {shelf} · Shelf")
        links = [f"[{shelf}](00-{shelf.lower()}.md)"]
        if duplicate and shelf == "G":
            links.append("[Repeated](00-f.md)")
        if shelf == omit:
            links = []
        content.append(
            f"**Numbered-document register ({len(links) + (count_delta if shelf == 'F' else 0)}):** "
            + " · ".join(links)
        )
    content.append("## 3. More")
    return "\n".join(content), files


class ArchitectureCatalogValidationTests(unittest.TestCase):
    def test_one_shelf_per_tracked_document(self):
        text, paths = catalog()
        self.assertEqual(module.validate_catalog(text, paths), [])

    def test_unregistered_document_is_detected(self):
        text, paths = catalog()
        paths.add("docs/44-new-architecture.md")
        self.assertTrue(any("no shelf" in x for x in module.validate_catalog(text, paths)))

    def test_duplicate_registration_is_detected(self):
        text, paths = catalog(duplicate=True)
        self.assertTrue(any("indexed 2 times" in x for x in module.validate_catalog(text, paths)))

    def test_declared_count_drift_is_detected(self):
        text, paths = catalog(count_delta=2)
        self.assertTrue(any("declares 3" in x for x in module.validate_catalog(text, paths)))

    def test_missing_shelf_registration_is_detected(self):
        text, paths = catalog(omit="S")
        self.assertTrue(any("no shelf" in x for x in module.validate_catalog(text, paths)))

    def test_untracked_index_entry_is_detected(self):
        text, paths = catalog()
        paths.remove("docs/00-f.md")
        self.assertTrue(any("registered but not tracked" in x for x in module.validate_catalog(text, paths)))


if __name__ == "__main__":
    unittest.main()
