"""Harness-only helper: the read-path cross-fact mechanism switched off for one recall (#671).

docs/plan-671-evidence-v5.md E2 defines "mechanism off" exactly as the C7 ordering-difference
report (``run_cross_fact_currentness_report.py``) does: ranking policy 3.2.0
(``ExplicitCurrentConstrainedRankingPolicy`` built from the live policy's own fields, version
excluded) substituted for ``runtime_composition.MULTI_ROUTE_RANKING_POLICY`` for the duration of
a ``with mechanism("off")`` block, ignoring cross-fact evidence. The facade reads that module
attribute at call time, so the substitution reaches exactly the recalls inside the block, and the
live policy is restored on exit, including on error (A4).

This module is evaluation tooling. It never ships runtime behaviour: nothing under
``reference/agentmem_ref`` imports it. The two readers below take the facade's recall outcome and
read only ``admissions[ref]["ranking_evidence"]`` (``cross_fact_limitation``,
``cross_fact_refusal_reason``).
"""

from __future__ import annotations

import dataclasses
from contextlib import contextmanager
from typing import Any, Iterator, Mapping

from agentmem_ref.runtime import runtime_composition
from agentmem_ref.runtime.temporal_order_constraints import ExplicitCurrentConstrainedRankingPolicy

MECHANISM_MODES = ("on", "off")


class LegacyRankingPolicy:
    """Policy 3.2.0 with the live policy's parameters; the cross-fact argument is ignored."""

    def __init__(self, live: Any) -> None:
        names = {f.name for f in dataclasses.fields(ExplicitCurrentConstrainedRankingPolicy) if f.init} - {"version"}
        self._policy = ExplicitCurrentConstrainedRankingPolicy(**{name: getattr(live, name) for name in names})

    def rank(self, *args: Any, cross_fact: Any = None, **kwargs: Any) -> Any:
        return self._policy.rank(*args, **kwargs)

    def identity(self) -> dict[str, Any]:
        return self._policy.identity()


@contextmanager
def mechanism(mode: str) -> Iterator[None]:
    """``on``: the live policy (no change). ``off``: policy 3.2.0 for the block, then restored."""

    if mode not in MECHANISM_MODES:
        raise ValueError(f"mechanism mode must be one of {MECHANISM_MODES}, got {mode!r}")
    live = runtime_composition.MULTI_ROUTE_RANKING_POLICY
    if mode == "off":
        runtime_composition.MULTI_ROUTE_RANKING_POLICY = LegacyRankingPolicy(live)
    try:
        yield
    finally:
        runtime_composition.MULTI_ROUTE_RANKING_POLICY = live


def _evidence(recalled: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    return ((recalled.get("admissions") or {}).get(ref) or {}).get("ranking_evidence") or {}


def limited_refs(recalled: Mapping[str, Any]) -> list[str]:
    """Admitted candidates carrying ``cross_fact_limitation``, in the facade's rank order."""

    return [str(ref) for ref in recalled.get("admitted") or () if _evidence(recalled, str(ref)).get("cross_fact_limitation")]


def refusal_counts(recalled: Mapping[str, Any]) -> dict[str, int]:
    """A count per ``cross_fact_refusal_reason`` over every candidate the facade evaluated."""

    counts: dict[str, int] = {}
    for ref in recalled.get("admissions") or {}:
        reason = _evidence(recalled, str(ref)).get("cross_fact_refusal_reason")
        if reason is not None:
            counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items()))


__all__ = ["MECHANISM_MODES", "LegacyRankingPolicy", "mechanism", "limited_refs", "refusal_counts"]
