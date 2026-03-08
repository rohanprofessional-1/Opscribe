import os
import sys
import uuid
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, create_engine, select
from apps.api.models import Client, User
from apps.api.database import DATABASE_URL

engine = create_engine(DATABASE_URL)

def create_test_account():
    with Session(engine) as session:
        # Check if test client exists
        test_domain = "dev.test"
        existing_client = session.exec(select(Client).where(Client.sso_domain == test_domain)).first()
        
        if existing_client:
            print(f"Test client already exists: {existing_client.id}")
            return
        
        print("Creating test account...")
        
        test_client = Client(
            name="Developer Test Corp",
            sso_domain=test_domain,
            sso_enabled=True,
            metadata_={"test": True}
        )
        session.add(test_client)
        session.flush() # Get ID
        
        test_user = User(
            email="dev@dev.test",
            full_name="Opscribe Developer",
            client_id=test_client.id
        )
        session.add(test_user)
        session.commit()
        
        print(f"Test Client ID: {test_client.id}")
        print(f"Test User Email: dev@dev.test")
        print("Successfully created test account.")

if __name__ == "__main__":
    create_test_account()
