# #732 R6 provider freeze v1

This record freezes the provider configuration for the #732 R6 generalization
acceptance **before any provider credential is used and before holdout authoring**.

## Frozen provider

- provider: Anthropic Messages API
- model: `claude-sonnet-5-5`
- temperature / sampling parameters: none sent
- `max_tokens`: 16000
- effort: `high`
- timeout: 20 seconds
- maximum prior-memory candidates: 8
- extractor version:
  `1.0.0/claude-sonnet-5-5/default/mt16000/high/9974ab010b12`
- frozen prompt sha256:
  `9974ab010b12fcd5b6e86352e4f269ab3b1e2f8842521e5b031b23904c1cd7b9`

The extractor remains opt-in. A caller must still provide an explicit egress
policy, and typed extraction has no mutation or authority effect.

## What this does not do

This freeze does **not** run a model, use a credential, author the R6 holdout,
or score anything.

The next permitted operation is a smoke request using this exact configuration
after `ANTHROPIC_API_KEY` is provisioned. Only after that smoke evidence is
accepted may the independent holdout be authored.

Changing the provider, model, sampling posture, max tokens, effort, prompt or
extractor version after this freeze requires a new provider-freeze identity.
No existing holdout may silently migrate to the changed configuration.

## Acceptance sequence

1. provider freeze;
2. credential-backed smoke request;
3. fresh independent G6 holdout authoring;
4. holdout freeze;
5. one holdout scoring on published Runtime Baseline v6;
6. extractor-on MESA and #580/#584 regressions;
7. R6 acceptance or rejection.

#673 remains held through step 7.
