# Companies House Scraper - Claude Code Guide

## Project Overview

A Python-based tool for downloading company data and documents from the UK Companies House API. Built with security, rate limiting, and resume capability as core features.

**Purpose**: Enable offline analysis of UK company records (profiles, officers, filings, documents) while respecting API rate limits and implementing proper security practices.

## Architecture

See `.private/dev/ARCHITECTURE.md` for comprehensive design documentation including:
- System architecture diagrams
- API endpoint mappings
- Design patterns and implementation details
- 42 identified issues and their solutions
- Security implementation strategies

## Key Files

### Core Application (4 files)

**scraper.py** (456 lines) - Main CLI and orchestration
- Click-based CLI with 6 options
- Company number validation and normalization
- Progress tracking (tqdm or simple counter)
- Bulk processing support
- Dry-run mode
- API key redaction in logs via `SensitiveDataFilter`

**api_client.py** (631 lines) - API wrapper with rate limiting
- `RateLimiter` class - Thread-safe token bucket (600 req/5min)
- `CompaniesHouseAPI` class - All 8 data endpoints
- Separate sessions for Data API and Document API
- Automatic pagination with safeguards
- Comprehensive error handling

**downloader.py** (544 lines) - Document downloads and organization
- PDF and XBRL downloads with streaming
- 7-category filing organization
- Content-type and size validation
- Atomic progress tracking
- Metadata preservation
- Summary generation

**validators.py** (147 lines) - Input validation and security
- Company number validation (UK format)
- API key validation
- Filename sanitization (injection prevention)
- Path traversal prevention

### Supporting Files

**requirements.txt** - Dependencies (all pinned)
- requests==2.31.0
- python-dotenv==1.0.0
- click==8.1.7
- tqdm==4.66.1 (optional)

**.env** (git-ignored) - Configuration
- `COMPANIES_HOUSE_API_KEY` - Required
- Optional: OUTPUT_DIR, MAX_RETRIES, rate limit settings

**.gitignore** - Excludes:
- Environment files (.env, .env.*)
- Downloads and data
- Logs, cache, temporary files
- Python artifacts, IDE files

## Directory Structure

```
companies-house-scraper/
├── scraper.py              # Main CLI
├── api_client.py           # API client + rate limiter
├── downloader.py           # Document downloads
├── validators.py           # Input validation
├── logging_filter.py       # API key redaction (legacy)
├── requirements.txt        # Dependencies
├── .env                    # Your API key (git-ignored)
├── .env.example            # Template
├── .gitignore             # Git exclusions
├── README.md              # User documentation
├── CLAUDE.md              # This file
├── scripts/               # Utility scripts
│   ├── validate_download.py     # Data validation
│   └── cleanup_duplicates.py    # Deduplication
├── examples/              # Example files
│   └── example_companies.txt
├── .private/              # Private docs (git-ignored)
│   └── dev/
│       ├── ARCHITECTURE.md         # Design docs
│       ├── BUILD_LOG.md            # Implementation log
│       └── VALIDATION_STRATEGY.md  # Validation procedures
└── downloads/             # Downloaded data (git-ignored)
    └── {company_number}/
        ├── logs/
        ├── *.json (8 files)
        └── accounts/, confirmations/, etc.
```

## Common Tasks

### Running the Scraper

```bash
# Single company
python scraper.py 00000006

# Dry run (preview)
python scraper.py 00000006 --dry-run

# With filters
python scraper.py 00000006 --types accounts,confirmations

# Bulk processing
python scraper.py --file companies.txt --verbose

# Resume interrupted download
python scraper.py 00000006 --resume
```

### Validating Downloads

```bash
# Validate single company
python scripts/validate_download.py 00000006

# Clean duplicates
python scripts/cleanup_duplicates.py 00000006
```

### Adding New Features

1. Check `.private/dev/ARCHITECTURE.md` for existing patterns
2. Follow security guidelines (input validation, sanitization)
3. Update relevant module:
   - API endpoints → `api_client.py`
   - Download logic → `downloader.py`
   - CLI options → `scraper.py`
   - Validation → `validators.py`
4. Test with `--dry-run` first
5. Run security scan: `/audit-security`

### Modifying Rate Limits

