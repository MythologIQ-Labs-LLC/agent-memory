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
