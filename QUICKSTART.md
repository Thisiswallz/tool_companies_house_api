# Companies House Scraper - Quick Start Guide

## Automated Setup (Recommended) ✨

### 1. Run Setup Script
```bash
./setup.sh
```

This automatically:
- ✓ Checks for Python 3
- ✓ Creates virtual environment
- ✓ Installs all dependencies
- ✓ Creates `.env` file
- ✓ Verifies installation

### 2. Add Your API Key
```bash
nano .env
# or
open .env
```

Replace `your_api_key_here` with your actual API key.

Get API key from: https://developer.company-information.service.gov.uk/

### 3. Test Installation
```bash
# Preview what would be downloaded
./run.sh 00000006 --dry-run
```

**Use `./run.sh` instead of `python scraper.py`** - it handles the virtual environment automatically!

---

## Manual Setup (Alternative)

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
cp .env.example .env
# Edit .env and add your API key
```

### 3. Test Installation
```bash
python3 scraper.py 00000006 --dry-run
```

## Basic Usage

**Note:** Use `./run.sh` (or `python3 scraper.py` if you're in the virtual environment manually)

### Download Everything for a Company
```bash
./run.sh 00000006
```

This downloads:
- Company profile, officers, charges, filing history
- All PDF documents
- XBRL files (where available)
- Organized into categories (accounts, confirmations, etc.)

### Multiple Companies
```bash
# Command line
./run.sh 00000006 00000007 SC123456

# From file
./run.sh --file example_companies.txt
```

### Filter by Type
```bash
# Only accounts and confirmations
./run.sh 00000006 --types accounts,confirmations

# Only incorporation documents
./run.sh 00000006 --types incorporation
```

### Resume Interrupted Download
```bash
./run.sh 00000006 --resume
```

### Enable Debug Logging
```bash
./run.sh 00000006 --verbose
```

## Output Location

```
downloads/00000006/
├── logs/scraper_YYYYMMDD_HHMMSS.log
├── summary.txt                      ← Start here
├── download_progress.json
├── company_profile.json
├── officers.json
├── accounts/
│   └── *.pdf, *.xbrl, *.meta.json
└── (other categories...)
```

## Common Options

| Command | Description |
|---------|-------------|
| `--dry-run` | Preview without downloading |
| `--resume` | Continue interrupted download |
| `--types` | Filter: accounts,confirmations,etc. |
| `--output` | Custom output directory |
| `--verbose` | Show debug information |
| `--file` | Read company numbers from file |

## Example Workflows

### 1. Quick Preview
```bash
./run.sh 00000006 --dry-run
```

### 2. Download Accounts Only
```bash
./run.sh 00000006 --types accounts
```

### 3. Bulk Processing
```bash
# Create companies.txt
echo "00000006" > companies.txt
echo "00000007" >> companies.txt

# Process all
./run.sh --file companies.txt --verbose
```

### 4. Resume After Interruption
```bash
./run.sh 00000006 --resume
```

## Troubleshooting

### "command not found: python"
→ Use `./run.sh` instead of `python`, or run `./setup.sh` first

### "API key is required"
→ Edit `.env` file and add `COMPANIES_HOUSE_API_KEY=your_key`

### "Company not found"
→ Check company number format (use 8 digits: `00000006`)

### "No module named 'click'" or similar import errors
→ Run `./setup.sh` or activate venv: `source venv/bin/activate`

### "Virtual environment not found"
→ Run `./setup.sh` to create it

### Slow downloads
→ Normal! API rate limit is 600 req/5min. Scraper waits automatically.

## Need Help?

1. Check logs: `cat downloads/logs/scraper_*.log`
2. Run with `--verbose` flag
3. See full documentation: `README.md` and `USAGE_EXAMPLES.md`

## Next Steps

After downloading:
- Review `summary.txt` for overview
- Check JSON files for structured data
- Browse PDFs in category folders
- Use XBRL files for financial analysis
