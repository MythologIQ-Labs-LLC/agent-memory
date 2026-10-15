# #819 preregistration addendum: candidate C2 (review-driven defect fixes)

Written and committed before C2 ran on AMB, LongMemEval or the held-out cohort.

## Why there is a C2

C1 (`4bd38e6c`) is frozen and is with the independent evaluator. An independent adversarial
review of the C1 diff found no governance bypass and confirmed that `ranked_prefix` is
byte-identical to contract 1.4.0. It did report two should-fix defects. Each was reproduced
through the public facade on **hand-written memories unrelated to any benchmark**:

1. **Selection can contradict ranking.** Ranking BM25 counts function words; selection BM25
   does not. A fact stuffed with query terms can therefore become the "best" by content
   relevance. That pushes the fact ranked first below the relative floor, so at `budget=1`
   C1 returns the stuffed fact where 1.4.0 returned the canonical one.
2. **The function-word list hides real evidence.** It held words that are also names or
   content: `don`, `will`, `may`, `us`, `won`, `like`, `one`, `past`, `near`, `mine`.
   Examples: "Tell me about Don", "Who is Will?", "What happened in May?", "What do I like?"
   all abstained. The blanket single-letter rule also dropped "Vitamin D" and "plan B".

C2 is decided on those repros alone, not on benchmark outcomes. Because C1's AMB and
held-out results have already been seen, C2's results on them are **not blind**. Only the
independent evaluator's hidden holdout is unseen for C2.

## Fixed changes (no others)

1. **Ranking consistency.** A fact that has positive informative-term relevance and is ranked
   above a fact selected as sufficient is itself sufficient, with basis
   `ranked_above_sufficient`. Facts with no informative-term match are still withheld. The
   effect is that selection never inverts ranking's order between two facts that both carry
   topical evidence.
2. **Contractions are normalised before selection tokenisation**, for query and fact text
   alike, and for selection only (ranking is unchanged):
   - `n't` becomes ` not`, with `won't` → `will not`, `can't` → `can not`,
     `shan't` → `shall not`;
   - `'s`, `'re`, `'ve`, `'ll`, `'d`, `'m` are removed.
3. **Function-word list and names.**
   - `like`, `one`, `past`, `near`, `mine` and `won` are removed, because their content reading
     is common in lower case.
   - The contraction fragments are removed, because normalisation makes them unnecessary.
   - The blanket single-letter rule is replaced by listing `a` and `i`.
   - `will`, `may`, `us`, `it`, `can`, `still`, `who` and `am` stay. A function word is
     nevertheless kept as evidence when the query writes it as a name: capitalised and not
     sentence-initial, or an all-caps acronym of two or more letters (not `I`). This exception
     is off when the query has no lower-case letters, or when more than half of its
     non-initial words are capitalised (title case).
4. `rho = 0.5`, the abstention rule, the bypasses and the contract shape are unchanged.
   `SELECTION_POLICY_VERSION` moves to `1.1.0` so C1 and C2 outputs can be told apart.

## Evaluation

Same as the main preregistration. C1 and C2 are both reported, and the evaluator gets both
SHAs. Choosing between them on the evaluator's hidden holdout is a two-candidate comparison;
it is disclosed as such and not corrected for.
