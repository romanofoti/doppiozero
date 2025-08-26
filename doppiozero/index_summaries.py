"""
index_summaries.py
Module for bulk indexing multiple GitHub conversations into a vector database for semantic search.
"""

from typing import List, Optional
import logging
from .index_summary import index_summary

logger = logging.getLogger(__name__)


def index_summaries(
    urls: List[str],
    executive_summary_prompt_path: str,
    topics_prompt_path: str,
    collection: str,
    cache_path: Optional[str] = None,
    updated_at: Optional[str] = None,
    model: Optional[str] = None,
    qdrant_url: Optional[str] = None,
    max_topics: Optional[int] = None,
    skip_if_up_to_date: bool = False,
) -> None:
    """
    Bulk index multiple GitHub conversations into a vector database for semantic search.

    Args:
        urls (List[str]): List of GitHub conversation URLs.
        executive_summary_prompt_path (str): Path to executive summary prompt file.
        topics_prompt_path (str): Path to topics prompt file.
        collection (str): Qdrant collection name.
        cache_path (Optional[str]): Directory for caching data (default: None).
        updated_at (Optional[str]): Only process if remote conversation is newer than this timestamp.
        model (Optional[str]): Embedding model to use.
        qdrant_url (Optional[str]): Qdrant server URL.
        max_topics (Optional[int]): Maximum number of topics to extract.
        skip_if_up_to_date (bool): Skip indexing if vector exists and is up-to-date.
    """
    for url in urls:
        try:
            index_summary(
                conversation_url=url,
                executive_summary_prompt_path=executive_summary_prompt_path,
                topics_prompt_path=topics_prompt_path,
                collection=collection,
                cache_path=cache_path,
                updated_at=updated_at,
                model=model,
                qdrant_url=qdrant_url,
                max_topics=max_topics,
                skip_if_up_to_date=skip_if_up_to_date,
            )
        except Exception as e:
            logger.error(f"Error indexing summary for {url}: {e}")
