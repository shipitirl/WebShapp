# SHAP-Aware Live Win % Engine

This repository provides a complete local stack for ingesting live NFL model outputs, applying SHAP-aware smoothing, and rendering updates in a real-time web UI. The system is optimized for sub-300ms latency while ensuring durable append-only storage for offline analytics.

## Features

- FastAPI backend with REST and websocket interfaces
- Redis-backed hot path with DuckDB/Parquet cold store
- SHAP-aware meta-model featuring exponential smoothing
- Agents for ingestion, drift detection, retraining triggers, and explainability
- React + Vite dashboard that visualizes win probability and SHAP buckets
- Prometheus + Grafana observability ready for extension

## Getting Started

1. **Python environment**

   ```bash
   uv venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

2. **Start infrastructure**

   ```bash
   make up
   ```

3. **Run the backend**

   ```bash
   make dev
   ```

4. **Start the webapp**

   ```bash
   cd webapp
   npm install
   npm run dev
   ```

5. **Seed demo data**

   ```bash
   make seed
   ```

Visit <http://localhost:5173> to view the live dashboard. The websocket endpoint streams updates for the configured game ID.

## Testing and Quality

- `make test` runs the backend test suite (placeholder)
- `make fmt` formats the Python codebase using Ruff
- `make bench` executes a local latency benchmark

## Data Layout

- `data/nfl_predictions/season=YYYY/week=WW/*.parquet` — append-only partitions
- `data/live.duckdb` — DuckDB database used for aggregated analytics
- Redis keys and channels are defined in `backend/cache.py`

## Observability

Prometheus scrapes metrics from the backend and Redis containers. Grafana can be pointed to Prometheus using the provided docker compose stack.

## Operator Runbook

1. **Start services**
   - `make up` to launch Redis, backend, webapp, Prometheus, and Grafana
2. **Tail logs**
   - Backend: `docker-compose -f infra/docker-compose.yml logs -f backend`
   - Watcher worker: `python -m backend.workers.watcher`
3. **Common failures**
   - *Redis unavailable*: ensure the container is running and accessible at `redis://localhost:6379`
   - *DuckDB lock contention*: the backend lazily refreshes views; restart the backend if locks persist
   - *Websocket disconnects*: verify the frontend is pointing to the correct host/port
4. **Reset state**
   - Stop services with `make down`
   - Remove transient data: `rm -rf data/live.duckdb logs/ reports/ artifacts/`
   - Restart with `make up`

## Architecture Diagram

```
Model Output -> Redis PubSub -> Watcher Worker -> Meta Model -> Redis Cache -> FastAPI -> WebSocket -> React UI
                                              \-> Async Parquet Append -> DuckDB -> Batch Analytics
```

Refer to `agents/*.yaml` for agent configurations and `scripts/bench_latency.py` for performance testing guidance.
