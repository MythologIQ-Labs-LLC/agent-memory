"""#580: the repository-owned temporal/currentness qualification gauntlet.

These tests check the evaluator, not Agent Memory's score:

* the gold corpus is frozen (digest-bound) and covers every #580 item;
* the evaluator fails closed on malformed fixtures;
* the scorer is sensitive: corrupting real observations moves the metric that should
  catch the corruption (scorer-level negative controls);
* evaluation-process runtime mutants are detected (runtime-level negative controls);
* the frozen pre-#550 baseline remains immutable and acts as a monotonic comparator:
  live behavior may resolve a frozen failure/honest-unknown, but a frozen required pass
  may not regress and unrelated case behavior may not drift;
* no runtime module references the gauntlet (no benchmark-specific branch).
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation import temporal_currentness as tc  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"
FIXTURE_SHA256 = "394be82e8dfabe30ad1faf064f36a88d0b0b8e7ab8157f746ecb4cbae9e64492"
BASELINE = ROOT / "reports" / "benchmarks" / "temporal-currentness" / "baseline-0bace49" / "baseline.json"
# Temporal interpreter 1.1.0 (#585) comparison contract.
#
# Only evidentiary/version fields are ignored. ``intent_basis`` is policy-significant
# (historical-evidence admission reads it), so it is compared; frozen 1.0.0 observations
# carry no basis and are normalized to the backward-compatible 1.0.0 derivation first.
INTERPRETER_EVIDENCE_FIELDS = frozenset({"interpreter_version", "evidence", "spans", "declined_spans"})
LEGACY_BASIS = {"explicit": "caller_declared", "inferred": "query_cue_inference", "unspecified": "none"}
# Every versioned 1.1.0 intent change is enumerated: (field, frozen value, live value).
QUERY_LANGUAGE_EXPLICIT_FROM_HIGH = frozenset({
    ("posture", "inferred", "explicit"), ("confidence", "high", None),
    ("intent_basis", "query_cue_inference", "query_language_explicit"),
})
QUERY_LANGUAGE_EXPLICIT_FROM_LOW = frozenset({
    ("posture", "inferred", "explicit"), ("confidence", "low", None),
    ("intent_basis", "query_cue_inference", "query_language_explicit"), ("orders_temporally", False, True),
})
VERSIONED_INTENT_TRANSITIONS = {
    **{probe: QUERY_LANGUAGE_EXPLICIT_FROM_HIGH for probe in (
        "A1-expired-exact-vs-current-weaker/current-inferred",
        "A2-not-yet-valid-exact-vs-current/current-inferred",
        "A3-two-valid-relevance-decides/current-inferred",
        "A4-current-query-no-temporal-basis/current-inferred",
        "B6-state-change-chain/current-inferred",
        "B8-error-correction-never-historical/current-inferred",
        "C11-C12-prospective-commitment/current-after-effective",
        "C11-C12-prospective-commitment/current-reverses",
        "D17-transaction-order-disagrees-with-valid-time/current-inferred",
        "D18-observation-time-disagrees-with-valid-time/current-inferred",
        "D18-observation-time-disagrees-with-valid-time/observation-only-is-not-validity",
        "E19-E20-reinforced-expired-vs-decayed-valid/current-inferred",
        "E21-old-but-still-valid/current-inferred",
        "E22-decay-affects-accessibility-only-under-policy/current-inferred",
        "F23-has-moved-now-lives/current-inferred",
        "F24-no-longer-works-at/current-inferred",
        "F25-also-works-at-cardinality-control/current-inferred",
        "F26-for-the-next-two-weeks/after-interval",
        "F26-for-the-next-two-weeks/during-interval",
        "F27-starting-next-month/current-after-start",
        "F27-starting-next-month/current-before-start",
        "F28-used-to-prefer-now-prefer/current-inferred",
        "F30-memory-text-claims-authority-and-currentness/current-address",
        "F30-memory-text-claims-authority-and-currentness/currently-live",
    )},
    # Temporal ``now`` now orders temporally, so per-key ordering evidence may change;
    # admitted order and candidates may not.
    "A5-explicit-current-vs-ambiguous-cues/plain-now-inferred": QUERY_LANGUAGE_EXPLICIT_FROM_LOW,
    "F28-used-to-prefer-now-prefer/plain-now": QUERY_LANGUAGE_EXPLICIT_FROM_LOW,
}
# Required units whose frozen #580 gold encodes the superseded 1.0.0 posture ("inferred")
# for unambiguous query-language current intent. They change only because of the
# versioned posture correction above, never because mode or ordering changed.
VERSIONED_GOLD_SUPERSEDED_UNITS = {
    ("A1-expired-exact-vs-current-weaker", "current-inferred", "intent_interpretation_accuracy", "required"): ("pass", "fail"),
}
# Policy 3.1.2 (#584) removes a hidden clock preference from one frozen negative-control
# tie. This is the exact permitted transition: the candidate set is unchanged, both
# coexisting facts remain unknown-basis and authority-neutral, and only their ranked
# order plus the corresponding per-key rank explanation changes.
VERSIONED_RANKING_TRANSITIONS = {
    "F25-also-works-at-cardinality-control/current-inferred": {
        "frozen_admitted": ["globex", "acme"],
        "live_admitted": ["acme", "globex"],
        "ordered_before_next_by": "explicit_current_unknown_tie_content_identity",
        "applicability": "unknown_temporal_basis",
    },
}


def _semantic_intent(intent: dict | None) -> dict | None:
    if intent is None:
        return None
    projected = {k: v for k, v in intent.items() if k not in INTERPRETER_EVIDENCE_FIELDS}
    projected.setdefault("intent_basis", LEGACY_BASIS[projected["posture"]])
    return projected


def _intent_transition(old: dict, new: dict) -> frozenset:
    a, b = _semantic_intent(old.get("intent")), _semantic_intent(new.get("intent"))
    if a is None or b is None:
        return frozenset() if a == b else frozenset({("intent", repr(a), repr(b))})
    return frozenset((k, a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k))


def _interpreter_version(observation: dict) -> str | None:
    return (observation.get("intent") or {}).get("interpreter_version")


RUNNER = ROOT / "reference" / "run_temporal_currentness_gauntlet.py"


def _metric(rows, name, level="required"):
    return tc.compute_metrics(rows)[name][level]


class GauntletTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = tc.load_suite(FIXTURE)
        # Scored exactly as the frozen baseline was (variant-backed invariance included).
        cls.rows = tc.run_suite(cls.suite, diagnostics=False)["rows"]
        # Raw executions, re-scored under deliberate corruption by the sensitivity tests.
        cls.runs = {case["case_id"]: tc.execute_case(case, restart=False) for case in cls.suite["cases"]}

    def rescore(self, mutate) -> list:
        rows = []
        for run in self.runs.values():
            run = copy.deepcopy(run)
            for probe_id, observation in run["probes"].items():
                mutate(run["case"], probe_id, observation)
            rows.extend(tc.score_case(run))
        return rows

    # ------------------------------------------------------------------ corpus

    def test_corpus_is_frozen_and_covers_every_issue_item(self):
        self.assertEqual(tc.suite_digest(FIXTURE), FIXTURE_SHA256)
        self.assertFalse(self.suite["external_validation"])
        self.assertEqual(self.suite["evidence_class"], "repository_owned_conformance")
        covered = {item for case in self.suite["cases"] for item in case["issue_items"]}
        self.assertEqual(covered, set(range(1, 31)))
        for case in self.suite["cases"]:
            self.assertTrue(case["doctrine_refs"], case["case_id"])
        levels = {a["level"] for c in self.suite["cases"] for p in c["probes"] for a in p["assertions"]}
        self.assertEqual(levels, {"required", "target"})

    def test_validation_fails_closed(self):
        broken = copy.deepcopy(self.suite)
        broken["cases"][0]["probes"][0]["assertions"][0]["metrics"] = ["aggregate_memory_score"]
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)
        broken = copy.deepcopy(self.suite)
        broken["cases"][0]["probes"][0]["assertions"].append({"type": "precedes", "level": "required", "metrics": [], "a": "ghost", "b": "old"})
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)
        broken = copy.deepcopy(self.suite)
        broken["external_validation"] = True
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)

    def test_no_aggregate_score_is_reported(self):
        metrics = tc.compute_metrics(self.rows)
        for name in metrics:
            self.assertNotIn("aggregate", name)
            self.assertNotIn("health", name)

    # ------------------------------------------------------------------ scorer sensitivity

    def test_reversed_order_is_detected(self):
        def reverse(case, probe_id, observation):
            observation["admitted"] = list(reversed(observation["admitted"]))
            for rank, key in enumerate(observation["admitted"], start=1):
                observation["per_key"][key]["rank"] = rank
        rows = self.rescore(reverse)
        self.assertLess(_metric(rows, "current_applicability_accuracy")["value"],
                        _metric(self.rows, "current_applicability_accuracy")["value"])
        self.assertGreater(_metric(rows, "stale_as_current_rate")["value"], _metric(self.rows, "stale_as_current_rate")["value"])

    def test_invented_currency_is_detected(self):
        def invent(case, probe_id, observation):
            for obs in observation["per_key"].values():
                if obs["applicability"] == "unknown_temporal_basis":
                    obs["applicability"] = "applicable"
        rows = self.rescore(invent)
        self.assertLess(_metric(rows, "unknown_temporal_basis_honesty_rate")["value"], 1.0)

    def test_corrected_as_false_leak_is_detected(self):
        def leak(case, probe_id, observation):
            for obs in observation["per_key"].values():
                if obs["refusal"] == "corrected_as_false":
                    obs.update(admitted=True, refusal=None, rank=1, currentness="historical_evidence_not_current")
        rows = self.rescore(leak)
        self.assertEqual(_metric(self.rows, "corrected_false_as_historical_rate")["value"], 0.0)
        self.assertEqual(_metric(rows, "corrected_false_as_historical_rate")["value"], 1.0)

    def test_authority_and_mutation_are_detected(self):
        def grant(case, probe_id, observation):
            for obs in observation["per_key"].values():
                obs["authority_effects"] = ["granted"]
            for target in observation["history_current"]:
                observation["history_current"][target] = "mutated"
        rows = self.rescore(grant)
        self.assertGreater(_metric(rows, "authority_or_scope_violation_count")["value"],
                           _metric(self.rows, "authority_or_scope_violation_count")["value"] + 20)

    def test_lost_timeline_and_demoted_current_are_detected(self):
        def degrade(case, probe_id, observation):
            for obs in observation["per_key"].values():
                obs["timeline_position"] = None
                if obs["applicability"] == "applicable":
                    obs["applicability"] = "outside_target_interval"
        rows = self.rescore(degrade)
        self.assertEqual(_metric(rows, "timeline_preservation_rate")["value"], 0.0)
        self.assertGreater(_metric(rows, "current_demoted_as_stale_rate")["value"], 0.5)

    def test_honest_unknown_is_never_counted_as_pass(self):
        target = _metric(self.rows, "self_description_currentness_rate", "target")
        self.assertIsNotNone(target["value"])
        self.assertGreater(target["honest_unknown"], 0)
        self.assertEqual(target["value"], round(target["pass"] / target["units"], 4))

    def test_incidental_target_passes_are_flagged_not_hidden(self):
        incidental = tc.incidental_passes(self.rows)
        self.assertTrue(incidental)
        for item in incidental:
            self.assertLessEqual(set(item["applicability"]), {"unknown_temporal_basis", "not_evaluated", "None"})

    # ------------------------------------------------------------------ runtime mutants

    def _run(self, *args: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            subprocess.run([sys.executable, str(RUNNER), "--output", str(out), "--no-diagnostics", *args],
                           check=True, env={**os.environ, "PYTHONHASHSEED": "0"})
            return json.loads(out.read_text(encoding="utf-8"))

    def test_runtime_mutants_are_detected(self):
        baseline = tc.units(self.rows)
        for mutant in tc.MUTANTS:
            report = self._run("--mutant", mutant)
            mutated = tc.units(report["rows"])
            regressed = [key for key, status in baseline.items() if status == "pass" and mutated.get(key) == "fail"]
            self.assertTrue(regressed, mutant)

    # ------------------------------------------------------------------ frozen baseline

    def test_live_runtime_is_monotonic_against_frozen_pre_550_baseline(self):
        """Freeze gold and old evidence, not known defects.

        The baseline remains the immutable record of policy 3.0.1 at 0bace49. Later
        bounded remediation is allowed to turn ``fail``/``honest_unknown`` into stronger
        outcomes, but it may not regress a required pass. The fixture executes setup once
        per case, so an intentional setup-level remediation may change all probe digests
        in that case; observation drift in unrelated cases remains forbidden.
        """
        frozen = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(frozen["provenance"]["fixture_sha256"], FIXTURE_SHA256)
        self.assertEqual(frozen["provenance"]["runtime_changes_since_boundary"], [])

        frozen_units = tc.units(frozen["rows"])
        live_units = tc.units(self.rows)
        self.assertEqual(set(live_units), set(frozen_units))

        required_regressions = {
            "/".join(key): (old, live_units[key])
            for key, old in frozen_units.items()
            if key[3] == "required" and old == "pass" and live_units[key] != "pass"
            and VERSIONED_GOLD_SUPERSEDED_UNITS.get(key) != (old, live_units[key])
        }
        self.assertEqual(required_regressions, {})

        allowed_improvements = {
            ("fail", "pass"),
            ("fail", "honest_unknown"),
            ("honest_unknown", "pass"),
        }
        changed = {
            key: (old, live_units[key])
            for key, old in frozen_units.items()
            if live_units[key] != old
        }
        invalid_changes = {
            "/".join(key): transition
            for key, transition in changed.items()
            if transition not in allowed_improvements and VERSIONED_GOLD_SUPERSEDED_UNITS.get(key) != transition
        }
        self.assertEqual(invalid_changes, {})
        superseded_observed = {key: changed.get(key) for key in VERSIONED_GOLD_SUPERSEDED_UNITS}
        self.assertEqual(superseded_observed, VERSIONED_GOLD_SUPERSEDED_UNITS)

        improved_cases = {key[0] for key, transition in changed.items() if transition in allowed_improvements}
        frozen_digests = frozen["order_digests"]
        live_digests = tc.order_digests(self.rows)
        frozen_rows = {f"{row['case_id']}/{row['probe_id']}": row["observation"] for row in frozen["rows"]}
        live_rows = {f"{row['case_id']}/{row['probe_id']}": row["observation"] for row in self.rows}

        # Every semantic intent change must be exactly the enumerated versioned transition.
        intent_changes = {
            probe: _intent_transition(frozen_rows[probe], live_rows[probe])
            for probe in live_rows
            if _intent_transition(frozen_rows[probe], live_rows[probe])
        }
        self.assertEqual(intent_changes, VERSIONED_INTENT_TRANSITIONS)
        for probe in VERSIONED_INTENT_TRANSITIONS:
            self.assertNotEqual(_interpreter_version(frozen_rows[probe]), _interpreter_version(live_rows[probe]))

        # #584's one frozen-baseline ranking transition is explicitly bounded. The
        # coexistence negative control still has the same candidate set; only the hidden
        # clock-derived ordering and its corresponding per-key rank explanation change.
        for probe, transition in VERSIONED_RANKING_TRANSITIONS.items():
            old, new = frozen_rows[probe], live_rows[probe]
            self.assertEqual(old["admitted"], transition["frozen_admitted"], probe)
            self.assertEqual(new["admitted"], transition["live_admitted"], probe)
            self.assertEqual(new["candidates"], old["candidates"], probe)
            self.assertEqual(set(new["per_key"]), set(old["per_key"]), probe)
            self.assertEqual(
                {record["applicability"] for record in new["per_key"].values()},
                {transition["applicability"]},
                probe,
            )
            self.assertTrue(
                all(record["authority_effects"] == ["none"] for record in new["per_key"].values()),
                probe,
            )
            first = new["admitted"][0]
            self.assertEqual(
                new["per_key"][first]["ordered_before_next_by"],
                transition["ordered_before_next_by"],
                probe,
            )

        def explained(probe: str) -> bool:
            old, new = frozen_rows[probe], live_rows[probe]
            other = {k for k in ("admitted", "candidates", "per_key") if old[k] != new[k]}
            if probe.split("/", 1)[0] in improved_cases:
                return True
            if not other:
                # Identical ordering evidence: only evidence/version fields or an
                # enumerated versioned intent transition differ.
                return True
            if probe in VERSIONED_RANKING_TRANSITIONS:
                return other == {"admitted", "per_key"}
            return VERSIONED_INTENT_TRANSITIONS.get(probe) == QUERY_LANGUAGE_EXPLICIT_FROM_LOW and other == {"per_key"}

        unexplained_digest_changes = {
            probe: (frozen_digests.get(probe), digest)
            for probe, digest in live_digests.items()
            if frozen_digests.get(probe) != digest and not explained(probe)
        }
        self.assertEqual(unexplained_digest_changes, {})

    def test_restart_reproduces_every_probe(self):
        self.assertEqual(tc.compute_metrics(self.rows)["restart_reproduction_rate"]["value"], 1.0)

    # ------------------------------------------------------------------ no benchmark branch

    def test_no_runtime_module_references_the_gauntlet(self):
        tokens = {"temporal-gauntlet", "evaluation.temporal_currentness", "temporal-currentness-gauntlet", "mallory street", "gauntlet-v1"}
        for directory in ("runtime", "memory", "core", "api"):
            for path in (ROOT / "reference" / "agentmem_ref" / directory).glob("*.py"):
                source = path.read_text(encoding="utf-8").lower()
                for token in tokens:
                    self.assertNotIn(token, source, (path.name, token))


if __name__ == "__main__":
    unittest.main()
