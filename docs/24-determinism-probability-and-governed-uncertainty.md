# Determinism, Probability, and Governed Uncertainty

## Status

**Doctrine candidate.**

This document deliberately evaluates both the case for and the case against drawing deterministic boundaries around probabilistic memory behavior. It is not intended to settle the subject permanently. The boundary should evolve as memory systems, uncertainty estimation, formal methods, and empirical evidence improve.

## Core question

A capable memory system must operate on incomplete, noisy, ambiguous, changing, and sometimes adversarial information.

That makes some degree of probabilistic behavior unavoidable or desirable.

At the same time, a governed memory system cannot allow uncertain model outputs to silently become durable authority, cross tenant boundaries, delete evidence, mutate canonical state, or rewrite history merely because a model assigned a high score.

The architectural question is therefore not:

> Should memory be deterministic or probabilistic?

The more useful question is:

> **Which parts of memory should reason under uncertainty, and which consequences must remain rule-bound, auditable, and reproducible?**

## Working thesis

The current doctrine adopts the following working thesis for evaluation:

> **Probabilistic discovery may produce beliefs, rankings, hypotheses, candidates, confidence estimates, and proposed actions. Consequential memory transitions must occur inside an explicit governance envelope whose permissions, prohibitions, state transitions, and audit consequences are deterministic or formally bounded.**

A shorter form is:

> **Probabilistic epistemics. Governed consequences.**

An even more operational form is:

> **Uncertainty may propose. Authority disposes.**

This is intentionally more precise than saying "probabilistic discovery must always have deterministic consequences." Some actions may safely remain stochastic inside a deterministic set of allowed outcomes. The invariant is that probabilistic machinery must not create its own authority.

---

## Why the binary is misleading

"Deterministic" can mean several different things:

1. **computational determinism** — identical inputs produce identical outputs
2. **policy determinacy** — the same policy facts produce the same authorization result
3. **transition determinacy** — a permitted state transition has a defined result
4. **replayability** — enough information is captured to reconstruct why a result occurred
5. **formal boundedness** — behavior may be stochastic, but it cannot escape a verified safe set

Likewise, "probabilistic" can describe different things:

1. uncertainty about whether a memory is true
2. uncertainty about whether a memory is relevant
3. stochastic retrieval or sampling
4. learned ranking
5. confidence calibration
6. probabilistic source trust
7. stochastic exploration among candidate actions
8. probabilistic estimates of future risk or value

Conflating these categories produces bad architecture quickly.

A model can be probabilistic while the policy controlling what it may mutate is deterministic. A policy can also be deterministic while consuming probabilistic estimates as inputs. A runtime may permit stochastic selection among several safe actions while deterministically prohibiting every unsafe action.

---

## The governed-uncertainty model

A useful abstraction is:

```text
uncertain observations
        |
        v
probabilistic / learned interpretation
        |
        |  beliefs, confidence, ranking,
        |  contradiction likelihood,
        |  candidate actions
        v
deterministic or formally bounded governance envelope
        |
        |  identity
        |  scope
        |  authority
        |  policy
        |  sensitivity
        |  lifecycle constraints
        |  permitted transition set
        v
optional learned / stochastic choice
AMONG PERMITTED ACTIONS ONLY
        |
        v
defined state transition
        |
        v
provenance + audit receipt
```

The architecture therefore separates **epistemic uncertainty** from **authority certainty**.

The system may be uncertain about what is true while remaining certain about what it is allowed to do with that uncertainty.

---

## Formal sketch

Let:

```text
s = current memory state
x = new observation or query
E = epistemic process
b = belief / score / distribution produced by E
P = versioned governance policy
A = authority and scope facts
G = governance function
S_allowed = set of allowed memory actions
π = optional learned or stochastic action selector
T = governed state transition function
r = audit receipt
```

Then:

```text
b = E(x, s)
S_allowed = G(s, b, P, A)
a ~ π(a | b, S_allowed)
s' = T(s, a)
r = audit(s, b, P, A, a, s')
```

Required invariant:

```text
a ∈ S_allowed
```

