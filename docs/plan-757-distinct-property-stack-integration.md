# #757 / #766: reconcile signed negative schema identity with one trust-state checkpoint

**Scope:** evaluation-only integration branch `integration/757-distinct-schema-trust-state-no-ci`, forked from `finops/767-consolidate-qualification-no-ci`. The original PR #767 is stacked above #765/#764/#763. PR #766 is an independent main-based negative-classification hotfix.

## Preimplementation falsification

The 6-method `reference/tests/test_757_distinct_property_stack_integration.py` is committed **before** importing #766. It tests:
- exact signed, in-scope, active but distinct canonical properties **refuse** at property registry, issuer policy and the composite trust-state result;
- genuinely unmapped labels **abstain** in all three layers;
- a shared canonical property produces a local candidate only, never semantic truth or authority;
- a retired property must not be misidentified as two active distinct properties;
- key revocation outranks any apparent positive candidate and remains inspectable alongside the distinct-property refusal;
- structural isolation refusal is never downgraded by a schema classification.

The incumbent #767 composite already refuses explicitly distinct properties based on reason codes, but its lower-level registry and issuer-policy receipts still report `abstain`. Aligning the underlying status prevents downstream consumers from interpreting explicit negative schema evidence as mere uncertainty.

## Implementation and constraints

Import **exact blobs from PR #766** for `reference/agentmem_ref/evaluation/property_registry.py`, `reference/tests/test_property_registry.py`, and its preregistration document after this test/plan commit. Preserve the existing composite's independent refuse logic and receipt provenance rather than introducing a redundant positive-authority seam.

This branch inherits the **quiet** #767 FinOps correction: no redundant `.github/workflows/candidate-trust-state-qualification.yml` and restored Actions policy/inventory from `main`. Do not update the original open PR branches until reviewed, because their push triggers would consume the hosted Actions budget. No Actions dispatch, PR, merge, baseline declaration or R6 inference.

## Qualification via Claude Code cloud/local

On a clean exact-head checkout:

```bash
python -m pip install -r reference/requirements.txt
python -m unittest discover -s reference/tests -t reference -p "test_757_distinct_property_stack_integration.py"
python -m unittest discover -s reference/tests -t reference -p "test_property_registry.py"
python -m unittest discover -s reference/tests -t reference -p "test_issuer_policy.py"
python -m unittest discover -s reference/tests -t reference -p "test_issuer_policy_lineage.py"
python -m unittest discover -s reference/tests -t reference -p "test_source_actor_witnesses.py"
python -m unittest discover -s reference/tests -t reference -p "test_candidate_trust_state.py"
```

Then independently challenge invalid signatures, stale external expected heads, wrong scoped grants, schema revocation, rehashed history and post-construction mutation, and compare the exact-head full reference suite against the quiet parent. All outputs remain `identity_verified=false`, `can_supersede=false`, `authority_effect=none`, and `mutates_memory=false`. External trust-root distribution and durable state remain outside this slice.

**No tests are claimed to have executed merely because they were committed.**
