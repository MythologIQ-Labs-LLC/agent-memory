#!/usr/bin/env python3
"""Validate the Runtime Baseline register, every record it names, and the open declaration (#638, #674).

For every register entry: the record, boundary and qualification files are readable and
agree on the baseline id and frozen revision; their bytes equal the pinned blobs; the
record's identities equal the protected source at the frozen revision; the record-level
claims hold (no production 1.0, authority_effect none, dogfood evidence, public Gauntlet
qualification either ``pending`` or complete and bound to a verified head); and a
published entry is pinned to a first-parent commit of the candidate whose tree holds the
record and boundary bytes. A declared successor must be openable: the current entry is
complete and pinned, the predecessor matches, and every declared ``from`` is the current
record's value.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_runtime_baseline_equivalence import (  # noqa: E402
    DEFAULT_REGISTER,
    current_entry,
    declaration_open_failures,
    diff_pathspecs,
    load_boundary,
    load_declaration,
    load_register,
    qualification_block,
    require_commit,
)
from runtime_baseline_identity import (  # noqa: E402
    IDENTITY_SOURCES,
    IdentitySource,
    git_blob_sha,
    git_show,
    read_identities,
    record_identities,
)

ROOT = Path(__file__).resolve().parents[1]
PROBE_PROFILE = "gauntlet-orchestration-retrieval-probe-v1"


def expect(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise SystemExit(f"{label} mismatch: frozen source={actual!r}, manifest={expected!r}")


def exact_sha(label: str, value: Any) -> None:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise SystemExit(f"{label} must be an exact lowercase 40-hex SHA")


def file_blob(root: Path, path: str) -> str:
    try:
        return git_blob_sha((root / path).read_bytes())
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc


def blob_at(root: Path, revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{revision}:{path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"{path} is absent at {revision}")
    return result.stdout.strip()


def first_parent_ancestor(root: Path, candidate: str, revision: str) -> bool:
    result = subprocess.run(
        ["git", "rev-list", "--first-parent", candidate],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"unable to walk first-parent history of {candidate}: {result.stderr.strip()}")
    return revision in result.stdout.split()


def require_frozen_runtime_equivalence(root: Path, boundary: dict[str, Any], candidate: str) -> None:
    """Refuse a claimed qualification if the protected surface drifted between freeze and head."""

    diff = subprocess.run(
        ["git", "diff", "--quiet", str(boundary["frozen_revision"]), candidate, "--", *diff_pathspecs(boundary)],
        cwd=root,
        check=False,
    )
    if diff.returncode == 1:
        raise SystemExit(
            f"qualified checkout {candidate} differs from the frozen runtime revision "
            f"{boundary['frozen_revision']} on the protected surface"
        )
    if diff.returncode != 0:
        raise SystemExit("unable to compare qualified checkout to frozen runtime revision")


def validate_identities(
    root: Path, record: dict[str, Any], frozen: str, sources: tuple[IdentitySource, ...]
) -> None:
    source_values = read_identities(root, frozen, sources)
    record_values = record_identities(record, sources)
    for path, value in record_values.items():
        expect(path, source_values[path], value)


def validate_dogfood(root: Path, record: dict[str, Any], frozen: str) -> str:
    dogfood = record["dogfood"]
    if dogfood["status"] != "completed":
        raise SystemExit(f"{record['baseline_id']} cannot close before #637 dogfood is completed")
    if dogfood["authority_effect"] != "none":
        raise SystemExit("dogfood evidence must have authority_effect none")
    if dogfood["evidence_class"] != "baseline_or_probe":
        raise SystemExit("#637 dogfood must remain baseline_or_probe usability evidence")
    dogfood_commit = str(dogfood["merge_commit"])
    if "required_before_issue_638_close" not in dogfood:
        return dogfood_commit
    if dogfood["required_before_issue_638_close"] is not True:
        raise SystemExit("#637 dogfood must remain recorded as a required #638 close gate")
    dogfood_head = dogfood["verified_head"]
    require_commit(root, dogfood_commit, "dogfood merge commit")
    require_commit(root, dogfood_head, "dogfood verified head")
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", frozen, dogfood_commit], cwd=root, check=False)
    if ancestry.returncode:
        raise SystemExit("dogfood merge commit must descend from the frozen runtime revision")
    git_show(root, dogfood_commit, dogfood["golden_evidence"])
    git_show(root, dogfood_commit, "docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md")
    return dogfood_commit


def validate_qualification(
    root: Path, record: dict[str, Any], boundary: dict[str, Any], block: dict[str, Any]
) -> str:
    """Return a short description of the qualification state for the summary line."""

    frozen = str(boundary["frozen_revision"])
    if block["profile_id"] != PROBE_PROFILE:
        raise SystemExit("unexpected Runtime Baseline public Gauntlet profile")
    if block["transport"] != "stdio":
        raise SystemExit("Runtime Baseline public Gauntlet qualification must use stdio")
    if block["status"] == "pending":
        return "public baseline qualification is pending"
    if block["evidence_class"] != "baseline_or_probe":
        raise SystemExit("Runtime Baseline public Gauntlet evidence must remain baseline_or_probe")
    if block["authority_effect"] != "none":
        raise SystemExit("Runtime Baseline public Gauntlet evidence must have authority_effect none")
    if int(block["workflow_run"]) <= 0 or int(block["artifact_id"]) <= 0:
        raise SystemExit("Runtime Baseline public Gauntlet workflow/artifact IDs must be positive")
    digest = str(block["artifact_digest"])
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SystemExit("Runtime Baseline public Gauntlet artifact digest must be exact sha256")
    verified_head = block["verified_head"]
    require_commit(root, verified_head, "Runtime Baseline public Gauntlet verified head")
    if subprocess.run(["git", "merge-base", "--is-ancestor", frozen, verified_head], cwd=root, check=False).returncode:
        raise SystemExit("public Gauntlet verified head must descend from the frozen runtime revision")
    require_frozen_runtime_equivalence(root, boundary, verified_head)

    manifest_path = block["manifest"]
    adapter_path = block["adapter_source"]
    qualified_manifest = json.loads(git_show(root, verified_head, manifest_path))
    adapter_source = git_show(root, verified_head, adapter_path)
    expect("public Gauntlet system revision", qualified_manifest["system"]["revision"], block["system_revision"])
    expect("public Gauntlet adapter revision", qualified_manifest["adapter"]["revision"], block["adapter_revision"])
    expect("public Gauntlet transport", qualified_manifest["transport"]["kind"], block["transport"])
    expect("public Gauntlet baseline id", qualified_manifest["metadata"]["baseline_id"], record["baseline_id"])
    expect("public Gauntlet frozen runtime binding", block["system_revision"], f"git-commit:{frozen}")
    expect("public Gauntlet exact adapter blob", block["adapter_revision"], f"git-blob:{git_blob_sha(adapter_source)}")
    if int(block["sample_count"]) != 3:
        raise SystemExit("public Gauntlet orchestration probe must record its three-query sample count")
    if not 0.0 <= float(block["exact_top1"]) <= 1.0:
        raise SystemExit("public Gauntlet exact_top1 must be a bounded observed metric")
    return f"public baseline qualification is bound at workflow {block['workflow_run']}"


def validate_entry(
    root: Path,
    register: dict[str, Any],
    index: int,
    candidate: str,
    sources: tuple[IdentitySource, ...],
) -> str:
    entry = register["baselines"][index]
    is_last = index == len(register["baselines"]) - 1
    baseline_id = entry["baseline_id"]
    try:
        record = json.loads((root / entry["record"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unable to load runtime baseline record {entry['record']}: {exc}") from exc
    boundary = load_boundary(root, entry["source_boundary"])
    frozen = str(boundary["frozen_revision"])

    if record.get("baseline_id") != baseline_id or boundary.get("baseline_id") != baseline_id:
        raise SystemExit(f"register entry {baseline_id} names a record or boundary with a different baseline_id")
    commit = record["runtime_revision"]["commit"]
    exact_sha("runtime revision", commit)
    if commit != frozen:
        raise SystemExit(f"{baseline_id}: record runtime_revision.commit {commit} != boundary frozen_revision {frozen}")
    require_commit(root, frozen, f"{baseline_id} runtime revision")

    expect(f"{baseline_id} record blob", file_blob(root, entry["record"]), entry["record_blob"])
    expect(f"{baseline_id} source boundary blob", file_blob(root, entry["source_boundary"]), entry["source_boundary_blob"])
    expect(f"{baseline_id} qualification blob", file_blob(root, entry["qualification"]["path"]), entry["qualification"]["blob"])

    validate_identities(root, record, frozen, sources)
    if record["production_1_0"]:
        raise SystemExit("baseline source may not claim production 1.0")
    if record["authority_effect"] != "none":
        raise SystemExit("baseline authority_effect must remain none")
    dogfood_commit = validate_dogfood(root, record, frozen)

    block = qualification_block(root, entry)
    pending = block["status"] == "pending"
    if pending and not is_last:
        raise SystemExit(f"{baseline_id}: only the last register entry may carry a pending qualification")

    published = entry["published_commit"]
    if published is None:
        if not pending:
            raise SystemExit(f"{baseline_id}: a complete qualification requires published_commit")
    else:
        require_commit(root, published, f"{baseline_id} published commit")
        if not first_parent_ancestor(root, candidate, published):
            raise SystemExit(f"{baseline_id}: published_commit {published} is not on the first-parent history of {candidate}")
        expect(f"{baseline_id} record blob at published commit", blob_at(root, published, entry["record"]), entry["record_blob"])
        expect(
            f"{baseline_id} source boundary blob at published commit",
            blob_at(root, published, entry["source_boundary"]),
            entry["source_boundary_blob"],
        )
    qualification_summary = validate_qualification(root, record, boundary, block)
    return (
        f"{baseline_id} identities match frozen revision {frozen}; "
        f"#637 dogfood is evidence-bound at {dogfood_commit}; {qualification_summary}"
    )


def validate_register(
    root: Path,
    register_path: Path | str = DEFAULT_REGISTER,
    candidate: str = "HEAD",
    sources: tuple[IdentitySource, ...] = IDENTITY_SOURCES,
) -> list[str]:
    register = load_register(root, register_path)
    summaries = [validate_entry(root, register, index, candidate, sources) for index in range(len(register["baselines"]))]
    declared = register.get("declared_successor")
    if declared is not None:
        declaration = load_declaration(root, declared["declaration"])
        if declaration["baseline_id"] != declared["baseline_id"]:
            raise SystemExit(
                f"register declares successor {declared['baseline_id']} but {declared['declaration']} declares {declaration['baseline_id']}"
            )
        entry = current_entry(register)
        record = json.loads((root / entry["record"]).read_text(encoding="utf-8"))
        failures = declaration_open_failures(root, register, record, declaration)
        if failures:
            raise SystemExit("\n".join(failures))
        summaries.append(f"declared successor {declaration['baseline_id']} (issue #{declaration['issue']}) is open")
    return summaries


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--candidate", default="HEAD")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    for line in validate_register(root, args.register, args.candidate):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
