from __future__ import annotations

import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_json_v2_candidate import (  # noqa: E402
    CanonicalJsonV2Error,
    canonical_bytes_v2,
    canonicalize_json_text_v2,
)

FIXTURE = ROOT / "fixtures" / "runtime" / "canonical-json-v2-vectors-v1.json"
ACCEPTANCE = ROOT / "fixtures" / "runtime" / "canonical-json-v2-vectors-accepted-v1.json"


def _string_from_codepoints(items: list[str]) -> str:
    return "".join(chr(int(item, 16)) for item in items)


def _binary64(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def _valid_input(spec: dict) -> object:
    kind = spec["kind"]
    if kind == "null":
        return None
    if kind == "bool":
        return bool(spec["value"])
    if kind == "string":
        return spec["value"]
    if kind == "string_codepoints":
        return _string_from_codepoints(spec["hex"])
    if kind == "int":
        return int(spec["decimal"])
    if kind == "binary64_bits":
        return _binary64(spec["hex"])
    if kind == "json_value":
        return spec["value"]
    if kind == "object_entries":
        return {key: value for key, value in spec["entries"]}
    raise AssertionError(f"unexpected valid fixture input kind: {kind}")


def _run_case(case: dict) -> bytes:
    spec = case["input"]
    kind = spec["kind"]
    if kind == "json_text":
        return canonicalize_json_text_v2(spec["text"])
    if kind == "object_entries_typed":
        entries = []
        for raw_key, value in spec["entries"]:
            if raw_key["kind"] == "int":
                key = int(raw_key["decimal"])
            else:
                raise AssertionError(f"unexpected typed key fixture: {raw_key}")
            entries.append((key, value))
        return canonical_bytes_v2(dict(entries))
    return canonical_bytes_v2(_valid_input(spec))


class CanonicalJsonV2CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))

    def test_candidate_uses_the_accepted_vector_source_without_rewriting_it(self):
        self.assertEqual(self.acceptance["status"], "ACCEPTED_IMPLEMENTATION_VECTOR_SOURCE")
        self.assertEqual(
            self.acceptance["source_fixture"],
            "reference/fixtures/runtime/canonical-json-v2-vectors-v1.json",
        )
        self.assertEqual(self.acceptance["source_fixture_id"], self.fixture["fixture_id"])
        self.assertEqual(self.acceptance["case_count"], len(self.fixture["cases"]))
        self.assertEqual(len(self.fixture["cases"]), 44)
        self.assertIn("ADR-040 architecture decision", self.acceptance["scope"]["not_accepted"])

    def test_python_candidate_matches_every_accepted_vector(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                if "expected_utf8" in case:
                    self.assertEqual(_run_case(case), case["expected_utf8"].encode("utf-8"))
                    continue

                with self.assertRaises(CanonicalJsonV2Error) as caught:
                    _run_case(case)
                self.assertEqual(caught.exception.reason, case["expected_refusal"])

    def test_profile_keeps_integer_float_and_signed_zero_identity_distinct(self):
        self.assertEqual(canonical_bytes_v2(1), b"1")
        self.assertEqual(canonical_bytes_v2(1.0), b"1.0")
        self.assertEqual(canonical_bytes_v2(0.0), b"0.0")
        self.assertEqual(canonical_bytes_v2(-0.0), b"-0.0")


if __name__ == "__main__":
    unittest.main()
