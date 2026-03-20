from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from app.decorators import timed
from app.query_builder import QuerySpec
from app.services.interface import SearchServiceInterface


class PostgresSearchService(SearchServiceInterface):
    def __init__(self, dsn: str) -> None:
        super().__init__()
        self._dsn = dsn

    def _connect(self):
        return psycopg2.connect(self._dsn)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS games (
                        id INTEGER PRIMARY KEY,
                        title TEXT NOT NULL,
                        genre TEXT NOT NULL,
                        tags TEXT[] NOT NULL,
                        description TEXT NOT NULL,
                        price NUMERIC(10, 2) NOT NULL,
                        discount NUMERIC(5, 2) NOT NULL
                    );
                    """
                )
            conn.commit()

    def seed_games(self, games: List[Dict[str, Any]]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM games;")
                count = cur.fetchone()[0]
                if count > 0:
                    return

                psycopg2.extras.execute_batch(
                    cur,
                    """
                    INSERT INTO games (id, title, genre, tags, description, price, discount)
                    VALUES (%(id)s, %(title)s, %(genre)s, %(tags)s, %(description)s, %(price)s, %(discount)s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    games,
                )
            conn.commit()

    @timed("postgres.send_query")
    def send_query(self, query: QuerySpec, limit: int = 10) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []

        if query.search_term:
            conditions.append(
                "(title ILIKE %s OR description ILIKE %s OR EXISTS (SELECT 1 FROM unnest(tags) t WHERE t ILIKE %s))"
            )
            pattern = f"%{query.search_term}%"
            params.extend([pattern, pattern, pattern])

        if query.genre:
            conditions.append("genre = %s")
            params.append(query.genre)

        for item in query.filters:
            conditions.append("%s = ANY(tags)")
            params.append(item)

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        sql = (
            "SELECT id, title, genre, tags, description, price, discount "
            "FROM games"
            f"{where_clause} "
            "ORDER BY id "
            "LIMIT %s"
        )
        params.append(limit)

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [dict(row) for row in rows]

    @timed("postgres.fetch_pricing")
    def fetch_pricing_for_ids(self, game_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not game_ids:
            return {}

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, price, discount
                    FROM games
                    WHERE id = ANY(%s)
                    """,
                    (game_ids,),
                )
                rows = cur.fetchall()

        return {int(row["id"]): {"price": float(row["price"]), "discount": float(row["discount"])} for row in rows}

    def fetch_by_ids(self, game_ids: List[int]) -> List[Dict[str, Any]]:
        if not game_ids:
            return []

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, title, genre, tags, description, price, discount
                    FROM games
                    WHERE id = ANY(%s)
                    ORDER BY id
                    """,
                    (game_ids,),
                )
                rows = cur.fetchall()

        return [dict(row) for row in rows]
