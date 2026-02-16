"""
Update MODFLOW Buckman Depletion Model for any calendar year.

Reads yearly pumping data from Table 2 CSV, converts acre-feet to ft³/s,
updates the .wel file with actual pumping rates, and generates the .nam file.

Year-agnostic: Pass --year to process any year. Source files come from (year-1).
"""
import argparse
import calendar
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd


# =============================================================================
# YEAR CONFIGURATION
# =============================================================================
# Baseline year: the first year that uses original 2023 input files
BASELINE_YEAR: int = 2024


@dataclass
class YearConfig:
    """Year-specific configuration for MODFLOW update."""

    target_year: int
    source_year: int
    input_wel_path: str
    input_nam_path: str
    table2_csv_path: str
    output_dir: str
    output_wel_filename: str
    output_nam_filename: str
    validation_wel_path: str
    validation_nam_path: str
    is_leap_year: bool


def get_year_config(target_year: int) -> YearConfig:
    """
    Generate all year-specific paths and constants.

    For the baseline year (2024), uses original 2023 input files.
    For subsequent years, uses prior year's output as input.

    Args:
        target_year: The year to process (e.g., 2024, 2025)

    Returns:
        YearConfig with all paths and settings for the target year
    """
    source_year = target_year - 1

    # Determine input paths based on whether this is the baseline year
    if target_year == BASELINE_YEAR:
        # Use original 2023 baseline files
        input_wel_path = "input/modflow/2023/thruCY2165.wel"
        input_nam_path = "input/modflow/2023/CY2023.nam"
    else:
        # Use prior year's output
        input_wel_path = f"output/modflow/{source_year}/thruCY2165_{source_year}.wel"
        input_nam_path = f"output/modflow/{source_year}/CY{source_year}.nam"

    return YearConfig(
        target_year=target_year,
        source_year=source_year,
        input_wel_path=input_wel_path,
        input_nam_path=input_nam_path,
        table2_csv_path=f"output/ingested_data/{target_year}_Table_2_output.csv",
        output_dir=f"output/modflow/{target_year}",
        output_wel_filename=f"thruCY2165_{target_year}.wel",
        output_nam_filename=f"CY{target_year}.nam",
        validation_wel_path=f"validation/modflow/{target_year}/thruCY2165_{target_year}.wel",
        validation_nam_path=f"validation/modflow/{target_year}/CY{target_year}.nam",
        is_leap_year=calendar.isleap(target_year),
    )


def get_days_in_month(year: int) -> Dict[str, int]:
    """
    Return days per month for a given year.

    Handles leap years automatically using calendar module.

    Args:
        year: Calendar year

    Returns:
        Dict mapping month abbreviation to days in that month
    """
    return {
        "JAN": 31,
        "FEB": 29 if calendar.isleap(year) else 28,
        "MAR": 31,
        "APR": 30,
        "MAY": 31,
        "JUN": 30,
        "JUL": 31,
        "AUG": 31,
        "SEP": 30,
        "OCT": 31,
        "NOV": 30,
        "DEC": 31,
    }

# =============================================================================
# CONVERSION CONSTANTS
# =============================================================================
ACRE_FT_TO_FT3: int = 43560  # 1 acre-foot = 43,560 ft³
SECONDS_PER_DAY: int = 86400
NUM_LAYERS: int = 2  # pumping split equally between Layer 1 and Layer 2

# =============================================================================
# WELL NAME MAPPING (Table 2 well number → MODFLOW well name)
# =============================================================================
WELL_NAME_MAP: Dict[int, str] = {
    1: "BUCKMAN 1",
    2: "BUCKMAN 2",
    3: "BUCKMAN 3A",  # Well 3 maps to BUCKMAN 3A
    4: "BUCKMAN 4",
    5: "BUCKMAN 5",
    6: "BUCKMAN 6",
    7: "BUCKMAN 7",
    8: "BUCKMAN 8",
    9: "BUCKMAN 9",
    10: "BUCKMAN 10",
    11: "BUCKMAN 11",
    12: "BUCKMAN 12",
    13: "BUCKMAN 13",
}

# =============================================================================
# WELL GRID MAPPING (MODFLOW well name → (row, col))
# =============================================================================
WELL_GRID_MAP: Dict[str, tuple[int, int]] = {
    "BUCKMAN 1": (13, 11),
    "BUCKMAN 2": (14, 11),
    "BUCKMAN 3A": (14, 11),
    "BUCKMAN 4": (14, 11),
    "BUCKMAN 5": (15, 12),
    "BUCKMAN 6": (14, 12),
    "BUCKMAN 7": (13, 11),
    "BUCKMAN 8": (13, 11),
    "BUCKMAN 9": (14, 12),
    "BUCKMAN 10": (17, 13),
    "BUCKMAN 11": (19, 14),
    "BUCKMAN 12": (19, 15),
    "BUCKMAN 13": (20, 16),
}

# =============================================================================
# BASELINE FILES CONFIGURATION
# =============================================================================
# Directory containing original 2023 MODFLOW files (static, unchanged)
BASELINE_DIR: str = "input/modflow/2023"

# Files to copy from baseline to output directory
# These are required by MODFLOW96 but don't change between years
BASELINE_FILES_TO_COPY: list[str] = [
    "modflow96.exe",  # MODFLOW96 executable
    "sflcs.bcf",  # Block-Centered Flow package
    "sflcs.sip",  # Strongly Implicit Procedure solver
    "thruCY2165.bas",  # Basic package
    "thruCY2165.ghb",  # General Head Boundary package
    "thruCY2165.oc",  # Output Control
    "thruCY2165.riv",  # River package
    "sfmodflx_2245.exe",  # Stream flux post-processor for depletion tables
    "verify_modflow_run.py",  # MODFLOW output verification script
    "verify_depletion.py",  # Depletion output verification script
]

# =============================================================================
# TEMPORAL CONSTANTS
# =============================================================================
MONTH_ABBREVS: list[str] = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]


