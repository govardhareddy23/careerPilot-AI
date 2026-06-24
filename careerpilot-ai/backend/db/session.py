"""
Database session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import get_settings
from backend.db.models import Base

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables. Call once on startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency - yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
