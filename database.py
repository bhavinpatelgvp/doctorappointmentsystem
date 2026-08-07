"""
Database abstraction layer.

Provides the SQLAlchemy engine, session factory, and a helper to create
all tables. Uses parameterized queries/ORM throughout the application.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

# Detect SQLite to enable foreign key enforcement.
_IS_SQLITE = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if _IS_SQLITE else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)


if _IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """Yield a database session for dependency-style usage."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the database."""
    # Import models so they are registered on Base.metadata.
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_session():
    """Return a new database session (non-generator variant)."""
    return SessionLocal()
