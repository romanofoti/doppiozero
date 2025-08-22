"""
select_folder.py
Module for selecting the most recently updated folder in a target directory.
"""

from typing import List
import os
import time


def select_folder(target_dir: str) -> str:
    """
    Select the most recently updated folder in a target directory.

    Args:
        target_dir (str): Directory to search for folders.

    Returns:
        str: Path to the selected folder.
    """
    # Get a list of all folders in the target directory
    folders = [f.path for f in os.scandir(target_dir) if f.is_dir()]

    # If no folders are found, return an empty string
    if not folders:
        return ""

    # Sort the folders by modification time in descending order
    folders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # Return the most recently updated folder
    return folders[0]
