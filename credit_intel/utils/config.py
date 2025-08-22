import os
from typing import List

DEFAULT_TICKERS: List[str] = (
    os.getenv("CI_TICKERS", "AAPL,MSFT,GOOGL,AMZN").split(",")
)

RSS_FEEDS: List[str] = [
    # General business/markets RSS feeds (public)
    os.getenv("CI_RSS_REUTERS_BUSINESS", "https://feeds.reuters.com/reuters/businessNews"),
    os.getenv("CI_RSS_MARKETS", "https://feeds.reuters.com/reuters/USmarkets"),
]

FRED_API_KEY: str | None = os.getenv("FRED_API_KEY")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./credit_intel.db")

MODEL_DIR: str = os.getenv("MODEL_DIR", "./model_store")

DATA_REFRESH_MINUTES: int = int(os.getenv("DATA_REFRESH_MINUTES", "30"))

USER_AGENT: str = os.getenv(
    "CI_USER_AGENT",
    "credit-intel/0.1 (+https://example.com; contact@example.com)",
)