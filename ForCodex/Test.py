"""Comprehensive machine learning pipeline integrating PyTorch, XGBoost,
DuckDB, Kafka streaming, BentoML model serving, and Streamlit front end.

The module demonstrates how an organisation can migrate away from
TensorFlow-only workflows to a multi-model approach.  It includes:
    * DuckDB-backed feature storage.
    * Kafka producers/consumers for near-real-time streaming updates.
    * PyTorch neural network training utilities.
    * Gradient-boosted decision tree training with XGBoost.
    * BentoML service factory to expose both models as an HTTP API.
    * Streamlit application scaffold for interactive predictions.

The code is written as a collection of composable utilities so that each
component can be tested and replaced independently in a production system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import duckdb
import numpy as np
import pandas as pd
import torch
from kafka import KafkaConsumer, KafkaProducer
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import xgboost as xgb

import bentoml
from bentoml.io import JSON
import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Data access layer backed by DuckDB
# ---------------------------------------------------------------------------


@dataclass
class DuckDBConfig:
    """Configuration for the DuckDB feature store."""

    database: str = ":memory:"
    table_name: str = "events"


class DuckDBFeatureStore:
    """Feature store that persists tabular data in DuckDB."""

    def __init__(self, config: DuckDBConfig) -> None:
        self.config = config
        self.connection = duckdb.connect(config.database)
        self._initialise_table()

    def _initialise_table(self) -> None:
        self.connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                event_id VARCHAR,
                feature_vector DOUBLE[],
                label DOUBLE
            )
            """
        )

    def ingest_batch(self, records: Sequence[Tuple[str, Sequence[float], float]]) -> None:
        """Insert a batch of records into DuckDB."""

        if not records:
            return

        event_ids, features, labels = zip(*records)
        dataframe = pd.DataFrame(
            {
                "event_id": list(event_ids),
                "feature_vector": [list(v) for v in features],
                "label": list(labels),
            }
        )
        self.connection.execute(
            f"INSERT INTO {self.config.table_name} SELECT * FROM dataframe"
        )

    def load_training_frame(self) -> pd.DataFrame:
        """Return all stored data as a pandas DataFrame."""

        return self.connection.execute(
            f"SELECT event_id, feature_vector, label FROM {self.config.table_name}"
        ).fetchdf()


# ---------------------------------------------------------------------------
# Kafka streaming utilities
# ---------------------------------------------------------------------------


@dataclass
class KafkaConfig:
    """Configuration describing how to connect to Kafka."""

    bootstrap_servers: str
    topic: str
    group_id: str = "model-training"
    client_id: str = "ml-pipeline"


class KafkaStreamer:
    """Small wrapper around Kafka producer and consumer."""

    def __init__(self, config: KafkaConfig) -> None:
        self.config = config
        self.producer = KafkaProducer(
            bootstrap_servers=config.bootstrap_servers,
            client_id=config.client_id,
            value_serializer=lambda value: pd.Series(value).to_json().encode("utf-8"),
        )
        self.consumer = KafkaConsumer(
            config.topic,
            bootstrap_servers=config.bootstrap_servers,
            group_id=config.group_id,
            client_id=config.client_id,
            auto_offset_reset="earliest",
            value_deserializer=lambda payload: pd.read_json(payload.decode("utf-8"), typ="series"),
        )

    def produce(self, events: Iterable[Dict[str, Any]]) -> None:
        """Publish events to Kafka."""

        for event in events:
            self.producer.send(self.config.topic, value=event)
        self.producer.flush()

    def consume(self, limit: int) -> List[Dict[str, Any]]:
        """Consume up to ``limit`` events from Kafka."""

        output: List[Dict[str, Any]] = []
        for message in self.consumer:
            output.append(message.value.to_dict())
            if len(output) >= limit:
                break
        return output


# ---------------------------------------------------------------------------
# PyTorch model definition and training utilities
# ---------------------------------------------------------------------------


class EventNet(nn.Module):
    """Simple fully connected neural network for event scoring."""

    def __init__(self, input_dim: int, hidden_dim: int = 32) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        return self.network(features)


