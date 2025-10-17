from __future__ import annotations

import argparse
from pathlib import Path

from .main import run_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WebShapp demo runner")
    parser.add_argument("parquet", type=Path, nargs="?", default=Path("fixtures/sample_game.parquet"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from asyncio import run

    run(run_demo(args.parquet))


if __name__ == "__main__":
    main()
