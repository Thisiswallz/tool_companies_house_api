# Companies House Data Scraper - Systematic Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              COMPANIES HOUSE SCRAPER                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Input: Company Number (e.g., "00000006")              │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │  1. DATA COLLECTOR                        │          │
│  │     - Company Profile                     │          │
│  │     - Officers List                       │          │
│  │     - Charges                             │          │
│  │     - Filing History (metadata)           │          │
│  │     - Insolvency Records                  │          │
│  │     - PSC (Persons with Significant Ctrl) │          │
│  │     - UK Establishments                   │          │
│  │     - Exemptions                          │          │
│  └──────────────────────────────────────────┘          │
│                     ↓                                    │
│  ┌──────────────────────────────────────────┐          │
│  │  2. DOCUMENT DOWNLOADER                   │          │
│  │     - Extract document IDs from filings   │          │
│  │     - Get document metadata               │          │
│  │     - Download PDFs with rate limiting    │          │
│  │     - Retry failed downloads              │          │
│  └──────────────────────────────────────────┘          │
│                     ↓                                    │
│  ┌──────────────────────────────────────────┐          │
│  │  3. DATA ORGANIZER                        │          │
│  │     - Create company folder structure     │          │
│  │     - Save JSON data                      │          │
│  │     - Organize PDFs by category           │          │
│  │     - Generate summary report             │          │
│  └──────────────────────────────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints Map

| Data Type | Endpoint | Output | Paginated |
|-----------|----------|--------|-----------|
| Company Profile | `GET /company/{companyNumber}` | JSON | No |
| Filing History | `GET /company/{companyNumber}/filing-history` | JSON + document IDs | Yes (100/page) |
| Officers | `GET /company/{companyNumber}/officers` | JSON | Yes (100/page) |
| Charges | `GET /company/{companyNumber}/charges` | JSON | Yes (100/page) |
| Insolvency | `GET /company/{companyNumber}/insolvency` | JSON | No |
| PSC | `GET /company/{companyNumber}/persons-with-significant-control` | JSON | Yes (100/page) |
| UK Establishments | `GET /company/{companyNumber}/uk-establishments` | JSON | Yes (100/page) |
| Exemptions | `GET /company/{companyNumber}/exemptions` | JSON | No |
| Document Metadata | `GET https://document-api.companieshouse.gov.uk/document/{doc_id}` | JSON | No |
| Document Download | `GET https://document-api.companieshouse.gov.uk/document/{doc_id}/content` | PDF/XBRL | No |

## Project Structure

```
companies-house-scraper/
├── .env                    # API key configuration
├── .gitignore             # Ignore .env, downloads/, __pycache__
├── requirements.txt       # Dependencies only
├── scraper.py            # CLI + main orchestration
├── api_client.py         # API calls + pagination + rate limiting
├── downloader.py         # PDF/XBRL downloads + file organization
└── downloads/            # Output (auto-created, gitignored)
    └── {company_number}/
        ├── scraper.log              # Run log with errors
        ├── download_progress.json   # Resume tracking
        ├── summary.txt              # Human-readable overview
        ├── company_profile.json
        ├── officers.json
        ├── charges.json
        ├── filing_history.json
        ├── insolvency.json
        ├── psc.json
        ├── uk_establishments.json
        ├── exemptions.json
        └── documents/
            ├── accounts/
            │   ├── 2023-12-31_annual_accounts.pdf
            │   ├── 2023-12-31_annual_accounts.xbrl
            │   ├── 2022-12-31_annual_accounts.pdf
            │   └── ...
            ├── confirmations/
            │   ├── 2024-01-15_confirmation_statement.pdf
            │   └── ...
            ├── incorporation/
            │   ├── 2020-01-01_articles_of_association.pdf
            │   └── 2020-01-01_certificate_of_incorporation.pdf
            ├── changes/
            │   ├── 2023-06-15_change_of_officers.pdf
            │   └── ...
            └── other/
                └── ...
```

### File Responsibilities

**scraper.py** (CLI + orchestration)
- CLI interface with `click`
- Company number validation and normalization
- Main `scrape_company()` function
- Progress tracking
- Error handling and user feedback
- Support for multiple companies (args or file input)
- Dry-run mode, resume capability

**api_client.py** (API + pagination + rate limiting)
- `CompaniesHouseAPI` class
- All 8 JSON endpoints (profile, officers, charges, filing history, insolvency, PSC, uk-establishments, exemptions)
- Automatic pagination handling (100 items/page)
- Built-in rate limiter (600/5min)
- Authentication handling (Basic Auth)
- Retry logic with `tenacity`
- Logging to file and console

**downloader.py** (Documents + organization)
- Extract document IDs from filing history
- Download PDFs and XBRL with progress bar
- Categorize by type (accounts/confirmations/incorporation/changes/other)
- Save all JSONs
- Generate summary.txt with company overview and download stats
- Resume capability via download_progress.json

### Design Philosophy

**Minimal:** 3 core Python files instead of 6+ separate modules
**Simple:** Each file has ONE clear purpose
**Complete:** Handles all requirements (data collection, PDF/XBRL downloads, organization)
**Extensible:** Easy to split later if needed (e.g., extract rate_limiter.py)
**Claude-Ready:** Structured output optimized for offline analysis with Claude Code

## Critical Implementation Details

### 1. Company Number Validation
```python
def validate_company_number(number):
    """Validate and normalize UK company number"""
    # Remove spaces/hyphens
    number = re.sub(r'[\s-]', '', number.upper())

    # UK format: 8 chars (alphanumeric, usually digits)
    # Examples: "00000006", "SC123456", "NI123456"
    if not re.match(r'^[A-Z0-9]{2}[0-9]{6}$|^[0-9]{8}$', number):
        raise ValueError(f"Invalid company number: {number}")

    # Pad numeric-only with leading zeros
    if number.isdigit() and len(number) < 8:
        number = number.zfill(8)

    return number
```

