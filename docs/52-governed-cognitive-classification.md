# Governed Cognitive Classification

## Status

Implemented reference contract for issues #490 and #500.

This profile defines how deterministic, heuristic, model-backed, or hosted classification providers may contribute observations and recommendations without becoming Agent Memory authority.

```text
provider output != truth
provider confidence != permission
provider identity != authority
ranking != recall admission
recommendation != mutation authority
```

No new ADR is introduced. The existing component/capability contract from #274/#280 already represents provider identity, maturity, failure posture, behavior, and deterministic provider eligibility. Cognitive classification therefore reuses `ComponentRegistry` and adds a narrow Agent Memory-owned request/result contract above it.

## Runtime shape

```text
bounded memory evidence
    -> ComponentRegistry resolves cognitive_classification capability
    -> provider emits typed observation / recommendation
    -> Agent Memory normalizes provider evidence
    -> deterministic scope / currentness / exact-metadata checks
    -> downstream recall admission, lifecycle, policy, or PAMA logic
    -> consequence or refusal
```

The classifier runtime has no commit, delete, recall-admit, or PAMA-authorize method.

## Contract

`ClassificationRequest` binds:

- request and task identity;
- bounded input data;
- explicit output-label contract;
- scope, tenant, and purpose;
- candidate scope when relevant;
- source-currentness state;
- exact deterministic label when one already exists;
- evidence refs and policy/context refs;
- deterministic input digest.

`ProviderMetadata` binds:

- provider identity and version;
- provider class (`deterministic`, `ordinary_llm`, `specialized_model`, or bounded external provider);
- model/runtime ref;
- configuration ref;
- local/offline posture;
- data-egress posture.

`ClassificationResult` retains provider choices plus:

- provider label and effective label separately;
- exact-metadata override state;
- deterministic gate reasons;
- consequence eligibility;
- abstention, unavailability, malformed-output, or refusal state;
- latency/cost evidence where supplied;
- trace ref;
- result digest;
- `authority_effect: none`.

The result is evidence. A downstream operation must still satisfy the relevant deterministic admission, lifecycle, currentness, sensitivity, scope, or PAMA rules.

## Existing classification inventory

The inventory below answers #490's deterministic-versus-probabilistic question. It is intentionally about the decision boundary, not whether probabilistic evidence can be useful upstream.

| Surface | Provider use | Deterministic boundary |
|---|---|---|
| actor / tenant / scope | no probabilistic authority | exact configured/request scope controls visibility and consequence eligibility |
| consent / explicit sensitivity metadata | inferred signals may supplement | explicit metadata and policy constraints control handling |
| currentness / supersession / tombstone state | probabilistic discovery may flag anomalies | canonical version/currentness relation controls eligibility |
| PAMA mutation permission | provider may recommend action class | PAMA/policy decision controls permitted operation set |
| canonical structural mutation class | provider may propose structure | deterministic structural classification and authorization remain controlling |
| deletion hold / protected-memory state | provider may recommend prune | hold/protection/deletion authority controls consequence |
| memory semantic class | probabilistic classification allowed | exact type metadata overrides conflicting inference where present |
| salience / relevance | probabilistic or heuristic | may affect ordering/proposal only, never admission authority |
| contradiction likelihood | probabilistic or heuristic | exact conflict/currentness evidence overrides inference where available |
| relationship classification | probabilistic or heuristic | scope/currentness/provenance remain deterministic gates |
| recurrence / novelty | probabilistic or heuristic | recurrence confidence does not create block or mutation authority |
| consolidation / retention recommendation | probabilistic or heuristic | lifecycle/PAMA/deletion rules control durable consequence |
| recall candidate ranking | probabilistic or heuristic | governed final admission remains separate |

In short, some classifications may be probabilistic while their consequences remain deterministic.

## Abstention, failure, disagreement, and fallback

Providers return explicit states. `ok`, `abstained`, `unavailable`, and malformed output are not interchangeable.

Abstention is terminal by default. A fallback after abstention requires an explicit caller choice. Unavailability or malformed output may use an explicitly configured fallback, but every fallback still resolves through the same component capability and minimum-maturity requirement.

Provider disagreement is represented as disagreement. The runtime does not average labels, probabilities, or confidence into a synthetic authority signal.

```text
two providers disagree
    -> preserve both observations
    -> disagreement = true
    -> aggregation = none
```

## Exact metadata and negative paths

Exact deterministic metadata wins where doctrine requires it. The provider observation remains visible for audit, but the effective label follows the exact value and records `provider_conflicts_exact_metadata`.

Cross-scope and stale-source inputs are refused as consequence-eligible even when a provider returns a high-confidence label. This prevents relevance or confidence from laundering state across scope/currentness boundaries.

Malformed provider labels are normalized to `malformed` and fail closed. Provider exceptions become `unavailable` evidence rather than permissive success.

## Credential-free three-provider evaluation

`reference/run_cognitive_classification_evaluation.py` evaluates three materially different provider classes behind the same contract:

1. deterministic/rule baseline;
2. ordinary-LLM replay;
3. specialized-model replay.

The two model-backed rows are frozen simulations, not live provider measurements. The fixture is explicitly `simulation_only: true`. Their latency, cost, and locality fields are fixture evidence used to prove contract/reporting behavior, not claims about an actual vendor or model.

The evaluator reports separately:

- provider-label accuracy;
- effective-label accuracy after deterministic overrides;
- top-choice calibration/Brier value when probability exists;
- abstention, unavailable, malformed, and refusal counts;
- critical false positives and false negatives;
- latency;
- cost;
- locality/data egress;
- frozen-fixture reproducibility;
- governance refusal and authority-effect evidence;
- provider disagreement.

There is no aggregate health score.

Live provider qualification is tracked separately by #495. That work must bind real provider/model/config versions and real measurements before any performance preference is claimed.

## Privacy and egress

Provider locality and data-egress posture are explicit metadata. A hosted provider does not become eligible for protected data simply because it implements the classification capability. Runtime configuration and downstream privacy/sensitivity controls remain controlling.

Local/offline operation remains supported by the deterministic provider class even when no hosted provider is configured. Optional model-backed classifications may therefore become unavailable or lower fidelity without making Agent Memory itself inoperable.

## Reproducibility and drift

Every request has an input digest. Every result binds provider identity/version, model/runtime ref, configuration ref, evidence refs, and a result digest.

A provider version or configuration change creates a different evidence identity. Historical results are not silently rewritten. A future live benchmark must compare exact versions and report drift rather than treating provider upgrades as equivalent runs.

## ADR promotion disposition

No new ADR is warranted by this implementation.

The experiment establishes that the existing component/capability architecture cleanly represents classification providers, while the narrow request/result envelope is an implementation/profile contract. No new canonical authority primitive or second registry is required.

If future implementations expose a representation-neutral invariant that cannot be expressed by the current component, estimator, lifecycle, or PAMA doctrine, that evidence can independently trigger the #490 ADR promotion gate.