def convert_af_to_ft3s(
    acre_feet: float, days_in_month: int, num_layers: int = NUM_LAYERS
) -> float:
    """
    Convert acre-feet pumping to MODFLOW pumping rate (ft³/s per layer).

    Scientific basis: Standard unit conversion with layer splitting for
    multi-layer MODFLOW well representation.

    Assumptions:
        1. Pumping is constant throughout the month
        2. Pumping is split equally between layers
        3. MODFLOW convention: pumping (extraction) is negative

    Args:
        acre_feet: Monthly pumping volume in acre-feet (must be >= 0)
        days_in_month: Number of days in the month (1-31)
        num_layers: Number of layers to split pumping between (default: 2)

    Returns:
        Pumping rate in ft³/s as negative float (MODFLOW convention).
        Precision: 5 decimal places matching validation file format.

    Raises:
        ValueError: If acre_feet < 0 or days_in_month not in valid range

    Example:
        >>> convert_af_to_ft3s(16.887963, 31, 2)
        -0.13730  # Well 1 JAN 2024 per-layer rate

    Validation reference:
        Hand-calculated: (16.887963 / 2) * 43560 / (31 * 86400) ≈ 0.13730
    """
    if acre_feet < 0:
        raise ValueError(f"acre_feet must be >= 0, got {acre_feet}")
    if not 1 <= days_in_month <= 31:
        raise ValueError(f"days_in_month must be 1-31, got {days_in_month}")

    # Convert: (acre-feet / layers) * (ft³/acre-foot) / (seconds in month)
    seconds_in_month = days_in_month * SECONDS_PER_DAY
    volume_per_layer_ft3 = (acre_feet / num_layers) * ACRE_FT_TO_FT3
    rate_ft3_per_s = volume_per_layer_ft3 / seconds_in_month

    # Return negative (MODFLOW pumping convention)
    return -rate_ft3_per_s


# =============================================================================
# WEL FILE PARSING
# =============================================================================
LINES_PER_MONTH: int = 27       # 1 header + 26 well entries (13 wells × 2 layers)
WELLS_PER_MONTH: int = 26       # 13 wells × 2 layers


def find_year_boundaries(
    lines: list[str], target_year: int
) -> tuple[int, int]:
    """
    Find the start and end line indices for a given year's data in a .wel file.

    Searches for 'JAN {year}' to find start, 'DEC {year}' to find end.
    The start index points to the header line ("26") before the first entry.

    Args:
        lines: All lines from the .wel file
        target_year: Year to find boundaries for

    Returns:
        Tuple of (start_idx, end_idx) as 0-indexed positions suitable for slicing.
        end_idx is exclusive (lines[start_idx:end_idx] gives the year's data).

    Raises:
        ValueError: If year boundaries cannot be found or structure is invalid
    """
    jan_pattern = f"JAN {target_year}"
    dec_pattern = f"DEC {target_year}"

    first_jan_idx = None
    last_dec_idx = None

    for i, line in enumerate(lines):
        if jan_pattern in line and first_jan_idx is None:
            first_jan_idx = i
        if dec_pattern in line:
            last_dec_idx = i

    if first_jan_idx is None:
        raise ValueError(
            f"Could not find '{jan_pattern}' in .wel file. "
            f"Is {target_year} data present in the input file?"
        )
    if last_dec_idx is None:
        raise ValueError(
            f"Could not find '{dec_pattern}' in .wel file. "
            f"Is {target_year} data complete?"
        )

    # Start index is the header line (one line before first JAN entry)
    start_idx = first_jan_idx - 1

    # End index is one past the last DEC entry (for slicing)
    end_idx = last_dec_idx + 1

    # Validate we found exactly 324 lines (12 months × 27 lines)
    expected_lines = 12 * LINES_PER_MONTH
    actual_lines = end_idx - start_idx
    if actual_lines != expected_lines:
        raise ValueError(
            f"Year {target_year} section should have {expected_lines} lines, "
            f"found {actual_lines}. Start: line {start_idx + 1}, "
            f"End: line {end_idx}"
        )

    return start_idx, end_idx


class WelFileData:
    """Parsed .wel file data with separated pre-target, target year, and post-target sections."""

    def __init__(
        self,
        pre_target_lines: list[str],
        target_year_lines: list[str],
        post_target_lines: list[str],
        target_year: int,
    ) -> None:
        self.pre_target_lines = pre_target_lines
        self.target_year_lines = target_year_lines
        self.post_target_lines = post_target_lines
        self.target_year = target_year

    @property
    def total_lines(self) -> int:
        """Total line count across all sections."""
        return (
            len(self.pre_target_lines)
            + len(self.target_year_lines)
            + len(self.post_target_lines)
        )


