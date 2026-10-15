#!/usr/bin/env python3
"""Execute the five #644 Runtime Baseline v7 replay contracts (``644-v7-replay-dsl/1``).

    python reference/run_644_v7_replays.py --all --output-dir reports/validation/644-v7-replays
    python reference/run_644_v7_replays.py --replay <replay_id> --output-dir <dir>

Input: a frozen fixture ``reference/fixtures/644-v7-replays/<replay_id>.json``.
Output: ``<dir>/<replay_id>/report.json`` with every observation and expectation, and
``<dir>/<replay_id>/manifest.json`` binding fixture, runner, report and runtime tree by
sha256. Hashes are integrity bindings for review, never signatures, attestation or
acceptance. Verdict: PASS (all expectations hold, clean provenance), FAIL (an
expectation fails or a case cannot execute) or BLOCKED (provenance precondition
unmet, for example a dirty source tree). Exit status 0 PASS, 1 FAIL, 2 BLOCKED.

The runner drives only the public ``AgentMemory`` facade, ``ControlledRecallPlanner``
and the documented #644 observer/adapter methods. Private internals are touched only
for declared fault injection (S9) and the independent full-store census oracle (A9).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.adapter import RecallContext  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.recall_control import (  # noqa: E402
    ControlledRecallPlanner, DeterministicRecallController, RecallRouteBudget,
)
from agentmem_ref.runtime import evidence_sufficiency as es  # noqa: E402
from agentmem_ref.runtime import recall_observation_receipt as rr  # noqa: E402
from agentmem_ref.runtime import typed_proposition as typed  # noqa: E402
from agentmem_ref.runtime.adapter import DECLARED_TEMPORAL_KEY  # noqa: E402
from agentmem_ref.runtime.temporal_intent import parse_time  # noqa: E402

RUNNER_VERSION = "644-v7-replay-runner/1"
DSL_VERSION = "644-v7-replay-dsl/1"
FIXTURE_DIR = REFERENCE / "fixtures" / "644-v7-replays"
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "644-v7-replays"
OUTPUT_REL = "reports/validation/644-v7-replays/"
REPLAYS = (
    "typed-sufficiency-noninterference-and-negative-controls-v1",
    "governed-persisted-typed-slot-sufficiency-admission-recheck-v1",
    "governed-admitted-typed-value-coherence-v1",
    "committed-governed-transition-witness-v1",
    "same-slot-safety-counterevidence-and-immutable-stop-gate-v1",
)
TENANT, SCOPE, ACTOR, PURPOSE = "tenant:v7r", "project:a", "agent:v7r", "v7 replay"
OTHER_SCOPE = "project:b"
CLEAN = ("coverage_observed_unattested", "mechanical_coverage_observed")


class ReplayError(Exception):
    """A case could not execute as specified (a harness or scenario failure)."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()


# ------------------------------------------------------------------------------- scenario state

def _prop(spec: Mapping) -> dict:
    out = {"subject": spec["s"], "attribute": spec["a"], "value": spec["v"],
           "assertion": spec.get("assertion", "state"), "cardinality": spec.get("cardinality", "single"),
           "flags": dict(spec.get("flags", {}))}
    if "replaces" in spec:
        out["replaces_value"] = spec["replaces"]
    return out


