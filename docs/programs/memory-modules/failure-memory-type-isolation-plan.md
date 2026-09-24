# Failure Memory Type Isolation Plan

This bounded closeout plan belongs to #471 and exists because specialized failure-memory recall must not reactivate unrelated facts admitted by the shared governed adapter.

Implementation rule:

```text
candidate generation
  -> governed adapter admission
  -> failure-memory ownership/type filter
  -> current revision check
  -> failure-state check
  -> contextual policy
  -> active failure guidance
```

The type filter may only narrow an already-governed admitted set. It may not admit a candidate the adapter refused, mutate state, or grant action authority.

Required tests:

- an unrelated fact matching the same query can remain an adapter-level admitted fact but is refused by the failure-memory surface as a type mismatch;
- a superseded historical failure revision is not reactivated;
- the current failure revision remains active when otherwise admissible;
- disputed and retracted failure state remains inactive;
- restart restores the exact ownership map used by the type filter;
- all filtering outcomes keep `authority_effect = none`.
