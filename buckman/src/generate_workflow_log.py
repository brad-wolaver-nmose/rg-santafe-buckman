#!/usr/bin/env python3
"""
Standalone CLI for generating Buckman workflow logs.

Generates comprehensive MD and DOCX logs for regulatory compliance,
documenting inputs, processing, outputs, and verification results.

Usage:
    python3 src/generate_workflow_log.py --year 2024
    python3 src/generate_workflow_log.py --year 2024 --status FLAGS
    python3 src/generate_workflow_log.py --year 2024 --status FAIL

Author: Claude Code (Anthropic)
Date: 2026-02-18
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.workflow_logger import WorkflowLogger


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Buckman workflow log for regulatory compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 src/generate_workflow_log.py --year 2024
    python3 src/generate_workflow_log.py --year 2024 --status FLAGS
    python3 src/generate_workflow_log.py --year 2024 --status FAIL

Output:
    Generates both MD and DOCX files in output/logs/

Status Codes:
    PASS  - All tests passed, no flags
    FLAGS - Tests passed but soft flags require review
    FAIL  - One or more hard failures
        """,
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Calendar year to document (e.g., 2024)",
    )
    parser.add_argument(
        "--status",
        choices=["PASS", "FLAGS", "FAIL"],
        default="PASS",
        help="Overall verification status (default: PASS)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory (default: auto-detected)",
    )

    args = parser.parse_args()

    print(f"Generating workflow log for year {args.year}...")
    print(f"Status: {args.status}")
    print()

    try:
        logger = WorkflowLogger(
            year=args.year,
            project_root=args.project_root,
        )

        md_path, docx_path = logger.generate_and_save(status=args.status)

        print("=" * 60)
        print("WORKFLOW LOG GENERATED")
        print("=" * 60)
        print(f"  Markdown: {md_path}")
        print(f"  DOCX:     {docx_path}")
        print()
        print("These files document:")
        print("  - Input file inventory with SHA-256 hashes")
        print("  - Step-by-step execution log")
        print("  - Output file inventory")
        print("  - Verification test results")
        print("  - Physical interpretation for regulatory context")
        print()
        print("Ready for review and signature.")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"ERROR: Failed to generate workflow log: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
