"""#771 independent holdout ("Halcyon payments"), authored by the cloud reviewer.

Frozen BEFORE any run against it and before any runtime change. It was not
used to design the runtime, the v1 fixtures or the scorer. Wording is
deliberately natural (paraphrase, unseen terminology, lexical traps); no
phrasing was tuned against retrieval output.

Writes two files next to this script:
  halcyon-holdout-v1-input.json  execution-only lifecycle history + questions
  halcyon-holdout-v1-gold.json   graded relevance, critical groups, stale/prohibited

Grades: 3 = directly answers, 2 = necessary/strong support, 1 = topical
context only (never an answer), 0 = irrelevant (default for every fact).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TENANT, PROJECT = "acme", "halcyon"

EVENTS = [
    ("adr-db-v1", "retain", "adr-db", "ADR-003, written in 2016: we chose MySQL 5.6 as the ledger database because the team already operated it and its replication was well understood.", {}),
    ("adr-db-v2", "correct", "adr-db", "ADR-003 was superseded by ADR-019 in 2021: the ledger moved to PostgreSQL because we needed transactional DDL and native JSON columns.", {}),
    ("pgver-13", "retain", "pg-version", "The ledger database runs PostgreSQL 13.", {}),
    ("pgver-15", "correct", "pg-version", "The ledger database runs PostgreSQL 15 after the March 2024 upgrade.", {}),
    ("pgver-16", "correct", "pg-version", "The ledger database runs PostgreSQL 16 after the January 2026 upgrade.", {}),
    ("bus", "retain", "bus", "Payment events are published to the Kafka topic ledger-events, which has 12 partitions.", {}),
    ("bus-why", "retain", "bus-why", "In 2019 we picked Kafka over RabbitMQ because auditors require us to replay a full week of payment events.", {}),
    ("oncall-platform", "retain", "oncall", "The payments on-call rotation is owned by the Platform team.", {}),
    ("oncall-lrt", "correct", "oncall", "Since April 2025 the payments on-call rotation is owned by the Ledger Reliability team.", {}),
    ("ratelimit", "retain", "ratelimit", "The public payments API allows 600 requests per minute per merchant.", {}),
    ("ratelimit-rumor", "retain", "ratelimit-rumor", "Someone in chat guessed the payments API limit might be 1000 requests per minute; nobody confirmed it.", {}),
    ("authz-8s", "retain", "authz-timeout", "Card authorization calls time out after 8 seconds.", {}),
    ("authz-5s", "correct", "authz-timeout", "Card authorization calls now time out after 5 seconds to stay inside the processor SLA.", {}),
    ("freeze-bf25", "retain", "freeze-bf25", "Deploys to the payments cluster are frozen for the Black Friday window.", {"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"}),
    ("deploy-days", "retain", "deploy-days", "Production deploys for payments happen on Tuesdays and Thursdays.", {}),
    ("stripe-key", "retain", "stripe-key", "The staging Stripe API key is sk_test_51HalcyonStagingKey.", {}),
    ("stripe-key-del", "delete", "stripe-key", None, {}),
    ("inc-2207", "retain", "inc-2207", "Incident INC-2207 in 2023: a schema migration locked the ledger table for 40 minutes, so ledger migrations must now be online and batched.", {}),
    ("migration-rule", "retain", "migration-rule", "Ledger schema changes run through the online migration tool and need a DBA reviewer before merge.", {}),
    ("mobile-rate", "retain", "mobile-rate", "The mobile app API allows 120 requests per minute per device.", {"project": "mobile"}),
    ("mobile-oncall", "retain", "mobile-oncall", "The mobile app on-call rotation is owned by the Apps team.", {"project": "mobile"}),
    ("globex-db", "retain", "globex-db", "The ledger database runs Oracle 19c.", {"tenant": "globex"}),
    ("room", "retain", "room", "The Ledger Room on the third floor is booked for the quarterly finance review.", {}),
    ("bookclub", "retain", "bookclub", "Book club is reading Kafka's The Trial; we meet on Friday.", {}),
    ("money-repr", "retain", "money-repr", "The ledger stores amounts as integer minor units together with an ISO 4217 currency code.", {}),
    ("fx-fetch", "retain", "fx-fetch", "Exchange rates are fetched hourly from the ECB feed and cached for 60 minutes.", {}),
    ("fx-why", "retain", "fx-why", "We cache exchange rates for an hour because the ECB publishes once per business day and rate-limit errors from the feed broke checkout in 2022.", {}),
    ("region-eu", "retain", "region", "The payments service is deployed only in eu-west-1.", {}),
    ("region-eu-us", "correct", "region", "Since the 2024 expansion the payments service runs in eu-west-1 and us-east-1.", {}),
    ("region-draft", "retain", "region-draft", "A draft proposal suggested adding ap-southeast-2 for payments, but it was never approved.", {}),
    ("pci", "retain", "pci", "We never store card numbers; only processor tokens are kept so we stay in PCI SAQ-A scope.", {}),
    ("webhook-retry", "retain", "webhook-retry", "Failed webhook deliveries are retried with exponential backoff for up to 24 hours.", {}),
]

FACTS = [e[0] for e in EVENTS if e[1] != "delete"]
SUPERSEDED = ["adr-db-v1", "pgver-13", "pgver-15", "oncall-platform", "authz-8s", "region-eu"]
EXPIRED = ["freeze-bf25"]  # caller-declared validity window ended before "now"
PROHIBITED = ["stripe-key", "mobile-rate", "mobile-oncall", "globex-db"]

# id, query, intent, budget, {fact: grade}, critical groups, stratum
QUERIES = [
    ("H01", "Which PostgreSQL version does the ledger run on right now?", "current", 3,
     {"pgver-16": 3, "pgver-15": 1, "pgver-13": 1, "adr-db-v2": 1, "globex-db": 2}, [["pgver-16"]], "changing-fact-current"),
    ("H02", "What PostgreSQL version was the ledger on before the most recent upgrade?", "historical", 3,
     {"pgver-15": 3, "pgver-16": 2, "pgver-13": 1}, [["pgver-15"]], "changing-fact-history"),
    ("H03", "Why did the team originally choose MySQL for the ledger?", "historical", 3,
     {"adr-db-v1": 3, "adr-db-v2": 2}, [["adr-db-v1"]], "decision-why-history"),
    ("H04", "What motivated the ledger's move away from MySQL?", "historical", 3,
     {"adr-db-v2": 3, "adr-db-v1": 2}, [["adr-db-v2"]], "decision-why-history"),
    ("H05", "Why do we use Kafka instead of RabbitMQ for payment events?", "timeless", 3,
     {"bus-why": 3, "bus": 1}, [["bus-why"]], "decision-why"),
    ("H06", "Who currently owns the payments on-call rotation?", "current", 2,
     {"oncall-lrt": 3, "oncall-platform": 1, "mobile-oncall": 1}, [["oncall-lrt"]], "changing-fact-current"),
    ("H07", "What is the request limit for the public payments API?", "current", 3,
     {"ratelimit": 3, "ratelimit-rumor": 1, "mobile-rate": 2}, [["ratelimit"]], "unreliable-source"),
    ("H08", "How long before a card authorization request times out?", "current", 2,
     {"authz-5s": 3, "authz-8s": 1}, [["authz-5s"]], "correction-current"),
    ("H09", "Can we deploy the payments service to production this Thursday?", "current", 3,
     {"deploy-days": 3, "freeze-bf25": 2}, [["deploy-days"]], "expired-window"),
    ("H10", "What process must a ledger schema migration follow, and why?", "timeless", 3,
     {"migration-rule": 3, "inc-2207": 3}, [["migration-rule"], ["inc-2207"]], "multi-fact-why"),
    ("H11", "How are monetary amounts represented in the ledger?", "timeless", 2,
     {"money-repr": 3}, [["money-repr"]], "single-fact"),
    ("H12", "Why are exchange rates cached for an hour?", "timeless", 3,
     {"fx-why": 3, "fx-fetch": 2}, [["fx-why"]], "decision-why"),
    ("H13", "Which AWS regions run the payments service today?", "current", 3,
     {"region-eu-us": 3, "region-eu": 1, "region-draft": 1}, [["region-eu-us"]], "changing-fact-current"),
    ("H14", "Where was the payments service deployed before the 2024 expansion?", "historical", 3,
     {"region-eu": 3, "region-eu-us": 2}, [["region-eu"]], "correction-history"),
    ("H15", "Do we keep customers' card numbers?", "timeless", 2,
     {"pci": 3}, [["pci"]], "paraphrase"),
    ("H16", "For how long do we keep retrying a failed webhook delivery?", "timeless", 2,
     {"webhook-retry": 3}, [["webhook-retry"]], "single-fact"),
    ("H17", "Who is the payments team's data protection officer?", "current", 3,
     {}, [], "no-answer"),
    ("H18", "What is the staging Stripe API key?", "current", 3,
     {"stripe-key": 3}, [], "no-answer-deleted"),
    ("H19", "Who owns the mobile app on-call rotation?", "current", 3,
     {"mobile-oncall": 3, "oncall-lrt": 1}, [], "no-answer-cross-project"),
    ("H20", "For a refund flow, what are the API rate limit, the authorization timeout and the way amounts are stored?", "current", 4,
     {"ratelimit": 3, "authz-5s": 3, "money-repr": 3, "authz-8s": 1, "ratelimit-rumor": 1}, [["ratelimit"], ["authz-5s"], ["money-repr"]], "multi-fact-current"),
    ("H21", "What message bus carries money-movement events and how many shards does it have?", "timeless", 3,
     {"bus": 3, "bus-why": 1}, [["bus"]], "unseen-terminology"),
    ("H22", "Is the payments API limit 1000 requests per minute?", "current", 3,
     {"ratelimit": 3, "ratelimit-rumor": 1}, [["ratelimit"]], "contradiction"),
    ("H23", "Why can't we run a plain ALTER TABLE on the ledger?", "timeless", 3,
     {"inc-2207": 3, "migration-rule": 2}, [["inc-2207"]], "decision-why"),
    ("H24", "Where is the quarterly finance review held?", "timeless", 2,
     {"room": 3}, [["room"]], "distractor-domain"),
]


def build() -> tuple[dict, dict, dict]:
    events = []
    for eid, op, memory, text, extra in EVENTS:
        event = {"id": eid, "op": op, "memory": memory}
        if text is not None:
            event["text"] = text
        temporal = {k: extra[k] for k in ("valid_from", "valid_until") if k in extra}
        if temporal:
            event["temporal"] = temporal
        for key in ("project", "tenant"):
            if key in extra:
                event[key] = extra[key]
        events.append(event)
    inputs = {"schema": "served-memory-lifecycle-v2", "tenant": TENANT, "project": PROJECT,
              "purpose": "halcyon-engineering-assistant", "events": events,
              "queries": [{"id": q, "query": text, "intent": intent, "budget": budget}
                          for q, text, intent, budget, *_ in QUERIES]}
    cases, strata = [], {}
    for qid, text, intent, budget, grades, groups, stratum in QUERIES:
        unknown = set(grades) - set(FACTS)
        assert not unknown, unknown
        relevance = {fact: grades.get(fact, 0) for fact in FACTS}
        stale = sorted(SUPERSEDED + EXPIRED) if intent == "current" else []
        eligible = [f for f, g in relevance.items() if g >= 2 and f not in PROHIBITED and f not in stale]
        cases.append({"id": qid, "scenario": text, "intent": intent, "budget": budget,
                      "relevance": relevance, "critical_groups": groups,
                      "prohibited": list(PROHIBITED), "stale": stale,
                      "safe_answer_exists": bool(groups and eligible)})
        strata[qid] = stratum
    gold = {"schema": "served-memory-quality-v1", "cases": cases}
    return inputs, gold, strata


# v1.1 (added after the first v1 run, disclosed in the report): v1 encoded
# every value change as `correct`, i.e. a runtime ERROR correction ("the old
# value was false"). That contradicts v1's own gold, which credits the old
# values for historical questions. These six events are real-world state
# changes, so v1.1 replays them as `update` (replacement_kind=state_change).
# Questions, budgets, intents and gold are byte-identical to v1.
STATE_CHANGES = ("adr-db-v2", "pgver-15", "pgver-16", "oncall-lrt", "authz-5s", "region-eu-us")


def build_v1_1(inputs: dict) -> dict:
    import copy
    data = copy.deepcopy(inputs)
    for event in data["events"]:
        if event["id"] in STATE_CHANGES:
            assert event["op"] == "correct"
            event["op"] = "update"
    return data


def main() -> None:
    inputs, gold, strata = build()
    for name, doc in (("input", inputs), ("gold", gold), ("strata", strata)):
        (HERE / f"halcyon-holdout-v1-{name}.json").write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (HERE / "halcyon-holdout-v1.1-input.json").write_text(
        json.dumps(build_v1_1(inputs), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
