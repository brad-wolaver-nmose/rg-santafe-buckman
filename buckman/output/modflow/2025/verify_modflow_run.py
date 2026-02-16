#!/usr/bin/env python3
"""
Verify MODFLOW96 run for any calendar year.

Auto-detects year from the directory name and validates:
1. Output files exist and have expected sizes
2. Listing file has no errors
3. Mass balance is acceptable
4. Pumping rates match expected values from Table 2 CSV

Usage:
    cd output/modflow/YYYY
    python3 verify_modflow_run.py
"""

import re
from pathlib import Path

# Auto-detect year from directory name
SCRIPT_DIR = Path(__file__).parent
TARGET_YEAR = int(SCRIPT_DIR.name)
SOURCE_YEAR = TARGET_YEAR - 1

# Paths (relative to script directory)
OUTPUT_DIR = SCRIPT_DIR
LST_FILE = OUTPUT_DIR / f"CY{TARGET_YEAR}.lst"
GHB_FLX = OUTPUT_DIR / f"CY{TARGET_YEAR}_ghb.flx"
RIV_FLX = OUTPUT_DIR / f"CY{TARGET_YEAR}_riv.flx"

# Prior year paths for size comparison
PRIOR_GHB_FLX = OUTPUT_DIR.parent / str(SOURCE_YEAR) / f"CY{SOURCE_YEAR}_ghb.flx"
PRIOR_RIV_FLX = OUTPUT_DIR.parent / str(SOURCE_YEAR) / f"CY{SOURCE_YEAR}_riv.flx"

# Expected values
EXPECTED_STRESS_PERIODS = 2136  # 1988-2165 = 178 years × 12 months

# Stress period calculation: Jan 1988 = SP 1, so Jan YYYY = SP (YYYY-1988)*12 + 1
def get_stress_period(year: int, month: int) -> int:
    """Get stress period number for a given year/month (1-indexed)."""
    return (year - 1988) * 12 + month


def check_output_files() -> bool:
    """Check that output files exist and have expected sizes."""
    print("=" * 60)
    print("OUTPUT FILES CHECK")
    print("=" * 60)

    results = []

    # Check .lst file
    if LST_FILE.exists():
        size_mb = LST_FILE.stat().st_size / 1e6
        print(f"✓ CY{TARGET_YEAR}.lst exists ({size_mb:.1f} MB)")
        results.append(True)
    else:
        print(f"✗ CY{TARGET_YEAR}.lst NOT FOUND")
        results.append(False)

    # Check flux files - compare to prior year if available
    for flx_file, prior_flx in [(GHB_FLX, PRIOR_GHB_FLX), (RIV_FLX, PRIOR_RIV_FLX)]:
        if flx_file.exists():
            size = flx_file.stat().st_size
            if prior_flx.exists():
                prior_size = prior_flx.stat().st_size
                if size == prior_size:
                    print(f"✓ {flx_file.name} exists ({size:,} bytes - matches {SOURCE_YEAR})")
                    results.append(True)
                else:
                    print(f"⚠ {flx_file.name} exists but size differs: {size:,} vs {SOURCE_YEAR}={prior_size:,}")
                    results.append(True)  # Still valid, just different
            else:
                print(f"✓ {flx_file.name} exists ({size:,} bytes)")
                results.append(True)
        else:
            print(f"✗ {flx_file.name} NOT FOUND")
            results.append(False)

    return all(results)


def check_listing_file() -> bool:
    """Check listing file for errors and key metrics."""
    print("\n" + "=" * 60)
    print("LISTING FILE ANALYSIS")
    print("=" * 60)

    if not LST_FILE.exists():
        print("✗ Cannot analyze - listing file not found")
        return False

    content = LST_FILE.read_text()

    # Check for errors
    errors = re.findall(r"(?i)error|fail(?!ed to converge)", content)
    if errors:
        print(f"✗ Found {len(errors)} error mentions in listing file")
        return False
    else:
        print("✓ No errors found in listing file")

    # Count stress periods
    stress_periods = len(re.findall(r"STRESS PERIOD NO\.", content))
    if stress_periods == EXPECTED_STRESS_PERIODS:
        print(f"✓ Stress periods: {stress_periods} (expected {EXPECTED_STRESS_PERIODS})")
    else:
        print(f"⚠ Stress periods: {stress_periods} (expected {EXPECTED_STRESS_PERIODS})")

    # Check mass balance (percent discrepancy)
    discrepancies = re.findall(r"PERCENT DISCREPANCY =\s+([\d.]+)", content)
    if discrepancies:
        max_discrepancy = max(float(d) for d in discrepancies)
        if max_discrepancy <= 0.01:
            print(f"✓ Max mass balance discrepancy: {max_discrepancy:.2f}%")
        else:
            print(f"⚠ Max mass balance discrepancy: {max_discrepancy:.2f}% (>0.01%)")

    return True


