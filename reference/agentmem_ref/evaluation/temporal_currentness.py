"""Repository-owned temporal/currentness qualification gauntlet (#580).

Evaluation tooling only. It drives the public ``AgentMemory`` facade against a frozen,
digest-bound fixture corpus whose gold outcomes were authored from doctrine before the
corpus was run, and reports every dimension separately. It never modifies runtime
behavior: ranking ablations use the existing evaluation-only variant mechanism
(``benchmark_ranking_variants``), and negative-control mutants are installed only in the
evaluator's own process.

Evidence class: repository-owned conformance / falsification evidence. It is not
independent external validation, and a pass does not accept ADR-039.

Assertion statuses::

    pass            the gold outcome holds
    fail            the gold outcome does not hold
    honest_unknown  a TARGET outcome is not reached, but every involved memory is
                    exposed as having an unknown temporal basis (an honest outcome,
                    counted separately and never as a pass)
    not_applicable  the assertion could not be evaluated (recorded, never scored)
"""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

SUITE_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = "1.0.0"
EVALUATOR_VERSION = "1.1.0"

TENANT = "tenant:temporal-gauntlet"
SCOPE = "project:temporal-gauntlet"
ACTOR = "agent:temporal-gauntlet"
PURPOSE = "temporal currentness qualification"

LEVELS = ("required", "target")
ASSERTION_TYPES = {
    "admitted", "refused", "not_candidate", "precedes", "semantic", "clock", "intent", "timeline_order",
    "decided_by_non_temporal_stage", "no_mutation", "no_fabricated_declared_basis", "authority_none",
    "invariant_under_variant", "metabolism_not_used", "metabolism_carries_no_validity",
    "metabolism_disposition_is_proposal_only",
}
ROLES = {"current_applicable", "not_current", "not_affirmed_current", "prospective", "historical_evidence",
         "unknown_basis", "not_demoted"}
OPS = {"remember", "correct", "forget", "dispute", "remember_foreign_scope", "recall_repeat"}
DECLARED_FIELDS = ("valid_from", "valid_until", "observed_at")

# Metric definitions. "accuracy" = pass / units; "event_rate" = fail / units (the failure
# IS the event, e.g. stale presented ahead of current); "count" = failed assertions.
METRICS: dict[str, str] = {
    "current_applicability_accuracy": "accuracy",
    "stale_as_current_rate": "event_rate",
    "current_demoted_as_stale_rate": "event_rate",
    "as_of_state_accuracy": "accuracy",
    "historical_state_admission_accuracy": "accuracy",
    "corrected_false_as_historical_rate": "event_rate",
    "prospective_applicability_accuracy": "accuracy",
    "unknown_temporal_basis_honesty_rate": "accuracy",
    "atemporal_relevance_preservation_rate": "accuracy",
    "clock_source_accuracy": "accuracy",
    "intent_interpretation_accuracy": "accuracy",
    "state_change_vs_error_correction_accuracy": "accuracy",
    "coexistence_preservation_rate": "accuracy",
    "timeline_preservation_rate": "accuracy",
    "self_description_currentness_rate": "accuracy",
    "metabolism_validity_separation_rate": "accuracy",
    "authority_or_scope_violation_count": "count",
    "temporal_self_claim_rank_influence_count": "count",
}
NOT_MEASURABLE = {
    "conflict_coexistence_classification_accuracy": (
        "not measurable pre-#550: the runtime exposes no proposition/conflict classification; "
        "coexistence_preservation_rate records the safety half"
    ),
}

TEMPORAL_STAGES = {"temporal_applicability_tier", "temporal_order_within_query_regime", "temporal_evidence:newer_first"}
NOT_CURRENT_REFUSALS = {"superseded_not_current", "outside_historical_validity", "corrected_as_false"}
# Demotion semantics per intent, stated from doctrine rather than imported from the
# runtime: under current/as_of a candidate valid only outside the target instant is not
# the canonical answer; under prospective, one that is merely valid now is not.
DEMOTED_LABELS = {
    "current": {"outside_target_interval", "prospectively_applicable"},
    "as_of": {"outside_target_interval", "prospectively_applicable"},
    "prospective": {"outside_target_interval", "applicable_not_prospective"},
}
LADDER_CLASSES = {
    "explicit_intent": "missing_query_intent",
    "declared_self": "missing_temporal_self_description",
    "declared_cross": "missing_proposition_identity_or_cardinality",
    "governed_state_change": "resolvable_today_by_governed_state_change",
}
# Failures whose class follows from the metric itself rather than from a ladder rung.
METRIC_CLASSES = {
    "intent_interpretation_accuracy": "query_intent_interpretation",
    "temporal_self_claim_rank_influence_count": "relevance_ranking_rewards_temporal_self_claims",
}
ASSERTION_CLASSES = {"invariant_under_variant": "relevance_ranking_rewards_temporal_self_claims"}
# Canonical smallest-first order of counterfactual mechanisms. A probe's declared ladder
# comes first; every other diagnostic variant the case defines is appended in this order.
CANONICAL_LADDER = ("explicit_intent", "declared_self", "declared_cross", "governed_state_change")
DIMENSION_CLASSES = {"B_as_of_historical": "historical_admission", "E_metabolism_vs_validity": "metabolism_vs_validity"}


