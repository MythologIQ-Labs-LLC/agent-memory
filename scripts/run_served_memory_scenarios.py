#!/usr/bin/env python3
"""#771: execute governed reference composition and emit returned source IDs.

Inputs contain writes and questions ONLY, never relevance labels or answer keys.
The scorer consumes separately held gold after this process has finished.
This runner takes ranked-admitted facts at an evaluation-defined return budget;
it does not certify delivery by a downstream answering application.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import RecallContext  # noqa: E402
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime  # noqa: E402
from agentmem_ref.runtime_config import validate_runtime_configuration  # noqa: E402

SCHEMA = "served-memory-execution-v1"
CONFIG = ROOT / "reference/fixtures/runtime-configuration/reference-composed-runtime.json"
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
INTENTS = frozenset(("current", "historical", "timeless"))


def _name(value, name):
    if type(value) is not str or not LABEL.fullmatch(value):
        raise ValueError(name + " must be a bounded opaque identifier")
    return value


def _text(value, name):
    if type(value) is not str or not value.strip() or len(value) > 16384:
        raise ValueError(name + " must be nonempty bounded text")
    return value


def validate_inputs(data):
    """Reject gold-label injection and invalid identities before any writes."""
    if type(data) is not dict or set(data) != {
        "schema", "tenant", "project", "purpose", "writes", "queries",
    } or data["schema"] != SCHEMA:
        raise ValueError("invalid execution schema; gold cannot be passed")
    _name(data["tenant"], "tenant")
    _name(data["project"], "project")
    _text(data["purpose"], "purpose")
    writes, queries = data["writes"], data["queries"]
    if type(writes) is not list or not 1 <= len(writes) <= 500:
        raise ValueError("writes must be a bounded nonempty list")
    if type(queries) is not list or not 1 <= len(queries) <= 500:
        raise ValueError("queries must be a bounded nonempty list")
    seen = set()
    for w in writes:
        if type(w) is not dict or set(w) != {"id", "text", "project"}:
            raise ValueError("invalid write shape")
        _name(w["id"], "write id")
        _text(w["text"], "write text")
        _name(w["project"], "write project")
        if w["id"] in seen:
            raise ValueError("duplicate write id")
        seen.add(w["id"])
    seen = set()
    for q in queries:
        if type(q) is not dict or set(q) != {"id", "query", "intent", "budget"}:
            raise ValueError("invalid query shape")
        _name(q["id"], "query id")
        _text(q["query"], "query")
        if q["intent"] not in INTENTS:
            raise ValueError("unsupported temporal intent")
        if type(q["budget"]) is not int or not 1 <= q["budget"] <= 100:
            raise ValueError("return budget must be integer 1..100")
        if q["id"] in seen:
            raise ValueError("duplicate query id")
        seen.add(q["id"])
    return data


def _proposal(tenant, project, label, purpose):
    return policy.Proposal(
        proposal_id="proposal:quality:" + label,
        actor_id="agent:quality-evaluation",
        charter_version="charter-v1",
        target_reference="memory:quality:" + label,
        target_class=policy.M2,
        scope=tenant,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:quality:" + label,),
        tenant_ref=tenant,
        isolation_domain_refs=(tenant, project),
        required_isolation_domain_refs=(project,),
        project_ref=project,
        purpose=purpose,
    )


def run_scenarios(data, root: Path, *, revision: str, lane_id: str,
                  backend: str = "composed-multiroute"):
    """Real governed commits and recall; revision is a label until CLI verifies it."""
    validate_inputs(data)
    _text(revision, "revision")
    _name(lane_id, "lane id")
    if backend not in ("composed-multiroute", "governed-lexical"):
        raise ValueError("unsupported governed reference backend")
    runtime = ConfiguredCompositionRuntime.create(
        root, tenant=data["tenant"],
        plan=validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8"))),
    )
    labels = {}
    for w in data["writes"]:
        outcome = runtime.retain(
            _proposal(data["tenant"], w["project"], w["id"], data["purpose"]),
            w["text"],
        )
        if not outcome.committed or type(outcome.fact_uuid) is not str:
            raise RuntimeError("governed retain failed for opaque label " + w["id"])
        if outcome.fact_uuid in labels:
            raise RuntimeError("duplicate persisted fact identity")
        labels[outcome.fact_uuid] = w["id"]

    context = RecallContext(
        target_domain_refs=(data["tenant"], data["project"]),
        principal_ref="agent:quality-evaluation",
        project_ref=data["project"],
        purpose=data["purpose"],
    )
    rows = []
    for q in data["queries"]:
        if backend == "composed-multiroute":
            # This is the caller's declared temporal QUESTION, not a gold
            # currentness answer. It must reach the real applicability policy.
            declared_mode = {
                "current": "current",
                "historical": "historical",
                "timeless": "atemporal_or_unspecified",
            }[q["intent"]]
            result = runtime.multi_route_recall(
                q["query"], context, temporal_intent={"mode": declared_mode},
            )
            if result.query_temporal_intent.get("mode") != declared_mode:
                raise RuntimeError("composed recall did not honor declared temporal intent")
            if result.authority_effect != "none":
                raise RuntimeError("composed recall claimed authority")
            ranked = result.ranked_admitted
        else:
            # The baseline governed adapter admits canonical lexical results
            # in retrieval order, without multi-route ranking/currentness.
            # This is a separate diagnostic protocol, not interchangeable
            # with as-of historical or vector-enabled retrieval.
            result = runtime.recall(q["query"], context)
            ranked = result.admitted
        if (len(ranked) != len(set(ranked))
                or not set(ranked).issubset(result.admitted)):
            raise RuntimeError("ranking violates governed admission")
        returned = ranked[:q["budget"]]
        if any(ref not in labels for ref in returned):
            raise RuntimeError("unmapped governed result ID; refuse silent omissions")
        rows.append({"id": q["id"], "returned": [labels[ref] for ref in returned]})
    return {
        "schema": "served-memory-run-v1",
        "runtime_revision": revision,
        "lane_id": lane_id,
        "rows": rows,
    }


def _verified_revision():
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("cannot verify exact source revision") from exc
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or dirty:
        raise RuntimeError("execution requires clean exact git HEAD")
    return revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--lane-id", default="reference-governed-recall-v1")
    parser.add_argument("--backend", choices=("composed-multiroute", "governed-lexical"),
                        default="composed-multiroute")
    args = parser.parse_args()
    if args.output.exists() or args.store.exists():
        parser.error("output and store paths must not preexist")
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    validate_inputs(data)
    sha = _verified_revision()
    result = run_scenarios(data, args.store, revision=sha,
                           lane_id=args.lane_id, backend=args.backend)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
