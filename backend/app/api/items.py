from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..models.item import ItemType
from ..schemas.item import ItemCreate, ItemRead, ItemUpdate, QuickAddPreview, QuickAddRequest
from ..services import items as items_service
from ..services.quick_add import parse_quick_add
from ..services.items import ItemNotFoundError
from .deps import get_db, require_unlocked

router = APIRouter(
    prefix="/api/items", tags=["items"], dependencies=[Depends(require_unlocked)]
)


@router.post("", response_model=ItemRead, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> ItemRead:
    """Create a new Todo or Note. The type must be given explicitly by the caller."""
    item = items_service.create_item(db, payload)
    return ItemRead.model_validate(item)


@router.post("/parse", response_model=QuickAddPreview, response_model_by_alias=True)
def parse_quick_add_text(payload: QuickAddRequest) -> QuickAddPreview:
    """Interpret quick-capture text (e.g. "call dentist tomorrow !high") without saving anything."""
    result = parse_quick_add(payload.text)
    return QuickAddPreview(
        title=result.title,
        item_type=result.item_type,
        priority=result.priority,
        due_date=result.due_date,
        tags=list(result.tags),
        recurrence=result.recurrence,
    )


@router.get("", response_model=list[ItemRead])
def list_items(
    type: ItemType | None = Query(default=None),
    completed: bool | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    """List items, optionally filtered by type and/or completion state."""
    items = items_service.list_items(db, item_type=type, completed=completed, tag=tag)
    return [ItemRead.model_validate(item) for item in items]


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)) -> ItemRead:
    """Fetch a single item by id."""
    try:
        item = items_service.get_item(db, item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ItemRead.model_validate(item)


@router.get("/{item_id}/backlinks", response_model=list[ItemRead])
def get_backlinks(item_id: int, db: Session = Depends(get_db)) -> list[ItemRead]:
    """Items that link to this one using [[Title]] syntax."""
    try:
        items = items_service.get_backlinks(db, item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [ItemRead.model_validate(item) for item in items]


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)) -> ItemRead:
    """Partially update an item's fields."""
    try:
        item = items_service.update_item(db, item_id, payload)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    """Permanently delete an item."""
    try:
        items_service.delete_item(db, item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{item_id}/complete", response_model=ItemRead)
def complete_item(item_id: int, db: Session = Depends(get_db)) -> ItemRead:
    """Mark a Todo (or any item) as completed."""
    try:
        item = items_service.set_completed(db, item_id, True)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ItemRead.model_validate(item)


@router.post("/{item_id}/reopen", response_model=ItemRead)
def reopen_item(item_id: int, db: Session = Depends(get_db)) -> ItemRead:
    """Mark a completed item as not completed."""
    try:
        item = items_service.set_completed(db, item_id, False)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ItemRead.model_validate(item)


@router.post("/{item_id}/convert", response_model=ItemRead)
def convert_item(item_id: int, db: Session = Depends(get_db)) -> ItemRead:
    """Flip an item between TODO and NOTE."""
    try:
        item = items_service.convert_item(db, item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ItemRead.model_validate(item)
