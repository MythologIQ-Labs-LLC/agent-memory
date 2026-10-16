"""Offline negative/positive fixtures for the architecture claim-owner table."""
import importlib.util
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_architecture_index.py"
spec = importlib.util.spec_from_file_location("validate_architecture_index", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

GOOD = """<!-- BEGIN CLAIM OWNERS -->
| Claim ID | Class | Primary owner |
|---|---|---|
| runtime-baseline-identity | baseline | reports/runtime/baseline-register.json |
| public-api-contract | contract | docs/44-public-api-contract.md |
<!-- END CLAIM OWNERS -->"""
PATHS = {
    "reports/runtime/baseline-register.json",
    "docs/44-public-api-contract.md",
    "docs/SYSTEM_STATE.md",
    "docs/adr/ADR-001-uor-is-identity-not-memory.md",
}


def with_row(row):
    return GOOD.replace("<!-- END CLAIM OWNERS -->", row + "\n<!-- END CLAIM OWNERS -->")


def errors(text, heads=None):
    return module.validate_claim_owners(text, PATHS, heads)


class ClaimOwnershipTests(unittest.TestCase):
    def test_valid_claims(self):
        self.assertEqual(module.validate_claim_owners(GOOD, PATHS), [])

    def test_duplicate_claim_fails_closed(self):
        bad = GOOD.replace(
            "<!-- END CLAIM OWNERS -->",
            "| runtime-baseline-identity | baseline | docs/44-public-api-contract.md |\n<!-- END CLAIM OWNERS -->",
        )
        self.assertTrue(any("duplicate claim owner" in error for error in module.validate_claim_owners(bad, PATHS)))

    def test_unknown_owner_fails_closed(self):
        self.assertTrue(any("not tracked" in error for error in module.validate_claim_owners(GOOD, set())))

    def test_unknown_authority_class_fails_closed(self):
        bad = GOOD.replace("| baseline |", "| marketing |")
        self.assertTrue(any("unknown claim class" in error for error in module.validate_claim_owners(bad, PATHS)))

    def test_malformed_and_missing_section_fail_closed(self):
        self.assertTrue(module.validate_claim_owners("unrelated text", PATHS))
        bad = GOOD.replace(" | contract | ", " | contract | https://untracked ")
        self.assertTrue(any("invalid" in error for error in module.validate_claim_owners(bad, PATHS)))

    def test_live_delivery_claim_names_governing_issue(self):
        self.assertEqual(errors(with_row("| release-integration-status | delivery | #410 |")), [])

    def test_delivery_claim_owned_by_document_fails_closed(self):
        bad = with_row("| release-integration-status | delivery | docs/SYSTEM_STATE.md |")
        self.assertTrue(any("governing issue" in error for error in errors(bad)))

    def test_issue_owner_outside_delivery_fails_closed(self):
        bad = with_row("| architectural-decision-status | doctrine | #410 |")
        self.assertTrue(any("only allowed for live delivery" in error for error in errors(bad)))

    def test_collection_owner_requires_tracked_members(self):
        self.assertEqual(errors(with_row("| architectural-decision-status | doctrine | docs/adr/ |")), [])
        bad = with_row("| benchmark-admission | qualification | reference/missing/ |")
        self.assertTrue(any("no tracked files" in error for error in errors(bad)))

    def test_revision_bound_or_historical_owner_is_not_promoted(self):
        row = with_row("| canonical-substrate-maturity | qualification | docs/SYSTEM_STATE.md |")
        for head in (
            "# State\n\n**Purpose:** concise revision-bound projection.\n",
            "# Old dashboard (historical snapshot)\n",
            "Status: **HISTORICAL, revision-bound addendum**\n",
        ):
            found = errors(row, {"docs/SYSTEM_STATE.md": head})
            self.assertTrue(any("historical or revision-bound" in error for error in found), head)
        current = {"docs/SYSTEM_STATE.md": "# Inventory\n\nHistorical sprint plans explain prior decisions.\n"}
        self.assertEqual(errors(row, current), [])

    def test_reversed_markers_and_path_escape_fail_closed(self):
        reversed_markers = "<!-- END CLAIM OWNERS -->\n| x | contract | docs/44-public-api-contract.md |\n<!-- BEGIN CLAIM OWNERS -->"
        self.assertEqual(errors(reversed_markers), ["claim owner end marker precedes start marker"])
        bad = with_row("| public-api-contract | contract | docs/../reports/runtime/baseline-register.json |")
        self.assertTrue(any("escapes repository" in error for error in errors(bad)))

    @unittest.skipUnless(shutil.which("git"), "git required to inventory tracked files")
    def test_repository_catalog_validates_against_all_tracked_files(self):
        # Regression: owners outside docs/ were reported untracked when only docs/ was inventoried.
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
