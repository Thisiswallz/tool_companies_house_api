#!/usr/bin/env python3
"""Validate downloaded company data against Companies House API."""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

import requests
from dotenv import load_dotenv
import os


class DownloadValidator:
    """Validate downloaded company data for accuracy and completeness."""

    def __init__(self, company_dir: Path):
        """Initialize validator.

        Args:
            company_dir: Path to company download directory
        """
        self.company_dir = Path(company_dir)
        self.issues = defaultdict(list)
        self.warnings = defaultdict(list)

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file from company directory."""
        filepath = self.company_dir / filename
        if not filepath.exists():
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)

    def validate_profile(self) -> bool:
        """Validate company profile data."""
        profile = self.load_json('profile.json')

        if not profile:
            self.issues['profile'].append("Missing profile.json")
            return False

        # Check required fields
        required = ['company_number', 'company_name', 'company_status', 'type']
        for field in required:
            if field not in profile:
                self.issues['profile'].append(f"Missing required field: {field}")

        # Check data quality
        if profile.get('company_status') not in ['active', 'dissolved', 'liquidation', 'administration']:
            self.warnings['profile'].append(
                f"Unusual company status: {profile.get('company_status')}"
            )

        return len(self.issues['profile']) == 0

    def validate_filing_history(self) -> Dict[str, Any]:
        """Validate filing history completeness.

        Returns:
            Dict with statistics
        """
        filing_history = self.load_json('filing_history.json')
        progress = self.load_json('download_progress.json')

        stats = {
            'total_filings': 0,
            'filings_with_docs': 0,
            'pdfs_downloaded': 0,
            'pdfs_missing': 0,
            'failed_downloads': 0,
            'missing_filings': []
        }

        if not filing_history:
            self.issues['filing_history'].append("Missing filing_history.json")
            return stats

        items = filing_history.get('items', [])
        stats['total_filings'] = len(items)

        # Count filings with document links
        for item in items:
            if 'document_metadata' in item.get('links', {}):
                stats['filings_with_docs'] += 1

        # Check downloaded PDFs
        if progress:
            stats['pdfs_downloaded'] = len(progress.get('completed', []))
            stats['failed_downloads'] = len(progress.get('failed', []))

        # Count actual PDF files
        pdf_count = sum(
            1 for f in self.company_dir.rglob('*.pdf')
            if f.is_file()
        )

        stats['pdfs_missing'] = stats['filings_with_docs'] - pdf_count

        # Report discrepancies
        if stats['pdfs_missing'] > 0:
            self.warnings['filing_history'].append(
                f"{stats['pdfs_missing']} PDFs missing "
                f"(expected {stats['filings_with_docs']}, found {pdf_count})"
            )

        if stats['failed_downloads'] > 0:
            self.warnings['filing_history'].append(
                f"{stats['failed_downloads']} downloads failed (may be iXBRL/HTML accounts)"
            )

        return stats

    def validate_officers(self) -> Dict[str, Any]:
        """Validate officers data.

        Returns:
            Dict with statistics
        """
        officers = self.load_json('officers.json')

        stats = {
            'total_officers': 0,
            'active_count': 0,
            'resigned_count': 0
        }

        if not officers:
            self.warnings['officers'].append("No officers data")
            return stats

        items = officers.get('items', [])
        stats['total_officers'] = len(items)

        # Count active vs resigned
        for officer in items:
            if officer.get('resigned_on'):
                stats['resigned_count'] += 1
            else:
                stats['active_count'] += 1

        # API provides counts too
        api_active = officers.get('active_count', 0)
        api_resigned = officers.get('resigned_count', 0)

        # Warn if mismatch (API counts might not match items due to pagination)
        if api_active != stats['active_count']:
            self.warnings['officers'].append(
                f"Active count mismatch: API reports {api_active}, "
                f"found {stats['active_count']} in items"
            )

        return stats

    def validate_psc(self) -> Dict[str, Any]:
        """Validate PSC (Persons with Significant Control) data.

        Returns:
            Dict with statistics
        """
        psc = self.load_json('psc.json')

        stats = {
            'total_psc': 0,
            'individuals': 0,
            'corporate': 0
        }

        if not psc:
            self.warnings['psc'].append("No PSC data (may be exempt or none registered)")
            return stats

        items = psc.get('items', [])
        stats['total_psc'] = len(items)

        for entity in items:
            kind = entity.get('kind', '')
            if 'individual' in kind:
                stats['individuals'] += 1
            elif 'corporate' in kind:
                stats['corporate'] += 1

        return stats

    def validate_charges(self) -> Dict[str, Any]:
        """Validate charges/mortgages data.

        Returns:
            Dict with statistics
        """
        charges = self.load_json('charges.json')

        stats = {
            'total_charges': 0,
            'satisfied': 0,
            'outstanding': 0
        }

        if not charges:
            # No charges is normal for many companies
            return stats

        items = charges.get('items', [])
        stats['total_charges'] = len(items)

        for charge in items:
            status = charge.get('status', '').lower()
            if 'satisfied' in status:
                stats['satisfied'] += 1
            elif 'outstanding' in status:
                stats['outstanding'] += 1

        return stats

    def validate_file_organization(self) -> Dict[str, Any]:
        """Validate file organization and metadata.

        Returns:
            Dict with statistics
        """
        stats = {
            'total_pdfs': 0,
            'pdfs_with_metadata': 0,
            'pdfs_without_metadata': 0,
            'corrupted_pdfs': 0,
            'category_counts': {}
        }

        categories = ['accounts', 'confirmations', 'incorporation', 'changes',
                      'mortgages', 'dissolutions', 'other']

        for category in categories:
            category_dir = self.company_dir / category
            if not category_dir.exists():
                continue

            pdf_files = list(category_dir.glob('*.pdf'))
            stats['category_counts'][category] = len(pdf_files)
            stats['total_pdfs'] += len(pdf_files)

            # Check for metadata and PDF validity
            for pdf_file in pdf_files:
                meta_file = pdf_file.with_suffix('.meta.json')

                if meta_file.exists():
                    stats['pdfs_with_metadata'] += 1
                else:
                    stats['pdfs_without_metadata'] += 1
                    self.warnings['organization'].append(
                        f"Missing metadata: {pdf_file.name}"
                    )

                # Validate PDF magic bytes
                try:
                    with open(pdf_file, 'rb') as f:
                        magic = f.read(4)
                        if not magic.startswith(b'%PDF'):
                            stats['corrupted_pdfs'] += 1
                            self.issues['organization'].append(
                                f"Corrupted PDF: {pdf_file.name}"
                            )
                except Exception as e:
                    self.issues['organization'].append(
                        f"Cannot read {pdf_file.name}: {e}"
                    )

        return stats

    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks.

        Returns:
            Complete validation report
        """
        report = {
            'company_dir': str(self.company_dir),
            'company_number': None,
            'company_name': None,
            'validations': {},
            'summary': {}
        }

        # Profile
        profile = self.load_json('profile.json')
        if profile:
            report['company_number'] = profile.get('company_number')
            report['company_name'] = profile.get('company_name')

        print(f"🔍 Validating: {report['company_name']} ({report['company_number']})")
        print("=" * 70)

        # Run validations
        report['validations']['profile'] = self.validate_profile()
        report['validations']['filing_history'] = self.validate_filing_history()
        report['validations']['officers'] = self.validate_officers()
        report['validations']['psc'] = self.validate_psc()
        report['validations']['charges'] = self.validate_charges()
        report['validations']['organization'] = self.validate_file_organization()

        # Summary (do this AFTER validations run)
        total_issues = sum(len(v) for v in self.issues.values())
        total_warnings = sum(len(v) for v in self.warnings.values())

        report['issues'] = dict(self.issues)
        report['warnings'] = dict(self.warnings)
        report['summary'] = {
            'total_issues': total_issues,
            'total_warnings': total_warnings,
            'status': 'PASS' if total_issues == 0 else 'FAIL'
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print validation report to console."""

        # Filing history
        fh = report['validations']['filing_history']
        print(f"\n📄 Filing History:")
        print(f"   Total filings: {fh['total_filings']}")
        print(f"   Filings with documents: {fh['filings_with_docs']}")
        print(f"   PDFs downloaded: {fh['pdfs_downloaded']}")
        if fh['failed_downloads'] > 0:
            print(f"   ⚠️  Failed downloads: {fh['failed_downloads']}")

        # Officers
        officers = report['validations']['officers']
        print(f"\n👥 Officers:")
        print(f"   Total: {officers['total_officers']}")
        print(f"   Active: {officers['active_count']}")
        print(f"   Resigned: {officers['resigned_count']}")

        # PSC
        psc = report['validations']['psc']
        print(f"\n🏢 Persons with Significant Control:")
        print(f"   Total: {psc['total_psc']}")
        if psc['total_psc'] > 0:
            print(f"   Individuals: {psc['individuals']}")
            print(f"   Corporate: {psc['corporate']}")

        # Charges
        charges = report['validations']['charges']
        if charges['total_charges'] > 0:
            print(f"\n💰 Charges:")
            print(f"   Total: {charges['total_charges']}")
            print(f"   Outstanding: {charges['outstanding']}")
            print(f"   Satisfied: {charges['satisfied']}")

        # File organization
        org = report['validations']['organization']
        print(f"\n📁 File Organization:")
        print(f"   Total PDFs: {org['total_pdfs']}")
        print(f"   PDFs with metadata: {org['pdfs_with_metadata']}")
        if org['corrupted_pdfs'] > 0:
            print(f"   ❌ Corrupted PDFs: {org['corrupted_pdfs']}")

        print(f"\n   By category:")
        for cat, count in sorted(org['category_counts'].items()):
            if count > 0:
                print(f"      {cat}: {count}")

        # Issues
        print(f"\n{'=' * 70}")
        if report['summary']['total_issues'] > 0:
            print(f"\n❌ ISSUES FOUND ({report['summary']['total_issues']}):")
            for category, issues in report['issues'].items():
                for issue in issues:
                    print(f"   [{category}] {issue}")

        # Warnings
        if report['summary']['total_warnings'] > 0:
            print(f"\n⚠️  WARNINGS ({report['summary']['total_warnings']}):")
            for category, warnings in report['warnings'].items():
                for warning in warnings:
                    print(f"   [{category}] {warning}")

        # Summary
        print(f"\n{'=' * 70}")
        status_emoji = "✅" if report['summary']['status'] == 'PASS' else "❌"
        print(f"{status_emoji} VALIDATION STATUS: {report['summary']['status']}")
        print()


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_download.py <company_number>")
        print("Example: python validate_download.py 10616124")
        sys.exit(1)

    company_number = sys.argv[1]
    company_dir = Path('downloads') / company_number

    if not company_dir.exists():
        print(f"Error: Directory not found: {company_dir}")
        sys.exit(1)

    validator = DownloadValidator(company_dir)
    report = validator.run_all_validations()
    validator.print_report(report)

    # Save report
    report_file = company_dir / 'validation_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"📊 Full report saved to: {report_file}")

    # Exit code
    sys.exit(0 if report['summary']['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
