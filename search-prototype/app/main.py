import json
import os
import time
from pathlib import Path
from typing import List, Literal

import psycopg2
from elasticsearch import Elasticsearch
from fastapi import FastAPI, Query

from app.query_builder import QuerySpec
from app.services.elasticsearch_search_service import ElasticSearchService
from app.services.postgres_search_service import PostgresSearchService


def _postgres_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'games')} "
        f"user={os.getenv('POSTGRES_USER', 'games_user')} "
        f"password={os.getenv('POSTGRES_PASSWORD', 'games_pass')}"
    )


def _wait_for_postgres(dsn: str, retries: int = 30) -> None:
    for attempt in range(1, retries + 1):
        try:
            with psycopg2.connect(dsn):
                return
        except psycopg2.OperationalError:
            if attempt == retries:
                raise
            time.sleep(1)


def _wait_for_elasticsearch(host: str, retries: int = 30) -> None:
    client = Elasticsearch(host)
    for attempt in range(1, retries + 1):
        try:
            if client.ping():
                return
        except Exception:
            pass
        if attempt == retries:
            raise RuntimeError("Elasticsearch did not become ready in time")
        time.sleep(1)


app = FastAPI(title="Search Service Prototype")

postgres_service: PostgresSearchService
elasticsearch_service: ElasticSearchService


@app.on_event("startup")
def startup_event() -> None:
    global postgres_service, elasticsearch_service

    dsn = _postgres_dsn()
    es_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    es_index = os.getenv("ELASTICSEARCH_INDEX", "games")

    _wait_for_postgres(dsn)
    _wait_for_elasticsearch(es_host)

    postgres_service = PostgresSearchService(dsn)
    postgres_service.ensure_schema()

    elasticsearch_service = ElasticSearchService(es_host, es_index, postgres_service)
    elasticsearch_service.ensure_index()

    data_path = Path(__file__).resolve().parent.parent / "data" / "games.json"
    with open(data_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    postgres_service.seed_games(games)
    elasticsearch_service.seed_games(games)

    print("[BOOT] Search prototype ready with seeded sample data")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/search")
def search_games(
    engine: Literal["postgres", "elasticsearch", "elasticsearch_enriched"] = "elasticsearch",
    q: str = "",
    genre: str = "",
    filters: List[str] = Query(default=[]),
    limit: int = 10,
) -> dict:
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    if engine == "postgres":
        service = postgres_service
    else:
        service = elasticsearch_service

    query: QuerySpec = (
        service.reset_query()
        .set_search_term(q)
        .set_genre(genre)
        .set_filters(filters)
        .build_query()
    )

    if engine == "elasticsearch_enriched":
        results = elasticsearch_service.send_query_with_db_enrichment(query, limit=limit)
    else:
        results = service.send_query(query, limit=limit)

    return {
        "engine": engine,
        "query": {
            "search_term": query.search_term,
            "genre": query.genre,
            "filters": query.filters,
            "limit": limit,
        },
        "count": len(results),
        "results": results,
    }
