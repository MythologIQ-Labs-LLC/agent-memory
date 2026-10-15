# #819 hidden holdout cohort: pre-candidate commitment

Registered 2026-10-15T13:36:20Z, before any #819 candidate revision was received or evaluated.
The cohort content (queries, memory texts, expected and excluded items) stays private until
the engineering session freezes a candidate SHA. Only these SHA-256 values are published now,
so the cohort and scoring cannot be changed after candidate performance is seen.

| File | SHA-256 |
| --- | --- |
| `generate.py` (deterministic generator, fixed seed) | `26ea8054bc7977d3013ec2d90c5041e1aa067a3f0dea5417257c11e21c156678` |
| `harness.py` (public-facade runner and predeclared scoring) | `805d76b1a4eb61207aefdb527648388f1d68985dcc841720435551ec1a35d365` |
| `cases.json` (generated cohort) | `8674577ec8e9f467ad1633b302f96f519361942d57becd11325dcb166c14e962` |

Shape, public: 160 scenarios and 176 queries, 16 scenarios in each of ten categories:
factual precision, query disambiguation, corrected memory, temporal currentness, conflicting
unreconciled statements, multi-hop, abstention, cross-scope isolation, irrelevant context and
multi-session use (which also checks a forgotten memory never resurfaces). Every scenario runs
in a fresh store through the public `AgentMemory` facade only (`remember`, `correct` with
qualified evidence, `forget`, `recall(budget=5)`); logical references are opaque hashes.

Scoring is fixed in `harness.py`: strict pass per query, precision, recall, abstention (empty
return), ordering where declared, and three hard gates that must stay at zero: cross-scope
leaks, forgotten-memory resurfacing, and stale (superseded) values returned as current.
