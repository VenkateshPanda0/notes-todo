"""Build a link graph from [[wiki-links]] across all items."""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.item import Item

_WIKI_LINK = re.compile(r"\[\[([^\[\]|\n]+?)(?:\|[^\[\]\n]+?)?\]\]")
_FENCED_CODE = re.compile(r"(```|~~~).*?\1", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")


def normalize_title(title: str) -> str:
    return title.strip().lower()


def extract_links(content: str) -> list[str]:
    """Titles linked with [[Title]] or [[Title|label]], in order, ignoring links inside code."""
    text = _INLINE_CODE.sub("", _FENCED_CODE.sub("", content))
    seen: list[str] = []
    for match in _WIKI_LINK.finditer(text):
        title = match.group(1).strip()
        if title and normalize_title(title) not in {normalize_title(t) for t in seen}:
            seen.append(title)
    return seen


@dataclass
class GraphNode:
    key: str
    title: str
    id: int | None = None
    item_type: str | None = None
    completed: bool = False
    tags: list[str] = field(default_factory=list)
    missing: bool = False
    degree: int = 0


@dataclass
class Graph:
    nodes: list[GraphNode]
    edges: list[tuple[str, str]]


def build_graph(db: Session) -> Graph:
    """Every item becomes a node; each [[link]] becomes a directed edge.

    Links to titles that don't exist yet become "missing" placeholder nodes. When several items
    share a title, links resolve to the oldest one.
    """
    items = list(db.execute(select(Item).where(Item.deleted_at.is_(None)).order_by(Item.id)).scalars().all())

    nodes: dict[str, GraphNode] = {}
    by_title: dict[str, str] = {}
    for item in items:
        key = f"item:{item.id}"
        nodes[key] = GraphNode(
            key=key,
            id=item.id,
            title=item.title,
            item_type=item.item_type.value,
            completed=item.completed,
            tags=[t.name for t in item.tags],
        )
        by_title.setdefault(normalize_title(item.title), key)

    edges: list[tuple[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for item in items:
        source = f"item:{item.id}"
        for title in extract_links(item.content):
            target = by_title.get(normalize_title(title))
            if target is None:
                target = f"missing:{normalize_title(title)}"
                nodes.setdefault(target, GraphNode(key=target, title=title, missing=True))
                by_title[normalize_title(title)] = target
            if target == source or (source, target) in seen_edges:
                continue
            seen_edges.add((source, target))
            edges.append((source, target))
            nodes[source].degree += 1
            nodes[target].degree += 1

    return Graph(nodes=list(nodes.values()), edges=edges)
