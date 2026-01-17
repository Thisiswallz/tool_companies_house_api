# Companies House Data Scraper

A Python tool to download company data and documents from the UK Companies House API with built-in rate limiting, resume capability, and comprehensive data validation.

## Overview

This scraper provides complete access to Companies House public data:
- **Company profiles** - Basic company information, addresses, SIC codes
- **Officers** - Directors, secretaries, and their appointment history
- **PSC** - Persons with significant control
- **Charges** - Mortgages and security interests
- **Filing history** - Complete filing records with metadata
- **Documents** - Automatic PDF and XBRL downloads, organized by category
- **Insolvency** - Insolvency records and proceedings
- **UK Establishments** - Branch and establishment information

## Features

- **Complete data collection**: All 8 Companies House API endpoints
- **Document downloads**: Automatic PDF and XBRL download with categorization
- **Rate limiting**: Built-in 600 req/5min rate limiter respects API limits
- **Resume capability**: Continue interrupted downloads
- **Security focused**: Input validation, path traversal prevention, API key redaction in logs
- **Bulk processing**: Process multiple companies from file or command line
- **Progress tracking**: Visual progress bars with tqdm (optional)
- **Dry-run mode**: Preview downloads before executing
- **Type filtering**: Download only specific document categories

## Quick Start

### 1. Get API Key

