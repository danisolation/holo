from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Holo starting up...")
    yield
    # Shutdown
    await engine.dispose()
    logger.info("Holo shut down.")


app = FastAPI(
    title="Holo - Stock Intelligence",
    description="AI-powered stock analysis for HOSE",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "holo"}
