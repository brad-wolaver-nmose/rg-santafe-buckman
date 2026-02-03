"""
Update MODFLOW Buckman Depletion Model from CY2023 to CY2024.

Reads 2024 monthly pumping data from Table 2 CSV, converts acre-feet to ft³/s,
updates the .wel file with actual pumping rates, and generates the .nam file.
"""
from pathlib import Path
from typing import Dict

import pandas as pd

# =============================================================================
# FILE PATHS
# =============================================================================
INPUT_WEL_PATH: str = "input/modflow/2023/thruCY2165.wel"
INPUT_NAM_PATH: str = "input/modflow/2023/CY2023.nam"
TABLE2_CSV_PATH: str = "output/ingested_data/2024_Table_2_output.csv"
VALIDATION_WEL_PATH: str = "validation/modflow/2024/thruCY2165_2024.wel"
VALIDATION_NAM_PATH: str = "validation/modflow/2024/CY2024.nam"
OUTPUT_DIR: str = "output/modflow/2024"
OUTPUT_WEL_FILENAME: str = "thruCY2165_2024.wel"
OUTPUT_NAM_FILENAME: str = "CY2024.nam"

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
# TEMPORAL CONSTANTS
# =============================================================================
MONTH_ABBREVS: list[str] = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
TARGET_YEAR: int = 2024


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
# Line numbers are 1-indexed to match file content
WEL_2024_START_LINE: int = 8798  # Header line "26" before JAN 2024
WEL_2024_END_LINE: int = 9121    # Last BUCKMAN 13 DEC 2024 entry
LINES_PER_MONTH: int = 27       # 1 header + 26 well entries (13 wells × 2 layers)
WELLS_PER_MONTH: int = 26       # 13 wells × 2 layers


class WelFileData:
    """Parsed .wel file data with separated pre-2024, 2024, and post-2024 sections."""

    def __init__(
        self,
        pre_2024_lines: list[str],
        year_2024_lines: list[str],
        post_2024_lines: list[str],
    ) -> None:
        self.pre_2024_lines = pre_2024_lines
        self.year_2024_lines = year_2024_lines
        self.post_2024_lines = post_2024_lines

    @property
    def total_lines(self) -> int:
        """Total line count across all sections."""
        return (
            len(self.pre_2024_lines)
            + len(self.year_2024_lines)
            + len(self.post_2024_lines)
        )


def parse_wel_file(wel_path: str = INPUT_WEL_PATH) -> WelFileData:
    """
    Parse the .wel file and separate 2024 data from historical and future data.

    Scientific basis: MODFLOW .wel file format with stress period structure.
    Each month's stress period has a header line (entry count) followed by
    well entries (layer, row, col, rate, name).

    Assumptions:
        1. 2024 data starts at line 8798 (header for JAN 2024)
        2. 2024 data ends at line 9121 (BUCKMAN 13 DEC 2024 layer 2)
        3. Each month has 27 lines: 1 header + 26 well entries
        4. 12 months × 27 lines = 324 lines total for 2024

    Args:
        wel_path: Path to the input .wel file

    Returns:
        WelFileData object with pre_2024_lines, year_2024_lines, post_2024_lines

    Raises:
        FileNotFoundError: If .wel file does not exist
        ValueError: If 2024 section structure doesn't match expectations

    Example:
        >>> data = parse_wel_file()
        >>> len(data.year_2024_lines)
        324
    """
    from pathlib import Path

    path = Path(wel_path)
    if not path.exists():
        raise FileNotFoundError(f".wel file not found: {wel_path}")

    with open(wel_path, "r") as f:
        all_lines = f.readlines()

    total_lines = len(all_lines)
    print(f"Read {total_lines} lines from {wel_path}")

    # Convert to 0-indexed for list slicing
    start_idx = WEL_2024_START_LINE - 1  # 8797 (line 8798 is index 8797)
    end_idx = WEL_2024_END_LINE          # 9121 (line 9121 is index 9120, +1 for slice)

    # Split into three sections
    pre_2024_lines = all_lines[:start_idx]
    year_2024_lines = all_lines[start_idx:end_idx]
    post_2024_lines = all_lines[end_idx:]

    # Validate 2024 section structure
    expected_2024_lines = 12 * LINES_PER_MONTH  # 324 lines
    actual_2024_lines = len(year_2024_lines)
    if actual_2024_lines != expected_2024_lines:
        raise ValueError(
            f"2024 section should have {expected_2024_lines} lines, "
            f"found {actual_2024_lines}. "
            f"Check WEL_2024_START_LINE ({WEL_2024_START_LINE}) and "
            f"WEL_2024_END_LINE ({WEL_2024_END_LINE})."
        )

    # Validate each month has correct structure (header + 26 entries)
    for month_idx in range(12):
        month_start = month_idx * LINES_PER_MONTH
        header_line = year_2024_lines[month_start].strip()

        # Header should be "26" (number of well entries)
        if header_line != "26":
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} 2024 header should be '26', found '{header_line}' "
                f"at 2024-section line {month_start + 1}"
            )

        # First entry should be BUCKMAN 1
        first_entry = year_2024_lines[month_start + 1]
        if "BUCKMAN 1" not in first_entry:
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} 2024 first entry should be BUCKMAN 1, "
                f"found: {first_entry.strip()}"
            )

        # Last entry should be BUCKMAN 13
        last_entry = year_2024_lines[month_start + WELLS_PER_MONTH]
        if "BUCKMAN 13" not in last_entry:
            month_name = MONTH_ABBREVS[month_idx]
            raise ValueError(
                f"{month_name} 2024 last entry should be BUCKMAN 13, "
                f"found: {last_entry.strip()}"
            )

    print(
        f"Parsed .wel file: {len(pre_2024_lines)} pre-2024, "
        f"{len(year_2024_lines)} 2024, {len(post_2024_lines)} post-2024 lines"
    )

    return WelFileData(
        pre_2024_lines=pre_2024_lines,
        year_2024_lines=year_2024_lines,
        post_2024_lines=post_2024_lines,
    )


def read_table2_pumping_data(
    csv_path: str = TABLE2_CSV_PATH,
) -> Dict[int, Dict[str, float]]:
    """
    Read 2024 monthly pumping data from Table 2 CSV.

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
