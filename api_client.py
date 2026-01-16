"""
Companies House API client with rate limiting and comprehensive endpoint support.

This module provides:
- RateLimiter: Token bucket rate limiter with thread safety
- CompaniesHouseAPI: Client for both Data API and Document API

Supports 8 data collection endpoints:
- Company profile
- Officers
- Filing history
- Charges
- Insolvency
- Persons with Significant Control (PSC)
- UK Establishments
- Exemptions
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from collections import deque

import requests
from requests.auth import HTTPBasicAuth

from validators import validate_api_key, validate_company_number


# Constants
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_ITEMS_PER_PAGE = 100
MAX_PAGINATION_ITERATIONS = 1000  # Safety ceiling for infinite loop prevention


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with thread safety.
    
    Implements Companies House API rate limit: 600 requests per 5 minutes.
    Uses a sliding window with thread-safe token bucket algorithm.
    
    Attributes:
        max_requests: Maximum number of requests allowed in window
        window_seconds: Time window in seconds (default: 300 = 5 minutes)
    """

    def __init__(self, max_requests: int = 600, window_seconds: int = 300):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()
        
        logger.info(
            f"Rate limiter initialized: {max_requests} requests per "
            f"{window_seconds} seconds"
        )

    def wait_if_needed(self) -> None:
        """
        Block if rate limit would be exceeded.
        
        This method is thread-safe and should be called before each API request.
        If the rate limit would be exceeded, it sleeps until a request slot
        becomes available.
        """
        with self.lock:
            now = time.time()
            
            # Remove requests outside the sliding window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            # If at capacity, wait until oldest request expires
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.window_seconds - now
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.requests.popleft()

            # Record this request
            self.requests.append(time.time())


