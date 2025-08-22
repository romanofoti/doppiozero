"""
create_weekly_note.py
Module for creating a new weekly note from a template and placing it in the notes directory.
"""

from typing import Optional
import os
import datetime


def create_weekly_note(
    template_path: str, target_dir: str, date: Optional[str] = None
) -> None:
    """
    Create a new weekly note from a template and place it in the notes directory.

    Args:
        template_path (str): Path to the weekly note template file.
        target_dir (str): Directory to store the new weekly note.
        date (Optional[str]): Date for the weekly note (default: today).
    """
    # Step 1: Determine the date for the weekly note
    if date is None:
        date_obj = datetime.date.today()
    else:
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format: {date}. Use YYYY-MM-DD.")
            return

    week_str = date_obj.strftime("Week of %Y-%m-%d")
    # Step 2: Read the template
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading template: {e}")
        return

    # Step 3: Create the note content
    note_content = template_content.replace("{{date}}", week_str)

    # Step 4: Write the new weekly note
    note_filename = f"{week_str}.md"
    note_path = os.path.join(target_dir, note_filename)
    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note_content)
        print(f"Weekly note created: {note_path}")
    except Exception as e:
        print(f"Error writing weekly note: {e}")
