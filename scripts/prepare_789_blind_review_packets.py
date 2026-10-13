#!/usr/bin/env python3
"""Prepare private, source-verified, label-blinded AMB v6 qualitative packets.

No benchmark executions, scores, provider calls or GitHub Actions. All raw
prompts/contexts and the unblinding key stay OUTSIDE the git checkout.

python scripts/prepare_789_blind_review_packets.py --output-dir /private/path/study-001 --accept-private-material
python scripts/prepare_789_blind_review_packets.py --verify-reviews /private/path/study-001/coordinator/key.json --packet /private/path/study-001/reviewer/packet.json --reviews /private/path/reviewer1.json /private/path/reviewer2.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOSSIER = "reports/benchmarks/audits/789-amb-v6-case-dossiers.json"
FROZEN_DOSSIER_BLOB = "4b0c4e37c28211fa71254fe888030ff8514e2410"
FROZEN_MAIN = "3eebb6d54e2a218c4fd10cf53c52acac8384c3e6"
PROTOCOL = "competitive-qualitative-blind-packet/1"
ARMS = ("agent_memory", "mem0_oss")
VENDOR_MARKERS = re.compile(r"\b(?:agent[\s_-]?memory|mem0|bm25)\b", re.IGNORECASE)


class PacketError(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise PacketError(reason)


def stable_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob(payload: bytes) -> str:
    # Repository .gitattributes: text=auto eol=lf.
    content = payload.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def safe_source(root: Path, path: str) -> Path:
    require(isinstance(path, str) and path.startswith("reports/benchmarks/amb/") and
            path.endswith("/single-turn.json"), "source path outside frozen AMB scope")
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()) and target.is_file(), "invalid source path")
    return target


def locked_write(path: Path, payload: bytes) -> None:
    """Never overwrite, follow a symlink or make reviewer material world-readable."""
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)


def initial_review_forms(packet: dict) -> list[dict]:
    """Unscored, unlocked form skeletons for an actual independent human.

    Two reviewers complete separate copies of this template. Do not auto-fill
    native outcomes, infer any rating or assert human independence.
    """
    from scripts.check_789_qualitative_review import DIMENSIONS
    return [
        {
            "schema_version": "competitive-qualitative-review/1",
            "case_id": item["case_id"],
            "blind_arm": item["blind_arm"],
            "reviewer_id": "REPLACE_WITH_INDEPENDENT_HUMAN_ID",
            "reviewer_kind": "human",
            "reviewed_at_utc": None,
            "locked": False,
            "benchmark_outcome_visible": False,
            "source_trace": item["source_trace"],
            "dimensions": {dim: {"rating": None, "rationale": "", "evidence_refs": []}
                           for dim in DIMENSIONS},
            # Null means NOT EXAMINED. Do not silently start from 'no breach'.
            "safety_flags": {"unauthorized_exposure": None, "deleted_data_exposure": None},
        }
        for item in packet["records"]
    ]


def verify_citations(review: dict, record: dict) -> None:
    """Every claimed evidence span must reference actual blinded source lines."""
    trace = record["source_trace"]
    prefix = re.escape(trace)
    pattern = re.compile(r"^" + prefix + r":(context|prompt):L([1-9][0-9]*)-L([1-9][0-9]*)$")
    lines_by_source = {
        "context": record["retrieved_context"].splitlines(),
        "prompt": record["task_prompt"].splitlines(),
    }
    for dimension, value in review["dimensions"].items():
        for citation in value["evidence_refs"]:
            match = pattern.fullmatch(citation)
            require(match is not None, "unbound or wrong-case evidence citation: " + dimension)
            source, first, last = match.group(1), int(match.group(2)), int(match.group(3))
            lines = lines_by_source[source]
            require(1 <= first <= last <= len(lines), "citation outside original source lines: " + dimension)
            require(any(line.strip() for line in lines[first - 1:last]),
                    "citation points at blank lines only: " + dimension)


def load_verified_sources(root: Path, dossier: dict) -> dict[str, dict]:
    reports = dossier.get("source_reports")
    require(isinstance(reports, list) and len(reports) == 3, "expected three source reports")
    source = {x.get("arm"): x for x in reports if isinstance(x, dict)}
    require(set(source) == {"agent_memory", "mem0_oss", "bm25_control"},
            "incomplete/duplicate named benchmark sources")
    out = {}
    for arm in ARMS:
        record = source[arm]
        path = safe_source(root, record.get("path"))
        content = path.read_bytes()
        require(git_blob(content) == record.get("git_blob_sha"), "pinned source blob mismatch: " + arm)
        data = json.loads(content)
        require(data.get("dataset") == "precisionmembench" and
                data.get("split") == "single-turn" and data.get("mode") == "retrieval",
                "incorrect source profile: " + arm)
        rows = data.get("results")
        require(isinstance(rows, list) and len(rows) == 77 and data.get("total_queries") == 77,
                "incorrect original case population: " + arm)
        ids = [r.get("query_id") for r in rows]
        require(all(isinstance(x, str) and x for x in ids) and len(set(ids)) == 77,
                "duplicate or missing query identities: " + arm)
        require(sum(row.get("correct") is True for row in rows) == data.get("correct"),
                "native pass total mismatch: " + arm)
        out[arm] = {r["query_id"]: r for r in rows}
    require(set(out["agent_memory"]) == set(out["mem0_oss"]), "source case IDs differ")
    for cid in out["agent_memory"]:
        a = out["agent_memory"][cid]
        b = out["mem0_oss"][cid]
        require(a.get("query") == b.get("query") and a.get("gold_answers") == b.get("gold_answers"),
                "source query/gold conflict: " + cid)
    return out


def prepare(root: Path, out_dir: Path, *, dossier_path: Path | None = None) -> dict:
    root = root.resolve()
    target = out_dir.resolve()
    require(not target.is_relative_to(root), "private materials must be outside repository")
    require(not target.exists(), "destination already exists; refuse overwrite")
    require(target.parent.is_dir(), "destination parent must already exist")
    dossier_path = dossier_path or (root / DOSSIER)
    dossier_bytes = dossier_path.read_bytes()
    require(git_blob(dossier_bytes) == FROZEN_DOSSIER_BLOB,
            "pinned preregistered dossier changed; a new study version is required")
    dossier = json.loads(dossier_bytes)
    require(dossier.get("source_main_sha") == FROZEN_MAIN,
            "frozen main evidence revision was changed")
    require(dossier.get("schema_version") == "competitive-case-dossier/1" and
            dossier.get("accepted_score_update") is False and
            dossier.get("qualitative_review_status") == "not_started",
            "unaccepted frozen source dossier required")
    target_ids = dossier.get("review_selection", {}).get("target_case_ids")
    require(isinstance(target_ids, list) and len(target_ids) == 24 and
            len(set(target_ids)) == 24 and all(isinstance(x, str) for x in target_ids),
            "the 24 preregistered cases must remain frozen")
    entries = dossier.get("entries")
    require(isinstance(entries, list) and len(entries) == 77, "77-case dossier required")
    indexed = {x.get("case_id"): x for x in entries}
    require(len(indexed) == 77 and set(target_ids) <= set(indexed),
            "qualitative case selection not in 77-case dossier")
    source = load_verified_sources(root, dossier)
    require(set(source["agent_memory"]) == set(indexed), "dossier and source cases differ")
    require(len({x["case_id"] for x in entries}) == 77,
            "duplicate dossier case identity")
    for cid, row in indexed.items():
        for arm in ARMS:
            require(source[arm][cid]["correct"] is row["arms"][arm]["passed_native_scorer"],
                    "dossier/native verdict mismatch: " + cid + ":" + arm)

    trace_seen: set[str] = set()
    bundle: list[dict] = []
    assignments: list[dict] = []
    for cid in target_ids:
        a = source["agent_memory"][cid]
        b = source["mem0_oss"][cid]
        prompt = a["query"]
        require(isinstance(prompt, str), "missing task prompt: " + cid)
        require(VENDOR_MARKERS.search(prompt) is None,
                "explicit provider name in task prompt: " + cid)
        flipped = bool(secrets.randbits(1))
        for label, system in zip(("A", "B"), (ARMS[::-1] if flipped else ARMS)):
            row = source[system][cid]
            context = row.get("context")
            require(isinstance(context, str) and len(context) <= 200000,
                    "invalid raw retrieval context: " + cid)
            # A vendor-name marker in the submitted context is a direct label leak.
            # Other stylistic/factual deblinding risks still need manual inspection.
            require(VENDOR_MARKERS.search(context) is None,
                    "explicit provider name in raw context: " + cid)
            token = "trace-" + secrets.token_hex(16)
            require(token not in trace_seen, "trace collision")
            trace_seen.add(token)
            bundle.append({
                "case_id": cid,
                "blind_arm": label,
                "task_prompt": prompt,
                "retrieved_context": context,
                "source_trace": token,
            })
            assignments.append({
                "case_id": cid,
                "blind_arm": label,
                "provider_id": system,
                "source_path": next(x["path"] for x in dossier["source_reports"] if x["arm"] == system),
                "source_git_blob": next(x["git_blob_sha"] for x in dossier["source_reports"] if x["arm"] == system),
                "source_trace": token,
                "source_content_sha256": digest(stable_bytes({"query": prompt, "context": context})),
            })
    secrets.SystemRandom().shuffle(bundle)
    packet = {
        "schema_version": PROTOCOL,
        "source_class": "historical_retrieval_context_not_task_answer",
        "benchmark_outcomes_visible": False,
        "gold_answers_visible": False,
        "blinding": "per_case_randomized_labels_only_unverified_stylistic_blinding",
        "required_human_reviewers": 2,
        "locked_form_schema": "competitive-qualitative-review/1",
        "note": (
            "24 purposively chosen cases, two retrieval-only product arms, 48 individual blind "
            "case/arm contexts. No model answers or user task success provided. Reviewers "
            "must mark genuinely unobservable dimensions not_applicable and justify them. "
            "Raw output format may still reveal identity: coordinator must inspect privately."
        ),
        "records": bundle,
    }
    packet_bytes = stable_bytes(packet)
    key = {
        "schema_version": "competitive-qualitative-assignment-key/1",
        "packet_protocol": PROTOCOL,
        "packet_sha256": digest(packet_bytes),
        "dossier_sha256": digest(stable_bytes(dossier)),
        "dossier_git_blob_sha": git_blob(dossier_bytes),
        "source_main_sha": dossier.get("source_main_sha"),
        "frozen_target_case_ids": target_ids,
        "assignments": assignments,
        "note": "PRIVATE COORDINATOR ONLY. Never commit or share before independent reviewer lock.",
    }
    # Create only AFTER verifying every source and all 48 expected rows.
    target.mkdir(mode=0o700)
    (target / "reviewer").mkdir(mode=0o700)
    (target / "coordinator").mkdir(mode=0o700)
    locked_write(target / "reviewer" / "packet.json", packet_bytes)
    locked_write(target / "reviewer" / "forms.PENDING.json",
                 stable_bytes(initial_review_forms(packet)))
    locked_write(target / "coordinator" / "key.json", stable_bytes(key))
    return {
        "status": "private_packet_prepared_not_reviewed",
        "cases": 24, "arms_per_case": 2, "records": len(bundle),
        "completed_human_reviews": 0, "required_human_reviews": 96,
        "packet_sha256": key["packet_sha256"],
        "reviewer_packet": str(target / "reviewer" / "packet.json"),
        "unscored_review_form_template": str(target / "reviewer" / "forms.PENDING.json"),
        "private_coordinator_key": str(target / "coordinator" / "key.json"),
        "warning": "No human work or blinding quality has been certified.",
    }


def verify_reviews(dossier: dict, packet: dict, key: dict, reviews: list[dict]) -> dict:
    """Proof that submitted source_trace tokens match this locked local packet."""
    from scripts.check_789_qualitative_review import review_coverage
    require(key.get("schema_version") == "competitive-qualitative-assignment-key/1" and
            packet.get("schema_version") == PROTOCOL and
            digest(stable_bytes(packet)) == key.get("packet_sha256"), "review packet/key mismatch")
    require(packet.get("benchmark_outcomes_visible") is False and
            packet.get("gold_answers_visible") is False, "unblinding before reviewer lock")
    expected = {(x["case_id"], x["blind_arm"]): x["source_trace"] for x in key["assignments"]}
    require(len(expected) == 48 and len(key["assignments"]) == 48 and
            len(set(expected.values())) == 48, "invalid/colliding blinded assignment traces")
    # The private coordinator key is a separate authority boundary. Even if a
    # packet and its digest are both rewritten, each of the preregistered case
    # arms must still map to exactly one pinned real product/source.
    cases = dossier["review_selection"]["target_case_ids"]
    required_pairs = {(cid, label) for cid in cases for label in ("A", "B")}
    require(set(expected) == required_pairs, "packet includes missing/foreign frozen cases")
    sources = {x["arm"]: x for x in dossier["source_reports"]}
    require(set(sources) == {"agent_memory", "mem0_oss", "bm25_control"},
            "frozen source roster mismatch")
    providers_by_case = {cid: set() for cid in cases}
    for assignment in key["assignments"]:
        provider = assignment.get("provider_id")
        require(provider in ARMS, "unrecognized product in blind coordinator key")
        source = sources[provider]
        require(assignment.get("source_path") == source["path"] and
                assignment.get("source_git_blob") == source["git_blob_sha"],
                "coordinator source identity conflicts with frozen dossier")
        providers_by_case[assignment["case_id"]].add(provider)
    require(all(providers == set(ARMS) for providers in providers_by_case.values()),
            "case arms must contain exactly one of each measured product")
    actual = {(x["case_id"], x["blind_arm"]): x["source_trace"] for x in packet["records"]}
    require(actual == expected and len(packet["records"]) == 48, "packet assignment altered")
    by_case = {}
    for item in packet["records"]:
        by_case.setdefault(item["case_id"], []).append(item["task_prompt"])
    require(all(len(prompts) == 2 and prompts[0] == prompts[1]
                for prompts in by_case.values()),
            "case prompts must match across blind product arms")
    require(key.get("frozen_target_case_ids") == dossier["review_selection"]["target_case_ids"],
            "key is not bound to the frozen selection")
    require(key.get("dossier_sha256") == digest(stable_bytes(dossier)),
            "coordinator key does not match the case dossier")
    require(key.get("dossier_git_blob_sha") == FROZEN_DOSSIER_BLOB and
            key.get("source_main_sha") == dossier.get("source_main_sha"),
            "coordinator key does not match frozen source identity")
    mapping = {(x["case_id"], x["blind_arm"]): x for x in key["assignments"]}
    for item in packet["records"]:
        arm = mapping[(item["case_id"], item["blind_arm"])]
        require(digest(stable_bytes({"query": item["task_prompt"],
                                     "context": item["retrieved_context"]})) ==
                arm.get("source_content_sha256"),
                "original source-content binding is broken")
    require(digest(stable_bytes(packet)) == key["packet_sha256"], "packet bytes changed")
    records = {(item["case_id"], item["blind_arm"]): item for item in packet["records"]}
    for review in reviews:
        require(isinstance(review, dict), "invalid review")
        ident = (review.get("case_id"), review.get("blind_arm"))
        require(ident in expected and review.get("source_trace") == expected[ident],
                "review source trace does not match private packet")
        # The independent structural checker validates the form before citation
        # inspection so malformed/incomplete dimensions fail with typed errors.
        from scripts.check_789_qualitative_review import validate_review
        validate_review(review, set(key["frozen_target_case_ids"]))
        # A review with a copied sample identity or no timestamp cannot be
        # independently sequenced against the coordinator's unblinding event.
        if review["reviewer_kind"] == "human":
            ident_text = review["reviewer_id"].strip()
            require(ident_text != "REPLACE_WITH_INDEPENDENT_HUMAN_ID" and
                    not ident_text.upper().startswith(("REPLACE_", "EXAMPLE_", "TEST_")),
                    "unfinished reviewer identity in locked form")
            stamp = review.get("reviewed_at_utc")
            require(isinstance(stamp, str) and stamp.endswith("Z"),
                    "human review requires explicit UTC lock timestamp")
            try:
                recorded = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise PacketError("invalid reviewer lock timestamp") from exc
            require(recorded.utcoffset() == timedelta(0),
                    "reviewer lock timestamp is not UTC")
        verify_citations(review, records[ident])
    result = review_coverage(dossier, reviews)
    result["packet_integrity"] = "matched"
    result["publication_authorized"] = False
    result["human_identity_and_true_blinding_verified"] = False
    result["release_gate"] = (
        "p0_safety_adjudication_required" if result["cases_with_reported_P0_flags"]
        else "human_independence_and_adjudication_required"
        if result["status"] == "ready_for_independent_adjudication"
        else "incomplete_human_coverage"
    )
    return result


def load_review_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, list), "review submission must be a JSON list")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output-dir", type=Path)
    action.add_argument("--verify-reviews", type=Path, metavar="PRIVATE_KEY_JSON")
    parser.add_argument("--reviews", type=Path, nargs="+",
                        help="one or more independently completed reviewer JSON arrays")
    parser.add_argument("--packet", type=Path, help="private reviewer packet (verify mode)")
    parser.add_argument("--accept-private-material", action="store_true",
                        help="explicitly acknowledge that source contexts must not be committed/shared")
    args = parser.parse_args()
    try:
        dossier_bytes = (ROOT / DOSSIER).read_bytes()
        require(git_blob(dossier_bytes) == FROZEN_DOSSIER_BLOB,
                "frozen study dossier has changed since preregistration")
        dossier = json.loads(dossier_bytes)
        if args.output_dir:
            require(args.accept_private_material, "explicit --accept-private-material required")
            report = prepare(ROOT, args.output_dir)
        else:
            require(args.packet is not None and args.reviews is not None,
                    "--verify-reviews requires --packet and --reviews")
            report = verify_reviews(
                dossier,
                json.loads(args.packet.read_text(encoding="utf-8")),
                json.loads(args.verify_reviews.read_text(encoding="utf-8")),
                [review for source in args.reviews
                 for review in load_review_file(source)],
            )
        print(json.dumps(report, indent=2))
        return 0
    except (PacketError, OSError, ValueError, KeyError, TypeError) as exc:
        print("BLIND QUALITATIVE GATE REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
