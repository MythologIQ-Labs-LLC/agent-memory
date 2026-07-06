# Memory Unit Examples

## Purpose

These examples show how different memory types should be represented under the doctrine.

The point is not to freeze an implementation schema forever. The point is to make memory objects carry enough identity, provenance, evidence, lifecycle, and authority information that future systems cannot pretend a summary is the same thing as a governed memory. Tempting, but no.

## Example: durable decision memory

```json
{
  "id": "uor:decision:project-memory-boundary",
  "type": "decision",
  "state": "crystallized",
  "content_ref": "repo://agent-memory/docs/adr/ADR-001-uor-is-identity-not-memory.md",
  "provenance": {
    "origin": "human-authored architecture decision",
    "observer": "agent-memory doctrine",
    "method": "ADR acceptance",
    "timestamp": "2026-07-06T00:00:00Z"
  },
  "evidence": [
    {
      "id": "evidence:adr-001",
      "kind": "architecture_decision_record",
      "ref": "docs/adr/ADR-001-uor-is-identity-not-memory.md",
      "confidence": 1
    }
  ],
  "saturation": {
    "sigma": 0.98,
    "calibrated": true,
    "threshold": 0.95,
    "durability_dimensions": ["approval", "cross_reference", "doctrine_dependency"]
  },
  "authority": {
    "pama_outcome": "allow_with_ledger",
    "risk_class": "high",
    "policy_refs": ["ADR-003", "ADR-004"]
  },
  "certification": {
    "status": "pass",
    "ref": "pull-request-review-or-merge-record",
    "scope": "doctrine"
  }
}
```

## Example: code artifact memory

```json
{
  "id": "uor:code:codegenome-overlay-edge",
  "type": "code_artifact",
  "state": "linked",
  "content_ref": "codegenome://graph/node/example",
  "provenance": {
    "origin": "CodeGenome graph extraction",
    "observer": "CodeGenome",
    "method": "tree-sitter plus semantic overlay",
    "timestamp": "2026-07-06T00:00:00Z"
  },
  "evidence": [
    {
      "id": "evidence:syntax-overlay",
      "kind": "syntax_overlay",
      "ref": "codegenome://overlay/syntax/example",
      "confidence": 1
    },
    {
      "id": "evidence:semantic-overlay",
      "kind": "semantic_overlay",
      "ref": "codegenome://overlay/semantic/example",
      "confidence": 0.8
    }
  ],
  "saturation": {
    "sigma": 0.71,
    "calibrated": true,
    "threshold": 0.95,
    "durability_dimensions": ["graph_reference", "impact_relevance", "observer_confidence"]
  },
  "authority": {
    "pama_outcome": "allow_with_ledger",
    "risk_class": "medium",
    "policy_refs": ["ADR-005"]
  },
  "certification": {
    "status": "pending",
    "scope": "code-reality-graph"
  }
}
```

## Example: correction memory

```json
{
  "id": "uor:correction:stale-decision-update",
  "type": "correction",
  "state": "corrected",
  "content_ref": "ledger://corrections/stale-decision-update",
  "provenance": {
    "origin": "user correction",
    "observer": "governed memory runtime",
    "method": "dispute resolution workflow",
    "timestamp": "2026-07-06T00:00:00Z"
  },
  "evidence": [
    {
      "id": "evidence:user-correction",
      "kind": "human_correction",
      "ref": "ledger://corrections/stale-decision-update/source",
      "confidence": 1
    },
    {
      "id": "evidence:prior-state",
      "kind": "prior_memory_state",
      "ref": "ledger://memory/prior-version",
      "confidence": 1
    }
  ],
  "saturation": {
    "sigma": 0.97,
    "calibrated": true,
    "threshold": 0.95,
    "durability_dimensions": ["human_correction", "dispute_resolution", "audit_continuity"]
  },
  "authority": {
    "pama_outcome": "allow_with_ledger",
    "risk_class": "high",
    "policy_refs": ["ADR-004"]
  },
  "certification": {
    "status": "pass",
    "ref": "ledger://corrections/stale-decision-update/certificate",
    "scope": "corrected-memory"
  }
}
```

## Example: Shadow Genome failure memory

```json
{
  "id": "uor:failure:hallucination-permanence",
  "type": "failure",
  "state": "crystallized",
  "content_ref": "shadow-genome://failures/hallucination-permanence",
  "provenance": {
    "origin": "conformance failure analysis",
    "observer": "Shadow Genome",
    "method": "negative memory capture",
    "timestamp": "2026-07-06T00:00:00Z"
  },
  "evidence": [
    {
      "id": "evidence:failed-trap-class",
      "kind": "conformance_failure",
      "ref": "fixtures/confidently-wrong-memory.json",
      "confidence": 1
    }
  ],
  "saturation": {
    "sigma": 1,
    "calibrated": true,
    "threshold": 0.95,
    "durability_dimensions": ["safety_relevance", "failure_recurrence", "policy_dependency"]
  },
  "authority": {
    "pama_outcome": "allow_with_ledger",
    "risk_class": "critical",
    "policy_refs": ["ADR-002", "ADR-003", "ADR-004"]
  },
  "certification": {
    "status": "pass",
    "ref": "shadow-genome://certificates/hallucination-permanence",
    "scope": "negative-memory"
  }
}
```

## Rule

Examples are allowed to be implementation-flavored.

Doctrine docs are not.