def _evidence(scope: str = SCOPE):
    skill = pm.SkillArtifact(
        skill_id="skill:v7-replay", version=1, purpose="v7 replay review", scope=scope,
        isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# Review\nConfirm the governed change.", provenance_refs=("evidence:v7-replay",))
    return pm.evidence_for(skill)


def context(scope: str = SCOPE) -> RecallContext:
    return RecallContext(target_domain_refs=(TENANT, scope), principal_ref=ACTOR, project_ref=scope, purpose=PURPOSE)


class Scenario:
    """A fresh store driven through the public facade; tracks fact labels."""

    def __init__(self, root: Path):
        self.root = root
        self.memory = self._open(SCOPE)
        self.labels: dict[str, str] = {}       # label -> fact uuid
        self.uuid_label: dict[str, str] = {}   # fact uuid -> label
        self.heads: dict[str, int] = {}
        self.texts: list[str] = []
        self.open_proposal: str | None = None

    def _open(self, scope: str) -> AgentMemory:
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose=PURPOSE)

    def close(self) -> None:
        self.memory.close()

    def _bind(self, label: str, fact_uuid: str) -> None:
        self.labels[label] = fact_uuid
        self.uuid_label[fact_uuid] = label

    def _new_head(self, ref: str, fact_uuid: str) -> None:
        self.heads[ref] = self.heads.get(ref, 1) + 1
        self._bind(f"{ref}@{self.heads[ref]}", fact_uuid)

    def resolve(self, label: str) -> str:
        if label.startswith("@literal:"):
            return label[len("@literal:"):]
        if label not in self.labels:
            raise ReplayError(f"unknown fact label {label}")
        return self.labels[label]

    def label(self, fact_uuid: str) -> str:
        return self.uuid_label.get(fact_uuid, f"@unlabelled:{fact_uuid}")

    def apply(self, op: Mapping) -> None:
        kind = op["op"]
        m = self.memory
        if kind == "remember":
            kw = {k: op[k] for k in ("valid_from", "valid_until") if k in op}
            if "prop" in op:
                kw["proposition"] = _prop(op["prop"])
            self.texts.append(op["text"])
            if "scope" in op:
                self.memory.close()
                other = self._open(op["scope"])
                try:
                    out = other.remember(op["ref"], op["text"], **kw)
                finally:
                    other.close()
                self.memory = self._open(SCOPE)
                if not out.get("committed"):
                    raise ReplayError(f"remember refused: {out}")
                self._bind(f"b:{op['ref']}", out["fact_uuid"])
                return
            out = m.remember(op["ref"], op["text"], **kw)
            if not out.get("committed"):
                raise ReplayError(f"remember refused: {out}")
            self.heads.setdefault(op["ref"], 1)
            self._bind(op["ref"], out["fact_uuid"])
        elif kind == "retain_extracted":
            self.texts.append(op["text"])
            proposal = contract.proposal_from_envelope(m._proposal(
                target_reference=op["ref"], fact_text=op["text"], operation="promotion", risk_class="low"))
            record = typed.typed_record(typed.validate(_prop(op["prop"])), "extracted:v7r@1")
            out = m.runtime.retain(proposal, op["text"], typed_write={"typed_proposition": record})
            if not out.committed:
                raise ReplayError(f"extracted retain refused: {out.refusal}")
            self.heads.setdefault(op["ref"], 1)
            self._bind(op["ref"], out.fact_uuid)
        elif kind == "forget":
            out = m.forget(op["ref"])
            if not out.get("committed"):
                raise ReplayError(f"forget refused: {out}")
        elif kind == "dispute":
            out = m.dispute(op["ref"], fact_uuid=self.labels[self._current_label(op["ref"])],
                            evidence=_evidence(), risk_class="low", evidence_refs=("evidence:dispute",))
            if not out.get("committed"):
                raise ReplayError(f"dispute refused: {out}")
        elif kind == "correct":
            self.texts.append(op["text"])
            cite = op.get("cite", "none")
            refs: tuple[str, ...] = ()
            if cite == "open_proposal":
                refs = (self._capture_open_proposal(),)
            elif cite == "forged":
                self._capture_open_proposal(required=False)
                refs = ("proposal:forged-v7-replay",)
            out = m.correct(op["ref"], op["text"], evidence=_evidence(), risk_class="low",
                            replacement_kind=op["kind"], evidence_refs=refs)
            if not out.get("committed"):
                raise ReplayError(f"correct refused: {out}")
            self._new_head(op["ref"], out["fact_uuid"])
        elif kind == "apply_open_proposal":
            pid = self._capture_open_proposal()
            target = next(p["target_reference"] for p in m.semantic_proposals(status="open") if p["proposal_id"] == pid)
            out = m.apply_semantic_proposal(pid, evidence=_evidence(), risk_class="low")
            if not out.get("committed"):
                raise ReplayError(f"apply refused: {out}")
            self._new_head(target, out["fact_uuid"])
        elif kind == "reopen":
            self.memory.close()
            self.memory = self._open(SCOPE)
        else:
            raise ReplayError(f"unknown operation {kind}")

    def _current_label(self, ref: str) -> str:
        n = self.heads.get(ref, 1)
        return ref if n == 1 else f"{ref}@{n}"

    def _capture_open_proposal(self, required: bool = True) -> str | None:
        props = self.memory.semantic_proposals(status="open")
        if len(props) != 1:
            if required:
                raise ReplayError(f"expected exactly one open semantic proposal, found {len(props)}")
            return None
        self.open_proposal = props[0]["proposal_id"]
        return self.open_proposal

    # --- recall machinery -----------------------------------------------------------------
    def planner(self, case: Mapping, controller=None) -> ControlledRecallPlanner:
        return ControlledRecallPlanner(self.memory.runtime.adapter, controller=controller or FixtureController(case))

    def governed(self, fn):
        return self.memory.runtime.durable_runtime.run_governed_read(fn)

    def recall(self, case: Mapping, planner=None):
        planner = planner or self.planner(case)
        ctx = context(SCOPE)
        refs = tuple(self.resolve(x) for x in case.get("logical_refs", ()))
        result = self.governed(lambda: planner.recall(case["query"], ctx, logical_memory_refs=refs))
        return planner, ctx, result

    def state(self) -> tuple[str, int]:
        adapter = self.memory.runtime.adapter
        return adapter.checkpoint_substrate().state_digest(), len(adapter.events)


