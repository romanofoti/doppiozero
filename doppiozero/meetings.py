"""
meetings.py
Utilities for archiving meeting transcripts: finding files, summarizing using LLM, and persisting notes.

Public API:
 - find_transcript_files(transcripts_dir) -> list[str]
 - summarize_transcript(transcript_text, prompt_path, llm=None) -> str
 - archive_meeting(...)
"""

from typing import List, Optional
import os
import datetime

from .utils.utils import get_logger, read_json_or_none, write_json_safe, ensure_dir
from .llm_client import llm_client

logger = get_logger(__name__)


def find_transcript_files(transcripts_dir: str) -> List[str]:
    """Return transcript file paths in the directory."""
    if not os.path.isdir(transcripts_dir):
        return []
    return [
        os.path.join(transcripts_dir, f)
        for f in os.listdir(transcripts_dir)
        if f.endswith(".txt") or f.endswith(".md")
    ]


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_file(path: str, content: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def summarize_transcript(transcript_text: str, prompt_path: str, llm=None) -> str:
    """Summarize a transcript using the given prompt file and an LLM client.

    The llm parameter may be injected for testing; defaults to the package `llm_client`.
    """
    llm = llm or llm_client
    try:
        prompt = _read_file(prompt_path)
    except Exception as e:
        logger.error(f"Error reading prompt file {prompt_path}: {e}")
        prompt = ""

    # Very small safety: keep transcript size reasonable for LLM input
    convo_text = transcript_text[:16000]
    full_prompt = prompt.replace("{{conversation}}", convo_text)

    try:
        return llm.generate(full_prompt)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return f"Summary (fallback): {convo_text[:200]}..."


def archive_meeting(
    transcripts_dir: str,
    target_dir: str,
    executive_summary_prompt_path: str,
    detailed_notes_prompt_path: str,
    transcript_files: Optional[List[str]] = None,
    llm=None,
    write_links: bool = True,
) -> None:
    """Archive meeting transcripts: summarize and persist executive + detailed notes.

    Returns a dict-like summary of what was written (for tests).
    """
    if transcript_files is None:
        transcript_files = find_transcript_files(transcripts_dir)
    if not transcript_files:
        logger.info("No transcript files found.")
        return

    for transcript_path in transcript_files:
        try:
            transcript = _read_file(transcript_path)
        except Exception as e:
            logger.warning(f"Could not read transcript {transcript_path}: {e}")
            continue

        exec_summary = summarize_transcript(transcript, executive_summary_prompt_path, llm=llm)
        detail_notes = summarize_transcript(transcript, detailed_notes_prompt_path, llm=llm)

        base = os.path.splitext(os.path.basename(transcript_path))[0]
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        exec_path = os.path.join(target_dir, f"{base}_executive_summary_{date_str}.md")
        detail_path = os.path.join(target_dir, f"{base}_detailed_notes_{date_str}.md")

        _write_file(exec_path, exec_summary)
        _write_file(detail_path, detail_notes)

        if write_links:
            notes_path = os.path.join(target_dir, "meeting_notes.md")
            link_text = f"- [[{exec_path}]]\n- [[{detail_path}]]\n"
            # Append links
            parent = os.path.dirname(notes_path)
            if parent:
                ensure_dir(parent)
            with open(notes_path, "a", encoding="utf-8") as notes_file:
                notes_file.write(link_text)

        logger.info(f"Processed {transcript_path}: summaries saved, notes updated.")
