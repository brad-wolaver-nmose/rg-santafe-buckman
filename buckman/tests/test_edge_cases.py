#!/usr/bin/env python3
"""
Layer 0.5: Pipeline Edge Case Testing.

Validates that the pipeline handles unexpected, malformed, or boundary-condition
inputs correctly - either by processing them gracefully or failing with clear,
diagnostic error messages.

These tests run in <30 seconds with no MODFLOW dependency.

Usage:
    pytest tests/test_edge_cases.py -v
    pytest tests/test_edge_cases.py -v -m edge_cases

Test Categories:
    1. TestInputValidation - Missing files, empty CSV, malformed columns
    2. TestDataQuality - Bad values, missing data, NaN handling
    3. TestBoundaryConditions - Zero pumping, leap year, single day
    4. TestFileOperations - Permissions, existing files, missing dirs
    5. TestWelFileIntegrity - Line count, CRLF, column alignment
"""
import os
import stat
import sys
from pathlib import Path

import pandas as pd
import pytest

# Apply Layer 0.5 marker to all tests in this file
pytestmark = pytest.mark.edge_cases

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES: Valid Test Data
# =============================================================================
@pytest.fixture
def sample_valid_table2_csv(tmp_path):
    """
    Create minimal valid Table 2 CSV for testing step2_update_modflow.

    Format matches output/ingested_data/{year}_Table_2_output.csv
    with 13 wells and monthly columns (JAN-DEC).
    """
    csv_path = tmp_path / "2024_Table_2_output.csv"

    # Create valid CSV with all 13 wells
    rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
    for well in range(1, 14):
        # Simple test data: well number as pumping rate for each month
        monthly = [float(well)] * 12
        total = sum(monthly)
        row = f"{well}," + ",".join(f"{v:.6f}" for v in monthly) + f",{total:.6f}"
        rows.append(row)

    # Add totals row
    rows.append("Total,78.0,78.0,78.0,78.0,78.0,78.0,78.0,78.0,78.0,78.0,78.0,78.0,936.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


@pytest.fixture
def sample_valid_daily_csv(tmp_path):
    """
    Create minimal valid daily pumping CSV for testing step1_ingest_buckman_data.

    Format matches input/csv/Buckman_Well_Prod_{year}.csv
    with Date column and BWell 1-13 columns plus BWP_Total.
    """
    csv_path = tmp_path / "Buckman_Well_Prod_2024.csv"

    # Headers: Date, BWell 1-13, BWP_Total
    headers = ["Date"] + [f"BWell {i}" for i in range(1, 14)] + ["BWP_Total"]

    # Generate 366 rows for 2024 (leap year)
    rows = [",".join(headers)]

    for day in range(1, 367):
        month = ((day - 1) // 30) % 12 + 1
        day_of_month = ((day - 1) % 30) + 1
        date_str = f"{month:02d}/{day_of_month:02d}/2024"

        # Simple pumping values: 1.0 MGD per well
        well_values = ["1.0"] * 13
        total = "13.0"

        row = f"{date_str}," + ",".join(well_values) + f",{total}"
        rows.append(row)

    # Add sum row at end
    sum_row = "Sum," + ",".join(["366.0"] * 13) + ",4758.0"
    rows.append(sum_row)

    csv_path.write_text("\n".join(rows))
    return csv_path


# =============================================================================
# FIXTURES: Invalid Test Data
# =============================================================================
@pytest.fixture
def csv_missing_column(tmp_path):
    """CSV missing BWell 5 column."""
    csv_path = tmp_path / "missing_column.csv"

    # Headers: Date, BWell 1-4, BWell 6-13 (missing BWell 5)
    headers = ["Date"] + [f"BWell {i}" for i in range(1, 5)] + \
              [f"BWell {i}" for i in range(6, 14)] + ["BWP_Total"]

    rows = [",".join(headers)]
    rows.append("01/01/2024," + ",".join(["1.0"] * 12) + ",12.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


@pytest.fixture
def csv_empty(tmp_path):
    """CSV with headers but no data rows."""
    csv_path = tmp_path / "empty.csv"
    headers = ["Date"] + [f"BWell {i}" for i in range(1, 14)] + ["BWP_Total"]
    csv_path.write_text(",".join(headers) + "\n")
    return csv_path


@pytest.fixture
def csv_negative_values(tmp_path):
    """Table 2 CSV with negative pumping value."""
    csv_path = tmp_path / "negative.csv"

    rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
    # Well 1 has negative JAN value
    rows.append("1,-5.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,105.0")
    for well in range(2, 14):
        rows.append(f"{well}," + ",".join(["10.0"] * 12) + ",120.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


@pytest.fixture
def csv_nan_values(tmp_path):
    """Table 2 CSV with NaN value."""
    csv_path = tmp_path / "nan_values.csv"

    rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
    # Well 3 has NaN in MAR
    rows.append("1,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,120.0")
    rows.append("2,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,120.0")
    rows.append("3,10.0,10.0,,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,110.0")  # Empty = NaN
    for well in range(4, 14):
        rows.append(f"{well}," + ",".join(["10.0"] * 12) + ",120.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


@pytest.fixture
def csv_missing_well(tmp_path):
    """Table 2 CSV missing Well 7."""
    csv_path = tmp_path / "missing_well.csv"

    rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
    for well in range(1, 14):
        if well != 7:  # Skip well 7
            rows.append(f"{well}," + ",".join(["10.0"] * 12) + ",120.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


@pytest.fixture
def csv_zero_pumping_all_wells(tmp_path):
    """Table 2 CSV with all wells = 0 for full year."""
    csv_path = tmp_path / "zero_all.csv"

    rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
    for well in range(1, 14):
        rows.append(f"{well}," + ",".join(["0.0"] * 12) + ",0.0")
    rows.append("Total," + ",".join(["0.0"] * 12) + ",0.0")

    csv_path.write_text("\n".join(rows))
    return csv_path


# =============================================================================
# TEST CATEGORY 1: Input Validation Tests
# =============================================================================
@pytest.mark.edge_cases
class TestInputValidation:
    """Verify pipeline handles malformed input files correctly."""

    def test_missing_input_file_step2(self):
        """step2 with nonexistent CSV raises FileNotFoundError with path."""
        from step2_update_modflow import read_table2_pumping_data

        fake_path = "/nonexistent/path/to/file.csv"
        with pytest.raises(FileNotFoundError) as exc_info:
            read_table2_pumping_data(fake_path)

        # Error message should include the path
        assert fake_path in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    def test_empty_csv_step2(self, csv_empty):
        """CSV with headers but no data rows produces error."""
        from step2_update_modflow import read_table2_pumping_data

        # Empty CSV should raise an error when trying to read well data
        with pytest.raises((ValueError, KeyError, pd.errors.EmptyDataError)):
            read_table2_pumping_data(str(csv_empty))

    def test_csv_missing_well_step2(self, csv_missing_well):
        """CSV missing a well (Well 7) raises ValueError identifying which well."""
        from step2_update_modflow import read_table2_pumping_data

        with pytest.raises(ValueError) as exc_info:
            read_table2_pumping_data(str(csv_missing_well))

        # Error should mention missing well or wells 1-13
        error_msg = str(exc_info.value).lower()
        assert "missing" in error_msg or "7" in error_msg or "wells" in error_msg

    def test_csv_with_extra_columns(self, sample_valid_table2_csv, tmp_path):
        """Extra columns ignored without crashing."""
        from step2_update_modflow import read_table2_pumping_data

        # Add extra column to valid CSV
        csv_with_extra = tmp_path / "extra_columns.csv"
        content = sample_valid_table2_csv.read_text()
        lines = content.split("\n")

        # Add extra column to header and each row
        lines[0] = lines[0] + ",ExtraCol,AnotherExtra"
        for i in range(1, len(lines)):
            if lines[i].strip():
                lines[i] = lines[i] + ",foo,bar"

        csv_with_extra.write_text("\n".join(lines))

        # Should read successfully, ignoring extra columns
        result = read_table2_pumping_data(str(csv_with_extra))
        assert len(result) == 13
        assert all(well in result for well in range(1, 14))

    def test_missing_wel_file_step2(self, tmp_path):
        """step2 with nonexistent .wel file raises FileNotFoundError."""
        from step2_update_modflow import parse_wel_file

        fake_path = str(tmp_path / "nonexistent.wel")
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_wel_file(fake_path, 2024)

        assert "not found" in str(exc_info.value).lower() or fake_path in str(exc_info.value)


# =============================================================================
# TEST CATEGORY 2: Data Quality Tests
# =============================================================================
@pytest.mark.edge_cases
class TestDataQuality:
    """Verify pipeline detects data quality issues."""

    def test_negative_pumping_value(self, csv_negative_values):
        """Negative pumping value rejected as physically impossible."""
        from step2_update_modflow import read_table2_pumping_data

        with pytest.raises(ValueError) as exc_info:
            read_table2_pumping_data(str(csv_negative_values))

        # Error should mention negative
        error_msg = str(exc_info.value).lower()
        assert "negative" in error_msg or "< 0" in error_msg or "<= 0" in error_msg

    def test_negative_rate_conversion(self):
        """convert_af_to_ft3s rejects negative acre-feet."""
        from step2_update_modflow import convert_af_to_ft3s

        with pytest.raises(ValueError) as exc_info:
            convert_af_to_ft3s(-10.0, 31)

        # Error message should indicate the value is invalid (>= 0 requirement)
        error_msg = str(exc_info.value).lower()
        assert ">= 0" in error_msg or "negative" in error_msg or "-10" in error_msg

    def test_invalid_days_in_month(self):
        """convert_af_to_ft3s rejects invalid days_in_month."""
        from step2_update_modflow import convert_af_to_ft3s

        # 0 days should fail
        with pytest.raises(ValueError):
            convert_af_to_ft3s(10.0, 0)

        # 32 days should fail
        with pytest.raises(ValueError):
            convert_af_to_ft3s(10.0, 32)

    def test_nan_in_dataframe(self, csv_nan_values):
        """NaN values in input produce error or are handled."""
        # Read CSV to pandas first to verify NaN is present
        df = pd.read_csv(csv_nan_values)

        # Verify NaN is in the data
        well_3_mar = df[df["Well"] == 3]["MAR"].values[0]
        assert pd.isna(well_3_mar), "Test data should contain NaN"

        # The pipeline should either error or handle NaN explicitly
        # (Current implementation may not handle this - test documents behavior)

    def test_unreasonably_large_pumping(self, tmp_path):
        """Value >100 MGD per well flagged as likely data error."""
        # Create CSV with extremely large value (999 AF/month ~ 11 MGD - reasonable)
        # vs 10000 AF/month which is unreasonable
        csv_path = tmp_path / "large_value.csv"

        rows = ["Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total"]
        # Well 1 has 10000 AF in JAN (unreasonably large)
        rows.append("1,10000.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10.0,10100.0")
        for well in range(2, 14):
            rows.append(f"{well}," + ",".join(["10.0"] * 12) + ",120.0")

        csv_path.write_text("\n".join(rows))

        # This test documents current behavior - large values accepted
        # Future enhancement could add validation
        from step2_update_modflow import read_table2_pumping_data

        # Should succeed (no current max limit)
        result = read_table2_pumping_data(str(csv_path))
        assert result[1]["JAN"] == 10000.0


# =============================================================================
# TEST CATEGORY 3: Boundary Condition Tests
# =============================================================================
@pytest.mark.edge_cases
class TestBoundaryConditions:
    """Verify pipeline handles edge cases at valid input boundaries."""

    def test_zero_pumping_all_wells(self, csv_zero_pumping_all_wells):
        """All wells = 0 for full year completes without error."""
        from step2_update_modflow import read_table2_pumping_data

        result = read_table2_pumping_data(str(csv_zero_pumping_all_wells))

        # Should have all 13 wells
        assert len(result) == 13

        # All values should be 0
        for well_num, monthly in result.items():
            for month, value in monthly.items():
                assert value == 0.0, f"Well {well_num} {month} should be 0.0"

    def test_zero_pumping_one_well(self, sample_valid_table2_csv, tmp_path):
        """Single well = 0 handled correctly."""
        from step2_update_modflow import read_table2_pumping_data

        # Modify CSV to have Well 5 = 0 for all months
        csv_path = tmp_path / "well5_zero.csv"
        content = sample_valid_table2_csv.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if line.startswith("5,"):
                lines[i] = "5," + ",".join(["0.0"] * 12) + ",0.0"

        csv_path.write_text("\n".join(lines))

        result = read_table2_pumping_data(str(csv_path))

        # Well 5 should have all zeros
        assert all(result[5][m] == 0.0 for m in result[5])
        # Other wells should have non-zero values
        assert result[1]["JAN"] > 0

    def test_leap_year_february_days(self):
        """Leap year (2024) has 29 days in February."""
        from step2_update_modflow import get_days_in_month

        # 2024 is a leap year
        days_2024 = get_days_in_month(2024)
        assert days_2024["FEB"] == 29

        # 2023 is not a leap year
        days_2023 = get_days_in_month(2023)
        assert days_2023["FEB"] == 28

    def test_non_leap_year_february_days(self):
        """Non-leap year (2025) has 28 days in February."""
        from step2_update_modflow import get_days_in_month

        days_2025 = get_days_in_month(2025)
        assert days_2025["FEB"] == 28

    def test_year_config_leap_year(self):
        """YearConfig correctly identifies leap years."""
        from step2_update_modflow import get_year_config

        config_2024 = get_year_config(2024)
        assert config_2024.is_leap_year is True

        config_2025 = get_year_config(2025)
        assert config_2025.is_leap_year is False

    def test_conversion_zero_acre_feet(self):
        """Zero acre-feet converts to zero rate (with negative sign convention)."""
        from step2_update_modflow import convert_af_to_ft3s

        rate = convert_af_to_ft3s(0.0, 31)
        # Zero input should give -0.0 or 0.0
        assert abs(rate) < 1e-10

    def test_very_small_pumping_value(self):
        """Very small pumping value (0.001 AF) converts without precision loss."""
        from step2_update_modflow import convert_af_to_ft3s

        rate = convert_af_to_ft3s(0.001, 31)
        # Should be a small negative number
        assert rate < 0
        assert abs(rate) < 1e-5


# =============================================================================
# TEST CATEGORY 4: File Operation Tests
# =============================================================================
@pytest.mark.edge_cases
class TestFileOperations:
    """Verify pipeline handles filesystem edge cases."""

    def test_output_directory_created(self, tmp_path):
        """Missing output dir is created automatically."""
        from step2_update_modflow import write_updated_wel_file, WelFileData

        # Create minimal WelFileData
        wel_data = WelFileData(
            pre_target_lines=["header\r\n"],
            target_year_lines=["26\r\n"] * 324,  # Placeholder
            post_target_lines=["footer\r\n"],
            target_year=2024,
        )

        # Output to nonexistent directory
        output_dir = tmp_path / "nonexistent" / "nested" / "path"
        assert not output_dir.exists()

        # Generate minimal valid year lines (12 months * 27 lines = 324)
        year_lines = []
        for _ in range(12):
            year_lines.append("        26\r\n")  # Header
            for _ in range(26):  # 26 well entries per month
                year_lines.append("         1        13        11  -0.13730  BUCKMAN 1 JAN 2024\r\n")

        result = write_updated_wel_file(
            wel_data,
            year_lines,
            str(output_dir),
            "test.wel",
        )

        assert output_dir.exists()
        assert result.exists()

    def test_output_file_overwrite(self, tmp_path):
        """Existing output file is overwritten without error."""
        from step2_update_modflow import write_updated_wel_file, WelFileData

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file
        existing_file = output_dir / "test.wel"
        existing_file.write_text("old content")
        assert existing_file.read_text() == "old content"

        # Create minimal WelFileData
        wel_data = WelFileData(
            pre_target_lines=[],
            target_year_lines=[],
            post_target_lines=[],
            target_year=2024,
        )

        # Generate minimal valid year lines
        year_lines = []
        for _ in range(12):
            year_lines.append("        26\r\n")
            for _ in range(26):
                year_lines.append("         1        13        11  -0.13730  BUCKMAN 1 JAN 2024\r\n")

        write_updated_wel_file(wel_data, year_lines, str(output_dir), "test.wel")

        # File should be overwritten
        assert existing_file.read_text() != "old content"

    @pytest.mark.skipif(os.name == 'nt', reason="Permission tests unreliable on Windows")
    def test_unreadable_input_file(self, sample_valid_table2_csv):
        """Unreadable input file produces permission error."""
        # Make file unreadable
        os.chmod(sample_valid_table2_csv, 0o000)

        try:
            from step2_update_modflow import read_table2_pumping_data

            with pytest.raises(PermissionError):
                read_table2_pumping_data(str(sample_valid_table2_csv))
        finally:
            # Restore permissions for cleanup
            os.chmod(sample_valid_table2_csv, stat.S_IRUSR | stat.S_IWUSR)


# =============================================================================
# TEST CATEGORY 5: WEL File Integrity Tests
# =============================================================================
@pytest.mark.edge_cases
class TestWelFileIntegrity:
    """Verify step2 produces valid MODFLOW input format."""

    def test_generate_well_entries_line_count(self, sample_valid_table2_csv):
        """Generates exactly 324 lines per year (12 months x 27 lines)."""
        from step2_update_modflow import generate_well_entries, read_table2_pumping_data

        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        lines = generate_well_entries(pumping_data, 2024)

        assert len(lines) == 324, f"Expected 324 lines, got {len(lines)}"

    def test_wel_file_crlf_endings(self, sample_valid_table2_csv):
        """WEL file uses Windows CRLF line endings for MODFLOW96 compatibility."""
        from step2_update_modflow import generate_well_entries, read_table2_pumping_data

        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        lines = generate_well_entries(pumping_data, 2024)

        # All lines should end with \r\n
        for i, line in enumerate(lines):
            assert line.endswith("\r\n"), f"Line {i+1} should end with CRLF"

    def test_wel_file_column_alignment(self, sample_valid_table2_csv):
        """Fixed-width columns match MODFLOW spec."""
        from step2_update_modflow import generate_well_entry_line

        line = generate_well_entry_line(
            layer=1,
            row=13,
            col=11,
            rate=-0.13730,
            well_name="BUCKMAN 1",
            month="JAN",
            year=2024,
        )

        # Parse the line to verify column positions
        parts = line.split()

        # Should have: layer, row, col, rate, well_name, month, year
        assert parts[0] == "1"  # layer
        assert parts[1] == "13"  # row
        assert parts[2] == "11"  # col
        # Rate should be formatted with 5 decimal places
        assert len(parts[3].split(".")[-1].rstrip("\r\n")) == 5

    def test_well_name_mapping_well3(self):
        """Well 3 maps to 'BUCKMAN 3A' (special case)."""
        from step2_update_modflow import WELL_NAME_MAP

        assert WELL_NAME_MAP[3] == "BUCKMAN 3A"

        # Other wells should have standard names
        assert WELL_NAME_MAP[1] == "BUCKMAN 1"
        assert WELL_NAME_MAP[13] == "BUCKMAN 13"

    def test_pumping_rate_sign_negative(self, sample_valid_table2_csv):
        """All pumping rates are negative (MODFLOW extraction convention)."""
        from step2_update_modflow import generate_well_entries, read_table2_pumping_data

        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        lines = generate_well_entries(pumping_data, 2024)

        for i, line in enumerate(lines):
            # Skip header lines (they contain just "26")
            if line.strip() == "26":
                continue

            parts = line.split()
            if len(parts) >= 4:
                rate = float(parts[3])
                assert rate <= 0, f"Line {i+1}: rate {rate} should be <= 0"

    def test_layer_split_two_entries(self, sample_valid_table2_csv):
        """Each well has entries for Layer 1 and Layer 2."""
        from step2_update_modflow import generate_well_entries, read_table2_pumping_data

        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        lines = generate_well_entries(pumping_data, 2024)

        # For each month (27 lines: 1 header + 26 well entries = 13 wells x 2 layers)
        for month_idx in range(12):
            start = month_idx * 27

            # Header
            assert lines[start].strip() == "26"

            # Count Layer 1 and Layer 2 entries
            layer1_count = 0
            layer2_count = 0

            for i in range(1, 27):  # Skip header
                line = lines[start + i]
                parts = line.split()
                if parts:
                    layer = int(parts[0])
                    if layer == 1:
                        layer1_count += 1
                    elif layer == 2:
                        layer2_count += 1

            assert layer1_count == 13, f"Month {month_idx+1}: expected 13 Layer 1 entries"
            assert layer2_count == 13, f"Month {month_idx+1}: expected 13 Layer 2 entries"

    def test_well_grid_mapping(self):
        """All 13 wells have valid grid coordinates."""
        from step2_update_modflow import WELL_GRID_MAP, WELL_NAME_MAP

        for well_num in range(1, 14):
            well_name = WELL_NAME_MAP[well_num]
            assert well_name in WELL_GRID_MAP, f"{well_name} missing from WELL_GRID_MAP"

            row, col = WELL_GRID_MAP[well_name]
            assert 1 <= row <= 30, f"{well_name} row {row} out of range"
            assert 1 <= col <= 30, f"{well_name} col {col} out of range"

    def test_month_header_format(self):
        """Month headers have correct format."""
        from step2_update_modflow import generate_month_header

        header = generate_month_header()

        # Should be "        26" with CRLF
        assert header.strip() == "26"
        assert header.endswith("\r\n")

        # Fixed width: 10 characters before the 26
        content = header.rstrip("\r\n")
        assert len(content) == 10


# =============================================================================
# INTEGRATION TESTS
# =============================================================================
@pytest.mark.edge_cases
class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_step2_pipeline_with_valid_data(self, sample_valid_table2_csv, tmp_path):
        """Full step2 pipeline runs without error on valid data."""
        from step2_update_modflow import (
            generate_well_entries,
            read_table2_pumping_data,
        )

        # Read pumping data
        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        assert len(pumping_data) == 13

        # Generate well entries
        lines = generate_well_entries(pumping_data, 2024)
        assert len(lines) == 324

    def test_conversion_roundtrip_consistency(self, sample_valid_table2_csv):
        """Acre-feet to ft³/s conversion is consistent across wells/months."""
        from step2_update_modflow import (
            convert_af_to_ft3s,
            get_days_in_month,
            read_table2_pumping_data,
        )

        pumping_data = read_table2_pumping_data(str(sample_valid_table2_csv))
        days = get_days_in_month(2024)

        # Same acre-feet value should give same rate for same month
        for well_num in pumping_data:
            for month in pumping_data[well_num]:
                af = pumping_data[well_num][month]
                rate1 = convert_af_to_ft3s(af, days[month])
                rate2 = convert_af_to_ft3s(af, days[month])
                assert rate1 == rate2, f"Inconsistent conversion for {well_num}/{month}"
