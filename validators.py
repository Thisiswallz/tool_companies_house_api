"""
Input validation and sanitization utilities for Companies House Scraper.

This module provides validation functions for:
- API keys
- Company numbers
- File paths and filenames
- Output path safety

All validators raise ValueError with descriptive messages on invalid input.
"""

import re
from pathlib import Path
from typing import Optional


def validate_api_key(api_key: str) -> None:
    """
    Validate API key format.

    Args:
        api_key: The API key to validate

    Raises:
        ValueError: If API key is invalid or missing

    Note:
        Does NOT test actual API authentication - only validates format.
    """
    if not api_key:
        raise ValueError(
            "API key is required. Set COMPANIES_HOUSE_API_KEY environment variable"
        )

    if len(api_key) < 20:
        raise ValueError("API key appears invalid (too short)")

    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        raise ValueError("API key contains invalid characters")


def validate_company_number(number: str) -> str:
    """
    Validate and normalize company number.

    Args:
        number: Raw company number input

    Returns:
        Normalized company number (uppercase, zero-padded if numeric)

    Raises:
        ValueError: If company number is invalid

    Examples:
        >>> validate_company_number("12345678")
        '12345678'
        >>> validate_company_number("123")
        '00000123'
        >>> validate_company_number("OC123456")
        'OC123456'
    """
    if not number or not isinstance(number, str):
        raise ValueError("Company number must be a non-empty string")

    # Remove whitespace and convert to uppercase
    number = number.strip().upper()

    # Must be 1-8 alphanumeric characters (Companies House standard)
    if not re.match(r'^[A-Z0-9]{1,8}$', number):
        raise ValueError(f"Invalid company number format: {number}")

    # Pad to 8 characters with leading zeros if purely numeric
    if number.isdigit():
        number = number.zfill(8)

    return number


def safe_output_path(base_dir: Path, filename: str) -> Path:
    """
    Resolve output path safely, preventing path traversal attacks.

    Args:
        base_dir: Base directory that all outputs must reside within
        filename: Filename or relative path to resolve

    Returns:
        Resolved absolute path guaranteed to be within base_dir

    Raises:
        ValueError: If resolved path would escape base_dir

    Examples:
        >>> safe_output_path(Path("/data"), "file.pdf")
        Path('/data/file.pdf')
        >>> safe_output_path(Path("/data"), "../etc/passwd")  # Raises ValueError
    """
    base_dir = base_dir.resolve()
    target = (base_dir / filename).resolve()

    # Ensure target is within base_dir (prevents path traversal)
    if not target.is_relative_to(base_dir):
        raise ValueError(f"Path traversal detected: {filename}")

    return target


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Remove invalid characters from filename and enforce length limits.

    Args:
        filename: Raw filename to sanitize
        max_length: Maximum filename length (default: 255 for most filesystems)

    Returns:
        Sanitized filename safe for filesystem use

    Note:
        - Removes characters: < > : " / \\ | ? * and control chars (0x00-0x1f)
        - Strips leading/trailing dots and spaces
        - Preserves file extensions when truncating
        - Returns 'unnamed' if result would be empty

    Examples:
        >>> sanitize_filename("file:name?.pdf")
        'file_name_.pdf'
        >>> sanitize_filename(" .hidden ")
        'hidden'
    """
    # Remove/replace invalid filesystem characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Enforce length limit while preserving extension
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if ext:
            filename = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            filename = name[:max_length]

    return filename or 'unnamed'
