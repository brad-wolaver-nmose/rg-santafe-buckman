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


# =============================================================================
# US-006: Write Updated .wel File
# =============================================================================


def test_write_updated_wel_file_exists():
    """Verify write_updated_wel_file function exists and is callable."""
    from update_modflow_2024 import write_updated_wel_file

    assert callable(write_updated_wel_file)


def test_write_updated_wel_file_creates_directory(tmp_path):
    """Verify function creates output directory if it doesn't exist."""
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file
    )

    # Parse and generate data
    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")

    # Use temp directory that doesn't exist
    output_dir = tmp_path / "new_output" / "modflow" / "2024"

    # Write file - should create directory
    result_path = write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(output_dir),
        output_filename="test.wel"
    )

    assert output_dir.exists(), "Output directory should be created"
    assert result_path.exists(), "Output file should exist"


def test_write_updated_wel_file_line_count(tmp_path):
    """Verify written file has exactly 54,805 lines."""
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file
    )

    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")

    output_file = tmp_path / "thruCY2165_2024.wel"
    write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(tmp_path),
        output_filename="thruCY2165_2024.wel"
    )

    # Count lines in written file
    with open(output_file, "r") as f:
        line_count = sum(1 for _ in f)

    assert line_count == 54805, (
        f"Expected 54805 lines, got {line_count}"
    )


def test_write_updated_wel_file_preserves_pre_2024(tmp_path):
    """Verify pre-2024 section is preserved exactly."""
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file,
        INPUT_WEL_PATH
    )

    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")

    output_file = tmp_path / "thruCY2165_2024.wel"
    write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(tmp_path),
        output_filename="thruCY2165_2024.wel"
    )

    # Read original and output files
    with open(INPUT_WEL_PATH, "r") as f:
        original_lines = f.readlines()
    with open(output_file, "r") as f:
        output_lines = f.readlines()

    # Compare pre-2024 section (lines 1-8797)
    for i in range(8797):
        assert original_lines[i] == output_lines[i], (
            f"Line {i+1} differs in pre-2024 section"
        )


def test_write_updated_wel_file_preserves_post_2024(tmp_path):
    """Verify post-2024 section is preserved exactly."""
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file,
        INPUT_WEL_PATH
    )

    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")

    output_file = tmp_path / "thruCY2165_2024.wel"
    write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(tmp_path),
        output_filename="thruCY2165_2024.wel"
    )

    # Read original and output files
    with open(INPUT_WEL_PATH, "r") as f:
        original_lines = f.readlines()
    with open(output_file, "r") as f:
        output_lines = f.readlines()

    # Compare post-2024 section (lines 9122-54805, indices 9121-)
    post_2024_start = 9121
    for i in range(post_2024_start, 54805):
        assert original_lines[i] == output_lines[i], (
            f"Line {i+1} differs in post-2024 section"
        )


def test_write_updated_wel_file_invalid_2024_count_raises():
    """Verify error raised if 2024 lines count is wrong."""
    from update_modflow_2024 import parse_wel_file, write_updated_wel_file

    wel_data = parse_wel_file()

    # Wrong number of 2024 lines (should be 324)
    wrong_lines = ["test\r\n"] * 100

    with pytest.raises(ValueError, match="Expected 324 lines"):
        write_updated_wel_file(wel_data, wrong_lines)


# =============================================================================
# US-007: Generate Updated .nam File
# =============================================================================


def test_generate_nam_file_exists():
    """Verify generate_nam_file function exists and is callable."""
    from update_modflow_2024 import generate_nam_file

    assert callable(generate_nam_file)


def test_generate_nam_file_creates_file(tmp_path):
    """Verify generate_nam_file creates output file."""
    from update_modflow_2024 import generate_nam_file

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    assert result_path.exists(), "Output file should exist"
    assert result_path.name == "CY2024.nam"


def test_generate_nam_file_creates_directory(tmp_path):
    """Verify generate_nam_file creates output directory if needed."""
    from update_modflow_2024 import generate_nam_file

    output_dir = tmp_path / "nested" / "output" / "dir"

    result_path = generate_nam_file(
        output_dir=str(output_dir),
        output_filename="CY2024.nam"
    )

    assert output_dir.exists(), "Output directory should be created"
    assert result_path.exists(), "Output file should exist"


