.PHONY: up down dev test fmt bench seed

up:
docker-compose -f infra/docker-compose.yml up -d --build

down:
docker-compose -f infra/docker-compose.yml down

dev:
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

test:
pytest

fmt:
ruff format

bench:
python scripts/bench_latency.py

seed:
python scripts/seed_demo.py --gid demo --input scripts/demo_packets.jsonl --speed 4
