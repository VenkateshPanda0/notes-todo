import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api.ai import router as ai_router
from .api.auth import router as auth_router
from .api.graph import router as graph_router
from .api.items import router as items_router
from .api.tags import router as tags_router
from .db.session import init_database
from .services.ai import AIDisabledError, AIUnavailableError
from .spa import SPAStaticFiles


def resolve_frontend_dist() -> str:
    """Locate the built frontend, whether running from source or a PyInstaller bundle."""
    if getattr(sys, "_MEIPASS", None):
        # Running from a PyInstaller-built exe: files are unpacked to a temp dir.
        return os.path.join(sys._MEIPASS, "frontend", "dist")
    # Running from source: backend/app/main.py -> ../../frontend/dist
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize local persistence before the application serves requests."""
    init_database()
    yield


app = FastAPI(
    title="Flow API",
    version="0.1.0",
    description="API for the Flow personal notes and todo application.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AIDisabledError)
async def _ai_disabled(_: Request, exc: AIDisabledError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(AIUnavailableError)
async def _ai_unavailable(_: Request, exc: AIUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service health for local checks and deployment probes."""
    return {"status": "ok"}


app.include_router(items_router)
app.include_router(tags_router)
app.include_router(graph_router)
app.include_router(ai_router)
app.include_router(auth_router)

# Serve the built React frontend. Mounted last so it never shadows /api/* or /health.
FRONTEND_DIST = resolve_frontend_dist()
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
