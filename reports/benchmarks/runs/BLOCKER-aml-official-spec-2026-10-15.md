# AML Cycle 2: the official API guide could not be retrieved, so spec validation is blocked (2026-10-15)

The Add/Search service (`integrations/aml-cycle2/` on branch `claude/wizardly-cray-bmkfrr`) was
built against a contract triangulated from three public Cycle 2 adapters. To validate it against
the **official** guide, that guide must be retrieved. Every route failed:

| Route | Result |
|---|---|
| `curl https://agentmemoryleaderboard.ai/api-guide` (also `www.`) from the session container | egress proxy: `403` on CONNECT (policy denial) |
| `curl https://agentmemories.ai/api-guide` | egress proxy: `403` on CONNECT |
| External web fetcher, both hosts | `getaddrinfo ENOTFOUND` |
| Web archive | fetcher refused |
| Public repo `AML-memory/agent-memory-leaderboard` @ `1b8142b` | contains answer/judge pipelines only, no Add/Search contract |

Minimum correction: allow `agentmemoryleaderboard.ai` (and `agentmemories.ai`) in this cloud
environment's network settings, or supply a copy of the guide. Then diff it field by field
against `integrations/aml-cycle2/README.md` § Contract and re-run the 21-check smoke. No
deployment, credential request or evaluation was attempted.