class FixtureController:
    """DeterministicRecallController with the fixture's explicit lexical limit / count target."""

    def __init__(self, case: Mapping):
        self.case = case
        self._inner = DeterministicRecallController()

    def plan(self, query, *, logical_memory_refs, available_routes):
        plan = self._inner.plan(query, logical_memory_refs=logical_memory_refs, available_routes=available_routes)
        if "lexical_limit" in self.case:
            plan = dataclasses.replace(plan, route_budgets=tuple(
                RecallRouteBudget(b.route_id, self.case["lexical_limit"], anchor_limit=b.anchor_limit)
                if b.route_id == "lexical" else b for b in plan.route_budgets))
        if "count_target" in self.case:
            plan = dataclasses.replace(plan, evidence_sufficiency_target=self.case["count_target"])
        return plan


class AuthorityClaimingController(FixtureController):
    def plan(self, query, *, logical_memory_refs, available_routes):
        plan = super().plan(query, logical_memory_refs=logical_memory_refs, available_routes=available_routes)
        return dataclasses.replace(plan, authority_effect="stop")


class Exploding(Mapping):
    def __getitem__(self, key):
        raise RuntimeError("hostile mapping")

    def __iter__(self):
        raise RuntimeError("hostile mapping")

    def __len__(self):
        return 1


# ------------------------------------------------------------------------------- helpers

def need_key(spec: Mapping) -> str:
    return typed.typed_slot(spec["s"], spec["a"])


def needs_of(case: Mapping) -> tuple:
    if "need_keys" in case:
        keys = []
        for raw in case["need_keys"]:
            if raw.startswith("@canonical:"):
                s, a = raw[len("@canonical:"):].split("|")
                keys.append(typed.typed_slot(s, a))
            else:
                keys.append(raw)
        return tuple(es.CoverageNeed(k) for k in keys)
    return tuple(es.CoverageNeed(need_key(n), n.get("min", 1)) for n in case["needs"])


def mutate(result, mutation: Mapping, sc: Scenario, ctx: RecallContext) -> None:
    m = mutation["m"]
    rec = result.recall
    if m == "inject_admitted":
        rec.admitted.append(sc.resolve(mutation["ref"]))
    elif m == "drop_candidate":
        rec.candidates.pop()
    elif m == "drop_admitted":
        dropped = rec.admitted.pop()
        if dropped in rec.ranked_admitted:
            rec.ranked_admitted.remove(dropped)
    elif m == "reverse_ranked":
        rec.ranked_admitted.reverse()
        if len(rec.ranked_admitted) < 2:
            raise ReplayError("reverse_ranked needs at least two ranked facts")
    elif m == "zero_route_counts":
        result.route_candidate_counts.update({k: 0 for k in result.route_candidate_counts})
    elif m == "change_query":
        rec.query = rec.query + " tampered"
    elif m == "change_plan":
        result.plan = dataclasses.replace(result.plan, evidence_sufficiency_target=result.plan.evidence_sufficiency_target + 1)
    elif m == "clear_refusals":
        if not rec.refusals:
            raise ReplayError("clear_refusals needs a refused candidate")
        rec.refusals.clear()
    elif m == "change_policy":
        rec.policy_version = "tampered-policy"
    elif m == "change_admission_mode":
        rec.admission_mode = "historical_evidence"
    elif m == "change_evaluated_at":
        rec.evaluated_at = "2001-01-01T00:00:00Z"
    elif m == "remove_receipt":
        result.observation_receipt = None
    elif m == "remint_receipt":
        old = result.observation_receipt
        result.observation_receipt = rr.capture_recall_observation(
            query=rec.query, reader_domain_refs=tuple(ctx.target_domain_refs), principal_ref=ctx.principal_ref,
            project_ref=ctx.project_ref, purpose=ctx.purpose, task_ref=ctx.task_ref,
            controller_ref=old.controller_ref, admission_policy=old.admission_policy,
            admission_mode=old.admission_mode, evaluated_at=old.evaluated_at,
            candidates=rec.candidates, admitted=rec.admitted, ranked=rec.ranked_admitted,
            route_observations=old.routes, observed_route_counts=result.route_candidate_counts,
            plan=result.plan.to_dict(), refusals=rec.refusals)
    elif m == "hostile_route_counts":
        result.route_candidate_counts = Exploding()
    elif m == "hostile_refusals":
        rec.refusals = Exploding()
    elif m == "plan_object":
        result.plan = object()
    elif m == "recall_none":
        result.recall = None
    elif m == "receipt_garbage":
        result.observation_receipt = "garbage"
    elif m == "counts_bool":
        result.route_candidate_counts.update({k: True for k in result.route_candidate_counts})
    else:
        raise ReplayError(f"unknown mutation {m}")


