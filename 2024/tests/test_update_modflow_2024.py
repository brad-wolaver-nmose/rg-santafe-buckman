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


# =============================================================================
# US-003: Unit Conversion Hand-Check Tests
# =============================================================================


def test_convert_hand_check_well1_jan():
    """
    US-003 hand-check: Well 1 JAN 2024.

    16.887963 AF, 31 days -> per-layer rate ≈ -0.13733 ft³/s
    (PRD says -0.13730 but exact calculation is -0.137328...)
    """
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=16.887963, days_in_month=31, num_layers=2)

    # Manual: (16.887963 / 2) * 43560 / (31 * 86400) = 0.137328...
    expected = -0.13733
    assert abs(result - expected) < 0.00001, (
        f"Well 1 JAN 2024: expected {expected}, got {result}"
    )


def test_convert_hand_check_well6_feb():
    """
    US-003 hand-check: Well 6 FEB 2024 (leap year).

    0.199476 AF, 29 days -> per-layer rate ≈ -0.00173 ft³/s
    """
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=0.199476, days_in_month=29, num_layers=2)

    expected = -0.00173
    assert abs(result - expected) < 0.00001, (
        f"Well 6 FEB 2024: expected {expected}, got {result}"
    )


def test_convert_hand_check_well10_dec():
    """
    US-003 hand-check: Well 10 DEC 2024.

    12.235564 AF, 31 days -> per-layer rate ≈ -0.09950 ft³/s
    """
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=12.235564, days_in_month=31, num_layers=2)

    expected = -0.09950
    assert abs(result - expected) < 0.00001, (
        f"Well 10 DEC 2024: expected {expected}, got {result}"
    )


def test_convert_output_precision():
    """
    Verify conversion output can be formatted to 5 decimal places.

    The conversion function returns a float; formatting is the caller's
    responsibility. This test verifies the values are stable at 5 decimals.
    """
    from update_modflow_2024 import convert_af_to_ft3s

    result = convert_af_to_ft3s(acre_feet=16.887963, days_in_month=31, num_layers=2)
    formatted = f"{result:.5f}"

    assert formatted == "-0.13733", f"Expected '-0.13733', got '{formatted}'"


def test_convert_negative_acre_feet_raises():
    """Verify negative acre-feet raises ValueError."""
    from update_modflow_2024 import convert_af_to_ft3s

    with pytest.raises(ValueError, match="acre_feet must be >= 0"):
        convert_af_to_ft3s(acre_feet=-1.0, days_in_month=31, num_layers=2)


def test_convert_invalid_days_raises():
    """Verify invalid days_in_month raises ValueError."""
    from update_modflow_2024 import convert_af_to_ft3s

    with pytest.raises(ValueError, match="days_in_month must be 1-31"):
        convert_af_to_ft3s(acre_feet=10.0, days_in_month=0, num_layers=2)

    with pytest.raises(ValueError, match="days_in_month must be 1-31"):
        convert_af_to_ft3s(acre_feet=10.0, days_in_month=32, num_layers=2)


# =============================================================================
# US-004: Parse the 2023 .wel File Structure
# =============================================================================


def test_parse_wel_file_function_exists():
    """Verify parse_wel_file function exists and is callable."""
    from update_modflow_2024 import parse_wel_file

    assert callable(parse_wel_file)


def test_parse_wel_file_returns_welfiledata():
    """Verify parse_wel_file returns WelFileData object with all sections."""
    from update_modflow_2024 import parse_wel_file, WelFileData

    result = parse_wel_file()

    assert isinstance(result, WelFileData)
    assert hasattr(result, "pre_2024_lines")
    assert hasattr(result, "year_2024_lines")
    assert hasattr(result, "post_2024_lines")


def test_parse_wel_file_2024_section_size():
    """
    Verify 2024 section contains exactly 324 lines.

    12 months × 27 lines/month (1 header + 26 well entries)
    """
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    expected_lines = 12 * 27  # 324
    assert len(result.year_2024_lines) == expected_lines, (
        f"2024 section should have {expected_lines} lines, "
        f"got {len(result.year_2024_lines)}"
    )


def test_parse_wel_file_preserves_total_lines():
    """
    Verify total lines matches the original file (54,805 lines).

    pre_2024 + 2024 + post_2024 = 54,805
    """
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    expected_total = 54805
    assert result.total_lines == expected_total, (
        f"Total lines should be {expected_total}, got {result.total_lines}"
    )


def test_parse_wel_file_pre_2024_ends_before_jan_2024():
    """Verify pre-2024 lines end with DEC 2023 data."""
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    # Last line of pre-2024 should be BUCKMAN 13 DEC 2023 layer 2
    last_pre_2024 = result.pre_2024_lines[-1].strip()
    assert "BUCKMAN 13" in last_pre_2024 and "DEC 2023" in last_pre_2024, (
        f"Last pre-2024 line should be BUCKMAN 13 DEC 2023, got: {last_pre_2024}"
    )


def test_parse_wel_file_2024_section_starts_with_header():
    """Verify 2024 section starts with header line '26'."""
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    first_2024_line = result.year_2024_lines[0].strip()
    assert first_2024_line == "26", (
        f"2024 section should start with header '26', got: {first_2024_line}"
    )


def test_parse_wel_file_2024_first_entry_is_buckman1_jan():
    """Verify first well entry in 2024 is BUCKMAN 1 JAN 2024."""
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    # Line index 1 (after header) should be BUCKMAN 1 JAN 2024
    first_entry = result.year_2024_lines[1].strip()
    assert "BUCKMAN 1" in first_entry and "JAN 2024" in first_entry, (
        f"First 2024 entry should be BUCKMAN 1 JAN 2024, got: {first_entry}"
    )


def test_parse_wel_file_2024_last_entry_is_buckman13_dec():
    """Verify last well entry in 2024 is BUCKMAN 13 DEC 2024."""
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    last_entry = result.year_2024_lines[-1].strip()
    assert "BUCKMAN 13" in last_entry and "DEC 2024" in last_entry, (
        f"Last 2024 entry should be BUCKMAN 13 DEC 2024, got: {last_entry}"
    )


def test_parse_wel_file_post_2024_starts_with_jan_2025():
    """Verify post-2024 section starts with JAN 2025 header."""
    from update_modflow_2024 import parse_wel_file

    result = parse_wel_file()

    # First line should be header "26" for JAN 2025
    first_post_2024 = result.post_2024_lines[0].strip()
    assert first_post_2024 == "26", (
        f"Post-2024 should start with header '26', got: {first_post_2024}"
    )

    # Second line should be BUCKMAN 1 JAN 2025
    second_post_2024 = result.post_2024_lines[1].strip()
    assert "BUCKMAN 1" in second_post_2024 and "JAN 2025" in second_post_2024, (
        f"First post-2024 entry should be BUCKMAN 1 JAN 2025, got: {second_post_2024}"
    )
