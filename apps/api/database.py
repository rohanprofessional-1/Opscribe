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
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
