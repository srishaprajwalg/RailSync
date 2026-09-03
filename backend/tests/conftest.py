import sys
import os
import pytest

# Ensure both backend/ and project root are in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.services.seeder import seed_database
from backend.db.session import get_db
from backend.main import app

@pytest.fixture(scope="session")
def test_engine():
    """Create an isolated in-memory SQLite engine strictly for test execution."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides an isolated transactional database session with full seed data for tests."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()

    seed_database(session, force_clean=True)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def override_fastapi_db(db_session):
    """Automatically overrides FastAPI get_db dependency during test execution."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
