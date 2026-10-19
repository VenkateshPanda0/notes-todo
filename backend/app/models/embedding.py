from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class ItemEmbedding(Base):
    """A cached embedding vector for an item, used to find related notes.

    `text_hash` covers the exact text that was embedded and `model` the embedding model, so a
    changed note or a different model simply triggers a re-embed.
    """

    __tablename__ = "item_embeddings"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of floats
