from sqlalchemy import create_engine, inspect, text
import os

# Connect to localhost:5432 (local Postgres)
DATABASE_URL = "postgresql://user:password@localhost:5432/opscribe"
engine = create_engine(DATABASE_URL)

def show_schema_and_data():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"--- Database Schema for {DATABASE_URL} ---")
    print(f"Tables found: {tables}\n")
    
    with engine.connect() as conn:
        for table in tables:
            print(f"=== Table: {table} ===")
            columns = inspector.get_columns(table)
            print("Columns:")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
                
            # Show first 3 rows
            print("\nData (first 3 rows):")
            try:
                result = conn.execute(text(f"SELECT * FROM \"{table}\" LIMIT 3"))
                rows = result.fetchall()
                if rows:
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("  (Empty)")
            except Exception as e:
                print(f"  Error reading data: {e}")
            print("\n" + "-"*30 + "\n")

if __name__ == "__main__":
    show_schema_and_data()
