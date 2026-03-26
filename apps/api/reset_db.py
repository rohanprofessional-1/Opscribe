import os
import sys
import shutil

# Add the project root to the python path so 'apps' can be resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlmodel import SQLModel
from sqlalchemy import text
from apps.api.database import engine

def reset():
    """
    Wipes the entire Postgres schema and recreates it fresh.
    Migration files are intentionally left intact — the API applies them
    automatically on the next startup via Alembic.

    Usage:
        python3 -m apps.api.reset_db

    After running, restart the API server. Alembic will rebuild all tables.
    """
    with engine.connect() as conn:
        print("Dropping public schema...")
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()

        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except Exception as e:
            print(f"Skipping vector extension (may need superuser): {e}")

    print()
    print("✅ Schema wiped. Migration files left intact.")
    print("   → Restart the API server — Alembic will rebuild all tables automatically.")

if __name__ == "__main__":
    reset()
