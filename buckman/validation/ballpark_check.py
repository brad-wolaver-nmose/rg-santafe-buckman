#!/usr/bin/env python3
"""
ballpark_check.py - Fast sanity check for Buckman Wellfield outputs.

Validates year N outputs against historical bounds (2022-2024) before
running the full 45-minute regression test. Completes in <5 seconds.

Scientific Basis:
    Groundwater depletion is cumulative and monotonic. Annual pumping
    should fall within reasonable bounds based on historical operations.
    Physics violations (negative values, non-monotonic depletions) are
    hard fails. Statistical outliers (>2σ from historical mean) are
    soft flags requiring human review.

Usage:
    python ballpark_check.py --year 2024
    python ballpark_check.py --year 2025 --outputs-dir validation/2025/outputs/

Exit Codes:
    0 - All checks passed
    1 - Script error/crash (reserved for Python exceptions)
    2 - Soft flags raised (human review recommended, continue)
    3 - Hard fails detected (physics violations, STOP)

Author: Claude Code (Anthropic)
Date: 2026-02-17
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import yaml


class CheckResult(NamedTuple):
    """Result of a single validation check."""

    name: str
    passed: bool
    is_hard_fail: bool
    message: str
    actual_value: float | None = None
    expected_range: str | None = None


def load_bounds(bounds_path: Path) -> dict:
    """
    Load historical bounds from YAML file.

    Args:
        bounds_path: Path to bounds.yaml file.

    Returns:
        Dictionary containing historical bounds and thresholds.

    Raises:
        FileNotFoundError: If bounds.yaml does not exist.
    """
    if not bounds_path.exists():
        raise FileNotFoundError(f"Bounds file not found: {bounds_path}")

    with open(bounds_path) as f:
        result: dict = yaml.safe_load(f)
        return result


def load_table(outputs_dir: Path, table_num: int, description: str) -> pd.DataFrame:
    """
    Load a table from outputs directory, trying multiple naming conventions.

    Args:
        outputs_dir: Directory containing output files.
        table_num: Table number (1-5).
        description: Human-readable description for error messages.

    Returns:
        DataFrame containing the table data.

    Raises:
        FileNotFoundError: If no matching file is found.
    """
    # Try various naming conventions (CSV and Excel)
    candidates = [
        f"Table_{table_num}_expected.xlsx",
        f"table{table_num}_expected.xlsx",
        f"expected_table{table_num}.csv",
        f"expected_table{table_num}_{description}.csv",
        f"table{table_num}_{description}.csv",
        f"Table_{table_num}.csv",
        f"Table_{table_num}.xlsx",
    ]
    for name in candidates:
        path = outputs_dir / name
        if path.exists():
            if name.endswith(".xlsx"):
                return pd.read_excel(path)
            else:
                return pd.read_csv(path)
    raise FileNotFoundError(f"Table {table_num} not found in {outputs_dir}. Tried: {candidates}")


def load_table1(outputs_dir: Path) -> pd.DataFrame:
    """Load Table 1 (annual pumping) from outputs directory."""
    return load_table(outputs_dir, 1, "annual_pumping")


def load_table3(outputs_dir: Path) -> pd.DataFrame:
    """Load Table 3 (stream depletions) from outputs directory."""
    return load_table(outputs_dir, 3, "stream_depletions")


def load_table5(outputs_dir: Path) -> pd.DataFrame:
    """Load Table 5 (La Cienega depletions) from outputs directory."""
    return load_table(outputs_dir, 5, "la_cienega_depletions")


def get_year_row(df: pd.DataFrame, year: int) -> pd.Series | None:
    """
    Find the row corresponding to a specific year in a DataFrame.

    Handles various column naming conventions for year data.

    Args:
        df: DataFrame to search.
        year: Year to find.

    Returns:
        Series for the matching row, or None if not found.
    """
    # Try common year column names
    year_cols = ["Year", "Well:", "Unnamed: 0", "year", "YEAR"]
    for col in year_cols:
        if col in df.columns:
            # Convert to numeric, coercing errors
            year_series = pd.to_numeric(df[col], errors="coerce")
            mask = year_series == year
            if mask.any():
                return df[mask].iloc[0]
    return None


def check_total_pumping(table1: pd.DataFrame, bounds: dict, year: int) -> list[CheckResult]:
    """
    Check total annual pumping against historical bounds.

    Hard fails:
        - Negative pumping
        - Exceeds 3x historical maximum (physics implausible)

    Soft flags:
        - Exceeds 2σ from historical mean
        - Exceeds 2x historical maximum
    """
    results = []
    pumping_bounds = bounds["table1_annual_pumping"]["total_annual"]

    # Find the row for this year
    year_row = get_year_row(table1, year)
    if year_row is None:
        return [
            CheckResult(
                name="total_pumping",
                passed=False,
                is_hard_fail=True,
                message=f"Cannot find year {year} in Table 1",
            )
        ]

    # Find the total column (various naming conventions)
    total_col = None
    for col in ["Total", "Annual_Total", "total", "TOTAL"]:
        if col in table1.columns:
            total_col = col
            break

    if total_col is None:
        return [
            CheckResult(
                name="total_pumping",
                passed=False,
                is_hard_fail=True,
                message="Cannot find total column in Table 1",
            )
        ]

    total_pumping = float(year_row[total_col])

    # Hard fail: Negative pumping
    if total_pumping < 0:
        results.append(
            CheckResult(
                name="pumping_non_negative",
                passed=False,
                is_hard_fail=True,
                message=f"HARD FAIL: Negative pumping detected: {total_pumping:.2f} AF",
                actual_value=total_pumping,
                expected_range=">= 0",
            )
        )
    else:
        results.append(
            CheckResult(
                name="pumping_non_negative",
                passed=True,
                is_hard_fail=False,
                message=f"PASS: Pumping is non-negative: {total_pumping:.2f} AF",
                actual_value=total_pumping,
            )
        )

    # Hard fail: Exceeds 3x historical max
    hard_max = pumping_bounds["hard_max"]
    if total_pumping > hard_max:
        results.append(
            CheckResult(
                name="pumping_hard_max",
                passed=False,
                is_hard_fail=True,
                message=f"HARD FAIL: Pumping {total_pumping:.2f} AF exceeds 3x historical max ({hard_max:.2f} AF)",
                actual_value=total_pumping,
                expected_range=f"<= {hard_max:.2f}",
            )
        )
    else:
        results.append(
            CheckResult(
                name="pumping_hard_max",
                passed=True,
                is_hard_fail=False,
                message=f"PASS: Pumping within hard limits: {total_pumping:.2f} AF",
                actual_value=total_pumping,
            )
        )

    # Soft flag: Exceeds 2x historical max
    soft_max = pumping_bounds["soft_max"]
    if total_pumping > soft_max:
        results.append(
            CheckResult(
                name="pumping_soft_max",
                passed=False,
                is_hard_fail=False,
                message=f"SOFT FLAG: Pumping {total_pumping:.2f} AF exceeds 2x historical max ({soft_max:.2f} AF)",
                actual_value=total_pumping,
                expected_range=f"<= {soft_max:.2f}",
            )
        )

    # Soft flag: Exceeds 2σ from mean
    mean = pumping_bounds["mean"]
    std = pumping_bounds["std"]
    sigma_threshold = bounds["thresholds"]["soft_flag_sigma"]
    upper_bound = mean + sigma_threshold * std
    lower_bound = mean - sigma_threshold * std

    if total_pumping > upper_bound or total_pumping < lower_bound:
        results.append(
            CheckResult(
                name="pumping_2sigma",
                passed=False,
                is_hard_fail=False,
                message=f"SOFT FLAG: Pumping {total_pumping:.2f} AF outside 2σ range [{lower_bound:.2f}, {upper_bound:.2f}]",
                actual_value=total_pumping,
                expected_range=f"[{lower_bound:.2f}, {upper_bound:.2f}]",
            )
        )
    else:
        results.append(
            CheckResult(
                name="pumping_2sigma",
                passed=True,
                is_hard_fail=False,
                message=f"PASS: Pumping within 2σ: {total_pumping:.2f} AF (range: [{lower_bound:.2f}, {upper_bound:.2f}])",
                actual_value=total_pumping,
            )
        )

    return results


def get_table3_depletions(table3: pd.DataFrame, year: int) -> tuple[float | None, float | None]:
    """
    Extract Pojoaque and Tesuque depletions from Table 3 for a given year.

    Table 3 has complex column structure. Handles multiple naming conventions.

    Returns:
        Tuple of (pojoaque_depletion, tesuque_depletion), None if not found.
    """
    # Try to find the year row
    year_row = get_year_row(table3, year)
    if year_row is None:
        return None, None

    # Pojoaque total column names
    pojoaque_cols = [
        "Unnamed: 3",  # Excel format (Total Impact column)
        "Rio_Pojoaque_Nambe_Total_AF",
        "Total\nImpact",  # May appear with newline
    ]
    pojoaque = None
    for col in pojoaque_cols:
        if col in table3.columns:
            val = year_row.get(col)
            if pd.notna(val):
                # Handle string values like "57.182** (57.185)"
                if isinstance(val, str):
                    val = val.split("(")[-1].rstrip(")")
                    val = val.replace("**", "").replace("*", "").strip()
                pojoaque = float(val)
                break

    # Tesuque total column names
    tesuque_cols = [
        "Unnamed: 6",  # Excel format (Total Impact column for Tesuque)
        "Rio_Tesuque_Total_AF",
    ]
    tesuque = None
    for col in tesuque_cols:
        if col in table3.columns:
            val = year_row.get(col)
            if pd.notna(val):
                if isinstance(val, str):
                    val = val.split("(")[-1].rstrip(")")
                    val = val.replace("**", "").replace("*", "").strip()
                tesuque = float(val)
                break

    return pojoaque, tesuque


def get_table5_la_cienega(table5: pd.DataFrame, year: int) -> float | None:
    """
    Extract La Cienega depletion from Table 5 for a given year.

    Returns:
        La Cienega depletion value, or None if not found.
    """
    year_row = get_year_row(table5, year)
    if year_row is None:
        return None

    # La Cienega column names
    la_cienega_cols = [
        "Total (AF)",
        "La_Cienega_Depletion_AF",
        "La_Cienega",
    ]
    for col in la_cienega_cols:
        if col in table5.columns:
            val = year_row.get(col)
            if pd.notna(val):
                return float(val)
    return None


def check_depletion_monotonicity(
    table3: pd.DataFrame, table5: pd.DataFrame, bounds: dict, year: int
) -> list[CheckResult]:
    """
    Check that cumulative depletions are monotonically increasing.

    This is a physics requirement: you cannot "undelete" groundwater
    that has already been removed from stream flow.

    Hard fails:
        - Current year depletion < previous year depletion
    """
    results = []
    time_series = bounds["time_series"]
    tolerance = bounds["thresholds"]["monotonic_tolerance_af"]

    # Get previous year's values if available
    years = time_series["years"]
    if year - 1 not in years:
        results.append(
            CheckResult(
                name="monotonicity_check",
                passed=True,
                is_hard_fail=False,
                message=f"SKIP: No previous year ({year - 1}) data for monotonicity check",
            )
        )
        return results

    prev_idx = years.index(year - 1)

    # Get current year values
    current_pojoaque, current_tesuque = get_table3_depletions(table3, year)
    current_la_cienega = get_table5_la_cienega(table5, year)

    # Check Rio Pojoaque/Nambe
    prev_pojoaque = time_series["rio_pojoaque_nambe_depletion_af"]["values"][prev_idx]
    if current_pojoaque is not None:
        if current_pojoaque < prev_pojoaque - tolerance:
            results.append(
                CheckResult(
                    name="monotonic_pojoaque",
                    passed=False,
                    is_hard_fail=True,
                    message=f"HARD FAIL: Pojoaque depletion decreased! {year}: {current_pojoaque:.3f} < {year - 1}: {prev_pojoaque:.3f} AF",
                    actual_value=current_pojoaque,
                    expected_range=f">= {prev_pojoaque:.3f}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="monotonic_pojoaque",
                    passed=True,
                    is_hard_fail=False,
                    message=f"PASS: Pojoaque depletion monotonic: {current_pojoaque:.3f} >= {prev_pojoaque:.3f} AF",
                    actual_value=current_pojoaque,
                )
            )
    else:
        results.append(
            CheckResult(
                name="monotonic_pojoaque",
                passed=False,
                is_hard_fail=True,
                message=f"Cannot find Pojoaque depletion for year {year} in Table 3",
            )
        )

    # Check Rio Tesuque
    prev_tesuque = time_series["rio_tesuque_depletion_af"]["values"][prev_idx]
    if current_tesuque is not None:
        if current_tesuque < prev_tesuque - tolerance:
            results.append(
                CheckResult(
                    name="monotonic_tesuque",
                    passed=False,
                    is_hard_fail=True,
                    message=f"HARD FAIL: Tesuque depletion decreased! {year}: {current_tesuque:.3f} < {year - 1}: {prev_tesuque:.3f} AF",
                    actual_value=current_tesuque,
                    expected_range=f">= {prev_tesuque:.3f}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="monotonic_tesuque",
                    passed=True,
                    is_hard_fail=False,
                    message=f"PASS: Tesuque depletion monotonic: {current_tesuque:.3f} >= {prev_tesuque:.3f} AF",
                    actual_value=current_tesuque,
                )
            )
    else:
        results.append(
            CheckResult(
                name="monotonic_tesuque",
                passed=False,
                is_hard_fail=True,
                message=f"Cannot find Tesuque depletion for year {year} in Table 3",
            )
        )

    # Check La Cienega
    prev_la_cienega = time_series["la_cienega_depletion_af"]["values"][prev_idx]
    if current_la_cienega is not None:
        if current_la_cienega < prev_la_cienega - tolerance:
            results.append(
                CheckResult(
                    name="monotonic_la_cienega",
                    passed=False,
                    is_hard_fail=True,
                    message=f"HARD FAIL: La Cienega depletion decreased! {year}: {current_la_cienega:.3f} < {year - 1}: {prev_la_cienega:.3f} AF",
                    actual_value=current_la_cienega,
                    expected_range=f">= {prev_la_cienega:.3f}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="monotonic_la_cienega",
                    passed=True,
                    is_hard_fail=False,
                    message=f"PASS: La Cienega depletion monotonic: {current_la_cienega:.3f} >= {prev_la_cienega:.3f} AF",
                    actual_value=current_la_cienega,
                )
            )
    else:
        results.append(
            CheckResult(
                name="monotonic_la_cienega",
                passed=False,
                is_hard_fail=True,
                message=f"Cannot find La Cienega depletion for year {year} in Table 5",
            )
        )

    return results


def check_depletion_bounds(table3: pd.DataFrame, bounds: dict, year: int) -> list[CheckResult]:
    """
    Check stream depletions against historical bounds.

    Soft flags:
        - Values significantly outside historical range
    """
    results = []
    stream_bounds = bounds["table3_stream_depletions"]

    # Get current year values
    current_pojoaque, current_tesuque = get_table3_depletions(table3, year)

    # Check Rio Pojoaque/Nambe
    pojoaque_bounds = stream_bounds["rio_pojoaque_nambe"]
    if current_pojoaque is not None:
        hist_max = pojoaque_bounds["max"]
        # Depletions should only increase, so we mainly check upper bound
        if current_pojoaque > hist_max * 1.5:  # 50% above historical max
            results.append(
                CheckResult(
                    name="pojoaque_bounds",
                    passed=False,
                    is_hard_fail=False,
                    message=f"SOFT FLAG: Pojoaque depletion {current_pojoaque:.3f} AF unusually high (historical max: {hist_max:.3f})",
                    actual_value=current_pojoaque,
                    expected_range=f"<= {hist_max * 1.5:.3f}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="pojoaque_bounds",
                    passed=True,
                    is_hard_fail=False,
                    message=f"PASS: Pojoaque depletion within bounds: {current_pojoaque:.3f} AF",
                    actual_value=current_pojoaque,
                )
            )

    # Check Rio Tesuque
    tesuque_bounds = stream_bounds["rio_tesuque"]
    if current_tesuque is not None:
        hist_max = tesuque_bounds["max"]
        if current_tesuque > hist_max * 1.5:
            results.append(
                CheckResult(
                    name="tesuque_bounds",
                    passed=False,
                    is_hard_fail=False,
                    message=f"SOFT FLAG: Tesuque depletion {current_tesuque:.3f} AF unusually high (historical max: {hist_max:.3f})",
                    actual_value=current_tesuque,
                    expected_range=f"<= {hist_max * 1.5:.3f}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="tesuque_bounds",
                    passed=True,
                    is_hard_fail=False,
                    message=f"PASS: Tesuque depletion within bounds: {current_tesuque:.3f} AF",
                    actual_value=current_tesuque,
                )
            )

    return results


def run_ballpark_check(year: int, outputs_dir: Path, bounds_path: Path) -> int:
    """
    Run all ballpark checks and return exit code.

    Args:
        year: The year being validated.
        outputs_dir: Directory containing output tables.
        bounds_path: Path to bounds.yaml file.

    Returns:
        0 if all checks pass, 2 if soft flags, 3 if hard fails.
        (Exit code 1 is reserved for Python exceptions/crashes)
    """
    print("=" * 60)
    print(f"BALLPARK CHECK: Year {year}")
    print(f"Outputs directory: {outputs_dir}")
    print(f"Bounds file: {bounds_path}")
    print("=" * 60)
    print()

    # Load bounds
    try:
        bounds = load_bounds(bounds_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 3  # Hard fail - missing required files

    # Load output tables
    try:
        table1 = load_table1(outputs_dir)
        table3 = load_table3(outputs_dir)
        table5 = load_table5(outputs_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 3  # Hard fail - missing required files

    # Run all checks
    all_results: list[CheckResult] = []

    print("--- Total Pumping Checks ---")
    pumping_results = check_total_pumping(table1, bounds, year)
    all_results.extend(pumping_results)
    for r in pumping_results:
        print(f"  {r.message}")

    print()
    print("--- Depletion Monotonicity Checks ---")
    mono_results = check_depletion_monotonicity(table3, table5, bounds, year)
    all_results.extend(mono_results)
    for r in mono_results:
        print(f"  {r.message}")

    print()
    print("--- Depletion Bounds Checks ---")
    bounds_results = check_depletion_bounds(table3, bounds, year)
    all_results.extend(bounds_results)
    for r in bounds_results:
        print(f"  {r.message}")

    # Summarize results
    print()
    print("=" * 60)

    hard_fails = [r for r in all_results if not r.passed and r.is_hard_fail]
    soft_flags = [r for r in all_results if not r.passed and not r.is_hard_fail]
    passes = [r for r in all_results if r.passed]

    print(f"SUMMARY: {len(passes)} passed, {len(soft_flags)} soft flags, {len(hard_fails)} hard fails")

    if hard_fails:
        print()
        print("HARD FAILS (physics violations - must fix before proceeding):")
        for r in hard_fails:
            print(f"  - {r.name}: {r.message}")
        print()
        print("EXIT CODE: 3 (hard fails detected - STOP)")
        return 3

    if soft_flags:
        print()
        print("SOFT FLAGS (statistical outliers - human review recommended):")
        for r in soft_flags:
            print(f"  - {r.name}: {r.message}")
        print()
        print("EXIT CODE: 2 (soft flags raised - continue with review)")
        return 2

    print()
    print("All checks passed! Safe to proceed with full regression.")
    print("EXIT CODE: 0")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fast sanity check for Buckman Wellfield outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - All checks passed
  1 - Script error/crash (reserved for Python exceptions)
  2 - Soft flags raised (human review recommended, continue)
  3 - Hard fails detected (physics violations, STOP)

Examples:
  python ballpark_check.py --year 2024
  python ballpark_check.py --year 2025 --outputs-dir validation/2025/outputs/
        """,
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to validate (e.g., 2024)",
    )

    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=None,
        help="Directory containing output tables. Default: validation/{year}/expected_outputs/",
    )

    parser.add_argument(
        "--bounds",
        type=Path,
        default=None,
        help="Path to bounds.yaml. Default: validation/historical/bounds.yaml",
    )

    args = parser.parse_args()

    # Set defaults
    script_dir = Path(__file__).parent
    if args.outputs_dir is None:
        args.outputs_dir = script_dir / str(args.year) / "expected_outputs"
    if args.bounds is None:
        args.bounds = script_dir / "historical" / "bounds.yaml"

    # Run checks
    exit_code = run_ballpark_check(args.year, args.outputs_dir, args.bounds)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
