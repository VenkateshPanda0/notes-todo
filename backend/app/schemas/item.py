from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.item import ItemType, Priority
from ..services.recurrence import normalize_recurrence
from ..services.tags import normalize_tags


class ItemCreate(BaseModel):
    """Payload for creating a new item. The caller must state the type explicitly."""

    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    item_type: ItemType = Field(alias="type")
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    recurrence: str | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        return normalize_tags(v)

    @field_validator("recurrence")
    @classmethod
    def _normalize_recurrence(cls, v: str | None) -> str | None:
        return normalize_recurrence(v)

    @model_validator(mode="after")
    def _only_todos_repeat(self) -> "ItemCreate":
        if self.recurrence and self.item_type != ItemType.TODO:
            raise ValueError("Only todos can repeat.")
        return self


class ItemUpdate(BaseModel):
    """Payload for editing an existing item. All fields are optional (partial update)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    item_type: ItemType | None = Field(default=None, alias="type")
    completed: bool | None = None
    priority: Priority | None = None
    due_date: date | None = None
    recurrence: str | None = None
    tags: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("recurrence")
    @classmethod
    def _normalize_recurrence(cls, v: str | None) -> str | None:
        return normalize_recurrence(v)

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
    recurrence: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

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
    recurrence: str | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class GraphNodeRead(BaseModel):
    """An item (or a link target that doesn't exist yet) in the link graph."""

    key: str
    id: int | None
    title: str
    item_type: ItemType | None = Field(serialization_alias="type")
    completed: bool
    tags: list[str]
    missing: bool
    degree: int

    model_config = ConfigDict(populate_by_name=True)


class GraphEdgeRead(BaseModel):
    source: str
    target: str


class GraphRead(BaseModel):
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]


# --- local AI -----------------------------------------------------------------------------------


class AIStatus(BaseModel):
    """Whether local AI is switched on, and whether Ollama is reachable."""

    enabled: bool
    available: bool
    local: bool
    base_url: str
    models: list[str]
    model: str
    embed_model: str
    chat_model_ready: bool
    embed_model_ready: bool
    error: str | None = None


class AISettingsUpdate(BaseModel):
    enabled: bool | None = None
    model: str | None = Field(default=None, max_length=128)
    embed_model: str | None = Field(default=None, max_length=128)


class SummaryRead(BaseModel):
    summary: str
    model: str


class PlanRead(BaseModel):
    plan: str
    model: str
    items: list[ItemRead]


class RelatedRead(BaseModel):
    item: ItemRead
    score: float


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=6, ge=1, le=12)


class AskRead(BaseModel):
    answer: str
    model: str
    sources: list[RelatedRead]
