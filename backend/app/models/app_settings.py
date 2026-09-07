from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class AppSettings(Base):
    """Single-row table holding local app-lock settings.

    There is always at most one row (id=1). If no row exists, the app
    has no lock configured and opens without a password prompt.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
