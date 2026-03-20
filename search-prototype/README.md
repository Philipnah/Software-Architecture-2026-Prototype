# Search Service Prototype (Python + Docker)

Minimal prototype for benchmarking game metadata search with two backends:

- PostgreSQL search
- Elasticsearch search
- Elasticsearch search with optional PostgreSQL enrichment (pricing/discount)

The prototype demonstrates:

- Builder pattern: query construction with a consistent API (`set_search_term`, `set_genre`, `set_filters`, `build_query`)
- Decorator pattern: performance timing logs (`[TIMING] ... took X ms`) in terminal output

## Run

```bash
docker compose up --build
```

API is exposed at:

- http://localhost:8000

## Quick checks

```bash
curl "http://localhost:8000/health"
```

### PostgreSQL search

```bash
curl "http://localhost:8000/search?engine=postgres&q=RPG&limit=5"
```

### Elasticsearch search

```bash
curl "http://localhost:8000/search?engine=elasticsearch&q=RPG&limit=5"
```

### Elasticsearch + DB enrichment (sequence diagram optional step)

```bash
curl "http://localhost:8000/search?engine=elasticsearch_enriched&q=RPG&limit=5"
```

### Filter examples

```bash
curl "http://localhost:8000/search?engine=elasticsearch&q=loot&genre=RPG&filters=multiplayer&limit=10"
```

```bash
curl "http://localhost:8000/search?engine=postgres&q=builder&filters=economy&limit=10"
```

## Benchmark style testing with curl

Run each command multiple times and compare terminal timing logs from the API container:

```bash
for i in {1..20}; do curl -s "http://localhost:8000/search?engine=postgres&q=RPG&limit=10" > /dev/null; done
```

```bash
for i in {1..20}; do curl -s "http://localhost:8000/search?engine=elasticsearch&q=RPG&limit=10" > /dev/null; done
```

```bash
for i in {1..20}; do curl -s "http://localhost:8000/search?engine=elasticsearch_enriched&q=RPG&limit=10" > /dev/null; done
```

View logs:

```bash
docker compose logs -f api
```
