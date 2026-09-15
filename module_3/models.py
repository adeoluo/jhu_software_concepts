from __future__ import annotations

import os
from datetime import date
from urllib.parse import quote_plus

from sqlalchemy import Date, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    """Build the PostgreSQL URL from DATABASE_URL or PG* environment variables."""
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


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Applicant(Base):
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