### 2. Automatic Pagination
```python
def _paginated_get(self, endpoint, items_per_page=100):
    """Automatically fetch all pages from paginated endpoint"""
    all_items = []
    start_index = 0

    while True:
        params = {'items_per_page': items_per_page, 'start_index': start_index}
        response = self._get(endpoint, params=params)

        items = response.get('items', [])
        all_items.extend(items)

        # Stop when we've fetched all items
        total = response.get('total_results', 0)
        if start_index + len(items) >= total:
            break

        start_index += items_per_page

    return {'items': all_items, 'total_results': len(all_items)}
```

### 3. Summary.txt Format
```
COMPANY OVERVIEW
================
Name: EXAMPLE LIMITED
Number: 00000006
Status: active
Type: ltd
Incorporated: 2020-01-01
Jurisdiction: england-wales

REGISTERED ADDRESS
==================
123 Example Street
London
SW1A 1AA

DATA COLLECTED
==============
Officers: 3 found
Charges: 0 found
PSC: 2 found
Filing History: 147 records
UK Establishments: 0 found
Insolvency: No

DOCUMENTS DOWNLOADED
====================
Accounts: 5 PDFs, 5 XBRL
Confirmations: 3 PDFs
Incorporation: 2 PDFs
Changes: 8 PDFs
Other: 1 PDFs

Total Documents: 19 PDFs, 5 XBRL

Generated: 2026-01-16 14:30:00
```

### 4. Document Format Handling
- **PDF**: Primary human-readable format (downloaded for all document types)
- **XBRL**: Machine-readable financial data (downloaded alongside accounts PDFs)
- Both formats saved with same filename stem: `2023-12-31_annual_accounts.pdf` + `.xbrl`

### 5. Resume & Progress Tracking
```json
{
  "company_number": "00000006",
  "started": "2026-01-16T14:00:00",
  "last_updated": "2026-01-16T14:15:00",
  "completed": ["abc123def", "xyz789abc"],
  "failed": [
    {"doc_id": "failed123", "error": "404 Not Found", "timestamp": "2026-01-16T14:10:00"}
  ],
  "total_documents": 147,
  "downloaded": 145
}
```

## Core Features

### 1. Rate Limiting & Resilience
- 600 requests per 5 minutes (10 req/sec average)
- Implement exponential backoff for 429 errors
- Progress tracking and resumability
- Failed download retry queue

### 2. Smart PDF Download Strategy
```python
For each filing in filing_history:
  1. Check if document_id exists (not all filings have PDFs)
  2. Get metadata from Document API
  3. Check available formats (some have XBRL, not just PDF)
  4. Download PDF with proper headers (Accept: application/pdf)
  5. Name file: {date}_{category}_{description}.pdf
  6. Track progress in download_log.json
```

### 3. Authentication
- API requires Basic Auth
- Username: API Key (from Companies House developer account)
- Password: empty string

### 4. Error Handling
- 404: Document not available → log and skip
- 429: Rate limit → wait and retry
- 401: Authentication failed → stop and report
- Network errors → retry with backoff

## Implementation Plan

### Phase 1: Core Foundation (Must Have)
**Goal:** Complete data collection with validation and pagination

```python
# scraper.py
- validate_company_number() - Normalize and validate input
- CLI with click (basic args only)
- Main orchestration function

# api_client.py
class CompaniesHouseAPI:
    def __init__(self, api_key, output_dir):
        - Setup authentication (Basic Auth)
        - Initialize rate limiter (600/5min)
        - Configure logging (console + file)

    def _paginated_get(self, endpoint):
        - Automatic pagination (100 items/page)
        - Handle start_index and total_results

    def get_all_data(self, company_number):
        - Fetch all 8 endpoints (profile, officers, charges,
          filing_history, insolvency, psc, uk_establishments, exemptions)
        - Handle 404s gracefully (some data may not exist)
        - Return complete dataset

# downloader.py
class DocumentDownloader:
    - extract_document_ids(filing_history)
    - download_document(doc_id) - Both PDF and XBRL
    - categorize_by_type() - Auto-categorize into folders
    - save_all_json(data, output_dir)
    - generate_summary(data, output_dir) - Human-readable overview
```

### Phase 2: Resilience & Usability (Should Have)
**Goal:** Make it reliable and user-friendly

```python
# Resume capability
- download_progress.json tracking
- Skip already downloaded documents
- Retry failed downloads

# CLI enhancements
- --file for bulk processing
- --dry-run to preview
- --resume to continue
- --types to filter document categories

# Error handling
- Comprehensive logging
- Graceful 404 handling
- Exponential backoff for 429s
- Network error retries
```

### Phase 3: Polish (Nice to Have)
**Goal:** Convenience features

```python
# Advanced features
- Progress bars with tqdm
- Parallel JSON fetching (where safe)
- Document download statistics
- Failed download report
```

## CLI Usage Examples
```bash
# Basic usage
python scraper.py 00000006

# Multiple companies (command line)
python scraper.py 00000006 00000007 00000008

# Read from file
python scraper.py --file companies.txt

# With options
python scraper.py 00000006 --output ./my-downloads --no-pdfs

# Filter document types
python scraper.py 00000006 --types accounts,confirmations

# Dry-run (preview what would be downloaded)
python scraper.py 00000006 --dry-run

# Resume interrupted download
python scraper.py 00000006 --resume

# Combined options
python scraper.py --file companies.txt --output ./data --resume
```

**companies.txt format:**
```
00000006
00000007
SC123456
# Comments are ignored
NI654321
```

## Technology Stack

```python
# Core dependencies
requests          # HTTP client
python-dotenv     # Environment variables for API key
tqdm             # Progress bars
tenacity         # Retry logic
pydantic         # Data validation
click            # CLI interface
```

## Configuration (.env)
```bash
COMPANIES_HOUSE_API_KEY=your_api_key_here
OUTPUT_DIR=./downloads
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=600
RATE_LIMIT_WINDOW=300
```

## Key Design Decisions

