"""Utility functions for the boundary coverage project."""


def sanitize_filename(name):
    """
    Sanitizes a string to be safe for use as a filename by replacing path separators.

    Args:
        name (str): The name to sanitize

    Returns:
        str: The sanitized filename
    """
    return name.replace('/', '&').replace('\\', '&')