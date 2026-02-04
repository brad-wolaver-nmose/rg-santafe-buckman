#!/usr/bin/env python3
"""
Stream depletion calculations for MODFLOW post-processor output.

Scientific Basis:
- Superposition model: MODFLOW calculates depletions from 1988-2024 pumping
- Analytical residuals: Core (2003) provides pre-1988 pumping effects
- Unit conversion: cfs * days * 86400 / 43560 = acre-feet

References:
- Core, A.A. (2003). Santa Fe River Water Budget Model Technical Report.
"""

from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Days per month for 2024 (leap year)
DAYS_2024: list[int] = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Otowi Gage cell definitions (layer, row, col)
ABOVE_OTOWI_CELLS: list[tuple[int, int, int]] = [
    (1, 1, 16), (1, 2, 16), (1, 3, 16), (1, 4, 16), (1, 5, 15),
    (1, 6, 14), (1, 7, 14), (1, 8, 13), (1, 9, 13), (1, 10, 12)
]

BELOW_OTOWI_CELLS: list[tuple[int, int, int]] = [
    (1, 11, 11), (1, 12, 11), (1, 13, 11), (1, 14, 10), (1, 15, 9),
    (1, 15, 10), (1, 16, 9), (1, 17, 8), (1, 18, 6), (1, 18, 7),
    (1, 19, 6), (1, 20, 5), (1, 21, 4), (1, 21, 5), (1, 22, 4), (1, 23, 3)
]


# =============================================================================
# CORE (2003) ANALYTICAL MODEL RESIDUALS
# =============================================================================

# Rio Pojoaque-Nambe: decreasing residuals from 1972-1987 pumping
# Values from Core (2003) PROJECTION.XLS, ends ~2015
CORE_2003_POJOAQUE: dict[int, float] = {
    1988: 40.432, 1989: 39.244, 1990: 37.971, 1991: 36.557, 1992: 34.928,
    1993: 33.112, 1994: 31.185, 1995: 29.226, 1996: 27.296, 1997: 25.439,
    1998: 23.678, 1999: 22.028, 2000: 20.491, 2001: 19.068, 2002: 17.753,
    2003: 16.543, 2004: 15.429, 2005: 14.404, 2006: 13.462, 2007: 12.595,
    2008: 11.797, 2009: 11.061, 2010: 10.383, 2011: 6.151, 2012: 4.693,
    2013: 3.234, 2014: 1.775, 2015: 0.316,
    # 2016+: 0 (residual effect exhausted)
}

# Rio Tesuque: longer-lasting residuals
# Values from Core (2003) PROJECTION.XLS, continues through 2050+
CORE_2003_TESUQUE: dict[int, float] = {
    1988: 21.015, 1989: 22.333, 1990: 23.391, 1991: 24.227, 1992: 24.868,
    1993: 25.327, 1994: 25.615, 1995: 25.747, 1996: 25.737, 1997: 25.608,
    1998: 25.378, 1999: 25.067, 2000: 24.691, 2001: 24.265, 2002: 23.800,
    2003: 23.308, 2004: 22.797, 2005: 22.273, 2006: 21.743, 2007: 21.212,
    2008: 20.683, 2009: 20.157, 2010: 19.639, 2011: 19.258, 2012: 18.767,
    2013: 18.276, 2014: 17.785, 2015: 17.295, 2016: 16.804, 2017: 16.313,
    2018: 15.822, 2019: 15.331, 2020: 14.841, 2021: 14.350, 2022: 13.859,
    2023: 13.368, 2024: 12.877, 2025: 12.387, 2026: 11.896, 2027: 11.405,
    2028: 10.914, 2029: 10.424, 2030: 9.933,
}


# =============================================================================
# UNIT CONVERSION FUNCTIONS
# =============================================================================

