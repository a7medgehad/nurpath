from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.db import init_db
from app.services.catalog import seed_catalog_to_db

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
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