For operations that are irreversible, cross an authority boundary, or create canonical state, the policy may further require:

```text
|S_allowed| <= 1
```

or an explicit review/certification step before `T` can commit.

The probabilistic system may influence which action is proposed. It may not expand its own permitted action set.

---

## A four-zone boundary model

### Zone 1 — Deterministic substrate

These functions should usually be deterministic because ambiguity here creates identity, integrity, or audit failure.

Examples:

- content hashing and exact identity resolution
- schema validation
- tenant and actor scope resolution
- ACL and capability checks
- cryptographic signature verification
- provenance attachment requirements
- lifecycle transition validity
- immutable ledger append semantics
- version comparison
- tombstone interpretation
- canonical pointer resolution
- duplicate identity checks where exact identity is available

This does not mean the inputs are necessarily trustworthy. It means the mechanics of checking and recording them should not depend on model mood.

### Zone 2 — Probabilistic epistemics

These functions are naturally uncertain and often benefit from probabilistic or learned behavior.

Examples:

- semantic similarity
- relevance ranking
- anomaly detection
- source reliability estimation
- contradiction detection
- entity resolution when identity is incomplete
- clustering
- pattern discovery
- procedure induction
- abstraction and summarization
- confidence estimation
- causal hypothesis generation
- novelty detection
- predicted usefulness
- predicted staleness
- adaptive retrieval depth

These outputs should remain labeled as estimates or proposals.

### Zone 3 — Governed decision boundary

This is the critical interface.

A probabilistic output is mapped into an explicit governance result such as:

```text
allow
allow_ephemeral_only
allow_with_ledger
allow_inside_scope
require_verification
require_human_review
quarantine
dispute
archive
block
```

The result should be explainable from:

- policy version
- authority state
- input classifications
- confidence or risk estimates used
- thresholds or decision rules used
- required evidence state

The policy itself may evolve, but its application should be versioned and inspectable.

### Zone 4 — Governed commit

Once an action crosses into durable state, the system should enforce defined consequences.

Examples:

- create a memory unit with required provenance
- transition `candidate -> pending_verification`
- mark a memory disputed instead of overwriting it
- promote only after certification
- create a tombstone when deletion is required
- archive rather than destroy evidence when policy requires preservation
- deny a cross-tenant retrieval
- reject mutation when authority is insufficient
- propagate deletion into declared derived artifacts

This is where "best effort" becomes dangerous.

---

## Operation-by-operation boundary map

| Memory operation | Probabilistic / learned behavior may be useful for | Deterministic or bounded behavior should govern |
|---|---|---|
| Observe | perception confidence, extraction | source identity, timestamping, raw evidence preservation |
| Propose memory | salience, novelty, classification | candidate schema, acquisition mode, required provenance |
| Admit | usefulness and confidence estimates | scope, sensitivity restrictions, authority, permitted storage class |
| Retrieve | semantic ranking, query expansion, adaptive depth | tenant filters, policy filters, prohibited memory exclusion |
| Consolidate | clustering, summarization, abstraction | provenance links, source retention, replacement authority |
| Reinforce | predicted utility, evidence weighting | what signals are permitted to affect saturation |
| Revise | contradiction detection, proposed correction | mutation authority, history preservation, no silent overwrite |
| Crystallize | candidate scoring | certification prerequisites and canonical transition |
| Forget | decay estimation, predicted future utility | deletion authority, legal/policy holds, tombstone semantics |
| Share | relevance and recipient usefulness | ACL, consent, tenant, sensitivity, destination scope |
| Inherit | selecting useful seed memories | acquisition mode, provenance, inherited-vs-observed distinction |
| Execute procedure | choosing among known procedures | tool permissions, policy constraints, destructive-action gates |

---

## The strongest deterministic boundaries

Not every memory mutation carries the same risk.

The strongest deterministic or formally verified boundaries should surround transitions that can:

1. create canonical or certified truth
2. erase or make evidence unrecoverable
3. cross tenant, user, organization, or trust-domain boundaries
4. change authority or policy
5. transform inferred state into authoritative state
6. expose sensitive memory
7. create durable behavioral control over future agents
8. propagate into successor or inherited memory
9. trigger external side effects
10. weaken future governance