def train_pytorch_model(
    dataframe: pd.DataFrame,
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
) -> EventNet:
    """Train a PyTorch model using the provided data frame."""

    features = np.stack(dataframe["feature_vector"].to_numpy())
    labels = dataframe["label"].to_numpy().reshape(-1, 1)

    dataset = TensorDataset(torch.from_numpy(features).float(), torch.from_numpy(labels).float())
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = EventNet(features.shape[1])
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_function = nn.BCELoss()

    model.train()
    for _ in range(epochs):
        for batch_features, batch_labels in dataloader:
            optimiser.zero_grad()
            predictions = model(batch_features)
            loss = loss_function(predictions, batch_labels)
            loss.backward()
            optimiser.step()
    return model


# ---------------------------------------------------------------------------
# XGBoost training utilities
# ---------------------------------------------------------------------------


def train_xgboost_model(dataframe: pd.DataFrame) -> xgb.Booster:
    """Train an XGBoost model using the same features as the neural network."""

    features = np.stack(dataframe["feature_vector"].to_numpy())
    labels = dataframe["label"].to_numpy()

    matrix = xgb.DMatrix(features, label=labels)
    params = {
        "max_depth": 4,
        "eta": 0.2,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
    }
    return xgb.train(params, matrix, num_boost_round=40)


# ---------------------------------------------------------------------------
# BentoML model packaging and service factory
# ---------------------------------------------------------------------------


def save_models_to_bentoml(torch_model: EventNet, xgb_model: xgb.Booster) -> Tuple[str, str]:
    """Persist trained models to BentoML's model store."""

    torch_model.eval()
    first_layer = next(module for module in torch_model.modules() if isinstance(module, nn.Linear))
    dummy_input = torch.rand(1, first_layer.in_features)
    scripted = torch.jit.trace(torch_model, dummy_input)

    torch_tag = bentoml.pytorch.save_model("event_net", scripted)
    xgb_tag = bentoml.xgboost.save_model("event_booster", xgb_model)
    return str(torch_tag), str(xgb_tag)


def create_bentoml_service(torch_tag: str, xgb_tag: str) -> bentoml.Service:
    """Create a BentoML service exposing PyTorch and XGBoost models."""

    torch_runner = bentoml.pytorch.load_runner(torch_tag)
    xgb_runner = bentoml.xgboost.load_runner(xgb_tag)

    service = bentoml.Service("event_scoring", runners=[torch_runner, xgb_runner])

    @service.api(input=JSON(), output=JSON())
    async def predict(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return predictions for both models."""

        vectors = payload["feature_vector"]
        torch_array = torch.tensor(vectors, dtype=torch.float32)
        torch_output = await torch_runner.async_run(torch_array)

        xgb_matrix = xgb.DMatrix(np.asarray(vectors))
        xgb_output = await xgb_runner.async_run(xgb_matrix)

        return {
            "pytorch_scores": torch_output.squeeze(-1).tolist(),
            "xgboost_scores": xgb_output.tolist(),
        }

    return service


# ---------------------------------------------------------------------------
# Streamlit front-end
# ---------------------------------------------------------------------------


DEFAULT_FEATURE_NAMES = ["age", "balance", "num_transactions", "velocity"]


def run_streamlit_app(api_url: str, feature_names: Sequence[str] = DEFAULT_FEATURE_NAMES) -> None:
    """Launch a Streamlit dashboard for real-time predictions."""

    st.set_page_config(page_title="Event Scoring Dashboard")
    st.title("Event Scoring Dashboard")
    st.write(
        "Submit feature values to retrieve predictions from the BentoML service "
        "powered by PyTorch and XGBoost models."
    )

    feature_inputs: Dict[str, float] = {}
    for name in feature_names:
        feature_inputs[name] = st.number_input(f"Feature: {name}", value=0.0, format="%.4f")

    if st.button("Predict"):
        payload = {"feature_vector": [[feature_inputs[name] for name in feature_names]]}
        response = requests.post(api_url, json=payload, timeout=5)
        if response.ok:
            predictions = response.json()
            st.success("Prediction received")
            st.json(predictions)
        else:
            st.error(f"Request failed with status {response.status_code}: {response.text}")


__all__ = [
    "DuckDBConfig",
    "DuckDBFeatureStore",
    "KafkaConfig",
    "KafkaStreamer",
    "EventNet",
    "train_pytorch_model",
    "train_xgboost_model",
    "save_models_to_bentoml",
    "create_bentoml_service",
    "run_streamlit_app",
]

