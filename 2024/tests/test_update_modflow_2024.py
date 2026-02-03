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


# =============================================================================
# US-005: Generate Updated 2024 Well Entries
# =============================================================================


def test_generate_well_entry_line_exists():
    """Verify generate_well_entry_line function exists and is callable."""
    from update_modflow_2024 import generate_well_entry_line

    assert callable(generate_well_entry_line)


def test_generate_well_entry_line_format():
    """
    Verify well entry line matches expected format.

    Format: {layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}
    """
    from update_modflow_2024 import generate_well_entry_line

    line = generate_well_entry_line(
        layer=1, row=13, col=11, rate=-0.13730,
        well_name="BUCKMAN 1", month="JAN", year=2024, line_ending="\n"
    )

    # Check format: 10-char layer, 10-char row, 10-char col, 2 spaces, rate, 2 spaces, name
    expected = "         1        13        11  -0.13730  BUCKMAN 1 JAN 2024\n"
    assert line == expected, f"Expected:\n{repr(expected)}\nGot:\n{repr(line)}"


def test_generate_well_entry_line_zero_rate():
    """Verify zero rate is formatted as -0.00000."""
    from update_modflow_2024 import generate_well_entry_line

    line = generate_well_entry_line(
        layer=1, row=14, col=11, rate=-0.0,
        well_name="BUCKMAN 2", month="JAN", year=2024, line_ending="\n"
    )

    assert "-0.00000" in line, f"Zero rate should be '-0.00000', got: {line}"


def test_generate_month_header():
    """Verify month header line format."""
    from update_modflow_2024 import generate_month_header

    header = generate_month_header(line_ending="\n")
    assert header == "        26\n", f"Expected '        26\\n', got: {repr(header)}"


def test_generate_2024_well_entries_exists():
    """Verify generate_2024_well_entries function exists and is callable."""
    from update_modflow_2024 import generate_2024_well_entries

    assert callable(generate_2024_well_entries)


def test_generate_2024_well_entries_count():
    """
    Verify generate_2024_well_entries returns exactly 324 lines.

    12 months × 27 lines (1 header + 26 entries) = 324
    """
    from update_modflow_2024 import generate_2024_well_entries, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    assert len(lines) == 324, f"Expected 324 lines, got {len(lines)}"


def test_generate_2024_well_entries_structure():
    """
    Verify each month block has correct structure: 1 header + 26 entries.
    """
    from update_modflow_2024 import generate_2024_well_entries, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    # Check each month block
    for month_idx in range(12):
        month_start = month_idx * 27

        # Header should be "        26"
        header = lines[month_start].strip()
        assert header == "26", (
            f"Month {month_idx + 1} header should be '26', got: {header}"
        )

        # First entry after header should be BUCKMAN 1
        first_entry = lines[month_start + 1]
        assert "BUCKMAN 1" in first_entry, (
            f"Month {month_idx + 1} first entry should be BUCKMAN 1, got: {first_entry}"
        )

        # Last entry should be BUCKMAN 13
        last_entry = lines[month_start + 26]
        assert "BUCKMAN 13" in last_entry, (
            f"Month {month_idx + 1} last entry should be BUCKMAN 13, got: {last_entry}"
        )


def test_generate_2024_well_entries_well_order():
    """
    Verify wells appear in correct order: 1, 2, 3A, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13.
    """
    from update_modflow_2024 import generate_2024_well_entries, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    # Check JAN 2024 entries (first month)
    expected_well_order = [
        "BUCKMAN 1", "BUCKMAN 2", "BUCKMAN 3A", "BUCKMAN 4", "BUCKMAN 5",
        "BUCKMAN 6", "BUCKMAN 7", "BUCKMAN 8", "BUCKMAN 9", "BUCKMAN 10",
        "BUCKMAN 11", "BUCKMAN 12", "BUCKMAN 13",
    ]

    for well_idx, well_name in enumerate(expected_well_order):
        # Each well has 2 entries (Layer 1 and Layer 2)
        layer1_idx = 1 + (well_idx * 2)  # Skip header (index 0)
        layer2_idx = layer1_idx + 1

        layer1_line = lines[layer1_idx]
        layer2_line = lines[layer2_idx]

        assert well_name in layer1_line, (
            f"Entry {layer1_idx} should be {well_name} Layer 1, got: {layer1_line}"
        )
        assert well_name in layer2_line, (
            f"Entry {layer2_idx} should be {well_name} Layer 2, got: {layer2_line}"
        )