These transitions should never occur solely because:

```text
model_confidence > threshold
```

without a policy that explicitly authorizes the transition and defines the other required conditions.

---

## Deterministic does not mean "one fixed threshold forever"

A naive deterministic design often looks like:

```text
if score >= 0.80:
    store_forever()
else:
    discard()
```

That is deterministic. It is also frequently terrible.

Thresholds may be:

- poorly calibrated
- domain dependent
- source dependent
- risk dependent
- time dependent
- vulnerable to adversarial optimization
- brittle near the boundary

A stronger pattern is:

```text
estimate uncertainty
estimate risk
classify scope
classify source
apply versioned policy
choose from permitted outcomes
record the decision basis
```

The governance result can remain deterministic even when several inputs are probabilistic.

---

## Probabilistic actions can exist inside deterministic envelopes

The doctrine should not prohibit stochastic behavior merely because it is stochastic.

Examples that may safely remain probabilistic:

- selecting which of several equally authorized memories to inspect first
- exploring alternative retrieval queries
- choosing among several non-destructive candidate plans
- sampling memories for offline consolidation analysis
- selecting among equally permissible compression strategies
- choosing which low-risk hypothesis to test next

The key condition is:

```text
stochastic choice cannot escape the allowed set
```

This is similar to runtime assurance and shielding approaches in learning-enabled systems: a learned or unverified controller can optimize behavior while a separate mechanism constrains the action space to acceptable behavior.

---

## Why memory itself argues for probabilistic epistemics

Human and biological memory do not behave like exact database recall.

Research on human decision making has modeled retrieval as selective and stochastic, with noisy evidence accumulated until a decision boundary is reached. Other work suggests working memory carries trial-level uncertainty information that humans incorporate into later decisions.

These findings do **not** prove that agent memory should copy neural mechanisms.

They do support two weaker conclusions:

1. useful memory systems may need to represent uncertainty rather than collapsing every memory into a binary true/false state
2. retrieval itself may introduce uncertainty and should not be treated as an infallible read operation

For agent systems, that supports fields such as:

```text
confidence
uncertainty
source_trust
contradiction_pressure
retrieval_score
scope_confidence
freshness_confidence
```

while keeping those fields separate from authority.

---

## Evidence supporting the governed-boundary view

### Memory retrieval is noisy and selective

Giguère and Love model human decisions as stochastic selective retrieval followed by evidence accumulation. They also show that limited selective retrieval can produce suboptimal decisions even when the underlying memory is complete.

Engineering implication:

> Retrieval quality should not be confused with memory truth, and repeated stochastic retrieval should not silently alter authority.

Open access:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC3651451/

### Working memory can represent uncertainty

Honig et al. report that people incorporate trial-level working-memory uncertainty into later rewarded decisions and combine that uncertainty with prior information.

Engineering implication:

> Memory representations can profitably preserve uncertainty rather than emitting only point estimates.

Open access:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC7165478/

### Different forms of uncertainty matter differently

Research distinguishes prior uncertainty, likelihood uncertainty, unexpected uncertainty, risk, and ambiguity rather than treating uncertainty as one scalar.

Engineering implication:

> A single `confidence` field may be too crude for mature memory governance.

Open access examples:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC3461114/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC4885745/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3166851/

### Learned memory control can outperform fixed heuristics

Recent agent-memory systems increasingly learn when to retrieve, consolidate, forget, or choose among memory structures rather than hard-coding every decision.

MemCon models memory operations as a controlled decision process and learns adaptive behavior. FluxMem uses an adaptive probabilistic gate for memory fusion rather than brittle fixed similarity rules.

Engineering implication:

> The architecture should permit probabilistic control where it improves utility, provided it cannot bypass governance.

Freely available preprints:

- https://arxiv.org/abs/2607.13591
- https://arxiv.org/abs/2602.14038

### Runtime assurance provides an adjacent architectural precedent

Simplex-style architectures separate a high-performance learned controller from a separately enforced safety mechanism. Related shielding work constrains the action space even when learned policies or hidden system parameters remain uncertain.

