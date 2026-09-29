"""#598 collateral-drift check: write interpreter 1.0.0 (base) vs 1.1.0 (working tree) on natural writes.

For every write, compares the full ``interpret_write`` output and the persisted form with
``markers.aspect`` and the (unpersisted) ``aspect_scope`` diagnostic removed. Any difference is
drift outside temporal aspect and is a review blocker. Also checks that 1.1.0 never introduces an
aspect regime that 1.0.0 did not report (1.1.0 may only withhold).

Usage (repository root):
  PYTHONPATH=reference python3 reports/benchmarks/replays/598-write-time-temporal-aspect/interpreter_drift.py \
      594 OUT.json
  PYTHONPATH=reference python3 reports/benchmarks/replays/598-write-time-temporal-aspect/interpreter_drift.py \
      /path/to/longmemeval_s_cleaned.json OUT.json
"""

from __future__ import annotations

import collections
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE_SHA = "0103b9f3ba0ab90c4914837dcb98a9cdad7c4c2a"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import proposition_semantics as v110  # noqa: E402


def _load_base():
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_SHA}:reference/agentmem_ref/runtime/proposition_semantics.py"],
                            capture_output=True, text=True, check=True).stdout
    path = Path(tempfile.mkdtemp()) / "proposition_semantics_v1_0_0.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("agentmem_ref.runtime._proposition_semantics_v1_0_0", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _non_aspect(out: dict) -> dict:
    out = copy.deepcopy(out)
    out.pop("aspect_scope", None)
    out.pop("interpreter", None)
    markers = out.get("markers") or {}
    markers.pop("aspect", None)
    if not markers:
        out.pop("markers", None)
    return out


def _persisted_non_aspect(module, out: dict) -> dict:
    stored = copy.deepcopy(module.persisted_form(out))
    stored.pop("version")
    markers = stored.get("markers") or {}
    markers.pop("aspect", None)
    if not markers:
        stored.pop("markers", None)
    return stored


def _regimes(out: dict) -> list[str]:
    return sorted((out.get("markers") or {}).get("aspect") or {})


def _texts(corpus: str) -> dict[str, str]:
    if corpus == "594":
        sample = ROOT / "reference" / "fixtures" / "benchmarks" / "proposition-semantics" / "sample-v1.json"
        return {item["item_id"]: item["text"] for item in json.loads(sample.read_text(encoding="utf-8"))["items"]}
    texts: dict[str, str] = {}
    seen: set[str] = set()
    for question in json.loads(Path(corpus).read_text(encoding="utf-8")):
        for session in question["haystack_sessions"]:
            for turn in session:
                if turn["content"] not in seen:
                    seen.add(turn["content"])
                    texts[f"{turn['role']}:{len(texts)}"] = turn["content"]
    return texts


def main(corpus: str, out_path: str) -> None:
    v100 = _load_base()
    assert (v100.INTERPRETER_VERSION, v110.INTERPRETER_VERSION) == ("1.0.0", "1.1.0")
    texts = _texts(corpus)
    started = time.time()
    drift, persisted_drift, introduced, changed = [], [], [], 0
    transitions, statuses, reasons = collections.Counter(), collections.Counter(), collections.Counter()
    hashes = {}
    for key, text in texts.items():
        a, b = v100.interpret_write(text), v110.interpret_write(text)
        if _non_aspect(a) != _non_aspect(b):
            drift.append(key)
        if _persisted_non_aspect(v100, a) != _persisted_non_aspect(v110, b):
            persisted_drift.append(key)
        before, after = _regimes(a), _regimes(b)
        if not set(after) <= set(before):
            introduced.append(key)
        changed += before != after
        transitions["+".join(before) or "none", "+".join(after) or "none"] += 1
        statuses[b["aspect_scope"]["status"]] += 1
        reasons.update(d["reason"] for d in b["aspect_scope"].get("declined", ()))
        if corpus == "594":
            hashes[key] = hashlib.sha256(json.dumps(_non_aspect(a), sort_keys=True, separators=(",", ":"))
                                         .encode()).hexdigest()
    report = {
        "base_sha": BASE_SHA,
        "corpus": "#594 accepted sample (268)" if corpus == "594" else "LongMemEval_S unique haystack turns (user+assistant)",
        "writes": len(texts),
        "seconds": round(time.time() - started, 1),
        "non_aspect_interpretation_drift": len(drift),
        "drift_items": drift[:50],
        "persisted_form_non_aspect_drift": len(persisted_drift),
        "aspect_regime_introduced_by_1_1_0": len(introduced),
        "introduced_items": introduced[:50],
        "writes_with_changed_aspect_regimes": changed,
        "regime_transitions_v100_to_v110": {f"{k[0]}->{k[1]}": v for k, v in sorted(transitions.items())},
        "aspect_scope_status_v110": dict(sorted(statuses.items())),
        "declined_reason_counts_v110": dict(sorted(reasons.items())),
    }
    if hashes:
        report["v1_0_0_non_aspect_sha256_by_item"] = hashes
    Path(out_path).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print({k: v for k, v in report.items() if not k.endswith("_by_item")})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
