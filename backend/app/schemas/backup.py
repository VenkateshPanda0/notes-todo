from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.item import ItemType, Priority
from ..services.recurrence import normalize_recurrence

EXPORT_FORMAT = "taskflow-export"
EXPORT_VERSION = 1
MAX_IMPORT_ITEMS = 50_000


class ExportItem(BaseModel):
    """One item in a TaskFlow export file."""

    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    item_type: ItemType = Field(alias="type")
    completed: bool = False
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    recurrence: str | None = None
    recurrence_day: int | None = Field(default=None, ge=1, le=31)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("recurrence", mode="before")
    @classmethod
    def _lenient_recurrence(cls, v):
        # A repeat rule we can't read shouldn't make the whole import fail; the todo just won't repeat.
        try:
            return normalize_recurrence(v) if isinstance(v, str) else None
        except ValueError:
            return None


class ExportFile(BaseModel):
    format: Literal["taskflow-export"] = EXPORT_FORMAT
    version: int = Field(default=EXPORT_VERSION, ge=1)
    exported_at: datetime | None = None
    items: list[ExportItem] = Field(max_length=MAX_IMPORT_ITEMS)


class ImportResult(BaseModel):
    mode: Literal["merge", "replace"]
    imported: int
    skipped: int


class AutoBackupInfo(BaseModel):
    name: str
    size: int
    modified: datetime


class AutoBackupList(BaseModel):
    enabled: bool
    directory: str | None
    backups: list[AutoBackupInfo]