def cfs_to_acre_feet(cfs: float, days: int) -> float:
    """
    Convert cubic feet per second to acre-feet for a given period.

    Scientific basis:
    - 1 cfs = 1 ft^3/s
    - 1 acre-foot = 43,560 ft^3
    - 1 day = 86,400 seconds

    Conversion: AF = cfs * days * 86400 / 43560 = cfs * days * 1.9835

    Args:
        cfs: Flow rate in cubic feet per second. Valid range: >= 0.
        days: Number of days in the period. Valid range: 1-366.

    Returns:
        Volume in acre-feet. Precision: 6 decimal places typical.

    Raises:
        ValueError: If cfs < 0 or days < 1.

    Example:
        >>> cfs_to_acre_feet(1.0, 30)  # 1 cfs for 30 days
        59.505  # approximately

    Validation:
        Hand calculation: 1 cfs * 30 days * 1.9835 = 59.505 AF
    """
    if cfs < 0:
        raise ValueError(f"cfs must be >= 0, got {cfs}")
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")
    return cfs * days * 1.9835


def cfs_to_af(cfs_value: float, month_index: int, year: int = 2024) -> float:
    """
    Convert cfs to acre-feet for a specific month, using actual days in that month.

    Scientific basis:
    - Unit conversion factor: 86400 sec/day / 43560 ft³/AF = 1.9835 AF/(cfs·day)
    - Days per month varies: 28-31 (29 for Feb in leap years)

    Assumptions:
    1. Month index is 0-based (0=January, 11=December)
    2. Uses DAYS_2024 for 2024 (leap year with 366 days)
    3. Negative cfs values raise ValueError

    Args:
        cfs_value: Flow rate in cubic feet per second. Valid range: >= 0.
        month_index: Zero-based month index (0=Jan, 11=Dec). Valid range: 0-11.
        year: Calendar year. Default: 2024 (leap year).

    Returns:
        Volume in acre-feet for that month.

    Raises:
        ValueError: If cfs_value < 0 or month_index not in 0-11.

    Example:
        >>> cfs_to_af(0.1, 0)  # 0.1 cfs in January (31 days)
        6.14885  # 0.1 * 31 * 1.9835

    Validation:
        Hand calculation: 0.1 cfs * 31 days * 1.9835 = 6.14885 AF
    """
    if cfs_value < 0:
        raise ValueError(f"cfs_value must be >= 0, got {cfs_value}")
    if not 0 <= month_index <= 11:
        raise ValueError(f"month_index must be 0-11, got {month_index}")

    days = DAYS_2024[month_index]
    return cfs_to_acre_feet(cfs_value, days)


def cfs_monthly_to_af_annual(cfs_list: list[float], year: int = 2024) -> float:
    """
    Convert 12 monthly cfs values to annual acre-feet total.

    Scientific basis:
    - Monthly cfs values represent average flow rate for each month
    - Each month contributes: cfs[i] * days[i] * 1.9835 AF
    - Annual total is sum of all 12 months

    Assumptions:
    1. Input list has exactly 12 values (Jan-Dec order)
    2. Each value is average cfs for that entire month
    3. Uses DAYS_2024 for 2024 (leap year with 366 days)

    Args:
        cfs_list: List of 12 monthly cfs values [Jan, Feb, ..., Dec]. Valid range: all >= 0.
        year: Calendar year. Default: 2024 (leap year).

    Returns:
        Annual total volume in acre-feet.

    Raises:
        ValueError: If cfs_list doesn't have 12 elements or contains negative values.

    Example:
        >>> # Constant 0.1 cfs all year
        >>> cfs_monthly_to_af_annual([0.1] * 12)
        72.596  # 0.1 * 366 * 1.9835 (approximately)

    Validation:
        Hand calculation: 0.1 cfs * 366 days * 1.9835 = 72.5961 AF
    """
    if len(cfs_list) != 12:
        raise ValueError(f"cfs_list must have 12 elements, got {len(cfs_list)}")

    annual_af = 0.0
    for i, cfs_value in enumerate(cfs_list):
        if cfs_value < 0:
            raise ValueError(f"cfs_list[{i}] must be >= 0, got {cfs_value}")
        annual_af += cfs_to_af(cfs_value, i, year)

    return annual_af


# =============================================================================
# ANALYTICAL RESIDUAL LOOKUP
# =============================================================================

