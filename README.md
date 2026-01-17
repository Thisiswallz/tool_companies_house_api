# Companies House Data Scraper

Download company data and documents from the UK Companies House API with built-in rate limiting and resume capability.

## What It Does

Downloads complete company records including:
- Company profiles, officers, PSC, charges, filing history
- Automatic PDF and XBRL document downloads
- Organized by category (accounts, confirmations, incorporation, etc.)
- All 8 Companies House API endpoints

## Features

- Built-in rate limiting (600 req/5min)
- Resume interrupted downloads
- Bulk processing from file
- Dry-run preview mode
- Filter by document type

## Setup

### 1. Get API Key
Register at [Companies House Developer Hub](https://developer.company-information.service.gov.uk/) and create a free API key.

### 2. Install
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env and add: COMPANIES_HOUSE_API_KEY=your_key_here
```

### 4. Run
```bash
# Preview
python scraper.py 00000006 --dry-run

# Download
python scraper.py 00000006
```

## Usage

```bash
# Single company
python scraper.py 00000006

# Multiple companies from file
python scraper.py --file companies.txt

# Preview before downloading
python scraper.py 00000006 --dry-run

# Download specific types only
python scraper.py 00000006 --types accounts,confirmations

# Resume interrupted download
python scraper.py 00000006 --resume

# Custom output directory
python scraper.py 00000006 --output ./my-data

# Verbose logging
python scraper.py 00000006 --verbose
```

**Document type filters**: accounts, confirmations, incorporation, changes, mortgages, dissolutions, other

## Output Structure

```
downloads/{company_number}/
├── company_profile.json
├── officers.json
├── charges.json
├── filing_history.json
├── psc.json
├── insolvency.json
├── exemptions.json
├── uk_establishments.json
├── summary.txt
├── download_progress.json
├── logs/
└── accounts/           # PDFs, XBRL, metadata
└── confirmations/
└── incorporation/
└── changes/
└── mortgages/
└── dissolutions/
└── other/
```

## Configuration

`.env` file:
```bash
COMPANIES_HOUSE_API_KEY=your_key_here

# Optional
OUTPUT_DIR=./downloads
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=600
RATE_LIMIT_WINDOW=300
```

## API Rate Limiting

The API allows **600 requests per 5 minutes**. The scraper automatically handles this - you'll see log messages when it needs to wait.

## Test Companies

```
00000006 - MARINE AND GENERAL MUTUAL LIFE ASSURANCE SOCIETY
10616124 - WASE LIMITED
SC123456 - Scottish company (SC prefix)
```

## Company Number Format

- Standard: 8 digits with leading zeros (e.g., `00000006`)
- Scottish: SC prefix + 6 digits (e.g., `SC123456`)
- Northern Ireland: NI prefix + 6 digits (e.g., `NI654321`)

## Resources

- [API Documentation](https://developer.company-information.service.gov.uk/)
- [API Specifications](https://developer-specs.company-information.service.gov.uk/)
- [Developer Forum](https://forum.companieshouse.gov.uk/)
