# #774 historical predecessor target: explicit successor identity policy

**Owner decision, 2026-10-12:** A question targeting the predecessor of
an **older, non-current version** MUST identify the target successor through
a governed fact UUID, or supply a sufficiently precise as-of date that can
resolve the successor under the same tenant/project scope and versioned
temporal policy. If neither resolves to an unambiguous, visible successor,
**return no asserted predecessor**.

Do **not** respond with "there was no predecessor"; unresolved targeting is
not evidence of a fact's historical absence. Ordinary governed historical
recall may return its unchanged ranked evidence as a fallback, but the
predecessor selector must not promote a guessed fact to rank one and must
set predecessor_ref/successor_ref to null, with no completeness assertion.

The current experimental #774 API implicitly anchors to the current head
or a head derived from a lexical top-k match. That is unsound for queries
such as blind theatre Q19, asking about the price **before a recorded £28
version** when another version later succeeded it. The wrongly selected
predecessor loses rank-one quality that frozen v7 got right. Blind Q15/Q16
likewise expose wrong-subject anchors.

## Policy and compatibility

- Require an explicit successor_ref for relation-specific promotion in
  the strict API, unless a **separately versioned**, qualified as-of target
  maps uniquely to a governed successor fact. If the caller supplies
  a date with ambiguous versions or no admitted fact, fail unresolved.
- Verify admission and logical-generation membership before resolving
  a predecessor, including #776 deletion and re-created memory IDs.
  Never cross a deleted-lineage boundary.
- An older-version query is not automatically equivalent to "before
  the current version." A query mentioning a historical value is *not*
  permission to anchor to the latest head.
- Existing free-form lexical temporal cues may classify a request as
  historical, but do **not** identify its required successor fact.
  Automatic predecessor routing remains disabled for promotion unless
  provenance-backed targeting qualifies independently.
- Do not make original #774's "latest predecessor" test cases disappear.
  Existing generic historical retrieval remains available; the legacy
  unqualified opt-in method should be versioned or explicitly deprecated
  rather than silently changing accepted external semantics.
- A future typed/caller-declared "predecessor of CURRENT version" mode
  may select the current head, but must prove a canonical subject
  identity and caller intent first, rather than inferring it from a phrase.

## Preregistered test contract

Branch evaluation/774-strict-predecessor-target-contract-no-ci is based on
#774 @ a6745a9218a46f99d57a049ed9203294f96959af.

Four tests in reference/tests/test_774_strict_successor_target_contract.py:

1. Explicit older successor reference yields its true immediate predecessor.
2. Without an anchored successor, a historical question cannot claim
   predecessor_ref and must leave normal historical top-k unchanged.
3. A query with a genuine lexical "before" cue, but ambiguous target,
   must not activate automatic predecessor promotion.
4. An explicitly declared current successor still supports the latest
   predecessor when that is what the caller intends.

The unqualified candidate is **expected to fail** at least 2/3. These
tests are only committed, not executed, and are intentionally NOT added
to a release gate or merged with #776. Do not tune by matching currency,
museum, theatre or any other authored keyword.

## Acceptance

Independently run these controls and add 2-, 3-, 5-revision
histories with fact corrections, valid-time windows, duplicate subject
names, another tenant/project, deleted generations, explicit older fact
anchors, and in/out-of-budget candidates. Do an additional independent
blind evaluation, not only a replay of theatre Q19. Compare P0 exposure,
top1_critical, critical coverage, false-negative history and distractors
against frozen v7 and candidate #774 using identical caller intents.

No Actions, unapproved PR, merge, frozen v7 change or automatic routing
promotion.
