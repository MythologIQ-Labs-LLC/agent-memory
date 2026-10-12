# #771 Cedarline v1.1: pre-execution answerability clarification

**Declared before any benchmark execution.** This is a separately versioned
correction, not an overwrite of frozen v1. Both v1 input and gold remain
unchanged and will remain reviewable.

## Exact issue

Version 1's C11 asks "Is the 2025 winter firmware freeze still active
today?" Its own explicitly declared 2025-12-01 expiry is sufficient evidence
to answer "no" under a 2026 present-time reference. Labeling the question
"no-safe-answer" confuses no *currently active* freeze with no *answer to
whether an earlier freeze ended*. It would reward a system for omitting useful
historical evidence. This was identified during independent author audit
before any results were inspected, and **is a gold/intent error, not a
measured runtime bug**.

Version 1.1 instead asks: "**What firmware deployment freeze is currently
in effect at Cedarline?**" The historical interval cannot prove the
existence of an active freeze. A useful answer would require current
admissible evidence not present in this synthetic corpus, so it is
appropriately an unanswered current-state lookup. It does not imply
that *no freeze exists anywhere*.

## Immutable change inventory

- Exactly one input question changed: C11 wording.
- Exactly one gold field changed: C11 `scenario` to match the new question.
- All **32 events**, **31 fact IDs**, **24 query IDs**, budgets, temporal
  intents, graded relevance, required groups, stale/prohibited sets and
  strata remain byte-for-byte the same when compared as parsed fields.
- No runtime source change. No v1 or v1.1 execution as of this freeze.

| Artifact | Git blob SHA |
|---|---|
| v1 input | `b08e05d3250a8fa032a8e7f5f5f0030a9c5b637a` |
| v1 gold | `1da8e7eb40a84a04604bcd21a820ef9688607312` |
| v1.1 input | `9c6524441b4b99633304b113b44dfa4d67c9ada8` |
| v1.1 gold | `54b00f621fd526d606963484319decc43dccf316` |

Use **v1.1** for primary independent evaluation of a new runtime. Retain
v1 only as historical preregistration provenance. Do not silently replace
these labels after observing v1.1 output. A third-party adjudicator must
still review question intent, factual support and value of abstention,
especially on existential/no-safe-answer queries.

No official same-harness qualification or acceptance is inferred.
