"""
Logging filter for sensitive data redaction.

This module provides the SensitiveDataFilter class that prevents
API keys and other sensitive data from being written to log files.

Usage:
    import logging
    from logging_filter import SensitiveDataFilter

    # Add to all loggers at startup
    logging.getLogger().addFilter(SensitiveDataFilter())
"""

import logging
import re


class SensitiveDataFilter(logging.Filter):
    """
    Redact API keys and other sensitive data from log messages.

    This filter prevents credentials from being logged by:
    - Redacting strings that look like API keys (20+ alphanumeric chars)
    - Replacing them with ***REDACTED*** in log output

    Examples:
        >>> handler = logging.StreamHandler()
        >>> handler.addFilter(SensitiveDataFilter())
        >>> logger.addHandler(handler)
        >>> logger.info("Using key: abc123xyz789...")  # Logs: Using key: ***REDACTED***
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by redacting sensitive data.

        Args:
            record: Log record to filter

        Returns:
            bool: Always True (allows record to be logged after redaction)
        """
        # Redact anything that looks like an API key (alphanumeric 20+ chars)
        record.msg = re.sub(
            r'[A-Za-z0-9_-]{20,}',
            '***REDACTED***',
            str(record.msg)
        )
        return True
