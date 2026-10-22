# Step 1: independent review of the seven #819 product controls

Reviewed revision: `reference/tests/test_819_served_context_quality_contract.py` at branch head
`706971c887825410f79c3fbe394c4ec1862807db`, git blob `e8c2e9aa3ff595a844ce44acb8ceeb06d0a27717`
(`original-test-blob.txt`). The module is carried **unmodified** into the implementation
commits; the blob id is the evidence that no assertion was weakened.

## Executed RED at the base (`red-706971c8.log`)

All seven tests fail at the base with the same cause: `recall_context` refuses the keyword
(`TypeError: recall_context does not accept ['consumer_profile']`). That is the expected RED and
says nothing yet about served-context behaviour.

## Behavioural baseline under the default profile (`default-profile-variant-706971c8.log`)

To separate "the keyword is unsupported" from "the default behaviour is wrong", the same seven
tests were run with the `consumer_profile=PROFILE` argument removed
(`test_819_default_profile_variant.py`, a scratch copy, never a candidate for the tree):

| test | default profile | reading |
|---|---|---|
| 1 wrong subject and wrong object excluded | FAIL (3 delivered, 1 expected) | the real product deficit: lexical neighbours are delivered |
| 2 paraphrase / plural / family relation preserved | pass | the default already preserves it; the control guards a selector against losing it |
| 3 no safe answer: no distractor served, status `empty`, budget intact | FAIL (2 distractors delivered) | the real no-answer deficit |
| 4 exact logical identity kept despite low overlap | pass | guards a selector |
| 5 governed `recall()` unchanged by the profile | pass | guards a selector |
| 6 other project cannot read private content | pass | admission boundary already holds; guards a selector |
| 7 correct / forget / restart obey lifecycle | pass | guards a selector |

So two of the seven are product-deficit witnesses and five are preservation guards. Both kinds
are needed: a selector that passes 1 and 3 by emptying every package would fail 2, 4 and 7.

## Defensibility of each requirement

1. **Subject and object discrimination.** Defensible. The query names its subject by possessive
   (`Liora's canoe`) and its object (`canoe`); the two distractors differ in exactly one of
   them. The test does not demand semantics beyond what the text grounds.
2. **Paraphrase, plural and implicit relation.** Defensible and important: it is the precise
   failure of the rejected `lexical_content` candidate (`2e6d26dc`, `830ce83f`). `parents` vs
   `father` is not lexically recoverable; `work` vs `works` is. The test asks only that the
   fact be delivered, so one grounded match suffices and no relation ontology is implied.
3. **No safe answer.** Defensible. It asserts an empty delivery, `status == "empty"` and an
   intact `max_items`, i.e. abstention must not be faked by a zero budget. One assumption
   worth stating: `status == "empty"` alone cannot distinguish "the selector declined every
   returned fact" from "the recall returned nothing". The implementation therefore adds a
   package-level `selection.assessment` (`no_relevant_evidence` vs `no_returned_candidates` vs
   `undetermined`); the mechanism suite pins it. The owner's assertion stays valid as written.
4. **Exact logical identity.** Defensible: caller-authorised identity is evidence by
   construction, whatever the wording.
5. **Governed recall invariance.** Defensible. It compares `returned`, `candidates`, `admitted`
   and `return_policy` (not `admissions`, which carry per-call decision ids and clocks).
6. **Scope isolation.** Defensible: a selector must never widen what admission permits.
7. **Lifecycle.** Defensible. It uses real `correct`/`forget` with evidence and a real reopen;
   the `assertNotIn("magenta", repr(context))` check also covers the selection block, so an
   implementation must not leak superseded text through decisions or reasons (it does not:
   decisions carry folded query terms and reason tokens only).

**No test assumption was found invalid; no test was changed.** The one gap (3) was closed by
adding the assessment field, not by editing the control.

## One existing test changed, and why

`reference/tests/test_691_authorization_privacy_challenge.py::test_scope_and_identity_overrides_are_refused_before_any_recall`
listed `{"consumer_profile": "lexical_content"}` among the keywords that must raise `TypeError`.
It was written when the facade refused the keyword as unknown. With the keyword now accepted,
the rejected profile name (and any unknown value) is refused as a value (`ValueError`), still
before any recall and with no audit event recorded. The test now asserts exactly that; the
scope and identity overrides keep their `TypeError` expectation.

## Correction after the owner's PR #841 review (comment 6350329872, policy 0.4.0)

The owner's independent controls (`reference/tests/test_841_independent_product_quality_challenges.py`,
blob `2cd42a06`, carried byte-identical from `review/841-paraphrase-and-uncertainty-challenges-no-ci`
@ `89fc3e72`; RED 4/4 at `5e428c73`, see `../review-841/`) establish two requirements that the
original control 1 contradicts in part:

- a same-subject single-statement fact whose predicate shares no term with the question
  (`Mara's eldest performs on the cello` for `Which instrument does Mara's child play?`) must be
  **delivered and labelled uncertain**, because a lexical selector cannot tell a paraphrased
  predicate from a different attribute;
- a returned fact that could not be inspected must never produce `no_relevant_evidence`.

Control 1 asserted that `Liora's bicycle is black.` is *declined* for `What color is Liora's
canoe?`. That is the same structure as the cello counterexample (subject matches, predicate
terms do not), so the two cannot both hold for a selector without a verified relation parser.
The owner's review states the rule: what cannot be verified is uncertainty, not a negative.
Control 1 was therefore corrected to: the correct fact is delivered as grounded
`subject_and_attribute_evidence` and ranked first; the wrong-subject fact is still declined;
any other delivered fact is labelled `attribute_undetermined` / `uncertain`. The original
assertion stays preserved at blob `e8c2e9aa`. The seven controls otherwise stand.