class GauntletError(RuntimeError):
    """The harness could not execute a case faithfully. Never silently skipped."""


# ---------------------------------------------------------------------------- suite


def suite_digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_suite(path: str | Path) -> dict[str, Any]:
    suite = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_suite(suite)
    return suite


def validate_suite(suite: Mapping[str, Any]) -> None:
    """Structural validation; fails closed on anything the evaluator would misread."""

    if suite.get("schema_version") != SUITE_SCHEMA_VERSION:
        raise GauntletError(f"unsupported suite schema {suite.get('schema_version')!r}")
    if suite.get("external_validation") is not False:
        raise GauntletError("suite must declare external_validation: false")
    case_ids: set[str] = set()
    for case in suite["cases"]:
        cid = case["case_id"]
        if cid in case_ids:
            raise GauntletError(f"duplicate case {cid}")
        case_ids.add(cid)
        keys: set[str] = set()
        for op in case["setup"]:
            if op["op"] not in OPS:
                raise GauntletError(f"{cid}: unknown op {op['op']!r}")
            if "key" in op and op["op"] not in {"dispute"}:
                if op["key"] in keys:
                    raise GauntletError(f"{cid}: duplicate key {op['key']}")
                keys.add(op["key"])
        for entry in case.get("metabolism", ()):
            if entry["key"] not in keys:
                raise GauntletError(f"{cid}: metabolism for unknown key {entry['key']}")
        variants = case.get("diagnostic_variants", {})
        probe_ids: set[str] = set()
        for probe in case["probes"]:
            pid = probe["probe_id"]
            if pid in probe_ids:
                raise GauntletError(f"{cid}: duplicate probe {pid}")
            probe_ids.add(pid)
            for assertion in probe["assertions"]:
                kind = assertion["type"]
                if kind not in ASSERTION_TYPES:
                    raise GauntletError(f"{cid}/{pid}: unknown assertion {kind!r}")
                if assertion["level"] not in LEVELS:
                    raise GauntletError(f"{cid}/{pid}: unknown level {assertion['level']!r}")
                for metric in assertion["metrics"]:
                    if metric not in METRICS:
                        raise GauntletError(f"{cid}/{pid}: unknown metric {metric!r}")
                if kind == "semantic" and assertion["role"] not in ROLES:
                    raise GauntletError(f"{cid}/{pid}: unknown role {assertion['role']!r}")
                for field in ("key", "a", "b"):
                    ref = assertion.get(field)
                    if ref is not None and not ref.startswith("*") and ref not in keys:
                        raise GauntletError(f"{cid}/{pid}: unknown key {ref!r}")
                if kind == "invariant_under_variant" and assertion["variant"] not in variants:
                    raise GauntletError(f"{cid}/{pid}: undefined variant {assertion['variant']!r}")
            for vid in probe.get("diagnostic_ladder", ()):
                if vid not in variants and vid != "explicit_intent":
                    raise GauntletError(f"{cid}/{pid}: undefined ladder variant {vid!r}")


# ---------------------------------------------------------------------------- execution


def _correction_evidence(scope: str):
    from agentmem_ref.memory import procedural_memory as pm

    skill = pm.SkillArtifact(
        skill_id="skill:temporal-gauntlet-correction",
        version=1,
        purpose="governed correction inside the temporal gauntlet",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the replacement against its source.",
        provenance_refs=("evidence:temporal-gauntlet-correction",),
    )
    return pm.evidence_for(skill)