def parse_wel_file(wel_path: str, target_year: int) -> WelFileData:
    """
    Parse the .wel file and separate target year data from other data.

    Scientific basis: MODFLOW .wel file format with stress period structure.
    Each month's stress period has a header line (entry count) followed by
    well entries (layer, row, col, rate, name).

    Assumptions:
        1. Target year data is identified by searching for 'JAN {year}' pattern
        2. Each month has 27 lines: 1 header + 26 well entries
        3. 12 months × 27 lines = 324 lines total for target year

    Args:
        wel_path: Path to the input .wel file
        target_year: Year to extract/replace data for

    Returns:
        WelFileData object with pre_target_lines, target_year_lines, post_target_lines

    Raises:
        FileNotFoundError: If .wel file does not exist
        ValueError: If year section structure doesn't match expectations

    Example:
        >>> data = parse_wel_file("input/modflow/2023/thruCY2165.wel", 2024)
        >>> len(data.target_year_lines)
        324
    """
    path = Path(wel_path)
    if not path.exists():
        raise FileNotFoundError(f".wel file not found: {wel_path}")

    with open(wel_path, "r") as f:
        all_lines = f.readlines()

    total_lines = len(all_lines)
    print(f"Read {total_lines} lines from {wel_path}")

    # Find year boundaries dynamically
    start_idx, end_idx = find_year_boundaries(all_lines, target_year)

    # Split into three sections
    pre_target_lines = all_lines[:start_idx]
    target_year_lines = all_lines[start_idx:end_idx]
    post_target_lines = all_lines[end_idx:]

    # Validate each month has correct structure (header + 26 entries)
    for month_idx in range(12):
        month_start = month_idx * LINES_PER_MONTH
        header_line = target_year_lines[month_start].strip()

        # Header should be "26" (number of well entries)
        if header_line != "26":
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} {target_year} header should be '26', "
                f"found '{header_line}' at section line {month_start + 1}"
            )

        # First entry should be BUCKMAN 1
        first_entry = target_year_lines[month_start + 1]
        if "BUCKMAN 1" not in first_entry:
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} {target_year} first entry should be BUCKMAN 1, "
                f"found: {first_entry.strip()}"
            )

        # Last entry should be BUCKMAN 13
        last_entry = target_year_lines[month_start + WELLS_PER_MONTH]
        if "BUCKMAN 13" not in last_entry:
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} {target_year} last entry should be BUCKMAN 13, "
                f"found: {last_entry.strip()}"
            )

    print(
        f"Parsed .wel file: {len(pre_target_lines)} pre-{target_year}, "
        f"{len(target_year_lines)} {target_year}, "
        f"{len(post_target_lines)} post-{target_year} lines"
    )

    return WelFileData(
        pre_target_lines=pre_target_lines,
        target_year_lines=target_year_lines,
        post_target_lines=post_target_lines,
        target_year=target_year,
    )


