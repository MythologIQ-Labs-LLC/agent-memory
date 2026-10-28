"""The public surface: PRD-001 R1's stages as functions of an adapter and an envelope.

Sprint 4a (plan LD4-LD6). Every function first evaluates ADR-030 compatibility
and validates the envelope; a stage runs only on ``current``. ``propose`` and
``approve`` write nothing. ``commit`` and ``forget`` forward the caller's
evidence and attestation to the adapter unchanged and otherwise park there
(DoD 20). No function accepts a verifier: the registry is the adapter's own.

Sprint 4c-2 (ADR-038): ``authorize`` binds an executable decision only for terminal
PAMA outcomes with no authority-floor constraint, after its ledger exists; ``witness``
binds the host's observation to that decision and consumes the authorization once.

RC-4 adds ``AgentMemory`` as a convenience facade over these same stages and the
qualified SQLite composition. It is not a second contract or authority surface.
"""

from __future__ import annotations

import functools
import threading
import unicodedata

import hashlib
import importlib.resources
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..core import policy
from ..memory import action_authority
from ..runtime import doctor
from ..runtime.adapter import REPLACEMENT_KINDS, WRITE_TARGET_REFUSED_REF, GovernedMemoryAdapter
from ..runtime.restart_runtime import RuntimeRecoveryError, _stage_and_replace
from ..runtime.temporal_intent import declared_temporal, resolve_intent
from . import contract, store_contract

__all__ = [
    "AgentMemory",
    "propose",
    "approve",
    "commit",
    "recall",
    "forget",
    "history",
    "posture",
    "authorize",
    "witness",
]


# -- #777 public read projection ------------------------------------------------------
# Applied to ordinary caller-facing responses only, AFTER canonical governance decided the
# read. It never retrieves hidden text, never broadens admission, and never rewrites stored
# semantics, tombstones or audit events. Detailed deletion records stay internal.



_PUBLIC_PROJECTION = {
    "policy_id": "public-deleted-lineage-redaction",
    "policy_version": "1.0.0",
    "deleted_lineage": "withheld",
}

#: Refusal reasons that would disclose a deletion relationship to an ordinary reader.
_DELETION_REFUSALS = frozenset({
    "tombstoned", "derived_from_tombstoned_source",
    "logical_memory_deleted", "derived_from_deleted_logical_memory",
})


def _never(value: str) -> bool:
    """The predicate for a store with no governed deletion: nothing can be withheld."""
    return False


def _withheld_predicate(adapter, context=None) -> Callable[[str], bool]:
    """The deleted-lineage withholding predicate for one projection. ``context`` is the
    reader's own recall context (#809): an identifier of a generation the reader could never
    have read is its own input, not a disclosure, and is not withheld from it."""
    if not adapter.has_governed_deletions():
        return _never
    cache: dict[str, bool] = {}

    def withheld(value: str) -> bool:
        if value not in cache:
            cache[value] = bool(adapter.public_identifier_withheld(value, context)
                                or adapter.public_memory_withheld(value, context))
        return cache[value]

    return withheld


def _mentions(value: Any, withheld: Callable[[str], bool]) -> bool:
    if isinstance(value, str):
        return withheld(value)
    if isinstance(value, dict):
        return any(withheld(k) or _mentions(v, withheld) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_mentions(v, withheld) for v in value)
    return False


def _normalize(value: Any) -> Any:
    """What ``_scrub`` returns when nothing is withheld: a copy with sequences as lists."""
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _scrub(value: Any, withheld: Callable[[str], bool]) -> Any:
    """Drop list items and mapping entries that name a withheld identifier; blank scalar refs."""
    if withheld is _never:
        return _normalize(value)  # same result, one traversal, no per-value lookups
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if withheld(key):
                continue
            if isinstance(item, str) and withheld(item):
                out[key] = ""
                continue
            out[key] = _scrub(item, withheld)
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub(item, withheld) for item in value if not _mentions(item, withheld)]
    return value


def _withheld_candidates(candidates, refusals, withheld: Callable[[str], bool]) -> set[str]:
    return {c for c in candidates if refusals.get(c) in _DELETION_REFUSALS or withheld(c)}


def _project_semantics(document: dict | None, withheld: Callable[[str], bool]) -> dict | None:
    if document is None:
        return None
    relations = [r for r in document.get("relations", ()) if not _mentions(r, withheld)]
    out = dict(document)
    if "relations" in document:
        out["relations"] = relations
    if "relation_count" in document:
        # count-only relations are not materialised; subtract only what was withheld
        out["relation_count"] = document["relation_count"] - (len(document.get("relations", ())) - len(relations))
    return out


def _gate(envelope: Mapping[str, Any], validator, stage: str):
    """(compat, validated envelope or None, early result or None)."""
    compat = contract.compatibility(envelope)
    if compat != contract.CURRENT:
        return compat, None, contract.result("none", compat)
    try:
        validated = validator(envelope)
    except ValueError as exc:
        return compat, None, contract.result("none", compat, validation_error=str(exc))
    return compat, validated, None


def propose(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any]) -> dict:
    """The proposal stage: evaluate, write nothing."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "proposal")
    if early is not None:
        return early
    decision = policy.evaluate(contract.proposal_from_envelope(validated))
    return contract.result("proposal", compat, outcome=decision.outcome,
                           decision=contract.decision_projection(decision))


def approve(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], *,
            evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The approval stage: ADR-037 4a discharge through the adapter's own registry; write nothing."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "approval")
    if early is not None:
        return early
    decision = memory.evaluate_proposal(contract.proposal_from_envelope(validated),
                                        evidence=evidence, attestation=attestation)
    return contract.result("approval", compat, outcome=decision.outcome,
                           decision=contract.decision_projection(decision))


def commit(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], fact_text: str, *,
           evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The commit stage: the adapter decides again and writes, or parks."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "commit")
    if early is not None:
        return early
    outcome = memory.commit_proposal(contract.proposal_from_envelope(validated), fact_text,
                                     evidence=list(evidence) or None, attestation=attestation)
    return contract.result("commit", compat, outcome=outcome.decision.outcome,
                           decision=contract.decision_projection(outcome.decision),
                           receipt=outcome.receipt, committed=outcome.committed,
                           fact_uuid=outcome.fact_uuid, refusal=outcome.refusal)


def recall(memory: GovernedMemoryAdapter, query: str, context_envelope: Mapping[str, Any]) -> dict:
    """Retrieval candidates and recall admission, as the adapter records them."""
    compat, validated, early = _gate(context_envelope, contract.validate_recall_context, "recall")
    if early is not None:
        return early
    context = contract.recall_context_from_envelope(validated)
    admission = memory.governed_recall(query, context)
    # Contract 1.4.0 (#670): the adapter path has no ranking stage, so the prefix is taken in
    # admission order; the budget is policy applied after admission, never authority.
    returned, return_policy = contract.apply_return_budget(
        admission.admitted, (validated.get("budget") or {}).get("k"))
    # #777: the public projection withholds deleted-generation identifiers after admission.
    withheld = _withheld_predicate(memory, context)
    hidden = _withheld_candidates(admission.candidates, admission.refusals, withheld)
    candidates = [c for c in admission.candidates if c not in hidden]
    admissions = _scrub({c: d for c, d in admission.decisions.items() if c not in hidden}, withheld)
    return contract.result("recall", compat, candidates=candidates,
                           admitted=list(admission.admitted), admissions=admissions,
                           candidate_policy=dict(admission.candidate_policy),
                           returned=returned, return_policy=return_policy,
                           public_projection=dict(_PUBLIC_PROJECTION))


def forget(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], *,
           evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """Governed deletion of the target's current fact; the adapter's keyword for the attestation is ``external_verification``."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "forget")
    if early is not None:
        return early
    proposal = contract.proposal_from_envelope(validated)
    fact_uuid = memory.current_fact_uuid(proposal.target_reference) or ""
    outcome = memory.governed_delete(proposal, fact_uuid,
                                     evidence=list(evidence) or None, external_verification=attestation)
    return contract.result("forget", compat, outcome=outcome.decision.outcome,
                           decision=contract.decision_projection(outcome.decision),
                           receipt=outcome.receipt, committed=outcome.committed,
                           fact_uuid=outcome.fact_uuid, refusal=outcome.refusal)