def get_analytical_residual(stream: str, year: int) -> float:
    """
    Get the Core (2003) analytical model residual for a stream and year.

    Scientific basis:
    The analytical model captures depletions from pre-1988 pumping that are
    still propagating through the aquifer system. These residuals decrease
    over time and eventually reach zero.

    Args:
        stream: Stream name, one of "pojoaque" or "tesuque" (case-insensitive).
        year: Calendar year. Valid range: 1988-2050.

    Returns:
        Residual depletion in acre-feet. Returns 0.0 if year is outside
        the range where residuals apply.

    Raises:
        ValueError: If stream name is not recognized.

    Example:
        >>> get_analytical_residual("tesuque", 2024)
        12.877
        >>> get_analytical_residual("pojoaque", 2024)
        0.0  # residual exhausted after 2015
    """
    stream_lower = stream.lower()

    if stream_lower == "pojoaque":
        return CORE_2003_POJOAQUE.get(year, 0.0)
    elif stream_lower == "tesuque":
        # For years beyond the table, use linear formula
        if year in CORE_2003_TESUQUE:
            return CORE_2003_TESUQUE[year]
        elif year > 2030:
            # Formula: y = -0.4908 * year + 1006.2
            value = -0.4908 * year + 1006.2
            return max(0.0, value)  # Don't return negative
        else:
            return 0.0
    else:
        raise ValueError(f"Unknown stream: {stream}. Expected 'pojoaque' or 'tesuque'.")


def print_residual_verification(year: int = 2024) -> None:
    """
    Print Core (2003) analytical model residual values for verification.

    Args:
        year: Calendar year to print residuals for. Default: 2024.
    """
    pojoaque_residual = get_analytical_residual("pojoaque", year)
    tesuque_residual = get_analytical_residual("tesuque", year)

    print(f"\n=== {year} Core (2003) Analytical Model Residuals ===")
    print(f"Rio Pojoaque-Nambe: {pojoaque_residual:.3f} AF")
    print(f"Rio Tesuque:        {tesuque_residual:.3f} AF")
    print(f"Note: Pojoaque residual exhausted after 2015 (now 0)")
    print(f"      Tesuque residual continues through 2050+")


# =============================================================================
# POST-PROCESSOR OUTPUT PARSING
# =============================================================================

def parse_postprocessor_output(file_path: str | Path) -> dict[int, dict[str, dict[str, float]]]:
    """
    Parse the sfmodflx_2245 post-processor output file.

    Scientific basis:
    The post-processor calculates stream depletions by summing MODFLOW
    boundary condition fluxes. Output is organized by year, with monthly
    values in cfs for each model cell and stream.

    Args:
        file_path: Path to the CY2024 output file.

    Returns:
        Nested dict: {year: {identifier: {month: value_cfs}}}
        Where identifier is cell coords like "1 13 11" or stream name like "R POJOAQUE"

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If file format is unexpected.

    Example:
        >>> data = parse_postprocessor_output("output/modflow/2024/depletions/CY2024")
        >>> data[2024]["R POJOAQUE"]["jan"]
        0.083581  # actual value from file
    """
    import re

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Post-processor output file not found: {file_path}")

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    result: dict[int, dict[str, dict[str, float]]] = {}
    current_year: int | None = None

    with open(file_path, "r") as f:
        for line in f:
            # Check for year header: "YEAR: 2024        jan         feb ..."
            year_match = re.match(r"YEAR:\s+(\d{4})\s+jan", line)
            if year_match:
                current_year = int(year_match.group(1))
                result[current_year] = {}
                continue

            if current_year is None:
                continue

            # Skip header and separator lines
            if line.strip().startswith(("LAY", "+_", "1 PUMPAGE", "number")):
                continue
            if not line.strip():
                continue

            # Parse cell data: "    1   9  14    0.025737    0.025725 ..."
            cell_match = re.match(r"\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+(?:\s+[\d.]+){11})", line)
            if cell_match:
                lay, row, col = int(cell_match.group(1)), int(cell_match.group(2)), int(cell_match.group(3))
                values_str = cell_match.group(4).strip()
                values = [float(v) for v in values_str.split()]
                if len(values) == 12:
                    cell_key = f"{lay} {row} {col}"
                    result[current_year][cell_key] = {months[i]: values[i] for i in range(12)}
                continue

            # Parse stream summary: "0  R POJOAQUE    0.083581 ..."
            stream_match = re.match(r"0\s+(R POJOAQUE|R TESUQUE|RIO GRANDE|RIV\s+TOTAL|LC SPRINGS)\s+([\d.]+(?:\s+[\d.]+){11})", line)
            if stream_match:
                stream_name = stream_match.group(1).strip()
                # Normalize RIV  TOTAL to RIV TOTAL
                stream_name = re.sub(r"\s+", " ", stream_name)
                values_str = stream_match.group(2).strip()
                values = [float(v) for v in values_str.split()]
                if len(values) == 12:
                    result[current_year][stream_name] = {months[i]: values[i] for i in range(12)}
                continue

    return result