def safe_unchanged(result) -> tuple[bool, bool]:
    try:
        return result.observation_unchanged() is True, False
    except Exception:  # noqa: BLE001 - recording whether verification raised is the observation
        return False, True


def report_observables(report, sc: Scenario, needs: tuple) -> dict:
    d = report.to_dict()
    first = needs[0].key if needs else None
    refs = d["need_support_refs"].get(first, []) if first else []
    obs = {
        "diagnosis": d["diagnosis"], "continuation_proposal": d["continuation_proposal"],
        "mechanical_coverage_met": d["mechanical_coverage_met"], "count_target_met": d["count_target_met"],
        "support_refs": sorted(sc.label(r) for r in refs), "support_count": len(refs),
        "need_missing": first in d["missing_needs"] if first else None,
        "stop_attested": d["stop_attested"], "authority_effect": d["authority_effect"],
        "answer_quality_verified": d["answer_quality_verified"], "can_admit": d["can_admit"],
        "can_mutate": d["can_mutate"],
        "budget_bound_routes": d["budget_bound_routes"], "unexecuted_routes": d["unexecuted_routes"],
    }
    coherence = [c for c in d["value_coherence"] if c["need_key"] == first]
    obs["coherence_status"] = coherence[0]["status"] if coherence else None
    obs["coherence_groups"] = (sorted(sorted(sc.label(r) for r in g) for g in coherence[0]["fact_groups"])
                               if coherence else None)
    obstacles = d.get("slot_obstacles", {}).get(first, {}) if first else {}
    for key in ("eligible_unretrieved", "qualified_counter_evidence", "declared_temporal_boundary"):
        obs[f"obstacles.{key}"] = obstacles.get(key)
    return obs


def census_oracle(sc: Scenario, slots: tuple[str, ...], admitted: set[str], ctx: RecallContext) -> dict:
    """Independent full-store enumeration with the contract's per-fact predicates (docs 79, 81)."""
    adapter = sc.memory.runtime.adapter
    counters = {s: {"eligible_unretrieved": 0, "qualified_counter_evidence": 0, "declared_temporal_boundary": 0}
                for s in sorted(slots)}
    for fact in adapter._substrate.all_facts():
        if fact.is_transaction_expired or adapter._admission_refusal(fact, ctx) is not None:
            continue
        stored = adapter.write_semantics(fact.uuid, ctx)
        record = stored.get("typed_proposition") if isinstance(stored, dict) else None
        if not isinstance(record, dict) or record.get("slot") not in counters:
            continue
        slot = record["slot"]
        declared = (fact.attributes or {}).get(DECLARED_TEMPORAL_KEY) or {}
        starts, recorded = parse_time(declared.get("valid_from")), parse_time(fact.created_at)
        if declared.get("valid_until") or (declared.get("valid_from") and (starts is None or recorded is None or starts > recorded)):
            counters[slot]["declared_temporal_boundary"] += 1
        if (record.get("basis") != typed.CALLER_DECLARED or stored.get("typed_ineligible_reasons")
                or not isinstance(record.get("flags"), dict) or any(record["flags"].values())):
            counters[slot]["qualified_counter_evidence"] += 1
        if fact.uuid not in admitted:
            counters[slot]["eligible_unretrieved"] += 1
    return counters


# ------------------------------------------------------------------------------- observation kinds

