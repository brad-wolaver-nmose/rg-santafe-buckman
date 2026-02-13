#!/usr/bin/env python3
"""
Verify sfmodflx_2245 depletion output for any calendar year.

Auto-detects year from the directory name and compares depletion
values with the prior year to ensure results are reasonable.

Usage:
    cd output/modflow/YYYY
    python3 verify_depletion.py

Checks:
1. File structure (timesteps, year sections)
2. Summary row values (R POJOAQUE, R TESUQUE, RIO GRANDE, etc.)
3. Reasonableness (current year values within expected range of prior year)

Outputs:
- Console output with verification results
- {YEAR}_verify_depletion.md markdown report
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Auto-detect year from directory name
SCRIPT_DIR = Path(__file__).parent
TARGET_YEAR = int(SCRIPT_DIR.name)
SOURCE_YEAR = TARGET_YEAR - 1

# Paths (relative to script directory)
OUTPUT_DIR = SCRIPT_DIR
DEP_TARGET = OUTPUT_DIR / f"CY{TARGET_YEAR}_dep"
DEP_SOURCE = OUTPUT_DIR.parent / str(SOURCE_YEAR) / "depletions" / f"CY{SOURCE_YEAR}"

# Alternative path for prior year (might be in main folder, not depletions subfolder)
if not DEP_SOURCE.exists():
    DEP_SOURCE = OUTPUT_DIR.parent / str(SOURCE_YEAR) / f"CY{SOURCE_YEAR}_dep"
if not DEP_SOURCE.exists():
    DEP_SOURCE = OUTPUT_DIR.parent / str(SOURCE_YEAR) / f"CY{SOURCE_YEAR}"

# Summary row labels to extract
SUMMARY_ROWS = ["R POJOAQUE", "R TESUQUE", "RIO GRANDE", "RIV  TOTAL", "LC SPRINGS"]

# Month abbreviations
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def parse_year_summary(content: str, year: int) -> Dict[str, List[float]]:
    """
    Extract summary row values for a specific year.

    Args:
        content: Full file content
        year: Year to extract (e.g., 2024, 2025)

    Returns:
        Dict mapping summary row label to list of 12 monthly values
    """
    # Find the year section
    year_pattern = rf"YEAR:\s*{year}\s+jan"
    match = re.search(year_pattern, content, re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not find YEAR: {year} in file")

    # Extract section from year header to next year or end
    start = match.start()
    next_year = re.search(rf"YEAR:\s*{year + 1}", content[start + 50:], re.IGNORECASE)
    if next_year:
        end = start + 50 + next_year.start()
    else:
        end = len(content)

    section = content[start:end]

    # Parse summary rows
    results: Dict[str, List[float]] = {}

    for label in SUMMARY_ROWS:
        # Match line starting with "0" followed by label
        pattern = rf"0\s+{re.escape(label)}\s+([\d.\s-]+)"
        match = re.search(pattern, section)
        if match:
            values_str = match.group(1).strip()
            values = [float(v) for v in values_str.split()[:12]]
            results[label] = values

    return results


def check_file_structure(filepath: Path) -> Tuple[bool, str]:
    """Check file has expected structure."""
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    content = filepath.read_text()

    # Check timesteps
    ts_match = re.search(r"number of timesteps in file =\s*(\d+)", content)
    if not ts_match:
        return False, "Could not find timesteps header"

    timesteps = int(ts_match.group(1))
    if timesteps != 2136:
        return False, f"Expected 2136 timesteps, found {timesteps}"

    return True, f"File structure OK (timesteps={timesteps})"


def main() -> int:
    """Run verification checks."""
    print("=" * 70)
    print(f"DEPLETION OUTPUT VERIFICATION (CY{TARGET_YEAR})")
    print(f"(Auto-detected year from directory: {SCRIPT_DIR})")
    print("=" * 70)

    all_passed = True
    md_lines: List[str] = []

    # Markdown header
    md_lines.append(f"# Depletion Output Verification (CY{TARGET_YEAR})")
    md_lines.append("")
    md_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append(f"**Target Year:** {TARGET_YEAR}")
    md_lines.append(f"**Comparison Year:** {SOURCE_YEAR}")
    md_lines.append(f"**Input File:** `{DEP_TARGET.name}`")
    md_lines.append(f"**Comparison File:** `{DEP_SOURCE.name}` (prior year)")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # Check file structure
    print("\n--- File Structure Checks ---")
    md_lines.append("## File Structure Checks")
    md_lines.append("")

    ok_target, msg_target = check_file_structure(DEP_TARGET)
    print(f"CY{TARGET_YEAR}: {msg_target}")

    md_lines.append(f"| File | Status |")
    md_lines.append(f"|------|--------|")
    md_lines.append(f"| CY{TARGET_YEAR}_dep | {msg_target} |")

    if not ok_target:
        all_passed = False

    # Check prior year file
    if DEP_SOURCE.exists():
        ok_source, msg_source = check_file_structure(DEP_SOURCE)
        print(f"CY{SOURCE_YEAR}: {msg_source}")
        md_lines.append(f"| CY{SOURCE_YEAR} | {msg_source} |")
        if not ok_source:
            all_passed = False
    else:
        print(f"CY{SOURCE_YEAR}: Not found (skipping comparison)")
        md_lines.append(f"| CY{SOURCE_YEAR} | Not found (skipping comparison) |")

    md_lines.append("")

    # Compare file sizes if both exist
    if DEP_TARGET.exists() and DEP_SOURCE.exists():
        size_target = DEP_TARGET.stat().st_size
        size_source = DEP_SOURCE.stat().st_size
        size_match = size_target == size_source
        print(f"\nFile sizes: {TARGET_YEAR}={size_target:,} bytes, {SOURCE_YEAR}={size_source:,} bytes")
        print(f"Size match: {'PASS' if size_match else 'WARN (sizes differ)'}")

        md_lines.append(f"**File Sizes:** {TARGET_YEAR}={size_target:,} bytes, {SOURCE_YEAR}={size_source:,} bytes")
        md_lines.append(f"**Size Match:** {'PASS' if size_match else 'WARN'}")
        md_lines.append("")

    # Parse summary values
    print("\n--- Summary Value Comparison ---")
    print("(Depletion = reduced streamflow in CFS, + values expected)")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Summary Value Comparison")
    md_lines.append("")
    md_lines.append("Depletion = reduced streamflow in CFS (positive values expected)")
    md_lines.append("")

    if not DEP_TARGET.exists():
        print(f"ERROR: Target file not found: {DEP_TARGET}")
        md_lines.append(f"**ERROR:** Target file not found")
        return 1

    content_target = DEP_TARGET.read_text()

    try:
        summary_target = parse_year_summary(content_target, TARGET_YEAR)
    except ValueError as e:
        print(f"ERROR: {e}")
        md_lines.append(f"**ERROR:** {e}")
        return 1

    # Try to parse prior year for comparison
    summary_source = None
    if DEP_SOURCE.exists():
        content_source = DEP_SOURCE.read_text()
        try:
            summary_source = parse_year_summary(content_source, SOURCE_YEAR)
        except ValueError:
            print(f"Warning: Could not parse {SOURCE_YEAR} data from {DEP_SOURCE}")

    # Compare annual averages for each summary row
    print(f"\n{'Location':<15} {f'{SOURCE_YEAR} Avg':>12} {f'{TARGET_YEAR} Avg':>12} {'Diff %':>10} {'Status':>8}")
    print("-" * 60)

    md_lines.append("### Annual Average Depletion by Location")
    md_lines.append("")
    md_lines.append(f"| Location | {SOURCE_YEAR} Avg (CFS) | {TARGET_YEAR} Avg (CFS) | Diff % | Status |")
    md_lines.append("|----------|----------------|----------------|--------|--------|")

    for label in SUMMARY_ROWS:
        if label not in summary_target:
            print(f"{label:<15} {'N/A':>12} {'N/A':>12} {'N/A':>10} {'SKIP':>8}")
            md_lines.append(f"| {label} | N/A | N/A | N/A | SKIP |")
            continue

        avg_target = sum(summary_target[label]) / 12

        if summary_source and label in summary_source:
            avg_source = sum(summary_source[label]) / 12
            if avg_source > 0.0001:
                pct_diff = ((avg_target - avg_source) / avg_source) * 100
            else:
                pct_diff = 0.0

            # Check reasonableness (within 50% of prior year)
            status = "PASS" if abs(pct_diff) < 50 else "WARN"
            if status == "WARN":
                all_passed = False

            print(f"{label:<15} {avg_source:>12.4f} {avg_target:>12.4f} {pct_diff:>+9.1f}% {status:>8}")
            md_lines.append(f"| {label} | {avg_source:.4f} | {avg_target:.4f} | {pct_diff:+.1f}% | {status} |")
        else:
            print(f"{label:<15} {'N/A':>12} {avg_target:>12.4f} {'N/A':>10} {'OK':>8}")
            md_lines.append(f"| {label} | N/A | {avg_target:.4f} | N/A | OK |")

    md_lines.append("")

    # Monthly breakdown for RIO GRANDE (primary metric)
    print(f"\n--- RIO GRANDE Monthly Comparison ---")
    print(f"{'Month':<6} {f'{SOURCE_YEAR}':>12} {f'{TARGET_YEAR}':>12} {'Diff %':>10}")
    print("-" * 45)

    md_lines.append("### RIO GRANDE Monthly Depletion")
    md_lines.append("")
    md_lines.append(f"| Month | {SOURCE_YEAR} (CFS) | {TARGET_YEAR} (CFS) | Diff % |")
    md_lines.append("|-------|------------|------------|--------|")

    rg_target = summary_target.get("RIO GRANDE", [0] * 12)
    rg_source = summary_source.get("RIO GRANDE", [0] * 12) if summary_source else [0] * 12

    for i, month in enumerate(MONTHS):
        v_target = rg_target[i] if i < len(rg_target) else 0
        v_source = rg_source[i] if i < len(rg_source) else 0
        if v_source > 0.0001:
            pct = ((v_target - v_source) / v_source) * 100
        else:
            pct = 0.0
        print(f"{month.upper():<6} {v_source:>12.4f} {v_target:>12.4f} {pct:>+9.1f}%")
        md_lines.append(f"| {month.upper()} | {v_source:.4f} | {v_target:.4f} | {pct:+.1f}% |")

    md_lines.append("")

    # Check all values are positive (depletion should reduce streamflow)
    print("\n--- Sign Check (all values should be positive) ---")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Sign Check")
    md_lines.append("")

    sign_ok = True
    for label, values in summary_target.items():
        negatives = [v for v in values if v < 0]
        if negatives:
            print(f"WARNING: {label} has negative values: {negatives}")
            md_lines.append(f"- **WARNING:** {label} has negative values: {negatives}")
            sign_ok = False
    if sign_ok:
        print("All summary values positive: PASS")
        md_lines.append("All summary values positive: **PASS**")

    md_lines.append("")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Summary")
    md_lines.append("")

    print("\nDepletion Results:")
    rg_avg_target = sum(rg_target) / 12 if rg_target else 0
    print(f"  RIO GRANDE avg depletion {TARGET_YEAR}: {rg_avg_target:.4f} CFS")

    md_lines.append("### Depletion Results")
    md_lines.append("")
    md_lines.append(f"- RIO GRANDE avg depletion {TARGET_YEAR}: **{rg_avg_target:.4f} CFS**")

    if summary_source:
        rg_avg_source = sum(rg_source) / 12 if rg_source else 0
        print(f"  RIO GRANDE avg depletion {SOURCE_YEAR}: {rg_avg_source:.4f} CFS")
        md_lines.append(f"- RIO GRANDE avg depletion {SOURCE_YEAR}: **{rg_avg_source:.4f} CFS**")

    md_lines.append("")

    if all_passed:
        status_msg = "PASS - All checks passed"
        print(f"\nOverall: {status_msg}")
    else:
        status_msg = "WARN - Some checks flagged for review"
        print(f"\nOverall: {status_msg}")

    md_lines.append(f"### Overall Result: **{status_msg}**")
    md_lines.append("")

    # Write markdown report
    md_path = OUTPUT_DIR / f"{TARGET_YEAR}_verify_depletion.md"
    md_path.write_text("\n".join(md_lines))
    print(f"\nReport written to: {md_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
