from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models.setting import Setting

_ENABLED = "ai_enabled"
_MODEL = "ai_model"
_EMBED_MODEL = "ai_embed_model"


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False
    model: str = ""
    embed_model: str = ""


def _get(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value


def get_ai_settings(db: Session) -> AISettings:
    return AISettings(
        enabled=_get(db, _ENABLED) == "1",
        model=_get(db, _MODEL),
        embed_model=_get(db, _EMBED_MODEL),
    )


def update_ai_settings(
    db: Session,
    *,
    enabled: bool | None = None,
    model: str | None = None,
    embed_model: str | None = None,
) -> AISettings:
    """Update only the fields that are provided."""
    if enabled is not None:
        _set(db, _ENABLED, "1" if enabled else "0")
    if model is not None:
        _set(db, _MODEL, model.strip())
    if embed_model is not None:
        _set(db, _EMBED_MODEL, embed_model.strip())
    db.commit()
    return get_ai_settings(db)