def observe_coverage(case: Mapping, sc: Scenario) -> dict:
    needs = needs_of(case)
    planner, ctx, result = sc.recall(case)
    for op in case.get("between", ()):
        sc.apply(op)
    for mutation in case.get("mutations", ()):
        mutate(result, mutation, sc, ctx)
    fault = case.get("fault")
    adapter = sc.memory.runtime.adapter
    if fault == "no_census_reader":
        adapter.current_typed_slot_obstacles = None
    elif fault == "no_substrate_enumeration":
        adapter._substrate.all_facts = None
    elif fault == "corrupt_index_key":
        adapter._semantic_index()["{corrupt"] = {"ref-corrupt": {}}
    obs_ctx = context(case.get("observe_scope", SCOPE))
    before_state = sc.state()
    before_result = (list(result.recall.candidates), list(result.recall.admitted),
                     list(result.recall.ranked_admitted), dict(result.recall.refusals))
    report = sc.governed(lambda: planner.observe_persisted_typed_coverage(result, obs_ctx, needs=needs))
    obs = report_observables(report, sc, needs)
    obs["receipt_unchanged"], obs["verification_raised"] = safe_unchanged(result)
    probes = case.get("probes", ())
    if "state_unchanged" in probes:
        obs["state_unchanged"] = sc.state() == before_state
    if "result_unchanged" in probes:
        obs["result_unchanged"] = before_result == (list(result.recall.candidates), list(result.recall.admitted),
                                                    list(result.recall.ranked_admitted), dict(result.recall.refusals))
    if "permutation_invariant" in probes:
        again = sc.governed(lambda: planner.observe_persisted_typed_coverage(result, obs_ctx, needs=tuple(reversed(needs))))
        obs["permutation_invariant"] = canonical(again.to_dict()) == canonical(report.to_dict())
    if "census_oracle" in probes:
        slots = tuple(sorted({n.key for n in needs}))
        ok = True
        for admitted in (tuple(result.recall.admitted), (), tuple(result.recall.admitted)[:1]):
            got = adapter.current_typed_slot_obstacles(slots, admitted, obs_ctx)
            ok = ok and got == census_oracle(sc, slots, set(admitted), obs_ctx)
        obs["census_matches_full_scan"] = ok
    if "restart_identical" in probes:
        first = canonical(report.to_dict())
        sc.apply({"op": "reopen"})
        planner2, ctx2, result2 = sc.recall(case)
        again = sc.governed(lambda: planner2.observe_persisted_typed_coverage(result2, ctx2, needs=needs))
        obs["restart_identical"] = canonical(again.to_dict()) == first
    values = [p.split(":", 1)[1] for p in probes if p.startswith("values_absent:")]
    if values:
        text = json.dumps(report.to_dict())
        obs["values_absent"] = not any(v in text for v in values)
    return obs


def observe_manual(case: Mapping, sc: Scenario) -> dict:
    needs = needs_of(case)
    planner, ctx, result = sc.recall(case)
    keys = tuple(n.key for n in needs)
    coverage = tuple(es.CoverageObservation(candidate_ref=sc.resolve(c["ref"]), need_keys=keys, origin=c["origin"])
                     for c in case["coverage"])
    report = result.observe_evidence_sufficiency(needs=needs, coverage=coverage)
    return report_observables(report, sc, needs)


def observe_pure(case: Mapping, sc: Scenario | None) -> dict:
    needs = tuple(es.CoverageNeed(need_key(n), n.get("min", 1)) for n in case["needs"])
    keys = tuple(n.key for n in needs)
    observation = es.SufficiencyObservation(
        admitted_refs=tuple(case["admitted"]), needs=needs,
        coverage=tuple(es.CoverageObservation(candidate_ref=c["ref"], need_keys=keys, origin=c["origin"])
                       for c in case.get("coverage", ())),
        route_work=tuple(es.RouteWorkObservation(**r) for r in case.get("route_work", ())))
    report = es.assess_sufficiency(observation)
    d = report.to_dict()
    return {"budget_bound_routes": d["budget_bound_routes"], "unexecuted_routes": d["unexecuted_routes"],
            "continuation_proposal": d["continuation_proposal"], "diagnosis": d["diagnosis"]}


def observe_forge_report(case: Mapping, sc: Scenario | None) -> dict:
    key = typed.typed_slot("Forge subject", "forge attribute")
    need = es.CoverageNeed(key)
    if case.get("with_unresolved_values"):
        observation = es.SufficiencyObservation(
            admitted_refs=("fact-a", "fact-b"), needs=(need,),
            coverage=tuple(es.CoverageObservation(candidate_ref=r, need_keys=(key,), origin=es.TYPED_OBSERVATION)
                           for r in ("fact-a", "fact-b")),
            typed_value_claims=(es.TypedValueClaim(candidate_ref="fact-a", need_key=key, value="one", cardinality="single", assertion="state"),
                                es.TypedValueClaim(candidate_ref="fact-b", need_key=key, value="two", cardinality="single", assertion="state")))
    else:
        observation = es.SufficiencyObservation(admitted_refs=("fact-a",), needs=(need,))
    report = es.assess_sufficiency(observation)
    dataclasses.replace(report, **{case["field"]: case["value"]})
    return {"constructed": True}


