from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from credit_intel.utils.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    from credit_intel.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)