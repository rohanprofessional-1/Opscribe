from typing import Generator
from sqlmodel import Session, create_engine
import os

# Use a default fallback for development if env var is not set
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/opscribe")

engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    from . import models  # Import models to register them with SQLModel
    from sqlmodel import SQLModel, text
    
    # Ensure the pgvector extension is enabled before creating tables
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            # Typically fails if user is not superuser, but vector is built into the ankane image
            print(f"Skipping vector extension creation: {e}")
            
    # Table creation is now handled automatically by Alembic migrations on startup
