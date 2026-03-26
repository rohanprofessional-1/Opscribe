from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
from dotenv import dotenv_values
from sqlmodel import SQLModel, text

# Import models to ensure they are registered in the metadata
from apps.api import models
from apps.api.ai_infrastructure.rag import models as rag_models

# Load environment variables
# Use the directory of this file to find the .env in apps/api/
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
envvars = dotenv_values(os.path.join(api_dir, ".env"))
database_url = envvars.get("DATABASE_URL") or os.environ.get("DATABASE_URL", "postgresql://user:password@127.0.0.1:5433/opscribe")
print(f"DEBUG: Alembic using database_url={database_url}")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Overwrite the ini-file sqlalchemy.url with the environment variable
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure public is in search path so vector type is found
        connection.execute(text('SET search_path TO public, "$user"'))
        
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
