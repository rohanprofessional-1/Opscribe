# Opscribe

Opscribe is an infrastructure knowledge platform that allows architects to diagram their systems and uses RAG to provide explanations to stakeholders.

## Project Structure

- `apps/web`: Frontend (Vite + React + TailwindCSS + React Flow)
- `apps/api`: Backend (FastAPI + SQLModel + pgvector)
- `packages/*`: Shared internal packages

## Prerequisites

- Node.js (v18+)
- Python (v3.10+)
- PostgreSQL (with `pgvector` extension)

## Getting Started

### 1. Install Dependencies

**Frontend & Shared Packages:**
```bash
npm install
```

**Backend:**
```bash
# Create virtual environment
python3 -m venv apps/api/venv

# Activate virtual environment
source apps/api/venv/bin/activate

# Install requirements
pip install -r apps/api/requirements.txt
```

### 2. Running the Application

**Run Everything (Frontend + Backend):**
```bash
# Ensure venv is created first
npm run dev
```

**Or Run Separately:**

**Frontend:**
```bash
npm run dev:web
# Opens at http://localhost:5173
```

**Backend:**
```bash
# Ensure venv is active
source apps/api/venv/bin/activate

npm run dev:api
# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Development

- **Database**: Ensure you have a Postgres instance running. Update `.env` in `apps/api` (create if needed) with `DATABASE_URL`.
- **Migrations**: Use `alembic` for database migrations (setup pending).