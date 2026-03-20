import asyncio
import os

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="analytics-service")

SERVICE_DELAY_SECONDS = float(os.getenv("SERVICE_DELAY_SECONDS", "0.2"))
PURCHASE_STATS_URL = os.getenv("PURCHASE_STATS_URL", "http://localhost:8001/stats")
DOWNLOAD_STATS_URL = os.getenv("DOWNLOAD_STATS_URL", "http://localhost:8002/stats")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analytics")
async def analytics() -> dict[str, int | str]:
    await asyncio.sleep(SERVICE_DELAY_SECONDS)

    timeout = httpx.Timeout(1.5)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            purchase_response = await client.get(PURCHASE_STATS_URL)
            purchase_response.raise_for_status()
            download_response = await client.get(DOWNLOAD_STATS_URL)
            download_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"dependency unavailable: {exc}") from exc

    purchases = int(purchase_response.json().get("purchases", 0))
    downloads = int(download_response.json().get("downloads", 0))

    return {
        "status": "ok",
        "purchases": purchases,
        "downloads": downloads,
    }
