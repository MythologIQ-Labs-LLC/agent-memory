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