def _apply_patch(case: Mapping[str, Any], patch: Mapping[str, Any] | None, transform: str | None) -> dict[str, Any]:
    case = copy.deepcopy(dict(case))
    patch = patch or {}
    for op in case["setup"]:
        key = op.get("key")
        if key in patch.get("replace_op", {}):
            replacement = patch["replace_op"][key]
            base = {k: v for k, v in op.items() if k not in {"op", "target", "replacement_kind"}}
            op.clear()
            op.update({**base, **replacement, "key": key})
        if key in patch.get("set_declared", {}):
            op.update(patch["set_declared"][key])
        if key in patch.get("replace_text", {}):
            op["text"] = patch["replace_text"][key]
        if transform == "transaction_only":
            for field in DECLARED_FIELDS:
                op.pop(field, None)
    for probe in case["probes"]:
        if probe["probe_id"] in patch.get("set_intent", {}):
            probe["temporal_intent"] = patch["set_intent"][probe["probe_id"]]
        if transform == "inferred_only":
            probe["temporal_intent"] = None
    return case


def _open(root: str, scope: str = SCOPE):
    from agentmem_ref import AgentMemory

    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose=PURPOSE)


def _committed(result: Mapping[str, Any], what: str) -> str:
    if not result.get("committed") or not result.get("fact_uuid"):
        raise GauntletError(f"setup {what} was not committed: {result.get('refusal') or result.get('outcome')}")
    return str(result["fact_uuid"])


def _run_setup(memory, root: str, case: Mapping[str, Any]):
    keys: dict[str, str] = {}
    declared: dict[str, dict[str, str]] = {}
    targets: dict[str, str] = {}
    for op in case["setup"]:
        kind = op["op"]
        fields = {field: op[field] for field in DECLARED_FIELDS if op.get(field) is not None}
        if kind == "remember":
            keys[op["key"]] = _committed(memory.remember(f"memory:{op['target']}", op["text"], **fields), op["key"])
            targets[op["target"]] = op["key"]
            declared[op["key"]] = fields
        elif kind == "correct":
            result = memory.correct(
                f"memory:{op['target']}", op["text"], evidence=_correction_evidence(SCOPE), risk_class="low",
                replacement_kind=op["replacement_kind"], **fields,
            )
            keys[op["key"]] = _committed(result, op["key"])
            targets[op["target"]] = op["key"]
            declared[op["key"]] = fields
        elif kind == "forget":
            if not memory.forget(f"memory:{op['target']}").get("committed"):
                raise GauntletError(f"setup forget {op['target']} was not committed")
        elif kind == "dispute":
            result = memory.dispute(
                f"memory:{op['target']}",
                fact_uuid=keys[op["key"]],
                evidence=_correction_evidence(SCOPE),
                risk_class="low",
            )
            if not result.get("committed"):
                raise GauntletError(f"setup dispute {op['key']} was not committed: {result.get('refusal') or result.get('outcome')}")
        elif kind == "remember_foreign_scope":
            memory.close()
            with _open(root, scope=op["scope"]) as foreign:
                keys[op["key"]] = _committed(foreign.remember(f"memory:{op['target']}", op["text"], **fields), op["key"])
            declared[op["key"]] = fields
            memory = _open(root)
        elif kind == "recall_repeat":
            for _ in range(int(op["times"])):
                memory.recall(op["query"], reference_time=case.get("reference_time_default"))
    return memory, keys, declared, targets


def _metabolism(case: Mapping[str, Any], keys: Mapping[str, str]) -> dict[str, Any]:
    from agentmem_ref.memory import metabolism as mb

    out = {}
    for entry in case.get("metabolism", ()):
        snapshot = mb.MetabolismSnapshot(
            memory_ref=keys[entry["key"]],
            lifecycle_state="active",
            evaluated_at_ms=int(entry["evaluated_at_ms"]),
            last_meaningful_use_ms=int(entry["last_meaningful_use_ms"]),
            baseline_saturation=float(entry.get("baseline_saturation", 0.0)),
            reinforcement_observations=tuple(
                mb.ReinforcementObservation(kind=kind, count=int(count)) for kind, count in sorted(entry["reinforcement"].items())
            ),
        )
        out[entry["key"]] = mb.NativeMetabolismEstimator().evaluate(snapshot).to_dict()
    return out