def observe_witness(case: Mapping, sc: Scenario) -> dict:
    ctx = context(case.get("observe_scope", SCOPE))
    refs = tuple(sc.resolve(x) for x in case["admitted"])
    adapter = sc.memory.runtime.adapter
    before = sc.state()
    witnesses = adapter.governed_applied_transition_witnesses(refs, ctx)
    after = sc.state()
    dicts = [w.to_dict() for w in witnesses]
    obs = {
        "witness_count": len(witnesses),
        "witness_statuses": [w.status for w in witnesses],
        "witnesses": [{"status": w.status, "source": sc.label(w.source_fact_ref), "prior": sc.label(w.prior_fact_ref),
                       "current": sc.label(w.current_target_fact_ref),
                       "proposal": "open_proposal" if w.proposal_ref == sc.open_proposal else w.proposal_ref}
                      for w in witnesses],
        "immediate_successor_verified_any": any(w.immediate_successor_verified for w in witnesses),
        "can_stop_any": any(w.can_stop for w in witnesses),
        "answer_quality_verified_any": any(w.answer_quality_verified for w in witnesses),
        "authority_effect_all_none": all(w.authority_effect == "none" for w in witnesses),
    }
    if "state_unchanged" in case.get("probes", ()):
        obs["state_unchanged"] = before == after
    if "text_absent" in case.get("probes", ()):
        blob = json.dumps(dicts)
        obs["text_absent"] = not any(t in blob for t in sc.texts)
    return obs


def observe_receipt(case: Mapping, sc: Scenario) -> dict:
    planner, ctx, result = sc.recall(case)
    receipt = result.observation_receipt
    obs = {"receipt_present": isinstance(receipt, rr.RecallObservationReceipt)}
    try:
        setattr(receipt, "can_stop", True)
        obs["receipt_assignment_refused"] = False
    except (dataclasses.FrozenInstanceError, AttributeError, TypeError):
        obs["receipt_assignment_refused"] = True
    public = receipt.to_dict() if obs["receipt_present"] else {}
    obs.update({"receipt_state_revision": public.get("state_revision"),
                "receipt_snapshot_attested": public.get("snapshot_attested"),
                "receipt_slot_closure_attested": public.get("slot_closure_attested"),
                "receipt_can_stop": public.get("can_stop")})
    refused = set(result.recall.refusals)
    obs["refused_identities_present"] = bool(refused)
    obs["refused_identities_disclosed"] = any(r in json.dumps(public) for r in refused)
    for mutation in case.get("mutations", ()):
        mutate(result, mutation, sc, ctx)
    obs["receipt_unchanged"], obs["verification_raised"] = safe_unchanged(result)
    return obs


def observe_forge_receipt(case: Mapping, sc: Scenario) -> dict:
    _, _, result = sc.recall(case)
    dataclasses.replace(result.observation_receipt, **{case["field"]: case["value"]})
    return {"constructed": True}


def observe_controller_authority(case: Mapping, sc: Scenario) -> dict:
    sc.recall(case, planner=sc.planner(case, controller=AuthorityClaimingController(case)))
    return {"recall_completed": True}


def twin_digest(case: Mapping, root: Path, observing: bool) -> str:
    sc = Scenario(root)
    log: list = []
    try:
        for op in case["setup"]:
            if op["op"] != "observe_all":
                sc.apply(op)
                continue
            planner, ctx, result = sc.recall(op)
            log.append(["planner", list(result.recall.candidates), list(result.recall.admitted),
                        list(result.recall.ranked_admitted), dict(result.recall.refusals)])
            if observing:
                needs = needs_of(op)
                keys = tuple(n.key for n in needs)
                sc.governed(lambda: planner.observe_persisted_typed_coverage(result, ctx, needs=needs))
                result.observe_evidence_sufficiency(needs=needs, coverage=tuple(
                    es.CoverageObservation(candidate_ref=r, need_keys=keys, origin=es.TYPED_OBSERVATION)
                    for r in result.recall.admitted[:1]))
                sc.governed(lambda: planner.observe_governed_transition_witnesses(result, ctx))
                result.observation_unchanged()
                result.observation_receipt.to_dict()
            else:
                # Harness correction H1: run_governed_read advances the durable recovery
                # generation on every call, even around a no-op (v6 behaviour). The plain twin
                # makes the same two wrapper calls so that only the observers differ.
                sc.governed(lambda: None)
                sc.governed(lambda: None)
        m = sc.memory
        query = next(op["query"] for op in case["setup"] if op["op"] == "observe_all")
        log.append(["recall", m.recall(query)])
        for label in sorted(sc.labels):
            if not label.startswith("b:") and "@" not in label:
                log.append(["history", label, m.history(label)])
        log.append(["proposals", m.semantic_proposals()])
        log.append(["posture", m.posture()])
        substrate = m.runtime.adapter.checkpoint_substrate()
        log.append(["facts", [dataclasses.asdict(f) for f in substrate.all_facts()]])
        log.append(["events", m.runtime.adapter.events])
        log.append(["state_digest", substrate.state_digest()])
    finally:
        sc.close()
    text = json.dumps(log, sort_keys=True, default=str)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?", "<ts>", text)
    text = re.sub(r'"elapsed_ms": [0-9.e-]+', '"elapsed_ms": 0', text)
    text = text.replace(str(root), "<root>")
    return sha256_bytes(text.encode())


