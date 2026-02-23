"""
Centralized constants for the Buckman Wellfield Pipeline.

All shared constants, conversion factors, well mappings, and cell definitions
are defined here as the single source of truth. Individual pipeline scripts
import from this module rather than defining constants locally.

Scientific Basis:
- USGS conversion: 1 acre-foot = 325,851 gallons; 1 MG = 3.06889 AF
- MODFLOW96 unit system: ft³/s for pumping rates
- Core (2003) analytical residuals: pre-1988 pumping effects
- Cell-to-stream mapping: hardcoded in FORTRAN post-processor

References:
- Core, A.A. (2003). Santa Fe River Water Budget Model Technical Report.
- USGS NAWQA Glossary (https://water.usgs.gov/nawqa/glos.html)
- docs/MODFLOW_CELL_MAPPING.md - Complete cell identification documentation
"""

import calendar
from pathlib import Path

# =============================================================================
# UNIT CONVERSION FACTORS
# =============================================================================

# USGS conversion factor: 1 million gallons = 3.06889 acre-feet
# Derivation: 1,000,000 gal / 325,851 gal/AF = 3.06889 AF/MG
MG_TO_AF_FACTOR: float = 3.06889

# 1 acre-foot = 43,560 cubic feet
ACRE_FT_TO_FT3: int = 43560

# Seconds in one day
SECONDS_PER_DAY: int = 86400


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Number of MODFLOW layers (pumping split equally between layers)
NUM_LAYERS: int = 2

# Baseline year: the first year that uses original 2023 input files
BASELINE_YEAR: int = 2024

# Default processing year
DEFAULT_YEAR: int = 2024


# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Path pattern for source CSV file — replace {year} with actual year at runtime
# CSV files are organized in year-specific subdirectories
INPUT_CSV_PATH: str = "./input/csv/{year}/Buckman_Well_Prod_{year}.csv"

# Output directory for ingested data (Table 1, Table 2, monthly CSVs)
INGESTED_DATA_DIR: str = "./output/ingested_data"

# Output directory for depletion tables (Tables 3, 4, 5)
DEPLETION_OUTPUT_DIR: str = "./output/depletion/"

# Validation data directory (contains reference Excel files for verification)
VALIDATION_DIR: str = "./validation"

# Directory containing original 2023 MODFLOW files (static, unchanged)
BASELINE_DIR: str = "input/modflow/2023"


# =============================================================================
# TOLERANCE THRESHOLDS
# =============================================================================

# Three-tier tolerance thresholds for daily BWP verification (MGD)
# Tier 1: Absolute noise floor — below instrument precision (database artifacts)
# Set to 0.0015 MGD to catch 100-gallon rounding artifacts (900-1,500 gal range)
NOISE_THRESHOLD_MGD: float = 0.0015

# Tier 2: Informational threshold — expected Excel rounding differences
DAILY_SUM_TOLERANCE_INFO_MGD: float = 0.001  # 1,000 gal/day tolerance

# Tier 3: Error threshold — significant mismatches requiring CSV review
DAILY_SUM_TOLERANCE_ERROR_MGD: float = 0.005  # 5,000 gal/day threshold

# Tolerance for annual Sum row verification (MG)
ANNUAL_SUM_TOLERANCE_MG: float = 0.01  # 10,000 gallons

# Tolerance for WEL file rate validation (ft³/s)
RATE_TOLERANCE: float = 0.0001


# =============================================================================
# TEMPORAL CONSTANTS
# =============================================================================

# Month abbreviations in calendar order (used for output filenames and tables)
MONTHS_ABBREV: tuple[str, ...] = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)

# Month tuples for iteration: (numeric string, abbreviation)
MONTHS_ORDERED: tuple[tuple[str, str], ...] = (
    ("01", "JAN"), ("02", "FEB"), ("03", "MAR"), ("04", "APR"),
    ("05", "MAY"), ("06", "JUN"), ("07", "JUL"), ("08", "AUG"),
    ("09", "SEP"), ("10", "OCT"), ("11", "NOV"), ("12", "DEC"),
)


def get_days_in_year(year: int) -> list[int]:
    """
    Return days per month for given year, handling leap years.

    Uses Python calendar module for correctness.

    Args:
        year: Calendar year (e.g., 2024, 2025)

    Returns:
        List of 12 integers, days in each month [Jan..Dec]

    Example:
        >>> get_days_in_year(2024)  # Leap year
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        >>> get_days_in_year(2025)  # Non-leap year
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    """
    return [
        31,
        29 if calendar.isleap(year) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    ]


