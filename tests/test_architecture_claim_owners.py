"""Offline negative/positive fixtures for the architecture claim-owner table."""
import importlib.util
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
PATHS = {"reports/runtime/baseline-register.json", "docs/44-public-api-contract.md"}


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


if __name__ == "__main__":
    unittest.main()
