# Phase 1 – Foundation

## Goal

Create a solid foundation so that frontend and backend can talk to each other.

## What was built

1. Complete folder structure (`NDA-Chatbot/`)
2. FastAPI backend with:
   - `/api/health` endpoint
   - CORS configuration
   - Environment-based settings (`pydantic-settings`)
3. React + TypeScript + Vite frontend with:
   - Tailwind CSS
   - Health-check page
   - Vite proxy for `/api`
4. `.env` and `.env.example` files
5. README and documentation

## How to verify

1. Start backend → open http://localhost:8000/api/health
2. Start frontend → open http://localhost:5173
3. You should see green status “Backend is Online”

## Next Phase

Phase 2 – Database models, SQLAlchemy, Alembic migrations.
