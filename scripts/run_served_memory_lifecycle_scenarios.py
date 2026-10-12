#!/usr/bin/env python3
"""#771 v2: replay a memory LIFECYCLE through governance, then emit served IDs.

The v1 runner can only ``retain``: nothing is ever corrected, deleted, scoped
to another tenant or declared time-bounded, so every "stale" label is a gold
annotation the runtime cannot act on. v2 inputs are an ordered event history:

  retain   new logical memory (optionally another project or tenant,
           optionally with caller-declared valid_from/valid_until)
  correct  governed ERROR correction: the previous value was wrong
           (runtime replacement_kind=error_correction; never historical evidence)
  update   governed STATE CHANGE: the previous value was true until now
           (runtime replacement_kind=state_change; admissible as history)
  delete   governed permanent deletion of a logical memory's current value

Corrections and deletions are executed through the real PAMA proposal path.
The host adjudication corpus (``TransitionRule``) is derived from the declared
event history BEFORE the runtime is created: it records that the history's
transitions were sanctioned, exactly as a host would configure verifier
trust. It never contains queries, relevance, expected answers or gold.

Inputs contain events and questions ONLY. Gold is scored afterwards by
``qualify_served_memory_run.py``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "reference"))

from run_served_memory_scenarios import (  # noqa: E402
    CONFIG, INTENTS, _name, _proposal, _text, _verified_revision,
)
from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import GovernedMemoryAdapter, RecallContext  # noqa: E402
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime  # noqa: E402
from agentmem_ref.runtime_config import validate_runtime_configuration  # noqa: E402
from agentmem_ref.verification import (  # noqa: E402
    TRANSITION_VERIFIER, TransitionRule, TransitionRuleCorpus, VerifierRegistry,
)

SCHEMA = "served-memory-lifecycle-v2"
OPS = frozenset(("retain", "correct", "update", "delete"))
_REPLACES = ("correct", "update")
_TEMPORAL = frozenset(("valid_from", "valid_until"))


def _memory_ref(memory: str) -> str:
    return "memory:quality:" + memory


def validate_inputs(data):
    """Closed shape; lifecycle consistency is checked before any write."""
    if type(data) is not dict or set(data) != {
        "schema", "tenant", "project", "purpose", "events", "queries",
    } or data["schema"] != SCHEMA:
        raise ValueError("invalid lifecycle execution schema; gold cannot be passed")
    _name(data["tenant"], "tenant")
    _name(data["project"], "project")
    _text(data["purpose"], "purpose")
    events, queries = data["events"], data["queries"]
    if type(events) is not list or not 1 <= len(events) <= 2000:
        raise ValueError("events must be a bounded nonempty list")
    if type(queries) is not list or not 1 <= len(queries) <= 500:
        raise ValueError("queries must be a bounded nonempty list")
    seen: set[str] = set()
    live: dict[str, dict] = {}       # memory -> scope of its current value
    ever: set[str] = set()
    for event in events:
        if type(event) is not dict or not {"id", "op", "memory"} <= set(event):
            raise ValueError("event requires id, op and memory")
        allowed = {"id", "op", "memory", "text", "project", "tenant", "temporal"}
        if set(event) - allowed:
            raise ValueError("unknown event field; gold cannot be passed")
        _name(event["id"], "event id")
        _name(event["memory"], "memory")
        if event["id"] in seen:
            raise ValueError("duplicate event id")
        seen.add(event["id"])
        op = event["op"]
        if op not in OPS:
            raise ValueError("unsupported lifecycle operation")
        if "temporal" in event:
            temporal = event["temporal"]
            if (type(temporal) is not dict or not temporal or set(temporal) - _TEMPORAL
                    or any(type(v) is not str or not v for v in temporal.values())):
                raise ValueError("temporal must declare valid_from/valid_until strings")
        if op == "retain":
            if event["memory"] in ever:
                raise ValueError("retain must introduce a new logical memory")
            _text(event.get("text"), "event text")
            _name(event.get("project", data["project"]), "event project")
            _name(event.get("tenant", data["tenant"]), "event tenant")
            ever.add(event["memory"])
            live[event["memory"]] = {
                "project": event.get("project", data["project"]),
                "tenant": event.get("tenant", data["tenant"]),
            }
        else:
            if event["memory"] not in live:
                raise ValueError(op + " requires a live logical memory")
            if set(event) & {"project", "tenant"}:
                raise ValueError(op + " cannot move a memory's scope")
            if live[event["memory"]]["tenant"] != data["tenant"]:
                raise ValueError("lifecycle changes are evaluated for the home tenant only")
            if op in _REPLACES:
                _text(event.get("text"), "event text")
            else:
                if "text" in event or "temporal" in event:
                    raise ValueError("delete carries no text or temporal declaration")
                del live[event["memory"]]
    qseen: set[str] = set()
    for q in queries:
        if type(q) is not dict or set(q) != {"id", "query", "intent", "budget"}:
            raise ValueError("invalid query shape")
        _name(q["id"], "query id")
        _text(q["query"], "query")
        if q["intent"] not in INTENTS:
            raise ValueError("unsupported temporal intent")
        if type(q["budget"]) is not int or not 1 <= q["budget"] <= 100:
            raise ValueError("return budget must be integer 1..100")
        if q["id"] in qseen:
            raise ValueError("duplicate query id")
        qseen.add(q["id"])
    return data


def canonical_input_digest(data: dict) -> str:
    validate_inputs(data)
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def lifecycle_facts(data: dict) -> dict:
    """Derive which fact-creating events end up superseded, deleted or foreign.

    Pure function of the execution inputs. The qualifier uses it to refuse
    gold that, e.g., does not prohibit a deleted memory.
    """
    validate_inputs(data)
    current: dict[str, str] = {}
    versions: dict[str, list[str]] = {}
    creators: dict[str, dict] = {}
    deleted_memories: set[str] = set()
    for event in data["events"]:
        memory = event["memory"]
        if event["op"] in ("retain", *_REPLACES):
            scope = creators[current[memory]] if event["op"] in _REPLACES else {
                "project": event.get("project", data["project"]),
                "tenant": event.get("tenant", data["tenant"]),
            }
            creators[event["id"]] = {"project": scope["project"], "tenant": scope["tenant"],
                                     "memory": memory}
            versions.setdefault(memory, []).append(event["id"])
            current[memory] = event["id"]
        else:
            deleted_memories.add(memory)
            del current[memory]
    superseded = {fid for memory, ids in versions.items() for fid in ids[:-1]}
    deleted = {fid for memory in deleted_memories for fid in versions[memory]}
    foreign = {fid for fid, scope in creators.items()
               if scope["tenant"] != data["tenant"] or scope["project"] != data["project"]}
    return {
        "fact_ids": sorted(creators),
        "superseded": sorted(superseded - deleted),
        "deleted": sorted(deleted),
        "out_of_scope": sorted(foreign),
    }


def _host_corpora(data: dict) -> dict[str, TransitionRuleCorpus]:
    """One single-rule corpus per transition event.

    TransitionRuleCorpus keys rules by (target, criterion), so one corpus can
    adjudicate only ONE correction per memory; a value corrected repeatedly
    (13 -> 15 -> 16) needs a rule per step.
    """
    corpora: dict[str, TransitionRuleCorpus] = {}
    value: dict[str, str] = {}
    for event in data["events"]:
        target = _memory_ref(event["memory"])
        if event["op"] == "retain":
            value[event["memory"]] = event["text"]
        elif event["op"] in _REPLACES:
            corpora[event["id"]] = TransitionRuleCorpus((TransitionRule(
                rule_id="rule:" + event["id"], target_reference=target,
                criterion="value-correction", from_state=value[event["memory"]],
                permitted_to_values=(event["text"],)),))
            value[event["memory"]] = event["text"]
        else:
            corpora[event["id"]] = TransitionRuleCorpus((TransitionRule(
                rule_id="rule:" + event["id"], target_reference=target,
                criterion="permanent-deletion", from_state="current",
                permitted_to_values=("deleted",)),))
    return corpora


def _host_registry(corpora: dict[str, TransitionRuleCorpus]) -> VerifierRegistry:
    verifiers = [corpus.verifier() for corpus in corpora.values()]
    registry = VerifierRegistry()
    registry.register(TRANSITION_VERIFIER, lambda item: any(v(item) for v in verifiers))
    return registry


def _event_proposal(data, event, memory_scope, *, op, version=0):
    base = _proposal(memory_scope["tenant"], memory_scope["project"], event["memory"], data["purpose"])
    base = replace(base, proposal_id="proposal:quality:" + event["id"],
                   evidence_refs=("evidence:quality:" + event["id"],))
    if op == "retain":
        return base
    common = dict(review_satisfied=True, approval_refs=("approval:quality-history",),
                  state_snapshot=f"v{version}")
    if op in _REPLACES:
        return replace(base, operation="correction", **common)
    return replace(base, operation="permanent_deletion", reversibility="irreversible", **common)


def run_scenarios(data, root: Path, *, revision: str, lane_id: str,
                  backend: str = "composed-multiroute"):
    validate_inputs(data)
    _text(revision, "revision")
    _name(lane_id, "lane id")
    if backend not in ("composed-multiroute", "governed-lexical"):
        raise ValueError("unsupported governed reference backend")
    root = Path(root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("evaluation requires an empty isolated store; replay would mix corpora")
    corpora = _host_corpora(data)
    registry = _host_registry(corpora)
    runtime = ConfiguredCompositionRuntime.create(
        root, tenant=data["tenant"], verifier_registry=registry,
        plan=validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8"))),
    )
    foreign_adapters: dict[str, GovernedMemoryAdapter] = {}
    labels: dict[str, str] = {}
    scope_of: dict[str, dict] = {}
    value: dict[str, str] = {}
    version: dict[str, int] = {}
    for event in data["events"]:
        memory, op = event["memory"], event["op"]
        temporal = event.get("temporal")
        if op == "retain":
            scope = {"tenant": event.get("tenant", data["tenant"]),
                     "project": event.get("project", data["project"])}
            scope_of[memory] = scope
            proposal = _event_proposal(data, event, scope, op="retain")
            if scope["tenant"] == data["tenant"]:
                outcome = runtime.retain(proposal, event["text"], temporal=temporal)
            else:
                adapter = foreign_adapters.setdefault(scope["tenant"], GovernedMemoryAdapter(
                    runtime.adapter.checkpoint_substrate(), tenant=scope["tenant"]))
                outcome = adapter.commit_proposal(proposal, event["text"], temporal=temporal)
            version[memory] = 1
        else:
            evidence = corpora[event["id"]].evidence_for(
                target_reference=_memory_ref(memory),
                criterion="value-correction" if op in _REPLACES else "permanent-deletion",
                pre_state=value[memory] if op in _REPLACES else "current",
                proposed_value=event["text"] if op in _REPLACES else "deleted",
            )
            proposal = _event_proposal(data, event, scope_of[memory], op=op, version=version[memory])
            if op in _REPLACES:
                outcome = runtime.correct(
                    proposal, event["text"], evidence=evidence, temporal=temporal,
                    replacement_kind="state_change" if op == "update" else "error_correction")
                version[memory] += 1
            else:
                outcome = runtime.delete_current(proposal, evidence=evidence)
        if not outcome.committed:
            raise RuntimeError(f"governed {op} failed for event {event['id']}")
        if op in ("retain", *_REPLACES):
            if type(outcome.fact_uuid) is not str or outcome.fact_uuid in labels:
                raise RuntimeError("missing or duplicate persisted fact identity")
            labels[outcome.fact_uuid] = event["id"]
            value[memory] = event["text"]

    context = RecallContext(
        target_domain_refs=(data["tenant"], data["project"]),
        principal_ref="agent:quality-evaluation",
        project_ref=data["project"],
        purpose=data["purpose"],
    )
    rows, diagnostics = [], []
    for q in data["queries"]:
        if backend == "composed-multiroute":
            declared_mode = {"current": "current", "historical": "historical",
                             "timeless": "atemporal_or_unspecified"}[q["intent"]]
            result = runtime.multi_route_recall(q["query"], context,
                                                temporal_intent={"mode": declared_mode})
            if result.query_temporal_intent.get("mode") != declared_mode:
                raise RuntimeError("composed recall did not honor declared temporal intent")
            ranked = result.ranked_admitted
        else:
            result = runtime.recall(q["query"], context)
            ranked = result.admitted
        if len(ranked) != len(set(ranked)) or not set(ranked).issubset(result.admitted):
            raise RuntimeError("ranking violates governed admission")
        if any(ref not in labels for ref in ranked):
            raise RuntimeError("unmapped governed result ID; refuse silent omissions")
        returned = ranked[:q["budget"]]
        rows.append({"id": q["id"], "returned": [labels[ref] for ref in returned]})
        # Diagnostic only (never scored): what ranked admission held beyond
        # the served budget, so "relevant but too late" is observable.
        diagnostics.append({"id": q["id"], "ranked_admitted_count": len(ranked),
                            "beyond_budget": [labels[ref] for ref in ranked[q["budget"]:]]})
    run = {
        "schema": "served-memory-run-v1",
        "runtime_revision": revision,
        "lane_id": lane_id,
        "execution_backend": backend,
        "input_sha256": canonical_input_digest(data),
        "rows": rows,
    }
    return run, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--lane-id", default="reference-lifecycle-v2")
    parser.add_argument("--backend", choices=("composed-multiroute", "governed-lexical"),
                        default="composed-multiroute")
    args = parser.parse_args()
    if args.output.exists() or args.store.exists():
        parser.error("output and store paths must not preexist")
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    validate_inputs(data)
    sha = _verified_revision()
    run, diagnostics = run_scenarios(data, args.store, revision=sha,
                                     lane_id=args.lane_id, backend=args.backend)
    args.output.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.diagnostics:
        args.diagnostics.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")


if __name__ == "__main__":
    main()
