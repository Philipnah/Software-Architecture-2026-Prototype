import asyncio
import random
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class Endpoint:
    name: str
    method: str
    url: str
    weight: float


@dataclass
class EndpointStats:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0


@dataclass
class LoadTestResult:
    started_at: float
    finished_at: float
    per_endpoint: dict[str, EndpointStats] = field(default_factory=dict)

    @property
    def total_attempted(self) -> int:
        return sum(stat.attempted for stat in self.per_endpoint.values())

    @property
    def total_succeeded(self) -> int:
        return sum(stat.succeeded for stat in self.per_endpoint.values())

    @property
    def total_failed(self) -> int:
        return sum(stat.failed for stat in self.per_endpoint.values())


class WeightedLoadTester:
    def __init__(
        self,
        endpoints: list[Endpoint],
        requests_per_second: float,
        worker_count: int,
        timeout_seconds: float = 1.5,
    ) -> None:
        self.endpoints = endpoints
        self.requests_per_second = requests_per_second
        self.worker_count = worker_count
        self.timeout_seconds = timeout_seconds
        self._weights = [endpoint.weight for endpoint in endpoints]

    def _pick_endpoint(self) -> Endpoint:
        return random.choices(self.endpoints, weights=self._weights, k=1)[0]

    async def _single_request(self, client: httpx.AsyncClient, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() == "POST":
            response = await client.post(endpoint.url)
        else:
            response = await client.get(endpoint.url)
        return response.status_code == 200

    async def run_for_duration(
        self,
        duration_seconds: float,
        disruption_at_seconds: float | None = None,
        disruption_coro=None,
    ) -> LoadTestResult:
        started_at = time.time()
        stats = {endpoint.name: EndpointStats() for endpoint in self.endpoints}
        stop_event = asyncio.Event()

        async def maybe_disrupt() -> None:
            if disruption_at_seconds is None or disruption_coro is None:
                return
            await asyncio.sleep(disruption_at_seconds)
            await disruption_coro()

        async def worker() -> None:
            timeout = httpx.Timeout(self.timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                while not stop_event.is_set():
                    endpoint = self._pick_endpoint()
                    endpoint_stats = stats[endpoint.name]
                    endpoint_stats.attempted += 1
                    try:
                        ok = await self._single_request(client, endpoint)
                    except httpx.HTTPError:
                        ok = False
                    except Exception:
                        ok = False

                    if ok:
                        endpoint_stats.succeeded += 1
                    else:
                        endpoint_stats.failed += 1

                    await asyncio.sleep(self.worker_count / max(self.requests_per_second, 0.1))

        workers = [asyncio.create_task(worker()) for _ in range(self.worker_count)]
        disruption_task = asyncio.create_task(maybe_disrupt())

        try:
            await asyncio.sleep(duration_seconds)
        finally:
            stop_event.set()
            await asyncio.gather(*workers, return_exceptions=True)
            await disruption_task

        finished_at = time.time()
        return LoadTestResult(started_at=started_at, finished_at=finished_at, per_endpoint=stats)
