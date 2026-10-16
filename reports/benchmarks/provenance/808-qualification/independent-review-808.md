# Independent adversarial review of the #808 qualification: findings and how each was handled

**Who reviewed.** An agent launched by this executing session ran read-only against `5a86518e` plus the uncommitted audit. It is adversarial, but **not independent of the executor in the governance sense** (see G2 in `INTEGRATION-HANDOFF.md`).

**Verdict:** changes required. Every must-fix and should-fix item below has been fixed in the commit that adds this file.

**What the reviewer confirmed unchanged:**
- The 14 original tests at `891b4234` are unmodified.
- Each of these checks reproduced:
  - 130/130 re-hash;
  - 12 valid and 9 refused as committed;
  - the R1–R4 and R9 counts;
  - the parity-v1 mislabel (scorer `4acdeccc` vs `6b9c2373`);
  - the LongMemEval denominators and the lane-v6 equivalence table;
  - the AMB repeats and identical pass sets;
  - the Graphiti token counts.
- Mutation tests on the RFC 3339 and pointer guards fail the new tests, as they should.

| # | Severity | Finding | Fix |
|---|---|---|---|
| M1 | must | The credential guard was weaker than at `891b4234` for embedded or suffixed flags (`sh -c '… --api-key=…'`, `--secret-key=`, `--password1=`, `--api-key-file=`, `x --auth-token abc`) and for parameter keys containing "tokens" | The original substring checks are restored. The flag and assignment patterns are unanchored. Only exact token-count keys are exempt. Regression tests added |
| M2 | must | The proposed composite input digest contradicted the frozen AMB lane rule, and `sorted()` dropped file order | The audit now uses the lane's own `input_sha256` (`caf5869b…`). G3 is withdrawn |
| M3 | must | The gap count was wrong (82 vs 98 metadata) | Recomputed after all fixes: 100 metadata, 42 governance, 4 evidence. The report numbers are generated |
| S1 | should | Executor ≠ reviewer was compared by exact string. Nothing bound the authority file to the owner | Identities are normalised and type-checked. `--review-authority-sha256` must equal an owner-published digest. Malformed records are refused, not crashed |
| S2 | should | The "valid" claims did not use re-hash mode, where 0/21 pass, and gzipped normalized runs gave a decode error | The audit reports re-hash-mode results (0/21, with reasons). The checker refuses a non-JSON normalized run clearly |
| S3 | should | Inference gaps were typed "metadata" whenever a shim log existed | Values that were never sent are typed "evidence" (4). They are resolved by citing the pinned llama-cpp-python 0.3.16 server defaults, whose file digest is verified against the wheel's RECORD. `n_ctx` is treated as a rename |
| S4 | should | Several claims were not produced by the reproduce command; "byte-identical" was wrong; "tied" was unproven | Cohort-table rebuild (4/4 identical), Graphiti LLM call identity (167/167 content-identical, 0/167 raw) and the gold-key AST scan are now computed by the script. The wording is corrected. Cross-lane replication is cited, not recomputed |
| S5 | should | Adapter-blob count was wrong (5 manifests, not 4), the preregistration recorded a commit, and there was no shallow-clone guard | Counts and wording are corrected. `adapter_history` verifies that the file was created inside the visible history |
| N | nit | Unreachable branch; non-dict authority traceback; bare `https://`; DEL and Unicode separators in pointers | All fixed, with tests |
