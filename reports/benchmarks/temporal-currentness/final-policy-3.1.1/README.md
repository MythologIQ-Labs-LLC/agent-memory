# Final temporal/currentness replay — policy 3.1.1

Issue: #580  
Evidence class: repository-owned conformance / falsification  
ADR-039: **PROPOSED**

## Disposition

The final frozen `temporal-currentness-gauntlet-v1` replay accepts the current temporal/currentness boundary for #580 after #585, #598, and redesigned #583.

This is not independent external validation and does not accept ADR-039.

The replay ran against:

```text
ranking policy: 3.1.1
temporal interpreter: 1.1.0
fixture SHA-256: 394be82e8dfabe30ad1faf064f36a88d0b0b8e7ab8157f746ecb4cbae9e64492
cases: 26
probes: 50
assertions: 211
```

Workflow run `37149865903` completed successfully. Artifact `11283382238` has SHA-256 `e68c4ac382bb26f0b3c3d4943f4deeaaa8a5aae11a74475cd183630380d5104a`.

The committed `accepted-evidence.json` preserves the decision metrics, failure-class disposition, and SHA-256 identity of every raw JSON file in that artifact.

## Required-level outcome

After accounting for the accepted #585 interpreter-version transition, the replay exposes **no new required temporal/currentness correctness regression**.

Required guarantees remain intact:

- current applicability accuracy: `1.0`;
- stale-as-current rate: `0.0`;
- current-demoted-as-stale rate: `0.0`;
- as-of state accuracy: `1.0`;
- historical-state admission accuracy: `1.0`;
- prospective applicability accuracy: `1.0`;
- unknown-temporal-basis honesty: `1.0`;
- clock-source accuracy: `1.0`;
- atemporal relevance preservation: `1.0`;
- coexistence preservation: `1.0`;
- state-change vs error-correction accuracy: `1.0`;
- metabolism/validity separation: `1.0`;
- authority/scope violations: `0`;
- temporal self-claim rank influence: `0`;
- cross-process ordering reproduction: `50/50`.

## Frozen-gold interpreter mismatch

The raw frozen-v1 metric reports required intent interpretation accuracy `0.8571` because case A1 still expects the old posture:

```text
current language -> inferred current intent
```

Accepted #585 deliberately changed unambiguous `current`, `now`, and equivalent temporal query language to:

```text
current language -> explicit query_language_explicit intent
```

The observed A1 result is therefore the accepted interpreter 1.1.0 behavior, not a regression. A1's actual applicability, ordering, clock, and stale/current assertions all pass.

The same version transition explains the two target-level `plain-now` intent mismatches. The frozen v1 corpus remains unchanged so the historical expectation is not rewritten after observing the newer runtime.

## F30 disposition

F30 is fixed at required level by redesigned #583:

```text
temporal_self_claim_rank_influence_count = 0
```

Neutralizing the adversarial candidate's temporal/currentness self-claim wording no longer changes the required ordering. Authority, mutation, and declared-basis protections remain intact.

This is the behavior the rejected global lexical-cue-removal PR #587 failed to achieve safely on LongMemEval_S.

## Remaining target-level limitations

Two substantive target-level families remain outside the final #580 correctness boundary.

### Proposition identity / cardinality

Nineteen units remain `fail` or `honest_unknown` because natural write-time semantic recognition does not yet provide enough proposition/cardinality evidence for all desired state-change/prospective cases.

This remains owned by #596/#597. It is not converted into a temporal ranking rule.

### Exception precedence

Two F26 units remain `honest_unknown` because bounded temporal exception precedence is not modeled.

This remains owned by #586 and is not pulled into RC solely to make the target column green.

## #584 pressure exposed by the replay

The replay supplies the evidence used for the subsequent #584 policy ruling.

### Unknown vs unknown

A4 shows two equal-relevance `unknown_temporal_basis` candidates ordered by transaction time. That is deterministic, but transaction recency is not currentness evidence.

The #584 ruling therefore removes transaction/observation-time currentness preference between unknown-basis candidates. Route-native/non-temporal evidence remains controlling, followed by the existing neutral deterministic digest for true residual ties.

### Applicable vs unknown

D18 shows why a global `applicable > unknown` tier is invalid. A highly relevant build-cache fact with unknown temporal basis correctly ranks above affirmatively applicable on-call facts about a different proposition.

The #584 ruling therefore permits affirmed-over-unknown dominance only inside a typed exclusive same-slot competition. It does not grant temporal certainty global relevance authority.

## Next boundary

#580 is complete once this evidence package lands on `main` against the accepted #583 runtime boundary.

The next temporal-policy work is #584:

1. freeze the M1-M13 follow-on adversarial contract without editing the frozen v1 suite;
2. implement the pairwise exclusive-slot constraint and time-neutral unknown fallback only against that frozen contract;
3. version ranking policy `3.1.1 -> 3.1.2` if behavior changes;
4. replay #580 v1, the #584 follow-on fixture, AgentMemBench, and LongMemEval_S;
5. run LongMemEval_M only if the established S escalation trigger fires.

ADR-039 remains **PROPOSED** throughout unless separately ruled.