def _observe(memory, probe: Mapping[str, Any], keys: Mapping[str, str], targets: Mapping[str, str]) -> dict[str, Any]:
    by_uuid = {uuid: key for key, uuid in keys.items()}
    name = lambda uuid: by_uuid.get(uuid, f"unkeyed:{uuid}")  # noqa: E731
    recalled = memory.recall(probe["query"], temporal_intent=probe.get("temporal_intent"), reference_time=probe.get("reference_time"))
    per_key: dict[str, dict[str, Any]] = {}
    intent = None
    for uuid in recalled["candidates"]:
        decision = recalled["admissions"].get(uuid, {})
        evidence = decision.get("ranking_evidence") or {}
        basis = decision.get("admission_basis") or {}
        clocks = (evidence.get("temporal_evidence") or {}).get("clocks") or {}
        if evidence.get("query_temporal_intent") and intent is None:
            intent = evidence["query_temporal_intent"]
        per_key[name(uuid)] = {
            "admitted": uuid in recalled["admitted"],
            "rank": recalled["admitted"].index(uuid) + 1 if uuid in recalled["admitted"] else None,
            "refusal": decision.get("refusal"),
            "outcome": decision.get("outcome"),
            "applicability": evidence.get("temporal_applicability"),
            "ordering_clock": evidence.get("temporal_ordering_clock"),
            "ordered_before_next_by": evidence.get("ordered_before_next_by"),
            "lexical_relevance_score": repr(evidence["lexical_relevance_score"]) if "lexical_relevance_score" in evidence else None,
            "clock_kinds": sorted(clocks),
            "declared_basis": (evidence.get("temporal_evidence") or {}).get("declared_basis"),
            "timeline_position": evidence.get("timeline_position"),
            "admission_mode": basis.get("admission_mode"),
            "currentness": basis.get("currentness"),
            "replacement_kind": basis.get("replacement_kind"),
            "metabolic_evidence": evidence.get("metabolic_evidence"),
            "authority_effects": sorted({str(evidence.get("authority_effect", "none")), str(basis.get("authority_effect", "none")),
                                         str((evidence.get("query_temporal_intent") or {}).get("authority_effect", "none"))}),
        }
    history = {target: name(memory.history(f"memory:{target}")["history"].get("current_fact_uuid")) for target in sorted(targets)}
    observation = {
        "admitted": [name(uuid) for uuid in recalled["admitted"]],
        "candidates": sorted(name(uuid) for uuid in recalled["candidates"]),
        "intent": intent,
        "per_key": per_key,
        "history_current": history,
    }
    observation["digest"] = _digest({k: observation[k] for k in ("admitted", "candidates", "intent", "per_key")})
    return observation


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def execute_case(case: Mapping[str, Any], *, patch: Mapping[str, Any] | None = None, transform: str | None = None,
                 restart: bool = True) -> dict[str, Any]:
    """Run one case in a fresh store: setup, every probe, then restart and re-probe."""

    case = _apply_patch(case, patch, transform)
    with tempfile.TemporaryDirectory() as root:
        memory = _open(root)
        try:
            memory, keys, declared, targets = _run_setup(memory, root, case)
            probes = {probe["probe_id"]: _observe(memory, probe, keys, targets) for probe in case["probes"]}
            restart_digests = {}
            if restart:
                memory.close()
                memory = _open(root)
                restart_digests = {probe["probe_id"]: _observe(memory, probe, keys, targets)["digest"] for probe in case["probes"]}
        finally:
            memory.close()
    return {
        "case": case,
        "keys": dict(keys),
        "declared": declared,
        "probes": probes,
        "restart_digests": restart_digests,
        "metabolism": _metabolism(case, keys),
    }


# ---------------------------------------------------------------------------- scoring


def _role_holds(role: str, obs: Mapping[str, Any] | None, mode: str | None) -> bool:
    if obs is None:
        return False
    admitted, label = obs["admitted"], obs["applicability"]
    demoted = label in DEMOTED_LABELS.get(mode or "", set())
    declared_valid = bool({"declared_valid_from", "declared_valid_until"} & set(obs["clock_kinds"]))
    if role == "current_applicable":
        return admitted and obs["currentness"] in (None, "current_state") and label == "applicable"
    if role == "not_current":
        if not admitted:
            return obs["refusal"] in NOT_CURRENT_REFUSALS
        return obs["currentness"] == "historical_evidence_not_current" or label in {"outside_target_interval", "prospectively_applicable"}
    if role == "not_affirmed_current":
        return not (admitted and label == "applicable")
    if role == "prospective":
        return admitted and label == "prospectively_applicable"
    if role == "historical_evidence":
        return admitted and obs["currentness"] == "historical_evidence_not_current"
    if role == "unknown_basis":
        return admitted and (label == "unknown_temporal_basis" or (label in (None, "not_evaluated") and not declared_valid))
    if role == "not_demoted":
        return admitted and not demoted
    raise GauntletError(f"unknown role {role}")


def _is_unknown(obs: Mapping[str, Any] | None) -> bool:
    return bool(obs) and obs["admitted"] and obs["applicability"] == "unknown_temporal_basis"


def _resolve(ref: str, observation: Mapping[str, Any]) -> str | None:
    if ref == "*first":
        return observation["admitted"][0] if observation["admitted"] else None
    if ref == "*second":
        return observation["admitted"][1] if len(observation["admitted"]) > 1 else None
    return ref


