from typing import Generator
from sqlmodel import Session, create_engine
import os
from uuid import UUID

# Use a default fallback for development if env var is not set
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@127.0.0.1:5433/opscribe")

engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    from . import models  # Import models to register them with SQLModel
    from apps.api.infrastructure.rag import models as rag_models  # Import RAG models for table creation
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


# Added for local testing
def seed_dev_data():
    """Initializes the database with a default developer client and organization for local testing."""
    from apps.api.models import Client, Graph
    from apps.api.routers.clients import DEV_USER_ID
    from sqlmodel import Session, select
    
    with Session(engine) as session:
        # Seed both the all-zeros ID and the common RFC 4122 example ID
        dev_ids = [
            DEV_USER_ID,
            UUID("123e4567-e89b-12d3-a456-426614174000") # RFC 4122 example
        ]

        for cid in dev_ids:
            # 1. Ensure the developer client exists
            client = session.get(Client, cid)
            if not client:
                print(f"Seeding Developer Client with ID: {cid}")
                client = Client(
                    id=cid,
                    name=f"Dev User ({str(cid)[:8]})",  # type: ignore
                    metadata_={"role": "admin", "temporary_auth": True},
                )
                session.add(client)
                session.commit()
                session.refresh(client)
            
            # 2. Ensure a default graph exists for this client
            graph = session.exec(select(Graph).where(Graph.client_id == cid)).first()
            if not graph:
                print(f"Seeding Default Infrastructure Graph for Client: {cid}")
                graph = Graph(
                    client_id=cid,
                    name="Infrastructure Design",
                    description="Default workspace created by the system.",
                )
                session.add(graph)
                session.commit()
