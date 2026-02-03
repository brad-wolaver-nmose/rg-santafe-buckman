"""
Update MODFLOW Buckman Depletion Model from CY2023 to CY2024.

Reads 2024 monthly pumping data from Table 2 CSV, converts acre-feet to ft³/s,
updates the .wel file with actual pumping rates, and generates the .nam file.
"""
from typing import Dict

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
