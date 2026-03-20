import csv
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


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_tags(genre_value: str) -> List[str]:
    if not genre_value:
        return ["unknown"]
    parts = [part.strip().lower() for part in genre_value.split(",") if part.strip()]
    return parts if parts else ["unknown"]


def _load_games_from_steam_csv(csv_path: Path) -> List[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Steam CSV file was not found at {csv_path}")

    games: List[dict] = []
    seen_ids = set()

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            steam_id_raw = (row.get("steam_id") or "").strip()
            if not steam_id_raw.isdigit():
                continue

            game_id = int(steam_id_raw)
            if game_id in seen_ids:
                continue
            seen_ids.add(game_id)

            genre = (row.get("genre") or "").strip() or "Unknown"
            description = (row.get("description") or "").strip() or "No description provided"

            games.append(
                {
                    "id": game_id,
                    "title": (row.get("title") or "").strip() or f"Game {game_id}",
                    "genre": genre,
                    "tags": _parse_tags(genre),
                    "description": description,
                    # steam.csv in this dataset does not include pricing fields.
                    "price": _parse_float(row.get("price"), default=0.0),
                    "discount": _parse_float(row.get("discount"), default=0.0),
                }
            )

    if not games:
        raise RuntimeError("No valid game records could be parsed from steam.csv")

    return games


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

    data_path = Path(__file__).resolve().parent.parent / "data" / "steam.csv"
    games = _load_games_from_steam_csv(data_path)

    postgres_service.seed_games(games)
    elasticsearch_service.seed_games(games)

    print(f"[BOOT] Search prototype ready with steam.csv data ({len(games)} records)")


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
