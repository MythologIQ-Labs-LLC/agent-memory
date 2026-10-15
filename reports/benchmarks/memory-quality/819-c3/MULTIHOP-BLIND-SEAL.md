# Blind multi-hop cohort seal (#819 C3 slice 4)

Authored by a separate agent that read only `scripts/run_memory_quality_scenarios.py` (input format),
not the runtime, tests, fixtures or any sealed cohort, after the entity-bridging mechanism was designed
and before any run against it. 30 scenarios, 32 queries: multi_hop 12, single_hop_with_names 8,
multi_hop_lifecycle 6, abstention_with_names 4.

sha256 `6acef4bf3d81f38472461daa4f7227d7fae39c98647d755891d8ed0b3f1cb343`, recorded before the first run. Each system was run once on it;
no runtime change was made after seeing its results.
