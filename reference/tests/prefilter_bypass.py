"""Test-only bypass of the #548 domain-eligibility prefilter.

The prefilter keeps domain-ineligible discovery matches from ever becoming candidates.
Full canonical admission still re-applies every domain condition to each candidate, and
that recheck must stay load-bearing, not dead code. Tests that assert admission's own
refusal behavior (reason codes, membership, JS parity) run with the prefilter bypassed,
so they exercise admission directly.

``test_domain_eligibility_prefilter`` separately proves the default, prefiltered
behavior: nothing domain-ineligible reaches callers, and admitted sets are identical
with and without the prefilter.
"""

from __future__ import annotations

from unittest import mock

from agentmem_ref.runtime.adapter import GovernedMemoryAdapter


def admission_only():
    """Patch the shared prefilter to pass every existing fact; admission is unchanged."""

    return mock.patch.object(GovernedMemoryAdapter, "domain_eligible", lambda self, fact, context: fact is not None)
