"""Immutable, non-authoritative observation of one controlled recall (#644).

Capture happens inside the planner BEFORE a mutable result reaches the caller.
This is deterministic change detection, NOT a signed attestation, atomic read,
trusted database revision, complete-index proof or stopping authorization.
Query and reader fingerprints are NOT secrecy-preserving against guessing.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

VERSION = "recall-observation-v1"
_DOMAIN = b"agent-memory/recall-observation/v1\x00"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _ids(items: tuple[str, ...], name: str) -> None:
    if type(items) is not tuple or len(set(items)) != len(items):
        raise ValueError(f"{name} requires unique immutable identities")
    if any(type(item) is not str or not item or len(item) > 512 or
           any(ord(c) < 32 or ord(c) == 127 for c in item) for item in items):
        raise ValueError(f"{name} has invalid identity")


def _binding_digest(domain: bytes, payload: object) -> str:
    """Internal deterministic binding; no authentication or secrecy promise."""
    return _sha(domain + _json_bytes(payload))


def _admission_binding(
    *, query: str, policy_version: str, admission_mode: str,
    evaluated_at: str, refusals: Mapping[str, str],
) -> str:
    if not all(type(value) is str for value in
               (query, policy_version, admission_mode, evaluated_at)):
        raise ValueError("admission binding fields must be strings")
    if not isinstance(refusals, Mapping) or any(
        type(k) is not str or type(v) is not str for k, v in refusals.items()
    ):
        raise ValueError("refusals must be a mapping of string identities to reasons")
    return _binding_digest(b"agent-memory/recall-admission-binding/v1\x00", {
        "query": query,
        "policy": policy_version,
        "mode": admission_mode,
        "evaluated_at": evaluated_at,
        "refusals": dict(refusals),
    })


def _hex_digest(value: str) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


@dataclass(frozen=True, slots=True)
class RouteObservation:
    route_id: str
    candidate_limit: int
    anchor_limit: int
    returned_count: int
    executed: bool

    def __post_init__(self) -> None:
        _ids((self.route_id,), "route id")
        if any(type(v) is not int or v < 0 for v in
               (self.candidate_limit, self.anchor_limit, self.returned_count)):
            raise ValueError("route observations require nonnegative integer counters")
        if type(self.executed) is not bool:
            raise ValueError("executed must be a boolean")
        if self.returned_count > self.candidate_limit:
            raise ValueError("route returned more than its budget")
        if (self.executed != (self.candidate_limit > 0)
                or (not self.executed and self.returned_count)):
            raise ValueError("route execution must match the captured budget")


@dataclass(frozen=True, slots=True)
class RecallObservationReceipt:
    """Content-committed snapshot. Caller cannot turn it into authority."""

    query_digest: str
    reader_digest: str
    controller_ref: str
    admission_policy: str
    admission_mode: str
    evaluated_at: str
    candidate_refs: tuple[str, ...]
    admitted_refs: tuple[str, ...]
    ranked_refs: tuple[str, ...]
    routes: tuple[RouteObservation, ...]
    observed_route_counts: tuple[tuple[str, int], ...]
    control_digest: str
    admission_digest: str
    content_digest: str
    version: str = VERSION
    state_revision: None = None
    snapshot_attested: bool = False
    slot_closure_attested: bool = False
    can_stop: bool = False
    authority_effect: str = "none"

    def _payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "query_digest": self.query_digest,
            "reader_digest": self.reader_digest,
            "controller_ref": self.controller_ref,
            "admission_policy": self.admission_policy,
            "admission_mode": self.admission_mode,
            "evaluated_at": self.evaluated_at,
            "candidate_refs": list(self.candidate_refs),
            "admitted_refs": list(self.admitted_refs),
            "ranked_refs": list(self.ranked_refs),
            "routes": [
                {"id": r.route_id, "candidate_limit": r.candidate_limit,
                 "anchor_limit": r.anchor_limit, "returned_count": r.returned_count,
                 "executed": r.executed}
                for r in self.routes
            ],
            "observed_route_counts": [list(pair) for pair in self.observed_route_counts],
            "control_digest": self.control_digest,
            "admission_digest": self.admission_digest,
        }

    def __post_init__(self) -> None:
        if (self.version != VERSION or self.state_revision is not None
                or self.snapshot_attested is not False
                or self.slot_closure_attested is not False
                or self.can_stop is not False
                or self.authority_effect != "none"):
            raise ValueError("receipt cannot claim revision, closure or authority")
        if not all(_hex_digest(value) for value in (
            self.query_digest, self.reader_digest,
            self.control_digest, self.admission_digest,
        )):
            raise ValueError("invalid receipt query, reader, plan or admission binding")
        for key in (self.controller_ref, self.admission_policy,
                    self.admission_mode, self.evaluated_at):
            if type(key) is not str:
                raise ValueError("receipt metadata must be strings")
        for name, values in (
            ("candidate refs", self.candidate_refs),
            ("admitted refs", self.admitted_refs),
            ("ranked refs", self.ranked_refs),
        ):
            _ids(values, name)
        if (not set(self.admitted_refs).issubset(self.candidate_refs)
                or not set(self.ranked_refs).issubset(self.admitted_refs)
                or len(self.ranked_refs) != len(self.admitted_refs)):
            raise ValueError("invalid governed candidate/admission/ranking membership")
        if (type(self.routes) is not tuple
                or any(type(r) is not RouteObservation for r in self.routes)):
            raise ValueError("route observations must be an immutable typed tuple")
        _ids(tuple(r.route_id for r in self.routes), "route identities")
        if (type(self.observed_route_counts) is not tuple
                or any(type(x) is not tuple or len(x) != 2
                       or type(x[0]) is not str or not x[0]
                       or type(x[1]) is not int or x[1] < 0
                       for x in self.observed_route_counts)):
            raise ValueError("observed route counts must be immutable nonnegative pairs")
        _ids(tuple(key for key, _ in self.observed_route_counts), "observed routes")
        observed = dict(self.observed_route_counts)
        if any(observed.get(r.route_id) != r.returned_count for r in self.routes):
            raise ValueError("route work and observed counters disagree")
        if not _hex_digest(self.content_digest) or not self.integrity_valid():
            raise ValueError("receipt digest does not match its immutable contents")

    def integrity_valid(self) -> bool:
        return self.content_digest == _sha(_DOMAIN + _json_bytes(self._payload()))

    def matches_mutable_result(
        self, *,
        candidates: list[str], admitted: list[str], ranked: list[str],
        route_counts: Mapping[str, int], routes_executed: tuple[str, ...],
        query: str, plan: Mapping[str, object], refusals: Mapping[str, str],
        policy_version: str, admission_mode: str, evaluated_at: str,
    ) -> bool:
        """Detect post-capture edits, not prove capture trust or query coverage."""
        try:
            control_digest = _binding_digest(
                b"agent-memory/recall-control-binding/v1\x00", plan
            )
            admission_digest = _admission_binding(
                query=query, policy_version=policy_version,
                admission_mode=admission_mode, evaluated_at=evaluated_at,
                refusals=refusals,
            )
        except (TypeError, ValueError, OverflowError):
            return False
        return (
            control_digest == self.control_digest
            and admission_digest == self.admission_digest
            and tuple(candidates) == self.candidate_refs
            and tuple(admitted) == self.admitted_refs
            and tuple(ranked) == self.ranked_refs
            and tuple(routes_executed) ==
                tuple(r.route_id for r in self.routes if r.executed)
            and tuple(sorted(route_counts.items())) == self.observed_route_counts
            and self.integrity_valid()
        )

    def to_dict(self) -> dict[str, object]:
        """Disclose admitted refs, not refused/hidden candidate identities."""
        return {
            "version": VERSION,
            "content_digest": self.content_digest,
            "query_digest": self.query_digest,
            "reader_digest": self.reader_digest,
            "candidate_count": len(self.candidate_refs),
            "admitted_refs": list(self.admitted_refs),
            "ranked_refs": list(self.ranked_refs),
            "routes": [
                {"route_id": r.route_id, "candidate_limit": r.candidate_limit,
                 "anchor_limit": r.anchor_limit, "returned_count": r.returned_count,
                 "executed": r.executed}
                for r in self.routes
            ],
            "observed_route_counts": [list(pair) for pair in self.observed_route_counts],
            "state_revision": None,
            "snapshot_attested": False,
            "slot_closure_attested": False,
            "can_stop": False,
            "authority_effect": "none",
        }


def capture_recall_observation(
    *,
    query: str,
    reader_domain_refs: tuple[str, ...],
    principal_ref: str,
    project_ref: str,
    purpose: str,
    task_ref: str,
    controller_ref: str,
    admission_policy: str,
    admission_mode: str,
    evaluated_at: str,
    candidates: list[str],
    admitted: list[str],
    ranked: list[str],
    route_observations: tuple[RouteObservation, ...],
    observed_route_counts: Mapping[str, int],
    plan: Mapping[str, object],
    refusals: Mapping[str, str],
) -> RecallObservationReceipt:
    """Copy mutable runtime outputs into a frozen diagnostic record."""
    if type(query) is not str:
        raise ValueError("query must be a string")
    _ids(reader_domain_refs, "reader domain refs")
    for value in (principal_ref, project_ref, purpose, task_ref):
        if type(value) is not str:
            raise ValueError("reader context must contain string fields")
    control_digest = _binding_digest(
        b"agent-memory/recall-control-binding/v1\x00", plan
    )
    admission_digest = _admission_binding(
        query=query, policy_version=admission_policy,
        admission_mode=admission_mode, evaluated_at=evaluated_at,
        refusals=refusals,
    )
    query_digest = _sha(b"query\x00" + query.encode("utf-8"))
    reader_digest = _sha(b"reader\x00" + _json_bytes({
        "domains": sorted(reader_domain_refs),
        "principal": principal_ref,
        "project": project_ref,
        "purpose": purpose,
        "task": task_ref,
    }))
    data = {
        "query_digest": query_digest,
        "reader_digest": reader_digest,
        "controller_ref": controller_ref,
        "admission_policy": admission_policy,
        "admission_mode": admission_mode,
        "evaluated_at": evaluated_at,
        "candidate_refs": tuple(candidates),
        "admitted_refs": tuple(admitted),
        "ranked_refs": tuple(ranked),
        "routes": tuple(route_observations),
        "observed_route_counts": tuple(sorted(observed_route_counts.items())),
        "control_digest": control_digest,
        "admission_digest": admission_digest,
    }
    # Construct digest before invoking the validating dataclass constructor.
    # The helper cannot forge missing revision or completeness authority.
    payload = {
        "version": VERSION, "query_digest": query_digest,
        "reader_digest": reader_digest, "controller_ref": controller_ref,
        "admission_policy": admission_policy, "admission_mode": admission_mode,
        "evaluated_at": evaluated_at,
        "candidate_refs": list(data["candidate_refs"]),
        "admitted_refs": list(data["admitted_refs"]),
        "ranked_refs": list(data["ranked_refs"]),
        "routes": [
            {"id": r.route_id, "candidate_limit": r.candidate_limit,
             "anchor_limit": r.anchor_limit, "returned_count": r.returned_count,
             "executed": r.executed}
            for r in data["routes"]
        ],
        "observed_route_counts": [list(pair) for pair in data["observed_route_counts"]],
        "control_digest": data["control_digest"],
        "admission_digest": data["admission_digest"],
    }
    return RecallObservationReceipt(
        **data, content_digest=_sha(_DOMAIN + _json_bytes(payload)),
    )
