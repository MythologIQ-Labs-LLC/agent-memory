"""Drive the doctrine fixture corpus through the adapter's enforcement code.

The governance-path tests assert that the adapter behaves correctly on
scenarios written alongside the adapter. This module does something harder:
it takes the repository's independently authored conformance fixtures and
runs their declared authority envelopes through the *same* enforcement
function the adapter uses in production, `receipts.enforce_selection`.

That distinction matters. A test suite written by the same hand as the code
can agree with itself. The fixture corpus was written to describe doctrine,
not to satisfy this implementation, so agreement between them is evidence
rather than tautology.

What is checked, per fixture carrying an authority envelope:

1. permitted and prohibited action sets are disjoint;
2. the declared selection is a member of the permitted set, enforced by the
   adapter's own membership rule rather than a reimplementation of it;
3. the declared selection is not a prohibited action;
4. every prohibited action is *rejected* by that same enforcement rule; and
5. a fixture expecting no crystallization does not permit one.

What is not checked is listed in `exemptions()`. Decay, calibration, retrieval
ranking, and lifecycle transition mechanics are outside this adapter, and a
runner that silently skipped them would misrepresent its own coverage.

Stdlib only apart from schema validation reached through `receipts`.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import receipts

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixtures(fixture_dir: Path | None = None) -> list[tuple[str, dict]]:
    directory = fixture_dir or FIXTURE_DIR
    return [
        (path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(directory.glob("*.json"))
    ]


def _envelopes(fixture: dict) -> list[tuple[str, dict]]:
    """Every authority envelope a fixture declares, named by where it came from."""
    found: list[tuple[str, dict]] = []
    governed = fixture.get("governed_uncertainty")
    if isinstance(governed, dict):
        found.append(("governed_uncertainty", governed))
    authority = fixture.get("memory_unit", {}).get("authority")
    if isinstance(authority, dict) and ("permitted_actions" in authority or "prohibited_actions" in authority):
        found.append(("memory_unit.authority", authority))
    return found


def check_envelope(source: str, envelope: dict) -> list[str]:
    permitted = tuple(envelope.get("permitted_actions") or ())
    prohibited = tuple(envelope.get("prohibited_actions") or ())
    selected = envelope.get("selected_action")
    failures: list[str] = []

    overlap = sorted(set(permitted) & set(prohibited))
    if overlap:
        failures.append(f"{source}: actions both permitted and prohibited: {overlap}")

    if selected is not None:
        if selected in prohibited:
            failures.append(f"{source}: selected action {selected!r} is prohibited")
        try:
            receipts.enforce_selection(permitted, selected)
        except ValueError as exc:
            failures.append(f"{source}: {exc}")

    # The enforcement rule must actively refuse every prohibited action.
    for action in prohibited:
        try:
            receipts.enforce_selection(permitted, action)
        except ValueError:
            continue
        failures.append(f"{source}: enforcement accepted prohibited action {action!r}")

    return failures


def check_fixture(fixture: dict) -> list[str]:
    failures: list[str] = []
    envelopes = _envelopes(fixture)
    for source, envelope in envelopes:
        failures.extend(check_envelope(source, envelope))

    expected = fixture.get("expected_behavior")
    if isinstance(expected, dict) and expected.get("crystallized") is False:
        for source, envelope in envelopes:
            permitted = tuple(envelope.get("permitted_actions") or ())
            crystallizing = [action for action in permitted if action.startswith("crystallize")]
            if crystallizing:
                failures.append(
                    f"{source}: fixture expects no crystallization but permits {crystallizing}"
                )
    return failures


def exemptions() -> list[str]:
    return [
        "Decay, saturation scoring, and calibration are not implemented by this adapter, "
        "so fixtures exercising them are checked only for envelope enforcement.",
        "Retrieval ranking is not exercised: the adapter's recall uses lexical matching, "
        "not the substrate's hybrid search.",
        "Lifecycle transition mechanics beyond commit, supersession, pruning, and deletion "
        "are not driven through the adapter.",
        "Fixtures without a declared authority envelope contribute structural coverage only.",
    ]


def run(fixture_dir: Path | None = None) -> dict:
    """Execute the corpus and summarize per-fixture results."""
    results: dict[str, list[str]] = {}
    with_envelope = 0
    for name, fixture in load_fixtures(fixture_dir):
        if _envelopes(fixture):
            with_envelope += 1
        results[name] = check_fixture(fixture)

    passed = sorted(name for name, failures in results.items() if not failures)
    failed = sorted(name for name, failures in results.items() if failures)
    return {
        "fixtures_run": sorted(results),
        "fixtures_passed": passed,
        "fixtures_failed": failed,
        "failures": {name: results[name] for name in failed},
        "fixtures_with_authority_envelope": with_envelope,
    }
