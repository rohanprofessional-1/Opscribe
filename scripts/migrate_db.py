import os
import sys
from sqlalchemy import create_engine, text

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.api.database import DATABASE_URL

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Migrating database...")
        
        # Add columns to client table if they don't exist
        try:
            conn.execute(text("ALTER TABLE client ADD COLUMN sso_domain VARCHAR"))
            print("Added sso_domain to client")
        except Exception as e:
            print(f"sso_domain already exists or error: {e}")
            
        try:
            conn.execute(text("ALTER TABLE client ADD COLUMN sso_enabled BOOLEAN DEFAULT FALSE"))
            print("Added sso_enabled to client")
        except Exception as e:
            print(f"sso_enabled already exists or error: {e}")
            
        try:
            conn.execute(text("ALTER TABLE client ADD COLUMN sso_provider_id VARCHAR"))
            print("Added sso_provider_id to client")
        except Exception as e:
            print(f"sso_provider_id already exists or error: {e}")
            
        # Create user table if it doesn't exist
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS op_user (
                    id UUID PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    full_name VARCHAR NOT NULL,
                    client_id UUID NOT NULL REFERENCES client(id) ON DELETE CASCADE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Created op_user table")
        except Exception as e:
            print(f"Error creating op_user table: {e}")
            
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
