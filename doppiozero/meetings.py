"""
meetings.py
Utilities for archiving meeting transcripts: finding files, summarizing using
LLM, and persisting notes.

Public API:
 - find_transcript_files(transcripts_dir) -> list[str]
 - summarize_transcript(transcript_text, prompt_path, llm=None) -> str
 - archive_meeting(...)
"""

from typing import List, Optional
import os
import datetime

from .utils.utils import ensure_dir, get_logger
from .clients.llm import llm_client

logger = get_logger(__name__)


class Meetings:
    """Class-based interface for meeting archival and summarization.

    Parameters
    ----------
    llm : Optional[Any]
        Optional LLM client instance used to generate summaries; falls back to
        the module-level default client when omitted.

    Attributes
    ----------
    llm : Any
        The LLM client instance used by summarization helpers.

    Notes
    -----
    This helper provides methods to find transcript files, summarize them using
    LLM prompts, and archive generated notes to a target directory.

    """

    def __init__(self, llm=None):
        """Initialize the Meetings helper with an optional LLM client.

        Args:
            llm : Optional LLM client instance. If omitted, a default client is used.

        Returns:
            None

        """
        self.llm = llm or llm_client

    def find_transcript_files(self, transcripts_dir: str) -> List[str]:
        """Return a list of transcript file paths from a directory.

        Args:
            transcripts_dir : Directory to search for transcript files.

        Returns:
            A list of filesystem paths to transcript files (txt or md).

        """
        if not os.path.isdir(transcripts_dir):
            return []
        return [
            os.path.join(transcripts_dir, f)
            for f in os.listdir(transcripts_dir)
            if f.endswith(".txt") or f.endswith(".md")
        ]

    def _read_file(self, path: str) -> str:
        """Read and return the contents of a text file.

        Args:
            path : Path to the file to read.

        Returns:
            The file contents as a string.

        """
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, path: str, content: str) -> None:
        """Write text content to the given file path, creating parent dirs.

        Args:
            path : The file path to write to.
            content : The string content to write.

        Returns:
            None

        """
        parent = os.path.dirname(path)
        if parent:
            ensure_dir(parent)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def summarize_transcript(self, transcript_text: str, prompt_path: str, llm=None) -> str:
        """Summarize a transcript using the provided LLM and prompt template.

        Args:
            transcript_text : The raw transcript text to summarize.
            prompt_path : Path to the summary prompt template file.
            llm : Optional LLM client to use for generation.

        Returns:
            The generated summary string (fallback shortened text on error).

        """
        llm = llm or self.llm
        try:
            prompt = self._read_file(prompt_path)
        except Exception as e:
            logger.error(f"Error reading prompt file {prompt_path}: {e}")
            prompt = ""

        convo_text = transcript_text[:16000]
        full_prompt = prompt.replace("{{conversation}}", convo_text)

        try:
            return llm.generate(full_prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Summary (fallback): {convo_text[:200]}..."

    def archive_meeting(
        self,
        transcripts_dir: str,
        target_dir: str,
        executive_summary_prompt_path: str,
        detailed_notes_prompt_path: str,
        transcript_files: Optional[List[str]] = None,
        llm=None,
        write_links: bool = True,
    ) -> None:
        """Archive meetings by summarizing transcripts and saving notes.

        Args:
            transcripts_dir : Directory containing transcript source files.
            target_dir : Directory where summaries and notes will be written.
            executive_summary_prompt_path : Path to the executive summary prompt template.
            detailed_notes_prompt_path : Path to the detailed notes prompt template.
            transcript_files : Optional explicit list of transcript files to process.
            llm : Optional LLM to use for summarization.
            write_links : Whether to append links to a meeting_notes.md index.

        Returns:
            None

        """
        if transcript_files is None:
            transcript_files = self.find_transcript_files(transcripts_dir)
        if not transcript_files:
            logger.info("No transcript files found.")
            return

        for transcript_path in transcript_files:
            try:
                transcript = self._read_file(transcript_path)
            except Exception as e:
                logger.warning(f"Could not read transcript {transcript_path}: {e}")
                continue

            exec_summary = self.summarize_transcript(
                transcript, executive_summary_prompt_path, llm=llm
            )
            detail_notes = self.summarize_transcript(
                transcript, detailed_notes_prompt_path, llm=llm
            )

            base = os.path.splitext(os.path.basename(transcript_path))[0]
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            exec_path = os.path.join(target_dir, f"{base}_executive_summary_{date_str}.md")
            detail_path = os.path.join(target_dir, f"{base}_detailed_notes_{date_str}.md")

            self._write_file(exec_path, exec_summary)
            self._write_file(detail_path, detail_notes)

            if write_links:
                notes_path = os.path.join(target_dir, "meeting_notes.md")
                # Keep link text lines short by building them separately
                link_text = "- [[{}]]\n- [[{}]]\n".format(exec_path, detail_path)
                parent = os.path.dirname(notes_path)
                if parent:
                    ensure_dir(parent)
                with open(notes_path, "a", encoding="utf-8") as notes_file:
                    notes_file.write(link_text)

            logger.info("Processed %s: summaries saved, notes updated.", transcript_path)


# Module-level singleton for convenience
meetings = Meetings()
