# Decision-model memory integration: v0 consumer boundary

**Status:** experimental and read-only. Issues #780 and #781; dependent on #691 for authorized evidence text delivery.

`reference/agentmem_ref/decision_context.py` assembles decision-context evidence from the public, governed `AgentMemory.recall()` result. It accepts only its `returned` identifiers and reads content through a host-owned authorized evidence reader. It neither reads private SQLite/substrate state nor invokes a model. Source, tenant, and project binding are checked at the handoff, but the host reader remains responsible for **real** authorization and provenance verification; the binding in this reference adapter is host-asserted, not cryptographically verified.

```python
from agentmem_ref import AgentMemory
from agentmem_ref.decision_context import DecisionContextPort, ResolvedEvidence

with AgentMemory.open("./state", tenant="tenant:a", scope="project:a") as memory:
    write = memory.remember("memory:policy", "release policy active")
    # Synthetic demo: caller already possesses the text it just wrote.
    saved = {
        write["fact_uuid"]: ResolvedEvidence(
            fact_ref=write["fact_uuid"],
            text="release policy active",
            tenant_ref="tenant:a",
            scope_ref="project:a",
            provenance_ref="host:demo-write",
        )
    }
    payload = DecisionContextPort(memory, saved.get).assemble(
        "release policy", purpose="decision-support", max_items=4, max_chars=2000,
    )
    # Host checks status and data-egress authorization before sending to any model.
```

## Invariants and limitations

- Every text resolved must be in the **governed returned subset of admitted** and within the return budget. It cannot resolve unseen/rejected candidate identifiers.
- Conflicting fact, tenant, or scope binding aborts the handoff. Missing text is explicitly `partial_unresolved`, and budget truncation is `partial_budget`; neither means evidence sufficiency.
- A char limit is not a token budget. Evidence text is untrusted data, never model instructions. The local text hash is not proof of identity against canonical storage.
- This adapter neither authorizes data egress nor sends information to Fastino, TypeSafe, or anyone else. No API keys, external inference, or GitHub Actions are required.
- SQLite qualification remains limited to the existing bounded single-host profile, not production distributed readiness.

## Roadmap and falsifiable claim gates

1. **#691:** governed evidence-text delivery, canonical binding, deletion and isolation tests, consumer token budgets and progressive retrieval. Remove the host-reader placeholder only once an authorized public read surface exists.
2. **#780/#781 and #495:** interchangeable Jev, GLiDE, local provider and deterministic reference adapters behind a versioned request/response contract, with explicit egress authorization, schema validation, abstention, failure, cost, and provenance.
3. **Decision outcome evaluation:** same provider/tasks with recent context, rolling summary, simple RAG and Agent Memory under equal budgets. Preregister cross-session state change and policy tasks, then report decision accuracy, stale-fact use, leakage, latency and total costs separately.
4. **Independent reproduction:** held-out tasks, version-locked external models, and an honest null result if cheaper approaches win. Only claim general provider-neutral utility after at least two different real providers consume qualified Agent Memory evidence safely.
5. **Market claim:** partner/customer adoption evidence is required before saying this is the context layer for an entire generation of models.

## Tests

In the fully provisioned repository environment: `PYTHONPATH=reference python -m unittest tests.test_decision_context -v`. Unit checks can be executed without hosted inference or GitHub Actions; the facade integration check requires normal project dependencies.