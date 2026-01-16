# Companies House Scraper - Usage Examples

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your API key
```

## Basic Usage

### Single Company

```bash
# Download everything for company 00000006
python scraper.py 00000006
```

This will:
1. Fetch all JSON data (profile, officers, charges, filing history, PSC, etc.)
2. Extract document IDs from filing history
3. Download all PDFs and XBRL files
4. Organize files by category (accounts, confirmations, changes, etc.)
5. Generate summary.txt with company overview
6. Create download_progress.json for resume capability

**Output:**
```
downloads/00000006/
├── logs/scraper_20260116_143500.log
├── download_progress.json
├── summary.txt
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

### Multiple Companies (Command Line)

```bash
# Process multiple companies in one run
python scraper.py 00000006 00000007 SC123456 NI000001
```

### Multiple Companies (From File)

Create `companies.txt`:
```
00000006
00000007
SC123456
# This is a comment - ignored
NI000001
```

Run:
```bash
python scraper.py --file companies.txt
```

## Advanced Options

### Custom Output Directory

```bash
# Save to custom location
python scraper.py 00000006 --output ./my-data
```

### Dry Run (Preview)

```bash
# See what would be downloaded without downloading
python scraper.py 00000006 --dry-run
```

**Output:**
```
[DRY RUN] Would download the following documents:
  1. 2023-12-31 - AA - Annual accounts made up to 31 December 2023
  2. 2023-06-15 - CS01 - Confirmation statement made up to 15 June 2023
  3. 2022-12-31 - AA - Annual accounts made up to 31 December 2022
  ... and 147 more

Total: 150 documents
```

### Filter by Document Type

```bash
# Only download accounts and confirmations
python scraper.py 00000006 --types accounts,confirmations

# Only download incorporation documents
python scraper.py 00000006 --types incorporation

# Multiple types
python scraper.py 00000006 --types accounts,confirmations,changes
```

**Available types:**
- `accounts` - Annual accounts, financial statements
- `confirmations` - Confirmation statements (CS01)
- `incorporation` - Articles of association, certificates
- `changes` - Officer changes, address changes
- `mortgages` - Charges and mortgages (MR01, MR02, MR04)
- `dissolutions` - Dissolution notices
- `other` - Everything else

### Resume Interrupted Download

If download is interrupted (network issue, rate limit, etc.):

```bash
# Continue from where it left off
python scraper.py 00000006 --resume
```

The scraper will:
1. Read `download_progress.json`
2. Verify which files actually exist
3. Skip already downloaded documents
4. Continue with remaining downloads

### Verbose Logging

```bash
# Enable debug logging to console
python scraper.py 00000006 --verbose
```

Shows:
- API request details
- Rate limiter status
- Download progress for each file
- Error details

## Combined Examples

### Bulk Processing with Options

```bash
# Process multiple companies, only accounts, with verbose logging
python scraper.py --file companies.txt \
  --types accounts \
  --output ./accounts-only \
  --verbose
```

### Resume Bulk Processing

```bash
# Resume bulk processing that was interrupted
python scraper.py --file companies.txt --resume
```

### Dry Run Before Large Download

```bash
# Preview first
python scraper.py 12345678 --dry-run

# If looks good, run for real
python scraper.py 12345678
```

## Understanding the Output

### summary.txt

Human-readable overview of the company:

```
COMPANY OVERVIEW
============================================================
Name: EXAMPLE LIMITED
Number: 00000006
Status: active
Type: ltd
Incorporated: 2020-01-01
Jurisdiction: england-wales

REGISTERED ADDRESS
============================================================
123 Example Street
London
SW1A 1AA

DATA COLLECTED
============================================================
Officers: 3 found
Charges: 0 found
PSC: 2 found
Filing History: 147 records
UK Establishments: 0 found
Insolvency: No

DOCUMENTS DOWNLOADED
============================================================
Accounts: 5 PDFs, 5 XBRL
Confirmations: 3 PDFs
Incorporation: 2 PDFs
Changes: 8 PDFs
Other: 1 PDFs

Total Documents: 19 PDFs, 5 XBRL

Generated: 2026-01-16 14:30:00
```

### download_progress.json

Tracks download status for resume capability:

```json
{
  "company_number": "00000006",
  "started": "2026-01-16T14:00:00",
  "last_updated": "2026-01-16T14:15:00",
  "completed": ["abc123def", "xyz789abc"],
  "failed": [
    {
      "doc_id": "failed123",
      "error": "404 Not Found",
      "timestamp": "2026-01-16T14:10:00"
    }
  ],
  "total_documents": 147,
  "downloaded": 145
}
```

### *.meta.json Files

Each PDF has accompanying metadata:

```json
{
  "filing_date": "2023-12-31",
  "filing_type": "AA",
  "description": "Annual accounts made up to 31 December 2023",
  "category": "accounts",
  "company_number": "00000006",
  "download_timestamp": "2026-01-16T14:30:00",
  "document_id": "abc123def",
  "api_metadata": {
    "resources": {...},
    "description": "...",
    ...
  }
}
```

## Error Handling

### Company Not Found

```bash
$ python scraper.py 99999999
Error: Company not found: 99999999
```

### Invalid API Key

```bash
$ python scraper.py 00000006
Error: Authentication failed - check API key
```

### Rate Limit Hit

The scraper automatically waits when approaching rate limit:

```
[INFO] Rate limit reached, sleeping 45.3s
[INFO] Resuming downloads...
```

### Network Errors

Documents that fail to download are tracked in `download_progress.json`:

```json
{
  "failed": [
    {
      "doc_id": "xyz123",
      "error": "Network timeout",
      "timestamp": "2026-01-16T14:10:00"
    }
  ]
}
```

Use `--resume` to retry failed downloads.

## Performance Tips

### Expected Download Times

For a company with 150 filings:
- JSON data collection: ~30 seconds (8 API calls)
- PDF metadata: ~30 seconds (150 requests, rate limited)
- PDF downloads: ~5-10 minutes (depends on file sizes)
- **Total: ~10-15 minutes**

### Bulk Processing

When processing multiple companies:
- Rate limiter is shared across all companies
- Large companies will consume more of the 600 req/5min limit
- Consider running in batches if processing 50+ companies

### Optimizing for Speed

```bash
# Skip document downloads, only get JSON data
# (Not implemented yet - feature request)

# Download only recent filings
# (Use --types to filter by category)

# Process high-priority companies first
# (Reorder companies.txt file)
```

## Troubleshooting

### "No module named 'click'"

```bash
pip install -r requirements.txt
```

### "COMPANIES_HOUSE_API_KEY not set"

Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your key
```

### Progress bar not showing

Install tqdm (optional):
```bash
pip install tqdm
```

Without tqdm, you'll see simple text progress:
```
Downloading [45/150]: CS01...
```

### Files not resuming correctly

Delete `download_progress.json` and start fresh:
```bash
rm downloads/00000006/download_progress.json
python scraper.py 00000006
```

## Complete Workflow Example

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env
# Add API key to .env

# 2. Preview download
python scraper.py 00000006 --dry-run

# 3. Download with filters
python scraper.py 00000006 --types accounts,confirmations

# 4. Review output
cat downloads/00000006/summary.txt
ls downloads/00000006/accounts/

# 5. Get more companies
echo "00000006" > companies.txt
echo "00000007" >> companies.txt
python scraper.py --file companies.txt

# 6. Check logs if issues
tail -f downloads/logs/scraper_*.log
```

## Next Steps

After downloading, you can:
1. Analyze JSON data with Python scripts
2. Review PDFs in `downloads/{company_number}/`
3. Parse XBRL files for financial data
4. Use Claude Code to analyze the data
5. Build custom reports from the structured data

## API Rate Limits

Companies House API limits:
- **600 requests per 5 minutes**
- Shared between data API and document API
- Scraper automatically handles rate limiting
- No need to manually wait between requests

## Security Notes

- API keys are redacted from logs
- File paths are validated to prevent path traversal
- Filenames are sanitized to prevent injection
- Content-type is validated before saving files
- File size limits (50MB per file) are enforced

## Support

For issues or questions:
1. Check `logs/scraper_*.log` for error details
2. Review this usage guide
3. Consult the plan document: `companies-house-scraper-plan.md`
4. Check Companies House API documentation