def evaluate_assertion(assertion: Mapping[str, Any], observation: Mapping[str, Any], run: Mapping[str, Any],
                       probe: Mapping[str, Any], variant_runner: Callable[[str], Mapping[str, Any]] | None) -> tuple[str, str]:
    """Return (status, detail). Evaluation reads only the observation and the gold."""

    kind = assertion["type"]
    per_key = observation["per_key"]
    mode = (observation.get("intent") or {}).get("mode")
    get = lambda ref: per_key.get(ref) if ref else None  # noqa: E731
    target_level = assertion["level"] == "target"

    def verdict(ok: bool, detail: str, involved: tuple[str, ...] = ()) -> tuple[str, str]:
        if ok:
            return "pass", detail
        if target_level and involved and all(_is_unknown(get(ref)) for ref in involved):
            return "honest_unknown", detail + " (every involved memory exposes unknown_temporal_basis)"
        return "fail", detail

    if kind == "admitted":
        obs = get(assertion["key"])
        return verdict(bool(obs and obs["admitted"]), f"{assertion['key']}: {_brief(obs)}")
    if kind == "refused":
        obs = get(assertion["key"])
        ok = bool(obs) and not obs["admitted"] and obs["refusal"] in assertion["reasons"]
        return verdict(ok, f"{assertion['key']}: {_brief(obs)} expected one of {assertion['reasons']}")
    if kind == "not_candidate":
        return verdict(assertion["key"] not in per_key, f"{assertion['key']} candidate={assertion['key'] in per_key}")
    if kind == "precedes":
        a, b = get(assertion["a"]), get(assertion["b"])
        ok = bool(a and a["admitted"]) and (not (b and b["admitted"]) or a["rank"] < b["rank"])
        return verdict(ok, f"{assertion['a']}={_brief(a)} {assertion['b']}={_brief(b)}", (assertion["a"], assertion["b"]))
    if kind == "semantic":
        obs = get(assertion["key"])
        ok = _role_holds(assertion["role"], obs, mode)
        return verdict(ok, f"{assertion['key']} expected {assertion['role']}: {_brief(obs)}", (assertion["key"],))
    if kind == "clock":
        obs = get(assertion["key"])
        return verdict(bool(obs) and obs["ordering_clock"] == assertion["clock"],
                       f"{assertion['key']} clock={obs and obs['ordering_clock']} expected {assertion['clock']}")
    if kind == "intent":
        gold, seen = probe["gold_intent"], observation.get("intent") or {}
        if not seen:
            return "not_applicable", "ranking evidence carries no query temporal intent under this policy"
        ok = seen.get("mode") == gold["mode"] and seen.get("posture") == gold["posture"]
        if gold["mode"] != "historical":
            ok = ok and seen.get("orders_temporally") == gold["orders_temporally"]
        return verdict(ok, f"observed {seen.get('mode')}/{seen.get('posture')}/{seen.get('confidence')} "
                           f"orders={seen.get('orders_temporally')} expected {gold}")
    if kind == "timeline_order":
        positions = [(get(ref) or {}).get("timeline_position") for ref in assertion["keys"]]
        ok = all(p is not None for p in positions) and positions == sorted(positions) and len(set(positions)) == len(positions)
        return verdict(ok, f"timeline positions {dict(zip(assertion['keys'], positions))}")
    if kind == "decided_by_non_temporal_stage":
        a_ref, b_ref = _resolve(assertion["a"], observation), _resolve(assertion["b"], observation)
        order = observation["admitted"]
        if a_ref not in order or b_ref not in order or abs(order.index(a_ref) - order.index(b_ref)) != 1:
            return "not_applicable", f"{a_ref}/{b_ref} not adjacent in admitted order"
        earlier = a_ref if order.index(a_ref) < order.index(b_ref) else b_ref
        stage = per_key[earlier]["ordered_before_next_by"]
        return verdict(stage not in TEMPORAL_STAGES, f"{earlier} ordered before next by {stage}")
    if kind == "no_mutation":
        current = observation["history_current"].get(assertion["target"])
        return verdict(current == assertion["key"], f"history({assertion['target']}).current={current}")
    if kind == "no_fabricated_declared_basis":
        obs = get(assertion["key"])
        caller_declared = bool(run["declared"].get(assertion["key"]))
        ok = bool(obs) and (caller_declared or obs["declared_basis"] is None)
        return verdict(ok, f"{assertion['key']} declared_basis={obs and obs['declared_basis']} caller_declared={caller_declared}")
    if kind == "authority_none":
        bad = {ref: obs["authority_effects"] for ref, obs in per_key.items() if obs["authority_effects"] != ["none"]}
        return verdict(not bad, f"non-none authority effects: {bad}")
    if kind == "invariant_under_variant":
        if variant_runner is None:
            return "not_applicable", "variant execution disabled"
        other = variant_runner(assertion["variant"])["probes"][probe["probe_id"]]
        def relative(obs):
            admitted = [ref for ref in obs["admitted"] if ref in assertion["keys"]]
            return admitted, sorted(ref for ref in assertion["keys"] if ref not in admitted)
        mine, theirs = relative(observation), relative(other)
        return verdict(mine == theirs, f"order {mine} vs {assertion['variant']} {theirs}")
    if kind == "metabolism_not_used":
        used = {ref: obs["metabolic_evidence"] for ref, obs in per_key.items() if obs["admitted"] and obs["metabolic_evidence"] != "not_used"}
        return verdict(not used, f"metabolic evidence used for applicability/order: {used}")
    if kind == "metabolism_carries_no_validity":
        forbidden = {"valid_from", "valid_until", "currentness", "applicability", "temporal_applicability", "supersedes", "truth"}
        leaks = {key: sorted(forbidden & _all_keys(value)) for key, value in run["metabolism"].items()}
        leaks = {k: v for k, v in leaks.items() if v}
        authority = {key: value["reinforcement"].get("authority_effect") for key, value in run["metabolism"].items()}
        ok = not leaks and all(v == "none" for v in authority.values()) and bool(run["metabolism"])
        return verdict(ok, f"metabolism validity fields={leaks} authority={authority}")
    if kind == "metabolism_disposition_is_proposal_only":
        evaluation = run["metabolism"].get(assertion["key"])
        obs = get(assertion["key"])
        ok = bool(evaluation) and bool(obs and obs["admitted"]) and evaluation["reinforcement"].get("authority_effect") == "none"
        return verdict(ok, f"disposition={evaluation and evaluation['disposition']} admitted={bool(obs and obs['admitted'])}")
    raise GauntletError(f"unhandled assertion {kind}")


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return set(value) | set().union(*(_all_keys(v) for v in value.values())) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(_all_keys(v) for v in value)) if value else set()
    return set()


