import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlmodel import Session
from sqlalchemy import text
from apps.api.database import engine

def wipe_dev_creds():
    """Wipes the existing AWS and GitHub credentials for the dev client to simulate a NET NEW client."""
    client_id = '00000000-0000-0000-0000-000000000000'
    print(f"Blowing away integrations and repositories for client {client_id}...")
    
    with Session(engine) as session:
        # Delete AWS Integrations
        session.exec(text(f"DELETE FROM client_integration WHERE client_id = '{client_id}'"))
        # Delete GitHub Repositories
        session.exec(text(f"DELETE FROM connected_repository WHERE client_id = '{client_id}'"))
        session.commit()
        
    print("✅ Credentials wiped! Dev client is now a NET NEW client ready for selective ingestion testing.")

if __name__ == "__main__":
    wipe_dev_creds()
