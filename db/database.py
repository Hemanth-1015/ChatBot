import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

load_dotenv()

# Use SQLite for easy local testing (change to PostgreSQL in production)
DEFAULT_DB_URL = "sqlite:///./autonomous_agent.db"

# Read DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# Failsafe: Supabase returns "postgres://" but SQLAlchemy requires "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"[INFO] Converted DATABASE_URL from postgres:// to postgresql://")

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific settings for local development
    connect_args = {"check_same_thread": False}
    engine: Engine = create_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )
else:
    # Production PostgreSQL settings with connection pooling
    # Optimized for Supabase and cloud PostgreSQL providers
    engine: Engine = create_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,           # Verify connections before use
        pool_recycle=300,             # Recycle connections after 5 minutes
        pool_size=10,                 # Maintain 10 persistent connections
        max_overflow=20,              # Allow up to 20 additional connections during peak load
        pool_timeout=30,              # Wait up to 30 seconds for available connection
        poolclass=QueuePool,          # Use queue-based connection pool
    )
    print(f"[INFO] Connected to PostgreSQL database with connection pooling (pool_size=10, max_overflow=20)")


def init_db() -> None:
    """Initialize the database by creating all tables."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    with get_db() as session:
        yield session
