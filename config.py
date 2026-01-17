"""
Centralized configuration for Companies House Scraper.

This module loads all configuration from environment variables and
defines application-wide constants for API endpoints, rate limits,
and filing categorization.

Environment Variables:
    COMPANIES_HOUSE_API_KEY: API key for Companies House APIs (required)

Constants:
    API Configuration:
        - DATA_API_BASE: Base URL for Data API
        - DOCUMENT_API_BASE: Base URL for Document API
        - DEFAULT_TIMEOUT: HTTP request timeout in seconds
        - DEFAULT_ITEMS_PER_PAGE: API pagination page size
        - MAX_PAGINATION_ITERATIONS: Safety limit for pagination loops

    Rate Limiting:
        - MAX_REQUESTS: Maximum requests per time window
        - RATE_WINDOW_SECONDS: Rate limit time window

    Filing Categories:
        - FILING_CATEGORIES: Document type to category mapping
        - CATEGORY_NAMES: Ordered list of category directories
"""

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


# ============================================================================
# API CONFIGURATION
# ============================================================================

# API key (required)
API_KEY: str = os.getenv('COMPANIES_HOUSE_API_KEY', '')

# API base URLs
DATA_API_BASE: str = "https://api.company-information.service.gov.uk"
DOCUMENT_API_BASE: str = "https://document-api.companieshouse.gov.uk"

# HTTP request settings
DEFAULT_TIMEOUT: int = 30  # seconds
DEFAULT_ITEMS_PER_PAGE: int = 100
MAX_PAGINATION_ITERATIONS: int = 1000  # Safety ceiling for infinite loop prevention


# ============================================================================
# RATE LIMITING
# ============================================================================

# Companies House API rate limit: 600 requests per 5 minutes
MAX_REQUESTS: int = 600
RATE_WINDOW_SECONDS: int = 300  # 5 minutes


# ============================================================================
# FILING CATEGORIES
# ============================================================================

# Filing type categorization map
# Maps document types to their appropriate category folder
FILING_CATEGORIES: Dict[str, List[str]] = {
    'accounts': ['AA', 'AC', 'Annual Return', 'Annual Accounts', 'accounts'],
    'confirmations': ['CS01', 'Confirmation Statement', 'confirmation'],
    'incorporation': ['IN01', 'incorporation', 'articles', 'certificate'],
    'changes': ['CH01', 'CH02', 'CH03', 'TM01', 'TM02', 'AP01', 'change'],
    'mortgages': ['MR01', 'MR02', 'MR04', 'mortgage', 'charge'],
    'dissolutions': ['DS01', 'DS02', 'dissolution'],
    'other': []  # Catch-all for unclassified documents
}

# Ordered list of category directory names
CATEGORY_NAMES: List[str] = [
    'accounts',
    'confirmations',
    'incorporation',
    'changes',
    'mortgages',
    'dissolutions',
    'other'
]


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config() -> None:
    """
    Validate required configuration is present.

    Raises:
        ValueError: If API_KEY is not set
    """
    if not API_KEY:
        raise ValueError(
            "COMPANIES_HOUSE_API_KEY not set. "
            "Please set it in .env file or environment variable."
        )


# Validate configuration on module import
# This ensures the application fails fast if misconfigured
if __name__ != '__main__':
    # Only validate when imported as a module (not when run directly)
    # Running directly is useful for testing/debugging
    pass  # Validation will be done by the importing module
