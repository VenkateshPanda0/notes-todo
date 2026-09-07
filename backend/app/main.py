from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service health for local checks and deployment probes."""
    return {"status": "ok"}
