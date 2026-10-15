# Independent adversarial review of C4 working head `3caf0c13` (base: C3 `6a2255c0`)

A separate review agent worked read-only. It was barred from sealed cohorts and benchmark data.
Its reproduction scripts compare C3 and C4 through the facade and through
`select_relevance_sufficient` directly.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | blocking | Dominance withheld the fact holding the answer when a fact restating the question matched more query words. A tool or another actor could suppress a user's answer this way. | **Mechanism removed.** Pinned by `test_answer_is_never_withheld_by_a_fact_that_restates_the_question` and `test_tool_text_cannot_suppress_the_users_answer`; both fail on `3caf0c13`. |
| F2 | blocking | An equal declared clock (same day) withheld the newer update. | **Removed with dominance.** `test_same_day_update_is_kept` fails on `3caf0c13`. |
| F3 | should-fix | Caller-declared dates overrode write order in the dominance guard. | **Removed with dominance.** Selection no longer reads dates. |
| F4 | should-fix | Plural "what/which X" list questions without an aggregate cue are read as single. Dominance dropped items, and the coverage rule drops an extra "Mom" fact. | The dominance part is removed. The coverage part is **a known limitation**: plural-list detection would change query interpretation broadly, with no evidence for it. |
| F5 | should-fix | A lowercase homograph ("mark it urgent", "will confirm") counted as coverage of the name. | **Fixed.** Coverage requires the selected fact to write the entity as a name. `test_lowercase_homograph_does_not_cover_a_name` fails on `3caf0c13`. |
| F6 | should-fix | The dominance loop was quadratic: 4,000 facts took 26.8 s against C3's 0.45 s, and a facade recall over 8,000 admitted facts took 18 s against 3 s. | **Removed with dominance.** Re-measured below. |
| F7 | note | `dominated_by` was left stale after lifecycle closure. | **Removed with dominance.** |

Attacks that held:
- `ranked_prefix` is identical between C3 and C4.
- Envelopes pass the schema.
- Results are deterministic across hash seeds and reopen.
- The transaction clock persists across reopen.
- No other-project or forgotten fact dominates or is named.
- There is no benchmark-specific behaviour.
- Corrections are respected, and equal coverage is kept.

## Re-verification at `df1190e9`

- F1, F2, F3, F6 and F7 are fixed. On F6: 0.52 s at 4,000 matching facts (it was 26.8 s); a
  facade recall over 8,000 admitted facts takes 2.9–3.0 s against C3's 3.3–3.4 s.
- `ranked_prefix` is byte-identical to C3.

**F5 was only partly fixed.** A capitalised homograph still covered the name: a sentence-initial
imperative ("Mark the … form as urgent."), an all-caps fact, a title-case heading, and
"… Will confirm later.".

**Fixed in the next commit.** `_names_mention` now applies the query interpreter's orthographic
rules to the fact's original text:
- in all-caps or title-case text, capitals carry no information;
- a sentence-initial capital counts only in possessive form ("Mom's …").

`CapitalisedHomographs` pins the four cases and the possessive control.

**Accepted note.** A possessive passing mention ("Florist for Mom's anniversary party…") still
covers Mom. This is erratum 1's conservative reading.

## Re-verification at `6f85868f`

Every earlier reproduction now behaves like C3. `ranked_prefix` is identical. The cost is within
about 6% of C3 on 0.3–1M-character facts, and grows linearly.

**Should-fix: ordinary note layouts still fooled the name rule.** The cases were headline case
with lowercase small words, list items, a line break, an em dash, and a closing parenthesis.

**Fixed in the next commit:**
- The fact-side capitalisation test uses the query interpreter's majority rule.
- A word after a line break, list marker, dash or closing parenthesis counts as a clause start.

`test_note_layouts` pins the reviewer's seven strings.

**Accepted residual ambiguity, recorded rather than chased.** Spelling cannot separate these from
genuine names:
- **Possessive shop names:** "Mark's Hardware …" counts as naming Mark.
- **Vocatives after a comma:** ", Mark it urgent".
- **Passing mentions** (erratum 1).

Both rule changes lean toward C3's more inclusive behaviour; coverage never adds more than C3.
