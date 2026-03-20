from dataclasses import dataclass, field
from typing import List


@dataclass
class QuerySpec:
    search_term: str = ""
    genre: str = ""
    filters: List[str] = field(default_factory=list)


class GameQueryBuilder:
    """Builder pattern for constructing a search query consistently."""

    def __init__(self) -> None:
        self._search_term = ""
        self._genre = ""
        self._filters: List[str] = []

    def set_search_term(self, term: str) -> "GameQueryBuilder":
        self._search_term = (term or "").strip()
        return self

    def set_genre(self, genre: str) -> "GameQueryBuilder":
        self._genre = (genre or "").strip()
        return self

    def set_filters(self, filter_list: List[str]) -> "GameQueryBuilder":
        self._filters = [f.strip() for f in (filter_list or []) if f and f.strip()]
        return self

    def build(self) -> QuerySpec:
        return QuerySpec(
            search_term=self._search_term,
            genre=self._genre,
            filters=self._filters,
        )

    def reset(self) -> "GameQueryBuilder":
        self._search_term = ""
        self._genre = ""
        self._filters = []
        return self