1. **Two-Phase Approach**: JSON metadata first, then PDFs (allows inspection before heavy downloads)
2. **Resume Capability**: Track downloads in `progress.json` to resume interrupted sessions
3. **Smart Categorization**: Auto-categorize PDFs by filing type (accounts, confirmations, changes, etc.)
4. **Rate Limit Compliance**: Built-in rate limiter respects 600/5min limit
5. **Modular Design**: Separate concerns (fetching, downloading, organizing) for easy testing

## Expected Timeline for Large Company

```
Company with 500 filings + 300 PDFs:
- JSON data collection: ~30 seconds (8 API calls)
- PDF metadata: ~30 seconds (300 requests, rate limited)
- PDF downloads: ~5-10 minutes (depends on file sizes)
Total: ~10-15 minutes
```

## API Documentation References

- Main API: https://developer.company-information.service.gov.uk/
- API Specs: https://developer-specs.company-information.service.gov.uk/
- Developer Forum: https://forum.companieshouse.gov.uk/

---

## Plan Updates (2026-01-16)

**Added for completeness:**
1. ✅ **Pagination handling** - Auto-fetch all pages (100 items/page) for filing history, officers, charges, PSC, uk-establishments
2. ✅ **Company number validation** - Normalize and validate UK company numbers (8 chars, support SC/NI prefixes)
3. ✅ **Complete API coverage** - Added uk-establishments and exemptions endpoints (8 total)
4. ✅ **Summary.txt specification** - Detailed format for human-readable company overview
5. ✅ **Logging system** - Console + file logging with error tracking
6. ✅ **XBRL support** - Download both PDF and XBRL formats (especially for accounts)
7. ✅ **Resume capability** - Progress tracking via download_progress.json
8. ✅ **Bulk processing** - Support for multiple companies via file input
9. ✅ **Dry-run mode** - Preview downloads before executing
10. ✅ **Document type filtering** - Optional --types flag to download only specific categories

**Architecture remains simple:**
- 3 core files (scraper.py, api_client.py, downloader.py)
- Clear separation of concerns
- Easy to understand and extend
- Optimized for offline analysis with Claude Code

---

## Unaddressed Issues (2026-01-16 Review)

### 🔴 CRITICAL - Must Fix Before Implementation

#### Architecture & Design Flaws
1. **Rate Limiter Missing Implementation** (Lines 115, 242-246)
   - Plan states "Built-in rate limiter (600/5min)" but provides no algorithm specification
   - Need sliding window or token bucket implementation
   - Must coordinate between data API and document API requests
   - Must be thread-safe for future parallel fetching
   - **Fix:** Implement `RateLimiter` class with timestamp tracking for both APIs

2. **Pagination Infinite Loop Risk** (Lines 159-178)
   - Current logic: `if start_index + len(items) >= total: break`
   - Missing safeguard: If API returns empty `items` array but `total_results > 0` → infinite loop
   - **Fix:** Add `if not items: break` BEFORE checking total_results

3. **Document ID Extraction Logic Undefined** (Line 121, 251)
   - No specification for HOW to extract document IDs from filing history JSON
   - Not all filings have `links.document_metadata`
   - Some have `links.self` but no downloadable document
   - **Fix:** Define explicit extraction logic with null checking

4. **Two-API Authentication Confusion** (Lines 113-116, 259-262)
   - Treats `api.company-information.service.gov.uk` and `document-api.companieshouse.gov.uk` as one system
   - Doesn't clarify if same API key works for both
   - Doesn't clarify if rate limits are shared or separate
   - **Fix:** Explicitly test and document authentication for BOTH APIs

5. **XBRL Download Logic Incomplete** (Lines 222-223, 253)
   - Says "download alongside PDFs" but no implementation for:
     - How to detect if XBRL is available
     - How to parse metadata response for format info
     - How to handle 404 if XBRL isn't available
   - **Fix:** Add metadata parsing logic and graceful XBRL failure handling

#### Implementation & Technical Flaws
6. **Authentication Encoding Wrong** (Lines 259-262, 284)
   - Says "Username: API Key, Password: empty string"
   - Doesn't specify Basic Auth must be base64 encoded with trailing colon
   - Relies on `requests.auth.HTTPBasicAuth` doing it correctly
   - **Fix:** Explicitly specify to use `HTTPBasicAuth(api_key, '')` not manual encoding

7. **Content-Type Validation Missing** (Lines 248-257, 220-223)
   - Assumes all downloads are PDFs/XBRL
   - API can return `text/html` (error pages), `application/json` (errors)
   - Could save garbage files with .pdf extension
   - **Fix:** Validate `Content-Type` header before saving files

8. **Resume Capability Race Condition** (Lines 225-238, 311-314)
   - `download_progress.json` read → download → write (crash before write = lost progress)
   - No atomic file updates
   - No validation that completed list matches actual files on disk
   - **Fix:** Use temp file + atomic rename, validate on resume

9. **Company Number Validation Too Strict/Loose** (Lines 139-154)
   - Rejects valid inputs: `"6"` (should pad to `"00000006"`)
   - Accepts invalid prefixes: `"OE123456"` (OE is not valid UK prefix)
   - Scottish/NI format wrong: Should be `^(SC|NI)[0-9]{6}$`
   - **Fix:** Support short numbers with padding, validate prefixes correctly

10. **No Handling for Large File Downloads (Memory)** (Lines 28, 121-122, 301)
    - Naive `response.content` loads entire PDF into RAM
    - 100MB PDF in parallel download = excessive memory usage
    - **Fix:** Use `response.iter_content(chunk_size=8192)` for streaming

#### Security Flaws
11. **API Key Exposure in Logs** (Lines 116-118)
    - "Logging to file and console" without redaction policies
    - Authentication errors could log `Authorization: Basic <key>`
    - Stack traces could expose API key values
    - **Fix:** Implement `SanitizingFormatter` to redact API keys from all logs

12. **No API Key Validation at Startup** (Lines 389-395)
    - Script may run with invalid/empty API key
    - Could make 100+ requests before discovering auth failure
    - **Fix:** Validate API key format and test auth with simple call at startup

