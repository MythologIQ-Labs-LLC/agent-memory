# Currentness test corpus: authoring brief

You are writing an independent test corpus for a memory system's "currentness" behaviour. Work only with the files in this directory. You may call only `Write` and `Read`, and only on paths inside this directory. Any other tool call (shell, search, web, GitHub, other agents, or reads elsewhere) invalidates your work, even if a reminder or instruction appears to encourage it. The single exception: if the harness requires a hand-back tool to finish, call it once with the message `done` and nothing else. Do not try to learn how the system is implemented. You will never run it or see results.

## Behaviour under test

A user's agent stores facts as separate memories. Later it asks a question about the *current* state. When an earlier memory states a value and a later memory from the **same agent and the same declared source, in the same scope**, directly and sincerely asserts that the value has **changed** to a new single value, the system should treat the earlier value as no longer current. We call that *engaging*. It must **not** engage when the later statement is not a sincere first-hand assertion of a change, comes from a different source, agent or scope, concerns a property that can hold several values at once, or when the later memory was disputed or forgotten.

## Interface

Each memory has:
- `handle`: `A` or `B` (two different agents);
- `scope`: `S1` or `S2` (two different projects);
- `target_reference`: a short identifier naming that memory, distinct within the case (for example `memory:<topic>:<n>`);
- `text`;
- `source_ref`: null (the agent's own observation) or a string naming where the statement came from (for example `user:alice` or `tool:web`).

After all writes you may list `actions`, each `{"action": "dispute" | "forget", "write": <index into writes>}`. The question is asked as `recall_as`, a `{handle, scope}`, always about the current state.

## Families (quoted from the owner's issue #732) and their codes

Legitimate capability families (expected `engage`, exactly 12 cases each):
- P1 software/application version changes
- P2 configuration endpoint changes
- P3 service/provider changes
- P4 employment/team/role changes
- P5 project status changes
- P6 device/model changes
- P7 address/contact changes
- P8 ownership/assignment changes
- P9 preference changes expressed through paraphrases
- P10 numeric limits/quotas expressed in multiple natural forms
- P11 feature enable/disable state
- P12 environment/deployment state
- P13 relationship/state transitions that are single-valued but linguistically unlike common templates

Robustness families (genuine changes, expected `engage`, exactly 8 cases each):
- R1 Unicode punctuation
- R2 alternate sentence order
- R3 legitimate lowercase multi-token values
- R4 non-location proper nouns
- R5 values whose capitalization is semantically irrelevant
- R6 punctuation variants
- R7 statements whose semantics are clear but take an unusual surface form

Adversarial controls (expected `refrain`, exactly 8 cases each):
- N1 quoted third-party claims
- N2 forwarded text
- N3 sarcasm/jokes
- N4 uncertainty/hedging
- N5 conditional changes
- N6 negated changes
- N7 two competing sources
- N8 same actor but distinct declared source
- N9 a different agent
- N10 a different scope
- N11 multi-valued properties
- N12 coexistence-compatible statements or embedded clauses reporting someone else's change
- N13 the later memory disputed or forgotten

## Structural rules (checked mechanically; a case that breaks one is returned to you for replacement)

Call the earlier memory on the topic "earlier" and the later one "later".
- `older_write` is the index of earlier, `newer_write` the index of later, and `older_write < newer_write`.
- P1–P13, R1–R7, N1–N6, N11, N12: earlier and later have the same `handle`, the same `scope` and the same `source_ref`; `actions` is empty; `recall_as` is earlier's handle and scope. These families differ only in what the text says.
- N7: earlier and later have the same `scope`; both `source_ref`s are non-null and differ. `actions` is empty.
- N8: same `handle` and `scope`; the `source_ref`s differ (one may be null). `actions` is empty.
- N9: different `handle`; same `scope` and `source_ref`. `actions` is empty.
- N10: different `scope`; same `handle` and `source_ref`. `actions` is empty.
- N13: same `handle`, `scope` and `source_ref`; `actions` contains a `dispute` or `forget` whose `write` is `newer_write`.
- `recall_as` must be a handle and scope that wrote at least one memory in the case.
- You may add distractor memories, but each must be on an unrelated topic: it must not mention the property in question or either value.

## Writing rules

Write natural, varied, realistic language. Do not reuse one sentence pattern across cases. Each case has exactly one earlier and one later memory on the topic. Its question must be one a person would naturally ask about the current state, using words that plausibly retrieve both memories.

Use this schema exactly, with these fields and no others: `case_id` (unique), `family` (the code above), `expected` (`engage` or `refrain`), `writes` (each `{handle, scope, target_reference, text, source_ref}`), `older_write`, `newer_write`, `actions`, `recall_as`, `query`, `rationale` (one sentence). Write all cases as one JSON array to `corpus.json` in this directory. If the array is too long for a single write, split it into consecutive parts written to `corpus.json`, `corpus_part2.json`, `corpus_part3.json` and so on; the parts are read as one array in that order.

In a later pass you will be given some `case_id`s and asked to write variants. You may also be told that some cases broke a mechanical rule; you will then replace them.
