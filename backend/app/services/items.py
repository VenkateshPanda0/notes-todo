from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.item import Item, ItemType
from ..schemas.item import ItemCreate, ItemUpdate


class ItemNotFoundError(Exception):
    """Raised when an item lookup by id fails."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__(f"Item {item_id} not found")


def create_item(db: Session, payload: ItemCreate) -> Item:
    """Persist a new item with an explicit, caller-provided type."""
    item = Item(
        title=payload.title,
        content=payload.content,
        item_type=payload.item_type,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(
    db: Session,
    item_type: ItemType | None = None,
    completed: bool | None = None,
) -> list[Item]:
    """Return items, optionally filtered by type and/or completion state."""
    stmt = select(Item).order_by(Item.created_at.desc())
    if item_type is not None:
        stmt = stmt.where(Item.item_type == item_type)
    if completed is not None:
        stmt = stmt.where(Item.completed == completed)
    return list(db.execute(stmt).scalars().all())


def get_item(db: Session, item_id: int) -> Item:
    """Fetch a single item by id or raise ItemNotFoundError."""
    item = db.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError(item_id)
    return item


def update_item(db: Session, item_id: int, payload: ItemUpdate) -> Item:
    """Apply a partial update to an existing item."""
    item = get_item(db, item_id)
    updates = payload.model_dump(exclude_unset=True, by_alias=False)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int) -> None:
    """Remove an item permanently."""
    item = get_item(db, item_id)
    db.delete(item)
    db.commit()


def set_completed(db: Session, item_id: int, completed: bool) -> Item:
    """Mark a Todo as completed or reopen it."""
    item = get_item(db, item_id)
    item.completed = completed
    db.commit()
    db.refresh(item)
    return item


def convert_item(db: Session, item_id: int) -> Item:
    """Flip an item's type between TODO and NOTE."""
    item = get_item(db, item_id)
    item.item_type = ItemType.NOTE if item.item_type == ItemType.TODO else ItemType.TODO
    db.commit()
    db.refresh(item)
    return item