def history(memory: GovernedMemoryAdapter, target_envelope: Mapping[str, Any], *, fact_text: str | None = None) -> dict:
    """Inspect history: what the adapter retains for one target. Reads only."""
    compat, validated, early = _gate(target_envelope, contract.validate_target_envelope, "history")
    if early is not None:
        return early
    target = validated["target_reference"]
    record = {
        "current_fact_uuid": memory.current_fact_uuid(target),
        "state_version": memory.state_version(target),
        "tombstoned": target in memory.tombstoned_ids(),
        "events": [event for event in memory.events if event.get("memory_id") == target],
    }
    if fact_text is not None:
        record["rejected_values"] = [dict(item) for item in memory.rejected_value_history(target, fact_text)]
    return contract.result("history", compat, history=record)


def posture(config_path: str | Path, *, qualification_path: str | Path | None = None,
            state_dir: str | Path | None = None) -> dict:
    """Inspect posture: the doctor's report for a configuration, under its schema. Reads only."""
    try:
        report = doctor.diagnose(config_path, qualification_path=qualification_path, state_dir=state_dir)
        contract.validate_posture_report(report)
    except (ValueError, OSError) as exc:
        return contract.result("none", contract.CURRENT, validation_error=f"{type(exc).__name__}: {exc}")
    return contract.result("posture", contract.CURRENT, posture=report)