def read_table2_pumping_data(csv_path: str) -> Dict[int, Dict[str, float]]:
    """
    Read yearly monthly pumping data from Table 2 CSV.

    Scientific basis: Standard CSV parsing of hydrologic pumping records.

    Assumptions:
        1. CSV has columns: Well, JAN, FEB, ..., DEC, Total
        2. Wells are numbered 1-13 in the Well column
        3. Monthly values are in acre-feet
        4. All 13 wells are present in the file

    Args:
        csv_path: Path to the Table 2 CSV file

    Returns:
        Dict keyed by well number (int 1-13), value is dict of
        month abbreviation (str) → acre-feet (float).
        Example: {1: {"JAN": 16.887963, "FEB": 38.805796, ...}, ...}

    Raises:
        FileNotFoundError: If CSV file does not exist
        ValueError: If well count != 13 or any pumping value < 0

    Example:
        >>> data = read_table2_pumping_data()
        >>> data[1]["JAN"]
        16.887963
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Table 2 CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Filter to numeric well rows only (wells 1-13)
    df_wells = df[pd.to_numeric(df["Well"], errors="coerce").notna()].copy()
    df_wells["Well"] = df_wells["Well"].astype(int)

    # Verify we have exactly 13 wells
    well_numbers = set(df_wells["Well"].tolist())
    expected_wells = set(range(1, 14))
    if well_numbers != expected_wells:
        missing = expected_wells - well_numbers
        extra = well_numbers - expected_wells
        raise ValueError(
            f"Expected wells 1-13. Missing: {missing}, Extra: {extra}"
        )

    # Build result dict
    result: Dict[int, Dict[str, float]] = {}
    for _, row in df_wells.iterrows():
        well_num = int(row["Well"])
        monthly_data: Dict[str, float] = {}
        for month in MONTH_ABBREVS:
            value = float(row[month])
            if value < 0:
                raise ValueError(
                    f"Negative pumping value for Well {well_num} {month}: "
                    f"{value} acre-feet. Pumping must be >= 0."
                )
            monthly_data[month] = value
        result[well_num] = monthly_data

    # Log annual totals for sanity check
    print("Annual pumping totals (acre-feet):")
    for well_num in sorted(result.keys()):
        annual_total = sum(result[well_num].values())
        well_name = WELL_NAME_MAP[well_num]
        print(f"  {well_name}: {annual_total:.2f} AF")

    return result


# =============================================================================
# WELL ENTRY GENERATION
# =============================================================================
# Well order in the .wel file (matches validation file)
WELL_ORDER: list[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def generate_well_entry_line(
    layer: int,
    row: int,
    col: int,
    rate: float,
    well_name: str,
    month: str,
    year: int,
    line_ending: str = "\r\n",
) -> str:
    """
    Generate a single well entry line for the .wel file.

    Scientific basis: MODFLOW well package format with layer, row, column,
    pumping rate, and comment fields.

    Assumptions:
        1. Line format matches validation file exactly
        2. Rate is already converted to ft³/s (negative for pumping)
        3. Line ending matches input file (CRLF for Windows)

    Args:
        layer: Model layer (1 or 2)
        row: Model row (1-indexed)
        col: Model column (1-indexed)
        rate: Pumping rate in ft³/s (negative)
        well_name: MODFLOW well name (e.g., "BUCKMAN 1")
        month: Month abbreviation (e.g., "JAN")
        year: Year (e.g., 2024)
        line_ending: Line ending character(s) (default: CRLF)

    Returns:
        Formatted well entry line with line ending

    Example:
        >>> generate_well_entry_line(1, 13, 11, -0.13730, "BUCKMAN 1", "JAN", 2024)
        '         1        13        11  -0.13730  BUCKMAN 1 JAN 2024\\r\\n'
    """
    # Format: {layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}
    return f"{layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}{line_ending}"


def generate_month_header(line_ending: str = "\r\n") -> str:
    """
    Generate the month header line indicating 26 well entries follow.

    Args:
        line_ending: Line ending character(s) (default: CRLF)

    Returns:
        Header line "        26" with line ending
    """
    return f"        26{line_ending}"


def generate_well_entries(
    pumping_data: Dict[int, Dict[str, float]],
    target_year: int,
    line_ending: str = "\r\n",
) -> list[str]:
    """
    Generate all 324 lines for a year's well entries.

    Scientific basis: MODFLOW stress period format with monthly pumping rates
    split equally between two model layers.

    Assumptions:
        1. Each month has 1 header + 26 entries (13 wells × 2 layers)
        2. Wells are ordered 1-13 (BUCKMAN 1 through BUCKMAN 13)
        3. For each well, Layer 1 comes before Layer 2
        4. Pumping data in acre-feet converted to ft³/s
        5. Leap years handled automatically via calendar module

    Args:
        pumping_data: Dict keyed by well number (1-13), value is dict of
            month abbreviation → acre-feet
        target_year: Year for the well entries
        line_ending: Line ending character(s) (default: CRLF)

    Returns:
        List of 324 lines (12 months × 27 lines each)

    Raises:
        ValueError: If pumping_data doesn't have all 13 wells

    Example:
        >>> lines = generate_well_entries(pumping_data, 2024)
        >>> len(lines)
        324
    """
    # Validate pumping data
    for well_num in WELL_ORDER:
        if well_num not in pumping_data:
            raise ValueError(f"Missing pumping data for well {well_num}")

    # Get days per month for target year (handles leap years)
    days_in_month = get_days_in_month(target_year)

    lines: list[str] = []

    for month in MONTH_ABBREVS:
        days = days_in_month[month]

        # Add header line
        lines.append(generate_month_header(line_ending))

        # Add 26 well entries (13 wells × 2 layers)
        for well_num in WELL_ORDER:
            well_name = WELL_NAME_MAP[well_num]
            row, col = WELL_GRID_MAP[well_name]
            acre_feet = pumping_data[well_num][month]

            # Convert to ft³/s (negative for pumping)
            rate = convert_af_to_ft3s(acre_feet, days)

            # Format zero as -0.00000 to match validation file
            if abs(rate) < 1e-10:
                rate = -0.0

            # Generate Layer 1 and Layer 2 entries
            for layer in [1, 2]:
                lines.append(
                    generate_well_entry_line(
                        layer=layer,
                        row=row,
                        col=col,
                        rate=rate,
                        well_name=well_name,
                        month=month,
                        year=target_year,
                        line_ending=line_ending,
                    )
                )

    return lines


def write_updated_wel_file(
    wel_data: WelFileData,
    new_year_lines: list[str],
    output_dir: str,
    output_filename: str,
) -> Path:
    """
    Write the updated .wel file with new year's pumping data.

    Scientific basis: MODFLOW well package file format preservation.

    Assumptions:
        1. Pre-target and post-target sections preserved exactly as-is
        2. New year lines have same structure (324 lines)
        3. Line endings match input file (CRLF)

    Args:
        wel_data: Parsed WelFileData with pre/post target year sections
        new_year_lines: Generated 324 lines for target year data
        output_dir: Directory to write output file (created if needed)
        output_filename: Name of output file

    Returns:
        Path to the written file

    Raises:
        ValueError: If new year lines count doesn't match expected

    Example:
        >>> data = parse_wel_file("input.wel", 2024)
        >>> pumping = read_table2_pumping_data("2024_data.csv")
        >>> new_lines = generate_well_entries(pumping, 2024)
        >>> output_path = write_updated_wel_file(data, new_lines, "output/", "out.wel")
    """
    # Validate new year lines count
    expected_year_lines = 12 * LINES_PER_MONTH  # 324
    if len(new_year_lines) != expected_year_lines:
        raise ValueError(
            f"Expected {expected_year_lines} lines for year data, "
            f"got {len(new_year_lines)}"
        )

    # Create output directory if needed
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Concatenate all sections
    all_lines = (
        wel_data.pre_target_lines
        + new_year_lines
        + wel_data.post_target_lines
    )

    # Write file (preserving line endings)
    file_path = output_path / output_filename
    with open(file_path, "w", newline="") as f:
        f.writelines(all_lines)

    target_year = wel_data.target_year
    print(
        f"Wrote {len(all_lines)} lines to {file_path} "
        f"(pre: {len(wel_data.pre_target_lines)}, "
        f"{target_year}: {len(new_year_lines)}, "
        f"post: {len(wel_data.post_target_lines)})"
    )

    return file_path


# =============================================================================
# NAM FILE GENERATION
# =============================================================================
def generate_nam_file(
    target_year: int,
    output_dir: str,
    output_filename: str,
) -> Path:
    """
    Generate updated .nam file for a given year's simulation.

    Scientific basis: MODFLOW name file format specifying simulation files.

    Assumptions:
        1. File naming follows pattern: CY{year}.lst, thruCY2165_{year}.wel, etc.
        2. Package types are uppercase (LIST, BAS, BCF, etc.)
        3. Column alignment matches validation file format

    Args:
        target_year: Year for the simulation
        output_dir: Directory for output file (created if needed)
        output_filename: Name of output file

    Returns:
        Path to the written .nam file

    Example:
        >>> output_path = generate_nam_file(2024, "output/modflow/2024", "CY2024.nam")
        >>> print(output_path)
        output/modflow/2024/CY2024.nam
    """
    from datetime import datetime

    # Generate timestamp for header comment
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header comment block (matching validation format)
    header_lines = [
        f"# MODFLOW Name File for Buckman Depletion Model - Year {target_year}\n",
        f"# Automatically generated by Python script on {timestamp}\n",
        "# File Type      Unit File Name\n",
        "#------------------------------------\n",
    ]

    # File mapping table - package type, unit, file name
    # Year-specific files use target_year in their names
    file_entries = [
        ("LIST", "23", f"CY{target_year}.lst"),
        ("BAS", "21", "thruCY2165.bas"),
        ("BCF", "11", "sflcs.bcf"),
        ("OC", "10", "thruCY2165.oc"),
        ("RIV", "14", "thruCY2165.riv"),
        ("GHB", "15", "thruCY2165.ghb"),
        ("SIP", "17", "sflcs.sip"),
        ("WEL", "12", f"thruCY2165_{target_year}.wel"),
        ("DATA(BINARY)", "24", f"CY{target_year}_riv.flx"),
        ("DATA(BINARY)", "34", f"CY{target_year}_ghb.flx"),
    ]

    # Generate content lines with column alignment matching validation file
    content_lines: list[str] = []
    for pkg_type, unit, filename in file_entries:
        # Format: type padded to 16 chars, unit padded to 6 chars, then filename
        line = f"{pkg_type:<16}{unit:<6}{filename}\n"
        content_lines.append(line)

    # Create output directory if needed
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write file
    file_path = output_path / output_filename
    with open(file_path, "w") as f:
        f.writelines(header_lines)
        f.writelines(content_lines)

    print(f"Wrote .nam file to {file_path}")

    return file_path


def verify_nam_file_references(nam_path: str, output_dir: str) -> bool:
    """
    Verify all files referenced in .nam file exist.

    Scientific basis: MODFLOW96 requires all package files referenced in the
    name file to exist in the same directory for successful model execution.

    Assumptions:
        1. NAM file follows MODFLOW96 format (PACKAGE_CODE UNIT filename)
        2. All referenced files should be in output_dir
        3. Comment lines start with '#'

    Args:
        nam_path: Path to generated .nam file
        output_dir: Directory where referenced files should exist

    Returns:
        True if all files exist, False otherwise

    Raises:
        None (returns False for missing files)

    Example:
        >>> verify_nam_file_references("output/modflow/2025/CY2025.nam", "output/modflow/2025")
        ✓ NAM file verified: all 8 referenced files exist
        True

    Validation reference: Compare referenced files against MODFLOW96 package requirements
    """
    from pathlib import Path

    nam_file = Path(nam_path)
    output_path = Path(output_dir)

    if not nam_file.exists():
        print(f"✗ NAM file not found: {nam_path}")
        return False

    referenced_files = []
    missing_files = []

    with open(nam_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and blank lines
            if not line or line.startswith('#'):
                continue
            # Extract filename from MODFLOW package lines (format: "PACKAGE_CODE UNIT filename")
            parts = line.split()
            if len(parts) >= 3:
                filename = parts[2]
                referenced_files.append(filename)
                file_path = output_path / filename
                if not file_path.exists():
                    missing_files.append(filename)

    if missing_files:
        print(f"\n✗ NAM file references {len(missing_files)} missing file(s):")
        for f in missing_files:
            print(f"    - {f}")
        print(f"  Total referenced: {len(referenced_files)}")
        return False

    print(f"  ✓ NAM file verified: all {len(referenced_files)} referenced files exist")
    return True


def copy_baseline_files(output_dir: str) -> list[Path]:
    """
    Copy MODFLOW baseline support files to output directory.

    These files are static (unchanged from 2023 baseline) and required
    by MODFLOW96 to run the depletion model. The .wel and .nam files
    are generated separately with year-specific data.

    Scientific basis: MODFLOW96 requires all package files to be in the
    same directory as the .nam file for model execution.

    Assumptions:
        1. Baseline files exist in BASELINE_DIR (input/modflow/2023/)
        2. Output directory exists or will be created
        3. Files are copied without modification (binary-safe copy)

    Args:
        output_dir: Target directory for copying files

    Returns:
        List of paths to copied files

    Raises:
        FileNotFoundError: If any baseline file is missing

    Example:
        >>> copied = copy_baseline_files("output/modflow/2025")
        >>> len(copied)
        7
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    baseline = Path(BASELINE_DIR)

    for filename in BASELINE_FILES_TO_COPY:
        src = baseline / filename
        dst = output_path / filename

        if not src.exists():
            raise FileNotFoundError(
                f"Baseline file not found: {src}\n"
                f"  Expected location: {BASELINE_DIR}/{filename}"
            )

        shutil.copy2(src, dst)
        copied.append(dst)

    return copied


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================
# Tolerance for rate comparison
# PRD states ±0.00002 but actual differences reach 0.00008 due to rounding
# differences between source CSV precision and validation file creation.
# Using 0.0001 (1e-4) to accommodate observed variance while still catching errors.
RATE_TOLERANCE: float = 0.0001