# =============================================================================
# OTOWI DEPLETION EXTRACTION (US-005)
# =============================================================================

def extract_otowi_depletions(
    parsed_data: dict[int, dict[str, dict[str, float]]],
    year: int = 2024
) -> tuple[list[float], list[float]]:
    """
    Extract and aggregate model cell depletions for Rio Grande above and below Otowi Gage.

    Scientific basis:
    The Otowi Gage divides the Rio Grande into upstream (above) and downstream (below)
    reaches. Depletions to each reach are summed from the contributing model cells.

    Assumptions:
    1. Cell coordinates (lay, row, col) match ABOVE_OTOWI_CELLS and BELOW_OTOWI_CELLS
    2. Values are in cubic feet per second (cfs)
    3. All 10 Above Otowi cells and 16 Below Otowi cells must be present

    Args:
        parsed_data: Output from parse_postprocessor_output()
        year: Calendar year to extract. Valid range: 1988-2100. Default: 2024.

    Returns:
        Tuple of (above_cfs, below_cfs) where each is a list of 12 monthly values.

    Raises:
        KeyError: If year not found or cells missing from parsed data.

    Example:
        >>> data = parse_postprocessor_output("output/modflow/2024/depletions/CY2024")
        >>> above, below = extract_otowi_depletions(data, 2024)
        >>> sum(above)  # Total above Otowi (cfs sum, not AF)
        1.21  # approximately

    Validation:
        Compare sum(above) + sum(below) to RIO GRANDE stream total.
    """
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    if year not in parsed_data:
        raise KeyError(f"Year {year} not found in parsed data. Available years: {sorted(parsed_data.keys())}")

    year_data = parsed_data[year]

    # Sum Above Otowi cells for each month
    above_cfs: list[float] = [0.0] * 12
    for lay, row, col in ABOVE_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        if cell_key not in year_data:
            raise KeyError(f"Above Otowi cell {cell_key} not found in {year} data")
        for i, month in enumerate(months):
            above_cfs[i] += year_data[cell_key][month]

    # Sum Below Otowi cells for each month
    below_cfs: list[float] = [0.0] * 12
    for lay, row, col in BELOW_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        if cell_key not in year_data:
            raise KeyError(f"Below Otowi cell {cell_key} not found in {year} data")
        for i, month in enumerate(months):
            below_cfs[i] += year_data[cell_key][month]

    return above_cfs, below_cfs


def print_otowi_verification(above_cfs: list[float], below_cfs: list[float]) -> None:
    """
    Print Otowi depletion sums for verification.

    Args:
        above_cfs: Monthly Above Otowi depletions (cfs).
        below_cfs: Monthly Below Otowi depletions (cfs).
    """
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    print("\n=== 2024 Otowi Depletions (cfs) ===")
    print(f"{'Month':<6} {'Above':>12} {'Below':>12} {'Total':>12}")
    print("-" * 44)
    for i, month in enumerate(months):
        total = above_cfs[i] + below_cfs[i]
        print(f"{month:<6} {above_cfs[i]:>12.6f} {below_cfs[i]:>12.6f} {total:>12.6f}")
    print("-" * 44)
    print(f"{'SUM':<6} {sum(above_cfs):>12.6f} {sum(below_cfs):>12.6f} {sum(above_cfs) + sum(below_cfs):>12.6f}")


