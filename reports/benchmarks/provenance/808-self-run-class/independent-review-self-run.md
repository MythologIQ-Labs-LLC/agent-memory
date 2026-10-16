# Adversarial review of the self-run class (`6fe8ad8a` / records `1ac8fd27`): findings and how each was handled

**Who reviewed.** An agent launched by the executing session. It is adversarial, but **not independent of the executor in the #808 G2 sense**. Its attack scripts were re-run against the fixes.

**Verdict:** changes required, small. The 21 records, the acceptance refusal and the scorecard/catalog isolation were confirmed correct.

| # | Severity | Finding | Fix |
|---|---|---|---|
| M1 | must | The frozen-lane match was exact and case-sensitive, used only the first profile segment, and ignored `run_id`. One unrelated file in the lane directory satisfied the lane-claim rule. The viewer patch had the same gap | Validator and viewer fold the text (NFKC, case, whitespace, `Cf` characters) and check `task_profile` **and** `run_id`. A lane claim now needs `normalized_run` in the lane evidence or `normalized/`, **plus** a `native_result` in the lane evidence. All of the reviewer's variants are refused |
| M2 | must | Trail equality used Python `==` (`0 == False == 0.0`) | Type-exact canonical-JSON comparison. A mutation test shows the new test fails without it |
| S1 | should | The literal `"<absent>"` collided with the removed-field sentinel | An internal sentinel object is used, and the literal is refused as a real value |
| S2 | should | The location rule was skipped when the manifest was outside the evidence root, or when no `manifest_uri` was passed | Under an evidence root, a self-run record must be a file inside it |
| S3 | should | Schema mode accepted empty `supersedes` / `corrections` | The schema now requires exactly one `supersedes` and at least one correction |
| S4 | should | `self_hosted` counted as local; judge-only local runs fit no tier, which was undocumented | The `local_*` tiers require `local` endpoints. `self_hosted` and judge/`other`-only runs fail closed, as documented |
| S5 | should | The viewer trusted `candidate_class.tier` | The viewer verifies the tier against `inference.calls` |
| S6 | should | The docs called `normalized/` the scorecards' input | Corrected: it is the scorecard builder's output and the catalog's only input. The constant is renamed `NORMALIZED_DIR` |
| N | nit | The LangMem basis said "sent as null"; the prompt-digest recipe and chat-only token counts were undocumented; a symlink into `normalized/` was not caught; "84 pointers" was imprecise | All fixed. The resolved-path guard has a mutation-verified test. The count is now 72 evidence pointers plus 12 superseded manifests |

**Documented boundary, not a defect.** Unversioned family names (`longmemeval-s-retrieval-parity`, `amb-precisionmembench-retrieval`) are not lane ids. The second is the AMB benchmark id itself, so both stay allowed.
