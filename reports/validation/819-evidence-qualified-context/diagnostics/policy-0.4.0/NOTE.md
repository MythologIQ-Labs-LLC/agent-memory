# Policy 0.4.0 (head f8556a79, selector blob 78c5c6c2): three turn-plane losses, a tokeniser bug

LongMemEval_S turn plane: evidence_qualified complete 367/428 vs default 369/428 (753/842 required
items vs 756/842); questions `bbf86515`, `gpt4_2f56ae70`, `7e974930`. All three lost gold turns are
first-person texts whose only first-person markers are contractions ("I'm", "I've", "I'll"). The
tokeniser keeps a contraction as one token, so `first_person()` returned False, and the first-person
query's third-party rule declined them as `subject_mismatch` on a proper-noun possessive they mention
("SpeedShine's", "The Handmaid's", "Mother's"). Session plane at 0.4.0: 428/428, zero loss.
Fixed in 0.4.1 (`_contraction_base`); contractions of function words are also no longer content terms.
