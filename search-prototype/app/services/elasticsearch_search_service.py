from typing import Any, Dict, List

from elasticsearch import Elasticsearch, helpers

from app.decorators import timed
from app.query_builder import QuerySpec
from app.services.interface import SearchServiceInterface
from app.services.postgres_search_service import PostgresSearchService


class ElasticSearchService(SearchServiceInterface):
    def __init__(self, host: str, index_name: str, postgres_service: PostgresSearchService) -> None:
        super().__init__()
        self._client = Elasticsearch(host)
        self._index_name = index_name
        self._postgres_service = postgres_service

    def ping(self) -> bool:
        return bool(self._client.ping())

    def ensure_index(self) -> None:
        if self._client.indices.exists(index=self._index_name):
            return

        self._client.indices.create(
            index=self._index_name,
            mappings={
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "text"},
                    "genre": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "description": {"type": "text"},
                }
            },
        )

    def seed_games(self, games: List[Dict[str, Any]]) -> None:
        count = self._client.count(index=self._index_name)["count"]
        if count > 0:
            return

        actions = []
        for g in games:
            actions.append(
                {
                    "_index": self._index_name,
                    "_id": g["id"],
                    "_source": {
                        "id": g["id"],
                        "title": g["title"],
                        "genre": g["genre"],
                        "tags": g["tags"],
                        "description": g["description"],
                    },
                }
            )

        helpers.bulk(self._client, actions)
        self._client.indices.refresh(index=self._index_name)

    @timed("elasticsearch.send_query")
    def send_query(self, query: QuerySpec, limit: int = 10) -> List[Dict[str, Any]]:
        must: List[Dict[str, Any]] = []
        filters: List[Dict[str, Any]] = []

        if query.search_term:
            must.append(
                {
                    "multi_match": {
                        "query": query.search_term,
                        "fields": ["title^3", "description", "tags^2"],
                        "fuzziness": "AUTO",
                    }
                }
            )

        if query.genre:
            filters.append({"term": {"genre": query.genre}})

        for item in query.filters:
            filters.append({"term": {"tags": item}})

        response = self._client.search(
            index=self._index_name,
            size=limit,
            query={
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filters,
                }
            },
        )

        hits = response.get("hits", {}).get("hits", [])
        results: List[Dict[str, Any]] = []
        ids: List[int] = []

        for h in hits:
            source = h.get("_source", {})
            game_id = int(source["id"])
            ids.append(game_id)
            results.append(
                {
                    "id": game_id,
                    "title": source.get("title"),
                    "genre": source.get("genre"),
                    "tags": source.get("tags", []),
                    "description": source.get("description"),
                    "score": h.get("_score", 0),
                }
            )

        return results

    @timed("elasticsearch.send_query_enriched")
    def send_query_with_db_enrichment(self, query: QuerySpec, limit: int = 10) -> List[Dict[str, Any]]:
        es_results = self.send_query(query, limit=limit)
        ids = [int(item["id"]) for item in es_results]
        pricing = self._postgres_service.fetch_pricing_for_ids(ids)

        for item in es_results:
            game_pricing = pricing.get(int(item["id"]), {})
            item["price"] = game_pricing.get("price")
            item["discount"] = game_pricing.get("discount")

        return es_results
