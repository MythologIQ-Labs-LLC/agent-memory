# Held-out retrieval-precision cohort (sealed)

Design: 59 beliefs (57 for test-user, 2 for other-user as isolation checks) across three non-software,
non-fiction domains: domain:home (dog, kitchen remodel, garden, HVAC), domain:finance (Roth IRA, mortgage,
budgeting, taxes, giving) and domain:health (strength training, diet, knee injury, medication, sleep), plus
5 user:universal communication preferences. Hard structure: two cross-domain name collisions (Mercury =
dog vs. fund; Atlas = mortgage lender vs. strength program) plus an other-user "Mercury"; supersession
chains of length 2 and 3 (dog food, contractor, countertops x3, Roth allocation, emergency fund, workout
schedule, diet x3); 6 open questions (3 resolved); 3 relation beliefs; 4 pinned test-user beliefs; heavy
reuse of generic words (plan, budget, weekly, schedule, goal) to make word overlap misleading.

Expectations were judged by meaning: shouldOnlyInclude lists only current, in-scope, non-pinned,
non-open-question beliefs a careful assistant would want; relation hits include in-scope participants.
70 cases: 31 single-belief, 12 multi-belief (2-4), 27 expect [].
Categories: paraphrase 13, out-of-scope 6, name-collision 5, distractor-overlap 5, supersession 4,
pinned-only 4, multi-belief 4, terse 3, relation 3, open-question-only 3, resolved-question 3,
general-knowledge 3, universal 3, direct 2, typo 2, negation 2, isolation 2, unrelated 2, exploratory 1.

Independence: authored entirely from my own judgement. I did NOT read the memory system's source code,
any existing benchmark fixtures, git history, or anything under /home/user/agent-memory or /tmp/claude-0
other than this output directory, and did not search the web for benchmark fixtures. Structure was
checked with an ad-hoc inline Python validator (ids, references, scope/pinned/superseded/resolved rules).
