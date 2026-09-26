# Runtime Identity and Naming Brief

**Status:** Exploratory design brief under #554  
**Decision status:** No runtime product name is selected by this document.  
**Related:** Agent Memory Gauntlet, future runtime licensing/product-boundary review

## 1. Why the runtime needs its own identity

`Agent Memory` has become broader than one runtime implementation.

The repository now acts as a commons containing:

```text
Agent Memory
├── architecture / doctrine / research
├── Memory Evaluation
├── Agent Memory Gauntlet
└── one reference/product runtime implementation
```

That makes the current package identity, `agent-memory-reference`, increasingly poor as a product name.

The generic Agent Memory name is valuable for the open research/evaluation commons precisely because it is descriptive and non-proprietary in tone.

The runtime may eventually need a distinct identity because it is the layer most likely to carry:

- commercial differentiation;
- a stricter or source-available licensing boundary;
- product support commitments;
- release/version promises;
- deployment profiles;
- proprietary hardening or integrations;
- trademarks/product identity distinct from the open benchmark/research commons.

This document does **not** make that licensing decision. It records the naming logic so licensing and identity can be decided deliberately later.

## 2. The naming insight from the Gauntlet

A useful product metaphor emerged from benchmark-driven development:

> **The runtime is the memory implementation that survives the Gauntlet.**

This has two parallel meanings.

### Runtime level

A credible memory runtime survives pressure from:

- retrieval benchmarks;
- temporal/currentness benchmarks;
- conflict/correction cases;
- governance attacks;
- deletion/forgetting tests;
- restart/recovery;
- concurrency;
- scale;
- evaluator integrity;
- future benchmarks it was not designed to game.

### Memory level

A retained memory earns durable influence by surviving appropriate scrutiny:

- contradiction;
- provenance review;
- time;
- correction;
- reinforcement or lack of it;
- lifecycle transitions;
- scope/purpose governance;
- retrieval applicability.

This does **not** mean:

```text
survived benchmark == true
survived benchmark == authorized
survived Gauntlet == infallible
```

It means the implementation has earned a stronger evidence posture by surviving independent pressure.

## 3. Naming criteria

A final runtime name should ideally satisfy these criteria.

### Meaning

It should evoke one or more of:

- endurance;
- persistence;
- survival under scrutiny;
- proving/testing;
- tempering/hardening;
- retained signal after noise/pressure;
- durable evidence;
- reliable recall.

### Tone

It should sound credible as infrastructure:

```text
<name> Runtime
<name> Memory
<name> SDK
<name> Server
<name> Core
```

It should not sound like a consumer journaling app, fantasy game item, or benchmark score.

### Semantic restraint

Avoid names that imply:

- absolute truth;
- perfect memory;
- certified security;
- omniscience;
- authority merely because the runtime retained something.

### Product separation

The name should be clearly distinguishable from:

- Agent Memory, the broader commons/repository;
- Agent Memory Gauntlet, the qualification product;
- Qortara/TARA/CoreForge and other MythologIQ products unless intentional family branding is chosen.

### Namespace practicality

Before lock:

- web/product collision search;
- GitHub organization/repository search;
- Python/PyPI name search;
- npm/package search if relevant;
- domain search;
- trademark review appropriate to intended commercial use.

A web search is not legal trademark clearance.

## 4. Naming metaphor families

### A. Tempering / hardening

Concept: the runtime becomes stronger by repeated controlled stress.

This is an excellent conceptual fit with the Gauntlet.

However, obvious terms are crowded. `Tempered` is already used by an AI/software venture studio, and `Anvil` is heavily occupied by current AI products including memory-related systems. Those should not be treated as clean candidates.

Useful language from this family may still inform taglines and architecture prose:

```text
tempered by evidence
forged under pressure
hardened by adversarial evaluation
```

### B. Proving / proof testing

Concept: historical proof houses tested barrels/components above ordinary operating pressure; a proof mark meant the item survived a prescribed test.

This metaphor maps exceptionally well to the Gauntlet philosophy.

Unfortunately `Proofmark` is already crowded across active software products, including knowledge/provenance products, so it is unsuitable as a clean runtime brand.

The broader language remains useful:

```text
proof-tested memory
proven under pressure
qualification evidence
```

Care is required because `proven` can overstate what benchmark survival establishes.

### C. Survival / endurance

Concept: what remains after repeated pressure.

Obvious forms such as `Endurant`, `Steadfast`, `Survivance`, and similar words already have active software/company usage or broad collision risk.

