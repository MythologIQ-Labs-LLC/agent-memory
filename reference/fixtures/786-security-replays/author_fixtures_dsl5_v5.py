"""Author ``cross-scope-write-authority-denial-v5`` (``786-security-replay-dsl/5``), superseding -v4 after its first execution.

The first execution of -v4 at ``a99f1ee7``
(``reports/validation/v7-integration/security-replays-dsl5/``) failed one check:
``W1h ... h_mentions`` observed ``['v1']``. Investigation: the host-layer ``CommitResult`` serialises
the proposal itself, and its ``charter_version`` is ``charter:local-v1``. The bare token ``v1``
matched that string, not a version of the owner's memory, so this is a fixture-token defect, not a
disclosure. The facade results that the -v3 token list was written for never carry the charter.

-v4 is not edited; this generation supersedes it with exactly one change. In W1h ``h_mentions``,
the token ``v1`` becomes ``'v1'``, a version *value* as the result's repr renders it (for example
``'before_state': 'v1'``), which ``charter:local-v1'`` does not contain. Every other byte of every
case is carried over, and contract sources are rehashed at the new base commit. Executed with the
byte-frozen ``run_786_security_replays_dsl5.py``.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE, TARGET = "cross-scope-write-authority-denial-v4", "cross-scope-write-authority-denial-v5"
CASE, PROBE = "W1h-host-built-promotion-naming-the-owners-canonical-memory", "h_mentions"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    base_commit = git("rev-parse", "HEAD")
    raw = (HERE / f"{SOURCE}.json").read_bytes()
    fixture = json.loads(raw)
    out = copy.deepcopy(fixture)
    out.update({
        "replay_id": TARGET,
        "fixture_version": fixture["fixture_version"] + 1,
        "frozen_on": "2026-10-28",
        "status": "supersedes_v4_after_its_first_execution",
        "supersession_reason": (
            "First execution of -v4 at a99f1ee7: W1h h_mentions observed ['v1'], because the bare token matched the "
            "proposal's own charter_version ('charter:local-v1') in the host-layer CommitResult. It was not a version of "
            "the owner's memory. This is a fixture-token defect; -v4 is not edited. The one change: that token becomes "
            "\"'v1'\" (a version value in the result's repr). author_fixtures_dsl5_v5.py."),
        "superseded_fixture": {"path": f"reference/fixtures/786-security-replays/{SOURCE}.json",
                               "sha256": hashlib.sha256(raw).hexdigest()},
        "base_commit": base_commit,
        "contract_sources": [
            {"path": s["path"], "sha256_at_base": hashlib.sha256(subprocess.run(
                ["git", "show", f"{base_commit}:{s['path']}"], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest()}
            for s in fixture["contract_sources"]],
    })
    case = next(c for c in out["cases"] if c["id"] == CASE)
    tokens = case["probes"][PROBE]["tokens"]
    assert tokens.count("v1") == 1, tokens
    tokens[tokens.index("v1")] = "'v1'"
    case["dsl5_disposition"] += " (-v5: the version token is the value 'v1', not the substring v1; see supersession_reason.)"
    (HERE / f"{TARGET}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{TARGET}: {len(out['cases'])} cases; one probe token changed in {CASE}")


if __name__ == "__main__":
    main()
