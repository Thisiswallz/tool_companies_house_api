#!/usr/bin/env python3
"""Clean up duplicate PDF files created by multiple scraper runs."""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict


def find_duplicates(company_dir: Path):
    """Find all duplicate PDF files.

    Returns:
        Dict mapping base filename to list of all versions
    """
    duplicates = defaultdict(list)

    # Find all PDFs
    for pdf_file in company_dir.rglob('*.pdf'):
        # Extract base name (without _N suffix)
        name = pdf_file.stem
        base_name = re.sub(r'_\d+$', '', name)

        duplicates[base_name].append(pdf_file)

    # Filter to only files with duplicates
    return {k: v for k, v in duplicates.items() if len(v) > 1}


def get_file_age(filepath: Path) -> float:
    """Get file modification time."""
    return filepath.stat().st_mtime


def cleanup_duplicates(company_dir: Path, dry_run: bool = True):
    """Remove duplicate PDFs, keeping the newest version.

    Args:
        company_dir: Company download directory
        dry_run: If True, only show what would be deleted
    """
    duplicates = find_duplicates(company_dir)

    if not duplicates:
        print("✅ No duplicates found!")
        return

    print(f"Found {len(duplicates)} files with duplicates\n")

    total_files = sum(len(versions) for versions in duplicates.values())
    total_to_delete = total_files - len(duplicates)

    files_to_delete = []

    for base_name, versions in sorted(duplicates.items()):
        # Sort by modification time (newest first)
        versions_sorted = sorted(versions, key=get_file_age, reverse=True)

        keep = versions_sorted[0]
        delete = versions_sorted[1:]

        print(f"📄 {base_name}")
        print(f"   ✓ Keep:   {keep.name}")
        for dup in delete:
            print(f"   ✗ Delete: {dup.name}")
            files_to_delete.append(dup)

            # Also delete associated metadata and XBRL
            meta_file = dup.with_suffix('.meta.json')
            xbrl_file = dup.with_suffix('.xbrl')

            if meta_file.exists():
                files_to_delete.append(meta_file)
            if xbrl_file.exists():
                files_to_delete.append(xbrl_file)
        print()

    print("=" * 70)
    print(f"Summary: {total_to_delete} duplicate PDFs found")
    print(f"Total files to delete: {len(files_to_delete)} (PDFs + metadata + XBRL)")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No files deleted")
        print("Run with --delete to actually remove files")
    else:
        response = input("\n⚠️  Delete these files? (yes/no): ")
        if response.lower() == 'yes':
            for filepath in files_to_delete:
                try:
                    filepath.unlink()
                    print(f"Deleted: {filepath}")
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")
            print(f"\n✅ Deleted {len(files_to_delete)} files")
        else:
            print("Cancelled - no files deleted")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 cleanup_duplicates.py <company_number> [--delete]")
        print("\nExamples:")
        print("  python3 cleanup_duplicates.py 10616124          # Dry run")
        print("  python3 cleanup_duplicates.py 10616124 --delete # Actually delete")
        sys.exit(1)

    company_number = sys.argv[1]
    dry_run = '--delete' not in sys.argv

    company_dir = Path('downloads') / company_number

    if not company_dir.exists():
        print(f"Error: Directory not found: {company_dir}")
        sys.exit(1)

    print(f"🔍 Scanning: {company_dir}")
    print("=" * 70)

    cleanup_duplicates(company_dir, dry_run)


if __name__ == '__main__':
    main()
