from unittest.mock import MagicMock

from doppiozero.contents import content_manager


class DummyQdrantClient:
    def __init__(self):
        self.query_points = MagicMock(return_value=[])


def test_order_by_mapping_uses_typed_order(monkeypatch):
    """When qdrant-client exposes Order models, vector_search should pass a typed
    Order object to query_points instead of a plain dict.
    """

    # Prepare a fake Order class to simulate qdrant-client models
    class FakeOrder:
        def __init__(self, key=None, order=None):
            self.key = key
            self.order = order

    class FakeOrderType:
        ASCENDING = "asc"
        DESCENDING = "desc"

    # Patch the imported QOrder and QOrderType in the contents module
    import doppiozero.contents as contents_mod

    monkeypatch.setattr(contents_mod, "QOrder", FakeOrder)
    monkeypatch.setattr(contents_mod, "QOrderType", FakeOrderType)

    dummy_client = DummyQdrantClient()

    # Patch _get_qdrant_client to return our dummy client and ensure no network
    monkeypatch.setattr(content_manager, "_get_qdrant_client", lambda url: dummy_client)

    # Run vector_search with an order_by that should map to a typed object
    content_manager.vector_search(
        "query",
        "test_collection",
        qdrant_url="http://localhost:6333",
        top_k=1,
        order_by="created_at desc",
    )

    # Ensure query_points was called
    assert dummy_client.query_points.called, "query_points was not called"

    # Inspect the call kwargs
    called_args, called_kwargs_dc = dummy_client.query_points.call_args
    order_by_passed = called_kwargs_dc.get("order_by")

    # With our fake models, order_by should be an instance of FakeOrder
    assert isinstance(order_by_passed, FakeOrder), "Expected a typed Order instance"
    assert order_by_passed.key == "created_at"
    assert order_by_passed.order == FakeOrderType.DESCENDING
