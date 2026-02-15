from fastapi import FastAPI
from contextlib import asynccontextmanager
from apps.api.database import create_db_and_tables
from apps.api.routers import clients, graphs, nodes, edges

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load resources
    print("Starting Opscribe API...")
    create_db_and_tables()
    yield
    # Clean up resources
    print("Shutting down Opscribe API...")

app = FastAPI(
    title="Opscribe API",
    description="Backend for Opscribe Infrastructure Knowledge Platform",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(clients.router)
app.include_router(graphs.router)
app.include_router(nodes.router)
app.include_router(edges.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "opscribe-api"}

@app.get("/")
async def root():
    return {"message": "Welcome to Opscribe API"}