# =============================================================================
# ERROR HANDLING
# =============================================================================

# =============================================================================
# TABLE 3 DATA GENERATION (US-008)
# =============================================================================

def generate_table3_data(
    parsed_data: dict[int, dict[str, dict[str, float]]],
    year: int = 2024
) -> dict[str, dict[str, float]]:
    """
    Generate Table 3 data structure combining analytical residuals with superposition results.

    Scientific basis:
    Table 3 reports stream depletion impacts to Rio Pojoaque-Nambe and Rio Tesuque.
    For each stream, the total impact is the sum of:
    - Residual Impact (Analytical): Pre-1988 pumping effects from Core (2003)
    - Impact of 1988-2024 Pumping (Superposition): MODFLOW model results

    Assumptions:
    1. Parsed data contains "R POJOAQUE" and "R TESUQUE" stream summaries
    2. Residual values are already in acre-feet (annual)
    3. Superposition values are in cfs (monthly), need conversion to AF (annual)

    Args:
        parsed_data: Output from parse_postprocessor_output()
        year: Calendar year to generate data for. Default: 2024.

    Returns:
        Dict structure:
        {
            "pojoaque": {
                "residual_af": float,       # Core (2003) analytical residual
                "superposition_af": float,  # Sum of R POJOAQUE monthly cfs -> AF
                "total_impact_af": float    # residual + superposition
            },
            "tesuque": {
                "residual_af": float,
                "superposition_af": float,
                "total_impact_af": float
            }
        }

    Raises:
        KeyError: If year or stream data not found in parsed data.

    Example:
        >>> data = parse_postprocessor_output("output/modflow/2024/depletions/CY2024")
        >>> table3 = generate_table3_data(data, 2024)
        >>> table3["pojoaque"]["total_impact_af"]
        60.797  # approximately

    Validation:
        Compare to validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx
    """
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    if year not in parsed_data:
        raise KeyError(f"Year {year} not found in parsed data. Available years: {sorted(parsed_data.keys())}")

    year_data = parsed_data[year]

    # Extract monthly cfs values for each stream
    if "R POJOAQUE" not in year_data:
        raise KeyError(f"R POJOAQUE not found in {year} data")
    if "R TESUQUE" not in year_data:
        raise KeyError(f"R TESUQUE not found in {year} data")

    pojoaque_cfs = [year_data["R POJOAQUE"][m] for m in months]
    tesuque_cfs = [year_data["R TESUQUE"][m] for m in months]

    # Convert monthly cfs to annual acre-feet
    pojoaque_superposition_af = cfs_monthly_to_af_annual(pojoaque_cfs)
    tesuque_superposition_af = cfs_monthly_to_af_annual(tesuque_cfs)

    # Get analytical residuals from Core (2003)
    pojoaque_residual_af = get_analytical_residual("pojoaque", year)
    tesuque_residual_af = get_analytical_residual("tesuque", year)

    # Calculate total impacts
    pojoaque_total_af = pojoaque_residual_af + pojoaque_superposition_af
    tesuque_total_af = tesuque_residual_af + tesuque_superposition_af

    return {
        "pojoaque": {
            "residual_af": pojoaque_residual_af,
            "superposition_af": pojoaque_superposition_af,
            "total_impact_af": pojoaque_total_af,
        },
        "tesuque": {
            "residual_af": tesuque_residual_af,
            "superposition_af": tesuque_superposition_af,
            "total_impact_af": tesuque_total_af,
        },
    }


