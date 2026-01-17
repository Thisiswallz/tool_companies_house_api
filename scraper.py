"""Companies House Scraper - CLI and main orchestration."""

import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import click

from api_client import CompaniesHouseAPI
from config import API_KEY, CATEGORY_NAMES
from downloader import DocumentDownloader
from logging_filter import SensitiveDataFilter
from utils import load_json_file
from validators import validate_company_number


# Try to import tqdm, fallback to simple progress
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


def setup_logging(output_dir: Path, verbose: bool = False) -> logging.Logger:
    """Configure logging to file and console.

    Args:
        output_dir: Directory for log files
        verbose: Enable debug logging to console

    Returns:
        Configured logger
    """
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

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

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    return logger


def read_companies_from_file(filepath: Path) -> List[str]:
    """Read company numbers from file.

    Args:
        filepath: Path to file with company numbers (one per line)

    Returns:
        List of company numbers
    """
    companies = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            companies.append(line)

    return companies


def scrape_company(
    company_number: str,
    api_client: CompaniesHouseAPI,
    downloader: DocumentDownloader,
    output_base: Path,
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """Scrape all data for a single company.

    Args:
        company_number: Company number
        api_client: API client instance
        downloader: Downloader instance
        output_base: Base output directory
        options: CLI options (dry_run, resume, types, etc.)

    Returns:
        Dict with status and stats
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        # Validate company number
        company_number = validate_company_number(company_number)
        logger.info(f"Processing company: {company_number}")

        # Setup company output directory
        company_dir = output_base / company_number
        company_dir.mkdir(parents=True, exist_ok=True)

        # Create category directories
        for category in CATEGORY_NAMES:
            (company_dir / category).mkdir(exist_ok=True)

        # Check if JSON data already exists (unless --force)
        profile_json = company_dir / "profile.json"
        if profile_json.exists() and not options.get('force'):
            logger.info("Using cached company data (use --force to refresh)")
            # Load cached data
            data = {}
            endpoints = [
                'profile', 'filing_history', 'officers', 'charges',
                'psc', 'uk_establishments', 'insolvency', 'exemptions'
            ]
            for endpoint in endpoints:
                json_file = company_dir / f"{endpoint}.json"
                endpoint_data = load_json_file(json_file)
                if endpoint_data:
                    data[endpoint] = endpoint_data
        else:
            # Fetch all JSON data
            logger.info("Fetching company data...")
            data = api_client.get_all_data(company_number)

            if not data.get('profile'):
                logger.error(f"Company not found: {company_number}")
                return {'status': 'error', 'error': 'Company not found'}

            # Save JSON data
            downloader.save_json_data(data, company_dir)

        # Extract document IDs
        filing_history = data.get('filing_history', {})
        documents = downloader.extract_document_ids(filing_history)

        logger.info(f"Found {len(documents)} documents")

        # Filter by types if specified
        if options.get('types'):
            allowed_types = [t.strip() for t in options['types'].split(',')]
            documents = [
                d for d in documents
                if downloader.categorize_filing(d['type']) in allowed_types
            ]
            logger.info(f"Filtered to {len(documents)} documents by type")

        # Dry-run mode
        if options.get('dry_run'):
            logger.info("[DRY RUN] Would download the following documents:")
            for i, doc in enumerate(documents[:10], 1):
                logger.info(
                    f"  {i}. {doc['date']} - {doc['type']} - {doc['description'][:50]}"
                )
            if len(documents) > 10:
                logger.info(f"  ... and {len(documents) - 10} more")
            logger.info(f"Total: {len(documents)} documents")
            return {'status': 'dry_run', 'total_documents': len(documents)}

        # Progress tracking
        progress_file = company_dir / "download_progress.json"

        # Resume capability
        completed_docs = set()
        if options.get('resume') and progress_file.exists():
            logger.info("Resuming previous download...")
            progress = downloader.validate_progress_on_resume(
                progress_file,
                company_dir
            )
            completed_docs = set(progress.get('completed', []))
            logger.info(f"Already downloaded: {len(completed_docs)} documents")

        # Download documents
        stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'by_category': {},
            'failed_items': []
        }

        documents_to_download = [
            d for d in documents if d['doc_id'] not in completed_docs
        ]

        if not documents_to_download:
            logger.info("All documents already downloaded")
        else:
            # Check how many already exist (if not forcing re-download)
            if not options.get('force'):
                existing_count = sum(
                    1 for doc in documents_to_download
                    if downloader.check_document_exists(
                        doc['doc_id'],
                        company_dir / downloader.categorize_filing(doc['type'])
                    )
                )
                if existing_count > 0:
                    logger.info(
                        f"Found {existing_count} existing files (will skip). "
                        f"Use --force to re-download."
                    )
                    actual_to_download = len(documents_to_download) - existing_count
                    if actual_to_download > 0:
                        logger.info(f"Downloading {actual_to_download} new documents...")
                    else:
                        logger.info("All documents already exist")
                else:
                    logger.info(f"Downloading {len(documents_to_download)} documents...")
            else:
                logger.info(f"Downloading {len(documents_to_download)} documents (--force enabled)...")

            # Progress display
            if HAS_TQDM:
                progress_iter = tqdm(
                    documents_to_download,
                    desc="Downloading",
                    unit="doc"
                )
            else:
                progress_iter = documents_to_download
                total = len(documents_to_download)

            for idx, doc in enumerate(progress_iter, 1):
                # Simple progress for non-tqdm
                if not HAS_TQDM:
                    print(
                        f"Downloading [{idx}/{total}]: {doc['type']}...",
                        end='\r'
                    )

                # Categorize
                category = downloader.categorize_filing(doc['type'])
                category_dir = company_dir / category

                # Download (skip existing unless --force specified)
                skip_existing = not options.get('force', False)
                success, error = downloader.download_document(
                    doc['doc_id'],
                    doc,
                    category_dir,
                    company_number,
                    skip_existing=skip_existing
                )

                # Update stats
                if success:
                    if error == "already_exists":
                        stats['skipped'] += 1
                    else:
                        stats['success'] += 1
                        stats['by_category'][category] = \
                            stats['by_category'].get(category, 0) + 1
                    downloader.update_progress(progress_file, doc['doc_id'], True)
                else:
                    stats['failed'] += 1
                    stats['failed_items'].append(f"{doc['doc_id']}: {error}")
                    downloader.update_progress(
                        progress_file,
                        doc['doc_id'],
                        False,
                        error
                    )

            if not HAS_TQDM:
                print()  # Clear progress line

        # Generate summary
        stats['total_pdfs'] = stats['success']
        stats['total_xbrl'] = 0  # Count XBRL files if needed

        downloader.generate_summary(data, company_dir, stats)

        elapsed = time.time() - start_time
        logger.info(
            f"Completed in {elapsed:.1f}s - "
            f"Downloaded: {stats['success']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}"
        )

        return {
            'status': 'success',
            'stats': stats,
            'elapsed': elapsed
        }

    except Exception as e:
        logger.error(f"Error processing {company_number}: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


@click.command()
@click.argument('company_numbers', nargs=-1, required=False)
@click.option(
    '--file', '-f',
    type=click.Path(exists=True, path_type=Path),
    help='File containing company numbers (one per line)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default='./downloads',
    help='Output directory (default: ./downloads)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview what would be downloaded without downloading'
)
@click.option(
    '--resume',
    is_flag=True,
    help='Resume interrupted download (legacy - now automatic)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force re-download even if files already exist'
)
@click.option(
    '--types',
    help='Filter document types (comma-separated: accounts,confirmations,etc.)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable debug logging'
)
def main(
    company_numbers: tuple,
    file: Optional[Path],
    output: Path,
    dry_run: bool,
    resume: bool,
    force: bool,
    types: Optional[str],
    verbose: bool
):
    """Companies House Data Scraper.

    Download company data and documents from Companies House API.

    By default, existing files are automatically skipped (smart resume).
    Use --force to re-download everything.

    Examples:

        \b
        # Single company (skips existing files)
        python scraper.py 00000006

        \b
        # Force re-download everything
        python scraper.py 00000006 --force

        \b
        # Multiple companies
        python scraper.py 00000006 00000007 SC123456

        \b
        # From file
        python scraper.py --file companies.txt

        \b
        # With options
        python scraper.py 00000006 --types accounts,confirmations --verbose

        \b
        # Dry run (preview without downloading)
        python scraper.py 00000006 --dry-run
    """
    # Setup output directory
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    # Setup logging
    logger = setup_logging(output, verbose)
    logger.info("Companies House Scraper started")

    # Get company numbers
    companies = []
    if file:
        logger.info(f"Reading companies from {file}")
        companies.extend(read_companies_from_file(file))
    if company_numbers:
        companies.extend(company_numbers)

    if not companies:
        click.echo("Error: No company numbers provided", err=True)
        click.echo("Use: python scraper.py <company_number> or --file <file>")
        sys.exit(1)

    logger.info(f"Processing {len(companies)} companies")

    # Get API key from config (already loaded from environment)
    if not API_KEY:
        click.echo(
            "Error: COMPANIES_HOUSE_API_KEY not set",
            err=True
        )
        click.echo("Set in .env file or environment variable")
        sys.exit(1)

    # Initialize API client
    try:
        api_client = CompaniesHouseAPI(API_KEY)
        downloader = DocumentDownloader(api_client, output)
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        sys.exit(1)

    # Prepare options
    options = {
        'dry_run': dry_run,
        'resume': resume,
        'force': force,
        'types': types,
        'verbose': verbose
    }

    # Process companies
    results = []
    for company_number in companies:
        result = scrape_company(
            company_number,
            api_client,
            downloader,
            output,
            options
        )
        results.append({
            'company_number': company_number,
            **result
        })

    # Summary for multiple companies
    if len(companies) > 1:
        logger.info("\n" + "=" * 60)
        logger.info("BULK PROCESSING SUMMARY")
        logger.info("=" * 60)

        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = sum(1 for r in results if r['status'] == 'error')

        logger.info(f"Total: {len(companies)}")
        logger.info(f"Success: {success_count}")
        logger.info(f"Errors: {error_count}")

        if error_count > 0:
            logger.info("\nFailed companies:")
            for result in results:
                if result['status'] == 'error':
                    logger.info(
                        f"  {result['company_number']}: {result.get('error', 'Unknown error')}"
                    )

    logger.info("Scraper completed")


if __name__ == '__main__':
    main()