class CompaniesHouseAPI:
    """
    Client for Companies House Data API and Document API.
    
    Provides methods for fetching company data from both APIs:
    - Data API: Company profiles, officers, filing history, etc. (JSON)
    - Document API: Document metadata and downloads (PDF/XBRL)
    
    Both APIs use the same API key with HTTPBasicAuth and share a rate limiter.
    
    Attributes:
        DATA_API_BASE: Base URL for Data API
        DOCUMENT_API_BASE: Base URL for Document API
        rate_limiter: Shared rate limiter for both APIs
    """

    DATA_API_BASE = "https://api.company-information.service.gov.uk"
    DOCUMENT_API_BASE = "https://document-api.companieshouse.gov.uk"

    def __init__(self, api_key: str):
        """
        Initialize API client.
        
        Args:
            api_key: Companies House API key
            
        Raises:
            ValueError: If API key is invalid
        """
        # Validate API key at startup
        validate_api_key(api_key)
        
        # Setup authentication (same for both APIs)
        self.auth = HTTPBasicAuth(api_key, '')
        
        # Create separate sessions for each API
        self.data_session = requests.Session()
        self.doc_session = requests.Session()
        
        # Add User-Agent header
        user_agent = "CompaniesHouseScraper/1.0 (Personal Research)"
        self.data_session.headers.update({'User-Agent': user_agent})
        self.doc_session.headers.update({'User-Agent': user_agent})
        
        # Shared rate limiter (600 requests per 5 minutes across BOTH APIs)
        self.rate_limiter = RateLimiter(max_requests=600, window_seconds=300)
        
        logger.info("CompaniesHouseAPI client initialized")

    def _data_get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make GET request to Data API.
        
        Args:
            endpoint: API endpoint (e.g., "/company/12345678")
            params: Query parameters
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            Response object
            
        Raises:
            requests.HTTPError: For HTTP errors (4xx, 5xx)
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.DATA_API_BASE}{endpoint}"
        logger.debug(f"Data API GET: {endpoint}")
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = DEFAULT_TIMEOUT
        
        response = self.data_session.get(
            url, 
            auth=self.auth, 
            params=params,
            **kwargs
        )
        
        # Log response status
        logger.debug(f"Response: {response.status_code} from {endpoint}")
        
        # Handle common error codes
        if response.status_code == 401:
            logger.error("Authentication failed - check API key")
            raise requests.HTTPError("401 Unauthorized - Invalid API key")
        elif response.status_code == 404:
            logger.warning(f"Resource not found: {endpoint}")
        elif response.status_code == 429:
            logger.error("Rate limit exceeded despite rate limiter")
            raise requests.HTTPError("429 Too Many Requests")
        elif response.status_code >= 500:
            logger.error(f"Server error: {response.status_code}")
        
        response.raise_for_status()
        return response

    def _doc_get(
        self, 
        endpoint: str, 
        **kwargs
    ) -> requests.Response:
        """
        Make GET request to Document API.
        
        Args:
            endpoint: API endpoint (e.g., "/document/{doc_id}")
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            Response object
            
        Raises:
            requests.HTTPError: For HTTP errors (4xx, 5xx)
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.DOCUMENT_API_BASE}{endpoint}"
        logger.debug(f"Document API GET: {endpoint}")
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = DEFAULT_TIMEOUT
        
        response = self.doc_session.get(url, auth=self.auth, **kwargs)
        
        logger.debug(f"Response: {response.status_code} from {endpoint}")
        
        # Handle common error codes
        if response.status_code == 401:
            logger.error("Authentication failed - check API key")
            raise requests.HTTPError("401 Unauthorized - Invalid API key")
        elif response.status_code == 404:
            logger.warning(f"Document not found: {endpoint}")
        elif response.status_code >= 500:
            logger.error(f"Server error: {response.status_code}")
        
        response.raise_for_status()
        return response

    def _paginated_get(
        self, 
        endpoint: str, 
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE
    ) -> Dict[str, Any]:
        """
        Automatically fetch all pages from a paginated endpoint.
        
        Implements infinite loop safeguards and proper pagination termination.
        
        Args:
            endpoint: API endpoint to paginate
            items_per_page: Number of items per page (default: 100)
            
        Returns:
            Dictionary with 'items' list and 'total_results' count
            
        Note:
            - Checks for empty items before total_results to avoid infinite loops
            - Enforces maximum iteration limit as safety ceiling
        """
        all_items = []
        start_index = 0
        
        for iteration in range(MAX_PAGINATION_ITERATIONS):
            params = {
                'items_per_page': items_per_page, 
                'start_index': start_index
            }
            
            response = self._data_get(endpoint, params=params)
            data = response.json()
            
            items = data.get('items', [])
            
            # CRITICAL: Check empty items BEFORE total_results
            # (prevents infinite loop if API returns incorrect total_results)
            if not items:
                logger.debug(f"No more items at start_index={start_index}")
                break
            
            all_items.extend(items)
            # API can return either 'total_count' or 'total_results' depending on endpoint
            total = data.get('total_count') or data.get('total_results', 0)

            logger.debug(
                f"Fetched {len(items)} items (total so far: {len(all_items)}/{total})"
            )

            # Primary termination: partial page indicates end of data
            # (more reliable than total_results which API sometimes reports as 0)
            if len(items) < items_per_page:
                logger.debug("Received partial page - reached end of pagination")
                break

            # Secondary check: if total_results is provided and valid, use it
            if total > 0 and len(all_items) >= total:
                logger.debug("Reached total_results count")
                break

            start_index += items_per_page
        else:
            # Loop completed without breaking (hit max iterations)
            logger.warning(
                f"Pagination stopped at max iterations ({MAX_PAGINATION_ITERATIONS})"
            )
        
        return {
            'items': all_items, 
            'total_results': len(all_items)
        }

    # ============================================================================
    # DATA COLLECTION ENDPOINTS (8 endpoints)
    # ============================================================================

    def get_company_profile(self, company_number: str) -> Dict[str, Any]:
        """
        Get company profile information.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Company profile data including:
            - company_name, company_number, company_status
            - registered_office_address
            - accounts, confirmation_statement
            - date_of_creation, type, jurisdiction
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails (404 if company not found)
            
        Example:
            >>> api.get_company_profile("00000006")
            {'company_name': 'EXAMPLE LTD', ...}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}"
        
        logger.info(f"Fetching company profile: {company_number}")
        response = self._data_get(endpoint)
        return response.json()

    def get_officers(self, company_number: str) -> Dict[str, Any]:
        """
        Get company officers (directors, secretaries, etc.).
        
        This endpoint is paginated and returns all pages automatically.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with:
            - items: List of officer records
            - total_results: Total number of officers
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails
            
        Example:
            >>> api.get_officers("00000006")
            {'items': [...], 'total_results': 5}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/officers"
        
        logger.info(f"Fetching officers for: {company_number}")
        return self._paginated_get(endpoint)

    def get_filing_history(self, company_number: str) -> Dict[str, Any]:
        """
        Get company filing history.
        
        This endpoint is paginated and returns all pages automatically.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with:
            - items: List of filing records (includes document_metadata links)
            - total_results: Total number of filings
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails
            
        Note:
            Each filing item may include links.document_metadata for downloadable docs.
            
        Example:
            >>> api.get_filing_history("00000006")
            {'items': [...], 'total_results': 150}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/filing-history"
        
        logger.info(f"Fetching filing history for: {company_number}")
        return self._paginated_get(endpoint)

    def get_charges(self, company_number: str) -> Dict[str, Any]:
        """
        Get company charges (mortgages and security interests).
        
        This endpoint is paginated and returns all pages automatically.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with:
            - items: List of charge records
            - total_results: Total number of charges
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails (404 if no charges)
            
        Example:
            >>> api.get_charges("00000006")
            {'items': [...], 'total_results': 2}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/charges"
        
        logger.info(f"Fetching charges for: {company_number}")
        return self._paginated_get(endpoint)

    def get_insolvency(self, company_number: str) -> Dict[str, Any]:
        """
        Get company insolvency information.
        
        This is NOT a paginated endpoint (single object response).
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Insolvency data (empty dict if company has no insolvency records)
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails (404 if no insolvency data)
            
        Example:
            >>> api.get_insolvency("00000006")
            {'cases': [...]}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/insolvency"
        
        logger.info(f"Fetching insolvency data for: {company_number}")
        
        try:
            response = self._data_get(endpoint)
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No insolvency data for {company_number}")
                return {}
            raise

    def get_psc(self, company_number: str) -> Dict[str, Any]:
        """
        Get Persons with Significant Control (PSC).
        
        This endpoint is paginated and returns all pages automatically.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with:
            - items: List of PSC records
            - total_results: Total number of PSCs
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails
            
        Example:
            >>> api.get_psc("00000006")
            {'items': [...], 'total_results': 1}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/persons-with-significant-control"
        
        logger.info(f"Fetching PSC for: {company_number}")
        return self._paginated_get(endpoint)

    def get_uk_establishments(self, company_number: str) -> Dict[str, Any]:
        """
        Get UK establishments (for overseas companies).
        
        This endpoint is paginated and returns all pages automatically.
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with:
            - items: List of establishment records
            - total_results: Total number of establishments
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails (404 if not overseas company)
            
        Example:
            >>> api.get_uk_establishments("FC000001")
            {'items': [...], 'total_results': 3}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/uk-establishments"
        
        logger.info(f"Fetching UK establishments for: {company_number}")
        
        try:
            return self._paginated_get(endpoint)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No UK establishments for {company_number}")
                return {'items': [], 'total_results': 0}
            raise

    def get_exemptions(self, company_number: str) -> Dict[str, Any]:
        """
        Get company exemptions.
        
        This is NOT a paginated endpoint (single object response).
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Exemptions data (empty dict if company has no exemptions)
            
        Raises:
            ValueError: If company number is invalid
            requests.HTTPError: If request fails (404 if no exemptions)
            
        Example:
            >>> api.get_exemptions("00000006")
            {'exemptions': {...}}
        """
        company_number = validate_company_number(company_number)
        endpoint = f"/company/{company_number}/exemptions"
        
        logger.info(f"Fetching exemptions for: {company_number}")
        
        try:
            response = self._data_get(endpoint)
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No exemptions for {company_number}")
                return {}
            raise

    def get_all_data(self, company_number: str) -> Dict[str, Any]:
        """
        Fetch all data for a company (all 8 endpoints).
        
        Convenience method that calls all data collection endpoints and
        aggregates results. Continues on 404 errors (some endpoints may not
        have data for all companies).
        
        Args:
            company_number: Company number (will be validated and normalized)
            
        Returns:
            Dictionary with keys:
            - profile: Company profile
            - officers: Officers list
            - filing_history: Filing history list
            - charges: Charges list
            - insolvency: Insolvency data
            - psc: PSC list
            - uk_establishments: UK establishments list
            - exemptions: Exemptions data
            - errors: Dict of endpoint -> error message for any failures
            
        Example:
            >>> data = api.get_all_data("00000006")
            >>> data['profile']['company_name']
            'EXAMPLE LTD'
            >>> len(data['officers']['items'])
            5
        """
        company_number = validate_company_number(company_number)
        logger.info(f"Fetching ALL data for: {company_number}")
        
        results = {
            'company_number': company_number,
            'errors': {}
        }
        
        # Define endpoints to fetch
        endpoints = [
            ('profile', self.get_company_profile),
            ('officers', self.get_officers),
            ('filing_history', self.get_filing_history),
            ('charges', self.get_charges),
            ('insolvency', self.get_insolvency),
            ('psc', self.get_psc),
            ('uk_establishments', self.get_uk_establishments),
            ('exemptions', self.get_exemptions),
        ]
        
        # Fetch each endpoint
        for key, method in endpoints:
            try:
                results[key] = method(company_number)
                logger.info(f"✓ Fetched {key}")
            except requests.HTTPError as e:
                error_msg = f"{e.response.status_code}: {str(e)}"
                results['errors'][key] = error_msg
                results[key] = None
                logger.warning(f"✗ Failed to fetch {key}: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                results['errors'][key] = error_msg
                results[key] = None
                logger.error(f"✗ Failed to fetch {key}: {error_msg}")
        
        # Summary
        success_count = len([k for k in endpoints if results.get(k[0]) is not None])
        logger.info(
            f"Completed data fetch for {company_number}: "
            f"{success_count}/{len(endpoints)} endpoints successful"
        )
        
        return results
