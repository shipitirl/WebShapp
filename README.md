# WebShapp

WebShapp is a lightweight reference implementation of a SHAP-driven game replay
stack designed for constrained environments. It demonstrates a hot parquet
ingestion pipeline, deterministic SHAP generation, in-memory replay, and a
simple websocket simulator suitable for automated tests.

## Features

- **Hot Parquet ingestion** with idempotency protection and timestamp ordering.
- **Deterministic SHAP adapter** that can be swapped for a production explainer.
- **Replay engine** that streams alternating prediction and SHAP payloads along
  with a rolling feature-importance timeline.
- **Search service** for quick lookups over ingested plays.
- **Latency metrics** tracking queue depth and P95 latencies.

## Project layout

```
app/
  cli.py            # CLI entrypoint for the demo runner
  config.py         # Tunable settings
  main.py           # Async demo wiring all services together
  models.py         # Dataclasses for plays, SHAP snapshots, and payloads
  service_layer.py  # Stateless service functions acting as HTTP handlers
  services/         # Engine, SHAP adapter, and parquet loader implementations
fixtures/
  sample_game.parquet  # JSON-backed parquet fixture used by tests
tests/
  test_e2e.py       # End-to-end replay contract tests
```

## Getting started

1. **Install requirements** – the implementation only depends on the Python
   standard library and `pytest` (bundled in the execution environment). No
   external packages are required.
2. **Run the tests**

   ```bash
   pytest
   ```

3. **Run the interactive demo**

   ```bash
   python -m app.cli fixtures/sample_game.parquet
   ```

   The demo prints websocket payloads, metrics, and search results to the
   console. It is fully self-contained and does not require a running web
   server.

## API contract

Although this reference build runs without an HTTP server, the service layer is
structured to be wrapped by an API gateway or framework of your choice. Each
function in `app.service_layer` mirrors an expected HTTP endpoint:

| Function | Suggested HTTP verb & path | Notes |
| --- | --- | --- |
| `ingest_game` | `POST /games/{game_id}/ingest` | Accepts an `InjectionRequest` payload |
| `start_replay` | `POST /games/{game_id}/start` | Returns an `asyncio.Task` handle that resolves to the live replay task |
| `pause_game` | `POST /games/{game_id}/pause` | Toggles the replay flow using `PauseRequest` |
| `get_metrics` | `GET /games/{game_id}/metrics` | Returns queue depth and latency stats |
| `search` | `GET /search` | Performs substring search over ingested plays |

Wrapping these functions inside FastAPI, Flask, or another framework only
requires thin request/response adapters. Because the data models are pure
`dataclasses`, they can be serialised with `dataclasses.asdict` or converted into
Pydantic models if desired.

## Testing goals covered

The `tests/test_e2e.py` suite exercises the full stack:

- Loads the sample parquet fixture and ingests it twice to confirm idempotency.
- Starts a replay and asserts the first websocket payload is a `game_state`
  message followed by alternating `prediction` and `shap` messages with a
  populated timeline.
- Verifies the replay produces ≥10 timeline updates and that the rolling
  snapshot is non-empty.
- Confirms the computed SHAP latency P95 stays below 1.5 seconds, queue depth
  stays within bounds, and search returns expected plays.
- Exercises pause/resume semantics to guard against regressions.

## Stretch ideas

The codebase is intentionally modular so you can extend it with the stretch
ideas from the original brief:

- Persist feature-importance timelines per game and team by appending to a
  lightweight SQLite database.
- Implement an offline compaction job that converts accumulated SHAP snapshots
  into weekly parquet partitions.
- Add a comparison helper that diff two plays and surfaces SHAP deltas.

These enhancements would live primarily inside the `services/` directory and can
reuse the deterministic SHAP adapter for rapid iteration.

## License

This project is released under the MIT License. See `LICENSE` for details.
