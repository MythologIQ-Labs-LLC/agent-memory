# Proposition-semantics annotation rubric v2 (#594)

Status: **DRAFT rubric v2, awaiting a second maintainer sample review.** v2 applies the maintainer ruling of 2026-09-28 on PR #595 (interpretation vs retention). v1 stays unchanged in `annotation-rubric.md`, because `draft-annotations-v1.json` pins it by hash. See §9 for the v1 → v2 differences. It defines what the labels *mean*. It does not describe, and was not derived from, the Agent Memory interpreter (`proposition_semantics.py`). No annotation under this rubric is accepted gold until the maintainer freezes it.

Unit: one user turn from `sample-v1.json`, read on its own. Annotators see only the text, never any runtime output.

## 1. What is being labelled

**Semantic interpretation is not retention policy.** The interpreter's job is to identify the proposition that a text in the write path expresses. It does not decide whether that proposition deserves long-term retention; retention and lifecycle policy decide how long it survives. Duration therefore never disqualifies a proposition. A short-term plan, a momentary choice, or an active search constraint is labelled exactly like a lasting fact.

A **proposition** is an asserted state, relation, preference, goal, search constraint, plan, choice, or bounded condition about an identifiable entity. Its entity, property, and value must all be determinable **from the turn alone**. The entity must be one of:

* the speaker (`user`);
* a person, pet, organization, place, or object in the speaker's life that the text identifies (`my sister`, `Max`, `my car`, `Acme`);
* a named entity whose attribute is asserted (`Alex moved to Denver`).

These are **not** memory propositions:

* questions and requests;
* instructions to the assistant;
* hypotheticals;
* fiction and role-play content;
* text the user asks the assistant to process (an essay to edit, code, a prompt to rewrite);
* general world knowledge ("Python is interpreted");
* opinions about general topics without a subject in the speaker's life.

**Unresolved references.** The unit is one turn read on its own. `that`, `these`, `those teams`, `them`, `both of those apps` and similar cannot be filled from hidden conversation context. When an intention or state is asserted but its entity or value depends on such a reference, the item is `ambiguous`, not `unknown`. A reference is resolved if its antecedent appears earlier in the same turn.

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

* **known**: the text commits to exactly one principal proposition, and its entity, property, and value are all determinable from the text alone.
  * **Supporting context does not compete.** Episodic anecdotes (what happened last week), reasons, background ownership, and closing acknowledgements that serve the principal proposition are supporting context. The principal is usually the plan, goal, state, or preference the turn is about, often the one its request targets.
  * **One predicate over a list is one proposition.** A single predicate applied to a coordinated list ("I'm considering UF and ASU", "packing shampoo, conditioner, and toothbrush") is one proposition whose value is the list. An explicit disjunction inside one value ("a glass or crystal paperweight") is also one value.
  * **Hedging does not change status.** A hedged claim can still be `known` (set `hedged = yes`); hedging concerns commitment, not identifiability.
* **ambiguous**: the text contains proposition(s), but the principal one cannot be determined uniquely. Reasons include:
  * two or more independent propositions of comparable standing compete (for example, two unrelated current plans, or a plan and an unrelated current state);
  * the entity or value depends on an unresolved reference (§1);
  * the value is vague ("more sustainable practices");
  * it is unclear whether the claim is about the speaker's own state, or it is a hypothetical guess about another person ("my mom would love…").

  Record every candidate in `propositions` and the reason in `notes`.
* **unknown**: the text asserts no proposition (§1). This is the correct outcome for pure questions, requests, task content, fiction, and general opinion, so an interpreter **abstaining** here is correct behavior.

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
5. Labels are never revised after seeing any interpreter output. A correction after maintainer review is a new, versioned revision with its own rationale and change manifest.

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

## 9. v1 → v2 differences

| topic | v1 | v2 |
| --- | --- | --- |
| scope of a proposition | "a claim … about a **durable or lasting** state" | any asserted state, relation, preference, goal, search constraint, plan, choice, or bounded condition; duration never disqualifies (interpretation ≠ retention) |
| momentary plans and choices | labelled `unknown` as not lasting | labelled like any other proposition |
| unresolved references | implied | explicit: an asserted intention whose value is an unresolved reference is `ambiguous` |
| supporting context | not defined; any second proposition could compete | episodic anecdotes, reasons, and background ownership do not compete with the principal proposition |
| coordinated values | two values of one property were `ambiguous` | one predicate over a list is one proposition with a list value |

Nothing else changed. §2's fields, §4 cardinality, §5 aspect, and §7–§8's evaluator contract are unchanged. The evaluator still refuses non-accepted gold, and Phase B predictions are produced without a declared `observed_at`. The timestamp-leakage assertion therefore stays a guard against benchmark metadata entering proposition scoring.
