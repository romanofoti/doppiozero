"""
archive_meeting.py
Agentic module for archiving meetings: processes transcripts, generates summaries, and updates notes.
"""

import os
from typing import List, Optional
import datetime


def find_transcript_files(transcripts_dir: str) -> List[str]:
    """Return a list of transcript files in the directory."""
    return [
        os.path.join(transcripts_dir, f)
        for f in os.listdir(transcripts_dir)
        if f.endswith(".txt") or f.endswith(".md")
    ]


def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_summary(transcript: str, prompt: str) -> str:
    """Generate a summary from transcript using a prompt (replace with LLM call)."""
    # Placeholder for LLM integration
    # In production, call your LLM API here
    return f"Summary for transcript:\n{transcript[:100]}...\nPrompt used: {prompt[:60]}..."


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
    # Step 1: Find transcript files
    if transcript_files is None:
        transcript_files = find_transcript_files(transcripts_dir)
    if not transcript_files:
        print("No transcript files found.")
        return
    # Step 2: Read prompts
    exec_prompt = read_file(executive_summary_prompt_path)
    detail_prompt = read_file(detailed_notes_prompt_path)
    # Step 3: Process each transcript
    for transcript_path in transcript_files:
        transcript = read_file(transcript_path)
        exec_summary = generate_summary(transcript, exec_prompt)
        detail_notes = generate_summary(transcript, detail_prompt)
        # Step 4: Save summaries and notes
        base = os.path.splitext(os.path.basename(transcript_path))[0]
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        exec_path = os.path.join(target_dir, f"{base}_executive_summary_{date_str}.md")
        detail_path = os.path.join(target_dir, f"{base}_detailed_notes_{date_str}.md")
        write_file(exec_path, exec_summary)
        write_file(detail_path, detail_notes)
        # Step 5: Update main meeting notes (append links)
        notes_path = os.path.join(target_dir, "meeting_notes.md")
        link_text = f"- [[{exec_path}]]\n- [[{detail_path}]]\n"
        with open(notes_path, "a", encoding="utf-8") as notes_file:
            notes_file.write(link_text)
        print(f"Processed {transcript_path}: summaries saved, notes updated.")
    # Optionally update a master notes file (not implemented)