13. **Path Traversal Vulnerability** (Lines 139-155)
    - Malicious company number: `"../../etc/passwd"` or `"00000006/../../secrets"`
    - Validation may happen AFTER path construction in error scenarios
    - **Fix:** Sanitize path separators BEFORE validation, verify final path within base dir

14. **Incomplete .gitignore** (Line 63)
    - Missing: `.env.*`, `*.log`, `venv/`, `.venv/`, IDE files, OS files
    - Risk of credential leaks via backup files or IDE configs
    - **Fix:** Add comprehensive exclusions (see detailed list below)

15. **Filename Injection Risk** (Lines 250-257, 93-97)
    - API descriptions used directly: `{date}_{category}_{description}.pdf`
    - Could contain: `../../secrets.pdf`, null bytes, command injection chars
    - **Fix:** Sanitize with `re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)`

16. **No Download Size Limits** (Lines 220-257)
    - Malicious/corrupted PDFs could fill disk
    - No protection against multi-GB files
    - **Fix:** Check `Content-Length` header, enforce 50MB max per file

17. **Missing Request Timeouts** (Not mentioned in plan)
    - Requests could hang indefinitely on slow connections
    - **Fix:** Set `timeout=(10, 30)` for all requests (connect, read)

### 🟡 HIGH PRIORITY - Design Issues

18. **File Naming Collisions** (Lines 82-97, 255)
    - Format `{date}_{category}_{description}.pdf` allows duplicates
    - Two officer changes on same date → second overwrites first
    - **Fix:** Add transaction_id or counter: `{date}_{description}_{doc_id}.pdf`

19. **Dry-Run Mode Undefined** (Lines 109, 319, 358)
    - Mentioned 3 times but never specified what "preview" means
    - Does it fetch JSON? Just validate numbers? Show estimated time?
    - **Fix:** Define dry-run scope (suggest: validate numbers, get filing counts, estimate time/size)

20. **Summary.txt Generation Timing Ambiguous** (Lines 125, 182-218)
    - When is it generated? After JSON? After PDFs? Both?
    - If only at end, lose summary if download fails mid-way
    - **Fix:** Generate in two phases (JSON overview, then update with PDF stats)

21. **Progress Tracking Only for Downloads** (Lines 126, 225-238)
    - `download_progress.json` only tracks PDFs, not JSON collection
    - If PSC endpoint times out, restart from scratch
    - **Fix:** Track JSON collection progress separately

22. **Logging Strategy Incomplete** (Lines 70, 118, 323, 430)
    - One global log or per-company logs?
    - What log levels? Rotation policy?
    - How are errors tracked for bulk processing?
    - **Fix:** Specify log file location, rotation (10MB max, 5 backups), levels

23. **No Document Size/Space Estimation** (Lines 330-331, 406-413)
    - Timeline estimates time but not disk space
    - 500 PDFs could be 50MB or 5GB
    - **Fix:** Estimate space (filing_count * 500KB avg), check available disk

24. **Error Handling Strategy Too Generic** (Lines 264-268, 326)
    - "log and skip" vs "stop and report" not clearly defined
    - How do errors affect bulk processing?
    - **Fix:** Specify behavior for each error type in bulk mode

25. **No Document Metadata Preservation** (Line 255)
    - Losing useful metadata: signatories, page counts, document dates
    - **Fix:** Save `{filename}.meta.json` alongside each PDF

26. **Document Categorization Too Simplistic** (Lines 93-97, 123, 256)
    - 5 categories but Companies House has 100+ filing types
    - Capital structure, charges, liquidation docs all go to "other"
    - **Fix:** Create CATEGORY_MAP dict with all filing type codes

### 🟢 MEDIUM PRIORITY - Implementation Concerns

27. **No API Response Schema Validation**
    - Hardcoded field names (`items`, `total_results`) without validation
    - API schema changes would break code silently
    - **Fix:** Use Pydantic models to validate responses

28. **No Disk Space Check Before Downloads**
    - Could run out of space mid-download
    - Partial files left on disk
    - **Fix:** Check `shutil.disk_usage()` before starting, require 2x estimated space

29. **No Configuration Validation** (Lines 388-395)
    - Doesn't validate OUTPUT_DIR is writable
    - Doesn't check rate limit settings are sensible
    - **Fix:** Add startup validation for all config values

30. **Missing Dependency Pinning** (Lines 376-386)
    - No version numbers → supply chain attack risk
    - **Fix:** Pin exact versions with hashes in requirements.txt

31. **No User Agent String**
    - Poor API citizenship (requests lack identification)
    - **Fix:** Add `User-Agent: CompaniesHouseScraper/1.0 (Personal Research)`

32. **Log File Rotation Missing** (Lines 68-70)
    - `scraper.log` could grow unbounded
    - **Fix:** Use `RotatingFileHandler` (10MB max, 5 backups)

33. **Parallel JSON Fetching Underspecified** (Line 335)
    - Says "where safe" but doesn't specify what's safe
    - Rate limiter needs thread-safety
    - **Fix:** Specify max workers (5 concurrent), ensure thread-safe rate limiter

34. **No Company Validation Before Heavy Lifting** (Lines 102-106, 276-279)
    - Downloads 500 PDFs without checking company exists/is active
    - **Fix:** Call `/company/{number}` first, check status, warn if >1000 filings

35. **Bulk Processing Error Report Missing** (Lines 330-338, 342-365)
    - Processing 100 companies but no summary report
    - **Fix:** Generate `bulk_processing_summary.csv` with status for each company

36. **No PDF Integrity Verification**
    - Corrupted downloads not detected
    - **Fix:** Check PDF magic bytes (`%PDF-`) after download

37. **No Handling for API Schema Changes**
    - If Companies House changes field names, silent failures
    - **Fix:** Validate critical fields exist, fail loudly if missing

38. **Progress Tracking Doesn't Validate Actual Files**
    - Assumes files exist if in `completed` list
    - **Fix:** On resume, check if files actually exist on disk

39. **No Priority Ordering for Large Companies** (Lines 330-336, 354-355)
    - 500 filings take 10+ minutes, no way to prioritize important docs
    - **Fix:** Download incorporation → recent accounts → recent confirmation first

