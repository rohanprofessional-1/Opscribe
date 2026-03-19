import sys
from uuid import UUID
from sqlmodel import Session
from apps.api.database import engine, create_db_and_tables
from apps.api.models import Client

def seed():
    create_db_and_tables()
    with Session(engine) as session:
        mock_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        client = session.get(Client, mock_id)
        if not client:
            client = Client(id=mock_id, name="Test Client")
            session.add(client)
            session.commit()
            print("Seeded test client.")
        else:
            print("Test client already exists.")

if __name__ == "__main__":
    seed()
