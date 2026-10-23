from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.item import Item, ItemType
from ..models.tag import Tag, item_tags
from ..schemas.item import ItemCreate, ItemUpdate
from .recurrence import anchor_for, next_due_date


class ItemNotFoundError(Exception):
    """Raised when an item lookup by id fails."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__(f"Item {item_id} not found")


TRASH_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)  # a function so tests can pin "now"


def _today() -> date:
    return date.today()  # a function so tests can pin "today"


def _spawn_next_occurrence(db: Session, item: Item) -> Item | None:
    """When a repeating todo is completed, create the next one. Returns it, or None if not needed."""
    if not item.recurrence or item.item_type != ItemType.TODO:
        return None
    due = next_due_date(item.due_date, item.recurrence, item.recurrence_day, _today())
    # Reopening and completing the same task again must not pile up copies of the same occurrence.
    already_there = db.execute(
        select(Item.id).where(
            Item.item_type == ItemType.TODO,
            Item.completed.is_(False),
            Item.deleted_at.is_(None),
            Item.title == item.title,
            Item.recurrence == item.recurrence,
            Item.due_date == due,
        )
    ).first()
    if already_there:
        return None
    following = Item(
        title=item.title,
        content=item.content,
        item_type=ItemType.TODO,
        priority=item.priority,
        due_date=due,
        recurrence=item.recurrence,
        recurrence_day=item.recurrence_day,
        tags=list(item.tags),
    )
    db.add(following)
    return following


def _resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    """Return Tag rows for already-normalized names, creating any that don't exist yet."""
    if not names:
        return []
    existing = {t.name: t for t in db.execute(select(Tag).where(Tag.name.in_(names))).scalars()}
    tags = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    return tags


def create_item(db: Session, payload: ItemCreate) -> Item:
    """Persist a new item with an explicit, caller-provided type."""
    item = Item(
        title=payload.title,
        content=payload.content,
        item_type=payload.item_type,
        priority=payload.priority,
        due_date=payload.due_date,
        recurrence=payload.recurrence,
        recurrence_day=anchor_for(payload.due_date, payload.recurrence),
        tags=_resolve_tags(db, payload.tags),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(
    db: Session,
    item_type: ItemType | None = None,
    completed: bool | None = None,
    tag: str | None = None,
) -> list[Item]:
    """Return items, optionally filtered by type, completion state and/or tag."""
    stmt = select(Item).where(Item.deleted_at.is_(None)).order_by(Item.created_at.desc())
    if tag is not None:
        stmt = stmt.where(Item.tags.any(Tag.name == tag.strip().lstrip("#").lower()))
    if item_type is not None:
        stmt = stmt.where(Item.item_type == item_type)
    if completed is not None:
        stmt = stmt.where(Item.completed == completed)
    return list(db.execute(stmt).scalars().all())


def get_item(db: Session, item_id: int, *, include_deleted: bool = False) -> Item:
    """Fetch a single item by id or raise ItemNotFoundError. Trashed items count as missing."""
    item = db.get(Item, item_id)
    if item is None or (item.deleted_at is not None and not include_deleted):
        raise ItemNotFoundError(item_id)
    return item


def update_item(db: Session, item_id: int, payload: ItemUpdate) -> Item:
    """Apply a partial update to an existing item."""
    item = get_item(db, item_id)
    updates = payload.model_dump(exclude_unset=True, by_alias=False)
    tag_names = updates.pop("tags", None)
    was_completed = item.completed
    for field, value in updates.items():
        setattr(item, field, value)
    if tag_names is not None:
        item.tags = _resolve_tags(db, tag_names)

    if item.item_type != ItemType.TODO:
        if updates.get("recurrence"):
            db.rollback()
            raise ValueError("Only todos can repeat.")
        item.recurrence = None
        item.recurrence_day = None
    elif "recurrence" in updates or "due_date" in updates:
        item.recurrence_day = anchor_for(item.due_date, item.recurrence)
    if item.completed and not was_completed:
        _spawn_next_occurrence(db, item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int) -> None:
    """Move an item to the Trash. It can be restored for TRASH_DAYS."""
    item = get_item(db, item_id)
    item.deleted_at = _now()
    db.commit()


def list_trash(db: Session) -> list[Item]:
    """Trashed items, most recently deleted first."""
    stmt = select(Item).where(Item.deleted_at.is_not(None)).order_by(Item.deleted_at.desc(), Item.id.desc())
    return list(db.execute(stmt).scalars().all())


def restore_item(db: Session, item_id: int) -> Item:
    """Bring an item back from the Trash."""
    item = get_item(db, item_id, include_deleted=True)
    if item.deleted_at is None:
        raise ItemNotFoundError(item_id)  # nothing to restore
    item.deleted_at = None
    db.commit()
    db.refresh(item)
    return item


def purge_item(db: Session, item_id: int) -> None:
    """Delete an item that is already in the Trash for good."""
    item = get_item(db, item_id, include_deleted=True)
    if item.deleted_at is None:
        raise ItemNotFoundError(item_id)  # only trashed items can be purged this way
    db.delete(item)
    db.commit()


def empty_trash(db: Session) -> int:
    """Permanently delete everything in the Trash. Returns how many items went."""
    items = list_trash(db)
    for item in items:
        db.delete(item)
    db.commit()
    return len(items)


def purge_expired_trash(db: Session, days: int = TRASH_DAYS) -> int:
    """Permanently delete items that have been in the Trash longer than `days`."""
    cutoff = _now() - timedelta(days=days)
    expired = [i for i in list_trash(db) if _aware(i.deleted_at) < cutoff]
    for item in expired:
        db.delete(item)
    db.commit()
    return len(expired)


def _aware(value: datetime) -> datetime:
    """SQLite hands datetimes back without a timezone; ours are always UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def set_completed(db: Session, item_id: int, completed: bool) -> Item:
    """Mark a Todo as completed or reopen it."""
    item = get_item(db, item_id)
    if completed and not item.completed:
        _spawn_next_occurrence(db, item)
    item.completed = completed
    db.commit()
    db.refresh(item)
    return item


def convert_item(db: Session, item_id: int) -> Item:
    """Flip an item's type between TODO and NOTE."""
    item = get_item(db, item_id)
    item.item_type = ItemType.NOTE if item.item_type == ItemType.TODO else ItemType.TODO
    if item.item_type == ItemType.NOTE:  # notes can't repeat
        item.recurrence = None
        item.recurrence_day = None
    db.commit()
    db.refresh(item)
    return item


def list_tags(db: Session) -> list[tuple[str, int]]:
    """Return (name, item_count) for every tag that is in use, alphabetically."""
    rows = db.execute(
        select(Tag.name, func.count(item_tags.c.item_id))
        .join(item_tags, item_tags.c.tag_id == Tag.id)
        .join(Item, Item.id == item_tags.c.item_id)
        .where(Item.deleted_at.is_(None))
        .group_by(Tag.id)
        .order_by(Tag.name)
    ).all()
    return [(name, count) for name, count in rows]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_backlinks(db: Session, item_id: int) -> list[Item]:
    """Items whose content links to this item's title with [[Title]] or [[Title|label]].

    Matching is case-insensitive for ASCII letters only (a SQLite limitation of lower()/LIKE).
    """
    item = get_item(db, item_id)
    needle = _escape_like(item.title.lower())
    content = func.lower(Item.content)
    stmt = (
        select(Item)
        .where(Item.id != item.id, Item.deleted_at.is_(None))
        .where(
            content.like(f"%[[{needle}]]%", escape="\\")
            | content.like(f"%[[{needle}|%", escape="\\")
        )
        .order_by(Item.updated_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