Engineering implication:

> Unverified or probabilistic optimization can coexist with stronger guarantees when authority is separated from optimization.

Freely available preprints:

- https://arxiv.org/abs/2109.13446
- https://arxiv.org/abs/2102.12981
- https://arxiv.org/abs/2506.11033

### Memory governance is becoming a first-class research problem

Recent work on governed evolving memory explicitly separates memory evolution from execution and introduces verification, temporal decay, and access control around consolidation.

Freely available preprint:

- https://arxiv.org/abs/2603.11768

---

## Evidence challenging naive deterministic governance

The same evidence base warns against treating deterministic policy as equivalent to safe policy.

### Static rules can be brittle

Recent memory-poisoning studies show that static write-time defenses may suppress direct attacks while failing on compositional or context-triggered attacks that appear benign until several memories are retrieved together.

Engineering implication:

> Governance cannot be only a static pre-write filter. Read-time, context-sensitive, and adaptive defenses are required.

Freely available preprints:

- https://arxiv.org/abs/2606.04329
- https://arxiv.org/abs/2607.14651

### Thresholds require calibration

Memory-poisoning defense work reports a tradeoff between overly conservative trust thresholds that reject too much legitimate memory and permissive thresholds that miss subtle attacks.

Engineering implication:

> Deterministic thresholds must be calibrated, risk-aware, and versioned. A deterministic mistake is still a mistake, merely with excellent reproducibility.

Freely available preprint:

- https://arxiv.org/abs/2601.05504

### Adaptive defenses may be necessary

Context-sensitive attacks can arise from combinations of individually acceptable memories.

Engineering implication:

> A safe architecture may require probabilistic or learned risk estimation on both write and read paths. The deterministic part is the authority boundary applied to those estimates, not necessarily the risk detector itself.

### Formal guarantees may themselves be probabilistic

Some runtime shielding methods provide probabilistic safety guarantees rather than absolute ones because the environment contains hidden parameters or uncertain models.

Engineering implication:

> The doctrine should accept formally bounded probabilistic guarantees where absolute determinism is impossible, while making the guarantee type explicit.

---

## Research synthesis

The evidence does not support either extreme:

```text
EXTREME A
Everything important should be deterministic.

EXTREME B
A sufficiently capable model should decide memory behavior end to end.
```

A stronger synthesis is:

```text
probabilistic perception
probabilistic discovery
probabilistic ranking
probabilistic hypothesis generation
probabilistic risk estimation
          |
          v
explicit deterministic / formally bounded authority envelope
          |
          v
optional stochastic optimization within allowed actions
          |
          v
defined state transition + audit
```

This separation preserves adaptation without outsourcing authority to uncertainty.

---

## Consequence classes

The required governance strength should scale with consequence.

### Class 0 — Ephemeral inference

Examples:

- ranking candidates
- query expansion
- temporary association

Default posture:

```text
probabilistic allowed
no durable mutation
minimal audit requirement
```

### Class 1 — Reversible operational memory

Examples:

- session cache
- provisional note
- temporary summary

Default posture:

```text
probabilistic proposal allowed
policy admission required
rollback available
```

### Class 2 — Durable but revisable memory

Examples:

- long-term preference
- procedure
- semantic fact

Default posture:

```text
probabilistic proposal allowed
explicit authority + provenance required
mutation history required
```

### Class 3 — Canonical / shared / sensitive memory

Examples:

- organizational policy memory
- cross-agent shared facts
- security-sensitive records
- certified memory

Default posture:

```text
strong deterministic policy boundary
verification or certification as required
scope enforcement
complete audit receipt
```

### Class 4 — Irreversible or authority-changing transition

Examples:

- cryptographic erasure
- permission expansion
- deletion of required evidence
- policy mutation
- inherited canonical seed update

Default posture:

```text
fail closed
explicit authority
strong prerequisites
no direct model-only authorization
human or external certification where risk requires
```

---

## Handling randomness itself

Randomness is not inherently incompatible with governance.

### Cryptographic randomness

Security systems intentionally depend on high-quality randomness.

