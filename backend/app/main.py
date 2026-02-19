import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_retriever
from app.api.routes import router
from app.core.config import settings
from app.core.db import init_db
from app.services.catalog import seed_catalog_to_db

logger = logging.getLogger("nurpath.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    profile = "local" if settings.qdrant_local_mode else "docker-first"
    logger.info(
        "Starting NurPath with profile=%s, database_url=%s, qdrant_url=%s",
        profile,
        settings.database_url,
        ":memory:" if settings.qdrant_local_mode else settings.qdrant_url,
    )
    init_db()
    retriever = get_retriever()
    diagnostics = retriever.diagnostics()
    if profile == "docker-first" and not diagnostics["qdrant_connected"]:
        raise RuntimeError("Qdrant is unreachable in docker-first mode.")
    seed_catalog_to_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version, "status": "ok"}


app.include_router(router)