def print_table3_verification(table3_data: dict[str, dict[str, float]], year: int = 2024) -> None:
    """
    Print Table 3 data for verification.

    Args:
        table3_data: Output from generate_table3_data()
        year: Calendar year for header. Default: 2024.
    """
    print(f"\n=== {year} Table 3 Data (Acre-Feet) ===")
    print(f"{'Stream':<20} {'Residual':>12} {'Superposition':>15} {'Total':>12}")
    print("-" * 61)

    for stream in ["pojoaque", "tesuque"]:
        data = table3_data[stream]
        stream_name = "Rio Pojoaque-Nambe" if stream == "pojoaque" else "Rio Tesuque"
        print(f"{stream_name:<20} {data['residual_af']:>12.3f} {data['superposition_af']:>15.3f} {data['total_impact_af']:>12.3f}")

    print("-" * 61)
    total_residual = table3_data["pojoaque"]["residual_af"] + table3_data["tesuque"]["residual_af"]
    total_super = table3_data["pojoaque"]["superposition_af"] + table3_data["tesuque"]["superposition_af"]
    total_impact = table3_data["pojoaque"]["total_impact_af"] + table3_data["tesuque"]["total_impact_af"]
    print(f"{'TOTAL':<20} {total_residual:>12.3f} {total_super:>15.3f} {total_impact:>12.3f}")


# =============================================================================
# ERROR HANDLING
# =============================================================================

# Buckman Wells cell - Row 13, Column 11
BUCKMAN_WELLS_CELL: tuple[int, int, int] = (1, 13, 11)


def print_error(
    what_failed: str,
    location: str,
    actual: str,
    expected: str,
    context: str
) -> None:
    """
    Print forensic-quality error message following CLAUDE.md standards.

    Prints error information in a structured 5-element format for debugging.

    Args:
        what_failed: Description of what operation failed.
        location: Where the failure occurred (file path, function name, etc.).
        actual: The actual value that was encountered.
        expected: The expected value or condition.
        context: Physical interpretation or additional context.

    Example:
        >>> print_error(
        ...     "File not found",
        ...     "/path/to/file.txt",
        ...     "File does not exist",
        ...     "File containing flux data",
        ...     "MODFLOW model must be run first"
        ... )
        ERROR: File not found
          Location: /path/to/file.txt
          Actual: File does not exist
          Expected: File containing flux data
          Physical context: MODFLOW model must be run first
    """
    print(f"ERROR: {what_failed}")
    print(f"  Location: {location}")
    print(f"  Actual: {actual}")
    print(f"  Expected: {expected}")
    print(f"  Physical context: {context}")


# =============================================================================
# TABLE 4 DATA GENERATION (US-009)
# =============================================================================

