
### LongMemEval_S session, 500 questions, k=50 (input d6f21ea9d60a)

| arm | complete | required items | delivered items | no-answer abstained (items delivered) |
|---|---|---|---|---|
| default `all_returned`, PR head `db81778c` | 428/428 | 803/803 | 19,187 | 0/72 (3,344 items) |
| opt-in 0.5.1, PR head | 428/428 | 803/803 | 18,390 | 0/72 (3,194 items) |
| default, experiment flag off | 428/428 | 803/803 | 19,187 | 0/72 (3,344 items) |
| opt-in 0.5.2, experiment flag off | 428/428 | 803/803 | 19,135 | 0/72 (3,329 items) |
| **default, content-term admission ON** | 406/428 | 775/803 | 6,586 | 0/72 (1,586 items) |
| **opt-in 0.5.2, content-term admission ON** | 406/428 | 775/803 | 6,544 | 0/72 (1,574 items) |
| SQLite FTS5 | 401/428 | 768/803 | 8,891 | 0/72 (2,562 items) |

default-arm returned ids, PR head vs experiment flag off, all 500 questions identical: True

### LongMemEval_S turn, 500 questions, k=50 (input d6f21ea9d60a)

| arm | complete | required items | delivered items | no-answer abstained (items delivered) |
|---|---|---|---|---|
| default `all_returned`, PR head `db81778c` | 369/428 | 756/842 | 21,400 | 0/72 (3,600 items) |
| opt-in 0.5.1, PR head | 369/428 | 756/842 | 19,316 | 0/72 (3,347 items) |
| default, experiment flag off | 369/428 | 756/842 | 21,400 | 0/72 (3,600 items) |
| opt-in 0.5.2, experiment flag off | 369/428 | 756/842 | 21,347 | 0/72 (3,582 items) |
| **default, content-term admission ON** | 382/428 | 780/842 | 11,928 | 0/72 (2,591 items) |
| **opt-in 0.5.2, content-term admission ON** | 382/428 | 780/842 | 11,861 | 0/72 (2,564 items) |
| SQLite FTS5 | 362/428 | 737/842 | 13,819 | 0/72 (3,219 items) |

default-arm returned ids, PR head vs experiment flag off, all 500 questions identical: True

### LoCoMo (AMB export locomo10 @ 03c1d0f1), 1540 questions, k=10

| arm | complete | required items | delivered items | no-answer abstained (items delivered) |
|---|---|---|---|---|
| default, PR head | 1278/1531 | 1734/2102 | 15,310 | 0/9 (90 items) |
| opt-in 0.5.1, PR head | 1278/1531 | 1734/2102 | 15,310 | 0/9 (90 items) |
| default, flag off | 1278/1531 | 1734/2102 | 15,310 | 0/9 (90 items) |
| opt-in 0.5.2, flag off | 1278/1531 | 1734/2102 | 15,310 | 0/9 (90 items) |
| **default, admission ON** | 1277/1531 | 1733/2102 | 15,261 | 0/9 (90 items) |
| **opt-in 0.5.2, admission ON** | 1277/1531 | 1733/2102 | 15,261 | 0/9 (90 items) |
| SQLite FTS5 | 1273/1531 | 1732/2102 | 15,269 | 0/9 (90 items) |

### #825 synthetic workload (14 cases, single-sentence facts, k=5, 3 repeats)

| size | arm | needed | strict | primary extras | forbidden | abstention |
|---|---|---|---|---|---|---|
| 1000 | sqlite_fts5_bm25 | 11/11 | 1 | 42 | 2 | 0/2 |
| 1000 | agent_memory_context_default (flag off) | 11/11 | 0 | 52 | 2 | 0/2 |
| 1000 | agent_memory_context_lexical (flag off) | 11/11 | 4 | 21 | 2 | 0/2 |
| 1000 | agent_memory_context_eq (flag off) | 11/11 | 0 | 50 | 2 | 0/2 |
| 1000 | agent_memory_context_default (flag content_term) | 11/11 | 1 | 34 | 2 | 0/2 |
| 1000 | agent_memory_context_lexical (flag content_term) | 11/11 | 1 | 33 | 2 | 0/2 |
| 1000 | agent_memory_context_eq (flag content_term) | 11/11 | 1 | 34 | 2 | 0/2 |
| 19000 | sqlite_fts5_bm25 | 11/11 | 1 | 42 | 2 | 0/2 |
| 19000 | agent_memory_context_default (flag off) | 11/11 | 0 | 52 | 2 | 0/2 |
| 19000 | agent_memory_context_lexical (flag off) | 11/11 | 4 | 21 | 2 | 0/2 |
| 19000 | agent_memory_context_eq (flag off) | 11/11 | 0 | 50 | 2 | 0/2 |
| 19000 | agent_memory_context_default (flag content_term) | 11/11 | 1 | 34 | 2 | 0/2 |
| 19000 | agent_memory_context_lexical (flag content_term) | 11/11 | 1 | 33 | 2 | 0/2 |
| 19000 | agent_memory_context_eq (flag content_term) | 11/11 | 1 | 34 | 2 | 0/2 |
