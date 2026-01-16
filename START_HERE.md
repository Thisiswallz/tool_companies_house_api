# 🚀 START HERE - Companies House Scraper

## You're All Set! ✅

The setup script has already:
- ✓ Created a virtual environment (`venv/`)
- ✓ Installed all dependencies
- ✓ Created your `.env` configuration file
- ✓ Verified all Python modules

## Your API Key is Configured

Your `.env` file contains:
```
COMPANIES_HOUSE_API_KEY=223cc054-5417-4566-b23f-f04574bfefb5
```

## Ready to Run!

### Test with a Dry Run (Preview Only)

```bash
./run.sh 00000006 --dry-run
```

This will show you what would be downloaded without actually downloading anything.

### Download Real Data

```bash
./run.sh 00000006
```

This downloads everything for company number `00000006`:
- Company profile, officers, charges, filing history (JSON)
- All PDF documents
- XBRL financial data (where available)
- Organized into category folders

### Download Specific Types Only

```bash
# Just accounts
./run.sh 00000006 --types accounts

# Accounts and confirmations
./run.sh 00000006 --types accounts,confirmations

# Incorporation documents only
./run.sh 00000006 --types incorporation
```

### Multiple Companies

```bash
# Command line
./run.sh 00000006 00000007 SC123456

# From a file
./run.sh --file example_companies.txt
```

### Resume Interrupted Downloads

If a download is interrupted (Ctrl+C, network error, etc.):

```bash
./run.sh 00000006 --resume
```

### Enable Verbose Logging

For detailed debugging information:

```bash
./run.sh 00000006 --verbose
```

## Where Does Data Go?

Everything downloads to `downloads/00000006/`:

```
downloads/00000006/
├── summary.txt                      ← Start here! Human-readable overview
├── logs/scraper_20260116_225900.log ← Detailed log file
├── download_progress.json           ← Resume tracking
├── company_profile.json             ← Company details
├── officers.json                    ← Directors, secretaries
├── charges.json                     ← Mortgages, charges
├── filing_history.json              ← All filings
├── psc.json                         ← Significant control persons
├── insolvency.json                  ← Insolvency records
├── exemptions.json                  ← Company exemptions
├── uk_establishments.json           ← UK branches (if applicable)
└── accounts/                        ← PDF + XBRL files organized by type
    ├── 20231231_AA_annual_accounts.pdf
    ├── 20231231_AA_annual_accounts.xbrl
    └── 20231231_AA_annual_accounts.meta.json
```

## All Available Options

```bash
./run.sh --help
```

Shows:
- `--file FILE` - Read company numbers from file
- `--output DIR` - Custom output directory
- `--dry-run` - Preview without downloading
- `--resume` - Continue interrupted downloads
- `--types TYPES` - Filter: accounts,confirmations,incorporation,changes,mortgages,dissolutions,other
- `--verbose` - Debug logging

## Common Commands

```bash
# Preview before downloading
./run.sh 00000006 --dry-run

# Download everything
./run.sh 00000006

# Download accounts only with verbose logging
./run.sh 00000006 --types accounts --verbose

# Process multiple companies from file
./run.sh --file companies.txt

# Resume interrupted download
./run.sh 00000006 --resume

# Custom output location
./run.sh 00000006 --output ~/Documents/company-data
```

## Rate Limiting

The scraper respects Companies House API limits:
- **600 requests per 5 minutes**
- Automatic rate limiting built-in
- No need to manually throttle

If you see slower downloads, it's normal - the scraper is waiting to stay within limits.

## File Categories

Documents are organized into 7 categories:

1. **accounts/** - Annual accounts, financial statements
2. **confirmations/** - Confirmation statements (annual returns)
3. **incorporation/** - Articles of association, incorporation certificates
4. **changes/** - Director changes, address changes
5. **mortgages/** - Charges, mortgages, security interests
6. **dissolutions/** - Dissolution notices
7. **other/** - Everything else

## Sample Company Numbers to Try

```
00000006 - MARINE AND GENERAL MUTUAL LIFE ASSURANCE SOCIETY
00000007 - LONDON AND DUBLIN SOCIETY FOR THE PREVENTION OF CRUELTY TO ANIMALS
SC123456 - Scottish company example (SC prefix)
NI123456 - Northern Ireland company example (NI prefix)
```

## Troubleshooting

### Error: "Virtual environment not found"
```bash
./setup.sh
```

### Error: "API key is required"
Edit `.env` and ensure your key is correct.

### Error: "Company not found"
Check the company number format (8 digits for standard companies, 2-letter prefix + 6 digits for SC/NI/etc.)

### Downloads are slow
This is normal! The API has rate limits. The scraper automatically waits.

### Need to stop a download?
Press `Ctrl+C` then resume later with `--resume`

## Next Steps

1. **Test it:** `./run.sh 00000006 --dry-run`
2. **Download:** `./run.sh 00000006`
3. **Check output:** `cat downloads/00000006/summary.txt`
4. **Explore data:** Browse the `downloads/00000006/` folder

## More Information

- **QUICKSTART.md** - Quick reference guide
- **USAGE_EXAMPLES.md** - Detailed usage examples
- **README.md** - Full documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## Get Help

Check logs for errors:
```bash
cat downloads/00000006/logs/scraper_*.log
```

Or run with verbose logging:
```bash
./run.sh 00000006 --verbose
```

---

**Ready to go!** Try: `./run.sh 00000006 --dry-run`
