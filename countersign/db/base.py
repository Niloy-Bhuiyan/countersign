"""Database engine, session and declarative base.

Amounts are ``NUMERIC`` everywhere. SQLite does not have a native numeric type, so
a type decorator converts on the way in and out; without it a local run would
silently hand back floats and the money guarantees would hold only on Postgres.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, TypeDecorator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column

from countersign.settings import settings


class Money(TypeDecorator):
    """NUMERIC(18, 4) that always returns a Decimal, including on SQLite."""

    impl = Numeric(18, 4, asdecimal=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, float):
            raise ValueError("refusing to store a float as an amount")
        return Decimal(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(str(value))


class Base(DeclarativeBase):
    pass


def pk() -> mapped_column:
    return mapped_column(String(36), primary_key=True)


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_column():
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