This family is semantically strong but likely requires a coined term rather than an ordinary English word.

### D. Remanence / persistence

`remanence` is a physical term for what remains after an external field is removed, making it an elegant memory metaphor.

It is nevertheless already used by active technical/software/publication projects and is not a clean candidate without deeper review.

The concept remains useful:

> what remains after the forcing function is gone

That is close to durable agent memory.

### E. Mythological memory-survivor

A MythologIQ product could use a mythological figure associated with memory, endurance, survival, counsel, or preservation.

This has brand-family advantages but significant namespace collision risk. Obvious memory figures such as Mnemosyne/Mimir/Muninn are widely used in technology already.

If this direction is pursued, prefer a less saturated figure/concept and verify that the mythology actually matches the product rather than merely sounding Nordic or Greek.

### F. Coined infrastructure name

The strongest practical path may be a coined name whose **etymology** encodes endurance/proving/memory while avoiding crowded literal terms.

Criteria for a coined name:

- pronounceable on first sight;
- spellable after hearing it;
- package-friendly lowercase form;
- not confused with medical/pharmaceutical products;
- not an accidental slur/negative word in major languages where practical;
- no claim of truth/certification embedded in the word;
- capable of being owned as a runtime brand.

## 5. Working descriptors, not brand candidates

Until a name is selected, use descriptors that communicate the architecture without pretending they are trademarks.

Preferred working descriptor:

> **Gauntlet-proven memory runtime**

Alternative technical descriptors:

- Gauntlet-qualified memory runtime;
- benchmark-hardened memory runtime;
- evidence-tempered memory runtime;
- governed durable memory runtime.

`Gauntlet-proven` must be used carefully in public claims. A specific release can only be described as having survived the profiles actually run, with evidence linked.

## 6. Candidate naming directions for a later naming sprint

Rather than lock obvious crowded names now, a later naming sprint should generate candidates from these roots/concepts.

### Root set: endurance

```text
dur-
fort-
stead-
remain-
rem-
perdur-
resil-
```

### Root set: proof/testing

```text
prove-
trial-
assay-
proof-
qual-
cert-     # caution: may imply certification
```

### Root set: memory/retention

```text
mneme-
memo-
retent-
engram-
recall-
trace-
```

### Root set: forging/tempering

```text
forge-
temper-
quench-
anneal-
harden-
```

The sprint should favor combinations or coined forms that survive namespace checks rather than selecting the prettiest dictionary word first.

## 7. Product architecture implication

A future product structure could become:

```text
Agent Memory                           permissive/open commons
├── architecture & research           open
├── Memory Evaluation                 open
├── Agent Memory Gauntlet             open
├── schemas / adapter contracts       open
└── reference/baseline implementations open where useful

<Distinct Runtime Brand>               separately governed product runtime
├── core runtime
├── production hardening
├── enterprise integrations
├── support/release channel
└── licensing/commercial terms
```

This is an architectural/licensing option, not a decision in this brief.

A key advantage is credibility: the Gauntlet remains useful to competitors and the community rather than becoming a proprietary benchmark whose main purpose is to sell the runtime.

## 8. Licensing terminology guardrail

If the future runtime license restricts commercial use, redistribution, competition, fields of use, or similar rights beyond an OSI-approved license, describe it accurately as **source-available** or under its specific license, not as open source.

The Agent Memory commons can remain genuinely open even if a separately branded runtime adopts a different licensing model.

Exact license design should receive legal review before changing public distribution terms.

## 9. Runtime release claim discipline

A runtime release should not inherit a vague claim such as:

```text
passes the Gauntlet
```

Instead publish a qualification manifest:

```text
runtime: <name> 1.0.0
Gauntlet revision: ...
profiles executed:
  core-retrieval/...       PASS / measured evidence
  temporal/...             PASS / limitations
  governance-isolation/... PASS
  operations/...           PASS / serialized concurrency
profiles not run:
  multimodal/...
known limitations:
  ...
```

The brand can embody survival under scrutiny while the evidence remains specific.

## 10. Decision checkpoint

Do not rename the package or repository until:

1. the Agent Memory commons/product boundary is accepted;
2. runtime licensing goals are decided;
3. the initial Gauntlet external-system product boundary exists;
4. at least 10-20 coined/semantic candidates receive collision checks;
5. a short list receives legal/trademark review appropriate to commercialization;
6. package/repository migration cost is understood;
7. the selected name works both technically and commercially.

## 11. Governing naming principle

> **Name the runtime for what survives scrutiny, not for what merely gets stored.**