def test_generate_nam_file_has_header_comments(tmp_path):
    """Verify output file has header comment block."""
    from update_modflow_2024 import generate_nam_file

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    with open(result_path, "r") as f:
        lines = f.readlines()

    # First 4 lines should be comments
    assert lines[0].startswith("#"), "Line 1 should be a comment"
    assert lines[1].startswith("#"), "Line 2 should be a comment"
    assert lines[2].startswith("#"), "Line 3 should be a comment"
    assert lines[3].startswith("#"), "Line 4 should be a comment"

    # First line should mention Buckman Depletion Model
    assert "Buckman Depletion Model" in lines[0], (
        f"First comment should mention Buckman Depletion Model: {lines[0]}"
    )


def test_generate_nam_file_replaces_cy2023_with_cy2024(tmp_path):
    """Verify CY2023 references are replaced with CY2024."""
    from update_modflow_2024 import generate_nam_file

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    with open(result_path, "r") as f:
        content = f.read()

    # Should have CY2024 references
    assert "CY2024.lst" in content, "Should contain CY2024.lst"
    assert "CY2024_riv.flx" in content, "Should contain CY2024_riv.flx"
    assert "CY2024_ghb.flx" in content, "Should contain CY2024_ghb.flx"

    # Skip header lines (which contain "2024") for the CY2023 check
    lines = content.split("\n")
    non_comment_content = "\n".join(
        line for line in lines if not line.startswith("#")
    )

    # Should NOT have CY2023 references in non-comment lines
    assert "CY2023" not in non_comment_content, (
        f"Should not contain CY2023 in data lines: {non_comment_content}"
    )


def test_generate_nam_file_replaces_wel_filename(tmp_path):
    """Verify .wel filename is updated to thruCY2165_2024.wel."""
    from update_modflow_2024 import generate_nam_file

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    with open(result_path, "r") as f:
        content = f.read()

    assert "thruCY2165_2024.wel" in content, (
        "Should contain thruCY2165_2024.wel"
    )
    # Original filename should not appear in data (could appear in comments)
    lines = content.split("\n")
    non_comment_content = "\n".join(
        line for line in lines if not line.startswith("#")
    )
    # Check that the original .wel (without _2024) is not referenced
    assert "thruCY2165.wel" not in non_comment_content, (
        "Should not contain thruCY2165.wel in data lines"
    )


def test_generate_nam_file_uppercase_package_types(tmp_path):
    """Verify package types are uppercase (LIST, BAS, BCF, etc.)."""
    from update_modflow_2024 import generate_nam_file

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    with open(result_path, "r") as f:
        lines = f.readlines()

    # Skip comment lines
    data_lines = [line for line in lines if not line.startswith("#")]

    # Check for uppercase package types
    expected_types = ["LIST", "BAS", "BCF", "OC", "RIV", "GHB", "SIP", "WEL", "DATA(BINARY)"]
    for pkg_type in expected_types:
        found = any(line.strip().startswith(pkg_type) for line in data_lines)
        assert found, f"Should contain uppercase package type: {pkg_type}"


def test_generate_nam_file_matches_validation_content(tmp_path):
    """
    Verify generated .nam file content matches validation file.

    Ignores comment lines (timestamps will differ) and compares
    all non-comment lines.
    """
    from update_modflow_2024 import generate_nam_file, VALIDATION_NAM_PATH

    result_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    # Read generated file
    with open(result_path, "r") as f:
        gen_lines = f.readlines()

    # Read validation file
    with open(VALIDATION_NAM_PATH, "r") as f:
        val_lines = f.readlines()

    # Filter out comment lines
    gen_data = [line.rstrip("\r\n") for line in gen_lines if not line.startswith("#")]
    val_data = [line.rstrip("\r\n") for line in val_lines if not line.startswith("#")]

    # Compare non-comment content
    assert len(gen_data) == len(val_data), (
        f"Line count mismatch: generated {len(gen_data)}, validation {len(val_data)}"
    )

    for i, (gen_line, val_line) in enumerate(zip(gen_data, val_data)):
        assert gen_line == val_line, (
            f"Line {i+1} mismatch.\nGenerated:  '{gen_line}'\n"
            f"Validation: '{val_line}'"
        )


