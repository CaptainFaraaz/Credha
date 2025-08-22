from __future__ import annotations
import json
from datetime import datetime
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from credit_intel.db.database import SessionLocal, init_db
from credit_intel.db import models
from credit_intel.utils.config import DEFAULT_TICKERS, RSS_FEEDS
from credit_intel.ingestion.structured import upsert_issuers, fetch_prices_for_ticker, fetch_macro_proxies
from credit_intel.ingestion.unstructured import ingest_rss
from credit_intel.features.compute import compute_features_for_issuer
from credit_intel.model.train import train_for_issuer
from credit_intel.model.score import score_latest

app = FastAPI(title="Credit Intel API", default_response_class=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def get_db() -> Session:
    return SessionLocal()


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/refresh")
def refresh():
    db = get_db()
    try:
        upsert_issuers(db, DEFAULT_TICKERS)
        for t in DEFAULT_TICKERS:
            fetch_prices_for_ticker(db, t)
        fetch_macro_proxies(db)
        ingest_rss(db, RSS_FEEDS, DEFAULT_TICKERS)
        # Train and score
        for t in DEFAULT_TICKERS:
            issuer = db.query(models.Issuer).filter(models.Issuer.ticker == t).one_or_none()
            if not issuer:
                continue
            try:
                train_for_issuer(db, issuer.id, t)
            except Exception:
                pass
            score_latest(db, issuer.id, t)
        return {"status": "refreshed"}
    finally:
        db.close()


@app.get("/issuers")
def list_issuers():
    db = get_db()
    try:
        rows = db.query(models.Issuer).all()
        return [{"id": r.id, "ticker": r.ticker, "name": r.name, "sector": r.sector} for r in rows]
    finally:
        db.close()


@app.get("/scores/{ticker}")
def get_scores(ticker: str):
    db = get_db()
    try:
        issuer = db.query(models.Issuer).filter(models.Issuer.ticker == ticker.upper()).one_or_none()
        if not issuer:
            return []
        rows = (
            db.query(models.Score)
            .filter(models.Score.issuer_id == issuer.id)
            .order_by(models.Score.as_of.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "as_of": r.as_of.isoformat(),
                "score": r.score,
                "contributions": json.loads(r.contributions_json),
                "summary": r.summary,
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/features/{ticker}")
def get_features(ticker: str):
    db = get_db()
    try:
        issuer = db.query(models.Issuer).filter(models.Issuer.ticker == ticker.upper()).one_or_none()
        if not issuer:
            return {}
        row = (
            db.query(models.Feature)
            .filter(models.Feature.issuer_id == issuer.id)
            .order_by(models.Feature.as_of.desc())
            .first()
        )
        return json.loads(row.data_json) if row else {}
    finally:
        db.close()


@app.get("/events/{ticker}")
def get_events(ticker: str):
    db = get_db()
    try:
        issuer = db.query(models.Issuer).filter(models.Issuer.ticker == ticker.upper()).one_or_none()
        if not issuer:
            return []
        rows = (
            db.query(models.Event)
            .filter(models.Event.issuer_id == issuer.id)
            .order_by(models.Event.published_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "published_at": r.published_at.isoformat(),
                "title": r.title,
                "url": r.url,
                "sentiment": r.sentiment,
                "event_type": r.event_type,
            }
            for r in rows
        ]
    finally:
        db.close()