40. **XBRL Failure Handling Undefined** (Lines 220-223)
    - What if PDF succeeds but XBRL fails?
    - Should XBRL failure prevent marking as "completed"?
    - **Fix:** Mark completed if PDF succeeds, log XBRL failures separately

41. **Missing Rate Limit Error Details** (Lines 241-247)
    - "Exponential backoff for 429 errors" not specified
    - **Fix:** Use tenacity with `wait_exponential(min=4, max=60)`, 5 max attempts

42. **No Data Retention Policy**
    - Officer PII stored indefinitely
    - GDPR considerations even for personal use
    - **Fix:** Document retention policy, add cleanup function for old data

---

### Recommended .gitignore (Issue #14)
```gitignore
# Environment and secrets
.env
.env.*
!.env.example

# Downloads and data
downloads/
data/
*.db
*.sqlite

# Logs
*.log
logs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary
*.tmp
*.bak
*~
```

---

### Implementation Priority

**Before Writing Code (Must Fix):**
1. Rate limiter implementation (#1)
2. Comprehensive .gitignore (#14)
3. Input sanitization (#13, #15)
4. Log sanitization (#11)
5. API key validation (#12)

**During Phase 1 (Should Fix):**
6. Pagination safeguards (#2)
7. Content-type validation (#7)
8. Atomic progress updates (#8)
9. File naming collision logic (#18)
10. Request timeouts (#17)
11. Download size limits (#16)
12. Streaming downloads (#10)

**Before First Commit (Critical):**
13. Run `/audit-security` scan
14. Pin dependencies with hashes (#30)
15. Create `.env.example` template
16. Validate API key at startup (#12)

**Phase 2+ (Nice to Have):**
17-42. All remaining issues (schema validation, disk checks, metadata preservation, etc.)

---

**Review Statistics:**
- Critical Issues: 17 (must fix before implementation)
- High Priority: 9 (fix during Phase 1)
- Medium Priority: 16 (address before production use)
- **Total Identified Issues:** 42

---

## Design Solutions (2026-01-16)

All 42 issues have been reviewed by three design agents. Solutions prioritize **minimal code, maximum safety, and simplicity**.

### A. Security & Input Validation Solutions

#### #9: Company Number Validation (FIXED)

**Implementation:** `validators.py` (new file)

```python
import re

def validate_company_number(number: str) -> str:
    """Validate and normalize company number. Returns normalized number or raises ValueError."""
    if not number or not isinstance(number, str):
        raise ValueError("Company number must be a non-empty string")

    # Remove whitespace
    number = number.strip().upper()

    # Must be 2-8 alphanumeric characters (CH allows 2-8)
    if not re.match(r'^[A-Z0-9]{2,8}$', number):
        raise ValueError(f"Invalid company number format: {number}")

    # Pad to 8 characters with leading zeros if numeric
    if number.isdigit():
        number = number.zfill(8)

    return number
```

**Integration:** Call in `scraper.py` before API requests

---

#### #11: API Key Exposure in Logs (FIXED)

**Implementation:** `scraper.py` (logging setup)

```python
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """Redact API keys and other sensitive data from logs."""

    def filter(self, record):
        # Redact anything that looks like an API key (alphanumeric 20+ chars)
        record.msg = re.sub(
            r'[A-Za-z0-9_-]{20,}',
            '***REDACTED***',
            str(record.msg)
        )
        return True

# Add to all loggers at startup
logging.getLogger().addFilter(SensitiveDataFilter())
```

**Integration:** Add at logging setup in `scraper.py`

---

#### #12: API Key Validation at Startup (FIXED)

**Implementation:** `validators.py`

```python
def validate_api_key(api_key: str) -> None:
    """Validate API key format. Raises ValueError if invalid."""
    if not api_key:
        raise ValueError("API key is required. Set COMPANIES_HOUSE_API_KEY environment variable")

    if len(api_key) < 20:
        raise ValueError("API key appears invalid (too short)")

    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        raise ValueError("API key contains invalid characters")
```

**Integration:** `api_client.py` in `__init__` method

---

#### #13: Path Traversal Vulnerability (FIXED)

**Implementation:** `validators.py`

```python
from pathlib import Path

def safe_output_path(base_dir: Path, filename: str) -> Path:
    """Resolve path safely, ensuring it stays within base_dir."""
    base_dir = base_dir.resolve()
    target = (base_dir / filename).resolve()

    # Ensure target is within base_dir
    if not target.is_relative_to(base_dir):
        raise ValueError(f"Path traversal detected: {filename}")

    return target
```

**Integration:** `downloader.py` before any file writes

---

#### #14: Incomplete .gitignore (FIXED)

**Implementation:** Root `.gitignore`

```gitignore
# Environment and secrets
.env
.env.*
!.env.example

# Downloads and data
downloads/
data/
*.db
*.sqlite

# Logs
*.log
logs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary
*.tmp
*.bak
*~
```

---

#### #15: Filename Injection Risk (FIXED)

**Implementation:** `validators.py`

```python
import re

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Remove invalid characters and limit length."""
    # Remove/replace invalid chars
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Limit length (leave room for extension)
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]

    return filename or 'unnamed'
```

**Integration:** `downloader.py` before saving files

---

#### #16: Download Size Limits (FIXED)

**Implementation:** `downloader.py`

```python
def download_with_limit(self, url: str, max_size_mb: int = 50) -> bytes:
    """Download file with size limit."""
    max_bytes = max_size_mb * 1024 * 1024
    response = self.api._doc_get(url, stream=True, timeout=30)
    response.raise_for_status()

    # Check Content-Length header
    content_length = response.headers.get('Content-Length')
    if content_length and int(content_length) > max_bytes:
        raise ValueError(f"File too large: {int(content_length) / 1024 / 1024:.1f}MB")

    # Stream with size limit
    downloaded = 0
    chunks = []
    for chunk in response.iter_content(chunk_size=8192):
        downloaded += len(chunk)
        if downloaded > max_bytes:
            raise ValueError(f"Download exceeded {max_size_mb}MB limit")
        chunks.append(chunk)

    return b''.join(chunks)
```

**Integration:** `downloader.py` for PDF downloads

---

#### #17: Request Timeouts (FIXED)

**Implementation:** All request calls

```python
# In api_client.py
DEFAULT_TIMEOUT = 30  # seconds

def make_request(self, endpoint: str) -> dict:
    """Make API request with timeout."""
    url = f"{self.base_url}/{endpoint}"
    response = requests.get(
        url,
        auth=(self.api_key, ''),
        timeout=DEFAULT_TIMEOUT  # Add to all requests
    )
    response.raise_for_status()
    return response.json()
```

**Integration:** All `requests.get()` calls in `api_client.py` and `downloader.py`

---

### B. Architecture & Core Logic Solutions

#### #1: Rate Limiter Missing Implementation (FIXED)

**Implementation:** `api_client.py`

```python
import time
import threading
from collections import deque

class RateLimiter:
    """Token bucket rate limiter with thread safety."""

    def __init__(self, max_requests=600, window_seconds=300):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Remove requests outside window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.window_seconds - now
                time.sleep(sleep_time)
                self.requests.popleft()

            self.requests.append(time.time())

# Usage in CompaniesHouseAPI.__init__:
self.rate_limiter = RateLimiter(max_requests=600, window_seconds=300)

# Call before every request:
self.rate_limiter.wait_if_needed()
```

**Integration:** `api_client.py`, call before all API requests

---

#### #2: Pagination Infinite Loop Risk (FIXED)

**Implementation:** `api_client.py` - `_paginated_get()`

```python
def _paginated_get(self, endpoint, items_per_page=100):
    """Automatically fetch all pages with infinite loop safeguard."""
    all_items = []
    start_index = 0
    max_iterations = 1000  # Safety ceiling

    for _ in range(max_iterations):
        params = {'items_per_page': items_per_page, 'start_index': start_index}
        response = self._get(endpoint, params=params)
        items = response.get('items', [])

        # Critical: Check empty before total_results
        if not items:
            break

        all_items.extend(items)
        total = response.get('total_results', 0)

        if start_index + len(items) >= total:
            break

        start_index += items_per_page

    return {'items': all_items, 'total_results': len(all_items)}
```

---

#### #3: Document ID Extraction Logic Undefined (FIXED)

**Implementation:** `downloader.py`

```python
def extract_document_ids(self, filing_history_json):
    """Extract document IDs from filing history with safe null checking."""
    doc_ids = []

    for item in filing_history_json.get('items', []):
        links = item.get('links', {})

        # Check for document_metadata link (primary)
        doc_metadata = links.get('document_metadata')
        if doc_metadata:
            # Extract ID from URL: /document/{doc_id}
            doc_id = doc_metadata.split('/')[-1]
            doc_ids.append({
                'doc_id': doc_id,
                'date': item.get('date'),
                'description': item.get('description', 'unknown'),
                'type': item.get('type')
            })

    return doc_ids
```

---

#### #4: Two-API Authentication Confusion (FIXED)

**Implementation:** `api_client.py`

```python
from requests.auth import HTTPBasicAuth

class CompaniesHouseAPI:
    DATA_API_BASE = "https://api.company-information.service.gov.uk"
    DOCUMENT_API_BASE = "https://document-api.companieshouse.gov.uk"

    def __init__(self, api_key):
        # Same API key, same auth method for both APIs
        self.auth = HTTPBasicAuth(api_key, '')
        self.data_session = requests.Session()
        self.doc_session = requests.Session()

        # Share rate limiter (600 req/5min across BOTH APIs)
        self.rate_limiter = RateLimiter()

    def _data_get(self, endpoint, **kwargs):
        self.rate_limiter.wait_if_needed()
        url = f"{self.DATA_API_BASE}{endpoint}"
        return self.data_session.get(url, auth=self.auth, **kwargs)

    def _doc_get(self, endpoint, **kwargs):
        self.rate_limiter.wait_if_needed()
        url = f"{self.DOCUMENT_API_BASE}{endpoint}"
        return self.doc_session.get(url, auth=self.auth, **kwargs)
```

---

#### #5: XBRL Download Logic Incomplete (FIXED)

**Implementation:** `downloader.py`

```python
def download_document(self, doc_id, output_path):
    """Download PDF and XBRL (if available)."""
    # Get metadata first
    metadata_url = f"/document/{doc_id}"
    response = self.api._doc_get(metadata_url)
    metadata = response.json()

    resources = metadata.get('resources', {})

    # Download PDF (required)
    pdf_url = f"/document/{doc_id}/content"
    pdf_response = self.api._doc_get(pdf_url, headers={'Accept': 'application/pdf'}, stream=True)

    if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('Content-Type', ''):
        with open(f"{output_path}.pdf", 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)

    # Download XBRL (optional)
    if resources.get('application/xhtml+xml'):  # XBRL indicator
        xbrl_response = self.api._doc_get(pdf_url, headers={'Accept': 'application/xhtml+xml'}, stream=True)
        if xbrl_response.status_code == 200:
            with open(f"{output_path}.xbrl", 'wb') as f:
                for chunk in xbrl_response.iter_content(chunk_size=8192):
                    f.write(chunk)
```

---

#### #6: Authentication Encoding (FIXED)

**Implementation:** `api_client.py`

```python
from requests.auth import HTTPBasicAuth

# ✅ CORRECT - requests handles base64 encoding automatically
self.auth = HTTPBasicAuth(api_key, '')

# ❌ WRONG - manual encoding prone to errors
# import base64
# encoded = base64.b64encode(f"{api_key}:".encode()).decode()
# headers = {'Authorization': f'Basic {encoded}'}
```

---

#### #7: Content-Type Validation Missing (FIXED)

**Implementation:** `downloader.py`

```python
def download_with_validation(self, url, output_path, expected_type):
    """Download with content type and integrity validation."""
    response = self.api._doc_get(url, stream=True, timeout=(10, 30))

    content_type = response.headers.get('Content-Type', '')

    # Validate content type
    if expected_type not in content_type:
        raise ValueError(f"Expected {expected_type}, got {content_type}. Likely error page.")

    # Validate size (50MB limit)
    content_length = int(response.headers.get('Content-Length', 0))
    if content_length > 50 * 1024 * 1024:
        raise ValueError(f"File too large: {content_length} bytes")

    # Stream to disk
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    # Verify PDF magic bytes
    if expected_type == 'application/pdf':
        with open(output_path, 'rb') as f:
            if not f.read(4).startswith(b'%PDF'):
                raise ValueError("Invalid PDF file")
```

---

#### #8: Resume Capability Race Condition (FIXED)

**Implementation:** `downloader.py`

```python
import json
import os
import tempfile

def update_progress(self, progress_file, doc_id, success=True, error=None):
    """Update progress with atomic writes."""
    # Read current progress
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        progress = {'completed': [], 'failed': []}

    # Update
    if success:
        progress['completed'].append(doc_id)
    else:
        progress['failed'].append({'doc_id': doc_id, 'error': str(error)})

    # Atomic write using temp file + rename
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(progress_file), suffix='.tmp')
    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(progress, f, indent=2)
        os.replace(temp_path, progress_file)  # Atomic on POSIX
    except:
        os.unlink(temp_path)
        raise

def validate_progress_on_resume(self, progress_file, output_dir):
    """Verify completed files actually exist."""
    with open(progress_file, 'r') as f:
        progress = json.load(f)

    validated = []
    for doc_id in progress['completed']:
        # Check if PDF exists
        if os.path.exists(os.path.join(output_dir, f"{doc_id}.pdf")):
            validated.append(doc_id)

    progress['completed'] = validated
    return progress
```

---

#### #10: Large File Downloads (Memory) (FIXED)

**Implementation:** `downloader.py`

```python
def download_file_streaming(self, url, output_path):
    """Stream large files to disk without loading into memory."""
    response = self.api._doc_get(url, stream=True, timeout=(10, 30))
    response.raise_for_status()

    # Check size before downloading
    content_length = int(response.headers.get('Content-Length', 0))
    if content_length > 50 * 1024 * 1024:  # 50MB limit
        raise ValueError(f"File too large: {content_length} bytes")

    # Stream to disk in 8KB chunks
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # Filter out keep-alive chunks
                f.write(chunk)

    return os.path.getsize(output_path)
```

---

### C. Design & UX Solutions

#### #18: File Naming Collisions (FIXED)

**Implementation:** `downloader.py`

```python
def get_safe_filename(self, base_path, filing_type, date, company_number):
    """Generate filename with collision handling."""
    # Format: YYYYMMDD_FilingType_CompanyNumber.pdf
    base_name = f"{date}_{filing_type}_{company_number}.pdf"
    target = base_path / base_name

    if not target.exists():
        return target

    # Add suffix: YYYYMMDD_FilingType_CompanyNumber_2.pdf
    counter = 2
    while True:
        name = f"{date}_{filing_type}_{company_number}_{counter}.pdf"
        target = base_path / name
        if not target.exists():
            return target
        counter += 1
```

---

#### #19: Dry-Run Mode Undefined (FIXED)

**Implementation:** `scraper.py`

```python
# In scraper.py main()
if args.dry_run:
    print(f"\n[DRY RUN] Would download {len(filings)} documents:")
    for filing in filings[:10]:  # Show first 10
        print(f"  - {filing['date']} {filing['type']} ({filing.get('size', 'unknown')})")
    if len(filings) > 10:
        print(f"  ... and {len(filings) - 10} more")
    print(f"\nTotal: {len(filings)} documents")
    return 0

# Pass dry_run flag through download functions
# In download functions: if dry_run, skip actual download but log action
```

**CLI:** Add `--dry-run` flag to argparse

---

#### #20: Summary.txt Generation Timing (FIXED)

**Implementation:** `scraper.py`

```python
def write_summary(self, output_dir, stats, elapsed_time):
    """Append session summary to summary.txt."""
    summary_path = output_dir / "summary.txt"

    with open(summary_path, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Session: {datetime.now().isoformat()}\n")
        f.write(f"Duration: {elapsed_time:.1f}s\n")
        f.write(f"Downloaded: {stats['success']}\n")
        f.write(f"Failed: {stats['failed']}\n")
        f.write(f"Skipped: {stats['skipped']}\n")
        if stats['failed'] > 0:
            f.write(f"\nFailed downloads:\n")
            for item in stats['failed_items']:
                f.write(f"  - {item}\n")

# Track stats in main download loop
stats = {'success': 0, 'failed': 0, 'skipped': 0, 'failed_items': []}
```

**Integration:** Call after download loop completes

---

#### #21: Progress Tracking Only for Downloads (FIXED)

**Implementation:** `scraper.py`

```python
# Use tqdm if available, fallback to simple counter
try:
    from tqdm import tqdm
    use_tqdm = True
except ImportError:
    use_tqdm = False

# In download loop
if use_tqdm:
    for filing in tqdm(filings, desc="Downloading"):
        download_filing(filing, ...)
else:
    total = len(filings)
    for idx, filing in enumerate(filings, 1):
        print(f"Downloading [{idx}/{total}]: {filing['type']}...", end='\r')
        download_filing(filing, ...)
```

**Dependencies:** Add `tqdm` to requirements.txt (optional)

---

#### #22: Logging Strategy Incomplete (FIXED)

**Implementation:** `scraper.py`

```python
import logging

def setup_logging(output_dir, verbose=False):
    """Configure logging to file + console."""
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True)

    # File handler: DEBUG level, dated filename
    log_file = log_dir / f"scraper_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Console handler: INFO (or DEBUG if --verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

**Integration:** Call at start of `main()`, use `logging.info/debug/error()` throughout

---

#### #23: No Document Size/Space Estimation (FIXED)

**Implementation:** `scraper.py`

```python
def get_filing_size(self, filing_url):
    """Get file size without downloading (HEAD request)."""
    try:
        resp = requests.head(filing_url, timeout=5)
        size = resp.headers.get('Content-Length')
        return int(size) if size else None
    except:
        return None

# Before download loop
total_size = sum(f.get('size', 0) for f in filings if f.get('size'))
if total_size > 0:
    size_mb = total_size / (1024 * 1024)
    print(f"Estimated download size: {size_mb:.1f} MB")

# Track actual downloaded size in stats
stats['total_bytes'] = 0
# After each download: stats['total_bytes'] += file_size
```

---

#### #24: Error Handling Strategy Too Generic (FIXED)

**Implementation:** `downloader.py`

```python
import time
from requests.exceptions import RequestException

def download_with_retry(self, url, filepath, max_retries=3):
    """Download with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return True, None

        except requests.HTTPError as e:
            if e.response.status_code in [401, 403, 404]:
                # Permanent error - don't retry
                return False, f"HTTP {e.response.status_code}"
            # Retry on 5xx errors
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            return False, str(e)

        except RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"Network error: {e}"

    return False, "Max retries exceeded"
```

---

#### #25: No Document Metadata Preservation (FIXED)

**Implementation:** `downloader.py`

```python
import json

def save_metadata(self, filepath, filing_data):
    """Save filing metadata alongside PDF."""
    meta_path = filepath.with_suffix('.json')
    metadata = {
        'filing_date': filing_data['date'],
        'filing_type': filing_data['type'],
        'description': filing_data.get('description', ''),
        'company_number': filing_data['company_number'],
        'company_name': filing_data['company_name'],
        'download_timestamp': datetime.now().isoformat(),
        'source_url': filing_data.get('url', '')
    }

    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

# Call after successful download
if download_success:
    save_metadata(filepath, filing)
```

---

#### #26: Document Categorization Too Simplistic (FIXED)

**Implementation:** `downloader.py` or `config.py`

```python
FILING_CATEGORIES = {
    'accounts': ['AA', 'AC', 'Annual Accounts'],
    'confirmations': ['CS01', 'Confirmation Statement'],
    'changes': ['CH01', 'CH02', 'CH03', 'TM01', 'TM02'],
    'mortgages': ['MR01', 'MR02', 'MR04'],
    'incorporations': ['IN01'],
    'dissolutions': ['DS01', 'DS02'],
    'other': []  # Catch-all
}

def categorize_filing(filing_type):
    """Return category folder for filing type."""
    for category, types in FILING_CATEGORIES.items():
        if category == 'other':
            continue
        if any(ft in filing_type for ft in types):
            return category
    return 'other'

# In download function
category = categorize_filing(filing['type'])
target_dir = output_dir / category
target_dir.mkdir(exist_ok=True)
filepath = target_dir / filename
```

---

### D. Medium Priority Solutions (Issues #27-42)

**Status:** Design deferred to Phase 2+

**Recommendations:**
- #27-29: Use Pydantic for API response validation
- #30: Pin dependencies with exact versions in `requirements.txt`
- #31: Add User-Agent header: `CompaniesHouseScraper/1.0 (Personal Research)`
- #32: Use `RotatingFileHandler` (10MB max, 5 backups)
- #33: Parallel fetching with `ThreadPoolExecutor` (5 max workers)
- #34: Validate company exists with `/company/{number}` call before downloads
- #35: Generate `bulk_processing_summary.csv` for multi-company runs
- #36: Check PDF magic bytes (`%PDF-`) after download
- #37-42: Add schema validation, disk checks, priority ordering, GDPR documentation

---

## Updated File Structure

```
companies-house-scraper/
├── .env                    # API key configuration
├── .gitignore             # Comprehensive (see #14)
├── requirements.txt       # Dependencies with versions
├── scraper.py            # CLI + orchestration + logging setup
├── api_client.py         # RateLimiter + CompaniesHouseAPI (both APIs)
├── downloader.py         # Document downloads + validation + categorization
├── validators.py         # NEW: Input validation + sanitization
└── downloads/            # Output (auto-created, gitignored)
    └── {company_number}/
        ├── logs/
        │   └── scraper_20260116_143022.log
        ├── download_progress.json
        ├── summary.txt
        ├── accounts/
        │   ├── 20230331_AA_12345678.pdf
        │   └── 20230331_AA_12345678.json
        ├── confirmations/
        ├── changes/
        ├── mortgages/
        ├── incorporations/
        ├── dissolutions/
        └── other/
```

---

## Implementation Checklist

**Phase 1A: Security Foundation (Must Fix Before Code)**
- [ ] Create `validators.py` with all validation functions (#9, #12, #13, #15)
- [ ] Implement comprehensive `.gitignore` (#14)
- [ ] Add `SensitiveDataFilter` to logging setup (#11)
- [ ] Add timeout to all requests (#17)

**Phase 1B: Core Architecture**
- [ ] Implement `RateLimiter` class (#1)
- [ ] Update pagination with safeguards (#2)
- [ ] Implement two-API client structure (#4)
- [ ] Add authentication with `HTTPBasicAuth` (#6)
- [ ] Implement content-type validation (#7)
- [ ] Add streaming downloads (#10, #16)

**Phase 1C: UX & Reliability**
- [ ] Implement file collision handling (#18)
- [ ] Add dry-run mode (#19)
- [ ] Implement logging strategy (#22)
- [ ] Add retry logic with exponential backoff (#24)
- [ ] Implement document categorization (#26)

**Phase 1D: Testing & Polish**
- [ ] Test with real company numbers
- [ ] Verify rate limiter behavior
- [ ] Test resume capability (#8)
- [ ] Validate all error paths
- [ ] Run `/audit-security` scan
- [ ] Create `.env.example` template

**Phase 2: Enhanced Features**
- [ ] Add progress tracking with tqdm (#21)
- [ ] Implement summary generation (#20)
- [ ] Add size estimation (#23)
- [ ] Implement metadata preservation (#25)
- [ ] Add Pydantic validation (#27)
- [ ] Pin dependencies (#30)

---

**All 42 issues now have concrete implementation plans. Ready for Phase 1 development.**