def generate_table4_data(
    parsed_data: dict[int, dict[str, dict[str, float]]],
    year: int = 2024
) -> dict[str, Any]:
    """
    Generate Table 4 data structure with cell-level and aggregated Rio Grande depletions.

    Scientific basis:
    Table 4 reports Rio Grande depletions above and below Otowi Gage. It includes:
    - Individual cell depletions from the MODFLOW model (cfs)
    - Stream summary rows (RIO GRANDE, R POJOAQUE, LC SPRINGS, R TESUQUE, RIV TOTAL)
    - Calculations converting cfs to acre-feet using days per month

    Assumptions:
    1. Parsed data contains all required cells and stream summaries
    2. Cell values are in cfs (monthly averages)
    3. Otowi classification is determined by cell membership in ABOVE/BELOW lists

    Args:
        parsed_data: Output from parse_postprocessor_output()
        year: Calendar year to generate data for. Default: 2024.

    Returns:
        Dict structure:
        {
            "cell_data": [  # List of cell rows
                {
                    "key": int,           # Unique key (2089-2132)
                    "year": int,
                    "lay": int,
                    "row": int,
                    "col": int,
                    "monthly_cfs": [12 floats],  # Jan-Dec
                    "otowi": str          # "above" or "below" or None
                },
                ...
            ],
            "stream_summaries": {  # Stream summary data
                "RIO GRANDE": [12 floats],
                "R POJOAQUE": [12 floats],
                "LC SPRINGS": [12 floats],
                "R TESUQUE": [12 floats],
                "RIV TOTAL": [12 floats],
            },
            "days_per_month": [12 ints],
            "above_otowi_cfs": [12 floats],   # Sum of above cells (cfs)
            "below_otowi_cfs": [12 floats],   # Sum of below cells (cfs)
            "above_otowi_af": [12 floats],    # Converted to AF
            "below_otowi_af": [12 floats],    # Converted to AF
            "above_otowi_annual_af": float,   # Annual total
            "below_otowi_annual_af": float,   # Annual total
            "total_rg_af": [12 floats],       # Sum of above + below (AF)
            "total_rg_annual_af": float,      # Annual total
            "buckman_cfs": [12 floats],       # Cell (1,13,11) cfs
            "buckman_af": [12 floats],        # Converted to AF
            "buckman_annual_af": float,       # Annual total
        }

    Raises:
        KeyError: If year or required data not found in parsed data.

    Example:
        >>> data = parse_postprocessor_output("output/modflow/2024/depletions/CY2024")
        >>> table4 = generate_table4_data(data, 2024)
        >>> table4["above_otowi_annual_af"]
        277.5  # approximately

    Validation:
        Compare to validation/TABLE 4 - Rio Grande, above below Otowi.xlsx
    """
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    if year not in parsed_data:
        raise KeyError(f"Year {year} not found in parsed data. Available years: {sorted(parsed_data.keys())}")

    year_data = parsed_data[year]

    # Build cell data list - matching order from validation file
    # First, the "extra" cells (rows 2-19 in validation), then above/below Otowi
    # Looking at validation: rows 2-19 are cells like (1,9,14), (1,9,15), etc.
    # Then rows 20-29 are Above Otowi cells (with "above" label)
    # Then rows 30-45 are Below Otowi cells (with "below" label)

    cell_data: list[dict[str, Any]] = []
    key_counter = 2089  # Starting key from validation file

    # Identify Above and Below Otowi cell keys for labeling
    above_keys = {f"{lay} {row} {col}" for lay, row, col in ABOVE_OTOWI_CELLS}
    below_keys = {f"{lay} {row} {col}" for lay, row, col in BELOW_OTOWI_CELLS}

    # Collect all cells from parsed data (excluding stream summaries)
    stream_names = {"R POJOAQUE", "R TESUQUE", "RIO GRANDE", "RIV TOTAL", "LC SPRINGS"}
    all_cells: list[tuple[int, int, int]] = []

    for identifier in year_data:
        if identifier not in stream_names:
            parts = identifier.split()
            if len(parts) == 3:
                lay, row, col = int(parts[0]), int(parts[1]), int(parts[2])
                all_cells.append((lay, row, col))

    # Sort cells: first non-Otowi cells, then above Otowi, then below Otowi
    # Within each group, sort by (row, col)
    non_otowi_cells = [(l, r, c) for l, r, c in all_cells
                       if f"{l} {r} {c}" not in above_keys and f"{l} {r} {c}" not in below_keys]
    above_cells_sorted = sorted([(l, r, c) for l, r, c in all_cells
                                  if f"{l} {r} {c}" in above_keys], key=lambda x: (x[1], x[2]))
    below_cells_sorted = sorted([(l, r, c) for l, r, c in all_cells
                                  if f"{l} {r} {c}" in below_keys], key=lambda x: (x[1], x[2]))

    # Build ordered cell list matching validation file structure
    # Based on validation, order is: non-Otowi first, then Above sorted, then Below sorted
    ordered_cells = sorted(non_otowi_cells, key=lambda x: (x[1], x[2])) + above_cells_sorted + below_cells_sorted

    for lay, row, col in ordered_cells:
        cell_key = f"{lay} {row} {col}"
        monthly_cfs = [year_data[cell_key][m] for m in months]

        otowi_label: str | None = None
        if cell_key in above_keys:
            otowi_label = "above"
        elif cell_key in below_keys:
            otowi_label = "below"

        cell_data.append({
            "key": key_counter,
            "year": year,
            "lay": lay,
            "row": row,
            "col": col,
            "monthly_cfs": monthly_cfs,
            "otowi": otowi_label,
        })
        key_counter += 1

    # Extract stream summaries
    stream_summaries: dict[str, list[float]] = {}
    for stream_name in ["RIO GRANDE", "R POJOAQUE", "LC SPRINGS", "R TESUQUE", "RIV TOTAL"]:
        if stream_name not in year_data:
            raise KeyError(f"{stream_name} not found in {year} data")
        stream_summaries[stream_name] = [year_data[stream_name][m] for m in months]

    # Calculate Otowi sums
    above_cfs, below_cfs = extract_otowi_depletions(parsed_data, year)

    # Convert to acre-feet
    above_af = [cfs_to_af(above_cfs[i], i) for i in range(12)]
    below_af = [cfs_to_af(below_cfs[i], i) for i in range(12)]
    total_rg_af = [above_af[i] + below_af[i] for i in range(12)]

    # Annual totals
    above_annual = sum(above_af)
    below_annual = sum(below_af)
    total_rg_annual = above_annual + below_annual

    # Buckman wells cell (1, 13, 11)
    buckman_key = f"{BUCKMAN_WELLS_CELL[0]} {BUCKMAN_WELLS_CELL[1]} {BUCKMAN_WELLS_CELL[2]}"
    if buckman_key not in year_data:
        raise KeyError(f"Buckman wells cell {buckman_key} not found in {year} data")
    buckman_cfs = [year_data[buckman_key][m] for m in months]
    buckman_af = [cfs_to_af(buckman_cfs[i], i) for i in range(12)]
    buckman_annual = sum(buckman_af)

    return {
        "cell_data": cell_data,
        "stream_summaries": stream_summaries,
        "days_per_month": DAYS_2024,
        "above_otowi_cfs": above_cfs,
        "below_otowi_cfs": below_cfs,
        "above_otowi_af": above_af,
        "below_otowi_af": below_af,
        "above_otowi_annual_af": above_annual,
        "below_otowi_annual_af": below_annual,
        "total_rg_af": total_rg_af,
        "total_rg_annual_af": total_rg_annual,
        "buckman_cfs": buckman_cfs,
        "buckman_af": buckman_af,
        "buckman_annual_af": buckman_annual,
    }