def observe_twin(case: Mapping, workdir: Path) -> dict:
    a = twin_digest(case, workdir / "twin-observing", True)
    b = twin_digest(case, workdir / "twin-plain", False)
    return {"twin_identical": a == b, "twin_digest_observing": a, "twin_digest_plain": b}


KINDS = {"coverage": observe_coverage, "manual_coverage": observe_manual, "witness": observe_witness,
         "receipt": observe_receipt, "forge_receipt": observe_forge_receipt,
         "controller_authority": observe_controller_authority}
PURE_KINDS = {"pure_assess": observe_pure, "forge_report": observe_forge_report}


# ------------------------------------------------------------------------------- evaluation

def match(matcher: Mapping, value) -> bool:
    (op, expected), = matcher.items()
    if op == "eq":
        return value == expected
    if op == "ne":
        return value != expected
    if op == "in":
        return value in expected
    if op == "not_in":
        return value not in expected
    raise ReplayError(f"unknown matcher {op}")


def run_case(case: Mapping, workdir: Path) -> dict:
    kind = case["kind"]
    obs: dict
    error = None
    raised = None
    if kind == "twin":
        obs = observe_twin(case, workdir)
    elif kind in PURE_KINDS:
        try:
            obs = PURE_KINDS[kind](case, None)
        except ReplayError as exc:
            error = f"scenario error: {exc}"
            obs = {}
        except Exception as exc:  # noqa: BLE001 - an expected refusal is an observation
            raised = exc
            obs = {}
    else:
        sc = Scenario(workdir / "store")
        try:
            try:
                for op in case.get("setup", ()):
                    sc.apply(op)
            except Exception as exc:  # noqa: BLE001
                error = f"setup failed: {type(exc).__name__}: {exc}"
                obs = {}
            else:
                try:
                    obs = KINDS[kind](case, sc)
                except ReplayError as exc:
                    error = f"scenario error: {exc}"
                    obs = {}
                except Exception as exc:  # noqa: BLE001 - an expected refusal is an observation
                    raised = exc
                    obs = {}
        finally:
            try:
                sc.close()
            except Exception:  # noqa: BLE001
                pass
    if raised is not None:
        obs = {"raises": type(raised).__name__, "raises_any": True, "raised_message": str(raised)[:200]}
    elif error is None:
        obs.setdefault("raises", None)
        obs.setdefault("raises_any", False)
    checks = []
    if error is None:
        for key, matcher in case["expect"].items():
            value = obs.get(key, "<absent>")
            checks.append({"observable": key, "matcher": matcher, "observed": value, "holds": match(matcher, value)})
    recorded = {k: obs.get(k) for k in case.get("record", ())}
    outcome = "error" if error else ("pass" if all(c["holds"] for c in checks) else "fail")
    return {"id": case["id"], "invariants": case["invariants"], "kind": kind, "outcome": outcome,
            "error": error, "checks": checks, "recorded": recorded,
            "observations": {k: v for k, v in obs.items() if not k.startswith("twin_digest")}}


# ------------------------------------------------------------------------------- provenance