def authorize(memory: GovernedMemoryAdapter, action_envelope: Mapping[str, Any], *,
              evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The action-authority stage: the adapter decides; a terminal outcome binds, after its ledger; else nothing binds."""
    compat, validated, early = _gate(action_envelope, contract.validate_action_envelope, "action_authority")
    if early is not None:
        return early
    action, proposal = contract.action_from_envelope(validated)
    try:
        authority = action_authority.authorize_action(memory, action, proposal,
                                                      evidence=list(evidence) or None, attestation=attestation)
    except ValueError as exc:
        return contract.result("action_authority", compat, refusal=str(exc))
    return contract.result(
        "action_authority", compat, outcome=authority.decision.outcome,
        decision=contract.decision_projection(authority.decision),
        action_authority={
            "decision_ref": authority.decision_ref,
            "bound": authority.bound,
            "execution_status": None if authority.action is None else authority.action.execution_status,
            "ledger_required": authority.ledger_required,
            "requirement": authority.requirement,
            "composition_id": None if authority.composition is None else authority.composition["composition_id"],
        },
    )


def witness(memory: GovernedMemoryAdapter, observation_envelope: Mapping[str, Any]) -> dict:
    """The execution-evidence stage: the host's observation, bound to the decision the adapter bound; consumes once."""
    compat, validated, early = _gate(observation_envelope, contract.validate_observation_envelope, "execution_evidence")
    if early is not None:
        return early
    try:
        document = action_authority.witness_execution(memory, validated["action_id"], validated)
    except ValueError as exc:
        return contract.result("execution_evidence", compat, refusal=str(exc))
    return contract.result("execution_evidence", compat, witness=document)


_DEFAULT_PROFILE = "rc1-local.json"
_DEFAULT_CONFIG_NAME = "runtime-config.json"
_DATABASE_NAME = "agent-memory.sqlite3"
_BINDING_NAME = "configuration-binding.json"
_WITNESS_NAME = "generation-witness.json"

# #786 store identity profiles, versioned by the store-open contract
# (``store_contract.STORE_OPEN_CONTRACT_VERSION``), not by the envelope contract.
# A profile is recorded once, when a store is created, and never rewritten.
STORE_PROFILE_FILE = "store-identity.json"
STORE_PROFILE_SINGLE_PROJECT = "single_project_v1"
STORE_PROFILE_SCOPE_DISTINCT = "scope_distinct_v1"
# Reported for a store created before profiles existed. Never written to disk.
STORE_PROFILE_LEGACY = "legacy_unprofiled"
STORE_PROFILES = (STORE_PROFILE_SINGLE_PROJECT, STORE_PROFILE_SCOPE_DISTINCT)
_STORE_IDENTITY_SCHEMA = "agent-memory-store-identity"


class StoreIdentityError(RuntimeRecoveryError):
    """The requested host identity cannot open this store under its identity profile.

    Messages never name keys, facts, or other projects: a refusal is decided by
    the store's profile and bound project alone, not by which memories exist.
    """


class _CanonicalTarget(str):
    """A canonical logical memory id the runtime itself produced (never caller input)."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _content_ref(text: str) -> str:
    return "content:" + _digest(text)


def _packaged_profile_text() -> str:
    resource = importlib.resources.files("agentmem_ref") / "_profiles" / _DEFAULT_PROFILE
    return resource.read_text(encoding="utf-8")


def _atomic_write_text(path: Path, text: str) -> None:
    # #840: an exclusive, unpredictable temporary per write -- never a predictable name a
    # planted symlink could redirect, and never left behind by a failed write.
    _stage_and_replace(path, (text if text.endswith("\n") else text + "\n").encode("utf-8"))


def _read_store_identity(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StoreIdentityError("store identity record is unreadable") from exc
    if (
        isinstance(record, dict)
        and record.get("schema") == _STORE_IDENTITY_SCHEMA
        and store_contract.record_compatibility(record.get("version")) == store_contract.MIGRATION_REQUIRED
    ):
        # Written under a newer store-open contract: its admission rules are not ours to
        # apply, so the store is neither opened, rewritten nor downgraded.
        raise StoreIdentityError(
            "store identity record requires a newer store-open contract than "
            f"{store_contract.STORE_OPEN_CONTRACT_ID} {store_contract.STORE_OPEN_CONTRACT_VERSION}"
        )
    if (
        not isinstance(record, dict)
        or record.get("schema") != _STORE_IDENTITY_SCHEMA
        # Exact type: JSON true or 1.0 compare equal to 1 in Python and are not version 1.
        or type(record.get("version")) is not int
        or record.get("version") != store_contract.RECORD_VERSION
        or record.get("profile") not in STORE_PROFILES
        or not isinstance(record.get("tenant"), str)
        or (record["profile"] == STORE_PROFILE_SINGLE_PROJECT
            and not isinstance(record.get("bound_project"), str))
    ):
        raise StoreIdentityError("store identity record is malformed")
    return record


def _claim_store_identity(path: Path, record: dict) -> dict:
    """Bind a fresh root to one identity, atomically and exclusively (#786).

    The record is written to a private temporary file and hard-linked into place:
    linking fails if any record already exists, so of several concurrent first opens
    exactly one identity wins and the rest re-read and check the winner. The claim
    precedes store creation, so an interrupted creation leaves a claimed root that
    only the claiming identity can complete.
    """
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.claim")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            winner = _read_store_identity(path)
            if winner is None:
                raise StoreIdentityError("store identity record vanished during claim")
            return winner
    finally:
        temporary.unlink(missing_ok=True)
    return record


def _check_store_identity(record: dict, *, tenant: str, scope: str, requested: str | None) -> None:
    if record["tenant"] != tenant:
        raise StoreIdentityError("requested tenant does not match the store identity")
    if requested is not None and requested != record["profile"]:
        raise StoreIdentityError(f"store identity profile is {record['profile']!r}, not {requested!r}")
    if record["profile"] == STORE_PROFILE_SINGLE_PROJECT and record["bound_project"] != scope:
        raise StoreIdentityError(
            "single-project store is bound to a different project; multi-project memory "
            f"requires a {STORE_PROFILE_SCOPE_DISTINCT!r} store"
        )


def _check_task_ref(task_ref: Any) -> None:
    """A host-bound task identity is canonical: NFC, unpadded, no control characters (#786)."""
    if (
        not isinstance(task_ref, str)
        or task_ref != task_ref.strip()
        or unicodedata.normalize("NFC", task_ref) != task_ref
        or (task_ref and any(ord(ch) < 32 for ch in task_ref))
    ):
        raise ValueError("task_ref must be a canonical, optional host-bound string")


def _checked_extractor(extractor: Any) -> Any:
    """An opted-in proposition extractor must carry the caller's egress policy (#732 R2)."""
    if extractor is None:
        return None
    if not callable(getattr(extractor, "extract", None)) or not callable(getattr(extractor, "egress_policy", None)):
        raise ValueError("proposition_extractor must provide extract() and a caller-supplied egress_policy")
    return extractor


def _serialized(method):
    """Run one public handle operation under the runtime-owned serialization lock (#530)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._serialization_lock:
            return method(self, *args, **kwargs)

    return wrapper


SEMANTIC_RETRIEVAL_DEFAULT = "off"
SEMANTIC_RETRIEVAL_MODES = ("off", "auto", "required")
SEMANTIC_MINIMUM_SIMILARITY = 0.30
SEMANTIC_CANDIDATE_LIMIT = 16
#: Shadow recall control (contract 1.5.0, #644 T-controller): the controller plans beside the
#: unchanged default planner; retrieval, admission and ranking are identical in both modes.
RECALL_CONTROL_DEFAULT = "off"
RECALL_CONTROL_MODES = ("off", "shadow")


def _semantic_route(root: Path, mode: str, representation_dir: str | Path | None) -> dict:
    """Build the semantic vector retriever for ``mode``, or record why it is disabled."""

    if mode not in SEMANTIC_RETRIEVAL_MODES:
        raise ValueError(f"semantic_retrieval must be one of {SEMANTIC_RETRIEVAL_MODES}")
    if mode == "off":
        return {"status": "disabled", "mode": mode, "reason": "off", "retriever": None}
    from ..runtime.representation_cache import DerivedVectorStore
    from ..runtime.representation_onnx import OnnxSentenceEmbeddingProvider, RepresentationUnavailable
    from ..runtime.vector_retrieval import NativeVectorCandidateRetriever

    try:
        provider = OnnxSentenceEmbeddingProvider(representation_dir)
    except RepresentationUnavailable as exc:
        if mode == "required":
            raise
        return {"status": "disabled", "mode": mode, "reason": f"unavailable: {exc}", "retriever": None}
    try:
        store = DerivedVectorStore(root, provider.spec.config_digest, provider.spec.dimensions)
    except ValueError as exc:
        # #802/#804: the derived cache directory or file is refused before any I/O through
        # it (a link, another owner, a foreign database, an inode SQLite did not pin).
        # Derived state is never authority: ``auto`` keeps the canonical runtime and the
        # lexical route and records why; ``required`` refuses, as it does for the model.
        if mode == "required":
            raise
        return {"status": "disabled", "mode": mode, "reason": f"derived store refused: {exc}", "retriever": None}
    retriever = NativeVectorCandidateRetriever(
        provider, minimum_similarity=SEMANTIC_MINIMUM_SIMILARITY, store=store
    )
    return {"status": "enabled", "mode": mode, "reason": "pinned provider verified", "retriever": retriever}


class AgentMemory:
    """Small developer surface over one governed SQLite Agent Memory runtime.

    Thread contract (#530): one handle may be called from any thread. Every public
    operation runs under the runtime-owned serialization lock, so operations never
    interleave and each still commits as one single-writer SQLite generation.
    Objects reached through ``handle.runtime`` are not independently thread-safe;
    direct callers must hold ``handle.runtime.serialization_lock``.

    Defaults are explicit and bounded to low-risk local operation. Higher-risk
    mutation remains subject to the same public proposal contract, evidence
    qualification, and PAMA decisions as direct callers of this module.
    """

    # #786 review RF1: the host-bound identity is fixed when the handle is bound. Every binding
    # check compares against these, so a caller holding the handle must not be able to re-bind it
    # to another project's memory, or brick a single-project store with one write.
    root = property(lambda self: self._root, doc="The store root this handle was bound to (read-only).")
    tenant = property(lambda self: self._tenant, doc="Host-bound tenant (read-only).")
    actor_id = property(lambda self: self._actor_id, doc="Host-bound principal (read-only).")
    charter_version = property(lambda self: self._charter_version, doc="Host-bound charter version (read-only).")
    scope = property(lambda self: self._scope, doc="Host-bound project scope (read-only).")
    purpose = property(lambda self: self._purpose, doc="Host-bound purpose (read-only).")
    task_ref = property(lambda self: self._task_ref, doc="Host-bound task identity (read-only).")
    store_profile = property(lambda self: self._store_profile, doc="The store's identity profile (read-only).")
    runtime = property(lambda self: self._runtime, doc="The runtime this handle was bound to (read-only).")

    def __init__(
        self,
        *,
        root: Path,
        config_path: Path,
        qualification_path: Path | None,
        tenant: str,
        actor_id: str,
        charter_version: str,
        scope: str,
        purpose: str,
        runtime: Any,
        semantic: dict | None = None,
        recall_control: str = RECALL_CONTROL_DEFAULT,
        proposition_extractor: Any = None,
        task_ref: str = "",
        store_profile: str,
    ) -> None:
        # #786 review RF1: the profile is named by whoever binds the handle (``open`` decides it
        # from the store); there is no silent legacy default that passes keys through unmapped.
        if store_profile not in (*STORE_PROFILES, STORE_PROFILE_LEGACY):
            raise ValueError(f"unknown store_profile {store_profile!r}")
        self._store_profile = store_profile
        _check_task_ref(task_ref)
        self._task_ref = task_ref
        self._root = root
        self.config_path = config_path
        self.qualification_path = qualification_path
        self._tenant = tenant
        self._actor_id = actor_id
        self._charter_version = charter_version
        self._scope = scope
        self._purpose = purpose
        self._runtime = runtime
        self._closed = False
        self._serialization_lock = getattr(runtime, "serialization_lock", None) or threading.RLock()
        self._semantic = semantic or {"status": "disabled", "mode": SEMANTIC_RETRIEVAL_DEFAULT,
                                      "reason": "off", "retriever": None}
        if recall_control not in RECALL_CONTROL_MODES:
            raise ValueError(f"recall_control must be one of {RECALL_CONTROL_MODES}")
        self._recall_control = recall_control
        self._proposition_extractor = _checked_extractor(proposition_extractor)
        # #802: the latest derived-sidecar reconciliation report (recovery or deletion).
        self._derived_reconciliation: dict = {"status": "complete", "stores_checked": 0, "rows_purged": 0,
                                              "stores_discarded": [], "foreign": [], "unsafe": [], "failed": [], "pending": []}

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        tenant: str = "tenant:local",
        actor_id: str = "agent:local",
        charter_version: str = "charter:local-v1",
        scope: str = "project:local",
        purpose: str = "local memory",
        config_path: str | Path | None = None,
        qualification_path: str | Path | None = None,
        verifier_registry=None,
        semantic_retrieval: str = SEMANTIC_RETRIEVAL_DEFAULT,
        representation_dir: str | Path | None = None,
        recall_control: str = RECALL_CONTROL_DEFAULT,
        proposition_extractor: Any = None,
        task_ref: str = "",
        store_profile: str | None = None,
        store_open_contract: str | None = None,
    ) -> "AgentMemory":
        """Create or recover one qualified local SQLite composition.

        ``store_profile`` (#786, store-open contract ``agent-memory-store-open`` 1.0.0) fixes how
        logical keys are owned. It is recorded once, when the store is created, and every later
        open must agree:

        * ``"single_project_v1"`` -- the default for a new store. Tenant-wide keys, and the store
          is bound to the creating ``scope``; other projects are refused.
        * ``"scope_distinct_v1"`` -- the only multi-project profile. Every public key is bound to
          (tenant, scope, key) by this facade, so one project can neither read, mutate, nor
          observe the occupancy of another project's keys.

        A store created before profiles existed is never migrated: it opens only for the single
        project its canonical scope metadata already contains, and only without an explicit
        ``store_profile``. A handle's tenant, project, task and principal are bound by its store:
        proposal ``overrides`` and recall keywords may restate or narrow that identity, never
        change it. These rules are versioned apart from the envelope contract: every envelope keeps
        its ADR-030 state against ``contract.CONTRACT_VERSION``, and the module-level surface
        judges envelopes exactly as that contract states. A host may pin the store-open contract
        it was written against with ``store_open_contract``; any state other than ``current``
        refuses the open before the filesystem is touched.

        ``semantic_retrieval`` (#669) is ``"off"`` (default), ``"auto"`` or
        ``"required"``. ``auto`` enables the semantic vector route only when the
        optional extra ``semantic`` is installed and the pinned model verifies;
        otherwise recall stays lexical and ``semantic_retrieval_posture()`` records why.
        ``required`` raises instead of degrading. The route only widens candidates:
        every candidate still crosses governed admission, and under ranking policy
        3.2.0 similarity orders only after every relevance and temporal stage.

        ``recall_control`` (contract 1.5.0, #644) is ``"off"`` (default) or ``"shadow"``.
        In shadow the deterministic System-One controller plans beside the unchanged
        default planner and ``recall()`` adds a ``recall_control`` report: the proposal,
        the actual per-route counts and the actual stop. Candidates, admission, ranking
        and returned facts are identical in both modes; the controller owns nothing.

        ``proposition_extractor`` (contract 1.6.0, #732) is off by default. Passing an
        extractor is this handle's opt-in to data egress: for each ``remember`` without a
        caller-declared ``proposition``, the new text and up to eight retained candidate
        texts admitted by this writer's own governed recall are sent to the extractor's
        provider, subject to the extractor's required ``egress_policy`` (a refused new text
        is not sent; a refused candidate is dropped). The typed result is computed once and
        persisted with the fact; it is never recomputed, and recovery never calls an
        extractor. A failure or refusal persists no typed proposition and the write commits.

        Existing durable state is never replaced by a fresh runtime. A partial
        state marker fails closed so a damaged or incomplete runtime cannot be
        silently reinitialized as empty memory.
        """
        from ..runtime.restart_runtime import RuntimeRecoveryError
        from ..runtime.runtime_behavior import validate_runtime_behavior_contract
        from ..runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

        # Validate host-bound identity and the host's store-open contract before filesystem creation.
        _check_task_ref(task_ref)
        if store_open_contract is not None:
            state = store_contract.compatibility(store_open_contract)
            if state != store_contract.CURRENT:
                raise StoreIdentityError(
                    f"host store-open contract {store_open_contract!r} is {state} against "
                    f"{store_contract.STORE_OPEN_CONTRACT_ID} {store_contract.STORE_OPEN_CONTRACT_VERSION}"
                )
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        if not tenant or not actor_id or not charter_version or not scope:
            raise ValueError("tenant, actor_id, charter_version, and scope must be non-empty")
        if recall_control not in RECALL_CONTROL_MODES:
            raise ValueError(f"recall_control must be one of {RECALL_CONTROL_MODES}")
        if store_profile is not None and store_profile not in STORE_PROFILES:
            raise ValueError(f"store_profile must be one of {STORE_PROFILES}")
        _checked_extractor(proposition_extractor)

        if config_path is None:
            resolved_config = root / _DEFAULT_CONFIG_NAME
            if not resolved_config.exists():
                _atomic_write_text(resolved_config, _packaged_profile_text())
        else:
            resolved_config = Path(config_path)

        resolved_qualification = Path(qualification_path) if qualification_path is not None else None
        value = doctor.load_configuration_value(resolved_config)
        bindings = doctor.load_qualification_bindings(resolved_qualification)
        plan = validate_runtime_behavior_contract(value, qualification_bindings=bindings)

        database = root / _DATABASE_NAME
        binding = root / _BINDING_NAME
        if not database.exists() and (root / _WITNESS_NAME).exists():
            # #821: a store a current runtime created has lost its database; never re-create it.
            raise RuntimeRecoveryError(
                "incomplete durable state: generation witness exists without SQLite runtime database"
            )
        semantic = _semantic_route(root, semantic_retrieval, representation_dir)
        # #786: decide the store identity before any runtime is recovered or created.
        identity_path = root / STORE_PROFILE_FILE
        identity = _read_store_identity(identity_path)
        if identity is not None:
            _check_store_identity(identity, tenant=tenant, scope=scope, requested=store_profile)
            profile = identity["profile"]
        elif database.exists():
            if store_profile is not None:
                raise StoreIdentityError(
                    "store predates identity profiles; it opens only as a restricted legacy "
                    "store and is never migrated implicitly"
                )
            profile = STORE_PROFILE_LEGACY
        elif binding.exists():
            raise RuntimeRecoveryError(
                "incomplete durable state: configuration binding exists without SQLite runtime database"
            )
        else:
            requested_profile = store_profile or STORE_PROFILE_SINGLE_PROJECT
            identity = _claim_store_identity(identity_path, {
                "schema": _STORE_IDENTITY_SCHEMA,
                "version": store_contract.RECORD_VERSION,
                "profile": requested_profile,
                "tenant": tenant,
                "bound_project": scope if requested_profile == STORE_PROFILE_SINGLE_PROJECT else None,
            })
            # A concurrent first open may have claimed the root for another identity.
            _check_store_identity(identity, tenant=tenant, scope=scope, requested=store_profile)
            profile = identity["profile"]
        if database.exists():
            try:
                runtime = SQLiteConfiguredCompositionRuntime.recover(
                    root,
                    plan=plan,
                    verifier_registry=verifier_registry,
                    vector_retriever=semantic["retriever"],
                )
            except RuntimeRecoveryError as exc:
                # #786: a claimed root whose first creation was interrupted before its first
                # checkpoint holds a database file but no runtime state; nothing was committed, so
                # the claiming identity completes the creation. A legacy (unclaimed) root, and any
                # store whose generation witness exists (#821), keep failing closed.
                if (profile == STORE_PROFILE_LEGACY or (root / _WITNESS_NAME).exists()
                        or str(exc) != "required SQLite runtime state is missing"):
                    raise
                runtime = SQLiteConfiguredCompositionRuntime.create(
                    root,
                    tenant=tenant,
                    plan=plan,
                    verifier_registry=verifier_registry,
                    vector_retriever=semantic["retriever"],
                )
        elif binding.exists():
            raise RuntimeRecoveryError(
                "incomplete durable state: configuration binding exists without SQLite runtime database"
            )
        else:
            runtime = SQLiteConfiguredCompositionRuntime.create(
                root,
                tenant=tenant,
                plan=plan,
                verifier_registry=verifier_registry,
                vector_retriever=semantic["retriever"],
            )

        actual_tenant = runtime.adapter.checkpoint_tenant()
        if actual_tenant != tenant:
            runtime.close()
            raise RuntimeRecoveryError(
                f"requested tenant {tenant!r} does not match recovered runtime tenant {actual_tenant!r}"
            )
        if profile == STORE_PROFILE_LEGACY:
            # Restricted legacy mode: the store's tenant-wide keys stay safe only while a single
            # trusted project uses it. Nothing on disk is rewritten.
            if runtime.adapter.canonical_project_refs() - {scope}:
                runtime.close()
                raise StoreIdentityError(
                    "legacy store is bound to a different project or holds several projects; "
                    "it requires an explicit, governed migration"
                )
        elif profile == STORE_PROFILE_SINGLE_PROJECT:
            # The record is a claim, not authority: canonical scope metadata must agree with it,
            # so an edited bound_project cannot rebind another project's store.
            if runtime.adapter.canonical_project_refs() - {identity["bound_project"]}:
                runtime.close()
                raise StoreIdentityError("store identity record does not match canonical store state")
        # #802: retry any interrupted sidecar cleanup against the recovered canonical facts,
        # whatever the semantic mode. A derived cache is never authority, so its state never
        # refuses the canonical runtime: the outcome is recorded for the posture instead.
        try:
            reconciliation = cls._reconcile_cached_representations(root, runtime)
        except Exception as exc:  # unexpected: the report, not the exception, carries it
            reconciliation = {"status": "incomplete", "stores_checked": 0, "rows_purged": 0,
                              "stores_discarded": [], "foreign": [], "unsafe": [],
                              "failed": [[str(root / "derived"), f"{type(exc).__name__}: {exc}"]]}
        reconciliation["pending"] = []
        handle = cls(
            root=root,
            config_path=resolved_config,
            qualification_path=resolved_qualification,
            tenant=tenant,
            actor_id=actor_id,
            charter_version=charter_version,
            scope=scope,
            purpose=purpose,
            runtime=runtime,
            semantic=semantic,
            recall_control=recall_control,
            proposition_extractor=proposition_extractor,
            task_ref=task_ref,
            store_profile=profile,
        )
        handle._derived_reconciliation = reconciliation
        return handle

    @staticmethod
    def _reconcile_cached_representations(root: Path, runtime, *, deleted_fact_uuid: str | None = None) -> dict:
        """Close derived sidecar rows no canonical fact accounts for (#802); provider-free.

        Only the recovered canonical facts decide what a sidecar may retain; the caller
        holds the runtime serialization lock. Returns the reconciliation report.
        """
        from ..runtime.representation_cache import reconcile_derived_vector_stores

        substrate = runtime.adapter.checkpoint_substrate()
        texts = {fact.uuid: fact.fact_text for fact in substrate.all_facts()}
        return reconcile_derived_vector_stores(
            root, texts, deleted_fact_uuid=deleted_fact_uuid
        )

    @property
    def contract_version(self) -> str:
        return contract.CONTRACT_VERSION

    @property
    def store_open_contract(self) -> dict:
        """The store-open contract this handle was opened under (#786); read-only."""
        return store_contract.describe(self.store_profile, contract.CONTRACT_VERSION)

    def _target(self, target_reference: str) -> str:
        """The canonical logical memory id for a caller's public key (#786).

        In a ``scope_distinct_v1`` store the facade itself binds every public key to
        (tenant, project, key); reserved or foreign canonical ids are refused, so no caller can
        name another project's memory.
        """
        if isinstance(target_reference, _CanonicalTarget):
            return str(target_reference)
        if self.store_profile != STORE_PROFILE_SCOPE_DISTINCT:
            return target_reference
        from .scoped_identity import scope_distinct_key

        return scope_distinct_key(self.tenant, self.scope, target_reference)

    def _check_overrides(self, overrides: Mapping[str, object] | None) -> None:
        """Bind proposal overrides to the handle's host-bound identity (#786, store-open 1.0.0).

        Checked at every operation's entry, so a refusal never depends on whether the target
        exists. An internally inconsistent scope keeps its contract 1.8.0 refusal (#786 review
        F3, replay W4) and is checked first; an override may restate the handle's tenant,
        project, task and domains but never change them, because re-declaring another
        project's scope through one handle is multi-project access, which a profiled or
        restricted legacy store does not admit.
        """
        if not overrides:
            return
        protected = {
            "contract_version", "proposal_id", "actor_id", "charter_version", "state_snapshot",
            "operation", "target_reference", "task_ref",
        }
        attempted = protected.intersection(overrides)
        if attempted:
            raise ValueError(f"facade proposal overrides may not replace protected fields: {sorted(attempted)}")
        domains = overrides.get("isolation_domain_refs", self._domain_refs())
        required = overrides.get("required_isolation_domain_refs", self._domain_refs())
        if not set(required or ()).issubset(set(domains or ())):
            raise ValueError("required isolation domains must also be bound isolation domains")
        bound = {
            "tenant_ref": self.tenant,
            "scope": self.scope,
            "project_ref": self.scope,
            "isolation_domain_refs": list(self._domain_refs()),
            "required_isolation_domain_refs": list(self._domain_refs()),
        }
        for field, expected in bound.items():
            if field not in overrides:
                continue
            value = overrides[field]
            normalized = list(value) if isinstance(value, (tuple, list)) else value
            if normalized != expected:
                raise ValueError("facade proposal may not override host-bound scope identity")

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("AgentMemory runtime is closed")

    def _domain_refs(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.tenant, self.scope)))

    def _writer_context(self, envelope: Mapping[str, Any]):
        """#786: the authority context of one proposal envelope, overrides applied: a host
        that declares another scope through ``overrides`` is judged under that scope, exactly
        as the adapter will judge the proposal."""
        return self.runtime.adapter.writer_context(
            isolation_domain_refs=tuple(envelope.get("isolation_domain_refs") or ()),
            scope=str(envelope.get("scope") or ""), actor_id=self.actor_id,
            project_ref=str(envelope.get("project_ref") or ""), task_ref=str(envelope.get("task_ref") or ""),
            purpose=str(envelope.get("purpose") or ""))

    def _visible_head(self, target_reference: str, envelope: Mapping[str, Any]) -> str | None:
        """#786: the target's current fact if this proposal's writer may act on it, else None.

        A live head outside the writer's scope is reported exactly as no head at all, so a
        correction, forget or dispute from another project reads as ``fact_not_found`` --
        indistinguishable from an id nobody ever wrote. The canonical refusal lives in the
        adapter (``write_target_refusal``, ``_delete_refusal``, ``_dispute_refusal``); this
        only keeps the facade result shape identical to the unknown-id case.
        """
        adapter = self.runtime.adapter
        head = adapter.current_fact_uuid(target_reference)
        if head is None or not adapter.fact_eligible_in_context(head, self._writer_context(envelope)):
            return None
        if str(envelope.get("operation")) in ("promotion", "correction"):
            probe = {**envelope, "proposal_id": "probe", "state_snapshot": "",
                     "evidence_refs": list(envelope.get("evidence_refs") or ["probe"])}
            if adapter.write_target_refusal(contract.proposal_from_envelope(probe)) is not None:
                return None  # a write the head's holders could not read (scope continuity) is not a visible target
        return head

    def _state_snapshot(self, target_reference: str, envelope: Mapping[str, Any]) -> str:
        """The state version this proposal's authority is resolved against. A live head the
        writer may not act on contributes nothing (#786): the proposal, its id and its receipt
        then carry ``v0`` rather than the protected memory's version."""
        adapter = self.runtime.adapter
        if adapter.current_fact_uuid(target_reference) is not None and self._visible_head(target_reference, envelope) is None:
            return "v0"
        return f"v{adapter.public_state_version(target_reference)}"

    def _proposal(
        self,
        *,
        target_reference: str,
        operation: str,
        fact_text: str = "",
        target_class: str = policy.M2,
        current_strength: str = "observed",
        proposed_strength: str = "reinforced",
        downstream_authority: str = policy.A1,
        reversibility: str = "reversible",
        risk_class: str = "low",
        evidence_refs: Sequence[str] = (),
        confidence: float | None = None,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> dict:
        self._require_open()
        if not target_reference:
            raise ValueError("target_reference must be non-empty")
        envelope: dict[str, object] = {
            "contract_version": contract.CONTRACT_VERSION,
            "actor_id": self.actor_id,
            "charter_version": self.charter_version,
            "target_reference": target_reference,
            "target_class": target_class,
            "scope": self.scope,
            "operation": operation,
            "current_strength": current_strength,
            "proposed_strength": proposed_strength,
            "downstream_authority": downstream_authority,
            "reversibility": reversibility,
            "risk_class": risk_class,
            "tenant_ref": self.tenant,
            "purpose": self.purpose if purpose is None else purpose,
            "isolation_domain_refs": list(self._domain_refs()),
            "required_isolation_domain_refs": list(self._domain_refs()),
            "project_ref": self.scope,
        }
        if self.task_ref:
            envelope["task_ref"] = self.task_ref
        if confidence is not None:
            envelope["confidence"] = confidence
        if overrides:
            # #786 (review F3 and store-open 1.0.0): malformed or identity-changing overrides are
            # refused before any target is resolved.
            self._check_overrides(overrides)
            envelope.update(dict(overrides))
        # #786: the snapshot is resolved under the proposal's effective scope (overrides applied)
        state_snapshot = self._state_snapshot(target_reference, envelope)
        refs = tuple(evidence_refs) or ((_content_ref(fact_text),) if fact_text else (f"state:{state_snapshot}",))
        material = {
            "actor_id": self.actor_id,
            "charter_version": self.charter_version,
            "target_reference": target_reference,
            "operation": operation,
            "state_snapshot": state_snapshot,
            "scope": self.scope,
            "tenant_ref": self.tenant,
            "fact_ref": _content_ref(fact_text) if fact_text else "",
            "risk_class": risk_class,
        }
        if self.task_ref:
            material["task_ref"] = self.task_ref
        envelope["proposal_id"] = "facade:" + hashlib.sha256(_canonical_bytes(material)).hexdigest()
        envelope["state_snapshot"] = state_snapshot
        if "evidence_refs" not in (overrides or {}):
            envelope["evidence_refs"] = list(refs)
        contract.validate_proposal_envelope(envelope)
        return envelope

    @staticmethod
    def _commit_result(outcome, *, stage: str = "commit") -> dict:
        return contract.result(
            stage,
            contract.CURRENT,
            outcome=outcome.decision.outcome,
            decision=contract.decision_projection(outcome.decision),
            receipt=outcome.receipt,
            committed=outcome.committed,
            fact_uuid=outcome.fact_uuid,
            refusal=outcome.refusal,
        )

    @_serialized
    def remember(
        self,
        target_reference: str,
        fact_text: str,
        *,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        confidence: float | None = None,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
        observed_at: str | None = None,
        source_ref: str | None = None,
        proposition: Mapping[str, Any] | None = None,
    ) -> dict:
        """Retain a low-risk observation through ordinary PAMA and durable commit.

        ``valid_from``/``valid_until``/``observed_at`` optionally declare temporal
        evidence (ISO-8601). They are recorded as the caller's claim and used only as
        post-admission applicability evidence (ADR-039, proposed). They never refuse,
        supersede, or change currentness.

        ``source_ref`` (#671) optionally names where the statement came from (for example
        ``user:alice`` or ``tool:web-search``; at most 256 characters). It defaults to
        ``actor:<actor_id>``, the acting agent's own observation, and is recorded in the
        fact's write provenance. It grants nothing: read-path cross-fact currentness only
        relates two facts that share it (owner ruling ``decision-671-same-source``).

        ``proposition`` (contract 1.6.0, #732 R1) optionally declares the typed proposition
        the text asserts: ``subject``, ``attribute``, ``value``, ``assertion`` (``state`` or
        ``change``), and optionally ``cardinality`` (``single``/``multi``/None),
        ``replaces_value`` and ``flags`` (``hedged``, ``attributed_to_other``,
        ``conditional``, ``negated``, ``joke_or_sarcasm``, ``quoted_or_forwarded``,
        ``coexistent``; each defaults to false). It is persisted as write-time evidence with
        basis ``caller_declared`` and outranks any extractor, which is then not called. It
        grants nothing: PAMA, the read-path guards and the lifecycle are unchanged.
        """
        target_reference = self._target(target_reference)
        from ..runtime import typed_proposition
        from ..runtime.cross_fact_currentness import validate_source_ref

        source_ref = validate_source_ref(source_ref)
        declared = typed_proposition.validate(proposition) if proposition is not None else None
        temporal = declared_temporal(
            {"valid_from": valid_from, "valid_until": valid_until, "observed_at": observed_at}
        )
        proposal = contract.proposal_from_envelope(
            self._proposal(
                target_reference=target_reference,
                fact_text=fact_text,
                operation="promotion",
                target_class=target_class,
                downstream_authority=downstream_authority,
                risk_class="low",
                evidence_refs=evidence_refs,
                confidence=confidence,
                purpose=purpose,
                overrides=overrides,
            )
        )
        typed_write = self._typed_write(proposal, fact_text, declared)
        outcome = self.runtime.retain(
            proposal,
            fact_text,
            evidence=list(evidence) or None,
            attestation=attestation,
            temporal=temporal,
            source_ref=source_ref,
            **({"typed_write": typed_write} if typed_write is not None else {}),
        )
        return self._commit_result(outcome)

    def _typed_write(self, proposal, fact_text: str, declared: Mapping[str, Any] | None) -> dict | None:
        """#732: the caller's declaration, else one extraction for this write, else None."""
        from ..runtime import proposition_extraction, typed_proposition

        if declared is not None:
            return {"typed_proposition": typed_proposition.typed_record(declared, typed_proposition.CALLER_DECLARED)}
        if self._proposition_extractor is None:
            return None
        try:
            admitted = self.runtime.recall(fact_text, self._handle_recall_context()).admitted
            candidates = self.runtime.adapter.typed_candidates(proposal, admitted)
        except Exception as exc:  # the write still commits without a typed proposition
            record = proposition_extraction.extraction_record(
                self._proposition_extractor, [], status="failed", reason=f"candidate_recall_failed:{type(exc).__name__}")
            return {"typed_proposition": None, "extraction": record}
        return proposition_extraction.extract_for_write(self._proposition_extractor, fact_text, candidates)

    @_serialized
    def correct(
        self,
        target_reference: str,
        fact_text: str,
        *,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str = "medium",
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
        observed_at: str | None = None,
        replacement_kind: str = "error_correction",
    ) -> dict:
        """Propose/commit a correction. Review requirements are not hidden or auto-satisfied.

        ``replacement_kind`` (#549) records why the current value is replaced:
        ``error_correction`` (default; the prior value was wrong and is never presented as
        historically true) or ``state_change`` (the prior value was true until this
        replacement's ``valid_from``, or the replacement time). The kind rides the same
        governed correction; it grants nothing, and only explicit historical/as-of recall
        may return a state-changed record, labelled as non-current historical evidence.
        """
        target_reference = self._target(target_reference)
        temporal = declared_temporal(
            {"valid_from": valid_from, "valid_until": valid_until, "observed_at": observed_at}
        )
        if replacement_kind not in REPLACEMENT_KINDS:
            raise ValueError(f"unknown replacement_kind {replacement_kind!r}")
        envelope = self._proposal(
            target_reference=target_reference,
            fact_text=fact_text,
            operation="correction",
            current_strength="reinforced",
            proposed_strength="reinforced",
            risk_class=risk_class,
            evidence_refs=evidence_refs,
            purpose=purpose,
            overrides=overrides,
        )
        if self._visible_head(target_reference, envelope) is None:
            return contract.result(
                "commit",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="fact_not_found",
            )
        proposal = contract.proposal_from_envelope(envelope)
        outcome = self.runtime.correct(
            proposal,
            fact_text,
            evidence=list(evidence) or None,
            attestation=attestation,
            temporal=temporal,
            replacement_kind=replacement_kind,
        )
        return self._commit_result(outcome)

    @_serialized
    def write_semantics(self, fact_uuid: str) -> dict | None:
        """Typed write-time interpretation persisted with one fact (#550). Evidence only.

        Proposition identity, cardinality, markers, anchored self-validity, and the
        same-slot classification computed when the fact was written. It carries
        ``authority_effect: none``; nothing in it refuses, supersedes, or mutates.
        """
        self._require_open()
        adapter = self.runtime.adapter
        context = self._handle_recall_context()
        return _project_semantics(adapter.write_semantics(fact_uuid, context), _withheld_predicate(adapter, context))

    @_serialized
    def semantic_proposals(self, *, status: str | None = None) -> list[dict]:
        """Write-time ``state_change`` proposals (#550) with status derived from lifecycle.

        ``open`` / ``applied`` / ``stale``. A proposal is never applied automatically.
        """
        self._require_open()
        proposals = self.runtime.adapter.semantic_proposals(self._handle_recall_context())
        return [item for item in proposals if status is None or item["status"] == status]

    def _handle_recall_context(self):
        """This handle's own recall context: evidence is visible only where recall could see it."""
        envelope = {
            "contract_version": contract.CONTRACT_VERSION,
            "target_domain_refs": list(self._domain_refs()),
            "principal_ref": self.actor_id,
            "project_ref": self.scope,
            "purpose": self.purpose,
        }
        if self.task_ref:
            envelope["task_ref"] = self.task_ref
        return contract.recall_context_from_envelope(contract.validate_recall_context(envelope))

    @_serialized
    def apply_semantic_proposal(
        self,
        proposal_id: str,
        *,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str = "medium",
        purpose: str | None = None,
        valid_from: str | None = None,
    ) -> dict:
        """Explicitly route one open write-time proposal through the governed correction.

        This is the caller's decision, not the interpreter's: it is exactly
        ``correct(target, replacement_text, replacement_kind="state_change")`` under
        ordinary PAMA, citing the proposal id as an evidence ref. Review requirements are
        not hidden or auto-satisfied, the proposal's ``effective_no_later_than`` is not
        applied as an effective time, and a proposal that is not ``open`` is refused.
        """
        self._require_open()
        proposal = next((item for item in self.runtime.adapter.semantic_proposals(self._handle_recall_context())
                         if item["proposal_id"] == proposal_id), None)
        if proposal is None or proposal["status"] != "open":
            return contract.result(
                "commit",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="semantic_proposal_not_open" if proposal else "semantic_proposal_not_found",
            )
        return self.correct(
            _CanonicalTarget(proposal["target_reference"]),
            proposal["replacement_text"],
            evidence=evidence,
            attestation=attestation,
            evidence_refs=(*tuple(evidence_refs), proposal_id),
            risk_class=risk_class,
            purpose=purpose,
            valid_from=valid_from,
            replacement_kind=proposal["replacement_kind"],
        )

    @_serialized
    def dispute(
        self,
        target_reference: str,
        *,
        fact_uuid: str | None = None,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str = "low",
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> dict:
        """Govern and durably mark one retained fact disputed without deleting or rewriting it.

        The closed public proposal vocabulary does not yet contain ``mark_disputed``.
        Until doctrine explicitly promotes that operation, the PAMA proposal uses the
        conservative ``other`` cell (review by default). The durable audit event records
        the actual ``memory.dispute`` transition and exact fact UUID. This is deliberately
        separate from correction/supersession and grants no truth or currentness authority.
        """
        target_reference = self._target(target_reference)
        self._check_overrides(overrides)
        self._require_open()

        def envelope_for(refs):
            return self._proposal(
                target_reference=target_reference,
                operation="other",
                current_strength="reinforced",
                proposed_strength="blocked",
                risk_class=risk_class,
                evidence_refs=refs,
                purpose=purpose,
                overrides=overrides,
            )

        probe = envelope_for(tuple(evidence_refs))
        target_fact = fact_uuid or self._visible_head(target_reference, probe)
        if target_fact and not self.runtime.adapter.fact_eligible_in_context(target_fact, self._writer_context(probe)):
            target_fact = None  # #786: a named fact outside the writer's scope reads as absent
        if not target_fact:
            return contract.result(
                "commit",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="fact_not_found",
            )
        refs = tuple(dict.fromkeys((f"fact:{target_fact}", *tuple(evidence_refs))))
        proposal = contract.proposal_from_envelope(envelope_for(refs))
        outcome = self.runtime.dispute(
            proposal,
            target_fact,
            evidence=list(evidence) or None,
            attestation=attestation,
        )
        return self._commit_result(outcome)

    @_serialized
    def recall(self, query: str, **kwargs) -> dict:
        """Ordinary caller-facing recall (#777 public projection applied); see ``_recall_document``."""
        self._require_open()
        return self._recall_document(query, public=True, **kwargs)

    @_serialized
    def _canonical_recall(self, query: str, **kwargs) -> dict:
        """IN-PROCESS EVALUATION ONLY, not part of the public contract (#777): the canonical
        recall document including deleted-lineage refusals, for governance evaluators that
        already hold the runtime. Ordinary callers use ``recall``."""
        self._require_open()
        return self._recall_document(query, public=False, **kwargs)

    def _recall_document(
        self,
        query: str,
        *,
        public: bool = True,
        logical_memory_refs: Sequence[str] = (),
        target_domain_refs: Sequence[str] | None = None,
        principal_ref: str | None = None,
        project_ref: str | None = None,
        task_ref: str | None = None,
        purpose: str | None = None,
        temporal_intent: Mapping[str, Any] | None = None,
        reference_time: str | None = None,
        budget: int | None = None,
    ) -> dict:
        """Run composed candidate generation followed by one governed admission pass.

        ``budget`` (contract 1.4.0, #670) is an optional return budget ``k``: ``returned``
        carries at most ``k`` of the ranked admitted facts while ``admitted`` always carries
        the full ranked admitted set; ``return_policy`` records what was returned and why.
        The budget is applied after admission and after ranking and is never authority.

        ``temporal_intent`` optionally declares what time the query is about
        (``{"mode": "current"|"as_of"|"historical"|"atemporal_or_unspecified"|
        "prospective", "reference_time", "target_start", "target_end",
        "expected_recall_shape"}``); explicit intent is authoritative. Without it, a
        bounded deterministic interpreter infers intent from generic temporal cues and
        records its confidence; ``reference_time`` anchors current/prospective
        applicability. Intent only orders admitted candidates (ADR-039, proposed).

        Under the store-open contract the recall keywords may narrow the handle's host-bound
        identity, never impersonate another principal, project, purpose or task, or add a domain
        outside the handle's (#786).
        """
        self._require_open()
        if principal_ref is not None and principal_ref != self.actor_id:
            raise ValueError("recall principal differs from host-bound identity")
        if project_ref is not None and project_ref != self.scope:
            raise ValueError("recall project differs from host-bound identity")
        if purpose is not None and purpose != self.purpose:
            raise ValueError("recall purpose differs from host-bound identity")
        if task_ref is not None and task_ref != self.task_ref:
            raise ValueError("recall task differs from host-bound identity")
        if target_domain_refs is not None and not set(target_domain_refs).issubset(self._domain_refs()):
            raise ValueError("recall domains exceed host-bound identity")
        logical_memory_refs = tuple(self._target(ref) for ref in logical_memory_refs)
        intent = resolve_intent(query, temporal_intent, reference_time=reference_time)
        domains = tuple(target_domain_refs) if target_domain_refs is not None else self._domain_refs()
        envelope = {
            "contract_version": contract.CONTRACT_VERSION,
            "target_domain_refs": list(domains),
            "principal_ref": self.actor_id if principal_ref is None else principal_ref,
            "project_ref": self.scope if project_ref is None else project_ref,
            "purpose": self.purpose if purpose is None else purpose,
        }
        if self.task_ref:
            envelope["task_ref"] = self.task_ref
        if budget is not None:
            envelope["budget"] = {"k": budget}
        validated = contract.validate_recall_context(envelope)
        context = contract.recall_context_from_envelope(validated)
        result = self.runtime.multi_route_recall(
            query,
            context,
            logical_memory_refs=tuple(logical_memory_refs),
            temporal_intent=intent,
        )
        rank = {candidate: index + 1 for index, candidate in enumerate(result.ranked_admitted)}
        # #777: ordinary readers never see deleted-generation identifiers, refusal reasons
        # that disclose a deletion, or counts/stop reasons derived from them.
        withheld = _withheld_predicate(self.runtime.adapter, context) if public else (lambda value: False)
        hidden = _withheld_candidates(result.candidates, result.refusals, withheld) if public else set()
        public_candidates = [c for c in result.candidates if c not in hidden]
        admissions: dict[str, dict] = {}
        for candidate in public_candidates:
            decision = dict(result.decisions.get(candidate, {}))
            decision["route_provenance"] = [hit.to_dict() for hit in result.provenance_for(candidate)]
            basis = getattr(result, "admission_basis", {}).get(candidate)
            if basis is not None:
                decision["admission_basis"] = dict(basis)
            if candidate in rank:
                decision["rank_position"] = rank[candidate]
                ranking = getattr(result, "ranking_evidence", {}).get(candidate)
                if ranking is not None:
                    decision["ranking_evidence"] = dict(ranking)
            if candidate in result.refusals:
                decision["refusal"] = result.refusals[candidate]
            admissions[candidate] = decision
        returned, return_policy = contract.apply_return_budget(
            result.ranked_admitted, (validated.get("budget") or {}).get("k"))
        recall_control = None
        if self._recall_control == "shadow":
            recall_control = self._shadow_recall_control(query, tuple(logical_memory_refs), result, validated,
                                                         public_candidates)
        return contract.result(
            "recall",
            contract.CURRENT,
            candidates=public_candidates,
            admitted=list(result.ranked_admitted),
            admissions=_scrub(admissions, withheld) if public else admissions,
            public_projection=dict(_PUBLIC_PROJECTION) if public else None,
            candidate_policy=dict(getattr(result, "candidate_policy", {}) or {}) or None,
            returned=returned,
            return_policy=return_policy,
            recall_control=recall_control,
        )

    def _shadow_recall_control(self, query: str, logical_memory_refs: tuple[str, ...], result, envelope,
                               public_candidates=None) -> dict:
        """Plan in shadow beside the executed recall (#644 T-controller S2-S4).

        Runs after ``multi_route_recall`` returned; reads only the result and the route
        capabilities, so it cannot change what was retrieved, admitted or ranked. Route
        counts are over caller-visible candidates only (``result.candidates``).
        """
        from ..runtime.recall_control import DeterministicRecallController, shadow_control_report
        from ..runtime.runtime_composition import EXACT_IDENTITY_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE
        from ..runtime.vector_retrieval import SEMANTIC_VECTOR_ROUTE
        from ..state.substrate import EvidenceNeighborTemporalGraphPort

        substrate = self.runtime.adapter.checkpoint_substrate()
        available = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        host_caps: dict[str, int] = {}
        retriever = self._semantic.get("retriever")
        if retriever is not None and retriever.available_for(substrate):
            available.append(SEMANTIC_VECTOR_ROUTE)
            host_caps[SEMANTIC_VECTOR_ROUTE] = SEMANTIC_CANDIDATE_LIMIT
        if isinstance(substrate, EvidenceNeighborTemporalGraphPort):
            available.append(SHARED_EVIDENCE_ROUTE)
        visible = list(result.candidates) if public_candidates is None else list(public_candidates)
        counts: dict[str, int] = {}
        for candidate in visible:
            for route in {hit.route_id for hit in result.provenance_for(candidate)}:
                counts[route] = counts.get(route, 0) + 1
        return shadow_control_report(
            controller=DeterministicRecallController(),
            query=query,
            logical_memory_refs=logical_memory_refs,
            available_routes=tuple(available),
            routes_executed=tuple(result.routes_executed),
            route_counts=counts,
            host_caps=host_caps,
            candidate_count=len(visible),
            policy_context={
                "tenant_scope_ref": f"{self.tenant}#{envelope.get('project_ref') or self.scope}",
                "recall_policy_ref": str(result.policy_version),
                "controller_contract_version": "1.0.0",
            },
        )

    @_serialized
    def forget(
        self,
        target_reference: str,
        *,
        permanent: bool = False,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str | None = None,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> dict:
        """Tombstone by default; permanent deletion remains a stricter explicit request."""
        target_reference = self._target(target_reference)
        self._check_overrides(overrides)
        self._require_open()
        operation = "permanent_deletion" if permanent else "pruning"
        envelope = self._proposal(
            target_reference=target_reference,
            operation=operation,
            current_strength="reinforced",
            proposed_strength="not_applicable" if permanent else "archived",
            reversibility="irreversible" if permanent else "reversible",
            risk_class=risk_class or ("high" if permanent else "low"),
            evidence_refs=evidence_refs,
            purpose=purpose,
            overrides=overrides,
        )
        if self._visible_head(target_reference, envelope) is None:
            return contract.result(
                "forget",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="fact_not_found",
            )
        proposal = contract.proposal_from_envelope(envelope)
        outcome = self.runtime.delete_current(
            proposal,
            evidence=list(evidence) or None,
            external_verification=attestation,
        )
        result = self._commit_result(outcome, stage="forget")
        if permanent and outcome.committed:
            # #802: the canonical generation is committed; now every persistent sidecar under
            # this root drops the deleted lineage, whatever the semantic mode. Two SQLite files
            # are not one transaction: an incomplete cleanup is reported loudly, with the
            # canonical receipt attached, and retried on the next open. It is never a claim
            # of full erasure, and the caller's authority is not re-used for anything else.
            from ..runtime.representation_cache import DerivedCacheReconciliationError

            cause = None
            try:
                report = self._reconcile_cached_representations(
                    self.root, self.runtime, deleted_fact_uuid=outcome.fact_uuid
                )
            except Exception as exc:
                cause = exc
                report = {"status": "incomplete", "stores_checked": 0, "rows_purged": 0,
                          "stores_discarded": [], "foreign": [], "unsafe": [],
                          "failed": [[str(self.root / "derived"), f"{type(exc).__name__}: {exc}"]]}
            complete = report["status"] == "complete"
            report["pending"] = [] if complete else [outcome.fact_uuid]
            self._derived_reconciliation = report
            if not complete:
                raise DerivedCacheReconciliationError(
                    "canonical permanent deletion committed, but derived vector cleanup is "
                    "incomplete; residue may remain and reopen will retry reconciliation",
                    fact_uuid=outcome.fact_uuid, report=report, result=result,
                ) from cause
        return result

    @_serialized
    def _canonical_history(self, target_reference: str, *, fact_text: str | None = None) -> dict:
        """IN-PROCESS EVALUATION ONLY (#777): the unprojected history record."""
        self._require_open()
        return history(self.runtime.adapter,
                       {"contract_version": contract.CONTRACT_VERSION, "target_reference": target_reference},
                       fact_text=fact_text)

    @_serialized
    def history(self, target_reference: str, *, fact_text: str | None = None) -> dict:
        target_reference = self._target(target_reference)
        self._require_open()
        raw = history(
            self.runtime.adapter,
            {"contract_version": contract.CONTRACT_VERSION, "target_reference": target_reference},
            fact_text=fact_text,
        )
        if "history" not in raw:
            return raw
        # #777: an ordinary handle sees only a memory whose current fact it may read, and only
        # that live generation's events. An out-of-scope memory reads as unknown. A memory this
        # handle could have read and that is now governed-deleted reads as ``tombstoned`` with
        # nothing else (docs/44; durability profile DUR-DEL-001): the deletion is the reader's
        # own lifecycle fact, while the deleted generation's identifiers, timestamps, events
        # and rejected values stay internal audit records.
        adapter = self.runtime.adapter
        record = raw["history"]
        context = self._handle_recall_context()
        if not adapter.public_current_visible(target_reference, context):
            # the version recorded by the deletion itself, never the live memory-wide counter,
            # which another scope's later generation would move
            deleted_version = adapter.public_deleted_version(target_reference, context)
            projected = {"current_fact_uuid": None,
                         "state_version": deleted_version if deleted_version is not None else 0,
                         "tombstoned": deleted_version is not None, "events": []}
            if fact_text is not None:
                projected["rejected_values"] = []
        else:
            start = adapter.public_generation_start(target_reference)
            withheld = _withheld_predicate(adapter, context)
            # Deletion records are audit metadata: every deletion correlation is omitted, as is
            # every correlation that began in an earlier (deleted) generation.
            hidden = {e.get("correlation_id") for e in record["events"]
                      if e.get("event_type") == "memory.delete"
                      or (start is not None and str(e.get("timestamp", "")) <= start)}
            # a write-target-refused attempt by another scope is an audit record, not the
            # memory's lifecycle: its whole correlation is withheld (#786, review F7)
            hidden |= {e.get("correlation_id") for e in record["events"]
                       if WRITE_TARGET_REFUSED_REF in (e.get("authority") or {}).get("authority_refs", ())}
            events = [e for e in record["events"]
                      if (start is None or str(e.get("timestamp", "")) > start) and e.get("correlation_id") not in hidden]
            projected = dict(record, tombstoned=False, events=_scrub(events, withheld))
            if "rejected_values" in projected:
                # a deleted generation's rejections stay internal audit records (#786, review F1)
                projected["rejected_values"] = [
                    row for row in projected["rejected_values"]
                    if not adapter.memory_deleted(str(row.get("superseded_fact_uuid", "")))
                    and not _mentions(row, withheld)]
        raw = dict(raw, history=projected, public_projection=dict(_PUBLIC_PROJECTION))
        from ..core import receipts
        receipts.validate(contract.RESULT_SCHEMA, raw)
        return raw

    @_serialized
    def posture(self) -> dict:
        """Return the canonical doctor report, including SQLite recovery when present."""
        self._require_open()
        report = doctor.diagnose(
            self.config_path,
            qualification_path=self.qualification_path,
            state_dir=self.root,
        )
        contract.validate_posture_report(report)
        return contract.result("posture", contract.CURRENT, posture=report)

    @_serialized
    def legacy_upgrade_status(self) -> dict:
        """#809: whether this store carries facts persisted before canonical derivation was
        recorded (``fresh`` / ``legacy_pending``) and, once upgraded, the recorded status
        (``legacy_qualified`` / ``legacy_unqualified``). Read-only; never authority."""
        self._require_open()
        return self.runtime.adapter.legacy_upgrade_status()

    @_serialized
    def upgrade_canonical_derivation(self) -> dict:
        """#809 legacy upgrade: an explicit governed operation (never implied by ``open``) that
        gives every pre-#809 fact a derivation record reconstructed from durable state only,
        keeps undecidable edges bound and quarantined, and labels the store. Published as one
        durable generation through the runtime's transactional seam. Idempotent."""
        self._require_open()
        durable = getattr(self.runtime, "durable_runtime", None)
        seam = getattr(durable, "run_governed_read", None)
        operation = self.runtime.adapter.upgrade_canonical_derivation
        return seam(operation) if callable(seam) else operation()

    @_serialized
    def semantic_retrieval_posture(self) -> dict:
        """Read-only status of the semantic vector route (#669); never authority."""

        self._require_open()
        retriever = self._semantic.get("retriever")
        spec = retriever.spec if retriever is not None else None
        store = getattr(retriever, "store", None) if retriever is not None else None
        return {
            "status": self._semantic["status"],
            "mode": self._semantic["mode"],
            "reason": self._semantic["reason"],
            "representation": None if spec is None else {
                "representation_ref": spec.representation_ref,
                "representation_version": spec.representation_version,
                "config_digest": spec.config_digest,
                "dimensions": spec.dimensions,
                "rebuild_posture": spec.rebuild_posture,
            },
            "minimum_similarity": None if retriever is None else retriever.minimum_similarity,
            "candidate_limit": None if retriever is None else SEMANTIC_CANDIDATE_LIMIT,
            "ordering": "subordinate: after every relevance and temporal stage (ranking policy 3.2.0)",
            "store": None if store is None else store.posture(),
            "derived_reconciliation": dict(self._derived_reconciliation),
            "authority_effect": "none",
        }

    @_serialized
    def verify_semantic_store(self, *, rebuild: bool = False) -> dict:
        """Recompute every derived vector against the pinned provider (#669)."""

        self._require_open()
        retriever = self._semantic.get("retriever")
        if retriever is None or getattr(retriever, "store", None) is None:
            raise ValueError("semantic retrieval is not enabled on this handle")
        texts = {fact.uuid: fact.fact_text for fact in self.runtime.adapter.checkpoint_substrate().all_facts()}
        return retriever.store.verify(texts, retriever.representation.embed, rebuild=rebuild)

    @_serialized
    def close(self) -> None:
        if self._closed:
            return
        self.runtime.close()
        retriever = self._semantic.get("retriever")
        if retriever is not None and getattr(retriever, "store", None) is not None:
            retriever.store.close()
        self._closed = True

    def __enter__(self) -> "AgentMemory":
        self._require_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