# Days per month for 2024 (leap year) — kept for backward compatibility
DAYS_2024: list[int] = get_days_in_year(2024)

# Days per month from validation files (non-leap year pattern)
# Note: Validation files use 28 for February regardless of year
DAYS_VALIDATION: list[int] = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# =============================================================================
# WELL MAPPINGS
# =============================================================================

# Well-to-OSE permit number mapping: well number (1-13) -> OSE permit number
# Well 3 is labeled "3/3A" in historical reports (combined wells 3 and 3A)
WELL_OSE_MAP: dict[int, str] = {
    1: "RG-20516-S-5",
    2: "RG-20516-S-6",
    3: "RG-20516-S",      # Labeled as "3/3A" in reports
    4: "RG-20516-S-2",
    5: "RG-20516-S-3",
    6: "RG-20516-S-4",
    7: "RG-20516-S-7",
    8: "RG-20516-S-8",
    9: "RG-20516-S-9",
    10: "RG-20516-S-10",
    11: "RG-20516-S-11",
    12: "RG-20516-S-12",
    13: "RG-20516-S-13",
}

# Well number (1-13) -> MODFLOW well name
WELL_NAME_MAP: dict[int, str] = {
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

# MODFLOW well name -> (row, col) in model grid
WELL_GRID_MAP: dict[str, tuple[int, int]] = {
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

# CSV column headers for wells 1-13 (as they appear in the source CSV)
CSV_WELL_COLUMNS: list[str] = [
    "BWell 1|Flow Mgd", "BWell 2|Flow Mgd", "BWell 3|Flow Mgd",
    "BWell 4|Flow Mgd", "BWell 5|Flow Mgd", "BWell 6|Flow Mgd",
    "BWell 7|Flow Mgd", "BWell 8|Flow Mgd", "BWell 9|Flow Mgd",
    "BWell 10|Flow Mgd", "BWell 11|Flow Mgd", "BWell 12|Flow Mgd",
    "BWell 13|Flow Mgd",
]

# Header name for the total/formula column in the source CSV
CSV_TOTAL_COLUMN: str = "BWP|Flow Mgd|MGD|Formula"


# =============================================================================
# MODFLOW BASELINE FILES
# =============================================================================

# Files to copy from baseline to output directory (required by MODFLOW96)
BASELINE_FILES_TO_COPY: list[str] = [
    "modflow96.exe",           # MODFLOW96 executable
    "sflcs.bcf",               # Block-Centered Flow package
    "sflcs.sip",               # Strongly Implicit Procedure solver
    "thruCY2165.bas",          # Basic package
    "thruCY2165.ghb",          # General Head Boundary package
    "thruCY2165.oc",           # Output Control
    "thruCY2165.riv",          # River package
    "sfmodflx_2245.exe",       # Stream flux post-processor
    "verify_modflow_run.py",   # MODFLOW output verification script
    "verify_depletion.py",     # Depletion output verification script
]

# WEL file structure: 1 header line + 26 well entries per month
LINES_PER_MONTH: int = 27       # 1 header + 26 well entries (13 wells x 2 layers)
WELLS_PER_MONTH: int = 26       # 13 wells x 2 layers


# =============================================================================
# CELL MAPPINGS (Otowi Gage classification)
# =============================================================================

# Above Otowi: Rio Grande cells upstream of Otowi Bridge gage
# 10 cells in Layer 1, rows 1-10
ABOVE_OTOWI_CELLS: list[tuple[int, int, int]] = [
    (1, 1, 16), (1, 2, 16), (1, 3, 16), (1, 4, 16), (1, 5, 15),
    (1, 6, 14), (1, 7, 14), (1, 8, 13), (1, 9, 13), (1, 10, 12)
]

# Below Otowi: Rio Grande cells downstream of Otowi Bridge gage
# 16 cells in Layer 1, rows 11-23
BELOW_OTOWI_CELLS: list[tuple[int, int, int]] = [
    (1, 11, 11), (1, 12, 11), (1, 13, 11), (1, 14, 10), (1, 15, 9),
    (1, 15, 10), (1, 16, 9), (1, 17, 8), (1, 18, 6), (1, 18, 7),
    (1, 19, 6), (1, 20, 5), (1, 21, 4), (1, 21, 5), (1, 22, 4), (1, 23, 3)
]

# Cell containing Buckman wells 1, 7, 8 (shared grid cell)
BUCKMAN_WELLS_CELL: tuple[int, int, int] = (1, 13, 11)


# =============================================================================
# CORE (2003) ANALYTICAL MODEL RESIDUALS
# =============================================================================

# Rio Pojoaque-Nambe: decreasing residuals from 1972-1987 pumping
# Values from Core (2003) PROJECTION.XLS, ends ~2015
# After 2015: 0 (residual effect exhausted)
CORE_2003_POJOAQUE: dict[int, float] = {
    1988: 40.432, 1989: 39.244, 1990: 37.971, 1991: 36.557, 1992: 34.928,
    1993: 33.112, 1994: 31.185, 1995: 29.226, 1996: 27.296, 1997: 25.439,
    1998: 23.678, 1999: 22.028, 2000: 20.491, 2001: 19.068, 2002: 17.753,
    2003: 16.543, 2004: 15.429, 2005: 14.404, 2006: 13.462, 2007: 12.595,
    2008: 11.797, 2009: 11.061, 2010: 10.383, 2011: 6.151, 2012: 4.693,
    2013: 3.234, 2014: 1.775, 2015: 0.316,
    # 2016+: 0 (residual effect exhausted)
}

# Rio Tesuque: longer-lasting residuals from 1972-1987 pumping
# Values from Core (1996), covers 1988-2050
# After 2050: 0.0 (residual effect exhausted)
CORE_2003_TESUQUE: dict[int, float] = {
    1988: 21.015, 1989: 22.333, 1990: 23.391, 1991: 24.227, 1992: 24.868,
    1993: 25.327, 1994: 25.615, 1995: 25.747, 1996: 25.737, 1997: 25.608,
    1998: 25.378, 1999: 25.067, 2000: 24.691, 2001: 24.265, 2002: 23.800,
    2003: 23.308, 2004: 22.797, 2005: 22.273, 2006: 21.743, 2007: 21.212,
    2008: 20.683, 2009: 20.157, 2010: 19.639, 2011: 19.258, 2012: 18.767,
    2013: 18.276, 2014: 17.785, 2015: 17.295, 2016: 16.804, 2017: 16.313,
    2018: 15.822, 2019: 15.331, 2020: 14.841, 2021: 14.350, 2022: 13.859,
    2023: 13.368, 2024: 12.877, 2025: 12.387, 2026: 11.896, 2027: 11.405,
    2028: 10.914, 2029: 10.424, 2030: 9.933, 2031: 9.442, 2032: 8.951,
    2033: 8.460, 2034: 7.970, 2035: 7.479, 2036: 6.988, 2037: 6.497,
    2038: 6.006, 2039: 5.516, 2040: 5.025, 2041: 4.534, 2042: 4.043,
    2043: 3.552, 2044: 3.062, 2045: 2.571, 2046: 2.080, 2047: 1.589,
    2048: 1.098, 2049: 0.608, 2050: 0.117,
    # 2051+: 0.0 (residual effect exhausted)
}


# =============================================================================
# LA CIENEGA SPRINGS HISTORICAL CUMULATIVE DATA
# =============================================================================

# Cumulative depletion totals from Table 5 validation image
# Values are cumulative acre-feet starting from 2004
LA_CIENEGA_CUMULATIVE: dict[int, float] = {
    2004: 0.45, 2005: 0.66, 2006: 0.83, 2007: 0.99, 2008: 1.16,
    2009: 1.32, 2010: 1.49, 2011: 1.65, 2012: 1.82, 2013: 1.97,
    2014: 2.13, 2015: 2.29, 2016: 2.45, 2017: 2.60, 2018: 2.75,
    2019: 2.90, 2020: 3.06, 2021: 3.21, 2022: 3.37, 2023: 3.54,
    2024: 3.74, 2025: 3.92, 2026: 4.10, 2027: 4.27, 2028: 4.46,
    2029: 4.62, 2030: 4.80,
}


# =============================================================================
# HISTORICAL BASELINE PATHS
# =============================================================================

# Default path to historical baseline file for Table 3 chaining
HISTORICAL_TABLE3_PATH: Path = Path(
    "validation/2024/expected_outputs/Table_3_expected.xlsx"
)