Edit `api_client.py`:
```python
# In RateLimiter.__init__
self.max_requests = 600      # Requests allowed
self.window_seconds = 300    # Time window (5 min)
```

Or set via `.env`:
```bash
RATE_LIMIT_REQUESTS=600
RATE_LIMIT_WINDOW=300
```

### Adding Filing Categories

Edit `downloader.py`:
```python
FILING_CATEGORIES = {
    'accounts': ['AA', 'AC'],
    'confirmations': ['CS01'],
    'new_category': ['TYPE1', 'TYPE2'],  # Add here
    # ...
}
```

## Testing

### Unit Testing
No formal test suite yet (Phase 2+). Current validation:
- Import tests (all modules)
- Validator functions (company number, filename)
- CLI help command
- Integration test in `scraper.py`

### End-to-End Testing
```bash
# Dry run test
python scraper.py 00000006 --dry-run --verbose

# Small download test
python scraper.py 00000006 --types incorporation --verbose

# Validation test
python scripts/validate_download.py 00000006
```

### Test Companies
- `00000006` - MARINE AND GENERAL MUTUAL LIFE ASSURANCE SOCIETY
- `10616124` - WASE LIMITED (validated test case)

## Known Issues

See `.private/dev/ARCHITECTURE.md` "Unaddressed Issues" section (42 identified issues).

