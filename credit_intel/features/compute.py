from __future__ import annotations
from datetime import datetime, timedelta
import json
import pandas as pd
from sqlalchemy.orm import Session

from credit_intel.db import models
from credit_intel.utils.logging import get_logger

logger = get_logger(__name__)


def _load_price_df(db: Session, issuer_id: int) -> pd.DataFrame:
    rows = (
        db.query(models.Price)
        .filter(models.Price.issuer_id == issuer_id)
        .order_by(models.Price.date.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([{ "date": r.date, "close": r.close, "volume": r.volume } for r in rows])
    df.set_index("date", inplace=True)
    return df


def _load_macro_df(db: Session) -> pd.DataFrame:
    rows = db.query(models.Macro).order_by(models.Macro.date.asc()).all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([{ "date": r.date, r.symbol: r.value } for r in rows])
    df = df.pivot_table(index="date", values=[r.symbol for r in rows], aggfunc="first")
    df.sort_index(inplace=True)
    return df


def _load_event_df(db: Session, issuer_id: int) -> pd.DataFrame:
    rows = (
        db.query(models.Event)
        .filter(models.Event.issuer_id == issuer_id)
        .order_by(models.Event.published_at.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([
        {"published_at": r.published_at, "sentiment": r.sentiment, "event_type": r.event_type}
        for r in rows
    ])
    df["date"] = df["published_at"].dt.date
    agg = df.groupby("date").agg(
        sentiment_mean=("sentiment", "mean"),
        sentiment_min=("sentiment", "min"),
        event_count=("event_type", "count"),
    )
    return agg


def compute_features_for_issuer(db: Session, issuer_id: int) -> dict:
    price = _load_price_df(db, issuer_id)
    if price.empty:
        logger.info(f"No price data for issuer {issuer_id}")
        return {}
    price["ret_1d"] = price["close"].pct_change()
    price["ret_7d"] = price["close"].pct_change(7)
    price["ret_30d"] = price["close"].pct_change(30)
    price["vol_30d"] = price["ret_1d"].rolling(30).std()
    price["dd"] = (price["close"] / price["close"].cummax()) - 1.0
    price["dd_90d"] = price["dd"].rolling(90).min()

    macro = _load_macro_df(db)
    if not macro.empty:
        merged = price.join(macro, how="left").ffill()
    else:
        merged = price.copy()

    events = _load_event_df(db, issuer_id)
    if not events.empty:
        merged = merged.join(events, how="left").fillna({"sentiment_mean": 0.0, "sentiment_min": 0.0, "event_count": 0})
    else:
        merged = merged.assign(sentiment_mean=0.0, sentiment_min=0.0, event_count=0)

    latest = merged.iloc[-1]
    feature_dict = {
        "ret_7d": float(latest.get("ret_7d", 0.0) or 0.0),
        "ret_30d": float(latest.get("ret_30d", 0.0) or 0.0),
        "vol_30d": float(latest.get("vol_30d", 0.0) or 0.0),
        "dd_90d": float(latest.get("dd_90d", 0.0) or 0.0),
        "vix": float(latest.get("VIX", 0.0) or 0.0),
        "ust10y": float(latest.get("UST10Y_YieldIndex", 0.0) or 0.0),
        "sentiment_mean": float(latest.get("sentiment_mean", 0.0) or 0.0),
        "sentiment_min": float(latest.get("sentiment_min", 0.0) or 0.0),
        "event_count": float(latest.get("event_count", 0.0) or 0.0),
    }

    snap = models.Feature(
        issuer_id=issuer_id,
        as_of=datetime.utcnow(),
        data_json=json.dumps(feature_dict),
    )
    db.add(snap)
    db.commit()
    return feature_dict