import os
import re
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    from backend.db.base import Base
except ImportError:
    from db.base import Base

# Load environment variables: prioritize project root .env as single source of truth
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, ".."))
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))

_root_env = os.path.join(_root_dir, ".env")
_backend_env = os.path.join(_backend_dir, ".env")

if os.path.exists(_root_env):
    load_dotenv(dotenv_path=_root_env, override=True)
elif os.path.exists(_backend_env):
    load_dotenv(dotenv_path=_backend_env, override=True)
else:
    load_dotenv(override=True)

class DatabaseConfigurationError(RuntimeError):
    """Raised when database configuration is invalid or missing required parameters."""
    pass

def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL connection strings from various cloud providers
    (Neon, Supabase, AWS RDS, GCP Cloud SQL, Render, Railway, Heroku)
    into SQLAlchemy 2.0 + psycopg 3 compatible format: 'postgresql+psycopg://...'
    """
    if not url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is missing or empty. "
            "RailVyuha requires a PostgreSQL connection string. "
            "Please configure DATABASE_URL in backend/.env or your environment variables. "
            "Example: postgresql+psycopg://user:password@host:5432/railvyuha"
        )

    # Replace legacy postgres:// or postgresql:// without driver
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    # Ensure psycopg driver is explicitly specified for postgresql schemes
    if url.startswith("postgresql+pg8000://") or url.startswith("postgresql+psycopg2://"):
        url = re.sub(r"^postgresql\+[a-zA-Z0-9_]+://", "postgresql+psycopg://", url)

    return url

from urllib.parse import urlparse

def mask_connection_url(url: str) -> str:
    """Masks credentials in database URL for safe logging/reporting."""
    if not url:
        return ""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)

def get_sanitized_connection_info(url: str = None) -> dict:
    """
    Extracts safe connection parameters (dialect, host, port, database, username)
    without ever exposing passwords.
    """
    target_url = url or globals().get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not target_url or target_url.startswith("sqlite"):
        return {
            "dialect": "sqlite",
            "host": "in-memory" if ":memory:" in (target_url or "") else "local-file",
            "port": None,
            "database": ":memory:" if ":memory:" in (target_url or "") else "sqlite",
            "username": None,
        }
    
    parsed = urlparse(target_url)
    dialect = parsed.scheme.split("+")[0] if "+" in parsed.scheme else parsed.scheme
    return {
        "dialect": dialect,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "username": parsed.username,
    }

# Retrieve and normalize DATABASE_URL
RAW_DATABASE_URL = os.getenv("DATABASE_URL")
IS_TEST_ENV = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("APP_ENV") == "test"

if not RAW_DATABASE_URL:
    if IS_TEST_ENV:
        # In test mode, fallback is handled via conftest.py fixtures
        DATABASE_URL = "sqlite:///:memory:"
    else:
        # In production/runtime mode, default to local PostgreSQL or fail with clear instructions
        DEFAULT_LOCAL_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/railvyuha"
        DATABASE_URL = DEFAULT_LOCAL_URL
else:
    # Explicit URL provided
    if RAW_DATABASE_URL.startswith("sqlite") and not IS_TEST_ENV:
        # Reject silent SQLite fallback in production/application runtime
        raise DatabaseConfigurationError(
            "SQLite is NOT permitted as the production/application database for RailVyuha. "
            "RailVyuha must run on PostgreSQL + PostGIS. "
            "SQLite is only allowed in isolated pytest test fixtures."
        )
    DATABASE_URL = normalize_database_url(RAW_DATABASE_URL)

# Connect args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "6543" in DATABASE_URL or "pooler" in DATABASE_URL:
    # Disable prepared statements for PgBouncer transaction mode
    connect_args = {"prepare_threshold": None}

# Engine initialization
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() in ("true", "1", "yes"),
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes the database schema."""
    Base.metadata.create_all(bind=engine)
