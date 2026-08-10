# Agentic Memory Theory and Development

## Purpose

This document turns the broader memory theory into an engineering model for agentic systems.

It defines what should count as agent memory, how memory functions differ, which operations a capable memory system should expose, how memory should be governed, and how implementations should be evaluated.

## Definition

**Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That boundary may be:

- token to token
- step to step
- task to task
- session to session
- deployment to deployment
- agent to successor agent
- individual agent to team or organization

This definition deliberately excludes the idea that memory is synonymous with vector retrieval.

## The seven functions of agentic memory

A mature agent-memory architecture should support seven distinct functions:

```text
1. encode
2. retain
3. consolidate
4. retrieve
5. revise
6. forget
7. inherit
```

### Encode

Turn observations, actions, outcomes, corrections, and decisions into candidate memory.

### Retain

Keep selected information across the relevant boundary.

### Consolidate

Transform repeated or important experience into more durable or reusable representations.

### Retrieve

Select retained information that is appropriate to the current task and authority scope.

### Revise

Correct, refine, supersede, split, or dispute existing memory when new evidence arrives.

### Forget

Suppress, decay, archive, delete, or abstract information according to policy.

### Inherit

Provide new agents or agent generations with knowledge they did not personally experience.

## Memory operation surface

An implementation should expose explicit operations rather than hiding all memory behavior inside prompts.

Minimum conceptual API:

```text
observe(input)
propose_memory(observation)
admit(candidate, policy)
store(memory_unit)
retrieve(query, scope, policy)
reinforce(memory_id, evidence)
revise(memory_id, mutation)
consolidate(memory_ids, target_type)
dispute(memory_id, evidence)
supersede(old_id, new_id)
forget(memory_id, mode)
explain(memory_id)
audit(memory_id)
```

Advanced systems may additionally expose:

```text
reflect()
generalize()
rehearse()
replay()
archive()
restore()
share()
inherit()
revoke()
certify()
```

## Memory taxonomy

No single taxonomy is sufficient. Agent memory should be classified along several independent dimensions.

### Dimension 1: temporal scope

| Class | Scope | Examples |
|---|---|---|
| Immediate | current model step | intermediate calculation, tool result |
| Working | current active reasoning context | scratch state, current plan |
| Session | current task or conversation | local decisions, temporary entities |
| Episodic | prior sessions or trajectories | past interaction, action/outcome trace |
| Long-term | durable reusable state | preferences, facts, procedures |
| Remote | deeply consolidated state | stable policies, mature world knowledge |
| Inherited | predates current agent experience | pretrained knowledge, seed policy, organizational rules |

### Dimension 2: content type

| Type | Description | Examples |
|---|---|---|
| Observation | perceived state | page content, sensor reading, message |
| Episodic | event in context | "deployment failed after migration" |
| Semantic | generalized fact or concept | "service X requires header Y" |
| Procedural | how to perform a task | runbook, tool sequence |
| Prospective | intended future action | follow-up, deadline, pending commitment |
| Preference | actor-specific choice | formatting preference, product preference |
| Relationship | relation among actors/entities | ownership, dependency, trust |
| Policy | authoritative constraint | retention rule, approval boundary |
| Failure | unsuccessful action and cause | known environment gotcha |
| Correction | explicit revision | user correction, bug fix |
| Decision | chosen action plus rationale | architecture decision |
| Evidence | support for another claim | logs, source artifact, witness record |
| Model | compact representation of environment | topology, workflow, causal graph |

### Dimension 3: representation

Memory may be represented as:

- exact records
- natural-language notes
- key-value state
- relational tables
- graphs
- embeddings
- event logs
- summaries
- procedural code
- symbolic rules
- learned model parameters
- adapters
- multimodal artifacts

The representation should follow the memory function. Embeddings are useful indexes, not universal memory objects.

### Dimension 4: control

| Control style | Description |
|---|---|
| Heuristic | fixed rules decide write/read behavior |
| Model-directed | LLM chooses memory actions |
| Policy-directed | governance policy constrains actions |
| Learned | memory control optimized through training |
| Human-governed | user or operator approves important transitions |
| Hybrid | combinations of the above |

## Write-path architecture

A trustworthy memory system should separate **experience** from **admitted memory**.

```text
raw experience
   |
   v
candidate extraction
   |
   v
sensitivity + scope classification
   |
   v
source trust + evidence assessment
   |
   v
novelty / contradiction analysis
   |
   v
policy admission
   |
   +--> reject
   +--> ephemeral
   +--> store as observation
   +--> store + request verification
   +--> consolidate into existing memory
   +--> propose durable promotion
```

Why this matters:

- prompt injection should not automatically become durable preference
- model speculation should not silently become fact
- repeated junk should not gain permanence through access count
- sensitive data should not be stored simply because it was mentioned