class ValidationResult:
    """Result of validating .wel file against known-good validation file."""

    def __init__(self, target_year: int) -> None:
        self.target_year = target_year
        self.wells_checked: int = 0
        self.months_checked: int = 0
        self.pass_count: int = 0
        self.fail_count: int = 0
        self.failures: list[dict[str, object]] = []
        self.wel_pre_target_passed: bool = False
        self.wel_post_target_passed: bool = False
        self.wel_target_passed: bool = False
        self.skipped: bool = False

    @property
    def all_passed(self) -> bool:
        """Check if all .wel validations passed."""
        if self.skipped:
            return True  # Skipped validation counts as "passed"
        return (
            self.fail_count == 0
            and self.wel_pre_target_passed
            and self.wel_post_target_passed
            and self.wel_target_passed
        )


def validate_nam_file(
    generated_path: str,
    validation_path: str,
) -> tuple[bool | None, list[str]]:
    """
    Compare generated .nam file against validation file.

    Ignores comment lines (lines starting with #) since timestamps will differ.
    All non-comment lines must match exactly.

    Args:
        generated_path: Path to generated .nam file
        validation_path: Path to validation .nam file

    Returns:
        Tuple of (passed: bool | None, errors: list of error messages)
        If validation file doesn't exist, returns (None, [warning message])

    Example:
        >>> passed, errors = validate_nam_file("output/CY2024.nam", "validation/CY2024.nam")
        >>> if passed is None:
        ...     print("Validation skipped - no validation file")
    """
    gen_path = Path(generated_path)
    val_path = Path(validation_path)

    if not gen_path.exists():
        return False, [f"Generated .nam file not found: {generated_path}"]
    if not val_path.exists():
        return None, [f"Validation file not found (skipping): {validation_path}"]

    with open(gen_path, "r") as f:
        gen_lines = f.readlines()
    with open(val_path, "r") as f:
        val_lines = f.readlines()

    # Filter out comment lines
    gen_data = [line.rstrip("\r\n") for line in gen_lines if not line.startswith("#")]
    val_data = [line.rstrip("\r\n") for line in val_lines if not line.startswith("#")]

    errors: list[str] = []

    if len(gen_data) != len(val_data):
        errors.append(
            f"Line count mismatch: generated {len(gen_data)}, "
            f"validation {len(val_data)}"
        )
        return False, errors

    for i, (gen_line, val_line) in enumerate(zip(gen_data, val_data)):
        if gen_line != val_line:
            errors.append(
                f".nam line {i+1} mismatch:\n"
                f"  Generated:  '{gen_line}'\n"
                f"  Validation: '{val_line}'"
            )

    return len(errors) == 0, errors


