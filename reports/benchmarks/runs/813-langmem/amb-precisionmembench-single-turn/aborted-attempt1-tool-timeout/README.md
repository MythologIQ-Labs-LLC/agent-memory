# Aborted attempt 1: stopped by the executor's tool time limit, not by the system

The first launch of this preregistered run was a child of an agent tool call with a two-hour
background limit. That limit stopped it during ingestion, before any case was scored:

- Graphiti was stopped after 5 of 35 episodes.
- LangMem was stopped manually after 16 of 35 documents, ahead of the same limit.

This is an executor infrastructure failure. It is not a provider or harness exception, and no
outcome was observed. The preregistration defines the reported run as the first *complete* run,
so this attempt is kept for audit and is not a result.

The run was relaunched fully detached with `scripts/run_amb_detached.sh`, using the same
configuration and models, a fresh store and a fresh shim call log. Files:

| File | Contents |
|---|---|
| `stdout.txt` | Native output up to the stop |
| `stderr.txt.gz` | Native error output up to the stop |
| `shim-calls.jsonl.gz` | LLM and embedding calls made before the stop |
