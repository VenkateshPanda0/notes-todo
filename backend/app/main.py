from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.items import router as items_router
from .db.session import init_database


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


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service health for local checks and deployment probes."""
    return {"status": "ok"}


app.include_router(items_router)
app.include_router(auth_router)
