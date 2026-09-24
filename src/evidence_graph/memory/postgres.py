from datetime import UTC, date, datetime

from evidence_graph.auth.quotas import QuotaExceeded
from evidence_graph.memory.threads import ThreadRecord

_SETUP = """
CREATE TABLE IF NOT EXISTS evidence_threads (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS evidence_threads_user_id ON evidence_threads (user_id);

CREATE TABLE IF NOT EXISTS evidence_quotas (
    user_id TEXT NOT NULL,
    day DATE NOT NULL,
    used INTEGER NOT NULL,
    PRIMARY KEY (user_id, day)
);
"""


class PostgresBackend:
    """One pool for checkpoints, thread ownership, and daily quotas."""

    def __init__(self, database_url: str) -> None:
        from psycopg_pool import ConnectionPool

        self.pool = ConnectionPool(
            conninfo=database_url,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=True,
        )
        with self.pool.connection() as conn:
            conn.execute(_SETUP)

    def checkpointer(self):
        from langgraph.checkpoint.postgres import PostgresSaver

        saver = PostgresSaver(self.pool)
        saver.setup()
        return saver

    def threads(self) -> "PostgresThreadStore":
        return PostgresThreadStore(self)

    def quotas(self) -> "PostgresQuotaStore":
        return PostgresQuotaStore(self)


class PostgresThreadStore:
    def __init__(self, backend: PostgresBackend) -> None:
        self._backend = backend

    def create(self, user_id: str, thread_id: str, query: str) -> ThreadRecord:
        now = datetime.now(UTC)
        with self._backend.pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence_threads (thread_id, user_id, query, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (thread_id, user_id, query, now, now),
            )
        return ThreadRecord(thread_id, user_id, query, now, now)

    def get(self, thread_id: str) -> ThreadRecord | None:
        with self._backend.pool.connection() as conn:
            row = conn.execute(
                """
                SELECT thread_id, user_id, query, created_at, updated_at
                FROM evidence_threads WHERE thread_id = %s
                """,
                (thread_id,),
            ).fetchone()
        return _thread_row(row) if row else None

    def list_for_user(self, user_id: str) -> list[ThreadRecord]:
        with self._backend.pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT thread_id, user_id, query, created_at, updated_at
                FROM evidence_threads WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [_thread_row(row) for row in rows]

    def touch(self, thread_id: str, query: str) -> None:
        with self._backend.pool.connection() as conn:
            conn.execute(
                """
                UPDATE evidence_threads
                SET query = %s, updated_at = %s
                WHERE thread_id = %s
                """,
                (query, datetime.now(UTC), thread_id),
            )

    def delete(self, thread_id: str) -> bool:
        with self._backend.pool.connection() as conn:
            row = conn.execute(
                "DELETE FROM evidence_threads WHERE thread_id = %s RETURNING thread_id",
                (thread_id,),
            ).fetchone()
        return row is not None


class PostgresQuotaStore:
    def __init__(self, backend: PostgresBackend) -> None:
        self._backend = backend

    def consume(self, user_id: str, limit: int, day: date | None = None) -> int:
        day = day or datetime.now(UTC).date()
        with self._backend.pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO evidence_quotas (user_id, day, used)
                VALUES (%s, %s, 1)
                ON CONFLICT (user_id, day)
                DO UPDATE SET used = evidence_quotas.used + 1
                WHERE evidence_quotas.used < %s
                RETURNING used
                """,
                (user_id, day, limit),
            ).fetchone()
        if row is None:
            raise QuotaExceeded(limit, limit)
        return int(row[0])


def _thread_row(row: tuple) -> ThreadRecord:
    return ThreadRecord(
        thread_id=row[0],
        user_id=row[1],
        query=row[2],
        created_at=row[3],
        updated_at=row[4],
    )
