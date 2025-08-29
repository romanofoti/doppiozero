import os
import time
import pytest
from doppiozero.contents import content_manager

QDRANT = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = "test_integration_smoke_collection"


@pytest.mark.integration
def test_qdrant_smoke():
    # If Qdrant is not reachable, skip the integration test quickly
    try:
        # quick health check
        hits = content_manager.vector_search("healthcheck", COLLECTION, qdrant_url=QDRANT, top_k=1)
    except Exception:
        pytest.skip("Qdrant not available at %s" % QDRANT)

    text = "Integration smoke document about caching and database connectivity."
    metadata = {
        "url": "https://example.com/integration/smoke/1",
        "title": "Integration Smoke",
        "executive_summary": "Integration smoke summary",
        "conversation": {"body": "Integration conversation body."},
    }

    # Upsert with a few retries in case Qdrant is cold
    for attempt in range(3):
        try:
            content_manager.vector_upsert(
                text,
                COLLECTION,
                metadata,
                qdrant_url=QDRANT,
                vector_id_key="url",
            )
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)

    # Small delay
    time.sleep(0.5)

    hits = content_manager.vector_search("database caching", COLLECTION, qdrant_url=QDRANT, top_k=5)
    assert any(
        h.get("url") == metadata["url"] for h in hits
    ), "Upserted document not found in search results"

    # Best-effort cleanup: try to remove the test collection if the client supports it
    try:
        client = content_manager._get_qdrant_client(QDRANT)
        if client is not None:
            try:
                client.delete_collection(collection_name=COLLECTION)
            except Exception:
                pass
    except Exception:
        pass
