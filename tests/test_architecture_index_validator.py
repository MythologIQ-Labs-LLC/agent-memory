"""Offline contract tests for the single architecture filing policy (#797)."""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
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

    def test_fragment_or_title_on_register_link_still_registers(self):
        text, paths = catalog()
        text = text.replace("[F](00-f.md)", '[F](00-f.md#purpose "Shelf F")')
        self.assertEqual(module.validate_catalog(text, paths), [])

    def test_untracked_index_entry_is_detected(self):
        text, paths = catalog()
        paths.remove("docs/00-f.md")
        self.assertTrue(any("registered but not tracked" in x for x in module.validate_catalog(text, paths)))


CLAIMS = """<!-- BEGIN CLAIM OWNERS -->
| Claim ID | Class | Primary owner |
|---|---|---|
| runtime-baseline-identity | baseline | reports/runtime/baseline-register.json |
| public-api-contract | contract | docs/44-public-api-contract.md |
<!-- END CLAIM OWNERS -->"""
CLAIM_PATHS = {
    "reports/runtime/baseline-register.json",
    "docs/44-public-api-contract.md",
    "docs/SYSTEM_STATE.md",
    "docs/43-substrate-inventory-and-maturity.md",
    "docs/adr/ADR-001-uor-is-identity-not-memory.md",
    "reference/agentmem_ref/evaluation/integrations/golden-keyed-retrieval-v1.json",
    "reference/agentmem_ref/api/contract.py",
}
REQUIRED_ROWS = """| release-integration-status | delivery | #410 |
| benchmark-admission | qualification | reference/agentmem_ref/evaluation/integrations/ |"""


def with_row(row, text=CLAIMS):
    return text.replace("<!-- END CLAIM OWNERS -->", row + "\n<!-- END CLAIM OWNERS -->")


def claim_errors(text, heads=None, required=None):
    heads = heads or {}
    return module.validate_claim_owners(
        text, CLAIM_PATHS, lambda path: heads.get(path, ""), {} if required is None else required
    )


def has(errors, fragment):
    return any(fragment in error for error in errors)


class ClaimOwnershipTests(unittest.TestCase):
    def test_valid_claims(self):
        self.assertEqual(claim_errors(CLAIMS), [])
        self.assertEqual(claim_errors(with_row(REQUIRED_ROWS), required=module.REQUIRED_CLAIMS), [])

    def test_duplicate_claim_fails_closed(self):
        bad = with_row("| runtime-baseline-identity | baseline | docs/44-public-api-contract.md |")
        self.assertTrue(has(claim_errors(bad), "duplicate claim owner"))

    def test_untracked_owner_fails_closed(self):
        self.assertTrue(has(module.validate_claim_owners(CLAIMS, set(), lambda _: "", {}), "not tracked"))

    def test_unknown_authority_class_fails_closed(self):
        self.assertTrue(has(claim_errors(CLAIMS.replace("| baseline |", "| marketing |")), "unknown claim class"))

    def test_malformed_missing_and_disguised_rows_fail_closed(self):
        self.assertTrue(claim_errors("unrelated text"))
        self.assertTrue(has(claim_errors(CLAIMS.replace(" | contract | ", " | contract | https://untracked ")), "invalid"))
        for row in ("| Claim ID | delivery | docs/SYSTEM_STATE.md |", "|--- | delivery | docs/SYSTEM_STATE.md |"):
            self.assertTrue(has(claim_errors(with_row(row)), "invalid"), row)
        self.assertTrue(has(claim_errors(with_row("| public-api | contract | reference/agentmem_ref/api/contract.py |")), "Markdown/JSON"))

    def test_required_claims_are_pinned_to_ruled_owners(self):
        required = module.REQUIRED_CLAIMS
        self.assertTrue(has(claim_errors(CLAIMS, required=required), "release-integration-status: required claim declaration missing"))
        for wrong in ("| release-integration-status | delivery | #1 |", "| release-integration-status | evidence | reports/runtime/baseline-register.json |"):
            text = with_row(REQUIRED_ROWS.replace("| release-integration-status | delivery | #410 |", wrong))
            self.assertTrue(has(claim_errors(text, required=required), "must be declared as delivery owned by #410"), wrong)

    def test_delivery_and_issue_owner_pairing(self):
        self.assertTrue(has(claim_errors(with_row("| release-integration-status | delivery | docs/SYSTEM_STATE.md |")), "governing issue"))
        self.assertTrue(has(claim_errors(with_row("| architectural-decision-status | doctrine | #410 |")), "only allowed for live delivery"))

    def test_collection_owner_requires_tracked_members(self):
        self.assertEqual(claim_errors(with_row("| architectural-decision-status | doctrine | docs/adr/ |")), [])
        self.assertTrue(has(claim_errors(with_row("| benchmark-admission | qualification | reference/missing/ |")), "no tracked files"))

    def test_navigation_history_and_projection_surfaces_are_never_owners(self):
        for owner in ("docs/SYSTEM_STATE.md", "docs/ARCHITECTURE_INDEX.md", "docs/plan-sprint4a-public-api-contract.md", "docs/programs/"):
            self.assertTrue(has(claim_errors(with_row(f"| x-claim | qualification | {owner} |")), "cannot own a claim"), owner)

    def test_self_demoted_owner_is_not_promoted(self):
        row = with_row("| canonical-substrate-maturity | qualification | docs/43-substrate-inventory-and-maturity.md |")
        owner = "docs/43-substrate-inventory-and-maturity.md"
        for head in (
            "# Old dashboard (historical snapshot)\n",
            "# T\n\nStatus: **HISTORICAL, revision-bound addendum**\n",
            "# T\n\n**Purpose:** concise revision bound projection.\n",
            "# T\n\n**Status:** deprecated; see ADR-099\n",
            "# T\n\n**Authority effect:** none\n",
        ):
            self.assertTrue(has(claim_errors(row, {owner: head}), "non-authoritative"), head)
        for head in (
            "# Inventory\n\nHistorical sprint plans explain prior decisions.\n",
            "# Contract\n\n**Status**: contract version `1.7.0`; the 1.2.0 field is superseded by bar\n",
            "# Inventory\n\n**Purpose:** one current answer; archived prototypes are listed below\n",
            "# Backlog\n\n## Superseded RC1 items\n\n```text\n# historical lanes\n```\n",
            "# Backlog\n\n```text\nStatus: historical lane example\n```\n",
        ):
            self.assertEqual(claim_errors(row, {owner: head}), [], head)

    def test_unreadable_owner_is_reported_not_crashed(self):
        def broken(_path):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        row = with_row("| canonical-substrate-maturity | qualification | docs/43-substrate-inventory-and-maturity.md |")
        self.assertTrue(has(module.validate_claim_owners(row, CLAIM_PATHS, broken, {}), "cannot read owner"))

    def test_reversed_markers_and_path_escape_fail_closed(self):
        reversed_markers = "<!-- END CLAIM OWNERS -->\n| x | contract | docs/44-public-api-contract.md |\n<!-- BEGIN CLAIM OWNERS -->"
        self.assertEqual(claim_errors(reversed_markers), ["claim owner end marker precedes start marker"])
        bad = with_row("| x-claim | contract | docs/../reports/runtime/baseline-register.json |")
        self.assertTrue(has(claim_errors(bad), "escapes repository"))

    @unittest.skipUnless(shutil.which("git"), "git required to inventory tracked files")
    def test_repository_catalog_validates_against_all_tracked_files(self):
        # Regression: owners outside docs/ were reported untracked when only docs/ was inventoried.
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
