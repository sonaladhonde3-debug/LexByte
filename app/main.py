from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import router

load_dotenv()


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logging.getLogger(__name__).info("AI Tax Assistant starting up")
    yield
    logging.getLogger(__name__).info("AI Tax Assistant shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Tax Assistant",
        version=os.getenv("APP_VERSION", "0.1.0"),
        description="RAG-backed Indian Income Tax assistant built with FastAPI and OpenAI.",
        lifespan=lifespan,
    )

    allowed_origins = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory="app/ui"), name="static")
    app.include_router(router)
    return app


app = create_app()
