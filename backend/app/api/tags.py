from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..schemas.item import TagCount
from ..services import items as items_service
from .deps import get_db, require_unlocked

router = APIRouter(prefix="/api/tags", tags=["tags"], dependencies=[Depends(require_unlocked)])


@router.get("", response_model=list[TagCount])
def list_tags(db: Session = Depends(get_db)) -> list[TagCount]:
    """Every tag currently in use, with how many items carry it."""
    return [TagCount(name=name, count=count) for name, count in items_service.list_tags(db)]