## Read-path architecture

Retrieval is also an admission decision.

```text
query / task
   |
   v
scope resolution
   |
   v
candidate generation
(exact + graph + temporal + semantic + procedural)
   |
   v
freshness / contradiction filtering
   |
   v
sensitivity + authority filtering
   |
   v
task-conditioned ranking
   |
   v
context assembly
   |
   v
recall explanation
```

Similarity alone is insufficient.

A semantically related memory may be:

- stale
- from the wrong user
- outside the current task scope
- maliciously injected
- contradicted
- too sensitive
- historically valid but currently superseded

## Memory as a control channel

Persistent memory can change how an agent interprets future instructions and which tools it chooses.

This makes memory a durable control channel.

Security boundaries should therefore exist at both:

```text
write time
and
read time
```

A system that validates writes but injects every retrieved memory into context without policy is still vulnerable.

## Memory consolidation

Consolidation is the transformation of lower-level retained experience into more useful durable state.

Possible transformations:

### Episodic to semantic

```text
Episode A: API returned 401 without tenant header
Episode B: API returned 401 without tenant header
Episode C: API succeeded after tenant header was added

=> Semantic memory:
"This API requires the tenant header."
```

### Episodic to procedural

```text
several successful task trajectories
=> reusable runbook
```

### Failure to guardrail

```text
repeated unsafe action + correction
=> policy or procedural constraint
```

### Multiple facts to model

```text
entities + relations + outcomes
=> environment graph / causal model
```

Every derived memory should preserve provenance to its supporting evidence.

## Reflection is not automatically truth

Many agent architectures use "reflection" to synthesize higher-level memories.

Reflection can be useful, but it is an inference operation.

Therefore:

```text
reflection output != evidence
reflection output != certification
reflection output != user intent
```

Reflections should carry:

- source memory references
- synthesis method/model
- confidence
- contradiction state
- creation time
- scope
- authority level

## Short-term and long-term memory should cooperate

Treating STM and LTM as unrelated subsystems forces awkward heuristics at the boundary.

A better model is a memory-control loop:

```text
active context
  <-> retrieval
  <-> long-term stores
  <-> consolidation
  <-> forgetting
```

The agent should be able to decide, under policy:

- what remains only in active context
- what is summarized
- what is stored durably
- what needs verification
- what should be discarded
- when old memory should be reloaded

Recent research increasingly treats memory operations themselves as agent actions rather than fixed plumbing. That direction is compatible with this doctrine only when learned autonomy remains bounded by authority, provenance, and deletion requirements.

## Prospective memory deserves first-class treatment

Most agent-memory systems focus on remembering the past.

Agents also need to remember **what must happen later**.

Prospective memory includes:

- deadlines
- promises
- pending reviews
- follow-ups
- conditions to recheck
- deferred tool actions
- dependency resolution

A prospective memory should include:

```yaml
intent: ...
trigger: time | event | state_change | manual
owner: ...
scope: ...
status: pending | satisfied | cancelled | expired
created_at: ...
due_at: ...
dependency_refs: [...]
authority: ...
```

This should not be confused with an execution scheduler. Memory records the obligation and state; another subsystem may perform or schedule the action.

## Procedural memory deserves first-class treatment

An agent that remembers facts but repeatedly relearns how to complete the same workflow has weak memory.

Procedural memory may store:

- successful action sequences
- environment-specific runbooks
- tool usage constraints
- recovery procedures
- diagnostic patterns
- verification methods

Procedure memory should be versioned because environments change.

## Failure memory

Failure is one of the highest-value memory classes for autonomous agents.

A useful failure memory should capture:

```yaml
attempt: ...
context: ...
expected_outcome: ...
actual_outcome: ...
root_cause: ...
correction: ...
verification: ...
applicability: ...
expires_or_recheck: ...
```

The important part is not "remember that something failed." It is retaining enough causal structure to prevent recurrence without overgeneralizing the failure.

## Multi-agent and shared memory

Shared memory introduces additional dimensions:

- owner
- contributor
- observer
- tenant
- role
- trust domain
- write authority
- read authority
- dispute authority
- inheritance rules

A useful mental model is:

```text
private memory
team memory
organizational memory
public memory
```

Promotion between scopes should be governed.

Private experience should never become organizational truth simply because one agent wrote it into a shared database.

## Inherited memory

New agent instances may begin with state they never experienced.

Inherited memory can include:

- model weights
- system policy
- organizational doctrine
- long-term user memory
- environment maps
- runbooks
- source reputation
- prior agent lessons

Inherited memory must be labeled as inherited so the new agent does not misrepresent it as direct observation.

Recommended provenance field:

```yaml
acquisition_mode: observed | inferred | taught | inherited | imported | synthesized
```

## Memory confidence model

At minimum, keep these separate:

```text
confidence: how strongly evidence supports the content
trust: how reliable the source is
relevance: how useful it is to the current task
saturation: how much persistence pressure it has accumulated
authority: whether a transition is permitted
certification: whether a required confirmation gate passed
```

A single scalar cannot safely replace all six.

## Memory anti-patterns

### 1. Vector database equals memory

Similarity search is an indexing technique.

### 2. Store every turn forever

This converts write-path laziness into read-path chaos.

### 3. Summaries without provenance

A concise hallucination is still a hallucination.

### 4. Retrieval count equals importance

Popularity loops can manufacture false salience.

### 5. Latest write wins

Newer is not always more authoritative.

### 6. Reflection equals truth

Synthesis requires evidence and scope.

### 7. One global user profile

Preferences and facts may be context-specific.

### 8. Silent overwrite

Corrections require history.

### 9. No forgetting policy

Retention becomes accidental permanence.

### 10. Memory evaluation equals QA recall

Memory matters because it changes action.

## Evaluation framework

A serious memory system should be evaluated across the full lifecycle.

### Encoding metrics

- useful-memory precision
- useful-memory recall
- sensitive-data rejection
- duplicate suppression
- unsupported-inference admission rate

### Retrieval metrics

- relevant recall
- temporal correctness
- scope correctness
- source diversity
- stale-memory rate
- contradiction contamination
- abstention quality

### Consolidation metrics

- abstraction accuracy
- provenance completeness
- transfer utility
- exception preservation
- compression ratio

### Revision metrics

- correction propagation
- supersession accuracy
- dispute handling
- rollback integrity

### Forgetting metrics

- false permanence
- valuable-memory loss
- stale recall
- deletion completeness
- interference reduction

### Agent outcome metrics

- task success
- avoided repeated failures
- reduced redundant exploration
- policy compliance
- tool-call quality
- latency
- token cost

### Security metrics

- memory-poisoning success rate
- cross-tenant leakage
- memory-induced jailbreak rate
- unauthorized mutation rate
- provenance stripping rate

## Benchmark doctrine

Benchmarks should distinguish at least four levels:

```text
Level 1: recall
Can the system retrieve a past fact?

Level 2: temporal and update reasoning
Can it distinguish current, historical, superseded, and conflicting state?

Level 3: memory-guided action
Does retained experience improve future task execution?

Level 4: governed memory
Can it improve behavior while preserving scope, authority, privacy, provenance, and correction?
```

A system that scores well at Level 1 may still fail badly at Level 3 or 4.

## Development sequence

Recommended order for building a new Agent Memory implementation:

### Phase 1: contracts

Define:

- memory unit schema
- identity
- provenance
- scope
- lifecycle states
- mutation events

### Phase 2: write admission

Implement:

- candidate extraction
- sensitivity classification
- source classification
- deduplication
- admission policy

### Phase 3: retrieval

Implement multiple recall paths:

- exact
- semantic
- temporal
- graph
- procedural

Then add policy-aware reranking.

### Phase 4: correction

Implement:

- dispute
- supersession
- mutation history
- rollback
- conflict resolution

### Phase 5: forgetting

Implement:

- decay
- archive
- pruning
- deletion
- tombstones
- dependency checks

### Phase 6: consolidation

Implement:

- summaries
- semantic extraction
- procedure induction
- reflection with provenance

### Phase 7: governance

Enforce:

- authority
- certification
- privacy
- tenancy
- audit

### Phase 8: evaluation

Test the full lifecycle with adversarial fixtures and memory-guided tasks.

## Conformance questions

An implementation claiming Agent Memory alignment should be able to answer:

1. What exactly is a memory unit?
2. Which persistence boundary does each memory class cross?
3. What is stored as raw evidence versus synthesis?
4. Who may create, revise, promote, or delete memory?
5. How is source trust represented?
6. How are contradictions handled?
7. How does the system distinguish current from historical truth?
8. How does forgetting work?
9. How does user deletion propagate through derived state?
10. How is sensitive memory scoped at retrieval time?
11. How is memory poisoning detected or contained?
12. How are procedures and failures retained?
13. How are prospective commitments represented?
14. How is inherited memory distinguished from direct experience?
15. What benchmark demonstrates improved agent behavior rather than simple recall?

If those answers are missing, the system probably has a retrieval feature, not a memory architecture.

## Related documents

- `AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`
- `06-conformance-test-plan.md`
- `09-calibration-protocol.md`
- `11-component-architecture.md`
- `20-memory-foundations-across-scales.md`
- `21-forgetting-consolidation-and-memory-metabolism.md`
- `23-research-bibliography.md`
