# Plan: #671 read-path currentness — interpreted cross-fact applicability (Option A; ranking policy 3.3.0; Runtime Baseline v5)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #671
**owner rulings in force**:
- `decision-671-currentness-mechanism`: Option A now, Option D next (roadmap seq 55–56, Entry #96);
- `decision-baseline-sequencing-v4-v5`;
- `decision-semantic-default` (stays off);
- `decision-temporal-posture`.

**doctrine**: relevance != currentness; newer != superseding; proposal != authority; ranking != recall admission; interpretation != authority; benchmark score != truth; recency is never authority.
**design evidence**:
- formal MESA M4: 250/250 pairs pass every write-time stage, and read-path currentness separates 0;
- `docs/plan-673-route-fusion.md` gate attempt 1: relevance currently decides "current" between unknown-basis facts;
- the #671 code map in this plan's research notes.

**iteration**: 7 (Gate Tribunal PASS at attempt 7, META_LEDGER Entry #100)

Gate history:
- **Attempt 1: VETO.** An independent prototype was run (`scratchpad/gate671/`).
  - **What worked.** With the mechanism off, MESA M4 reproduces v1 exactly. With it on, 250/250 pairs become `new_fact` wins, every one credited `currentness_mechanism` through `temporal_applicability_tier` by the unchanged classifier. All 16 #584 facade runs keep their order.
  - **Blocking findings:**
    1. **#580.** Eight target units go `honest_unknown` → `fail` (F23, F24 and F28, on the `self_description_currentness_rate` and `stale_as_current_rate` metrics). The frozen evaluator's `DEMOTED_LABELS` does not know the new label. Two order digests change on labels alone, which `VERSIONED_RANKING_TRANSITIONS` cannot express. Six test files had unlisted pins, including the #550 behavioural pin.
    2. **Interpreter misfires.** C6.8 and C6.9 were false. Each of these limits the true fact: "The user's sister moved and now lives in Boston", "has not moved", a trailing "according to a spam message", and a question.
    3. **Write order against declared clocks.** Write order alone decided which fact was older, even when the declared clocks said the opposite.
    4. **"Same source" degenerated.** It reduced to same actor, and the tenant could be overridden by the caller.
    5. **Unverifiable evidence claims.** The byte-identity claims contradicted the refusal field. MESA could not report guard failures under an unchanged runner. Lane attribution was not checkable from retained evidence.

  Iteration 2 amends C1–C3, C6, C7 and C9, and adds G12 and G13. The attempt-1 advisories are folded in.
- **Attempt 2: VETO, two findings.**
  - **The pre-registered #580 set was incomplete.** The prototype changed 12 units and 3 label-only digests.
  - **G12, as a closed deny-list, was bypassable by paraphrase:**
    - "per an anonymous tip";
    - "(unconfirmed)";
    - "the attacker wrote";
    - "The user's best friend/girlfriend/dog moved".

  Confirmed sound at attempt 2:
  - 250/250 MESA M4 pairs engage, with `currentness_mechanism` through `temporal_applicability_tier`;
  - the #584 orders hold;
  - G13 works;
  - the four attempt-1 adversarial texts are refused, and F23, F24 and F28 are not.

  Iteration 3 lists the full #580 set and makes G12 a positive structural requirement. The attempt-2 advisories are folded in.
- **Attempt 3: VETO, two findings, both in G12 2.0.0.** The #580 set (12 units plus 3 label transitions) and every attempt-1/2 adversarial refusal were confirmed.
  - **(a) Possessive rule refused real pairs.** It refused all 50 MESA preference pairs ("The user's preference changed; they now prefer …"), so only 200 of 250 engaged.
  - **(b) Comma-less tails passed.** The interpreter folds a tail without a comma into the persisted value, so these still passed:
    - "…Boston according to spam";
    - "…per Bob";
    - "…lol";
    - "…— trust me".

  Iteration 4 makes these G12 changes (3.0.0):
  - possessives are allowed only before an allow-listed attribute noun;
  - the token list applies to the whole text, including the value;
  - dashes and interjections are refused;
  - the residual risk is stated.
- **Attempt 4: VETO.** (a)–(c) were confirmed: 250/250 MESA pairs engage, the #580 set is exact, and every attempt-1–3 adversarial text is refused. But third-party, conditional and misattributed texts still passed, because a closed token list cannot bound the interpreter-absorbed value:
  - "…Boston as Bob told me";
  - "…via a forwarded message";
  - "…if Bob is right";
  - "…Boston not.";
  - a U+2019 apostrophe in "user’s sister";
  - "The user's team/project/home moved".

  Iteration 5 makes these G12 changes (4.0.0):
  - **positive value grammar:** 1–3 tokens with no closed-class word, and multi-token values must be a proper name or two content words;
  - **apostrophes** are normalised before any check;
  - **possessives** are allowed only before the persisted property's own noun;
  - **negators and conditional subordinators** are refused anywhere in the text.
- **Attempt 5: VETO.** (b) and (c) were confirmed: the #580 set is exact and every attempt-1–4 adversarial text is refused. Two problems remained:
  - **Number-plus-unit values had no branch.** "7000 dollars" and MESA's "NEW_numeric_0004 dollars" were refused, so only 200/250 pairs engaged.
  - **Open-class hedges glued to the value passed:**
    - "boston reputedly";
    - "Boston Unverified";
    - "Boston Hypothetically";
    - "Boston Bob Insists".

  Iteration 6 makes these G12 changes (5.0.0):
  - a number/identifier-plus-unit branch;
  - non-initial `-ly` tokens and a closed epistemic list are refused;
  - a 3-token proper name must end in a place or organisation suffix;
  - casing is read from the text span;
  - the residual is restated.
- **Attempt 6: VETO, one narrow finding.** (a)–(c) were confirmed: 250/250 MESA pairs engage, the #580 set is exact, and every attempt-1–5 adversarial text is refused. But a falsity or doubt word in the second slot of (4b) or (4c) passed outside the stated residual:
  - "boston untrue";
  - "boston hearsay";
  - "7000 reckoned".

  Iteration 7 makes these G12 changes (6.0.0):
  - the (4b) unit comes from a closed list;
  - the two-lowercase shape (4c) is removed, so such values fail closed;
  - a closed falsity and doubt list is added as an extra layer.

  The residual is not widened to cover hedged or negated claims, because the ruling excludes them.

## Purpose

Today an explicit-current query has no way to use the change evidence the runtime has already detected. Consider "The user moved and now lives in Boston" (newer) against "The user lives in Denver" (older), with no declared validity on either.
- **Write time succeeds.** The newer write is recognised and the slot is identified. A `state_change_candidate` relation with an open correction proposal is persisted on the newer fact.
- **Read time fails.** Both facts have an unknown temporal basis. The #584 pairwise rule needs one side `applicable`, so no edge forms, and lexical relevance decides which fact ranks as "current".

Option A connects the two. When guarded, typed, open change evidence exists between two live, same-actor, same-source, same-scope facts, an **explicit-current** recall **limits the older fact's applicability** for that currentness decision, under a new explicit basis `interpreted_cross_fact`.
- Nothing is mutated or corrected.
- The proposal stays open.
- History and non-current recall are untouched.
- Time order never substitutes for the typed evidence.

## Decisions

**C1 — Write provenance per fact (new; the guard identities).**
Facts carry no actor today. The facade's default evidence ref is a per-text content digest, so evidence refs can never serve as a shared "source".

- **What is recorded.** `_write` records an immutable `attributes["write_provenance"]` on every fact it commits:
  - `version: "1.0.0"`;
  - `actor_id`: the PAMA proposal's actor;
  - `tenant`: the adapter's `fact.group_id`, never the caller-overridable `tenant_ref`;
  - `purpose`;
  - `channel`: `caller_observation` for `promotion`, `caller_correction` for `correction`, `other:<operation>` otherwise;
  - `source_ref`.
- **`source_ref`** is a new optional facade `remember(..., source_ref=...)` argument: the caller-declared origin of the statement, for example `user:alice`, `conversation:42` or `tool:web-search`.
  - It defaults to `actor:<actor_id>`, meaning the acting agent's own direct observation.
  - It is validated as a non-empty string of at most 256 characters.
  - It is not settable through `overrides`.
- **Same source** means all three of these hold:
  - equal `source_ref`;
  - equal (`tenant`, `purpose`);
  - both channels are `caller_observation`.

  Callers that write statements from several origins through one actor can now separate them, and a mismatch refuses. A caller that declares nothing gets the actor-level default. Under that default, "same source" coincides with "same actor": the acting agent is the only source the runtime has evidence of.
- **Owner-ratified reading.** This definition of "same source" was ratified by the owner on 2026-10-07 (`decision-671-same-source`; see Open Questions).
- **Same actor** means `actor_id` is equal and non-empty.
- **Same scope** means `_same_semantic_scope` (domain_refs set, project_ref, task_ref) plus equal `required_domain_refs` and equal `tenant`. This is the isolation domain the write-time classifier already used.
- **Missing identity fails closed.** A fact without `write_provenance` never participates: any fact committed before v5, or by a harness path that bypasses `_write`. The refusal reason is `cross_fact_identity_unavailable`, and pre-v5 stores gain nothing.
- **What provenance is excluded from.** It is excluded from BM25 text, from the content-identity digest, from every ranking input other than this guard, and from the facade `write_semantics` view. The gate prototype verified that BM25 and the digest read only `fact_text`.

**C2 — Cross-fact evidence construction (adapter; read-only).**
`GovernedMemoryAdapter.cross_fact_applicability(admitted, context, intent) -> {target_uuid: evidence}` is a pure read. For each admitted fact S, and each persisted relation on S whose other fact T is also admitted in this recall, it accepts the pair only when **every** guard below holds. The first failing guard is recorded as the refusal reason.

| # | Guard | Refusal reason |
|---|---|---|
| G1 | Explicit-current profile (`temporal_order_constraints.explicit_current_profile`: mode current, posture explicit, basis caller_declared or query_language_explicit). Inferred `latest`, atemporal, historical and as-of intents are refused. | `not_explicit_current_profile` |
| G2 | The relation classification is `state_change_candidate`. A conflict, coexistence or unresolved relation never qualifies. | `relation_not_state_change` |
| G3 | The relation basis is `single_valued_replacement_marker` or `explicit_termination:*`. | `relation_basis_not_accepted` |
| G4 | The relation carries a proposal, with `applied: false` and `authority_effect: "none"`. | `no_open_proposal` |
| G5 | `_proposal_status(...) == "open"`. Both facts are the current fact of their own memory, neither is tombstoned or disputed, and the proposal has not been applied. This covers forget, tombstone, dispute and supersession at read time. | `proposal_not_open:<status>` |
| G6 | S's persisted markers carry no `hedge` and no `self_claims`, and S's `proposal_ineligible_reasons` is empty. This repeats the write-time downgrade at read time, as defence in depth. | `hedged_or_untrusted_claim` |
| G7 | Both facts carry `write_provenance`. | `cross_fact_identity_unavailable` |
| G8 | Same actor. | `actor_mismatch` |
| G9 | Same source (C1). | `source_mismatch` |
| G10 | Same scope (C1). | `scope_mismatch` |
| G11 | No mutual limitation. If T also carries an accepted relation to S, both are refused. This is unreachable on governed paths, because relations are persisted only on the newer fact; it is kept as a defensive guard. | `contradictory_cross_fact_evidence` |
| G12 | **Assertive first-party change evidence: a positive structural requirement on S's text**, versioned `cross_fact_assertion_filter 6.0.0`. It is applied only by this mechanism and leaves write-time recognition unchanged. **Normalisation first:** U+2019, U+2018, U+02BC and U+FF07 become `'`; U+201C and U+201D become `"`; then Unicode NFKC. S qualifies only when **all** of these hold, and anything else refuses:<br>(1) the text is one sentence: no `?`, no `(` or `)`, no dash (`—`, `–`, `--`, or ` - ` between words), and at most one terminal `.` or `!`, at the end;<br>(2) the **prefix**, from the start of the text to the first change marker, contains no comma, colon, semicolon or quotation mark. A possessive (`'s` or `s'`) in it is allowed only when the noun directly after it names the **persisted property itself**: its first four letters equal those of the property head word, so `preference` for `prefer` and `address` for `address`. Any other possessive refuses (sister, friend, dog, team, project, home…);<br>(3) the persisted proposition **value** is located in the text (case-insensitive, last occurrence). If it cannot be located the pair is refused, so the check fails closed;<br>(4) the **value is bounded positively**. The persisted value is lower-cased, so casing tests read the value's **span in the normalised text**. Every token matches `[A-Za-z0-9][A-Za-z0-9_.@&'+-]*`, and no token is an English **closed-class word** (a complete, fixed list of about 185 function words in the module, versioned with the filter). No token after the first ends in `-ly` or is in the closed **epistemic list**: `unverified`, `unconfirmed`, `unclear`, `uncertain`, `unsure`, `perchance`, `hypothetical`, `supposed`, `alleged`, `purported`, `rumou?red`, `reputed`, `disputed`, `doubtful`, `questionable`, `presumed`, and the falsity and doubt layer `untrue`, `false`, `fake`, `wrong`, `dubious`, `hearsay`, `guessed`, `reckoned`, `bogus`, `fabricated`, `invented`, `made-up`, `mistaken`. The value must then take exactly one of these shapes:<br>(4a) a single token, of any case;<br>(4b) a numeric or identifier token (containing a digit or `_`), optionally followed by one unit from the closed **unit list**: currency (`dollars?`, `usd`, `euros?`, `eur`, `pounds?`, `gbp`, `yen`, `cents?`), length (`km`, `kilometers?`, `kilometres?`, `miles?`, `m`, `meters?`, `metres?`, `cm`, `mm`, `feet`, `foot`, `ft`, `inches?`, `in`), mass (`kg`, `kilograms?`, `g`, `grams?`, `lbs?`, `ounces?`, `oz`), time (`seconds?`, `minutes?`, `hours?`, `days?`, `weeks?`, `months?`, `years?`), and `percent`, `%`, `points?`, `items?`, `people`, `users?`, `units?`. Examples: `7000 dollars`, `NEW_numeric_0004 dollars`, `42 km`;<br>(4c) *(removed in 6.0.0.)* Two-lowercase-token values such as `green tea` fail closed, and the mechanism does not engage on them;<br>(4d) a proper name: two Capitalised tokens, or three Capitalised tokens whose last is a place or organisation suffix (`City`, `Town`, `County`, `Bay`, `Beach`, `Springs`, `Falls`, `Heights`, `Park`, `Valley`, `Island`, `Labs`, `Lab`, `Inc`, `Corp`, `Corporation`, `Company`, `Co`, `LLC`, `Ltd`, `Group`, `Bank`, `University`, `College`, `School`, `Hospital`, `Systems`, `Technologies`, `Partners`).<br>Anything else refuses<br>(5) the **suffix**, after the value, consists only of optional temporal adverbs (`now`, `today`, `currently`, `anymore`, `these days`) and the terminal punctuation;<br>(6) the **whole text** contains no negator (`not`, `never`, `no`, `n't`, `nobody`, `nothing`, `neither`, `nor`) except within the termination marker `no longer` itself, and no conditional or concessive subordinator (`if`, `unless`, `whether`, `assuming`, `provided`, `supposing`, `though`, `although`, `even`). Both are closed classes;<br>(7) the **whole text** contains none of the attribution, hedge and interjection tokens: `according`, `per`, `via`, `reportedly`, `allegedly`, `rumou?r`, `heard`, `told`, `said`, `says`, `stated`, `wrote`, `claims?`, `tip`, `spam`, `forwarded`, `supposedly`, `unconfirmed`, `apparently`, `maybe`, `might`, `may`, `perhaps`, `possibly`, `probably`, `trust`, `lol`, `jk`, `haha`, `lmao`, `kidding`, `joke`, `joking`, `allegation`, `source`, `sources`. Matching is whole-word, and `May` followed by a digit is exempt. This list is an extra layer; (4)–(6) carry the guarantee.<br>Between the change marker and the value, punctuation is allowed (F24's `;`, F28's `,`, MESA's `;`).<br>**Residual risk, stated:** what can still pass is a first-party assertion, unconditional and unnegated, from the same actor and declared source, whose value fits (4a)–(4d). Only one value shape carries the open-class residual: two **deliberately Capitalised** tokens (4d) whose second token is an unlisted open-class word (the gate's contrived "Boston Insists" shape). A same-source writer can also assert a wrong value. Lowercase glued words cannot pass: (4c) is removed, and (4b) admits only listed units. That is not a third-party or untrusted claim, and the effect is a reversible, non-mutating applicability limitation. Every refusal is also recorded for #596/#597 as a write-time recognition fix. | `change_evidence_not_assertive:<1–7>` |
| G13 | **Declared clocks never contradict the relation's direction.** The relation's direction comes from the typed change text responding to the fact it was classified against. When both facts carry a declared clock of the same kind (`observed_at`, or `valid_from`), S's must not be earlier than T's. When T carries a declared clock and S carries none of that kind, the pair is refused, because the direction cannot be confirmed. No clock is ever used to choose a winner; clocks can only refuse. | `declared_clock_contradicts_direction` / `declared_clock_unconfirmed` |

The evidence object for an accepted pair is:
`{basis: "interpreted_cross_fact", source_fact_uuid, proposal_id, relation_basis, guards: [G1..G11 names], authority_effect: "none"}`.

T may be limited by several sources; every accepted source is listed. S has to be **admitted in the same recall**. A fact the caller cannot see never shapes the caller's ranking, so this cannot leak foreign-domain existence.

**C3 — Ranking policy 3.3.0 (applicability, not relevance).**
`ExplicitCurrentCrossFactRankingPolicy` subclasses the 3.2.0 policy. `POLICY_VERSION = "3.3.0"` and `CROSS_FACT_POLICY = "explicit_current_interpreted_cross_fact_v1"`, which is added to the policy identity.

- `rank(..., cross_fact=None)`. With `None` or `{}`, ranking and every evidence field are identical to 3.2.0 except the policy identity fields (`policy_version`, and the added `cross_fact_policy`). A test asserts this.
- **Separate version constants.** `CROSS_FACT_POLICY_VERSION = "3.3.0"` is new. The 3.2.0 class keeps its own constant, and `IDENTITY_SOURCES` reads the live policy's identity.
- **When a target is limited.** For each target T in `cross_fact`, the policy limits T only if all three hold:
  - T's computed label is `unknown_temporal_basis`. A caller-declared or interpreted window always wins, and the refusal is `target_has_temporal_basis`.
  - At least one accepted source S has the label `unknown_temporal_basis`. Where S is `applicable`, the #584 pairwise rule already governs and is left untouched; the refusal is `source_has_temporal_basis`.
  - S is not itself demoted.
- **What a limitation sets on T:**
  - `temporal_applicability = "limited_by_cross_fact_state_change"`;
  - `temporal_applicability_basis = "interpreted_cross_fact"`;
  - `cross_fact_limitation = [evidence…]`.
- **Where the label goes.** The label is added to `_DEMOTED[CURRENT]` only, not to AS_OF, so the existing `temporal_applicability_tier` stage moves T to tier 1. No new stage name is introduced, and the `_pre_temporal_key` stop-set is unchanged.
- **Refusals on targets.** A target refused by the adapter or the policy records `cross_fact_refusal_reason`, the first reason, but **only when G1 passes** (explicit-current). Under any other intent no cross-fact field is written. Historical, atemporal and inferred recalls are therefore identical to 3.2.0 apart from the policy identity fields.
- **Single pass.** "S not itself demoted" uses S's pre-cross-fact label, so chains are evaluated in one pass. An older fact is limited only through a direct relation, and a relation is created against at most `MAX_RELATIONS = 8` facts.
- **What never changes:**
  - admission: the admitted set is identical with and without the mechanism, and T stays admitted, returned and historical;
  - candidate generation;
  - BM25;
  - corroboration;
  - the 3.2.0 pairwise constraints and the content-identity fallback.
- Relevance can never cross the new tier boundary, because the tier stage precedes all relevance stages.

**C4 — Wiring.**
- `runtime_composition` (the facade) calls `adapter.cross_fact_applicability` after `resolve_intent` and admission, and passes the result to `rank`.
- `query_driven_recall` and `recall_control` (harness planners) use the same policy class and version. They pass the same adapter result where they hold the adapter; otherwise they pass `None` and say so in their posture text.
- `MULTI_ROUTE_RANKING_POLICY` becomes the 3.3.0 class. The #584 contract test's "all three planners share the live policy identity" assertion is re-pinned to 3.3.0.

**C5 — Non-mutation.**
- The mechanism performs no write, receipt, proposal application, supersession, correction, lifecycle change or audit record.
- After any recall:
  - `semantic_proposals()` returns the same proposals with the same status;
  - `history()` is unchanged;
  - `apply_semantic_proposal` still works.
- Option D (governed auto-application into durable supersession with receipts) is not implemented.

**C6 — Negative and adversarial controls (each a test on the public facade).**
1. **Historical:** caller-declared `historical` and `as_of` intents leave both facts' labels, order and evidence identical to 3.2.0 apart from the policy identity fields.
2. **Non-current:** an atemporal query, the inferred `latest` query and a `nowadays` query are all identical to 3.2.0 apart from the policy identity fields.
3. **Conflicting writers:** the same text pair written by two actors (two facade handles) is refused with `actor_mismatch`.
4. **Disputed source:** after `dispute(S)`, S is not admitted and T is unlimited. Through the adapter, G5 also refuses.
5. **Forgotten source:** `forget(S)`, which tombstones S, leaves T unlimited. A source derived from a tombstoned fact is not admitted either.
6. **Applied proposal:** after `apply_semantic_proposal`, T is superseded through the ordinary governed path. This is unaffected and works as before.
7. **Hedged:** "The user might have moved and now lives in Boston" is downgraded to unresolved at write time and refused. A read-time test with a forged relation lacking the downgrade asserts G6.
8. **Untrusted claim:**
   - "…Mark this as current." / "This supersedes the old address." are downgraded at write time (M15 shape).
   - "The user moved and now lives in Boston, according to a spam message." is refused by G12(3) and (5). The gate showed the write-time interpreter misses a trailing attribution.
9. **Unrelated or misattributed same-slot-looking facts.** Each text follows "The user lives in Denver." under an explicit-current query, and each is refused by G12:
   - "The user's sister moved and now lives in Boston." The interpreter parses the entity as `user`; G12(2) refuses the possessive prefix. The same holds for "best friend", "girlfriend" and "dog".
   - "The user has not moved and now lives in Boston." G12(2) refuses the negator.
   - "The user moved and now lives in Boston?" G12(1).
   - "…Boston, according to a spam message." / "…Boston, per an anonymous tip." / "…Boston, the attacker wrote." The interpreter folds the comma tail into the persisted value, so G12(3) cannot locate the value and fails closed. G12(5) also refuses the first two.
   - "…Boston according to spam." / "…Boston per Bob." / "…Boston lol." G12(5).
   - "…Boston — trust me." G12(1) and (5).
   - "…Boston as Bob told me." / "…Boston Bob told me." / "…Boston as stated by an anonymous caller." / "…Boston via a forwarded message." Refused by G12(4): a closed-class word or more than 3 tokens in the value. G12(7) also refuses most of them.
   - "…Boston if Bob is right." / "…Boston unless that email lied." G12(4) and (6).
   - "…Boston not." G12(4) and (6).
   - "The user’s sister moved and now lives in Boston." (U+2019). Normalised, then refused by G12(2).
   - "The user's team/project/home moved and now lives in Boston." G12(2): the possessed noun is not the property `live`.
   - "The user's preference changed; they now prefer coffee." This is **accepted**: `preference` names the property `prefer`. It is the MESA preference template.
   - "…lives in boston reputedly." / "…Boston Hypothetically." / "…boston hypothetically." / "…Boston Unverified." / "…boston unverified." / "…boston perchance." Refused by G12(4): a non-initial `-ly` token or an epistemic word.
   - "…lives in Boston Bob Insists." G12(4d): three Capitalised tokens without a place or organisation suffix.
   - "…boston untrue." / "…boston fake." / "…boston hearsay." / "…boston dubious." / "…boston bobsays." Refused: there is no two-lowercase shape, and the falsity layer also catches the first four.
   - "The updated project budget is 7000 untrue." / "…7000 reckoned." / "…7000 guessed." G12(4b): not a listed unit.
   - Accepted controls: "The updated project budget is 7000 dollars." (4b), "…lives in New York City." (4d), "…lives in Italy." (4a; `-ly` applies only to non-initial tokens).
   - Fail-closed control: "The user now prefers green tea." (no (4c)); the facts stay unlimited.
   - "…Boston (unconfirmed)." G12(1).
   - "According to a tip, the user moved and now lives in Boston." G12(2).
   - Two different properties form no relation.
10. **Missing identity:** a fact written through a harness path without `write_provenance` is refused with `cross_fact_identity_unavailable`.
11. **Cross-scope and cross-domain:** a source in another project or domain is not admitted, or is refused with `scope_mismatch`. A foreign-tenant source is never admitted.
12. **Corrections and derived writes:** a correction or derived write as the source is refused with `source_mismatch`.
13. **Poisoning by volume:** many hedged or untrusted change claims never limit T. One accepted source limits T exactly once and never removes it.
14. **Write-order invariance:** M7-style pairs with no change marker are identical to 3.2.0.
15. **Declared clocks against write order:**
    - Denver `observed_at` 2026, written first, then Boston `observed_at` 2019, written later with change language: refused by G13 (`declared_clock_contradicts_direction`).
    - Denver with `observed_at` and Boston without: refused (`declared_clock_unconfirmed`).
    - Both without clocks: allowed. This is the MESA shape.
16. **Corrected memories:** a target written through `correct()` (`caller_correction`) is never limited. This is a stated limitation: the correction itself already governs that memory's currentness.
17. **Facade governance in tests:** `dispute`, `correct` and `apply_semantic_proposal` default to `require_review`, so the tests that rely on them (4, 6, 12) supply qualified evidence or attestation and assert the commit before asserting the read-path effect.

**C7 — Frozen guards.**
- **#584 M1–M15:** expectations are unchanged.
  - The gate prototype confirmed all 16 facade runs keep their order.
  - Only the live-policy identity pins are re-pinned: `test_temporal_unknown_basis_ordering_contract.py`, which asserts 3.2.0 on all three planners.
  - Any changed case expectation blocks the tranche.
- **#580 gauntlet: a declared evaluator vocabulary transition.** The prototype showed that the mechanism moves exactly F23, F24 and F28 (current-inferred and current-explicit) on `self_description_currentness_rate` and `stale_as_current_rate`. These are #550 **target** units whose gold says the older fact is stale. They score `fail` only because the frozen evaluator's demotion vocabulary (`evaluation/temporal_currentness.py` `DEMOTED_LABELS` and `_role_holds` "not_current") predates the new label.
  - `temporal_currentness.py` gains `limited_by_cross_fact_state_change` in `DEMOTED_LABELS["current"]` and in the `not_current` role, under `EVALUATOR_VOCABULARY_VERSION` 1.0.0 → 1.1.0. The fixture, its gold and `FIXTURE_SHA256` are unchanged.
  - `test_temporal_currentness_gauntlet.py` gains `VERSIONED_EVALUATOR_TRANSITIONS`. It pre-registers, before implementation, the exact 12 units the attempt-2 prototype changed against the mechanism off. Each is keyed (case, probe, metric, level `target`) and is an allowed improvement:
    - `F23-has-moved-now-lives` / `current-inferred` and `current-explicit`, on `self_description_currentness_rate`, `stale_as_current_rate` and `current_applicability_accuracy`: 6 units, `honest_unknown` → `pass`. The `current_applicability_accuracy` units move with the reordering, not with the vocabulary.
    - `F24-no-longer-works-at` / `current-inferred`, on `self_description_currentness_rate` and `stale_as_current_rate`: 2 units, `honest_unknown` → `pass`.
    - `F28-used-to-prefer-now-prefer` / `current-inferred`, on the same two metrics: 2 units, `honest_unknown` → `pass`.
    - `F28-used-to-prefer-now-prefer` / `plain-now`, on the same two metrics: 2 units, `fail` → `pass` against the frozen baseline.

    All three cases declare `observed_at` in write order (older first), so G13 admits them.
  - Any unit not listed, and any transition to `fail`, blocks. If the implementation produces a different set, the tranche stops and re-plans; nothing is re-pinned to match.
  - **Label-only digest changes** (admitted order unchanged, per-key labels changed) need a new form. `VERSIONED_LABEL_TRANSITIONS` maps (case, probe, key) to (from label, to label) and requires the admitted order to be unchanged. It sits beside `VERSIONED_RANKING_TRANSITIONS`, which is unchanged. There are exactly three entries, each `unknown_temporal_basis` → `limited_by_cross_fact_state_change`:
    - F24 / `current-inferred` / acme;
    - F28 / `current-inferred` / tea;
    - F28 / `plain-now` / tea.

    These entries are asserted explicitly and are not absorbed by the test's existing `improved_cases` or intent-transition exemptions: a label change on any (case, probe, key) outside the table fails.
- **The #550 behavioural pin is superseded by the owner ruling.** `test_write_time_proposition_semantics.py:204` asserts that the older fact stays `unknown_temporal_basis` under current intent. It is re-pinned to assert `limited_by_cross_fact_state_change` with basis `interpreted_cross_fact`, and the write-time half is unchanged. The change cites `decision-671-currentness-mechanism`.
- **Identity pins re-pinned to 3.3.0** (policy version only, no behaviour): `test_post_admission_ranking_policy.py` (×2), `test_query_conditioned_applicability.py`, `test_semantic_route_policy_320.py` and the #584 contract test. The gate's full-suite on/off diff found exactly these 6 files. Any further failing test found during implementation is listed as an implementation amendment with its reason before it is changed.
- **Ordering-difference report.** `reference/run_cross_fact_currentness_report.py` is modelled on `run_semantic_route_ordering_report.py`. It runs the #584 cases, every #580 case, all 250 MESA M4 pairs through the formal adapter shape, and the C6 controls, each with the mechanism off and on. It reports:
  - per pair, the accepted evidence or the first failing guard (G1–G13). This is where guard failures are reported, because the frozen MESA runner's digest drops the new fields;
  - every ordering or label change, with attribution.

  Blockers:
  - any #580 change outside `VERSIONED_EVALUATOR_TRANSITIONS` and `VERSIONED_LABEL_TRANSITIONS`;
  - any #584 expectation change;
  - any reordered or relabelled candidate without `cross_fact_limitation`.

**C8 — Succession: Runtime Baseline v5.**
- Step A is declared only after v4 is published (B1/B2). v4 is never amended.
- `reports/runtime/baseline-v5-declaration.json` (issue 671) has these identity deltas:
  - `identity.ranking.active_policy_version` 3.2.0 → 3.3.0;
  - any `IDENTITY_SOURCES` value that moves, which are listed by `scripts/runtime_baseline_identity.py` at implementation, for example a new `cross_fact_policy` identity source if added.
- `pyproject_change` is null, and the public contract stays 1.5.0. Ranking evidence is free-form under `admissions`, so no envelope change is needed. If the gate finds a closed schema that the new fields violate, the plan takes contract 1.6.0 instead.
- `acceptance_evidence_required`:
  - the public Gauntlet probe;
  - lanes `longmemeval-s-retrieval-parity-v5` and `amb-precisionmembench-retrieval-v5`;
  - the formal MESA successor freeze `mesa-formal-v2` (C9).

**C9 — Evidence (a separate gated plan, pre-registered here).**
- **Lanes `-v5`.**
  - The control is not held to equality with `-v4`, because this is an intended behaviour change.
  - **Attribution rule:** every question or case whose ranked output differs from `-v4` must have at least one admitted candidate carrying `cross_fact_limitation`. Every other question must equal `-v4` exactly.
  - **Making attribution checkable.** The `-v5` lanes plan adds the needed runner fields under a new runner blob, recorded before any score:
    - `run_longmemeval.py` records per question `cross_fact_limited_count` and the limited item ids;
    - the AMB bridge records them through the L9-style sidecar.
  - Reported, not gated:
    - per-question up/down counts;
    - the LongMemEval knowledge-update slice;
    - `latest_gold_ranked_first`.
- **MESA.**
  - `mesa-formal-v2` copies v1 and changes only the `agent_memory` block (runtime tree, policy 3.3.0, contract 1.5.0). The runner and classifier are unchanged, with the same sha256.
  - The classifier credits `currentness_mechanism` through `_DEMOTED[CURRENT]` by name and the tier stage, which is already in `CURRENTNESS_STAGES`.
  - Pre-registered prediction, frozen before the replay:
    - for M4 pairs where both facts are admitted under an explicit-current query with an open, accepted relation, `temporal_applicability_currentness` is met;
    - every `new_fact` win has `win_basis == "currentness_mechanism"`;
    - no win is attributed to `lexical_ordering`, `temporal_order_tiebreak`, `content_identity_tiebreak` or a semantic route;
    - pairs failing any C2 guard keep their v1 classification. Their failing guard is reported by the C7 report, not by the frozen runner, whose `_ranking_digest` keeps its fields;
    - `dual_version_rate` is reported;
    - M1–M3 and M5–M6 are reported against v1 with their deltas.
  - A higher M4 score without this attribution is not acceptance.

## Implementation steps (after gate PASS, and after Runtime Baseline v4 is published)

1. **Write provenance (C1)** in `adapter._write`, plus the exclusions.
2. **`adapter.cross_fact_applicability`** (C2).
3. **The 3.3.0 policy class** (C3) in `temporal_order_constraints.py`, `_DEMOTED[CURRENT]` and the identity fields.
4. **Wiring** (C4).
5. **Tests:**
   - `test_cross_fact_currentness.py` covering C2's guards one by one, C3's off-equivalence and labels, C5's non-mutation, and all 14 C6 controls on the facade;
   - the #584 contract re-pin (identity only);
   - #580 `VERSIONED_RANKING_TRANSITIONS` entries attributed by the C7 report;
   - the planner identity re-pins.
6. **`run_cross_fact_currentness_report.py`** and its committed report.
7. **v5 Step A declaration** via `scripts/declare_runtime_baseline_changes.py`; the checker shows TRANSITION.
8. **Ledger entry**; merge commit.
9. **The C9 evidence plan**, with its own gate, followed by dispatch, acceptance and v5 B1/B2.

## Boundaries

- **non_goals:**
  - Option D (auto-application or supersession);
  - temporal inference from text (`valid_from` extraction);
  - route fusion (#673, re-planned after acceptance);
  - semantic default-on;
  - controller enforcement (T-controller-2).
- **exclusions:**
  - no admission change;
  - no lifecycle mutation;
  - no recency or write-clock input to the new decision;
  - no benchmark-specific behaviour;
  - no change to proposition recognition, slot identity or state-change detection;
  - no tuning after any score.

## Open Questions

- **Resolved 2026-10-07 by owner ruling: "Declared ref, actor default".** "Same source" means equal caller-declared `source_ref`, defaulting to `actor:<actor_id>`, plus the same tenant and purpose and direct caller observation on both sides, as C1 states. The ruling is recorded as roadmap node `decision-671-same-source`.
