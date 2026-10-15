# Agent Memory on the Agent Memory Leaderboard (AML) Cycle 2 Add/Search contract

This package runs Agent Memory as the memory system behind AML's two-operation evaluation
contract. AML calls `POST /add` with conversation messages and `POST /search` with a question.
AML owns answer generation, judging and scoring. This service owns only memory, and it
writes and reads through the public `AgentMemory` runtime (`AgentMemory.remember` and
`AgentMemory.recall`). There is no shadow index, no extra retriever, and no LLM.

**Status:** built and validated locally. It has **not** been deployed publicly, no AML key has
been requested, and no official evaluation has been run. Submitting needs explicit
authorization: see "Submission steps" below. The Cycle 2 deadline is 2026-10-31.

## Contract implemented

The official guide (`agentmemoryleaderboard.ai/api-guide`) was not reachable from the build
environment (DNS failure). The contract below is taken from section 05 ("ADD / SEARCH
CONTRACT") and section 06 ("ERROR HANDLING") of the guide, as quoted in
[eveiscoding/memory-retriever-xinyi-v1 `docs/API_CONTRACT.md`](https://github.com/eveiscoding/memory-retriever-xinyi-v1/blob/c9551c748a5af4cff4ab0f36c36d8d642b11d9e3/docs/API_CONTRACT.md).
Two other independent Cycle 2 adapters agree with it:
[syyr1987/hippocampus-mem](https://github.com/syyr1987/hippocampus-mem) and
[w6403/aml-memory-adapter](https://github.com/w6403/aml-memory-adapter). **Re-check it against
the live guide before deploying.**

| Item | Behaviour |
|---|---|
| `GET /health` | Unauthenticated; returns `200 {"status":"ok"}` |
| Auth | `Authorization: Bearer <key>`, `Authorization: Token <key>`, or `X-Api-Key: <key>`. Keys are compared in constant time. Anything else gets `401` |
| `POST /add` | `{request_id, user_id, session_id, messages:[{role, content, timestamp?}]}` returns `200 {"success":true, request_id, user_id, session_id}`, echoed exactly. It returns **only after every message has committed and is searchable**. It never returns 202 or a task id |
| `POST /search` | `{query, user_id, top_k, options?}` returns `200 {"data":[{id, content, score, created_at}]}`, holding at most `top_k` items in the runtime's ranked order, or `{"data":[]}` |
| Idempotency | The key is `(request_id, user_id)`. Replaying the same payload returns `200` and stores nothing. Reusing a key with a different payload returns `409`. The same `request_id` under another user is an independent request |
| Validation | Declared fields are strict and never coerced: string ids, non-empty `role` and `content`, integer-millisecond `timestamp`, integer `top_k`. A violation returns `422`. Undeclared fields are ignored. `top_k` above 200 is clamped, not refused |
| Errors | `{"detail":{"reason":…}}` with `400` (invalid JSON), `401`, `409`, `413` (body over 16 MB), `422`, `429` (over 128 requests in flight), or `500` (retryable; never a false `200`) |

### Memory semantics

- **Isolation.** Each `user_id` gets its own Agent Memory runtime root, which is its own
  SQLite database, at `<data>/users/<sha256(user_id)>`. Search opens only that root, so a
  query can't reach another user's memory. This is by construction, not by a filter.
  `session_id` is recorded but never used to narrow Search.
- **Content.** Each message is one memory, stored as `"[<ISO timestamp>] <role>: <content>"`.
  The timestamp prefix is included when one is given, and the timestamp also becomes the
  fact's `observed_at`. The stored text is what the AML answer model receives.
- **Search.** One `recall(query, budget=top_k)` call. For a multiple-choice question, the
  `options` are appended to the query text to widen lexical recall; the question itself is
  kept verbatim. `score` is `1/rank`, so it is monotone in the runtime's order.
- **Durability and crash safety.** A per-user `aml-ledger.sqlite3` (WAL, `synchronous=FULL`)
  records each request as pending before anything is written, then records each message's
  fact as it commits, then marks the request committed. A retry of a request a crash
  interrupted resumes it. Any fact the runtime committed before the ledger recorded it is
  adopted through `history(target_reference)`, so no message is stored twice. Search only
  returns facts the ledger has recorded.
- **Concurrency.** Different users run on separate runtimes. Runtime work is CPU-bound Python,
  so one compute slot (the default) serializes it and other requests queue. Measured on
  4 vCPU: interleaving 8 threads made Add **3×** slower and Search **9×** slower than
  serialized execution of the same work. See the evidence below.

## Evidence (local, 2026-10-15)

| Check | Result | File |
|---|---|---|
| Contract smoke, source tree | 21/21 | `evidence/2026-10-15-local/smoke-source-tree.json` |
| Contract smoke, installed wheel (non-editable) | 21/21 | `smoke-installed-wheel.json` |
| Contract smoke, Docker image | 21/21 | `smoke-container.json` |
| Container `SIGKILL` and restart: acknowledged memories intact, replay stores nothing, `SIGTERM` exits 0 | pass | `container-restart.txt` |
| Unit and integration tests, real runtime (SIGTERM and SIGKILL restarts, crash-window resume, 8 concurrent users with forced handle eviction, auth schemes, strict validation) | 10/10 | `tests/test_aml_service.py` |

The smoke checks are: health without auth; `401` on a bad or missing key; chunked Add with an
exact ID echo; searchable immediately after Add; the `data` array shape; non-empty
`id`/`content`; descending scores; all 45 acknowledged messages returned; `top_k` respected;
`options` accepted; idempotent replay storing nothing; `409` on reuse; isolation (an unknown
user gets `[]`, and a second user sees none of the first user's memories); and `422` on
malformed input.

Load probe: synthetic content, 20-message chunks, `top_k` = 100, every query lexically
overlapping every memory (a worst case for admission).

| Probe | Add per 20-msg chunk, p50 | Add wall | Search p50 | Search wall | Failures |
|---|---:|---:|---:|---:|---:|
| 1 user × 1,000 msgs, serial | 123 ms | 6.3 s | 103 ms | 2.1 s (20 searches) | 0 |
| 8 users × 1,000 msgs, 8 concurrent, **compute gate on** (shipped default) | 1,036 ms (queued) | 52.7 s | 874 ms (queued) | 17.6 s (160 searches) | 0 |
| 8 users × 1,000 msgs, 8 concurrent, no gate (before the fix) | 2,884 ms | 144.6 s | 7,889 ms | 157.6 s | 0 |

With the gate on, the service handles about **150 messages/s** of Add and **9 searches/s** at
1,000 memories per user on 4 vCPU. Service RSS was about 120 MiB, and disk use was about
14 KB per message (110 MB for 8,000 messages, including the governance ledger). AML's
published limits are a 1,200 s HTTP timeout per call and a 72 h budget for a Full run.
Queueing at the platform's default concurrency (Add 64, Search 32) stays well inside the
per-call timeout at these rates.

Code version for each row: the source-tree smoke and both ungated probes ran before the
compute gate was added. Every other row ran on the committed code.

## Deployment profile

Nothing here has been deployed or paid for.

- **Host.** One VM or container host with 2–4 vCPU, 4 GB RAM, and a persistent SSD volume
  (estimate about 15 KB per stored message). Use a single service process: per-user locking
  is in-process, so do **not** run several replicas against one data directory.
- **Container.**
  `docker build -f integrations/aml-cycle2/deploy/Dockerfile -t agent-memory-aml .`, then
  `docker run -d -e AML_MEMORY_KEY=… -v aml-data:/data -p 127.0.0.1:8080:8080 agent-memory-aml`.
  The image runs as non-root (uid 10001) with a health check. It refuses to start without a
  key of at least 16 characters. Behind a TLS-intercepting proxy, add
  `--secret id=extra_ca,src=<ca.pem>` to the build; the CA is never stored in a layer.
- **VM without a container.** Install with
  `pip install . ./integrations/aml-cycle2` into `/opt/agent-memory-aml`, then use
  `deploy/agent-memory-aml.service` (systemd, hardened, key file mode 0400).
- **TLS.** `deploy/Caddyfile` sets automatic HTTPS, the 16 MB body limit, and 1,200 s proxy
  timeouts. The service itself listens only on loopback or the container network.
- **Data obligations.** Data is used only for the evaluation run. Request bodies are never
  logged; logs record the method, path, status, latency, and a 12-character user hash.
  Delete the data volume within 30 days of the run.

### Reproducible smoke against any deployment

```bash
AML_MEMORY_KEY=… agent-memory-aml-smoke --base-url https://memory.example.org --report smoke.json
AML_MEMORY_KEY=… python -m aml_agent_memory.load_probe --base-url https://memory.example.org --users 8 --messages 1000
```

The smoke uses fresh random user ids and never reads existing data.

### Local run

```bash
pip install . ./integrations/aml-cycle2       # from the repository root
AML_MEMORY_KEY=$(openssl rand -hex 24) agent-memory-aml --data-dir ./aml-data --port 8080
PYTHONPATH=reference:integrations/aml-cycle2/src python -m unittest discover -s integrations/aml-cycle2/tests
```

## Submission steps (not executed; each needs explicit authorization)

1. Deploy the profile above to a public HTTPS hostname. This costs money: a VM, storage, and
   a domain or tunnel.
2. Submit the evaluation access request at `agentmemoryleaderboard.ai/evaluation`. AML
   issues an Eval Key, which is bound to the memory system key you register.
3. Run AML's non-scored compatibility smoke test with that key.
4. Start the Full evaluation. It is private until it completes and passes review.
5. Request publication. No leaderboard claim should be made until AML publishes the entry.

## Known limits

- Retrieval is the runtime's lexical and governed recall. There is no embedding route
  (the semantic extra is off), so paraphrased questions with no shared terms may recall
  nothing.
- Recall cost grows with how many of a user's memories match the query. In the worst-case
  probe above, Search took about 100 ms at 1,000 memories. Very long histories, such as
  BEAM's million-token conversations, were not probed.
