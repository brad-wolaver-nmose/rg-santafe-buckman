#!/usr/bin/env python3
"""
Comprehensive workflow verification for Buckman wellfield depletion analysis.

Verifies that all outputs exist and are valid for a given year's workflow.
Runs pytest tests and custom verification scripts to ensure data quality.

Usage:
    python3 verify_workflow.py --year 2025
    python3 verify_workflow.py --year 2025 --step 1  # Verify specific step only
    python3 verify_workflow.py --year 2025 --verbose  # Show detailed output

Scientific basis: Verification ensures workflow outputs meet data quality
standards and computational accuracy requirements for regulatory reporting.

Assumptions:
    1. Workflow steps 1-3 have been completed for the target year
    2. pytest and all dependencies are installed
    3. Verification scripts (verify_modflow_run.py, verify_depletion.py) exist
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print('='*70)


def check_file_exists(filepath: str, description: str) -> bool:
    """
    Check if a file exists and print status.

    Args:
        filepath: Path to file to check
        description: Human-readable description

    Returns:
        True if file exists, False otherwise
    """
    exists = Path(filepath).exists()
    status = "✓" if exists else "✗"
    size = ""
    if exists:
        size_bytes = Path(filepath).stat().st_size
        if size_bytes > 1024*1024:
            size = f" ({size_bytes / (1024*1024):.1f} MB)"
        elif size_bytes > 1024:
            size = f" ({size_bytes / 1024:.1f} KB)"
    print(f"  {status} {description}: {filepath}{size}")
    return exists


def verify_step1(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 1 outputs (Tables 1-2).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 1: INGEST PUMPING DATA - {year}")

    checks_passed = 0
    total_checks = 0

    # Check output files exist
    files = [
        (f"output/ingested_data/{year}_Table_1_updated.xlsx", "Table 1 (Excel)"),
        (f"output/ingested_data/{year}_Table_1_updated.csv", "Table 1 (CSV)"),
        (f"output/ingested_data/{year}_Table_2_output.xlsx", "Table 2 (Excel)"),
        (f"output/ingested_data/{year}_Table_2_output.csv", "Table 2 (CSV)"),
    ]

    # Check monthly files
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for i, month in enumerate(months, 1):
        files.append((f"output/ingested_data/{year}_{i:02d}_{month}.csv",
                     f"Monthly data: {month}"))

    print("\n📋 File Checks:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_ingest_buckman_data.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_ingest_buckman_data.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_ingest_buckman_data.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 1 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def verify_step2(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 2 outputs (MODFLOW input files).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 2: UPDATE MODFLOW - {year}")

    checks_passed = 0
    total_checks = 0

    # Determine directory structure
    if year <= 2024:
        modflow_dir = f"output/modflow/{year}/modflow"
    else:
        modflow_dir = f"output/modflow/{year}"

    # Check MODFLOW input files
    files = [
        (f"{modflow_dir}/thruCY2165_{year}.wel", "WEL file"),
        (f"{modflow_dir}/CY{year}.nam", "NAM file"),
        (f"{modflow_dir}/modflow96.exe", "MODFLOW96 executable"),
        (f"{modflow_dir}/sflcs.bcf", "BCF package"),
        (f"{modflow_dir}/sflcs.sip", "SIP solver"),
        (f"{modflow_dir}/thruCY2165.bas", "BAS package"),
        (f"{modflow_dir}/thruCY2165.ghb", "GHB package"),
        (f"{modflow_dir}/thruCY2165.oc", "OC package"),
        (f"{modflow_dir}/thruCY2165.riv", "RIV package"),
        (f"{modflow_dir}/sfmodflx_2245.exe", "Post-processor"),
        (f"{modflow_dir}/verify_modflow_run.py", "Verification script"),
        (f"{modflow_dir}/verify_depletion.py", "Depletion verification"),
    ]

    print("\n📋 File Checks:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_update_modflow.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_update_modflow.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_update_modflow.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 2 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def verify_step3(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 3 outputs (Tables 3-5 and MODFLOW outputs).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 3: GENERATE DEPLETION TABLES - {year}")

    checks_passed = 0
    total_checks = 0

    # Determine directory structure
    if year <= 2024:
        modflow_dir = f"output/modflow/{year}/modflow"
    else:
        modflow_dir = f"output/modflow/{year}"

    # Check depletion table outputs
    files = [
        (f"output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx", "Table 3"),
        (f"output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx", "Table 4"),
        (f"output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx", "Table 5"),
    ]

    # Check MODFLOW outputs (should exist if step 3 ran)
    modflow_files = [
        (f"{modflow_dir}/CY{year}.lst", "MODFLOW list file"),
        (f"{modflow_dir}/CY{year}_riv.flx", "River flux output"),
        (f"{modflow_dir}/CY{year}_ghb.flx", "GHB flux output"),
        (f"{modflow_dir}/CY{year}_dep", "Depletion file"),
    ]

    print("\n📋 Depletion Tables:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    print("\n📋 MODFLOW Outputs:")
    for filepath, description in modflow_files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_generate_depletion_tables.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_generate_depletion_tables.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_generate_depletion_tables.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    # Run custom verification scripts if they exist
    verify_modflow_script = Path(modflow_dir) / "verify_modflow_run.py"
    if verify_modflow_script.exists():
        print(f"\n🔍 Running Custom Verification:")
        result = subprocess.run(
            ["python3", str(verify_modflow_script), str(year)],
            capture_output=not verbose,
            text=True,
            cwd=modflow_dir
        )
        total_checks += 1
        if result.returncode == 0:
            print("  ✓ verify_modflow_run.py PASSED")
            checks_passed += 1
        else:
            print("  ✗ verify_modflow_run.py FAILED")
            if verbose and result.stdout:
                print(result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 3 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Buckman wellfield depletion workflow outputs"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to verify (e.g., 2025)"
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="Verify only specific step (default: all steps)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed test output"
    )

    args = parser.parse_args()

    print_section(f"BUCKMAN WORKFLOW VERIFICATION - YEAR {args.year}")

    total_passed = 0
    total_checks = 0
    steps_run = []

    if args.step is None or args.step == 1:
        success, passed, total = verify_step1(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 1", success))

    if args.step is None or args.step == 2:
        success, passed, total = verify_step2(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 2", success))

    if args.step is None or args.step == 3:
        success, passed, total = verify_step3(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 3", success))

    # Print final summary
    print_section(f"FINAL SUMMARY - YEAR {args.year}")
    for step_name, success in steps_run:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {step_name}")

    print(f"\n📊 Overall: {total_passed}/{total_checks} checks passed")

    if total_passed == total_checks:
        print("\n🎉 All verifications passed!")
        return 0
    else:
        print(f"\n⚠️  {total_checks - total_passed} verification(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
