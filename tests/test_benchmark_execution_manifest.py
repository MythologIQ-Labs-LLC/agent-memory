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


ACCEPTED_DIR = ROOT / "reference/fixtures/benchmarks/execution-manifest-accepted"
ACCEPTED = json.loads((ACCEPTED_DIR / "manifest.json").read_text())
AUTHORITY = json.loads((ACCEPTED_DIR / "review-authority.json").read_text())


def digest(authority) -> str:
    """Stands in for the digest the owner publishes for the record under test."""
    import hashlib
    return hashlib.sha256(json.dumps(authority, sort_keys=True).encode()).hexdigest()


class AcceptanceGuardTests(unittest.TestCase):
    """#808 items 3-4: a verified synthetic acceptance, and every way to forge or weaken it."""

    def accept(self, manifest=None, authority=AUTHORITY, root=ROOT, normalized=None):
        validator.validate(copy.deepcopy(manifest or ACCEPTED), normalized, evidence_root=root, authority=copy.deepcopy(authority),
                           authority_sha256=digest(authority), expected_authority_sha256=digest(authority))

    def refuse(self, change, message, authority_change=None, root=ROOT):
        value, authority = copy.deepcopy(ACCEPTED), copy.deepcopy(AUTHORITY)
        change(value)
        if authority_change:
            authority_change(authority)
        with self.assertRaisesRegex(Exception, message):
            validator.validate(value, evidence_root=root, authority=authority,
                               authority_sha256=digest(authority), expected_authority_sha256=digest(authority))

    def test_verified_synthetic_acceptance_passes(self):
        self.accept()

    def test_accepted_fixture_normalized_run_is_schema_valid(self):
        import jsonschema
        schema = json.loads((ROOT / "schemas/memory-benchmark-run.schema.json").read_text())
        normalized = json.loads((ACCEPTED_DIR / "normalized.json").read_text())
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(normalized)
        pointer = [a for a in normalized["artifacts"] if a["kind"] == "execution_manifest"]
        self.assertEqual([a["uri"] for a in pointer], [str((ACCEPTED_DIR / "manifest.json").relative_to(ROOT))])

    def test_self_declared_reviewer_without_authority_is_refused(self):
        with self.assertRaisesRegex(Exception, "claim, not a decision"):
            validator.validate(copy.deepcopy(ACCEPTED), evidence_root=ROOT, authority=None)

    def test_authority_for_other_reviewer_or_run_is_refused(self):
        self.refuse(lambda x: x["review"].update(reviewer="someone-else"), "different reviewer")
        self.refuse(lambda x: None, "different run_id", lambda a: a["decisions"][0].update(run_id="other"))
        self.refuse(lambda x: None, "different normalized run", lambda a: a["decisions"][0].update(normalized_sha256="0" * 64))
        self.refuse(lambda x: None, "not accepted", lambda a: a["decisions"][0].update(decision="rejected"))
        self.refuse(lambda x: x["review"].update(decision_ref="https://example.invalid/unknown"), "no unique decision")
        self.refuse(lambda x: x["review"].update(decision_ref="see chat"), "stable https")

    def test_authority_must_match_owner_published_digest(self):
        for expected in (None, "0" * 64):
            with self.subTest(expected=expected), self.assertRaisesRegex(Exception, "owner-published digest"):
                validator.validate(copy.deepcopy(ACCEPTED), evidence_root=ROOT, authority=copy.deepcopy(AUTHORITY),
                                   authority_sha256=digest(AUTHORITY), expected_authority_sha256=expected)

    def test_cli_binds_authority_file_digest(self):
        import hashlib
        import subprocess
        import sys
        file_digest = hashlib.sha256((ACCEPTED_DIR / "review-authority.json").read_bytes()).hexdigest()
        base = [sys.executable, str(ROOT / "scripts/validate_benchmark_execution_manifest.py"), str(ACCEPTED_DIR / "manifest.json"),
                "--evidence-root", str(ROOT), "--review-authority", str(ACCEPTED_DIR / "review-authority.json")]
        self.assertEqual(subprocess.run(base + ["--review-authority-sha256", file_digest], capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(base, capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(base + ["--review-authority-sha256", "0" * 64], capture_output=True).returncode, 1)

    def test_malformed_authority_is_refused_not_crashed(self):
        for authority in ([], {"decisions": ["x"]}, {"decisions": "x"}, {}):
            with self.subTest(authority=authority), self.assertRaisesRegex(ValueError, "list of decision objects"):
                validator.validate(copy.deepcopy(ACCEPTED), evidence_root=ROOT, authority=authority,
                                   authority_sha256=digest(authority), expected_authority_sha256=digest(authority))

    def test_bare_or_hostless_decision_ref(self):
        for ref in ("https://", "https:///x", "https://example"):
            with self.subTest(ref=ref):
                self.refuse(lambda x, ref=ref: x["review"].update(decision_ref=ref), "stable https",
                            lambda a, ref=ref: a["decisions"][0].update(decision_ref=ref))

    def test_reviewer_must_differ_from_executor(self):
        self.refuse(lambda x: None, "independent of the executor",
                    lambda a: a["decisions"][0].update(executor=a["decisions"][0]["reviewer"]))
        self.refuse(lambda x: None, "independent of the executor", lambda a: a["decisions"][0].pop("executor"))
        for executor in ("SYNTHETIC-INDEPENDENT-REVIEWER", "synthetic-independent-reviewer ", " synthetic-independent-reviewer",
                         1, ["x"], {"name": "x"}, ""):
            with self.subTest(executor=executor):
                self.refuse(lambda x: None, "independent of the executor",
                            lambda a, e=executor: a["decisions"][0].update(executor=e))

    def test_normalized_identity_dict_alone_cannot_accept(self):
        normalized = json.loads((ACCEPTED_DIR / "normalized.json").read_text())
        with self.assertRaisesRegex(Exception, "re-hashed"):
            validator.validate(copy.deepcopy(ACCEPTED), normalized, authority=copy.deepcopy(AUTHORITY))

    def test_forged_or_missing_normalized_hash(self):
        self.refuse(lambda x: x["normalized_run"].update(sha256="0" * 64), "SHA-256 mismatch for normalized_run")
        self.refuse(lambda x: x["normalized_run"].update(uri="reference/fixtures/benchmarks/absent.json"), "missing evidence file")

    def test_forged_or_missing_artifact(self):
        self.refuse(lambda x: x["artifacts"][1].update(sha256="0" * 64), "SHA-256 mismatch for row_level_results")
        self.refuse(lambda x: x["artifacts"][1].update(uri="reference/fixtures/benchmarks/absent.jsonl"), "missing evidence file")

    def test_missing_row_level_artifact(self):
        self.refuse(lambda x: x["artifacts"].pop(1), "native and per-row artifacts")

    def test_supplied_normalized_must_equal_hashed_file(self):
        normalized = json.loads((ACCEPTED_DIR / "normalized.json").read_text())
        normalized["execution"]["sample_count"] = 11
        with self.assertRaisesRegex(Exception, "differs from the hashed file"):
            self.accept(normalized=normalized)

    def test_identity_mismatches_against_hashed_normalized_run(self):
        for field, change in (
            ("system.revision", lambda x: x["system"].update(revision="f" * 40)),
            ("benchmark.input_sha256", lambda x: x["benchmark"].update(input_sha256="c" * 64)),
            ("execution.sample_count", lambda x: x["benchmark"].update(sample_count=9)),
            ("execution.selection_id", lambda x: x["benchmark"].update(selection_id="other")),
        ):
            with self.subTest(field=field):
                value = copy.deepcopy(ACCEPTED)
                value["review"].update(status="candidate", comparison_eligibility="not_assessed")
                change(value)
                with self.assertRaisesRegex(Exception, f"disagrees on {field}"):
                    validator.validate(value, evidence_root=ROOT)

    def test_paid_hosted_inference_declared_without_cost(self):
        hosted = {"purpose": "generation", "provider": "example-provider", "model_id": "model-x",
                  "model_revision": "2026-01-01", "model_digest": None, "endpoint_class": "hosted",
                  "parameters": {"temperature": 0, "top_p": 1, "seed": 1, "context_window_tokens": 8192,
                                 "max_output_tokens": 256}, "prompt_sha256": "d" * 64, "count": 3}
        for status in ("candidate", "accepted"):
            with self.subTest(status=status):
                self.refuse(lambda x: (x["inference"].update(used=True, calls=[dict(hosted)]),
                                       x["review"].update(status=status, comparison_eligibility="not_assessed")),
                            "never not_applicable")

    def test_unpinned_model_version_blocks_acceptance_only(self):
        local = {"purpose": "embedding", "provider": "local", "model_id": "embedder", "model_revision": "latest",
                 "model_digest": None, "endpoint_class": "local", "parameters": {"dimensions": 8},
                 "prompt_sha256": None, "count": 1}
        self.refuse(lambda x: x["inference"].update(used=True, calls=[dict(local)]), "floating alias")
        candidate = copy.deepcopy(EXAMPLE)
        candidate["inference"].update(used=True, calls=[dict(local)])
        validator.validate(candidate)

    def test_unreconciled_wall_time(self):
        self.refuse(lambda x: x["timing"].update(elapsed_ms=600000), "inconsistent with elapsed_ms")

    def test_non_rfc3339_timestamps(self):
        for bad in ("20261014T120000Z", "2026-10-14 12:00:00Z", "2026-10-14T12:00:00+00:00Z"):
            with self.subTest(timestamp=bad):
                self.refuse(lambda x, bad=bad: x["timing"].update(started_at=bad), "started_at|RFC 3339")
        self.refuse(lambda x: x["timing"].update(started_at="2026-10-14T25:00:00Z"), "hour|RFC 3339")

    def test_redaction_not_reviewed(self):
        self.refuse(lambda x: x["redaction"].update(reviewed=False), "redaction review")

    def test_secrets_in_argv(self):
        for arg in ("--token=abc", "--hf-token", "OPENAI_API_KEY=abc", "sk-ABCDEFGHIJKLMNOPQRSTUV",
                    "Authorization: Bearer abc.def", "ghp_" + "a" * 36, "AKIA" + "A" * 16):
            with self.subTest(arg=arg):
                self.refuse(lambda x, arg=arg: x["execution"]["argv_redacted"].append(arg), "credential")

    def test_credentials_embedded_in_longer_arguments(self):
        # Each of these was refused by the first checker revision and must stay refused.
        for arg in ("sh -c 'run --api-key=abc123'", "x --auth-token abc", "--secret-key=abc", "--password1=x",
                    "--api_key:abc", "--api-key-file=/x", "--openai-api-key=abc", "env OPENAI_API_KEY=abc run"):
            with self.subTest(arg=arg):
                self.refuse(lambda x, arg=arg: x["execution"]["argv_redacted"].append(arg), "credential")

    def test_credential_like_parameter_keys(self):
        for key in ("api_key_tokens", "access_tokens", "secret_tokens", "token", "api_key"):
            call = {"purpose": "embedding", "provider": "local", "model_id": "e", "model_revision": "r1",
                    "model_digest": None, "endpoint_class": "local", "parameters": {key: "abc"},
                    "prompt_sha256": None, "count": 1}
            with self.subTest(key=key):
                self.refuse(lambda x, call=call: x["inference"].update(used=True, calls=[call]), "credential fields")

    def test_compressed_normalized_run_is_a_clear_refusal(self):
        import gzip
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "reference/fixtures/benchmarks/execution-manifest-accepted"
            target.mkdir(parents=True)
            for name in ("native.json", "rows.jsonl"):
                (target / name).write_bytes((ACCEPTED_DIR / name).read_bytes())
            packed = gzip.compress((ACCEPTED_DIR / "normalized.json").read_bytes(), mtime=0)
            (target / "normalized.json").write_bytes(packed)
            value = copy.deepcopy(ACCEPTED)
            value["review"].update(status="candidate", comparison_eligibility="not_assessed")
            import hashlib
            value["normalized_run"]["sha256"] = hashlib.sha256(packed).hexdigest()
            with self.assertRaisesRegex(ValueError, "not a JSON memory-benchmark-run"):
                validator.validate(value, evidence_root=root)

    def test_benign_token_counts_are_not_secrets(self):
        value = copy.deepcopy(EXAMPLE)
        value["execution"]["argv_redacted"] += ["--max-tokens", "256", "max_tokens=256", "--retrieval-top-k"]
        validator.validate(value)

    def test_secrets_in_artifact_pointers_and_parameters(self):
        self.refuse(lambda x: x["artifacts"][0].update(uri="reports/run.json?token=abc"), "credential|unsafe")
        self.refuse(lambda x: x["artifacts"][0].update(uri="reports/sk-ABCDEFGHIJKLMNOPQRSTUV.json"), "credential")
        call = {"purpose": "embedding", "provider": "local", "model_id": "e", "model_revision": "r1",
                "model_digest": None, "endpoint_class": "local", "parameters": {"note": "Bearer abc"},
                "prompt_sha256": None, "count": 1}
        self.refuse(lambda x: x["inference"].update(used=True, calls=[call]), "credential values")

    def test_duplicate_artifact_ids(self):
        self.refuse(lambda x: x["artifacts"].append(dict(x["artifacts"][0])), "duplicate evidence")
        self.refuse(lambda x: x["artifacts"].append(dict(x["artifacts"][0], kind="other")), "same path")

    def test_malicious_relative_evidence_paths(self):
        for uri in ("../outside.json", "/etc/passwd", "a/../../b.json", "a//b.json", "a\\..\\b.json",
                    "C:/x.json", "~/x.json", "a/%2e%2e/b.json", "file:///etc/passwd", "a/./b.json", "", "a\x00b",
                    "a\x7fb.json", "a\u2028b.json"):
            with self.subTest(uri=uri):
                self.refuse(lambda x, uri=uri: x["artifacts"][0].update(uri=uri), "unsafe evidence pointer|credential|non-empty")

    def test_symlink_escape_is_refused(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            target = root / "reference/fixtures/benchmarks/execution-manifest-accepted"
            target.mkdir(parents=True)
            for name in ("normalized.json", "rows.jsonl"):
                (target / name).write_bytes((ACCEPTED_DIR / name).read_bytes())
            outside = Path(tmp) / "native.json"
            outside.write_bytes((ACCEPTED_DIR / "native.json").read_bytes())
            os.symlink(outside, target / "native.json")
            with self.assertRaisesRegex(Exception, "escapes the evidence root"):
                self.accept(root=root)


class CatalogAssociationTests(unittest.TestCase):
    """#808 item 5: an opt-in execution-manifest pointer is inspectable provenance, never score authority."""

    def test_ui_catalog_projects_manifest_pointer_without_changing_metrics(self):
        import sys
        sys.path.insert(0, str(ROOT / "reference"))
        from agentmem_ref.evaluation import ui_catalog
        normalized = json.loads((ACCEPTED_DIR / "normalized.json").read_text())
        without = copy.deepcopy(normalized)
        without["artifacts"] = [a for a in without["artifacts"] if a["kind"] != "execution_manifest"]
        path = "reference/fixtures/benchmarks/execution-manifest-accepted/normalized.json"
        projected, baseline = ui_catalog._run_projection(path, normalized), ui_catalog._run_projection(path, without)
        pointer = [e for e in projected["evidence"] if e.get("artifact_id") == "execution-manifest"]
        self.assertEqual(len(pointer), 1)
        self.assertNotIn("sha256", pointer[0])  # the manifest binds the run's digest, so the reverse pointer cannot
        self.assertEqual(projected["metrics"], baseline["metrics"])
        self.assertEqual(projected["status"], baseline["status"])
        self.assertEqual(projected["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
