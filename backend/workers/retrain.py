"""Triggerable retraining workflow stubs."""
from __future__ import annotations

import logging
from pathlib import Path

from agents.tools import trigger_retrain

logger = logging.getLogger(__name__)


def retrain(model_version: str, reason: str) -> str:
    """Stub that persists retraining intent and returns new version."""

    Path("artifacts").mkdir(exist_ok=True)
    path = Path("artifacts") / "retrain.log"
    entry = f"Triggered from {model_version} because {reason}\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    new_version = f"{model_version}+1"
    logger.info("Retraining stub -> %s", new_version)
    return new_version
