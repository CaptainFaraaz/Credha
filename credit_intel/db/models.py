from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from credit_intel.db.database import Base


class Issuer(Base):
    __tablename__ = "issuers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100))

    prices: Mapped[list[Price]] = relationship("Price", back_populates="issuer", cascade="all, delete-orphan")
    features: Mapped[list[Feature]] = relationship("Feature", back_populates="issuer", cascade="all, delete-orphan")
    scores: Mapped[list[Score]] = relationship("Score", back_populates="issuer", cascade="all, delete-orphan")
    events: Mapped[list[Event]] = relationship("Event", back_populates="issuer", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("issuer_id", "date", name="uq_price_issuer_date"),
        Index("ix_price_issuer_date", "issuer_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("issuers.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float)

    issuer: Mapped[Issuer] = relationship("Issuer", back_populates="prices")


class Macro(Base):
    __tablename__ = "macro"
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_macro_symbol_date"),
        Index("ix_macro_symbol_date", "symbol", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("issuer_id", "as_of", name="uq_feature_issuer_asof"),
        Index("ix_feature_issuer_asof", "issuer_id", "as_of"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("issuers.id", ondelete="CASCADE"), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)

    issuer: Mapped[Issuer] = relationship("Issuer", back_populates="features")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("issuer_id", "as_of", name="uq_score_issuer_asof"),
        Index("ix_score_issuer_asof", "issuer_id", "as_of"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("issuers.id", ondelete="CASCADE"), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    contributions_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    issuer: Mapped[Issuer] = relationship("Issuer", back_populates="scores")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_event_issuer_published", "issuer_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issuer_id: Mapped[int | None] = mapped_column(ForeignKey("issuers.id", ondelete="SET NULL"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    sentiment: Mapped[float | None] = mapped_column(Float)
    event_type: Mapped[str | None] = mapped_column(String(100))
    raw_text: Mapped[str | None] = mapped_column(Text)

    issuer: Mapped[Issuer | None] = relationship("Issuer", back_populates="events")