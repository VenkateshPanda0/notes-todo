from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..schemas.item import GraphEdgeRead, GraphNodeRead, GraphRead
from ..services.graph import build_graph
from .deps import get_db, require_unlocked

router = APIRouter(prefix="/api/graph", tags=["graph"], dependencies=[Depends(require_unlocked)])


@router.get("", response_model=GraphRead, response_model_by_alias=True)
def get_graph(db: Session = Depends(get_db)) -> GraphRead:
    """Items as nodes and [[wiki-links]] between them as edges."""
    graph = build_graph(db)
    return GraphRead(
        nodes=[
            GraphNodeRead(
                key=n.key,
                id=n.id,
                title=n.title,
                item_type=n.item_type,
                completed=n.completed,
                tags=n.tags,
                missing=n.missing,
                degree=n.degree,
            )
            for n in graph.nodes
        ],
        edges=[GraphEdgeRead(source=s, target=t) for s, t in graph.edges],
    )
