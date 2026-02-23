"""Shared SQLAlchemy declarative base and mixins."""

from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def prefixed_id(prefix: str) -> str:
    """Generate random prefixed ID string.

    Args:
        prefix: Three-letter model prefix like USR or GRP.
    Returns:
        str: Random ID like USR_abcd1234.
    """
    suffix = token_urlsafe(9).replace("-", "").replace("_", "")
    return f"{prefix.upper()}_{suffix[:14]}"


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base class."""


class TimestampedModel:
    """Abstract mixin for create/update timestamps.

    Args:
        None
    Returns:
        None: Mixes timestamp columns into inheriting models.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PrefixedIDModel:
    """Abstract mixin for prefixed random IDs.

    Args:
        None
    Returns:
        None: Adds string ID primary key to inheriting models.
    """

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
