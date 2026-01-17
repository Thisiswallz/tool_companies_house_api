"""Shared utility functions for Companies House scraper."""

import json
import logging
from pathlib import Path
from typing import Dict, Any


logger = logging.getLogger(__name__)


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling.

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary with JSON data, or empty dict if file doesn't exist or is invalid

    Examples:
        >>> load_json_file(Path("profile.json"))
        {'company_number': '00000006', 'company_name': '...'}

        >>> load_json_file(Path("missing.json"))
        {}
    """
    filepath = Path(filepath)

    if not filepath.exists():
        logger.debug(f"JSON file not found: {filepath}")
        return {}

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return {}


def save_json_file(filepath: Path, data: Dict[str, Any], indent: int = 2):
    """Save JSON file with formatting.

    Args:
        filepath: Path where to save JSON file
        data: Dictionary to save as JSON
        indent: Indentation level for JSON formatting (default: 2)

    Raises:
        IOError: If file cannot be written

    Examples:
        >>> save_json_file(Path("output.json"), {"key": "value"})
        >>> save_json_file(Path("compact.json"), {"key": "value"}, indent=None)
    """
    filepath = Path(filepath)

    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=indent)
        logger.debug(f"Saved JSON to {filepath}")
    except Exception as e:
        logger.error(f"Error saving JSON to {filepath}: {e}")
        raise