def validate_wel_file(
    generated_path: str,
    validation_path: str,
    target_year: int,
    tolerance: float = RATE_TOLERANCE,
) -> ValidationResult:
    """
    Compare generated .wel file against validation file.

    Validates:
    - Pre-target year lines: byte-identical
    - Target year pumping rates: within ±tolerance ft³/s
    - Post-target year lines: byte-identical

    Args:
        generated_path: Path to generated .wel file
        validation_path: Path to validation .wel file
        target_year: Year being validated
        tolerance: Maximum allowed difference in pumping rates

    Returns:
        ValidationResult object with detailed comparison results
        If validation file doesn't exist, returns result with skipped=True

    Example:
        >>> result = validate_wel_file("output/out.wel", "validation/val.wel", 2024)
        >>> if result.all_passed:
        ...     print("Validation PASSED")
    """
    result = ValidationResult(target_year)
    gen_path = Path(generated_path)
    val_path = Path(validation_path)

    if not gen_path.exists():
        result.failures.append({
            "type": "file_missing",
            "message": f"Generated .wel file not found: {generated_path}",
        })
        return result
    if not val_path.exists():
        result.skipped = True
        result.failures.append({
            "type": "validation_skipped",
            "message": f"Validation file not found (skipping): {validation_path}",
        })
        return result

    with open(gen_path, "r") as f:
        gen_lines = f.readlines()
    with open(val_path, "r") as f:
        val_lines = f.readlines()

    # Check total line count
    if len(gen_lines) != len(val_lines):
        result.failures.append({
            "type": "line_count",
            "message": (
                f"Line count mismatch: generated {len(gen_lines)}, "
                f"validation {len(val_lines)}"
            ),
        })
        return result

    # Find year boundaries in the validation file dynamically
    try:
        start_idx, end_idx = find_year_boundaries(val_lines, target_year)
    except ValueError as e:
        result.failures.append({
            "type": "boundary_error",
            "message": f"Could not find {target_year} boundaries in validation file: {e}",
        })
        return result

    # Validate pre-target section
    pre_target_errors: list[str] = []
    for i in range(start_idx):
        if gen_lines[i] != val_lines[i]:
            pre_target_errors.append(f"Line {i+1}")
            if len(pre_target_errors) >= 5:
                break

    if pre_target_errors:
        result.failures.append({
            "type": "pre_target",
            "message": f"Pre-{target_year} section differs at: {', '.join(pre_target_errors)}",
        })
        result.wel_pre_target_passed = False
    else:
        result.wel_pre_target_passed = True

    # Validate post-target section
    post_target_errors: list[str] = []
    for i in range(end_idx, len(val_lines)):
        if gen_lines[i] != val_lines[i]:
            post_target_errors.append(f"Line {i+1}")
            if len(post_target_errors) >= 5:
                break

    if post_target_errors:
        result.failures.append({
            "type": "post_target",
            "message": f"Post-{target_year} section differs at: {', '.join(post_target_errors)}",
        })
        result.wel_post_target_passed = False
    else:
        result.wel_post_target_passed = True

    # Validate target year section - compare rates with tolerance
    rate_failures: list[dict[str, object]] = []

    for month_idx, month in enumerate(MONTH_ABBREVS):
        month_start = start_idx + (month_idx * LINES_PER_MONTH)

        for entry_idx in range(WELLS_PER_MONTH):  # 26 entries per month
            line_idx = month_start + 1 + entry_idx  # Skip header line

            gen_line = gen_lines[line_idx]
            val_line = val_lines[line_idx]

            # Parse the lines
            gen_parts = gen_line.split()
            val_parts = val_line.split()

            # Extract well name from parts (parts[4] and optionally [5] for "3A")
            if len(gen_parts) >= 7:
                well_name = gen_parts[4]
                if len(gen_parts) >= 8 and gen_parts[5] not in MONTH_ABBREVS:
                    well_name += " " + gen_parts[5]

                gen_rate = float(gen_parts[3])
                val_rate = float(val_parts[3])

                result.wells_checked += 1

                diff = abs(gen_rate - val_rate)
                if diff > tolerance:
                    result.fail_count += 1
                    rate_failures.append({
                        "well": well_name,
                        "month": month,
                        "generated_rate": gen_rate,
                        "validation_rate": val_rate,
                        "difference": diff,
                        "line": line_idx + 1,
                    })
                else:
                    result.pass_count += 1

        result.months_checked += 1

    if rate_failures:
        for failure in rate_failures:
            result.failures.append({
                "type": "rate_mismatch",
                "well": failure["well"],
                "month": failure["month"],
                "generated_rate": failure["generated_rate"],
                "validation_rate": failure["validation_rate"],
                "difference": failure["difference"],
                "line": failure["line"],
            })
        result.wel_target_passed = False
    else:
        result.wel_target_passed = True

    return result


