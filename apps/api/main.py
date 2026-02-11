from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load resources
    print("Starting Opscribe API...")
    yield
    # Clean up resources
    print("Shutting down Opscribe API...")

app = FastAPI(
    title="Opscribe API",
    description="Backend for Opscribe Infrastructure Knowledge Platform",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "opscribe-api"}

@app.get("/")
async def root():
    return {"message": "Welcome to Opscribe API"}
