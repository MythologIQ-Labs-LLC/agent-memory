"""Deterministic multi-session agent-utility harness (longitudinal lane, #819 lane 5).

Each scenario replays an agent's memory writes across several sessions (every session is a
fresh ``AgentMemory.open`` on the same durable root) and then asks task probes through the
public ``AgentMemory.recall`` only. Expectations name *writes* (``w1``, ``w2``...), never fact
UUIDs, and are read by the scorer only: nothing in a fixture reaches the runtime except the
write calls and the probe query an agent would issue.

The agent view of a recall is ``returned`` (budget ``k``) plus the per-fact labels the
contract already exposes. A returned fact counts as *labelled non-current* exactly when the
temporal-currentness gauntlet would call it ``not_current`` (historical-evidence admission,
``outside_target_interval``, ``prospectively_applicable`` or the cross-fact limitation).

Per-probe outcome classes (a probe may carry several):

``stale_used``            a ``stale`` write is returned unlabelled, or outranks every ``current`` one
``incorrect_supersession`` a ``current`` write is refused as superseded or labelled non-current
``missing_current``       a ``current`` write is not returned at all
``missing_dependency``    a ``dependency`` write is not returned
``history_lost``          a ``history`` write (historical probe) is not returned
``isolation_violation``   a ``forbidden`` write (other scope / forgotten) is returned
``unnecessary_abstention`` nothing returned although ``current`` writes exist

A probe succeeds when it has none of these.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

HARNESS_VERSION = "1.0.0"
DEFAULT_BUDGET = 5
NOT_CURRENT_LABELS = frozenset({"outside_target_interval", "prospectively_applicable",
                                "limited_by_cross_fact_state_change"})
NOT_CURRENT_REFUSALS = frozenset({"superseded_not_current", "tombstoned", "not_current"})
OUTCOME_CLASSES = ("stale_used", "incorrect_supersession", "missing_current", "missing_dependency",
                   "history_lost", "isolation_violation", "unnecessary_abstention")
FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "benchmarks" / "longitudinal-utility" / "scenarios-v1.json"


class LongitudinalError(ValueError):
    pass


def load_fixture(path: Path | None = None) -> dict:
    data = json.loads((path or FIXTURE_PATH).read_text(encoding="utf-8"))
    if data.get("fixture_version") != "1.0.0":
        raise LongitudinalError("unsupported fixture_version")
    return data


def fixture_digest(path: Path | None = None) -> str:
    return "sha256:" + hashlib.sha256((path or FIXTURE_PATH).read_bytes()).hexdigest()


def _correction_evidence(tenant: str, scope: str) -> list:
    """Qualifying evidence for a governed correction: a reviewed procedure citing its source.

    This is the same qualifying-evidence shape the facade tests use. It satisfies PAMA for the
    medium-risk correction cell; it is evidence, not a bypass.
    """
    from ..memory import procedural_memory as pm

    skill = pm.SkillArtifact(
        skill_id="skill:longitudinal-user-correction",
        version=1,
        purpose="apply a correction the user stated in conversation",
        scope=scope,
        isolation_domain_refs=(tenant, scope),
        required_isolation_domain_refs=(tenant, scope),
        procedure_markdown="# verify\nConfirm the correction against the user's own statement.",
        provenance_refs=("evidence:user-statement",),
    )
    return pm.evidence_for(skill)


def _open(root: Path, scenario: Mapping[str, Any], scope: str | None, open_kwargs: Mapping[str, Any]):
    from .. import AgentMemory

    return AgentMemory.open(
        root,
        tenant=scenario.get("tenant", "tenant:longitudinal"),
        actor_id=scenario.get("actor", "agent:assistant"),
        scope=scope or scenario.get("scope", "project:assistant"),
        purpose="longitudinal agent utility",
        **open_kwargs,
    )


def _apply_write(memory, write: Mapping[str, Any], ledger: dict, tenant: str, scope: str) -> dict:
    op = write["op"]
    kwargs = {key: write[key] for key in ("valid_from", "valid_until", "observed_at") if key in write}
    if op == "remember":
        if "proposition" in write:
            kwargs["proposition"] = write["proposition"]
        if "source_ref" in write:
            kwargs["source_ref"] = write["source_ref"]
        result = memory.remember(write["ref"], write["text"], **kwargs)
    elif op == "correct":
        evidence = _correction_evidence(tenant, scope) if write.get("evidence", True) else ()
        result = memory.correct(write["ref"], write["text"], evidence=evidence,
                                replacement_kind=write.get("replacement_kind", "error_correction"), **kwargs)
    elif op == "forget":
        result = memory.forget(write["ref"])
    else:
        raise LongitudinalError(f"unknown op {op!r}")
    if write.get("expect_committed", True) and not result.get("committed"):
        raise LongitudinalError(f"write {write['id']} did not commit: {result.get('outcome')} {result.get('refusal')}")
    if op != "forget":
        ledger[write["id"]] = result.get("fact_uuid")
    return result


def _observe(result: Mapping[str, Any], fact_uuid: str) -> dict:
    admission = result["admissions"].get(fact_uuid)
    if admission is None:
        return {"candidate": False, "returned": False, "refusal": None, "label": None, "currentness": None}
    ranking = admission.get("ranking_evidence") or {}
    basis = admission.get("admission_basis") or {}
    return {
        "candidate": True,
        "returned": fact_uuid in result["returned"],
        "rank": result["returned"].index(fact_uuid) + 1 if fact_uuid in result["returned"] else None,
        "refusal": admission.get("refusal"),
        "label": ranking.get("temporal_applicability"),
        "currentness": basis.get("currentness"),
    }


def _labelled_not_current(obs: Mapping[str, Any]) -> bool:
    return obs["currentness"] == "historical_evidence_not_current" or obs["label"] in NOT_CURRENT_LABELS


def score_probe(probe: Mapping[str, Any], result: Mapping[str, Any], ledger: Mapping[str, Any]) -> dict:
    def uuids(key: str) -> list[tuple[str, str]]:
        return [(wid, ledger[wid]) for wid in probe.get(key, ()) if ledger.get(wid)]

    observed = {wid: _observe(result, uuid) for key in ("current", "stale", "dependency", "history", "forbidden")
                for wid, uuid in uuids(key)}
    classes: list[str] = []
    current = uuids("current")
    current_ranks = [observed[w]["rank"] for w, _ in current if observed[w]["returned"]]
    best_current = min(current_ranks) if current_ranks else None
    for wid, _ in uuids("stale"):
        obs = observed[wid]
        if obs["returned"] and (not _labelled_not_current(obs) or (best_current is None or obs["rank"] < best_current)):
            classes.append("stale_used")
            break
    for wid, _ in current:
        obs = observed[wid]
        if obs["refusal"] in NOT_CURRENT_REFUSALS or (obs["returned"] and _labelled_not_current(obs)):
            classes.append("incorrect_supersession")
            break
    if any(not observed[w]["returned"] for w, _ in current):
        classes.append("missing_current")
    if any(not observed[w]["returned"] for w, _ in uuids("dependency")):
        classes.append("missing_dependency")
    if any(not observed[w]["returned"] for w, _ in uuids("history")):
        classes.append("history_lost")
    if any(observed[w]["returned"] for w, _ in uuids("forbidden")):
        classes.append("isolation_violation")
    if current and not result["returned"]:
        classes.append("unnecessary_abstention")
    cross = [w for w, _ in current + uuids("dependency") + uuids("history")
             if probe["_write_session"].get(w, probe["session"]) < probe["session"]]
    return {
        "probe_id": probe["id"],
        "success": not classes,
        "classes": classes,
        "returned_count": len(result["returned"]),
        "cross_session_needed": len(cross),
        "cross_session_recalled": sum(1 for w in cross if observed[w]["returned"]),
        "observed": observed,
    }


def run_scenario(scenario: Mapping[str, Any], *, recall_hook: Callable[..., dict] | None = None,
                 open_kwargs: Mapping[str, Any] | None = None) -> list[dict]:
    """Replay one scenario in a fresh temporary root and score every probe.

    ``open_kwargs`` selects the arm (handle options passed to every ``AgentMemory.open``).
    """
    open_kwargs = dict(open_kwargs or {})
    tenant = scenario.get("tenant", "tenant:longitudinal")
    default_scope = scenario.get("scope", "project:assistant")
    ledger: dict[str, Any] = {}
    write_session: dict[str, int] = {}
    outcomes: list[dict] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for index, session in enumerate(scenario["sessions"], start=1):
            handles: dict[str, Any] = {}
            try:
                for write in session.get("writes", ()):
                    scope = write.get("scope", default_scope)
                    if scope not in handles:
                        handles[scope] = _open(root, scenario, scope, open_kwargs)
                    _apply_write(handles[scope], write, ledger, tenant, scope)
                    write_session[write["id"]] = index
                for probe in session.get("probes", ()):
                    scope = probe.get("scope", default_scope)
                    if scope not in handles:
                        handles[scope] = _open(root, scenario, scope, open_kwargs)
                    kwargs = {"budget": probe.get("budget", scenario.get("budget", DEFAULT_BUDGET))}
                    if "temporal_intent" in probe:
                        kwargs["temporal_intent"] = probe["temporal_intent"]
                    recall = recall_hook or (lambda memory, query, **kw: memory.recall(query, **kw))
                    result = recall(handles[scope], probe["query"], **kwargs)
                    outcome = score_probe({**probe, "session": index, "_write_session": write_session}, result, ledger)
                    outcome.update({"scenario_id": scenario["id"], "family": scenario["family"],
                                    "phrasing": probe.get("phrasing", "unqualified")})
                    outcomes.append(outcome)
            finally:
                for handle in handles.values():
                    handle.close()
    return outcomes


def summarize(outcomes: Sequence[Mapping[str, Any]]) -> dict:
    def block(rows: Sequence[Mapping[str, Any]]) -> dict:
        needed = sum(r["cross_session_needed"] for r in rows)
        return {
            "probes": len(rows),
            "success": sum(1 for r in rows if r["success"]),
            **{name: sum(1 for r in rows if name in r["classes"]) for name in OUTCOME_CLASSES},
            "cross_session_recall": f"{sum(r['cross_session_recalled'] for r in rows)}/{needed}",
        }

    families = sorted({r["family"] for r in outcomes})
    phrasings = sorted({r["phrasing"] for r in outcomes})
    return {
        "overall": block(outcomes),
        "by_family": {f: block([r for r in outcomes if r["family"] == f]) for f in families},
        "by_phrasing": {p: block([r for r in outcomes if r["phrasing"] == p]) for p in phrasings},
    }


def run_fixture(path: Path | None = None, *, open_kwargs: Mapping[str, Any] | None = None) -> dict:
    fixture = load_fixture(path)
    outcomes = [row for scenario in fixture["scenarios"] for row in run_scenario(scenario, open_kwargs=open_kwargs)]
    case_rows = [{key: row[key] for key in ("scenario_id", "probe_id", "family", "phrasing", "success", "classes",
                                             "returned_count", "cross_session_needed", "cross_session_recalled")}
                 for row in outcomes]
    return {
        "harness_version": HARNESS_VERSION,
        "fixture_digest": fixture_digest(path),
        "open_kwargs": dict(open_kwargs or {}),
        "summary": summarize(outcomes),
        "cases": case_rows,
    }
