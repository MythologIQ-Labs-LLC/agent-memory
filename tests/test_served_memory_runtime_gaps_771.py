"""#771 minimal reproductions of served-memory product gaps in the governed runtime.

Each test drives the real SQLite-backed ConfiguredCompositionRuntime through the
v2 lifecycle runner and states the behaviour a user would need. They are
``expectedFailure`` because the gaps live in protected candidate generation,
ranking or admission (frozen v6/v7 behaviour) and were NOT patched during
qualification. When a sanctioned runtime change closes a gap, its test turns
into an unexpected success and must be promoted to a normal test.
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_served_memory_lifecycle_scenarios as lifecycle  # noqa: E402

BACKENDS = ("composed-multiroute", "governed-lexical")


def _serve(events, query, *, intent="current", budget=3, backend="composed-multiroute"):
    data = {"schema": lifecycle.SCHEMA, "tenant": "tenant-gap", "project": "proj-gap",
            "purpose": "gap-reproduction", "events": copy.deepcopy(events),
            "queries": [{"id": "q", "query": query, "intent": intent, "budget": budget}]}
    with tempfile.TemporaryDirectory() as tmp:
        run, diag = lifecycle.run_scenarios(data, Path(tmp), revision="gap", lane_id="gap", backend=backend)
    return run["rows"][0]["returned"], diag[0]["beyond_budget"]


def _retain(eid, text, **extra):
    return {"id": eid, "op": "retain", "memory": eid, "text": text, **extra}


class RuntimeGapReproductions(unittest.TestCase):
    def test_baseline_controls_hold(self):
        # Sanity: the harness itself serves an exact, unambiguous match.
        events = [_retain("webhook", "Failed webhook deliveries are retried for up to 24 hours.")]
        for backend in BACKENDS:
            served, _ = _serve(events, "How long are failed webhook deliveries retried?", backend=backend)
            self.assertEqual(served[:1], ["webhook"], backend)

    @unittest.expectedFailure
    def test_G1_function_word_overlap_does_not_fill_a_no_answer_context(self):
        # Holdout H17/H18/H19: unanswerable questions receive a full budget of
        # memories whose only overlap is a function word ("the", "is").
        events = [_retain("bookclub", "Book club is reading The Trial; we meet on Friday."),
                  _retain("room", "The finance review is held in the Ledger Room.")]
        for backend in BACKENDS:
            served, _ = _serve(events, "Who is the data protection officer?", backend=backend)
            self.assertEqual(served, [], backend)

    @unittest.expectedFailure
    def test_G2_elapsed_declared_validity_is_not_served_as_current(self):
        # Holdout H09: a caller-declared window that ended is still served for a
        # current-intent question (design #549: valid_until is evidence, not lifecycle).
        events = [_retain("freeze", "Payments deploys are frozen for the holiday window.",
                          temporal={"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"}),
                  _retain("days", "Payments deploys happen on Tuesdays and Thursdays.")]
        served, _ = _serve(events, "Are payments deploys allowed this Thursday?", intent="current")
        self.assertNotIn("freeze", served)

    @unittest.expectedFailure
    def test_G3_unconfirmed_claim_is_not_ranked_above_the_recorded_fact(self):
        # Holdout H22: quoting a rumor's number ranks the rumor first; source
        # reliability is not represented in ranking.
        events = [_retain("limit", "The public payments API allows 600 requests per minute per merchant."),
                  _retain("rumor", "Someone guessed the payments API limit might be 1000 requests per minute; unconfirmed.")]
        served, _ = _serve(events, "Is the payments API limit 1000 requests per minute?")
        self.assertEqual(served[:1], ["limit"])

    @unittest.expectedFailure
    def test_G4_compound_question_serves_each_required_fact_within_budget(self):
        # Holdout H20: all three required facts are admitted but ranked past a
        # budget of 4, behind facts that overlap more words of the long question.
        events = [
            _retain("limit", "The public payments API allows 600 requests per minute per merchant."),
            _retain("timeout", "Card authorization calls time out after 5 seconds."),
            _retain("amounts", "The ledger stores amounts as integer minor units with a currency code."),
            _retain("fx", "Exchange rates for a refund are fetched hourly and the rate is cached for the flow."),
            _retain("rumor", "Someone guessed the API rate limit for the refund flow might be higher."),
            _retain("incident", "A migration on the ledger in 2023 locked the table and the way we deploy changed."),
        ]
        served, _ = _serve(events, "For a refund flow, what are the API rate limit, the authorization timeout "
                                   "and the way amounts are stored?", budget=4)
        self.assertTrue({"limit", "timeout", "amounts"} <= set(served), served)

    @unittest.expectedFailure
    def test_G5_lexical_ties_do_not_depend_on_write_order(self):
        # governed-lexical breaks score ties by insertion-ordered identifiers,
        # so the served top-1 flips when unrelated history is written earlier.
        a = [_retain("answer", "The ledger database runs PostgreSQL 16."),
             _retain("other", "The ledger database backup job is nightly.")]
        first, _ = _serve(a, "Which database does the ledger run?", backend="governed-lexical", budget=1)
        second, _ = _serve(list(reversed(a)), "Which database does the ledger run?",
                           backend="governed-lexical", budget=1)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
