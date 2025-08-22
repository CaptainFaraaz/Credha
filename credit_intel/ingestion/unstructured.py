from __future__ import annotations
from datetime import datetime, timezone
from typing import Iterable

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy.orm import Session

from credit_intel.db import models
from credit_intel.utils.logging import get_logger

logger = get_logger(__name__)
_analyzer = SentimentIntensityAnalyzer()


EVENT_KEYWORDS = {
    "restructur": "debt_restructuring",
    "bankrupt": "bankruptcy",
    "downgrad": "rating_downgrade",
    "upgrade": "rating_upgrade",
    "guidance": "guidance",
    "lawsuit": "litigation",
    "probe": "regulatory_probe",
    "layoff": "workforce_reduction",
    "default": "default",
    "misses": "earnings_miss",
    "beats": "earnings_beat",
}


def classify_event(text: str) -> str | None:
    t = text.lower()
    for key, label in EVENT_KEYWORDS.items():
        if key in t:
            return label
    return None


def map_to_issuer(db: Session, title: str, tickers: Iterable[str]) -> int | None:
    text = title.upper()
    for t in tickers:
        if t in text.split():
            issuer = db.query(models.Issuer).filter(models.Issuer.ticker == t).one_or_none()
            if issuer:
                return issuer.id
    return None


def ingest_rss(db: Session, feeds: Iterable[str], known_tickers: Iterable[str]) -> int:
    inserted = 0
    for url in feeds:
        try:
            logger.info(f"Fetching RSS: {url}")
            parsed = feedparser.parse(url)
        except Exception as e:
            logger.warning(f"RSS fetch failed for {url}: {e}")
            continue
        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if not title or not link or not published_parsed:
                continue
            published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            exists = (
                db.query(models.Event)
                .filter(models.Event.url == link)
                .one_or_none()
            )
            if exists:
                continue
            sentiment = _analyzer.polarity_scores(title)["compound"]
            event_type = classify_event(title)
            issuer_id = map_to_issuer(db, title, known_tickers)
            ev = models.Event(
                issuer_id=issuer_id,
                source=url,
                title=title,
                url=link,
                published_at=published_at,
                sentiment=sentiment,
                event_type=event_type,
                raw_text=None,
            )
            db.add(ev)
            inserted += 1
        db.commit()
    logger.info(f"Inserted {inserted} events")
    return inserted