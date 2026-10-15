"""Synthetic/offline contract tests for benchmark execution envelope."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manifest_validator", ROOT / "scripts/validate_benchmark_execution_manifest.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
EXAMPLE = json.loads((ROOT / "reference/fixtures/benchmarks/benchmark-execution-manifest-example.json").read_text())


class ManifestTests(unittest.TestCase):
    def test_candidate_passes(self):
        validator.validate(copy.deepcopy(EXAMPLE))

    def reject(self, change, message):
        value = copy.deepcopy(EXAMPLE)
        change(value)
        with self.assertRaisesRegex(Exception, message):
            validator.validate(value)

    def test_time_reversal(self):
        self.reject(lambda x: x["timing"].update(finished_at="2026-10-14T11:00:00Z"), "earlier")

    def test_hardware_required(self):
        self.reject(lambda x: x["hardware"].pop("cpu_model"), "cpu_model")

    def test_false_inference_claim(self):
        self.reject(lambda x: x["inference"].update(used=True), "inference.used")

    def test_unknown_cost_not_zero(self):
        value = copy.deepcopy(EXAMPLE)
        value["costs"].update(status="not_measured", amount=None, input_tokens=None, output_tokens=None)
        validator.validate(value)
        value["costs"]["amount"] = 0
        with self.assertRaisesRegex(Exception, "cost status"):
            validator.validate(value)

    def test_acceptance_requires_reviewer(self):
        self.reject(lambda x: x["review"].update(status="accepted"), "reviewer")

    def test_eligible_must_be_accepted(self):
        self.reject(lambda x: x["review"].update(comparison_eligibility="eligible_on_profile"), "comparison eligibility")

    def test_acceptance_requires_redaction_review(self):
        value = copy.deepcopy(EXAMPLE)
        value["review"].update(status="accepted", reviewer="independent", decision_ref="https://github.com/example/review")
        with self.assertRaisesRegex(Exception, "redaction review"):
            validator.validate(value)

    def test_no_unsafe_relative_evidence_path(self):
        self.reject(lambda x: x["artifacts"][0].update(uri="../private/secret"), "unsafe evidence")

    def test_duplicate_artifact_path(self):
        self.reject(lambda x: x["artifacts"].append(copy.deepcopy(x["artifacts"][0])), "duplicate evidence")

    def test_command_credential_guard(self):
        self.reject(lambda x: x["execution"]["argv_redacted"].append("--api-key=unsafe"), "credential")

    def test_accepted_hosted_model_requires_cost(self):
        value = copy.deepcopy(EXAMPLE)
        value["review"].update(status="accepted", reviewer="independent", decision_ref="https://github.com/example/review")
        value["redaction"]["reviewed"] = True
        value["inference"].update(used=True, calls=[{
            "purpose": "generation", "provider": "example-provider", "model_id": "model-x",
            "model_revision": "model-version-one", "model_digest": None, "endpoint_class": "hosted",
            "parameters": {"temperature": 0, "top_p": 1, "seed": 42,
                           "context_window_tokens": 2048, "max_output_tokens": 200},
            "prompt_sha256": "b" * 64, "count": 1
        }])
        with self.assertRaisesRegex(Exception, "hosted inference requires a measured cost"):
            validator.validate(value)

    def test_accepted_generation_requires_prompt_digest(self):
        value = copy.deepcopy(EXAMPLE)
        value["review"].update(status="accepted", reviewer="independent", decision_ref="https://github.com/example/review")
        value["redaction"]["reviewed"] = True
        value["inference"].update(used=True, calls=[{
            "purpose": "generation", "provider": "local", "model_id": "model-x",
            "model_revision": "pinned", "model_digest": None, "endpoint_class": "local",
            "parameters": {"temperature": 0, "top_p": 1, "seed": 42,
                           "context_window_tokens": 2048, "max_output_tokens": 200},
            "prompt_sha256": None, "count": 1
        }])
        with self.assertRaisesRegex(Exception, "prompt digest"):
            validator.validate(value)

    def test_normalized_run_identity(self):
        value = copy.deepcopy(EXAMPLE)
        normalized = {
            "run_id": value["run_id"], "system": {"id": value["system"]["id"], "revision": value["system"]["revision"]},
            "benchmark": {"id": value["benchmark"]["id"], "task_profile": value["benchmark"]["task_profile"],
                          "input_sha256": value["benchmark"]["input_sha256"]},
            "execution": {"selection_id": value["benchmark"]["selection_id"], "sample_count": value["benchmark"]["sample_count"]},
        }
        validator.validate(value, normalized)
        normalized["execution"]["sample_count"] = 99
        with self.assertRaisesRegex(Exception, "sample_count"):
            validator.validate(value, normalized)


if __name__ == "__main__":
    unittest.main()
