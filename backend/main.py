"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
import backend.models  # noqa: F401 — ensure all ORM models are registered
from backend.routers import (
    health_router,
    jobs_router,
    seniority_router,
    summary_router,
    technologies_router,
)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JobFinding API",
    description="API for JobFinding — labor market intelligence platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(summary_router, prefix="/api/v1")
app.include_router(technologies_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(seniority_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "JobFinding API",
        "version": "1.0.0",
        "docs": "/docs",
    }