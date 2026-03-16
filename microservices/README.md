# Microservices Prototype (Phase 1)

This setup implements three Python microservices in separate Docker containers and a terminal-based experiment runner to measure lost requests during a targeted service restart.

## Services

- `purchase_service` (`POST /purchase`, `GET /stats`) - 40% traffic
- `download_service` (`POST /download`, `GET /stats`) - 40% traffic
- `analytics_service` (`GET /analytics`) - 20% traffic

Each request waits briefly, then returns HTTP 200 on success.

`analytics_service` depends on the other two services by requesting:

- `purchase_service:/stats` for purchased count
- `download_service:/stats` for downloaded count

If dependencies are unavailable, analytics returns HTTP 503.

## Start Services

From this folder:

```bash
docker compose up --build -d
```

Quick health checks:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Run Restart Experiment

This sends weighted traffic and restarts one microservice mid-test.

```bash
python3 experiment/run_microservice_experiment.py \
  --duration 45 \
  --restart-at 15 \
  --target-service purchase_service \
  --rps 40 \
  --workers 12
```

Example with report file output:

```bash
python3 experiment/run_microservice_experiment.py --output ./microservice_report.json
```

## How Lost Requests Are Measured

- `attempted`: request sent by load generator
- `succeeded`: HTTP 200 response
- `failed`: timeout, connection error, or non-200 response
- `lost_ratio = failed / attempted`

The report prints both total and per-endpoint loss.

## Stop Services

```bash
docker compose down
```

---

This completes the microservices phase. Waiting for your order to build the monolith phase.