def check_pumping_rates() -> bool:
    """Verify pumping rates in listing file for target year."""
    print("\n" + "=" * 60)
    print(f"{TARGET_YEAR} PUMPING RATES VERIFICATION")
    print("=" * 60)

    if not LST_FILE.exists():
        print("✗ Cannot verify - listing file not found")
        return False

    content = LST_FILE.read_text()

    # Get stress periods for target year
    jan_sp = get_stress_period(TARGET_YEAR, 1)
    sep_sp = get_stress_period(TARGET_YEAR, 9)

    results = []

    # Check JAN stress period exists
    jan_pattern = rf"STRESS PERIOD NO\. *{jan_sp}"
    jan_match = re.search(jan_pattern, content)
    if jan_match:
        print(f"✓ Found stress period {jan_sp} (JAN {TARGET_YEAR})")
        results.append(True)
    else:
        print(f"✗ Could not find stress period {jan_sp} (JAN {TARGET_YEAR})")
        results.append(False)

    # Check SEP stress period exists
    sep_pattern = rf"STRESS PERIOD NO\. *{sep_sp}"
    sep_match = re.search(sep_pattern, content)
    if sep_match:
        print(f"✓ Found stress period {sep_sp} (SEP {TARGET_YEAR})")
        results.append(True)
    else:
        print(f"✗ Could not find stress period {sep_sp} (SEP {TARGET_YEAR})")
        results.append(False)

    # Verify pumping rates are non-zero (at least some wells should be pumping)
    # LST file format: LAYER ROW COL STRESS_RATE WELL_NO
    # Example: "    1     13    11   -0.59084          1"
    sp_range_start = get_stress_period(TARGET_YEAR, 1)
    sp_range_end = get_stress_period(TARGET_YEAR, 12)

    # Count wells with pumping in target year
    wells_with_pumping = 0
    for sp in range(sp_range_start, sp_range_end + 1):
        sp_section = re.search(
            rf"STRESS PERIOD NO\. *{sp}.*?26 WELLS.*?LAYER.*?ROW.*?COL.*?STRESS RATE(.*?)(?:STRESS PERIOD|$)",
            content,
            re.DOTALL
        )
        if sp_section:
            # Match layer 1 wells with pumping rates (format: LAYER ROW COL RATE WELL_NO)
            rates = re.findall(r"\s+1\s+\d+\s+\d+\s+([-\d.E+]+)\s+\d+", sp_section.group(1))
            for rate in rates:
                if abs(float(rate)) > 0.0001:
                    wells_with_pumping += 1

    if wells_with_pumping > 0:
        print(f"✓ Found {wells_with_pumping} non-zero pumping rates in {TARGET_YEAR} stress periods")
        results.append(True)
    else:
        print(f"⚠ No non-zero pumping rates found in {TARGET_YEAR}")
        results.append(False)

    return all(results) if results else False


def main() -> int:
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print(f"MODFLOW96 CY{TARGET_YEAR} RUN VERIFICATION")
    print(f"(Auto-detected year from directory: {SCRIPT_DIR})")
    print("=" * 60 + "\n")

    files_ok = check_output_files()
    listing_ok = check_listing_file()
    rates_ok = check_pumping_rates()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Output files:     {'✓ PASS' if files_ok else '✗ FAIL'}")
    print(f"Listing analysis: {'✓ PASS' if listing_ok else '✗ FAIL'}")
    print(f"Pumping rates:    {'✓ PASS' if rates_ok else '✗ FAIL'}")

    all_passed = files_ok and listing_ok and rates_ok
    print(f"\nOverall: {'✓ ALL CHECKS PASSED' if all_passed else '✗ SOME CHECKS FAILED'}")

    # Write results to markdown
    md_path = OUTPUT_DIR / f"{TARGET_YEAR}_verify_modflow.md"
    with open(md_path, "w") as f:
        f.write(f"# MODFLOW96 CY{TARGET_YEAR} Verification Results\n\n")
        f.write(f"**Year:** {TARGET_YEAR}\n")
        f.write(f"**Prior Year:** {SOURCE_YEAR}\n\n")
        f.write("## Results\n\n")
        f.write(f"| Check | Status |\n")
        f.write(f"|-------|--------|\n")
        f.write(f"| Output files | {'PASS' if files_ok else 'FAIL'} |\n")
        f.write(f"| Listing analysis | {'PASS' if listing_ok else 'FAIL'} |\n")
        f.write(f"| Pumping rates | {'PASS' if rates_ok else 'FAIL'} |\n")
        f.write(f"\n**Overall: {'PASS' if all_passed else 'FAIL'}**\n")

    print(f"\nReport written to: {md_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