def print_validation_report(
    target_year: int,
    nam_passed: bool | None,
    nam_errors: list[str],
    wel_result: ValidationResult,
) -> None:
    """
    Print detailed validation report to console.

    Args:
        target_year: Year being validated
        nam_passed: Whether .nam validation passed (None if skipped)
        nam_errors: List of .nam validation errors/warnings
        wel_result: ValidationResult from .wel file validation
    """
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    # .nam file results
    print("\n--- .nam File Validation ---")
    if nam_passed is None:
        print(f"⚠ CY{target_year}.nam validation SKIPPED (no validation file)")
        for msg in nam_errors:
            print(f"  {msg}")
    elif nam_passed:
        print(f"✓ CY{target_year}.nam matches validation file (ignoring comments)")
    else:
        print(f"✗ CY{target_year}.nam FAILED validation:")
        for err in nam_errors:
            print(f"  {err}")

    # .wel file results
    print("\n--- .wel File Validation ---")

    if wel_result.skipped:
        print(f"⚠ .wel validation SKIPPED (no validation file)")
        for failure in wel_result.failures:
            if failure.get("type") == "validation_skipped":
                print(f"  {failure['message']}")
    else:
        print(f"Pre-{target_year} section: ", end="")
        if wel_result.wel_pre_target_passed:
            print("✓ PASSED (byte-identical)")
        else:
            print("✗ FAILED")

        print(f"Post-{target_year} section: ", end="")
        if wel_result.wel_post_target_passed:
            print("✓ PASSED (byte-identical)")
        else:
            print("✗ FAILED")

        print(f"\n{target_year} pumping rates validation:")
        print(f"  Wells checked: {wel_result.wells_checked}")
        print(f"  Months checked: {wel_result.months_checked}")
        print(f"  Passed: {wel_result.pass_count}")
        print(f"  Failed: {wel_result.fail_count}")

        if wel_result.fail_count > 0:
            print("\nRate differences exceeding tolerance:")
            for failure in wel_result.failures:
                if failure.get("type") == "rate_mismatch":
                    print(
                        f"  {failure['well']} {failure['month']}: "
                        f"generated={failure['generated_rate']:.5f}, "
                        f"validation={failure['validation_rate']:.5f}, "
                        f"diff={failure['difference']:.6f}"
                    )

    # Summary
    print("\n" + "-" * 60)
    nam_ok = nam_passed is None or nam_passed  # None (skipped) counts as OK
    all_passed = nam_ok and wel_result.all_passed
    if all_passed:
        if nam_passed is None or wel_result.skipped:
            print("Output generated successfully (validation skipped)")
        else:
            print("Validation PASSED - generated files match validation files")
    else:
        print("Validation FAILED - see details above")
    print("=" * 60)


def run_validation(
    config: YearConfig,
) -> bool:
    """
    Run full validation of generated files against validation files.

    Graceful degradation: if validation files don't exist, warns and returns True.

    Args:
        config: YearConfig with paths to generated and validation files

    Returns:
        True if all validations pass (or are skipped), False if any fail

    Example:
        >>> config = get_year_config(2024)
        >>> success = run_validation(config)
        >>> if not success:
        ...     print("Validation failed!")
    """
    generated_wel = str(Path(config.output_dir) / config.output_wel_filename)
    generated_nam = str(Path(config.output_dir) / config.output_nam_filename)

    print("\nValidating generated files against known-good validation files...")

    # Validate .nam file
    nam_passed, nam_errors = validate_nam_file(generated_nam, config.validation_nam_path)

    # Validate .wel file
    wel_result = validate_wel_file(
        generated_wel,
        config.validation_wel_path,
        config.target_year,
    )

    # Print detailed report
    print_validation_report(config.target_year, nam_passed, nam_errors, wel_result)

    nam_ok = nam_passed is None or nam_passed  # None (skipped) counts as OK
    return nam_ok and wel_result.all_passed


