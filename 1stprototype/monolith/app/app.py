import asyncio
import os

from fastapi import FastAPI

app = FastAPI(title="game-platform-monolith")

PURCHASE_COUNT = 0
DOWNLOAD_COUNT = 0

PURCHASE_DELAY_SECONDS = float(os.getenv("PURCHASE_DELAY_SECONDS", "0.15"))
DOWNLOAD_DELAY_SECONDS = float(os.getenv("DOWNLOAD_DELAY_SECONDS", "0.15"))
ANALYTICS_DELAY_SECONDS = float(os.getenv("ANALYTICS_DELAY_SECONDS", "0.2"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/purchase")
async def purchase_game() -> dict[str, int | str]:
    global PURCHASE_COUNT
    await asyncio.sleep(PURCHASE_DELAY_SECONDS)
    PURCHASE_COUNT += 1
    return {"status": "ok", "purchases": PURCHASE_COUNT}


@app.post("/download")
async def download_game() -> dict[str, int | str]:
    global DOWNLOAD_COUNT
    await asyncio.sleep(DOWNLOAD_DELAY_SECONDS)
    DOWNLOAD_COUNT += 1
    return {"status": "ok", "downloads": DOWNLOAD_COUNT}


@app.get("/purchase/stats")
async def purchase_stats() -> dict[str, int]:
    return {"purchases": PURCHASE_COUNT}


@app.get("/download/stats")
async def download_stats() -> dict[str, int]:
    return {"downloads": DOWNLOAD_COUNT}


@app.get("/analytics")
async def analytics() -> dict[str, int | str]:
    await asyncio.sleep(ANALYTICS_DELAY_SECONDS)

    # In the monolith, analytics depends on internal endpoint data equivalents.
    purchases = PURCHASE_COUNT
    downloads = DOWNLOAD_COUNT

    return {
        "status": "ok",
        "purchases": purchases,
        "downloads": downloads,
    }
