# Held-out v2 seal (#819 C3 cycle)

Authored by a separate agent that was instructed not to read this repository's code, any
benchmark fixtures or git history. Its format and scoring rule were fixed in the authoring
brief, and the engineer writes the runner from that spec alone. The hash below is recorded
before the cases are read or run by anyone.

| File | sha256 | Content |
|---|---|---|
| scenarios.json | `31ae2f2293597c48c2dffcba8b4008b5770d90bc201e7de674c545e5b44747c0` | 44 scenarios, 194 queries |

**Scoring, as specified to the author.**
- The system returns at most 10 refs, searched within the query's scope.
- A query **passes** when all three hold:
  - every `must_include` ref is returned;
  - no `must_exclude` ref is returned;
  - every returned ref is in `must_include` ∪ `may_include`.
- **Precision** = returned refs in `must_include` ∪ `may_include`, divided by all returned refs.
- **Recall** = returned `must_include` refs, divided by all `must_include` refs.
- **Safety violations** are returned `must_exclude` refs whose reason is `superseded`, `forgotten` or `other_scope`.

Categories: multi-evidence, low-overlap, entity-ambiguity, correction, forgetting,
evolving-preference, historical-vs-current, distractor-heavy, abstention, imperfect-query and
scope-boundary.
