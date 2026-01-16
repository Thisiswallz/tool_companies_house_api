"""Document download orchestration with validation and organization."""

import json
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import requests

from validators import sanitize_filename, safe_output_path


logger = logging.getLogger(__name__)


# Filing type categorization map
FILING_CATEGORIES = {
    'accounts': ['AA', 'AC', 'Annual Return', 'Annual Accounts', 'accounts'],
    'confirmations': ['CS01', 'Confirmation Statement', 'confirmation'],
    'incorporation': ['IN01', 'incorporation', 'articles', 'certificate'],
    'changes': ['CH01', 'CH02', 'CH03', 'TM01', 'TM02', 'AP01', 'change'],
    'mortgages': ['MR01', 'MR02', 'MR04', 'mortgage', 'charge'],
    'dissolutions': ['DS01', 'DS02', 'dissolution'],
    'other': []  # Catch-all
}


class DocumentDownloader:
    """Handle document downloads and file organization."""

    def __init__(self, api_client, output_dir: Path):
        """Initialize downloader.

        Args:
            api_client: CompaniesHouseAPI instance
            output_dir: Base output directory
        """
        self.api = api_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_document_ids(self, filing_history_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract document IDs from filing history with safe null checking.

        Args:
            filing_history_json: Filing history response from API

        Returns:
            List of dicts with document info
        """
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
                    'date': item.get('date', 'unknown'),
                    'description': item.get('description', 'unknown'),
                    'type': item.get('type', 'unknown'),
                    'category': item.get('category', 'unknown')
                })

        return doc_ids

    def categorize_filing(self, filing_type: str) -> str:
        """Return category folder for filing type.

        Args:
            filing_type: Filing type code or description

        Returns:
            Category name
        """
        filing_type_lower = filing_type.lower()

        for category, types in FILING_CATEGORIES.items():
            if category == 'other':
                continue
            for type_pattern in types:
                if type_pattern.lower() in filing_type_lower:
                    return category

        return 'other'

    def download_with_validation(self, url: str, output_path: Path,
                                   expected_type: str, max_size_mb: int = 50) -> bool:
        """Download file with content-type and size validation.

        Args:
            url: URL to download
            output_path: Where to save file
            expected_type: Expected content-type
            max_size_mb: Max file size in MB

        Returns:
            True if download succeeded

        Raises:
            ValueError: If content-type wrong or file too large
        """
        max_bytes = max_size_mb * 1024 * 1024

        try:
            response = self.api._doc_get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('Content-Type', '')
            if expected_type not in content_type:
                logger.warning(
                    f"Expected {expected_type}, got {content_type}. Likely error page."
                )
                return False

            # Check Content-Length header
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_bytes:
                logger.warning(
                    f"File too large: {int(content_length) / 1024 / 1024:.1f}MB"
                )
                return False

            # Stream to disk with size limit
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            logger.warning(f"Download exceeded {max_size_mb}MB limit")
                            return False
                        f.write(chunk)

            # Verify PDF magic bytes if PDF
            if expected_type == 'application/pdf':
                with open(output_path, 'rb') as f:
                    magic = f.read(4)
                    if not magic.startswith(b'%PDF'):
                        logger.warning(f"Invalid PDF file: {output_path}")
                        os.remove(output_path)
                        return False

            return True

        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_file_streaming(self, url: str, output_path: Path,
                                 max_size_mb: int = 50) -> int:
        """Stream large files to disk without loading into memory.

        Args:
            url: URL to download
            output_path: Where to save
            max_size_mb: Max size in MB

        Returns:
            File size in bytes

        Raises:
            ValueError: If file too large
        """
        max_bytes = max_size_mb * 1024 * 1024

        response = self.api._doc_get(url, stream=True, timeout=(10, 30))
        response.raise_for_status()

        # Check size before downloading
        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > max_bytes:
            raise ValueError(
                f"File too large: {content_length / 1024 / 1024:.1f}MB"
            )

        # Stream to disk in 8KB chunks
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        return os.path.getsize(output_path)

    def check_document_exists(self, doc_id: str, category_dir: Path) -> Optional[Path]:
        """Check if document already exists and is valid.

        Args:
            doc_id: Document ID
            category_dir: Category directory to search

        Returns:
            Path to existing file if found and valid, None otherwise
        """
        # Search for any PDF containing this doc_id
        for pdf_file in category_dir.glob("*.pdf"):
            # Check if metadata exists and contains this doc_id
            meta_file = pdf_file.with_suffix('.meta.json')
            if meta_file.exists():
                try:
                    import json
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                    if metadata.get('document_id') == doc_id:
                        # Validate PDF integrity
                        if pdf_file.stat().st_size > 0:
                            with open(pdf_file, 'rb') as f:
                                magic = f.read(4)
                                if magic.startswith(b'%PDF'):
                                    return pdf_file
                except Exception:
                    continue
        return None

    def download_document(self, doc_id: str, doc_info: Dict[str, Any],
                          category_dir: Path, company_number: str,
                          skip_existing: bool = True) -> Tuple[bool, Optional[str]]:
        """Download PDF and XBRL (if available).

        Args:
            doc_id: Document ID
            doc_info: Document metadata
            category_dir: Category output directory
            company_number: Company number
            skip_existing: If True, skip if valid file already exists

        Returns:
            Tuple of (success, error_message)
        """
        # Check if document already exists
        if skip_existing:
            existing_file = self.check_document_exists(doc_id, category_dir)
            if existing_file:
                logger.debug(f"Skipping existing file: {existing_file.name}")
                return True, "already_exists"

        try:
            # Get metadata first
            metadata_url = f"/document/{doc_id}"
            metadata_response = self.api._doc_get(metadata_url)

            if metadata_response.status_code == 404:
                return False, "Document not found (404)"

            metadata_response.raise_for_status()
            metadata = metadata_response.json()

            # Generate filename
            date = doc_info.get('date', 'unknown').replace('-', '')
            filing_type = doc_info.get('type', 'unknown')
            description = doc_info.get('description', 'unknown')[:50]

            # Sanitize and create base filename
            filename_base = f"{date}_{filing_type}_{description}"
            filename_base = sanitize_filename(filename_base)

            # Ensure unique filename
            pdf_path = self._get_unique_filename(category_dir, filename_base, '.pdf')

            # Download PDF (required)
            pdf_url = f"/document/{doc_id}/content"
            success = self.download_with_validation(
                pdf_url,
                pdf_path,
                'application/pdf'
            )

            if not success:
                return False, "PDF download failed"

            # Save metadata alongside PDF
            self.save_metadata(pdf_path, doc_info, company_number, metadata)

            # Download XBRL (optional) - check if available
            resources = metadata.get('resources', {})
            if 'application/xhtml+xml' in str(resources):
                xbrl_path = pdf_path.with_suffix('.xbrl')
                try:
                    xbrl_response = self.api._doc_get(
                        pdf_url,
                        headers={'Accept': 'application/xhtml+xml'},
                        stream=True
                    )
                    if xbrl_response.status_code == 200:
                        with open(xbrl_path, 'wb') as f:
                            for chunk in xbrl_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        logger.debug(f"Downloaded XBRL: {xbrl_path.name}")
                except Exception as e:
                    logger.debug(f"XBRL not available or failed: {e}")

            return True, None

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False, "Document not found (404)"
            return False, f"HTTP {e.response.status_code}"
        except Exception as e:
            return False, str(e)

    def _get_unique_filename(self, directory: Path, base_name: str,
                             extension: str) -> Path:
        """Generate unique filename with collision handling.

        Args:
            directory: Target directory
            base_name: Base filename without extension
            extension: File extension (e.g., '.pdf')

        Returns:
            Unique file path
        """
        target = directory / f"{base_name}{extension}"

        if not target.exists():
            return target

        # Add suffix: filename_2.pdf, filename_3.pdf, etc.
        counter = 2
        while True:
            target = directory / f"{base_name}_{counter}{extension}"
            if not target.exists():
                return target
            counter += 1

    def save_metadata(self, filepath: Path, filing_data: Dict[str, Any],
                      company_number: str, api_metadata: Dict[str, Any]):
        """Save filing metadata alongside PDF.

        Args:
            filepath: PDF file path
            filing_data: Filing info from filing history
            company_number: Company number
            api_metadata: Metadata from document API
        """
        meta_path = filepath.with_suffix('.meta.json')
        metadata = {
            'filing_date': filing_data.get('date'),
            'filing_type': filing_data.get('type'),
            'description': filing_data.get('description', ''),
            'category': filing_data.get('category', ''),
            'company_number': company_number,
            'download_timestamp': datetime.now().isoformat(),
            'document_id': filing_data.get('doc_id'),
            'api_metadata': api_metadata
        }

        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def update_progress(self, progress_file: Path, doc_id: str,
                        success: bool = True, error: Optional[str] = None):
        """Update progress with atomic writes.

        Args:
            progress_file: Progress JSON file path
            doc_id: Document ID
            success: Whether download succeeded
            error: Error message if failed
        """
        # Read current progress
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                progress = json.load(f)
        else:
            progress = {
                'company_number': None,
                'started': datetime.now().isoformat(),
                'completed': [],
                'failed': [],
                'total_documents': 0,
                'downloaded': 0
            }

        # Update
        progress['last_updated'] = datetime.now().isoformat()
        if success:
            if doc_id not in progress['completed']:
                progress['completed'].append(doc_id)
                progress['downloaded'] = len(progress['completed'])
        else:
            progress['failed'].append({
                'doc_id': doc_id,
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

        # Atomic write using temp file + rename
        progress_dir = progress_file.parent
        temp_fd, temp_path = tempfile.mkstemp(
            dir=progress_dir,
            suffix='.tmp',
            text=True
        )
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(progress, f, indent=2)
            os.replace(temp_path, progress_file)  # Atomic on POSIX
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def validate_progress_on_resume(self, progress_file: Path,
                                     output_dir: Path) -> Dict[str, Any]:
        """Verify completed files actually exist.

        Args:
            progress_file: Progress JSON file
            output_dir: Output directory

        Returns:
            Validated progress dict
        """
        with open(progress_file, 'r') as f:
            progress = json.load(f)

        validated = []
        for doc_id in progress.get('completed', []):
            # Check if any PDF with this doc_id exists
            found = False
            for category_dir in output_dir.iterdir():
                if category_dir.is_dir():
                    for pdf_file in category_dir.glob(f"*{doc_id}*.pdf"):
                        found = True
                        break
                if found:
                    break

            if found:
                validated.append(doc_id)

        progress['completed'] = validated
        progress['downloaded'] = len(validated)

        return progress

    def generate_summary(self, data: Dict[str, Any], output_dir: Path,
                         download_stats: Optional[Dict[str, Any]] = None):
        """Generate summary.txt with company overview.

        Args:
            data: All company data from API
            output_dir: Company output directory
            download_stats: Download statistics
        """
        summary_path = output_dir / "summary.txt"

        profile = data.get('profile', {})

        with open(summary_path, 'w') as f:
            # Company overview
            f.write("COMPANY OVERVIEW\n")
            f.write("=" * 60 + "\n")
            f.write(f"Name: {profile.get('company_name', 'N/A')}\n")
            f.write(f"Number: {profile.get('company_number', 'N/A')}\n")
            f.write(f"Status: {profile.get('company_status', 'N/A')}\n")
            f.write(f"Type: {profile.get('type', 'N/A')}\n")
            f.write(f"Incorporated: {profile.get('date_of_creation', 'N/A')}\n")
            f.write(f"Jurisdiction: {profile.get('jurisdiction', 'N/A')}\n\n")

            # Registered address
            f.write("REGISTERED ADDRESS\n")
            f.write("=" * 60 + "\n")
            address = profile.get('registered_office_address', {})
            if address:
                address_lines = [
                    address.get('address_line_1'),
                    address.get('address_line_2'),
                    address.get('locality'),
                    address.get('region'),
                    address.get('postal_code')
                ]
                for line in address_lines:
                    if line:
                        f.write(f"{line}\n")
            else:
                f.write("N/A\n")
            f.write("\n")

            # Data collected
            f.write("DATA COLLECTED\n")
            f.write("=" * 60 + "\n")

            officers = data.get('officers', {}).get('items', [])
            f.write(f"Officers: {len(officers)} found\n")

            charges = data.get('charges', {}).get('items', [])
            f.write(f"Charges: {len(charges)} found\n")

            psc = data.get('psc', {}).get('items', [])
            f.write(f"PSC: {len(psc)} found\n")

            filing_history = data.get('filing_history', {}).get('items', [])
            f.write(f"Filing History: {len(filing_history)} records\n")

            uk_est = data.get('uk_establishments', {}).get('items', [])
            f.write(f"UK Establishments: {len(uk_est)} found\n")

            insolvency = data.get('insolvency')
            f.write(f"Insolvency: {'Yes' if insolvency else 'No'}\n\n")

            # Documents downloaded (if stats provided)
            if download_stats:
                f.write("DOCUMENTS DOWNLOADED\n")
                f.write("=" * 60 + "\n")

                category_stats = download_stats.get('by_category', {})
                for category, count in sorted(category_stats.items()):
                    f.write(f"{category.title()}: {count} PDFs\n")

                f.write(f"\nTotal Documents: {download_stats.get('total_pdfs', 0)} PDFs")
                xbrl_count = download_stats.get('total_xbrl', 0)
                if xbrl_count > 0:
                    f.write(f", {xbrl_count} XBRL")
                f.write("\n\n")

            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        logger.info(f"Summary written to {summary_path}")

    def save_json_data(self, data: Dict[str, Any], output_dir: Path):
        """Save all JSON data files.

        Args:
            data: All company data
            output_dir: Company output directory
        """
        # Save individual endpoint data
        endpoints = [
            'profile', 'filing_history', 'officers', 'charges',
            'psc', 'uk_establishments', 'insolvency', 'exemptions'
        ]

        for endpoint in endpoints:
            endpoint_data = data.get(endpoint)
            if endpoint_data:
                filename = f"{endpoint}.json"
                filepath = output_dir / filename
                with open(filepath, 'w') as f:
                    json.dump(endpoint_data, f, indent=2)
                logger.debug(f"Saved {filename}")