def print_table4_verification(table4_data: dict[str, Any], year: int = 2024) -> None:
    """
    Print Table 4 summary data for verification.

    Args:
        table4_data: Output from generate_table4_data()
        year: Calendar year for header. Default: 2024.
    """
    print(f"\n=== {year} Table 4 Data Summary ===")

    # Cell count summary
    cell_data = table4_data["cell_data"]
    above_count = sum(1 for c in cell_data if c["otowi"] == "above")
    below_count = sum(1 for c in cell_data if c["otowi"] == "below")
    other_count = sum(1 for c in cell_data if c["otowi"] is None)
    print(f"Cells: {len(cell_data)} total ({above_count} above, {below_count} below, {other_count} other)")

    # Otowi depletions (AF)
    print(f"\nRio Grande Depletions (Acre-Feet):")
    print(f"  Above Otowi:  {table4_data['above_otowi_annual_af']:>10.3f} AF")
    print(f"  Below Otowi:  {table4_data['below_otowi_annual_af']:>10.3f} AF")
    print(f"  Total RG:     {table4_data['total_rg_annual_af']:>10.3f} AF")

    # Buckman wells
    print(f"\nBuckman Wells (Row 13, Col 11):")
    print(f"  Annual Total: {table4_data['buckman_annual_af']:>10.3f} AF")

    # Monthly breakdown (first 3 months as sample)
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    print(f"\nMonthly Above Otowi (AF): {months[0]}={table4_data['above_otowi_af'][0]:.3f}, "
          f"{months[1]}={table4_data['above_otowi_af'][1]:.3f}, {months[2]}={table4_data['above_otowi_af'][2]:.3f}, ...")
    print(f"Monthly Below Otowi (AF): {months[0]}={table4_data['below_otowi_af'][0]:.3f}, "
          f"{months[1]}={table4_data['below_otowi_af'][1]:.3f}, {months[2]}={table4_data['below_otowi_af'][2]:.3f}, ...")
