"""
archive_meeting.py
Agentic module for archiving meetings: processes transcripts, generates summaries, and updates notes.
"""

import os
from typing import Optional, List


def find_transcript_files(transcripts_dir: str) -> List[str]:
    """Return a list of transcript files in the directory."""
    return [
        os.path.join(transcripts_dir, f)
        for f in os.listdir(transcripts_dir)
        if f.endswith('.txt') or f.endswith('.md')
    ]


def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def generate_summary(transcript: str, prompt: str) -> str:
    """Stub: Generate a summary from transcript using a prompt (replace with LLM call)."""
    # TODO: Integrate with LLM API
    return f"Summary for transcript:\n{transcript[:100]}..."


def archive_meeting(
    transcripts_dir: str,
    target_dir: str,
    executive_summary_prompt_path: str,
    detailed_notes_prompt_path: str,
    transcript_files: Optional[List[str]] = None,
) -> None:
    """
    Archive a meeting by processing transcripts, generating summaries, and updating notes.
    Modular agentic workflow following PocketFlow principles.
    """
    if transcript_files is None:
        transcript_files = find_transcript_files(transcripts_dir)
    exec_prompt = read_file(executive_summary_prompt_path)
    detail_prompt = read_file(detailed_notes_prompt_path)
    for transcript_path in transcript_files:
        transcript = read_file(transcript_path)
        exec_summary = generate_summary(transcript, exec_prompt)
        detail_notes = generate_summary(transcript, detail_prompt)
        # Save summaries and notes
        base = os.path.splitext(os.path.basename(transcript_path))[0]
        exec_path = os.path.join(target_dir, f"{base}_executive_summary.md")
        detail_path = os.path.join(target_dir, f"{base}_detailed_notes.md")
        write_file(exec_path, exec_summary)
        write_file(detail_path, detail_notes)
        # Optionally update a master notes file (not implemented)
