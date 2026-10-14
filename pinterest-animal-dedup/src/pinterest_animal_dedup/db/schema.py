from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from pinterest_animal_dedup.config import settings


class Base(DeclarativeBase):
    pass


class CandidateRow(Base):
    __tablename__ = "candidates"

    pin_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    url: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    media_type: Mapped[str] = mapped_column(String(32), default="unknown")
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_query: Mapped[str] = mapped_column(String(256), default="")
    pin_json: Mapped[str] = mapped_column(Text, default="{}")
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    domestic_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    aggregate_dedup: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    score_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    adaptation_mode: Mapped[str] = mapped_column(String(8), default="B")
    adaptation_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def get_engine():
    return create_engine(settings.database_url, future=True)


def get_session_factory():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
