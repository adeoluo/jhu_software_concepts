"""SQLAlchemy model for the Module 3 ``applicants`` table and database connection settings."""

from __future__ import annotations

import os
from datetime import date
from urllib.parse import quote_plus

from sqlalchemy import Date, Float, Integer, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for the ORM models."""


_override_url: str | None = None


def database_url() -> str:
    """Build the PostgreSQL URL from an override, DATABASE_URL, or PG* environment variables."""
    if _override_url:
        return _override_url
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    username = os.getenv("PGUSER") or os.getenv("USER")
    if not username:
        raise RuntimeError("Set DATABASE_URL or PGUSER before starting the application.")

    password = os.getenv("PGPASSWORD", "")
    database = os.getenv("PGDATABASE", "gradcafe_module_3")
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    credentials = encoded_username
    if password:
        credentials += f":{encoded_password}"
    return f"postgresql+psycopg://{credentials}@{host}:{port}/{database}"


def sqlalchemy_url(url: str) -> str:
    """Make plain ``postgresql://`` URLs use the psycopg 3 driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(sqlalchemy_url(database_url()), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def use_database(url: str) -> None:
    """Point every loader, query, and ORM session at ``url`` (used by ``create_app`` and tests)."""
    global _override_url, engine
    _override_url = url
    engine.dispose()
    engine = create_engine(sqlalchemy_url(url), pool_pre_ping=True)
    SessionLocal.configure(bind=engine)


class Applicant(Base):
    """One Grad Cafe result row. The schema is unchanged from Module 3; ``p_id`` is the uniqueness key."""

    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program: Mapped[str | None] = mapped_column(Text)
    university: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    date_added: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(Text)
    us_or_international: Mapped[str | None] = mapped_column(Text)
    gpa: Mapped[float | None] = mapped_column(Float)
    gre: Mapped[float | None] = mapped_column(Float)
    gre_v: Mapped[float | None] = mapped_column(Float)
    gre_aw: Mapped[float | None] = mapped_column(Float)
    degree: Mapped[str | None] = mapped_column(Text)
    llm_generated_program: Mapped[str | None] = mapped_column(Text)
    llm_generated_university: Mapped[str | None] = mapped_column(Text)