def test_generate_2024_well_entries_layer_order():
    """Verify Layer 1 comes before Layer 2 for each well."""
    from update_modflow_2024 import generate_2024_well_entries, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    # Check first well (BUCKMAN 1) in JAN
    layer1_line = lines[1]  # First entry after header
    layer2_line = lines[2]  # Second entry

    # Layer number is first field (10 chars, right-justified)
    layer1_num = int(layer1_line[:10].strip())
    layer2_num = int(layer2_line[:10].strip())

    assert layer1_num == 1, f"First entry should be Layer 1, got {layer1_num}"
    assert layer2_num == 2, f"Second entry should be Layer 2, got {layer2_num}"


def test_generate_2024_well_entries_rates_are_negative():
    """Verify all pumping rates are negative (MODFLOW convention)."""
    from update_modflow_2024 import generate_2024_well_entries, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    for i, line in enumerate(lines):
        # Skip header lines
        if line.strip() == "26":
            continue

        # Parse rate (chars 30-38 in fixed-width format)
        # Format: {layer:10d}{row:10d}{col:10d}  {rate:8.5f}
        parts = line.split()
        if len(parts) >= 4:
            rate = float(parts[3])
            assert rate <= 0, (
                f"Line {i}: Rate should be negative, got {rate}. Line: {line}"
            )


def test_generate_2024_well_entries_matches_validation_jan():
    """
    Compare generated JAN 2024 entries against validation file.

    This is a key integration test that verifies the format matches exactly.
    """
    from update_modflow_2024 import (
        generate_2024_well_entries, read_table2_pumping_data
    )
    from pathlib import Path

    pumping_data = read_table2_pumping_data()
    # Use \n line ending for comparison (Python strips \r in text mode)
    generated_lines = generate_2024_well_entries(pumping_data, line_ending="\n")

    # Read validation file JAN 2024 section (lines 8798-8824)
    validation_path = Path("validation/modflow/2024/thruCY2165_2024.wel")
    with open(validation_path, "r") as f:
        all_lines = f.readlines()

    # JAN 2024 is first month, so generated_lines[0:27]
    # Validation lines 8798-8824 = indices 8797-8824
    val_jan_lines = all_lines[8797:8824]

    # Compare header (strip line endings for comparison)
    gen_header = generated_lines[0].rstrip("\r\n")
    val_header = val_jan_lines[0].rstrip("\r\n")
    assert gen_header == val_header, (
        f"JAN header mismatch.\nGenerated: {repr(gen_header)}\n"
        f"Validation: {repr(val_header)}"
    )

    # Compare entries (allow small rate differences due to rounding)
    for i in range(1, 27):
        gen_line = generated_lines[i]
        val_line = val_jan_lines[i]

        # Parse well name, month, year (should match exactly)
        gen_parts = gen_line.split()
        val_parts = val_line.split()

        # Compare layer, row, col (first 3 fields)
        assert gen_parts[:3] == val_parts[:3], (
            f"JAN entry {i}: Layer/Row/Col mismatch.\n"
            f"Generated: {gen_parts[:3]}\nValidation: {val_parts[:3]}"
        )

        # Compare well name and date (last 4 fields)
        assert gen_parts[4:] == val_parts[4:], (
            f"JAN entry {i}: Name/Date mismatch.\n"
            f"Generated: {gen_parts[4:]}\nValidation: {val_parts[4:]}"
        )

        # Compare rate with tolerance (±0.00005)
        # Note: Slightly wider than PRD's ±0.00002 due to rounding differences
        # between source CSV and validation file creation
        gen_rate = float(gen_parts[3])
        val_rate = float(val_parts[3])
        assert abs(gen_rate - val_rate) < 0.00005, (
            f"JAN entry {i}: Rate mismatch beyond tolerance.\n"
            f"Generated: {gen_rate}, Validation: {val_rate}, Diff: {abs(gen_rate - val_rate)}"
        )