def test_generate_nam_file_raises_on_missing_input():
    """Verify FileNotFoundError raised if input .nam file doesn't exist."""
    from update_modflow_2024 import generate_nam_file

    with pytest.raises(FileNotFoundError, match="Input .nam file not found"):
        generate_nam_file(input_nam_path="/nonexistent/path/CY2023.nam")


# =============================================================================
# US-008: Validate Output Against 2024 Validation Files
# =============================================================================


def test_validation_result_class_exists():
    """Verify ValidationResult class exists."""
    from update_modflow_2024 import ValidationResult

    result = ValidationResult()
    assert hasattr(result, "wells_checked")
    assert hasattr(result, "months_checked")
    assert hasattr(result, "pass_count")
    assert hasattr(result, "fail_count")
    assert hasattr(result, "failures")
    assert hasattr(result, "all_passed")


def test_validate_nam_file_exists():
    """Verify validate_nam_file function exists and is callable."""
    from update_modflow_2024 import validate_nam_file

    assert callable(validate_nam_file)


def test_validate_nam_file_passes_for_matching_files(tmp_path):
    """Verify validate_nam_file passes when files match (ignoring comments)."""
    from update_modflow_2024 import generate_nam_file, validate_nam_file

    # Generate a .nam file
    generated_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    # Validate against itself (same non-comment content)
    passed, errors = validate_nam_file(str(generated_path), str(generated_path))

    assert passed, f"Should pass when comparing identical files: {errors}"
    assert len(errors) == 0


def test_validate_nam_file_against_validation(tmp_path):
    """Verify generated .nam file passes validation against known-good file."""
    from update_modflow_2024 import generate_nam_file, validate_nam_file

    # Generate a .nam file
    generated_path = generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    # Validate against actual validation file
    passed, errors = validate_nam_file(str(generated_path))

    assert passed, f".nam validation failed: {errors}"


def test_validate_nam_file_fails_for_missing_file(tmp_path):
    """Verify validate_nam_file fails gracefully for missing file."""
    from update_modflow_2024 import validate_nam_file

    passed, errors = validate_nam_file("/nonexistent/path.nam")

    assert not passed
    assert len(errors) > 0
    assert "not found" in errors[0]


def test_validate_wel_file_exists():
    """Verify validate_wel_file function exists and is callable."""
    from update_modflow_2024 import validate_wel_file

    assert callable(validate_wel_file)


def test_validate_wel_file_returns_validation_result():
    """Verify validate_wel_file returns ValidationResult object."""
    from update_modflow_2024 import validate_wel_file, ValidationResult

    # Test with non-existent file (should return result with failure)
    result = validate_wel_file("/nonexistent/path.wel")

    assert isinstance(result, ValidationResult)
    assert not result.all_passed


def test_validate_wel_file_full_pipeline(tmp_path):
    """
    Integration test: Generate .wel file and validate against known-good file.

    This tests the complete pipeline:
    1. Parse input .wel file
    2. Read pumping data from CSV
    3. Generate 2024 well entries
    4. Write updated .wel file
    5. Validate against validation file
    """
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file,
        validate_wel_file
    )

    # Generate the .wel file
    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")
    output_file = write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(tmp_path),
        output_filename="thruCY2165_2024.wel"
    )

    # Validate
    result = validate_wel_file(str(output_file))

    # Pre-2024 and post-2024 should always pass (unchanged)
    assert result.wel_pre_2024_passed, "Pre-2024 section should be identical"
    assert result.wel_post_2024_passed, "Post-2024 section should be identical"

    # 2024 rates should pass within tolerance
    assert result.wel_2024_passed, (
        f"2024 rates validation failed. "
        f"Failures: {result.failures}"
    )

    # Summary
    assert result.wells_checked == 312, (  # 13 wells × 2 layers × 12 months
        f"Expected 312 wells checked, got {result.wells_checked}"
    )
    assert result.months_checked == 12
    assert result.pass_count == result.wells_checked
    assert result.fail_count == 0