This is not a violation of deterministic governance. The governance rule determines when keys, nonces, salts, or tokens must be generated and how they may be used. Their values should not be deterministic.

### Exploration randomness

Agents may use randomness to avoid local optima or diversify retrieval.

For consequential operations, record enough information to explain or replay the decision when practical:

- model/version
- policy version
- candidate set
- probability distribution or scores
- selected action
- random seed when appropriate and safe

Not every system requires bit-for-bit replay, but every consequential transition should remain causally inspectable.

---

## Concurrency and distributed memory

Distributed systems introduce nondeterminism even without machine learning.

Two agents may observe or update related memory concurrently.

The goal should therefore not be universal bit-for-bit determinism.

The stronger requirement is:

> **Conflicting concurrent events must resolve through explicit, versioned transition semantics rather than silent last-writer-wins mutation.**

Possible deterministic outcomes include:

```text
reject stale version
create conflict state
merge under declared rule
preserve both scoped claims
require reconciliation
serialize through authority owner
```

"Whichever write arrived last" is an ordering fact, not a theory of truth.

---

## The deterministic-consequence rule

A useful doctrine rule is:

> **Every probabilistic memory operation that can cause a consequential state transition must terminate in one of a finite set of policy-defined outcomes.**

For example:

```text
probabilistic contradiction detector
        |
        +--> no material conflict
        +--> mark for review
        +--> enter disputed state
        +--> quarantine from canonical recall

NOT
        +--> silently overwrite the old memory
```

Likewise:

```text
probabilistic sensitivity classifier
        |
        +--> public
        +--> internal
        +--> restricted
        +--> uncertain -> require stronger handling

NOT
        +--> unknown -> assume public
```

Uncertainty itself should be a valid policy input.

---

## Fail-safe handling of uncertainty

A mature governance system should distinguish:

```text
known safe
known unsafe
uncertain
insufficient evidence
policy not applicable
policy conflict
```

Do not coerce all uncertainty into yes/no before the governance layer sees it.

For high-risk operations:

```text
uncertain != allow
```

For low-risk operations:

```text
uncertain may permit reversible exploration
```

This makes risk proportionality explicit.

---

## Calibration requirements

Any probabilistic component that influences governance should expose calibration evidence appropriate to its use.

Possible measures include:

- expected calibration error
- Brier score
- precision/recall at operational thresholds
- false admission rate
- false rejection rate
- uncertainty quality under distribution shift
- adversarial robustness
- abstention quality
- performance by memory class and source class

Thresholds should be versioned with:

```yaml
policy_id: ...
policy_version: ...
estimator_id: ...
estimator_version: ...
threshold: ...
risk_class: ...
calibration_dataset: ...
calibrated_at: ...
known_limitations: ...
```

---

## Required audit receipt

For a consequential transition influenced by probabilistic reasoning, the audit record should capture at least:

```yaml
memory_id: ...
prior_state: ...
proposed_action: ...
committed_action: ...
policy_id: ...
policy_version: ...
authority_scope: ...
source_refs: [...]
estimator_refs: [...]
probabilistic_signals:
  confidence: ...
  risk: ...
  relevance: ...
  contradiction: ...
thresholds_or_rules: [...]
review_or_certification: ...
resulting_state: ...
timestamp: ...
```

The purpose is not bureaucracy for its own sake. It is to keep uncertainty from becoming invisible after the state transition has happened.

---

## Conformance tests

An implementation aligned with this doctrine should be tested against at least the following cases.

### Probabilistic high-confidence error

A model assigns very high confidence to a false memory.

Expected:

```text
confidence alone cannot grant canonical promotion
```

### Boundary jitter

The same candidate falls slightly above and below a learned threshold across runs.

Expected:

```text
authority and scope invariants remain stable
transition behavior is policy-defined
```

### Cross-tenant high relevance

A private memory from tenant A is semantically perfect for tenant B's query.

Expected:

```text
retrieval denied deterministically by scope
```

### Poisoned multi-memory composition

Individually benign memories become malicious when retrieved together.

Expected:

```text
read-path risk detection can quarantine or constrain assembly
```

### Uncertain sensitivity

The classifier cannot confidently determine whether a candidate is sensitive.

Expected:

```text
high-risk durable or shared storage does not default to permissive behavior
```

### Probabilistic contradiction

A detector flags likely conflict with certified memory.

Expected:

```text
existing memory is not silently overwritten
candidate enters a governed dispute / verification path
```

### Stochastic retrieval

Repeated retrieval returns different candidate ordering.

Expected:

```text
all returned memories still satisfy deterministic scope and policy constraints
```

### Concurrent mutation

Two authorized agents produce conflicting updates.

Expected:

```text
explicit conflict/version semantics; no silent last-writer truth assignment
```

### Irreversible deletion

A model predicts a memory has no future utility.

Expected:

```text
utility prediction cannot itself authorize irreversible deletion
```

### Policy revision

The same memory is evaluated under two policy versions.

Expected:

```text
different outcomes are attributable to explicit policy change, not hidden drift
```

---

## Questions that remain open

This doctrine intentionally leaves several questions unresolved.

1. Which governance decisions require strict computational determinism versus only deterministic policy semantics?
2. When is a probabilistic safety guarantee sufficient for memory mutation?
3. Should low-risk lifecycle decay ever be stochastic by design?
4. How should uncertainty propagate through consolidation and derived memories?
5. How much replayability is required when the underlying model is nondeterministic?
6. Should model confidence influence authority at all, or only verification priority?
7. How should governance respond when calibrated models disagree?
8. Can learned policy components themselves be certified within bounded scopes?
9. How should thresholds adapt under distribution shift without creating silent policy mutation?
10. Which memory transitions require external or human certification regardless of model quality?
11. How should deterministic governance behave when policy inputs themselves are uncertain or contradictory?
12. What is the right formalism for proving that stochastic action selection cannot escape the permitted action set?

These questions are research targets, not embarrassing gaps to hide behind confident prose.

---

## Proposed doctrine invariants

The following should be tested for adoption across Agent Memory:

1. **Uncertainty is data. Do not collapse it prematurely.**
2. **Probabilistic outputs are evidence or proposals, not authority.**
3. **A learned component may not expand its own mutation authority.**
4. **Consequential transitions must terminate in policy-defined outcomes.**
5. **Scope, tenancy, identity, and explicit authority constraints must survive stochastic behavior.**
6. **Irreversible transitions require stronger deterministic prerequisites than reversible ones.**
7. **Static deterministic rules must be calibrated and adversarially tested.**
8. **Read-time governance is required because safe individual memories can compose unsafely.**
9. **Stochastic optimization is acceptable inside a governed action envelope.**
10. **Policy and estimator versions must be distinguishable in audit evidence.**
11. **A deterministic error is not inherently safer than a probabilistic one.**
12. **The architecture should optimize for governed uncertainty, not fake certainty.**

---

## Research-use policy

The repo should prefer research material that can be legally and freely inspected by contributors and agents whenever practical.

Preferred sources:

```text
open-access journal articles
PubMed Central full text
arXiv and other lawful preprints
open conference papers
university / author-hosted manuscripts
public standards and technical reports
open datasets and benchmark repositories
```

The purpose is not to accumulate citations as decoration.

The purpose is to learn from available evidence, record which ideas influenced doctrine, distinguish evidence from analogy, and keep the architecture challengeable by future research.

When a source is paywalled, proprietary, or unavailable for inspection, the doctrine should avoid depending on claims that cannot be independently evaluated by contributors.

---

## Related documents

- `03-scoring-and-decay.md`
- `04-governance-and-pama.md`
- `06-conformance-test-plan.md`
- `09-calibration-protocol.md`
- `15-memory-threat-model.md` (planned)
- `17-conflict-resolution-engine.md` (planned)
- `20-memory-foundations-across-scales.md`
- `21-forgetting-consolidation-and-memory-metabolism.md`
- `22-agentic-memory-theory-and-development.md`
- `23-research-bibliography.md`
- `adr/ADR-020-probabilistic-discovery-deterministic-governance.md`
