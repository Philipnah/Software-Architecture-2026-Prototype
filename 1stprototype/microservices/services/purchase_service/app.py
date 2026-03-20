import asyncio
import os

from fastapi import FastAPI

app = FastAPI(title="purchase-service")

PURCHASE_COUNT = 0
SERVICE_DELAY_SECONDS = float(os.getenv("SERVICE_DELAY_SECONDS", "0.15"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/purchase")
async def purchase_game() -> dict[str, int | str]:
    global PURCHASE_COUNT
    await asyncio.sleep(SERVICE_DELAY_SECONDS)
    PURCHASE_COUNT += 1
    return {"status": "ok", "purchases": PURCHASE_COUNT}


@app.get("/stats")
async def stats() -> dict[str, int]:
    return {"purchases": PURCHASE_COUNT}
