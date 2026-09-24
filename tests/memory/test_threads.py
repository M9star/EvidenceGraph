from langgraph.checkpoint.memory import MemorySaver

from evidence_graph.auth import InMemoryQuotaStore
from evidence_graph.config import Settings
from evidence_graph.memory import InMemoryThreadStore, build_stores


def test_list_and_get_are_scoped_to_the_owner():
    store = InMemoryThreadStore()
    store.create("alice", "t-a", "alice query")
    store.create("bob", "t-b", "bob query")

    assert store.get("t-a").user_id == "alice"
    assert [r.thread_id for r in store.list_for_user("alice")] == ["t-a"]
    assert [r.thread_id for r in store.list_for_user("bob")] == ["t-b"]


def test_delete_removes_only_that_thread():
    store = InMemoryThreadStore()
    store.create("alice", "t-a", "q")
    store.create("alice", "t-a2", "q2")

    assert store.delete("t-a") is True
    assert store.get("t-a") is None
    assert store.get("t-a2") is not None
    assert store.delete("missing") is False


def test_stores_default_to_memory_without_a_database_url():
    checkpointer, threads, quotas = build_stores(Settings(_env_file=None, database_url=None))

    assert isinstance(checkpointer, MemorySaver)
    assert isinstance(threads, InMemoryThreadStore)
    assert isinstance(quotas, InMemoryQuotaStore)