def _brief(obs: Mapping[str, Any] | None) -> str:
    if obs is None:
        return "not a candidate"
    if not obs["admitted"]:
        return f"refused:{obs['refusal']}"
    return f"rank {obs['rank']} {obs['applicability']} {obs['currentness'] or ''}".strip()


def _unit_status(statuses: list[str]) -> str:
    scored = [s for s in statuses if s != "not_applicable"]
    if not scored:
        return "not_applicable"
    if "fail" in scored:
        return "fail"
    if "honest_unknown" in scored:
        return "honest_unknown"
    return "pass"


def score_case(run: Mapping[str, Any], variant_runner: Callable[[str], Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    case = run["case"]
    rows = []
    for probe in case["probes"]:
        observation = run["probes"][probe["probe_id"]]
        results = []
        for index, assertion in enumerate(probe["assertions"]):
            status, detail = evaluate_assertion(assertion, observation, run, probe, variant_runner)
            results.append({"index": index, "type": assertion["type"], "level": assertion["level"],
                            "metrics": assertion["metrics"], "status": status, "detail": detail,
                            **{k: assertion[k] for k in ("key", "a", "b", "role", "variant") if k in assertion}})
        rows.append({
            "case_id": case["case_id"], "dimension": case["dimension"], "probe_id": probe["probe_id"],
            "query": probe["query"], "temporal_intent": probe.get("temporal_intent"),
            "reference_time": probe.get("reference_time"), "gold_intent": probe["gold_intent"],
            "observation": observation, "assertions": results,
            "restart_reproduced": (run["restart_digests"].get(probe["probe_id"]) == observation["digest"]) if run["restart_digests"] else None,
            "ambiguous": probe.get("ambiguous", []),
        })
    return rows


def incidental_passes(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Passing TARGET orderings that no temporal evidence decided.

    A target ``precedes`` that holds while neither memory has an affirmed temporal basis
    (unknown or not evaluated) was decided by relevance, not by knowing which state is
    current. It is reported so that a later change cannot count it as progress, and so
    a regression that flips it is read as relevance movement, not temporal behavior.
    """

    out = []
    for row in rows:
        per_key = row["observation"]["per_key"]
        for result in row["assertions"]:
            if result["type"] != "precedes" or result["level"] != "target" or result["status"] != "pass":
                continue
            a, b = per_key.get(result["a"]), per_key.get(result["b"])
            labels = {(a or {}).get("applicability"), (b or {}).get("applicability")}
            if b and labels <= {"unknown_temporal_basis", "not_evaluated", None}:
                out.append({"case_id": row["case_id"], "probe_id": row["probe_id"], "a": result["a"], "b": result["b"],
                            "applicability": sorted(str(x) for x in labels),
                            "decided_by": a.get("ordered_before_next_by") if a and b and a["rank"] + 1 == b["rank"] else "non_adjacent"})
    return out


def units(rows: list[Mapping[str, Any]]) -> dict[tuple[str, str, str, str], str]:
    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for row in rows:
        for result in row["assertions"]:
            for metric in result["metrics"]:
                grouped.setdefault((row["case_id"], row["probe_id"], metric, result["level"]), []).append(result["status"])
    return {key: _unit_status(statuses) for key, statuses in grouped.items()}


def compute_metrics(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    unit_status = units(rows)
    metrics: dict[str, Any] = {}
    for name, kind in METRICS.items():
        entry: dict[str, Any] = {"kind": kind}
        for level in LEVELS:
            statuses = [s for (_, _, m, lv), s in unit_status.items() if m == name and lv == level and s != "not_applicable"]
            counts = {s: statuses.count(s) for s in ("pass", "honest_unknown", "fail")}
            n = len(statuses)
            if kind == "count":
                value = sum(1 for row in rows for r in row["assertions"]
                            if name in r["metrics"] and r["level"] == level and r["status"] == "fail")
            elif kind == "accuracy":
                value = round(counts["pass"] / n, 4) if n else None
            else:
                value = round(counts["fail"] / n, 4) if n else None
            entry[level] = {"units": n, **counts, "value": value}
        metrics[name] = entry
    for name, reason in NOT_MEASURABLE.items():
        metrics[name] = {"kind": "not_measurable", "status": "not_measurable_pre_550", "reason": reason}
    restart = [row["restart_reproduced"] for row in rows if row["restart_reproduced"] is not None]
    metrics["restart_reproduction_rate"] = {
        "kind": "accuracy", "probes": len(restart), "reproduced": sum(restart),
        "value": round(sum(restart) / len(restart), 4) if restart else None,
        "not_reproduced": [f"{row['case_id']}/{row['probe_id']}" for row in rows if row["restart_reproduced"] is False],
    }
    return metrics


# ---------------------------------------------------------------------------- diagnostics


def auto_variant(case: Mapping[str, Any], vid: str, probe_id: str) -> Mapping[str, Any] | None:
    variants = case.get("diagnostic_variants", {})
    if vid in variants:
        return variants[vid]
    if vid == "explicit_intent":
        probe = next(p for p in case["probes"] if p["probe_id"] == probe_id)
        mode = probe["gold_intent"]["mode"]
        if mode in {"current", "prospective", "historical", "atemporal_or_unspecified"}:
            return {"set_intent": {probe_id: {"mode": mode}}}
    return None


def diagnose(case: Mapping[str, Any], rows: list[Mapping[str, Any]], runner: Callable[[str, Mapping[str, Any]], Mapping[str, Any]]) -> list[dict[str, Any]]:
    """For every failed or honest-unknown unit, find the smallest diagnostic variant that resolves it.

    Variants are counterfactual *inputs* (caller intent, declared validity, a governed
    state change), never runtime changes. The first passing rung of the probe's ladder
    names the smallest mechanism that would supply the missing information.
    """

    unit_status = units(rows)
    findings = []

    def attempt(vids: tuple[str, ...], case_id: str, probe_id: str, metric: str, level: str) -> str:
        patches = [auto_variant(case, vid, probe_id) for vid in vids]
        if any(p is None for p in patches):
            return "not_defined"
        merged: dict[str, dict] = {}
        for patch in patches:
            for field, value in patch.items():
                merged.setdefault(field, {}).update(value)
        variant_rows = score_case(runner("+".join(vids), merged))
        return units(variant_rows).get((case_id, probe_id, metric, level), "not_applicable")

    for (case_id, probe_id, metric, level), status in sorted(unit_status.items()):
        if status not in {"fail", "honest_unknown"}:
            continue
        probe = next(p for p in case["probes"] if p["probe_id"] == probe_id)
        declared = list(probe.get("diagnostic_ladder", ()))
        extra = [vid for vid in CANONICAL_LADDER if vid not in declared and vid in case.get("diagnostic_variants", {})]
        ladder = tuple(declared + extra)
        rungs = [{"variant": vid, "status": attempt((vid,), case_id, probe_id, metric, level)} for vid in ladder]
        resolving = next((r["variant"] for r in rungs if r["status"] == "pass"), None)
        if resolving is None:
            # No single mechanism suffices: try pairs, smallest first, in ladder order.
            for i, first in enumerate(ladder):
                for second in ladder[i + 1:]:
                    status_pair = attempt((first, second), case_id, probe_id, metric, level)
                    rungs.append({"variant": f"{first}+{second}", "status": status_pair})
                    if status_pair == "pass" and resolving is None:
                        resolving = f"{first}+{second}"
        failing_types = {a["type"] for row in rows if row["probe_id"] == probe_id for a in row["assertions"]
                         if metric in a["metrics"] and a["level"] == level and a["status"] in {"fail", "honest_unknown"}}
        if metric in METRIC_CLASSES:
            cls = METRIC_CLASSES[metric]
        elif failing_types & set(ASSERTION_CLASSES):
            cls = ASSERTION_CLASSES[sorted(failing_types & set(ASSERTION_CLASSES))[0]]
        elif resolving:
            cls = "+".join(LADDER_CLASSES.get(part, part) for part in resolving.split("+"))
        else:
            cls = probe.get("unresolved_class_hint") or DIMENSION_CLASSES.get(case["dimension"]) or "unclassified"
        findings.append({"case_id": case_id, "probe_id": probe_id, "metric": metric, "level": level, "status": status,
                         "ladder": rungs, "smallest_resolving_variant": resolving, "failure_class": cls,
                         "dimension_class": DIMENSION_CLASSES.get(case["dimension"])})
    return findings


def negative_controls(case: Mapping[str, Any], runner: Callable[[str, Mapping[str, Any]], Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Fixture-declared bad inputs that the required assertions must reject."""

    out = []
    for vid in case.get("negative_control_variants", ()):
        rows = score_case(runner(vid, case["diagnostic_variants"][vid]))
        failed = [f"{r['probe_id']}#{a['index']}:{a['type']}" for r in rows for a in r["assertions"]
                  if a["level"] == "required" and a["status"] == "fail"]
        out.append({"case_id": case["case_id"], "variant": vid, "detected": bool(failed), "failed_required_assertions": failed})
    return out


# ---------------------------------------------------------------------------- runtime mutants


MUTANTS = ("invent_currency", "ignore_validity")


def install_mutant(name: str) -> None:
    """Evaluation-process-only runtime mutants proving the evaluator can fail bad temporal behavior.

    ``invent_currency``: unknown temporal basis is reported as applicable.
    ``ignore_validity``: every candidate is reported applicable, so nothing is demoted.
    """

    from agentmem_ref.runtime import ranking_policy

    original = ranking_policy.temporal_applicability
    if name == "invent_currency":
        def mutant(intent, temporal):
            label = original(intent, temporal)
            return "applicable" if label == "unknown_temporal_basis" else label
    elif name == "ignore_validity":
        def mutant(intent, temporal):
            label = original(intent, temporal)
            return "applicable" if label not in {"not_evaluated", "no_reference_time"} else label
    else:
        raise ValueError(f"unknown mutant {name!r}")
    ranking_policy.temporal_applicability = mutant


# ---------------------------------------------------------------------------- suite run


def run_suite(suite: Mapping[str, Any], *, transform: str | None = None, diagnostics: bool = True,
              case_filter: Callable[[Mapping[str, Any]], bool] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    for case in suite["cases"]:
        if case_filter and not case_filter(case):
            continue
        run = execute_case(case, transform=transform)
        cache: dict[str, Mapping[str, Any]] = {}

        def runner(vid: str, patch: Mapping[str, Any], _case=case, _cache=cache) -> Mapping[str, Any]:
            if vid not in _cache:
                _cache[vid] = execute_case(_case, patch=patch, transform=transform, restart=False)
            return _cache[vid]

        def variant_runner(vid: str, _case=case, _runner=runner) -> Mapping[str, Any]:
            return _runner(vid, _case["diagnostic_variants"][vid])

        case_rows = score_case(run, variant_runner)
        rows.extend(case_rows)
        if diagnostics:
            findings.extend(diagnose(case, case_rows, runner))
            controls.extend(negative_controls(case, runner))
    return {"rows": rows, "metrics": compute_metrics(rows), "diagnostics": findings, "fixture_negative_controls": controls,
            "incidental_target_passes": incidental_passes(rows)}


def order_digests(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    return {f"{row['case_id']}/{row['probe_id']}": row["observation"]["digest"] for row in rows}
