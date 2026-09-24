from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from evidence_graph.auth.quotas import InMemoryQuotaStore, QuotaStore
from evidence_graph.config import Settings
from evidence_graph.memory.threads import InMemoryThreadStore, ThreadStore


def build_stores(
    settings: Settings,
) -> tuple[BaseCheckpointSaver, ThreadStore, QuotaStore]:
    """Postgres when DATABASE_URL is set; otherwise process-local memory.

    Tests and `make run` stay offline. Production sets the URL so threads survive restart.
    """
    if not settings.database_url:
        return MemorySaver(), InMemoryThreadStore(), InMemoryQuotaStore()
    from evidence_graph.memory.postgres import PostgresBackend

    backend = PostgresBackend(settings.database_url)
    return backend.checkpointer(), backend.threads(), backend.quotas()


def delete_thread_checkpoints(checkpointer: BaseCheckpointSaver, thread_id: str) -> None:
    delete = getattr(checkpointer, "delete_thread", None)
    if delete is not None:
        delete(thread_id)
        return
    storage = getattr(checkpointer, "storage", None)
    if isinstance(storage, dict):
        storage.pop(thread_id, None)