def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def provenance(fixture_path: Path) -> dict:
    status = [line for line in git("status", "--porcelain", "--untracked-files=all").splitlines()
              if line[3:].strip('"') and not line[3:].strip('"').startswith(OUTPUT_REL)]
    return {
        "source_commit": git("rev-parse", "HEAD"),
        "runtime_tree": git("rev-parse", "HEAD:reference/agentmem_ref"),
        "dirty_paths": sorted(line[3:] for line in status),
        "dirty_exclusion": OUTPUT_REL,
        "fixture": {"path": (str(fixture_path.resolve().relative_to(ROOT)) if fixture_path.resolve().is_relative_to(ROOT)
                             else str(fixture_path.resolve())), "sha256": sha256_file(fixture_path)},
        "runner": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve()),
                   "version": RUNNER_VERSION},
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "platform": platform.platform(),
    }


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    fixture_path = fixture_dir / f"{replay_id}.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("replay_id") != replay_id or fixture.get("dsl_version") != DSL_VERSION:
        raise ValueError("fixture identity or DSL version mismatch")
    prov = provenance(fixture_path)
    cases = []
    with tempfile.TemporaryDirectory(prefix="v7-replay-") as tmp:
        for i, case in enumerate(fixture["cases"]):
            workdir = Path(tmp) / f"case-{i:03d}"
            workdir.mkdir()
            cases.append(run_case(case, workdir))
    failed = [c["id"] for c in cases if c["outcome"] != "pass"]
    reasons = []
    if failed:
        verdict = "FAIL"
        reasons.append(f"{len(failed)} case(s) did not pass: {', '.join(failed)}")
    elif prov["dirty_paths"] and not allow_dirty:
        verdict = "BLOCKED"
        reasons.append("source tree is dirty outside the evidence directory")
    elif prov["dirty_paths"]:
        verdict = "BLOCKED"
        reasons.append("--allow-dirty: development run, not evidence")
    else:
        verdict = "PASS"
        reasons.append("every expectation held on a clean source tree")
    invariants = {inv["id"]: {"statement": inv["statement"], "cases": [], "holds": True} for inv in fixture["invariants"]}
    for c in cases:
        for inv in c["invariants"]:
            invariants[inv]["cases"].append(c["id"])
            invariants[inv]["holds"] = invariants[inv]["holds"] and c["outcome"] == "pass"
    observations_sha256 = sha256_bytes(canonical([{k: c[k] for k in ("id", "outcome", "checks", "recorded", "observations")}
                                                  for c in cases]))
    return {
        "schema": "644-v7-replay-report/1", "replay_id": replay_id, "dsl_version": DSL_VERSION,
        "verdict": verdict, "verdict_reasons": reasons,
        "summary": {"cases": len(cases), "passed": sum(c["outcome"] == "pass" for c in cases),
                    "failed": sum(c["outcome"] == "fail" for c in cases),
                    "errors": sum(c["outcome"] == "error" for c in cases)},
        "invariants": invariants, "cases": cases, "observations_sha256": observations_sha256,
        "provenance": prov,
        "authority_boundary": ("A replay verdict is evidence for independent review. It is not v7 acceptance, not "
                               "publication, and not stop authority. sha256 values are integrity bindings, not signatures."),
    }


def write_outputs(report: dict, output_dir: Path, command: str) -> dict:
    target = output_dir / report["replay_id"]
    target.mkdir(parents=True, exist_ok=True)
    report_bytes = json.dumps(report, indent=1, sort_keys=True, default=str).encode() + b"\n"
    (target / "report.json").write_bytes(report_bytes)
    manifest = {
        "schema": "644-v7-replay-manifest/1", "replay_id": report["replay_id"], "verdict": report["verdict"],
        "fixture": report["provenance"]["fixture"], "runner": report["provenance"]["runner"],
        "report": {"path": "report.json", "sha256": sha256_bytes(report_bytes)},
        "observations_sha256": report["observations_sha256"],
        "source_commit": report["provenance"]["source_commit"], "runtime_tree": report["provenance"]["runtime_tree"],
        "command": command,
        "attestation": "none: hashes bind contents for review; they are not signatures and confer no acceptance",
    }
    (target / "manifest.json").write_bytes(json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--replay", choices=REPLAYS)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--allow-dirty", action="store_true", help="development only; the verdict is then BLOCKED")
    args = parser.parse_args(argv)
    replays = REPLAYS if args.all else (args.replay,)
    command = "python reference/run_644_v7_replays.py " + ("--all" if args.all else f"--replay {args.replay}")
    worst = 0
    for replay_id in replays:
        report = run_replay(replay_id, fixture_dir=args.fixture_dir, allow_dirty=args.allow_dirty)
        manifest = write_outputs(report, args.output_dir, command)
        s = report["summary"]
        print(f"{replay_id}: {report['verdict']} ({s['passed']}/{s['cases']} cases) report sha256 {manifest['report']['sha256']}")
        for reason in report["verdict_reasons"]:
            print(f"  - {reason}")
        worst = max(worst, {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["verdict"]])
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
