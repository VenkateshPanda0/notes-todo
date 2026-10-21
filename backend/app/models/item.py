from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .embedding import ItemEmbedding
from .tag import Tag, item_tags


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemType(str, Enum):
    TODO = "TODO"
    NOTE = "NOTE"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Item(Base):
    """A user-created item explicitly classified as a todo or note."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    item_type: Mapped[ItemType] = mapped_column(
        "type", SqlEnum(ItemType, name="item_type"), nullable=False
    )
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[Priority] = mapped_column(
        SqlEnum(Priority, name="priority"), default=Priority.MEDIUM, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Repeat rule such as "1w" (see services/recurrence.py); only meaningful for todos.
    recurrence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Day of month a monthly/yearly series is anchored to, so month-end dates don't drift.
    recurrence_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    tags: Mapped[list[Tag]] = relationship(
        secondary=item_tags, lazy="selectin", order_by=Tag.name, passive_deletes=True
    )
    # Removed together with the item (SQLite does not enforce foreign keys by default).
    embedding: Mapped[ItemEmbedding | None] = relationship(
        cascade="all, delete-orphan", uselist=False
    )
