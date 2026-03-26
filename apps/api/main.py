from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load .env file automatically
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from apps.api.database import create_db_and_tables
from apps.api.routers import clients, graphs, nodes, edges, discovery, github, pipeline, admin, rag
from apps.api.routers.admin import bootstrap_github_app_from_env
from alembic.config import Config
from alembic import command

def run_migrations():
    print("Running database migrations...")
    api_dir = os.path.dirname(__file__)
    alembic_ini_path = os.path.join(api_dir, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(api_dir, "alembic"))
    try:
        command.upgrade(alembic_cfg, "head")
        print("Database migrations applied successfully.")
    except Exception as e:
        print(f"Error running database migrations: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load resources
    print("Starting Opscribe API...")
    create_db_and_tables()
    run_migrations()
    # Seed GitHub App credentials from env into DB on first boot
    from sqlmodel import Session
    from apps.api.database import engine
    with Session(engine) as session:
        bootstrap_github_app_from_env(session)
    yield
    # Clean up resources
    print("Shutting down Opscribe API...")

app = FastAPI(
    title="Opscribe API",
    description="Backend for Opscribe Infrastructure Knowledge Platform",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from apps.api.routers import clients, graphs, nodes, edges, discovery, github, pipeline, admin, integrations

app.include_router(clients.router)
app.include_router(graphs.router)
app.include_router(nodes.router)
app.include_router(edges.router)
app.include_router(github.router)
app.include_router(discovery.router)
app.include_router(pipeline.router)
app.include_router(admin.router)
app.include_router(integrations.router)
app.include_router(rag.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "opscribe-api"}

@app.get("/")
async def root():
    return {"message": "Welcome to Opscribe API"}
