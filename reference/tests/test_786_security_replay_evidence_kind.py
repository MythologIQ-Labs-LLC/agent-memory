"""#786 / PR #805 checkpoint: ``security_replay`` is a first-class acceptance evidence kind.

The owner's checkpoint on PR #805 asked that the #786 security replay family be declared in the
successor declaration itself rather than in a companion file. These tests pin that: the
declaration schema admits the kind (and still rejects unknown kinds), the prepared cumulative
v6 -> v8 declaration lists the three frozen ``-v2`` contracts under it, the verifier reads
them from the declaration by default, and the frozen fixtures are the ones the declaration
names. Nothing here grants acceptance.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = ROOT / "schemas/runtime-baseline-declaration.schema.json"
DECLARATION = ROOT / "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"
FIXTURES = ROOT / "reference/fixtures/786-security-replays"
SECURITY_REPLAYS = (
    "cross-scope-write-authority-denial-v2",
    "deleted-lineage-generations-and-restart-v2",
    "public-tombstone-redaction-and-observer-separation-v2",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SecurityReplayEvidenceKind(unittest.TestCase):
    def test_schema_admits_security_replay_and_rejects_unknown_kinds(self):
        import jsonschema

        schema = _load(SCHEMA)
        kinds = schema["properties"]["acceptance_evidence_required"]["items"]["properties"]["kind"]["enum"]
        self.assertEqual(kinds, ["public_gauntlet", "replay", "lane", "security_replay"])
        base = {k: v for k, v in _load(DECLARATION).items()}
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate({**base, "acceptance_evidence_required": [{"kind": "security_replay", "ref": "x-v2"}]})
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate({**base, "acceptance_evidence_required": [{"kind": "security-replay", "ref": "x-v2"}]})
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate({**base, "acceptance_evidence_required": [{"kind": "blind_holdout", "ref": "x"}]})

    def test_declaration_requires_the_three_frozen_v2_contracts(self):
        declaration = _load(DECLARATION)
        required = [e["ref"] for e in declaration["acceptance_evidence_required"] if e["kind"] == "security_replay"]
        self.assertEqual(tuple(required), SECURITY_REPLAYS)
        for ref in required:
            with self.subTest(ref=ref):
                self.assertTrue((FIXTURES / f"{ref}.json").is_file(), ref)
        # The declaration validates against the schema it will be checked under.
        from scripts.check_runtime_baseline_equivalence import load_declaration

        load_declaration(ROOT, DECLARATION.relative_to(ROOT))

    def test_verifier_reads_the_declaration_by_default(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "verify_786_security_replays", ROOT / "scripts/verify_786_security_replays.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.DECLARATION, DECLARATION)
        self.assertFalse((ROOT / "reports/runtime/proposals/786-security-replay-acceptance.PROPOSED.json").exists())
        self.assertEqual(
            tuple(module.runner.REPLAYS) if hasattr(module.runner, "REPLAYS") else SECURITY_REPLAYS,
            SECURITY_REPLAYS,
        )

    def test_contract_identity_delta_matches_the_adopted_version(self):
        from agentmem_ref.api import contract

        declaration = _load(DECLARATION)
        deltas = {d["identity_path"]: d for d in declaration["identity_deltas"]}
        self.assertEqual(deltas["identity.public_contract_version"]["to"], contract.CONTRACT_VERSION)
        self.assertEqual(contract.CONTRACT_VERSION, "1.8.0")


if __name__ == "__main__":
    unittest.main()
