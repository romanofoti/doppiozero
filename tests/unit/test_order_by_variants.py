from unittest.mock import MagicMock

from doppiozero.contents import content_manager


class DummyQdrantClient:
    def __init__(self):
        self.query_points = MagicMock(return_value=[])


def test_multiple_order_fields_and_synonyms(monkeypatch):
    class FakeOrder:
        def __init__(self, key=None, order=None):
            self.key = key
            self.order = order

    class FakeOrderType:
        ASCENDING = "asc"
        DESCENDING = "desc"

    import doppiozero.contents as contents_mod

    monkeypatch.setattr(contents_mod, "QOrder", FakeOrder)
    monkeypatch.setattr(contents_mod, "QOrderType", FakeOrderType)

    dummy_client = DummyQdrantClient()
    monkeypatch.setattr(content_manager, "_get_qdrant_client", lambda url: dummy_client)

    # Multiple fields, mixed synonyms
    content_manager.vector_search(
        "query",
        "test_collection",
        qdrant_url="http://localhost:6333",
        top_k=1,
        order_by="created_at asc, updated_at descending",
    )

    assert dummy_client.query_points.called
    _, called_kwargs_dc = dummy_client.query_points.call_args
    order_by_passed = called_kwargs_dc.get("order_by")

    # Should be a list of FakeOrder instances
    assert isinstance(order_by_passed, list)
    assert len(order_by_passed) == 2
    assert order_by_passed[0].key == "created_at"
    assert order_by_passed[1].key == "updated_at"
    assert order_by_passed[0].order == FakeOrderType.ASCENDING
    assert order_by_passed[1].order == FakeOrderType.DESCENDING
