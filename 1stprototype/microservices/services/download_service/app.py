import asyncio
import os

from fastapi import FastAPI

app = FastAPI(title="download-service")

DOWNLOAD_COUNT = 0
SERVICE_DELAY_SECONDS = float(os.getenv("SERVICE_DELAY_SECONDS", "0.15"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/download")
async def download_game() -> dict[str, int | str]:
    global DOWNLOAD_COUNT
    await asyncio.sleep(SERVICE_DELAY_SECONDS)
    DOWNLOAD_COUNT += 1
    return {"status": "ok", "downloads": DOWNLOAD_COUNT}


@app.get("/stats")
async def stats() -> dict[str, int]:
    return {"downloads": DOWNLOAD_COUNT}
