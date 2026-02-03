"""
Smoke tests for update_modflow_2024 module.
Verifies code RUNS - domain expert must verify MODFLOW results independently.

These tests support the Ralph iterate-until-pass loop.
They catch mechanical failures, not hydrological errors.
"""
import calendar
import pytest


def test_module_imports():
    """Verify module imports without syntax errors."""
    import update_modflow_2024


def test_convert_function_exists():
    """Verify the acre-feet to ft3/s conversion function exists and is callable."""
    from update_modflow_2024 import convert_af_to_ft3s

    assert callable(convert_af_to_ft3s)


def test_convert_af_to_ft3s_known_answer():
    """
    Verify conversion against hand-calculated value.

    Well 1 JAN 2024: 16.887963 acre-feet, 31 days in January.
    Per-layer rate = (16.887963 / 2) * 43560 / (31 * 86400) = ~0.13730 ft3/s
    Returned as negative (MODFLOW pumping convention).

    Tolerance is wide (0.001) because this is a smoke test, not a precision test.
    """
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=16.887963, days_in_month=31, num_layers=2)

    assert result is not None
    assert isinstance(result, float)
    # Negative (pumping convention) and approximately correct magnitude
    assert result < 0, f"Expected negative pumping rate, got {result}"
    assert -0.15 < result < -0.12, (
        f"Well 1 JAN 2024 rate {result} outside expected range [-0.15, -0.12]"
    )


def test_convert_zero_pumping():
    """Verify zero acre-feet produces zero (or near-zero) rate."""
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=0.0, days_in_month=31, num_layers=2)
    assert abs(result) < 1e-10, f"Expected zero rate for zero pumping, got {result}"


def test_leap_year_february():
    """
    Verify February 2024 uses 29 days (leap year).

    Well 6 FEB 2024: 0.199476 acre-feet, 29 days.
    Per-layer rate ≈ -0.00173 ft3/s.
    """
    from update_modflow_2024 import convert_af_to_ft3s

    days_feb_2024 = calendar.monthrange(2024, 2)[1]
    assert days_feb_2024 == 29, f"2024 is a leap year, February should have 29 days"

    result = convert_af_to_ft3s(
        acre_feet=0.199476, days_in_month=days_feb_2024, num_layers=2
    )
    assert -0.005 < result < -0.001, (
        f"Well 6 FEB 2024 rate {result} outside expected range"
    )


def test_well_name_mapping_exists():
    """Verify the well name mapping constant is defined and has 13 entries."""
    from update_modflow_2024 import WELL_NAME_MAP

    assert isinstance(WELL_NAME_MAP, dict)
    assert len(WELL_NAME_MAP) == 13, (
        f"Expected 13 wells in mapping, got {len(WELL_NAME_MAP)}"
    )
    # Well 3 maps to BUCKMAN 3A (the notable exception)
    assert "3A" in str(WELL_NAME_MAP.get(3, "")), (
        "Well 3 should map to BUCKMAN 3A"
    )


def test_read_table2_function_exists():
    """Verify the read_table2_pumping_data function exists and is callable."""
    from update_modflow_2024 import read_table2_pumping_data

    assert callable(read_table2_pumping_data)


def test_read_table2_pumping_data():
    """
    Verify CSV parsing returns dict with 13 wells and 12 months each.
    Uses actual Table 2 CSV file.
    """
    from update_modflow_2024 import read_table2_pumping_data

    result = read_table2_pumping_data()

    # Check structure: 13 wells
    assert isinstance(result, dict)
    assert len(result) == 13, f"Expected 13 wells, got {len(result)}"

    # Check all wells 1-13 present
    for well_num in range(1, 14):
        assert well_num in result, f"Well {well_num} missing from result"
        assert len(result[well_num]) == 12, (
            f"Well {well_num} should have 12 months, got {len(result[well_num])}"
        )

    # Check known values from CSV
    assert abs(result[1]["JAN"] - 16.887963) < 0.0001, (
        f"Well 1 JAN should be 16.887963, got {result[1]['JAN']}"
    )
    assert abs(result[6]["FEB"] - 0.199476) < 0.0001, (
        f"Well 6 FEB should be 0.199476, got {result[6]['FEB']}"
    )
    # Well 5 has all zeros
    assert result[5]["JAN"] == 0.0, f"Well 5 JAN should be 0.0, got {result[5]['JAN']}"


def test_read_table2_no_negative_values():
    """Verify all pumping values are non-negative."""
    from update_modflow_2024 import read_table2_pumping_data

    result = read_table2_pumping_data()

    for well_num, monthly_data in result.items():
        for month, value in monthly_data.items():
            assert value >= 0, (
                f"Well {well_num} {month} has negative value: {value}"
            )
