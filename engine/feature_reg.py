"""Simple feature registry with schema versioning support."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import json

REGISTRY_PATH = Path("data/feature_registry.json")


@dataclass
class FeatureSchema:
    """Metadata describing a feature vector."""

    name: str
    version: str
    fields: List[str]


class FeatureRegistry:
    """In-memory registry backed by a JSON file."""

    def __init__(self, path: Path = REGISTRY_PATH) -> None:
        self._path = path
        self._items: Dict[str, FeatureSchema] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        for name, payload in data.items():
            self._items[name] = FeatureSchema(
                name=name,
                version=payload["version"],
                fields=payload["fields"],
            )

    def save(self) -> None:
        payload = {
            name: {"version": schema.version, "fields": schema.fields}
            for name, schema in self._items.items()
        }
        self._path.write_text(json.dumps(payload, indent=2))

    def upsert(self, schema: FeatureSchema) -> None:
        self._items[schema.name] = schema
        self.save()

    def get(self, name: str) -> FeatureSchema:
        return self._items[name]


registry = FeatureRegistry()
