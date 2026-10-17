"""Run an unchanged benchmark runner with one AgentMemory.open option injected (#819 lane 5).

    LANE_OPEN_OPTION=typed_replacement LANE_COUNTERS=counters.json \
        python with_open_option.py <runner.py> [runner args...]

``LANE_OPEN_OPTION`` is ``off`` or ``typed_replacement``; it is passed as
``unspecified_intent_currentness`` to every ``AgentMemory.open``. Runner and bridge files
are executed as-is (their blobs stay those of the accepted lanes). The wrapper also counts,
per recall, whether any fact carried the cross-fact label and whether the #819 activation
fired, and how many writes declared a typed proposition; counts go to ``LANE_COUNTERS``.
"""

from __future__ import annotations

import atexit
import json
import os
import runpy
import sys
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.runtime.cross_fact_currentness import CROSS_FACT_LABEL, UNSPECIFIED_TYPED_ACTIVATION

OPTION = os.environ.get("LANE_OPEN_OPTION", "off")
COUNTERS = {"open_option": OPTION, "opens": 0, "remembers": 0, "typed_propositions_declared": 0,
            "recalls": 0, "recalls_with_cross_fact_label": 0, "recalls_with_unspecified_activation": 0,
            "facts_with_unspecified_activation": 0}

_open = AgentMemory.open.__func__
_remember = AgentMemory.remember
_recall = AgentMemory.recall


def open_with_option(cls, *args, **kwargs):
    COUNTERS["opens"] += 1
    kwargs.setdefault("unspecified_intent_currentness", OPTION)
    return _open(cls, *args, **kwargs)


def remember(self, *args, **kwargs):
    COUNTERS["remembers"] += 1
    if kwargs.get("proposition") is not None:
        COUNTERS["typed_propositions_declared"] += 1
    return _remember(self, *args, **kwargs)


def recall(self, *args, **kwargs):
    result = _recall(self, *args, **kwargs)
    COUNTERS["recalls"] += 1
    evidence = [(a.get("ranking_evidence") or {}) for a in (result.get("admissions") or {}).values()]
    activated = sum(1 for e in evidence if e.get("cross_fact_activation") == UNSPECIFIED_TYPED_ACTIVATION)
    COUNTERS["recalls_with_cross_fact_label"] += any(e.get("temporal_applicability") == CROSS_FACT_LABEL for e in evidence)
    COUNTERS["recalls_with_unspecified_activation"] += bool(activated)
    COUNTERS["facts_with_unspecified_activation"] += activated
    return result


AgentMemory.open = classmethod(open_with_option)
AgentMemory.remember = remember
AgentMemory.recall = recall


@atexit.register
def _write() -> None:
    target = os.environ.get("LANE_COUNTERS")
    if target:
        Path(target).write_text(json.dumps(COUNTERS, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    sys.path.insert(0, str(Path(script).resolve().parent))
    runpy.run_path(script, run_name="__main__")
