# Companies House Scraper

A Python tool to download company data and documents from the UK Companies House API.

## Features

- **Complete data collection**: Company profile, officers, charges, filing history, PSC, insolvency records
- **Document downloads**: Automatic PDF and XBRL download with categorization
- **Rate limiting**: Built-in 600 req/5min rate limiter respects API limits
- **Resume capability**: Continue interrupted downloads
- **Security focused**: Input validation, path traversal prevention, API key redaction in logs
- **Bulk processing**: Process multiple companies from file or command line
- **Progress tracking**: Visual progress with tqdm (optional)

## Quick Start

### 1. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Get API Key

1. Register at [Companies House Developer Hub](https://developer.company-information.service.gov.uk/)
2. Create an API key
3. Copy `.env.example` to `.env`
4. Add your API key to `.env`:

```bash
cp .env.example .env
# Edit .env and set COMPANIES_HOUSE_API_KEY=your_key_here
```

### 3. Run Scraper

```bash
# Single company
python scraper.py 00000006

# Multiple companies
python scraper.py 00000006 00000007 SC123456

# From file
python scraper.py --file companies.txt

# Preview before downloading
python scraper.py 00000006 --dry-run
```

## CLI Usage

```bash
python scraper.py [OPTIONS] [COMPANY_NUMBERS]...

Options:
  -f, --file PATH           File with company numbers (one per line)
  -o, --output PATH         Output directory (default: ./downloads)
  --dry-run                 Preview downloads without executing
  --resume                  Continue interrupted download
  --types TEXT              Filter by type: accounts,confirmations,etc.
  -v, --verbose            Enable debug logging
  --help                   Show help message
```

## Examples

```bash
# Download everything for company 00000006
python scraper.py 00000006

# Only download accounts and confirmations
python scraper.py 00000006 --types accounts,confirmations

# Process multiple companies from file
python scraper.py --file companies.txt --output ./data

# Resume interrupted download
python scraper.py 00000006 --resume

# Preview what would be downloaded
python scraper.py 00000006 --dry-run --verbose
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

## File Descriptions

- **scraper.py**: CLI and main orchestration
- **api_client.py**: API client with rate limiting and pagination
- **downloader.py**: Document download and file organization
- **validators.py**: Input validation and sanitization

## Rate Limits

The API allows **600 requests per 5 minutes**. The scraper automatically:
- Tracks requests across data and document APIs
- Waits when approaching rate limit
- Resumes after cooldown period

## Security

- API keys redacted from logs
- Path traversal prevention
- Filename sanitization
- Content-type validation
- File size limits (50MB per file)

## Troubleshooting

### "API key is required"
Make sure `.env` file exists with `COMPANIES_HOUSE_API_KEY=your_key`

### "Company not found"
Verify company number format. Use 8 digits with leading zeros: `00000006`

### Rate limit errors
The scraper handles this automatically. Wait will be logged.

### Resume after interruption
Use `--resume` flag to continue from last successful download

## License

For personal/research use. Review Companies House API terms of service.
