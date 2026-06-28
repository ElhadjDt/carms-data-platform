"""
CARMS Residency API — FastAPI application entry point.
Registers routers for disciplines, programs, schools, sites, streams, and QA (RAG).
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

from src.api.routers import (
    disciplines,
    programs,
    schools,
    sites,
    streams,
    qa,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.qa.qa_chain import initialize
    initialize()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CARMS Residency API",
        version="1.0.0",
        description="Backend API for residency programs and QA system.",
        lifespan=lifespan,
    )

    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(disciplines.router)
    app.include_router(programs.router)
    app.include_router(schools.router)
    app.include_router(sites.router)
    app.include_router(streams.router)
    app.include_router(qa.router)

    return app


app = create_app()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}