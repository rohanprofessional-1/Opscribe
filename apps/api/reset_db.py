import os
import shutil
from sqlmodel import SQLModel
from sqlalchemy import text
from apps.api.database import engine
from apps.api import models

def reset():
    # 1. Clear Alembic version files and cache
    api_dir = os.path.dirname(__file__)
    versions_dir = os.path.join(api_dir, "alembic", "versions")
    if os.path.exists(versions_dir):
        for f in os.listdir(versions_dir):
            path = os.path.join(versions_dir, f)
            if f.endswith(".py"):
                print(f"Deleting migration file: {f}")
                os.remove(path)
            elif os.path.isdir(path) and f == "__pycache__":
                shutil.rmtree(path)

    # 2. Drop schema and alembic_version table
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
            print(f"Skipping vector extension creation: {e}")
            # Note: Postgres transactions fail on any error. We need to rollback if we are using an explicit transaction.
            # But here we are using autocommit or separate commits.
        
        # Double check alembic_version is gone
        try:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
            conn.commit()
        except:
            pass

    print("Database reset and migration history cleared. Ready for fresh Alembic baseline.")

if __name__ == "__main__":
    reset()
