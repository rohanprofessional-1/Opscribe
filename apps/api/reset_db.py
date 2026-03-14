from apps.api.database import engine, create_db_and_tables
from sqlalchemy import text

with engine.connect() as con:
    con.execute(text('DROP SCHEMA public CASCADE;'))
    con.execute(text('CREATE SCHEMA public;'))
    con.execute(text('GRANT ALL ON SCHEMA public TO public;'))
    con.commit()

create_db_and_tables()
print("Database schema dropped and recreated successfully.")
