from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.query_builder import GameQueryBuilder, QuerySpec


class SearchServiceInterface(ABC):
    """Common API for search services used in the benchmark."""

    def __init__(self) -> None:
        self._builder = GameQueryBuilder()

    def set_search_term(self, term: str) -> "SearchServiceInterface":
        self._builder.set_search_term(term)
        return self

    def set_genre(self, genre: str) -> "SearchServiceInterface":
        self._builder.set_genre(genre)
        return self

    def set_filters(self, filter_list: List[str]) -> "SearchServiceInterface":
        self._builder.set_filters(filter_list)
        return self

    def build_query(self) -> QuerySpec:
        return self._builder.build()

    def reset_query(self) -> "SearchServiceInterface":
        self._builder.reset()
        return self

    @abstractmethod
    def send_query(self, query: QuerySpec, limit: int = 10) -> List[Dict[str, Any]]:
        raise NotImplementedError
