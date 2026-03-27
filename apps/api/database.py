from typing import Generator, Optional
from sqlmodel import Session, create_engine
from sqlalchemy.orm import sessionmaker
from apps.api.repository import ClientRepository
from fastapi import Depends
import os
from uuid import UUID

# Use a default fallback for development if env var is not set
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@127.0.0.1:5433/opscribe")

engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Generator[Session, None, None]:
    if os.getenv("MOCK_DEMO") == "true":
        yield None
        return
    with Session(engine) as session:
        yield session

def get_repo(session: Optional[Session] = Depends(get_session)):
    """FastAPI dependency for the ClientRepository."""
    return ClientRepository(session)

def create_db_and_tables():
    if os.getenv("MOCK_DEMO") == "true":
        print("MOCK_DEMO=true: Skipping database/table creation.")
        return
        
    from . import models  # Import models to register them with SQLModel
    from apps.api.ai_infrastructure.rag import models as rag_models  # Import RAG models for table creation
    from sqlmodel import SQLModel, text
    
    # Ensure the pgvector extension is enabled before creating tables
    # We must use AUTOCOMMIT so a failure here doesn't abort a surrounding transaction
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            # Typically fails if user is not superuser, but vector is built into the ankane image
            print(f"Skipping vector extension creation: {e}")
            
    # Table creation is now handled automatically by Alembic migrations on startup
    pass