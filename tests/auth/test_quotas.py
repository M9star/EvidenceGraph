from datetime import date

import pytest

from evidence_graph.auth import InMemoryQuotaStore, QuotaExceeded


def test_consume_increments_until_the_limit():
    store = InMemoryQuotaStore()

    assert store.consume("alice", limit=2, day=date(2026, 9, 24)) == 1
    assert store.consume("alice", limit=2, day=date(2026, 9, 24)) == 2
    with pytest.raises(QuotaExceeded) as exc:
        store.consume("alice", limit=2, day=date(2026, 9, 24))
    assert exc.value.used == 2
    assert exc.value.limit == 2


def test_quotas_are_per_user_and_per_day():
    store = InMemoryQuotaStore()

    store.consume("alice", limit=1, day=date(2026, 9, 24))
    assert store.consume("bob", limit=1, day=date(2026, 9, 24)) == 1
    assert store.consume("alice", limit=1, day=date(2026, 9, 25)) == 1