1. Register at [Companies House Developer Hub](https://developer.company-information.service.gov.uk/)
2. Create an API key (free for personal use)
3. Keep your key handy for the next step

### 2. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Configure API Key

```bash
# Copy the example config
cp .env.example .env

# Edit .env and add your API key
# COMPANIES_HOUSE_API_KEY=your_key_here
```

### 4. Run Your First Download

```bash
# Preview what would be downloaded (dry run)
python scraper.py 00000006 --dry-run

# Download everything for company 00000006
python scraper.py 00000006
```

## Installation

### Option 1: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your API key
```

### Option 2: Using setup.sh (if available)

```bash
./setup.sh
# Follow prompts to add API key
```

## Usage

### Basic Usage

```bash
# Single company
python scraper.py 00000006

# Multiple companies (command line)
python scraper.py 00000006 00000007 SC123456

# Multiple companies (from file)
python scraper.py --file companies.txt

# Preview before downloading
python scraper.py 00000006 --dry-run
```

### Advanced Options

```bash
# Download only accounts and confirmations
python scraper.py 00000006 --types accounts,confirmations

# Custom output directory
python scraper.py 00000006 --output ./my-data

# Resume interrupted download
python scraper.py 00000006 --resume

# Enable debug logging
python scraper.py 00000006 --verbose

# Combined options
python scraper.py --file companies.txt \
  --types accounts,confirmations \
  --output ./data \
  --resume \
  --verbose
```

### Command-Line Options

```
Options:
  -f, --file PATH           File with company numbers (one per line)
  -o, --output PATH         Output directory (default: ./downloads)
  --dry-run                 Preview downloads without executing
  --resume                  Continue interrupted download
  --types TEXT              Filter by type: accounts,confirmations,etc.
  -v, --verbose            Enable debug logging
  --help                   Show help message
```

### Document Type Filters

Available types for `--types` option:
- `accounts` - Annual accounts, financial statements
- `confirmations` - Confirmation statements (CS01)
- `incorporation` - Articles of association, incorporation certificates
- `changes` - Director changes, address changes
- `mortgages` - Charges, mortgages (MR01, MR02, MR04)
- `dissolutions` - Dissolution notices
- `other` - Everything else

Example:
```bash
python scraper.py 00000006 --types accounts,confirmations,incorporation
```

## Output Structure

```
downloads/
└── {company_number}/
    ├── logs/
    │   └── scraper_YYYYMMDD_HHMMSS.log
    ├── download_progress.json      # Resume tracking
    ├── summary.txt                 # Human-readable summary
    ├── company_profile.json
    ├── officers.json
    ├── charges.json
    ├── filing_history.json
    ├── psc.json
    ├── insolvency.json
    ├── exemptions.json
    ├── uk_establishments.json
    └── accounts/
        ├── 20231231_AA_annual_accounts.pdf
        ├── 20231231_AA_annual_accounts.xbrl
        ├── 20231231_AA_annual_accounts.meta.json
        └── ...
    └── confirmations/
    └── incorporation/
    └── changes/
    └── mortgages/
    └── dissolutions/
    └── other/
```

### File Descriptions

**JSON Data Files:**
- `company_profile.json` - Company details, address, SIC codes
- `officers.json` - Directors, secretaries (current and resigned)
- `charges.json` - Mortgages and security interests
- `filing_history.json` - Complete filing records
- `psc.json` - Persons with significant control
- `insolvency.json` - Insolvency proceedings (if applicable)
- `exemptions.json` - Filing exemptions
- `uk_establishments.json` - UK branches and establishments

**Document Files:**
- `*.pdf` - PDF documents from filings
- `*.xbrl` - XBRL financial data (for accounts)
- `*.meta.json` - Metadata for each document (filing date, type, description)

**Tracking Files:**
- `summary.txt` - Human-readable overview of company and downloads
- `download_progress.json` - Resume tracking and failed downloads
- `logs/scraper_*.log` - Detailed execution log

## Configuration

Create a `.env` file in the project root:

```bash
# Required
COMPANIES_HOUSE_API_KEY=your_api_key_here

# Optional (defaults shown)
OUTPUT_DIR=./downloads
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=600
RATE_LIMIT_WINDOW=300
```

## Examples

### Example 1: Quick Preview

```bash
# See what would be downloaded without downloading
python scraper.py 00000006 --dry-run
```

Output:
```
[DRY RUN] Would download the following documents:
  1. 2023-12-31 - AA - Annual accounts made up to 31 December 2023
  2. 2023-06-15 - CS01 - Confirmation statement made up to 15 June 2023
  3. 2022-12-31 - AA - Annual accounts made up to 31 December 2022
  ... and 147 more

Total: 150 documents
```

### Example 2: Download Accounts Only

```bash
python scraper.py 00000006 --types accounts
```

Downloads only annual accounts (AA) filings and their associated documents.

### Example 3: Bulk Processing

```bash
# Create companies.txt
cat > companies.txt << EOF
00000006
00000007
SC123456
# Comments are ignored
EOF

# Process all companies
python scraper.py --file companies.txt --verbose
```

### Example 4: Resume After Interruption

If download is interrupted (Ctrl+C, network error, etc.):

```bash
python scraper.py 00000006 --resume
```

The scraper will:
1. Read `download_progress.json`
2. Verify which files actually exist
3. Skip already downloaded documents
4. Continue with remaining downloads

### Example 5: Monitor Specific Company

```bash
# Download to custom location with verbose logging
python scraper.py 00000006 \
  --output ~/Documents/companies/00000006 \
  --types accounts,confirmations \
  --verbose
```

## API Rate Limiting

The Companies House API allows **600 requests per 5 minutes**. The scraper automatically:
- Tracks requests across both data and document APIs
- Waits when approaching rate limit
- Resumes after cooldown period
- Logs rate limit delays

You'll see messages like:
```
[INFO] Rate limit reached, sleeping 45.3s
[INFO] Resuming downloads...
```

This is normal behavior - the scraper is being a good API citizen.

## File Organization

The project follows a clean directory structure:

```
companies-house-scraper/
├── scraper.py              # Main CLI
├── api_client.py           # API client with rate limiting
├── downloader.py           # Document download logic
├── validators.py           # Input validation and security
├── requirements.txt        # Dependencies
├── .env                    # Your API key (not in git)
├── .env.example            # Template
├── .gitignore             # Git exclusions
├── README.md              # This file
├── CLAUDE.md              # Claude Code guide
├── scripts/               # Utility scripts
│   ├── validate_download.py
│   └── cleanup_duplicates.py
├── examples/              # Example files
│   └── example_companies.txt
├── .private/              # Private documentation (git-ignored)
│   └── dev/
│       ├── ARCHITECTURE.md
│       ├── BUILD_LOG.md
│       └── VALIDATION_STRATEGY.md
└── downloads/             # Downloaded data (git-ignored)
```

## Troubleshooting

### API Key Issues

**Error: "API key is required"**

Make sure `.env` file exists with `COMPANIES_HOUSE_API_KEY=your_key`

```bash
cp .env.example .env
# Edit .env and add your key
```

**Error: "Authentication failed"**

Your API key may be invalid or expired. Get a new one from [Companies House Developer Hub](https://developer.company-information.service.gov.uk/).

### Company Not Found

**Error: "Company not found: 99999999"**

Verify company number format:
- Standard companies: 8 digits with leading zeros (e.g., `00000006`)
- Scottish companies: SC prefix + 6 digits (e.g., `SC123456`)
- Northern Ireland: NI prefix + 6 digits (e.g., `NI654321`)

### Download Issues

**Downloads are slow**

This is normal! The API has rate limits (600 req/5min). The scraper automatically waits to stay within limits.

**Some PDFs failed to download**

Check `download_progress.json` for failed downloads:
```bash
cat downloads/00000006/download_progress.json | jq '.failed'
```

Common causes:
- iXBRL/HTML accounts (newer format, not PDF) - Expected
- Document temporarily unavailable - Use `--resume` to retry
- Network timeout - Use `--resume` to retry

**Resume not working correctly**

Delete progress file and start fresh:
```bash
rm downloads/00000006/download_progress.json
python scraper.py 00000006
```

### Module Import Errors

**Error: "No module named 'click'"**

Install dependencies:
```bash
pip install -r requirements.txt
```

**Error: "Virtual environment not found"**

Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Progress Bar Not Showing

**Missing tqdm progress bars**

Install tqdm (optional):
```bash
pip install tqdm
```

Without tqdm, you'll see simple text progress:
```
Downloading [45/150]: CS01...
```

## Validation

After downloading, verify data accuracy:

```bash
# Run validation script
python scripts/validate_download.py 00000006
```

This checks:
- All required JSON files present
- PDF downloads vs filing history
- File integrity (PDF magic bytes)
- Metadata completeness

See `.private/dev/VALIDATION_STRATEGY.md` for detailed validation procedures.

## Security

- **API keys redacted from logs** - Your key never appears in log files
- **Path traversal prevention** - Input validation prevents directory traversal attacks
- **Filename sanitization** - Prevents injection attacks via malicious filenames
- **Content-type validation** - Ensures downloaded files are expected types
- **File size limits** - 50MB per file to prevent disk exhaustion
- **Input validation** - Company numbers validated before API calls

## Performance

### Expected Download Times

For a company with 150 filings:
- JSON data collection: ~30 seconds (8 API calls)
- PDF metadata: ~30 seconds (150 requests, rate limited)
- PDF downloads: ~5-10 minutes (depends on file sizes)
- **Total: ~10-15 minutes**

### Resource Usage

- **Memory**: Minimal (streaming downloads, 8KB chunks)
- **Disk**: Variable (depends on document count)
- **Network**: Rate-limited (600 req/5min, ~10 req/sec average)

### Optimizing for Speed

```bash
# Download only recent accounts
python scraper.py 00000006 --types accounts

# Process high-priority companies first
# (Reorder companies.txt file)

# Run multiple scrapers in parallel (advanced)
# Each needs its own rate limiter instance
```

## Development

### Project Structure

See `CLAUDE.md` for detailed development guide.

### Running Validation

```bash
# Validate a download
python scripts/validate_download.py 00000006

# Clean up duplicate files
python scripts/cleanup_duplicates.py 00000006
```

### Adding New Features

See `.private/dev/ARCHITECTURE.md` for design details and implementation patterns.

## Common Workflows

### Workflow 1: Monitor Single Company

```bash
# Initial download
python scraper.py 00000006 --verbose

# Check summary
cat downloads/00000006/summary.txt

# Weekly updates
python scraper.py 00000006 --resume
```

### Workflow 2: Bulk Data Collection

```bash
# Create company list
echo "00000006" > companies.txt
echo "00000007" >> companies.txt
echo "SC123456" >> companies.txt

# Preview
python scraper.py --file companies.txt --dry-run

# Download
python scraper.py --file companies.txt --verbose

# Validate
for company in $(cat companies.txt); do
  python scripts/validate_download.py "$company"
done
```

### Workflow 3: Research Project

```bash
# Download only financial data for analysis
python scraper.py --file research_companies.txt \
  --types accounts \
  --output ./research-data

# Extract XBRL for analysis
find research-data -name "*.xbrl" -exec cp {} ./analysis/ \;
```

## Sample Company Numbers

Try these to test the scraper:

```
00000006 - MARINE AND GENERAL MUTUAL LIFE ASSURANCE SOCIETY
00000007 - LONDON AND DUBLIN SOCIETY FOR THE PREVENTION OF CRUELTY TO ANIMALS
SC123456 - Scottish company example (SC prefix)
NI123456 - Northern Ireland company example (NI prefix)
10616124 - WASE LIMITED (validated test case)
```

## Dependencies

Core dependencies:
- `requests` - HTTP client for API calls
- `python-dotenv` - Environment variable management
- `click` - CLI framework
- `tqdm` - Progress bars (optional)

All dependencies pinned to specific versions in `requirements.txt`.

## API Documentation

- Main API: https://developer.company-information.service.gov.uk/
- API Specs: https://developer-specs.company-information.service.gov.uk/
- Developer Forum: https://forum.companieshouse.gov.uk/

## License

For personal/research use. Review Companies House API terms of service before commercial use.

## Support

### Check Logs

```bash
cat downloads/00000006/logs/scraper_*.log
```

### Run with Verbose Logging

```bash
python scraper.py 00000006 --verbose
```

### Common Issues

See Troubleshooting section above or check:
- `.private/dev/ARCHITECTURE.md` - Technical design details
- `.private/dev/VALIDATION_STRATEGY.md` - Data validation procedures

## Next Steps

After downloading:
1. Review `summary.txt` for overview
2. Check JSON files for structured data
3. Browse PDFs in category folders
4. Use XBRL files for financial analysis
5. Run validation script to verify accuracy
6. Build custom reports from the structured data

---

**Ready to start?** Try: `python scraper.py 00000006 --dry-run`
