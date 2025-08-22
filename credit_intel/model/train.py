from __future__ import annotations
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Tuple

from sqlalchemy.orm import Session
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from credit_intel.db import models
from credit_intel.model.persistence import save_model
from credit_intel.utils.logging import get_logger

logger = get_logger(__name__)


FEATURE_ORDER = [
    "ret_7d",
    "ret_30d",
    "vol_30d",
    "dd_90d",
    "vix",
    "ust10y",
    "sentiment_mean",
    "sentiment_min",
    "event_count",
]


def _load_training_frame(db: Session, issuer_id: int) -> pd.DataFrame:
    prices = (
        db.query(models.Price)
        .filter(models.Price.issuer_id == issuer_id)
        .order_by(models.Price.date.asc())
        .all()
    )
    if not prices:
        return pd.DataFrame()
    p = pd.DataFrame([{ "date": r.date, "close": r.close } for r in prices]).set_index("date").sort_index()
    p["ret_1d"] = p["close"].pct_change()
    p["ret_7d"] = p["close"].pct_change(7)
    p["ret_30d"] = p["close"].pct_change(30)
    p["vol_30d"] = p["ret_1d"].rolling(30).std()
    p["dd"] = (p["close"] / p["close"].cummax()) - 1.0
    p["dd_90d"] = p["dd"].rolling(90).min()

    macro_rows = db.query(models.Macro).order_by(models.Macro.date.asc()).all()
    if macro_rows:
        m = pd.DataFrame([{ "date": r.date, r.symbol: r.value } for r in macro_rows])
        m = m.pivot_table(index="date", values=[r.symbol for r in macro_rows], aggfunc="first").sort_index()
        df = p.join(m, how="left").ffill()
    else:
        df = p

    ev_rows = (
        db.query(models.Event)
        .filter(models.Event.issuer_id == issuer_id)
        .order_by(models.Event.published_at.asc())
        .all()
    )
    if ev_rows:
        e = pd.DataFrame([{ "published_at": r.published_at, "sentiment": r.sentiment } for r in ev_rows])
        e["date"] = e["published_at"].dt.date
        e = e.groupby("date").agg(sentiment_mean=("sentiment", "mean"), sentiment_min=("sentiment", "min"), event_count=("sentiment", "count"))
        df = df.join(e, how="left").fillna({"sentiment_mean": 0.0, "sentiment_min": 0.0, "event_count": 0})
    else:
        df = df.assign(sentiment_mean=0.0, sentiment_min=0.0, event_count=0)

    df = df.dropna()

    stress = (
        (df["dd_90d"] < -0.15)
        | (df["ret_7d"] < -0.08)
        | (df["ret_30d"] < -0.15)
        | (df["sentiment_min"] < -0.5)
    ).astype(int)

    X = df[FEATURE_ORDER].copy()
    y = stress.values
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X = X.dropna()
    y = y[-len(X):]
    X["event_count"] = X["event_count"].astype(float)
    return X, y, df.index[-len(X):]


def train_for_issuer(db: Session, issuer_id: int, ticker: str) -> tuple[Pipeline, dict]:
    data = _load_training_frame(db, issuer_id)
    if isinstance(data, pd.DataFrame) and data.empty:
        raise ValueError("Insufficient data to train")
    X, y, idx = data
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    model.fit(X.values, y)

    contributions = {name: 0.0 for name in FEATURE_ORDER}
    try:
        import shap  # optional
        explainer = shap.LinearExplainer(model.named_steps["clf"], X, feature_perturbation="interventional")
        shap_values = explainer.shap_values(X.tail(1))
        contributions = {name: float(val) for name, val in zip(FEATURE_ORDER, shap_values[0])}
    except Exception:
        pass

    save_model(ticker, model, FEATURE_ORDER)
    return model, contributions