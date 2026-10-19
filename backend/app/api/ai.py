from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..schemas.item import (
    AISettingsUpdate,
    AIStatus,
    ItemRead,
    PlanRead,
    RelatedRead,
    SummaryRead,
)
from ..services import ai_assist, ai_settings
from ..services.ai import AIUnavailableError, OllamaClient, pick_chat_model, pick_embed_model
from ..services.items import ItemNotFoundError
from .deps import get_db, require_unlocked

router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_unlocked)])


def get_ai_client() -> OllamaClient:
    """The Ollama client. Overridden in tests."""
    return OllamaClient()


def _status(db: Session, client: OllamaClient) -> AIStatus:
    settings = ai_settings.get_ai_settings(db)
    base = dict(
        enabled=settings.enabled,
        local=client.is_local,
        base_url=client.base_url,
        model=settings.model,
        embed_model=settings.embed_model,
    )
    try:
        models = client.list_models()
    except AIUnavailableError as exc:
        return AIStatus(
            available=False,
            models=[],
            chat_model_ready=False,
            embed_model_ready=False,
            error=str(exc),
            **base,
        )
    return AIStatus(
        available=True,
        models=models,
        chat_model_ready=pick_chat_model(models, settings.model) is not None,
        embed_model_ready=pick_embed_model(models, settings.embed_model) is not None,
        **base,
    )


@router.get("/status", response_model=AIStatus)
def get_status(db: Session = Depends(get_db), client: OllamaClient = Depends(get_ai_client)) -> AIStatus:
    """Settings plus a live check of the local Ollama server."""
    return _status(db, client)


@router.put("/settings", response_model=AIStatus)
def update_settings(
    payload: AISettingsUpdate,
    db: Session = Depends(get_db),
    client: OllamaClient = Depends(get_ai_client),
) -> AIStatus:
    ai_settings.update_ai_settings(
        db, enabled=payload.enabled, model=payload.model, embed_model=payload.embed_model
    )
    return _status(db, client)


@router.post("/summarize/{item_id}", response_model=SummaryRead)
def summarize(
    item_id: int, db: Session = Depends(get_db), client: OllamaClient = Depends(get_ai_client)
) -> SummaryRead:
    """Summarize a note or todo with the local model. The summary is returned, not saved."""
    try:
        summary, model = ai_assist.summarize_item(db, client, item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SummaryRead(summary=summary, model=model)


@router.post("/plan-day", response_model=PlanRead)
def plan_day(db: Session = Depends(get_db), client: OllamaClient = Depends(get_ai_client)) -> PlanRead:
    """A short plan for today from overdue, due-soon and high-priority todos."""
    plan, model, items = ai_assist.plan_day(db, client)
    return PlanRead(plan=plan, model=model, items=[ItemRead.model_validate(i) for i in items])


@router.get("/related/{item_id}", response_model=list[RelatedRead])
def related(
    item_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    client: OllamaClient = Depends(get_ai_client),
) -> list[RelatedRead]:
    """Items closest in meaning to this one, using local embeddings."""
    try:
        pairs = ai_assist.related_items(db, client, item_id, limit)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [RelatedRead(item=ItemRead.model_validate(item), score=round(score, 4)) for item, score in pairs]