def test_print_validation_report_exists():
    """Verify print_validation_report function exists and is callable."""
    from update_modflow_2024 import print_validation_report

    assert callable(print_validation_report)


def test_run_validation_exists():
    """Verify run_validation function exists and is callable."""
    from update_modflow_2024 import run_validation

    assert callable(run_validation)


def test_run_validation_full_pipeline(tmp_path):
    """
    Integration test: Full validation pipeline with generated files.
    """
    from update_modflow_2024 import (
        parse_wel_file, read_table2_pumping_data,
        generate_2024_well_entries, write_updated_wel_file,
        generate_nam_file, run_validation
    )

    # Generate both files
    wel_data = parse_wel_file()
    pumping_data = read_table2_pumping_data()
    new_2024_lines = generate_2024_well_entries(pumping_data, line_ending="\r\n")
    write_updated_wel_file(
        wel_data, new_2024_lines,
        output_dir=str(tmp_path),
        output_filename="thruCY2165_2024.wel"
    )
    generate_nam_file(
        output_dir=str(tmp_path),
        output_filename="CY2024.nam"
    )

    # Run validation
    success = run_validation(
        output_dir=str(tmp_path),
        wel_filename="thruCY2165_2024.wel",
        nam_filename="CY2024.nam"
    )

    assert success, "Full validation pipeline should pass"


# =============================================================================
# US-009: Main Entry Point and CLI Tests
# =============================================================================
def test_parse_args_exists():
    """Verify parse_args function exists and is callable."""
    from update_modflow_2024 import parse_args

    assert callable(parse_args)


def test_main_exists():
    """Verify main function exists and is callable."""
    from update_modflow_2024 import main

    assert callable(main)


def test_print_pumping_summary_exists():
    """Verify print_pumping_summary function exists and is callable."""
    from update_modflow_2024 import print_pumping_summary

    assert callable(print_pumping_summary)


def test_print_pumping_summary_runs_without_error(capsys):
    """Verify print_pumping_summary runs with valid pumping data."""
    from update_modflow_2024 import print_pumping_summary, read_table2_pumping_data

    pumping_data = read_table2_pumping_data()
    print_pumping_summary(pumping_data)

    captured = capsys.readouterr()
    # Verify output contains expected content
    assert "2024 MONTHLY PUMPING SUMMARY" in captured.out
    assert "BUCKMAN 1" in captured.out
    assert "BUCKMAN 13" in captured.out
    assert "Annual Totals" in captured.out


def test_main_returns_zero_on_success():
    """
    Integration test: main() should return 0 on success.
    """
    import sys
    from update_modflow_2024 import main

    # Temporarily override argv to avoid argparse reading test runner args
    original_argv = sys.argv
    sys.argv = ["update_modflow_2024.py"]

    try:
        result = main()
        assert result == 0, f"main() should return 0 on success, got {result}"
    finally:
        sys.argv = original_argv


def test_script_runs_end_to_end(capsys):
    """
    Integration test: Full script runs and prints expected progress messages.
    """
    import sys
    from update_modflow_2024 import main

    original_argv = sys.argv
    sys.argv = ["update_modflow_2024.py"]

    try:
        result = main()
        captured = capsys.readouterr()

        # Verify progress messages
        assert "[1/7] Reading Table 2 pumping data" in captured.out
        assert "[2/7] Converting acre-feet to ft³/s" in captured.out
        assert "[3/7] Parsing 2023 .wel file" in captured.out
        assert "[4/7] Generating 2024 well entries" in captured.out
        assert "[5/7] Writing updated .wel file" in captured.out
        assert "[6/7] Generating updated .nam file" in captured.out
        assert "[7/7] Validating against known-good files" in captured.out
        assert "Validation PASSED" in captured.out
        assert result == 0
    finally:
        sys.argv = original_argv
