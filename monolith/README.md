# Monolith Prototype (Phase 2)

This setup implements one Python monolith service in a single Docker container. It includes the same three endpoints and weighted traffic experiment as the microservices setup, but disruption is a full monolith restart.

## Endpoints and Traffic Weights

- `POST /purchase` - 40%
- `POST /download` - 40%
- `GET /analytics` - 20%

Each endpoint waits briefly and then responds.

Analytics depends on purchase/download counters via the same app state.

## Start Monolith

From this folder:

```bash
docker compose up --build -d
```

Health check:

```bash
curl http://localhost:8000/health
```

## Run Monolith Restart Experiment

```bash
python3 experiment/run_monolith_experiment.py \
  --duration 45 \
  --restart-at 15 \
  --rps 40 \
  --workers 12
```

Optional output file:

```bash
python3 experiment/run_monolith_experiment.py --output ./monolith_report.json
```

## Compare with Microservices

Run this in `microservices/`:

```bash
python3 experiment/run_microservice_experiment.py \
  --duration 45 \
  --restart-at 15 \
  --target-service purchase_service \
  --rps 40 \
  --workers 12 \
  --output ./microservice_report.json
```

Then compare the two JSON reports:

- `totals.lost_ratio`
- `per_endpoint.*.lost_ratio`

## Stop Monolith

```bash
docker compose down
```
