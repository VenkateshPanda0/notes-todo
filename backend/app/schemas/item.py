from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.item import ItemType, Priority
from ..services.tags import normalize_tags


class ItemCreate(BaseModel):
    """Payload for creating a new item. The caller must state the type explicitly."""

    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    item_type: ItemType = Field(alias="type")
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        return normalize_tags(v)


class ItemUpdate(BaseModel):
    """Payload for editing an existing item. All fields are optional (partial update)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    item_type: ItemType | None = Field(default=None, alias="type")
    completed: bool | None = None
    priority: Priority | None = None
    due_date: date | None = None
    tags: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else normalize_tags(v)


class ItemRead(BaseModel):
    """Representation of an item returned by the API."""

    id: int
    title: str
    content: str
    item_type: ItemType = Field(serialization_alias="type")
    completed: bool
    priority: Priority
    due_date: date | None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        # The ORM relationship yields Tag objects; the API exposes plain names.
        return [getattr(tag, "name", tag) for tag in v]


class TagCount(BaseModel):
    """A tag and how many items currently use it."""

    name: str
    count: int


class QuickAddRequest(BaseModel):
    """A single line of free text to interpret as an item."""

    text: str = Field(min_length=1, max_length=1000)


class QuickAddPreview(BaseModel):
    """What quick-add understood from the text. Nothing is saved."""

    title: str
    item_type: ItemType = Field(serialization_alias="type")
    priority: Priority
    due_date: date | None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
