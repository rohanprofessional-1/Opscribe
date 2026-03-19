# Opscribe Database Migrations

This folder contains the Alembic configuration and migration scripts for the Opscribe API database.

Opscribe is configured to **automatically apply pending migrations on startup**. When you run the FastAPI server, it will always execute `alembic upgrade head` before accepting traffic.

## How to Make Schema Changes

When you need to modify the database schema (e.g., adding a new table, adding a column to an existing `SQLModel`, or removing a column), follow these steps:

### 1. Update the Models
Make your changes to the Python classes in `apps/api/models.py`.

### 2. Auto-Generate a Migration Script
Run the following command from the root of the repository to generate a new migration script based on your changes:

```bash
cd apps/api
PYTHONPATH=.. venv/bin/alembic revision --autogenerate -m "Description of your changes"
```

Alembic will compare your `models.py` definitions to the current state of your local database and output a new python file in the `alembic/versions/` directory.

### 3. Review the Script
Always briefly open the newly generated script in `apps/api/alembic/versions/` to verify that Alembic correctly interpreted your changes. 
*Note: Alembic is very good, but sometimes complex operations like renaming a column might be interpreted as a "drop" and "add" instead of an "alter".*

### 4. Restart the Server
Once the migration script is generated, simply restart your local dev server.
Because of the startup hook in `main.py`, the server will automatically run the new migration against your local postgres instance.

If you don't want to restart the server, you can apply it manually:
```bash
cd apps/api
PYTHONPATH=.. venv/bin/alembic upgrade head
```

---

## Troubleshooting

### "Table already exists" or "Out of sync"
If you switch branches frequently, your local database might have tables or columns that don't match the migration history of your current branch.

If you get stuck and just want to reset your local database to a clean state matching the current branch, run:
```bash
PYTHONPATH=. apps/api/venv/bin/python apps/api/reset_db.py
```
This will drop everything. When you restart the API server, Alembic will rebuild the entire schema from scratch.
