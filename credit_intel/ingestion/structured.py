from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from credit_intel.db import models
from credit_intel.utils.logging import get_logger

logger = get_logger(__name__)


def upsert_issuers(db: Session, tickers: Iterable[str]) -> None:
    normalized = [t.strip().upper() for t in tickers if t.strip()]
    for ticker in normalized:
        issuer = db.query(models.Issuer).filter(models.Issuer.ticker == ticker).one_or_none()
        if issuer is None:
            issuer = models.Issuer(ticker=ticker)
            db.add(issuer)
    db.commit()


def fetch_prices_for_ticker(db: Session, ticker: str, lookback_days: int = 365 * 3) -> int:
    end = datetime.utcnow().date()
    start = end - timedelta(days=lookback_days)
    logger.info(f"Downloading price history for {ticker} from {start} to {end}")
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if data is None or data.empty:
        logger.warning(f"No data for {ticker}")
        return 0
    data = data.reset_index().rename(columns={"Date": "date", "Close": "close", "Volume": "volume"})
    issuer = db.query(models.Issuer).filter(models.Issuer.ticker == ticker).one()
    inserted = 0
    for _, row in data.iterrows():
        date = pd.to_datetime(row["date"]).date()
        exists = (
            db.query(models.Price)
            .filter(models.Price.issuer_id == issuer.id, models.Price.date == date)
            .one_or_none()
        )
        if exists:
            continue
        price = models.Price(
            issuer_id=issuer.id,
            date=date,
            close=float(row["close"]),
            volume=float(row["volume"]) if not pd.isna(row["volume"]) else None,
        )
        db.add(price)
        inserted += 1
    db.commit()
    logger.info(f"Inserted {inserted} rows for {ticker}")
    return inserted


MACRO_SYMBOLS = {
    "^VIX": "VIX",
    "^TNX": "UST10Y_YieldIndex",
}


def fetch_macro_proxies(db: Session, lookback_days: int = 365 * 5) -> int:
    end = datetime.utcnow().date()
    start = end - timedelta(days=lookback_days)
    total = 0
    for yf_symbol, macro_symbol in MACRO_SYMBOLS.items():
        logger.info(f"Downloading macro proxy {macro_symbol} ({yf_symbol})")
        data = yf.download(yf_symbol, start=start, end=end, progress=False, auto_adjust=False)
        if data is None or data.empty:
            logger.warning(f"No data for macro {macro_symbol}")
            continue
        data = data.reset_index().rename(columns={"Date": "date", "Close": "close"})
        inserted = 0
        for _, row in data.iterrows():
            date = pd.to_datetime(row["date"]).date()
            exists = (
                db.query(models.Macro)
                .filter(models.Macro.symbol == macro_symbol, models.Macro.date == date)
                .one_or_none()
            )
            if exists:
                continue
            value = float(row["close"]) if not pd.isna(row["close"]) else None
            if value is None:
                continue
            rec = models.Macro(symbol=macro_symbol, date=date, value=value)
            db.add(rec)
            inserted += 1
        db.commit()
        logger.info(f"Inserted {inserted} rows for macro {macro_symbol}")
        total += inserted
    return total