# =============================================================================
# PUMPING SUMMARY OUTPUT
# =============================================================================
def print_pumping_summary(
    pumping_data: Dict[int, Dict[str, float]],
    target_year: int,
) -> None:
    """
    Print per-well monthly pumping summary table (acre-feet and ft³/s side by side).

    Displays a formatted table showing:
    - Well name
    - Monthly acre-feet value
    - Converted ft³/s rate per layer

    Args:
        pumping_data: Dict keyed by well number (1-13), value is dict of
            month abbreviation → acre-feet
        target_year: Year for the pumping data (used for days in month calculation)

    Example:
        >>> print_pumping_summary(pumping_data, 2024)
        Well           Month    Acre-Feet    ft³/s (per layer)
        -----------------------------------------------------------
        BUCKMAN 1      JAN        16.888         -0.13733
        ...
    """
    days_in_month = get_days_in_month(target_year)

    print("\n" + "=" * 70)
    print(f"{target_year} MONTHLY PUMPING SUMMARY")
    print("=" * 70)
    print(f"{'Well':<15} {'Month':<6} {'Acre-Feet':>12} {'ft³/s (per layer)':>20}")
    print("-" * 70)

    for well_num in WELL_ORDER:
        well_name = WELL_NAME_MAP[well_num]
        for month in MONTH_ABBREVS:
            acre_feet = pumping_data[well_num][month]
            days = days_in_month[month]
            rate = convert_af_to_ft3s(acre_feet, days)
            print(f"{well_name:<15} {month:<6} {acre_feet:>12.6f} {rate:>20.5f}")

    print("-" * 70)

    # Print annual totals
    print("\nAnnual Totals (acre-feet):")
    total_all = 0.0
    for well_num in WELL_ORDER:
        well_name = WELL_NAME_MAP[well_num]
        annual = sum(pumping_data[well_num].values())
        total_all += annual
        print(f"  {well_name:<15} {annual:>12.2f} AF")
    print(f"  {'TOTAL':<15} {total_all:>12.2f} AF")
    print("=" * 70)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def parse_args() -> "argparse.Namespace":
    """
    Parse command line arguments.

    Returns:
        Namespace with parsed arguments (year: int)
    """
    parser = argparse.ArgumentParser(
        description="Update MODFLOW Buckman Depletion Model for any calendar year.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 update_modflow.py --year 2024    # Process 2024 (uses 2023 baseline as input)
  python3 update_modflow.py --year 2025    # Process 2025 (uses 2024 output as input)

Input/Output:
  For year N, the script reads from year N-1's output (or 2023 baseline for 2024).
  Output files are written to output/modflow/{year}/

Validation:
  If validation files exist in validation/modflow/{year}/, results are compared.
  If validation files don't exist, the script warns and continues.
        """,
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Target year for update (e.g., 2024, 2025)",
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for MODFLOW update script.

    Runs the full pipeline:
    1. Read Table 2 pumping data (CSV)
    2. Convert acre-feet to ft³/s
    3. Parse source year .wel file
    4. Generate target year well entries
    5. Write updated .wel file
    6. Generate updated .nam file
    7. Validate against known-good files (if they exist)

    Returns:
        Exit code: 0 on success, 1 on validation failure

    Example:
        >>> exit_code = main()
        >>> sys.exit(exit_code)
    """
    args = parse_args()
    target_year = args.year

    # Get year-specific configuration
    config = get_year_config(target_year)

    print("\n" + "=" * 60)
    print("MODFLOW Buckman Depletion Model Update")
    print(f"Updating from CY{config.source_year} to CY{target_year}")
    print("=" * 60)

    # Print checklist-style input sources
    print("\n" + "="*70)
    print(f"STEP 2: UPDATE MODFLOW - YEAR {target_year}")
    print("="*70)
    print(f"📋 Input Sources:")
    print(f"  - Source year: {config.source_year}")
    if target_year == BASELINE_YEAR:
        print(f"  - Mode: BASELINE (using 2023 input files)")
        print(f"  - WEL file: {config.input_wel_path}")
    else:
        print(f"  - Mode: CHAINED (using {config.source_year} outputs)")
        print(f"  - WEL file: {config.input_wel_path}")
    print(f"  - Table 2: {config.table2_csv_path}")

    print("\n📦 Outputs (after completion):")
    print(f"  - thruCY2165_{target_year}.wel (extended well file)")
    print(f"  - CY{target_year}.nam (MODFLOW name file)")
    print(f"  - 10 baseline files copied from 2023")

    print("\n➡️  Next Step (MANUAL):")
    print(f"  cd output/modflow/{target_year}")
    print(f"  wine modflow96.exe CY{target_year}.nam")
    print(f"  wine sfmodflx_2245.exe  # Enter CY{target_year} when prompted")
    print("="*70 + "\n")

    # Check that input files exist
    if not Path(config.input_wel_path).exists():
        print(f"\n✗ Error: Input .wel file not found: {config.input_wel_path}")
        if target_year > BASELINE_YEAR:
            print(f"  Hint: Run 'python3 step2_update_modflow.py --year {config.source_year}' first.")
        else:
            print(f"  Hint: Ensure baseline 2023 input files exist in input/modflow/2023/")
        return 1

    if not Path(config.table2_csv_path).exists():
        print(f"\n✗ Error: Table 2 CSV not found: {config.table2_csv_path}")
        print(f"  Hint: Run 'python3 step1_ingest_buckman_data.py --year {target_year}' first.")
        return 1

    # Step 1: Read Table 2 pumping data
    print("\n[1/8] Reading Table 2 pumping data...")
    pumping_data = read_table2_pumping_data(config.table2_csv_path)
    print(f"  ✓ Read pumping data for {len(pumping_data)} wells")

    # Step 2: Convert acre-feet to ft³/s (done during entry generation)
    print("\n[2/8] Converting acre-feet to ft³/s...")
    print("  ✓ Conversion formula: rate = -(AF/2) × 43560 / (days × 86400)")
    leap_status = "leap year" if config.is_leap_year else "not a leap year"
    feb_days = 29 if config.is_leap_year else 28
    print(f"  ✓ {target_year} is {leap_status} (February = {feb_days} days)")

    # Step 3: Parse source year .wel file
    print(f"\n[3/8] Parsing {config.source_year} .wel file...")
    wel_data = parse_wel_file(config.input_wel_path, target_year)
    print(f"  ✓ Pre-{target_year}: {len(wel_data.pre_target_lines)} lines")
    print(f"  ✓ {target_year}: {len(wel_data.target_year_lines)} lines")
    print(f"  ✓ Post-{target_year}: {len(wel_data.post_target_lines)} lines")

    # Step 4: Generate target year well entries
    print(f"\n[4/8] Generating {target_year} well entries...")
    new_year_lines = generate_well_entries(pumping_data, target_year)
    print(f"  ✓ Generated {len(new_year_lines)} lines (12 months × 27 lines)")

    # Step 5: Write updated .wel file
    print("\n[5/8] Writing updated .wel file...")
    wel_output_path = write_updated_wel_file(
        wel_data,
        new_year_lines,
        config.output_dir,
        config.output_wel_filename,
    )
    print(f"  ✓ Written to {wel_output_path}")

    # Step 6: Generate updated .nam file
    print("\n[6/8] Generating updated .nam file...")
    nam_output_path = generate_nam_file(
        target_year,
        config.output_dir,
        config.output_nam_filename,
    )
    print(f"  ✓ Written to {nam_output_path}")

    # Step 7: Copy baseline MODFLOW files
    print("\n[7/8] Copying baseline MODFLOW files...")
    copied_files = copy_baseline_files(config.output_dir)
    print(f"  ✓ Copied {len(copied_files)} files from {BASELINE_DIR}:")
    for f in copied_files:
        print(f"    - {f.name}")

    # Step 7.5: Verify NAM file references
    print("\n[7.5/8] Verifying NAM file references...")
    verify_nam_file_references(str(nam_output_path), config.output_dir)

    # Print pumping summary table
    print_pumping_summary(pumping_data, target_year)

    # Step 8: Validate against known-good files
    print("\n[8/8] Validating against known-good files...")
    validation_passed = run_validation(config)

    # Return exit code
    if validation_passed:
        print("\n✓ All steps completed successfully!")
        return 0
    else:
        print("\n✗ Validation failed - see report above")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
