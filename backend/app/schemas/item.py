from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.item import ItemType, Priority


class ItemCreate(BaseModel):
    """Payload for creating a new item. The caller must state the type explicitly."""

    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    item_type: ItemType = Field(alias="type")
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None

    model_config = ConfigDict(populate_by_name=True)


class ItemUpdate(BaseModel):
    """Payload for editing an existing item. All fields are optional (partial update)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    item_type: ItemType | None = Field(default=None, alias="type")
    completed: bool | None = None
    priority: Priority | None = None
    due_date: date | None = None

    model_config = ConfigDict(populate_by_name=True)


class ItemRead(BaseModel):
    """Representation of an item returned by the API."""

    id: int
    title: str
    content: str
    item_type: ItemType = Field(serialization_alias="type")
    completed: bool
    priority: Priority
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
