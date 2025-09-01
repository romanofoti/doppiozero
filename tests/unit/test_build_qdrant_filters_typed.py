from doppiozero.utils.utils import build_qdrant_filters


def test_build_qdrant_filters_returns_typed_filter(monkeypatch):
    # Create fake model classes to simulate qdrant-client models
    class FakeMatchValue:
        def __init__(self, value=None):
            self.value = value

    class FakeRange:
        def __init__(self, gte=None, lte=None, gt=None, lt=None):
            self.gte = gte
            self.lte = lte
            self.gt = gt
            self.lt = lt

    class FakeFieldCondition:
        def __init__(self, key=None, match=None, range=None):
            self.key = key
            self.match = match
            self.range = range

    class FakeFilter:
        def __init__(self, must=None, should=None):
            self.must = must
            self.should = should

    # Monkeypatch the qdrant_client.models import names so the function
    # imports the fake classes when it does `from qdrant_client.models import ...`.
    import qdrant_client.models as qmodels

    monkeypatch.setattr(qmodels, "Filter", FakeFilter, raising=False)
    monkeypatch.setattr(qmodels, "FieldCondition", FakeFieldCondition, raising=False)
    monkeypatch.setattr(qmodels, "MatchValue", FakeMatchValue, raising=False)
    monkeypatch.setattr(qmodels, "Range", FakeRange, raising=False)

    # Provide a simple filter dict input
    input_dc = {"labels": "bug, performance", "stars": ">=10"}

    out = build_qdrant_filters(input_dc)

    # The fake Filter should be returned when models are present
    assert isinstance(out, FakeFilter)
    assert out.must is not None
