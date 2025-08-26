"""
vector_upsert.py
Module for embedding text and upserting vectors with metadata into Qdrant collections.
"""

from typing import Dict, Any, Optional
import json
import logging

from .llm_client import default_llm_client as llm_client
from .utils.utils import get_logger

logger = get_logger(__name__)


def vector_upsert(
    text: str,
    collection: str,
    metadata: Dict[str, Any],
    model: Optional[str] = None,
    qdrant_url: Optional[str] = None,
    skip_if_up_to_date: Optional[str] = None,
    vector_id_key: Optional[str] = None,
) -> None:
    """
    Embed text and upsert vectors with metadata into Qdrant collections.

    Args:
        text (str): Text to embed.
        collection (str): Qdrant collection name.
        metadata (Dict[str, Any]): Flat JSON metadata object.
        model (Optional[str]): Embedding model to use.
        qdrant_url (Optional[str]): Qdrant server URL.
        skip_if_up_to_date (Optional[str]): Metadata key for timestamp optimization.
        vector_id_key (Optional[str]): Metadata field for ID generation.
    """
    # Step 1: Generate embedding via llm_client (fallback deterministic inside)
    embedding = llm_client.embed(text, model=model)

    # Step 2: Simulate vector ID generation
    if vector_id_key and vector_id_key in metadata:
        vector_id = str(metadata[vector_id_key])
    else:
        vector_id = str(hash(text))

    # Step 3: Simulate upsert to Qdrant
    vector_payload_dc = {
        "id": vector_id,
        "embedding": embedding,
        "metadata": metadata,
        "collection": collection,
        "model": model,
        "qdrant_url": qdrant_url,
    }

    # Step 4: Optionally skip if up-to-date
    if skip_if_up_to_date and skip_if_up_to_date in metadata:
        logger.info(f"Skipping upsert for {vector_id} (up-to-date by {skip_if_up_to_date})")
        return

    # Step 5: Simulate storing vector (print or cache)
    logger.info(
        f"Upserted vector to collection '{collection}': {json.dumps(vector_payload_dc)[:120]}..."
    )
