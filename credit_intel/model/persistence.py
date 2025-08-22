from __future__ import annotations
import os
import pickle
from typing import Any
from credit_intel.utils.config import MODEL_DIR


def model_path_for_ticker(ticker: str) -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"model_{ticker}.pkl")


def save_model(ticker: str, model: Any, feature_names: list[str]) -> None:
    path = model_path_for_ticker(ticker)
    with open(path, "wb") as f:
        pickle.dump({"model": model, "features": feature_names}, f)


def load_model(ticker: str) -> tuple[Any, list[str]] | None:
    path = model_path_for_ticker(ticker)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        obj = pickle.load(f)
        return obj["model"], obj["features"]