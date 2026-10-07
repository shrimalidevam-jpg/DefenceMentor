from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.api.routes import assessment, auth, chat, curriculum, daily_growth, daily_review, diagnostic, health, learning, mastery, rag, ssb_guidance, study_planner, tutorials
from app.services.parent_progress_reports import start_parent_report_scheduler, stop_parent_report_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_parent_report_scheduler()
    try:
        yield
    finally:
        stop_parent_report_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    description="NDA Chatbot: An AI-Driven Adaptive Learning and Assessment Platform",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# CORS middleware – allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(curriculum.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(diagnostic.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(mastery.router, prefix="/api")
app.include_router(assessment.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(tutorials.router, prefix="/api")
app.include_router(tutorials.admin_router, prefix="/api")
app.include_router(study_planner.router, prefix="/api")
app.include_router(daily_review.router, prefix="/api")
app.include_router(daily_growth.router, prefix="/api")
app.include_router(ssb_guidance.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint – simple welcome message."""
    return {
        "message": "Welcome to NDA Chatbot API",
        "docs": "/docs",
        "health": "/api/health"
    }
