"""#572: bounded built-in recall-decision validation without weaker guarantees."""

from __future__ import annotations

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from agentmem_ref.core import receipts


SCHEMA = "contextual-recall-admission.schema.json"


def _decision() -> dict:
    return {
        "schema_version": "1.0.0",
        "profile_version": "0.1.0",
        "decision_id": "ref-1",
        "candidate_ref": "fact-1",
        "policy": {
            "policy_ref": "contextual-recall-policy:none",
            "policy_version": "1.0.0",
            "status": "unavailable",
            "selection_mode": "deterministic",
        },
        "context": {
            "target_domain_refs": ["tenant-a", "domain-b"],
            "principal_ref": "agent:a",
            "project_ref": "project:a",
            "task_ref": "task:a",
            "purpose": "recall",
            "destination_ref": "",
        },
        "outcome": "admit",
        "reason_code": "builtin_admission",
        "evidence_refs": [],
        "evaluated_at": "2026-01-01T00:00:01Z",
        "interpretation": {
            "authority_effect": "current_recall_only",
            "prior_admission_authority": "none",
            "memory_mutation": "not_performed",
            "relevance_authority": "none",
            "risk_signal_authority": "none",
        },
    }


class BuiltinRecallValidationFastPathTest(TestCase):
    def test_fastpath_is_bound_to_current_schema_blob(self):
        self.assertTrue(receipts._builtin_recall_fastpath_enabled())

    def test_valid_builtin_decision_matches_canonical_oracle(self):
        document = _decision()
        receipts._validate_with_jsonschema(SCHEMA, document)
        receipts.validate(SCHEMA, document)

    def test_builtin_fastpath_does_not_call_jsonschema(self):
        with patch.object(
            receipts,
            "_validate_with_jsonschema",
            wraps=receipts._validate_with_jsonschema,
        ) as canonical:
            receipts.validate(SCHEMA, _decision())
        canonical.assert_not_called()

    def test_schema_identity_mismatch_falls_back_to_canonical_validator(self):
        with patch.object(receipts, "_builtin_recall_fastpath_enabled", return_value=False):
            with patch.object(
                receipts,
                "_validate_with_jsonschema",
                wraps=receipts._validate_with_jsonschema,
            ) as canonical:
                receipts.validate(SCHEMA, _decision())
        canonical.assert_called_once()

    def test_contextual_policy_decision_stays_on_canonical_validator(self):
        document = _decision()
        document["policy"]["policy_ref"] = "contextual-recall-policy:test"
        document["policy"]["status"] = "evaluated"
        with patch.object(
            receipts,
            "_validate_with_jsonschema",
            wraps=receipts._validate_with_jsonschema,
        ) as canonical:
            receipts.validate(SCHEMA, document)
        canonical.assert_called_once()

    def test_optional_risk_evidence_stays_on_canonical_validator(self):
        document = _decision()
        document["risk_evidence"] = {
            "signal_ref": "signal:1",
            "signal_semantics": "advisory",
            "estimator_ref": "estimator:1",
            "estimator_version": "1.0.0",
        }
        with patch.object(
            receipts,
            "_validate_with_jsonschema",
            wraps=receipts._validate_with_jsonschema,
        ) as canonical:
            receipts.validate(SCHEMA, document)
        canonical.assert_called_once()

    def test_malformed_builtin_mutants_fail_fast_and_match_oracle(self):
        mutants = []

        missing = _decision()
        del missing["candidate_ref"]
        mutants.append(missing)

        extra = _decision()
        extra["unexpected"] = True
        mutants.append(extra)

        empty_id = _decision()
        empty_id["decision_id"] = ""
        mutants.append(empty_id)

        empty_candidate = _decision()
        empty_candidate["candidate_ref"] = ""
        mutants.append(empty_candidate)

        duplicate_domain = _decision()
        duplicate_domain["context"]["target_domain_refs"] = ["tenant-a", "tenant-a"]
        mutants.append(duplicate_domain)

        bad_domain = _decision()
        bad_domain["context"]["target_domain_refs"] = [""]
        mutants.append(bad_domain)

        non_string_context = _decision()
        non_string_context["context"]["project_ref"] = 7
        mutants.append(non_string_context)

        bad_status = _decision()
        bad_status["policy"]["status"] = "trusted"
        mutants.append(bad_status)

        bad_selection = _decision()
        bad_selection["policy"]["selection_mode"] = "probabilistic"
        mutants.append(bad_selection)

        bad_outcome = _decision()
        bad_outcome["outcome"] = "allow"
        mutants.append(bad_outcome)

        empty_reason = _decision()
        empty_reason["reason_code"] = ""
        mutants.append(empty_reason)

        duplicate_evidence = _decision()
        duplicate_evidence["evidence_refs"] = ["e:1", "e:1"]
        mutants.append(duplicate_evidence)

        bad_interpretation = _decision()
        bad_interpretation["interpretation"]["relevance_authority"] = "ranking"
        mutants.append(bad_interpretation)

        for document in mutants:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    receipts._validate_with_jsonschema(SCHEMA, deepcopy(document))
                with self.assertRaises(ValueError):
                    receipts.validate(SCHEMA, deepcopy(document))

    def test_fastpath_accepts_schema_valid_enum_and_evidence_variants(self):
        """The optimized path must preserve schema semantics, not only today's builder literals."""
        for outcome in (
            "admit",
            "admit_with_warning",
            "require_verification",
            "require_review",
            "quarantine",
            "block",
        ):
            document = _decision()
            document["outcome"] = outcome
            document["evidence_refs"] = ["e:1", "e:2"]
            receipts._validate_with_jsonschema(SCHEMA, document)
            receipts.validate(SCHEMA, document)


if __name__ == "__main__":
    import unittest

    unittest.main()