**Fixed in Phase 1:**
- ✅ All critical security issues (#9-17)
- ✅ Core architecture issues (#1-10)
- ✅ UX/reliability issues (#18-26)

**Deferred to Phase 2+:**
- Pydantic schema validation (#27-29)
- Dependency hashing (#30)
- Log rotation (#32)
- Parallel JSON fetching (#33)
- Bulk processing CSV summary (#35)

**Most Common Issues:**
1. iXBRL/HTML accounts (not PDF) - Expected behavior
2. Officer count mismatch - API caching, no impact
3. Rate limit delays - Normal behavior

## Security Best Practices

### Implemented Protections

1. **API Key Security**
   - Keys redacted from all logs via `SensitiveDataFilter`
   - Stored in `.env` (git-ignored)
   - Validated at startup

2. **Input Validation**
   - Company numbers validated (UK format)
   - Filenames sanitized (remove invalid chars)
   - Path traversal prevented

3. **Download Safety**
   - Content-type validation (PDF, XBRL only)
   - File size limits (50MB)
   - Streaming downloads (no large memory loads)
   - PDF magic bytes verification

4. **Network Safety**
   - Request timeouts (30s)
   - Rate limiting (600 req/5min)
   - Exponential backoff on errors

### Before Committing

Always run:
```bash
/audit-security
```

Never commit:
- `.env` files
- API keys or credentials
- Downloaded data (`downloads/`)
- Log files

## Development Workflow

### Starting New Feature

1. Check existing patterns in `.private/dev/ARCHITECTURE.md`
2. Create feature plan (optional: add to `.private/dev/`)
3. Implement in appropriate module
4. Test with `--dry-run` and `--verbose`
5. Validate with scripts
6. Run security scan
7. Update documentation if needed

### Code Style

Follow existing patterns:
- Type hints for function signatures
- Docstrings for classes and complex functions
- Security-first design (validate inputs)
- Comprehensive error handling
- Logging for debugging

### Error Handling Strategy

- **404 errors**: Log and skip (document not available)
- **429 errors**: Auto-wait via rate limiter
- **401 errors**: Stop and report (auth failed)
- **Network errors**: Retry with exponential backoff (3 attempts)
- **Validation errors**: Raise immediately with clear message

## Configuration

### Environment Variables

Required:
```bash
COMPANIES_HOUSE_API_KEY=your_key_here
```

Optional:
```bash
OUTPUT_DIR=./downloads
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=600
RATE_LIMIT_WINDOW=300
```

### Default Behaviors

- **Output**: `./downloads/{company_number}/`
- **Rate limit**: 600 requests per 5 minutes
- **Timeout**: 30 seconds per request
- **Max file size**: 50MB
- **Retries**: 3 attempts with exponential backoff
- **Progress**: tqdm if available, else simple counter

## API Reference

### Companies House APIs

**Data API**: `https://api.company-information.service.gov.uk`
- Company profile
- Officers
- Charges
- Filing history
- PSC
- Insolvency
- Exemptions
- UK establishments

**Document API**: `https://document-api.companieshouse.gov.uk`
- Document metadata
- PDF downloads
- XBRL downloads

Both use same authentication (API key as username, empty password).

### Rate Limits

- **600 requests per 5 minutes** (shared across both APIs)
- Automatic handling via `RateLimiter`
- Logs when waiting for rate limit cooldown

## Output Data Structure

### JSON Files (8 total)

1. `company_profile.json` - Company details
2. `officers.json` - Directors/secretaries
3. `charges.json` - Mortgages
4. `filing_history.json` - All filings
5. `psc.json` - Significant control
6. `insolvency.json` - Insolvency records
7. `exemptions.json` - Filing exemptions
8. `uk_establishments.json` - UK branches

### Document Categories (7 folders)

1. **accounts/** - Annual accounts (AA, AC)
2. **confirmations/** - Confirmation statements (CS01)
3. **incorporation/** - Formation documents (IN01)
4. **changes/** - Officer/address changes (CH01, TM01, etc.)
5. **mortgages/** - Charge documents (MR01, MR02, MR04)
6. **dissolutions/** - Dissolution notices (DS01, DS02)
7. **other/** - Uncategorized filings

### Metadata Files

Each PDF has accompanying `.meta.json`:
```json
{
  "filing_date": "2023-12-31",
  "filing_type": "AA",
  "description": "Annual accounts made up to 31 December 2023",
  "category": "accounts",
  "company_number": "00000006",
  "download_timestamp": "2026-01-16T14:30:00",
  "document_id": "abc123def"
}
```

## Troubleshooting

### Import Errors

Check virtual environment is activated:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### API Errors

Check API key is set:
```bash
cat .env | grep COMPANIES_HOUSE_API_KEY
```

### Download Failures

Check progress file:
```bash
cat downloads/00000006/download_progress.json | jq '.failed'
```

Use `--resume` to retry:
```bash
python scraper.py 00000006 --resume
```

### Rate Limit Issues

Normal behavior - scraper will log:
```
[INFO] Rate limit reached, sleeping 45.3s
```

To reduce rate limit pressure:
- Use `--types` to filter
- Process fewer companies at once
- Avoid running multiple scraper instances

## Performance Optimization

### Current Performance

For company with 150 filings:
- JSON collection: ~30s
- PDF downloads: ~5-10 minutes
- Total: ~10-15 minutes

### Optimization Options

1. **Filter by type** - Only download needed categories
2. **Batch processing** - Process related companies together
3. **Custom output** - Store on faster disk
4. **Resume capability** - Don't re-download existing files

## Dependencies Management

### Updating Dependencies

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade requests

# Re-freeze requirements
pip freeze > requirements.txt
```

### Version Compatibility

Current versions tested with:
- Python 3.8+
- requests 2.31.0
- python-dotenv 1.0.0
- click 8.1.7
- tqdm 4.66.1

## Contributing Guidelines

(For future contributors)

1. Read `.private/dev/ARCHITECTURE.md` first
2. Follow existing code style
3. Add validation for all inputs
4. Include error handling
5. Update documentation
6. Test with real API
7. Run security scan

## Resources

### Documentation

- `README.md` - User guide
- `CLAUDE.md` - This file (developer guide)
- `.private/dev/ARCHITECTURE.md` - System design
- `.private/dev/BUILD_LOG.md` - Implementation history
- `.private/dev/VALIDATION_STRATEGY.md` - Data validation

### External Resources

- [Companies House API Docs](https://developer.company-information.service.gov.uk/)
- [API Specifications](https://developer-specs.company-information.service.gov.uk/)
- [Developer Forum](https://forum.companieshouse.gov.uk/)

## Quick Reference

### File Locations

Scripts: `scripts/validate_download.py`, `scripts/cleanup_duplicates.py`
Examples: `examples/example_companies.txt`
Private docs: `.private/dev/ARCHITECTURE.md`, etc.
Config: `.env` (create from `.env.example`)

### Common Commands

```bash
# Run scraper
python scraper.py <company_number> [OPTIONS]

# Validate download
python scripts/validate_download.py <company_number>

# View help
python scraper.py --help
```

### Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add API key
```

---

**Need help?** Check README.md for user documentation or `.private/dev/ARCHITECTURE.md` for technical details.
