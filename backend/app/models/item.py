from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemType(str, Enum):
    TODO = "TODO"
    NOTE = "NOTE"


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
