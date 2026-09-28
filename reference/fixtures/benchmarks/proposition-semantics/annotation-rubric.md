# Proposition-semantics annotation rubric v1 (#594)

Status: **DRAFT rubric, awaiting maintainer review.** It defines what the labels *mean*. It does not describe, and was not derived from, the Agent Memory interpreter (`proposition_semantics.py`). No annotation under this rubric is accepted gold until the maintainer freezes it.

Unit: one user turn from `sample-v1.json`, read on its own. Annotators see only the text, never any runtime output.

## 1. What is being labelled

A **memory proposition** is a claim the text commits to about a durable or lasting state of an identifiable entity. It can be stated as `(entity, property, value)` without guessing. The entity must be one of:

* the speaker (`user`);
* a person, pet, organization, place, or object in the speaker's life that the text identifies (`my sister`, `Max`, `my car`, `Acme`);
* a named entity whose stateful attribute is asserted (`Alex moved to Denver`).

These are **not** memory propositions:

* questions and requests;
* instructions to the assistant;
* hypotheticals;
* fiction and role-play content;
* text the user asks the assistant to process (an essay to edit, code, a prompt to rewrite);
* general world knowledge ("Python is interpreted");
* opinions about general topics without a stateful subject in the speaker's life.

A proposition embedded in a request still counts. For example, "I just moved to Austin, what neighborhoods are good for families?" commits to `(user, residence, Austin)`.

## 2. Fields

| field | values | meaning |
| --- | --- | --- |
| `status` | `known` / `ambiguous` / `unknown` | see §3 |
| `propositions` | list of `{entity, property, value, polarity}` | every memory proposition in the text, principal first; `polarity` is `affirmed`, `ended` (true before, no longer), or `negated` |
| `principal` | index into `propositions`, or `null` | the one proposition the text is principally about; `null` unless `status = known` |
| `cardinality` | `single_valued` / `multi_valued` / `hierarchical` / `unknown` | for the principal property, see §4 |
| `temporal_aspect` | `present` / `prospective` / `past_habitual` / `none_unknown` | for the principal proposition, see §5 |
| `aspect_explicit` | `yes` / `no` | whether the aspect is carried by explicit wording (`currently`, `planning to`, `used to`) rather than tense alone |
| `change_marker` | `yes` / `no` / `ambiguous` | the text says a state changed: moved, switched, started, quit, no longer, used to … now |
| `coexistence_marker` | `yes` / `no` / `ambiguous` | the text says a value is held alongside another: also, too, as well, in addition, both |
| `hedged` | `yes` / `no` | the principal claim is uncertain: maybe, I think, probably, might |
| `self_authority_claim` | `yes` / `no` | the text asserts authority about itself as memory: "this overrides what I said", "remember this as the truth", "ignore my earlier message" |
| `temporal_language_non_temporal` | `yes` / `no` | the text contains temporal words used as discourse or content, not about when the proposition holds ("Now, write…", "for now", "at the same time") |
| `notes` | text | rationale, especially for `ambiguous` |

## 3. Status

* **known**: the text commits to exactly one principal memory proposition, and its entity, property, and value are all determinable from the text alone. Surrounding requests and context do not compete with it. A hedged claim can still be `known` (set `hedged = yes`); hedging concerns commitment, not identifiability.
* **ambiguous**: the text contains memory proposition(s), but the principal one cannot be determined uniquely. Reasons include:
  * several independent propositions compete;
  * the subject is an unresolved pronoun;
  * the value is vague;
  * it is unclear whether the claim is about the speaker's own state.

  Record every candidate in `propositions` and the reason in `notes`.
* **unknown**: the text contains no memory proposition (§1). This is the correct outcome for most requests, questions, and task content, so an interpreter **abstaining** here is correct behavior.

## 4. Cardinality (ordinary meaning of the principal property)

Cardinality asks how many values the entity can hold at once for this property, in ordinary meaning. It is not about how many values this text mentions.

* **single_valued**: the entity holds one value at a time: age, marital status, a favorite X, the car one currently drives when stated as "my car".
* **multi_valued**: several values may hold at once: hobbies, things one likes, pets, languages spoken, employers (people can hold more than one job), memberships.
* **hierarchical**: values relate by containment, so a finer and a coarser value can both be true (Brooklyn and New York). Use this for residence and location, where different values at the *same level* conflict.
* **unknown**: the property's cardinality cannot be determined, or there is no principal proposition.

## 5. Temporal aspect (of the principal proposition)

* **present**: asserted as holding at the time of speaking, whether by explicit wording ("currently", "these days") or by present stative tense ("I live in…"). Set `aspect_explicit` accordingly.
* **prospective**: planned, intended, scheduled, or expected to hold later ("I'm going to start…", "next month I move…").
* **past_habitual**: a former habitual or continuing state ("I used to live…", "back when I worked at…").
* **none_unknown**: no aspect is determinable. This covers a single past event without a lasting state ("I went to Paris last year"), which is recorded in `notes`.

## 6. Procedure

1. Read only the text. Do not consult any Agent Memory output or code.
2. List the memory propositions, then decide `status`, then fill the other fields for the principal proposition.
3. Normalise lightly:
   * entity `user` for first person;
   * a property phrase in plain lower-case English (`residence`, `employer`, `likes`, `pet`, `favorite cuisine`);
   * a value that is the minimal text span.
4. When unsure between `known` and `ambiguous`, choose `ambiguous` and explain.
5. Labels are never revised after seeing any interpreter output. A correction after maintainer review is a new, versioned gold revision with its own rationale.

## 7. How a future evaluator uses this (not scored now)

A future scoring run, only after the maintainer accepts gold, compares interpreter output field by field. It never produces one aggregate score. Section 8 gives the planned evaluator contract.

* proposition slot correctness: entity match **and** value match, where the value is normalized and matched by containment of tokens. The property is compatible through an alias table that is frozen *with* the accepted gold, not fitted afterwards.
* cardinality precision per class;
* aspect precision per class;
* ambiguity and abstention appropriateness;
* deterministic reproduction.

## 8. Planned evaluator contract (design only)

These rules are in the evaluator, pinned by synthetic evaluator-only tests (`test_proposition_evaluator.py`). The tests prove that the evaluator detects each failure class; they are not Agent Memory performance evidence.

| failure class | detected as |
| --- | --- |
| wrong proposition slot | predicted known, gold known, and the entity or property alias differs |
| wrong value | slot matches, value does not |
| over-eager single-valued cardinality | predicted `single_valued` where gold is `multi_valued` or `hierarchical` |
| coexistence misclassified as replacement | gold `coexistence_marker = yes`, and the prediction has a change or replacement signal or `single_valued` from a replacement |
| temporal aspect over-classification | predicted aspect not `none_unknown` where gold is `none_unknown`, or a differing non-none aspect |
| unknown incorrectly promoted to known | gold `unknown` or `ambiguous`, predicted `known` |
| benchmark timestamp leakage | any gold or prediction field carries a value equal to a source session or question timestamp, or the prediction depends on an `observed_at` that the gold text does not contain |
