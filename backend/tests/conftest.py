import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tests start the real app lifespan, which would otherwise write ./backups next to ./flow.db.
os.environ["TASKFLOW_DISABLE_AUTO_BACKUP"] = "1"

from backend.app.api.deps import get_db
from backend.app.db.session import init_database
from backend.app.main import app
from backend.app.services import session as session_service


@pytest.fixture(autouse=True)
def reset_session_state():
    """Session tokens and attempt counters are process-wide, so isolate every test."""
    session_service.reset()
    yield
    session_service.reset()


@pytest.fixture()
def db_session_factory():
    """A fresh in-memory SQLite database per test, schema created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client(db_session_factory):
    """A TestClient wired to the isolated in-memory database via dependency override."""

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()