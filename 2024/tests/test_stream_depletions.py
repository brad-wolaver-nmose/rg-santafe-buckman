"""
Smoke tests for stream_depletions module.
Verifies code RUNS - domain expert must verify calculations independently.

These tests support the Ralph iterate-until-pass loop.
They catch mechanical failures, not logical errors.

Scientific context:
- Stream depletions are reductions in surface water flow caused by groundwater pumping
- Values in cfs (cubic feet per second) or acre-feet (AF)
- Typical depletion magnitudes: 0.001-1.0 cfs per cell, 50-100 AF/year per stream
"""
import pytest
from pathlib import Path


def test_module_imports():
    """Verify module imports without syntax errors."""
    import stream_depletions


def test_cfs_to_af_exists():
    """Verify unit conversion function exists."""
    from stream_depletions import cfs_to_acre_feet
    assert callable(cfs_to_acre_feet)


def test_cfs_to_af_runs():
    """
    Verify cfs_to_acre_feet executes without crashing.

    Hand calculation check:
    - 1 cfs for 30 days = 1 * 30 * 1.9835 = 59.505 AF
    """
    from stream_depletions import cfs_to_acre_feet

    # Simple realistic input: 1 cfs for 30 days
    result = cfs_to_acre_feet(1.0, 30)

    assert result is not None
    assert isinstance(result, float)
    # Sanity check: should be roughly 59.5 AF (not 0, not 1000)
    assert 50 < result < 70, f"Result {result} outside expected range [50, 70]"


def test_cfs_to_af_sanity():
    """
    Verify conversion produces physically reasonable values.

    Scientific basis:
    - 1 cfs = 1 ft³/s = 86,400 ft³/day
    - 1 AF = 43,560 ft³
    - So 1 cfs for 1 day = 86400/43560 = 1.9835 AF

    Test: 0.1 cfs for 31 days (January) should be ~6.15 AF
    """
    from stream_depletions import cfs_to_acre_feet

    result = cfs_to_acre_feet(0.1, 31)

    # Expected: 0.1 * 31 * 1.9835 = 6.149 AF
    assert 5.0 < result < 8.0, f"Result {result} outside expected range [5, 8]"


def test_core_2003_residuals_exist():
    """Verify Core (2003) analytical model constants are defined."""
    from stream_depletions import CORE_2003_POJOAQUE, CORE_2003_TESUQUE

    # Pojoaque should have values 1988-2015
    assert 1988 in CORE_2003_POJOAQUE
    assert 2015 in CORE_2003_POJOAQUE
    assert isinstance(CORE_2003_POJOAQUE[2015], float)

    # Tesuque should have values 1988-2030+
    assert 1988 in CORE_2003_TESUQUE
    assert 2024 in CORE_2003_TESUQUE
    assert isinstance(CORE_2003_TESUQUE[2024], float)


def test_core_2003_pojoaque_value():
    """
    Verify Pojoaque residual value matches Core (2003) table.

    From Core (2003) PROJECTION.XLS:
    - 2015: 0.316 AF (last positive value)
    - 2024: 0 (residual exhausted after 2015)
    """
    from stream_depletions import get_analytical_residual

    # 2015 should be ~0.316 AF
    result_2015 = get_analytical_residual("pojoaque", 2015)
    assert 0.0 < result_2015 < 1.0, f"2015 Pojoaque residual {result_2015} should be ~0.316"

    # 2024 should be 0 (or very small)
    result_2024 = get_analytical_residual("pojoaque", 2024)
    assert result_2024 == 0.0 or result_2024 < 0.01, f"2024 Pojoaque residual should be 0"


def test_core_2003_tesuque_value():
    """
    Verify Tesuque residual value matches Core (2003) table.

    From Core (2003) PROJECTION.XLS:
    - 2024: 12.877 AF
    """
    from stream_depletions import get_analytical_residual

    result = get_analytical_residual("tesuque", 2024)

    # Expected: 12.877 AF (allow 0.5 AF tolerance)
    assert 12.0 < result < 14.0, f"2024 Tesuque residual {result} should be ~12.877"


def test_otowi_cell_definitions():
    """Verify Otowi gage cell lists are defined correctly."""
    from stream_depletions import ABOVE_OTOWI_CELLS, BELOW_OTOWI_CELLS

    # Above Otowi should have 10 cells
    assert len(ABOVE_OTOWI_CELLS) == 10, f"Expected 10 Above Otowi cells, got {len(ABOVE_OTOWI_CELLS)}"

    # Below Otowi should have 16 cells
    assert len(BELOW_OTOWI_CELLS) == 16, f"Expected 16 Below Otowi cells, got {len(BELOW_OTOWI_CELLS)}"

    # All cells should be (layer, row, col) tuples with layer=1
    for cell in ABOVE_OTOWI_CELLS + BELOW_OTOWI_CELLS:
        assert len(cell) == 3, f"Cell {cell} should be (layer, row, col) tuple"
        assert cell[0] == 1, f"Cell {cell} should have layer=1"


def test_days_per_month_2024():
    """Verify 2024 days per month (leap year) is defined correctly."""
    from stream_depletions import DAYS_2024

    assert len(DAYS_2024) == 12, "Should have 12 months"
    assert DAYS_2024[1] == 29, "February 2024 should have 29 days (leap year)"
    assert sum(DAYS_2024) == 366, "2024 is a leap year with 366 days"


def test_parse_postprocessor_output_exists():
    """Verify parser function exists."""
    from stream_depletions import parse_postprocessor_output
    assert callable(parse_postprocessor_output)


def test_print_error_exists():
    """Verify forensic error printing function exists."""
    from stream_depletions import print_error
    assert callable(print_error)


def test_extract_otowi_depletions_exists():
    """Verify extract_otowi_depletions function exists and is callable."""
    from stream_depletions import extract_otowi_depletions
    assert callable(extract_otowi_depletions)


def test_print_otowi_verification_exists():
    """Verify print_otowi_verification function exists and is callable."""
    from stream_depletions import print_otowi_verification
    assert callable(print_otowi_verification)


def test_extract_otowi_depletions_with_mock_data():
    """
    Verify extract_otowi_depletions correctly sums cell values.

    Uses minimal mock data to test the aggregation logic.
    """
    from stream_depletions import extract_otowi_depletions, ABOVE_OTOWI_CELLS, BELOW_OTOWI_CELLS

    # Create mock parsed data with 0.1 cfs for all cells and months
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    mock_data: dict[int, dict[str, dict[str, float]]] = {2024: {}}

    for lay, row, col in ABOVE_OTOWI_CELLS + BELOW_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        mock_data[2024][cell_key] = {month: 0.1 for month in months}

    above, below = extract_otowi_depletions(mock_data, 2024)

    # Above: 10 cells * 0.1 = 1.0 per month
    assert len(above) == 12
    assert abs(above[0] - 1.0) < 0.001, f"Expected 1.0, got {above[0]}"

    # Below: 16 cells * 0.1 = 1.6 per month
    assert len(below) == 12
    assert abs(below[0] - 1.6) < 0.001, f"Expected 1.6, got {below[0]}"


def test_print_residual_verification_exists():
    """Verify print_residual_verification function exists and is callable."""
    from stream_depletions import print_residual_verification
    assert callable(print_residual_verification)


def test_print_residual_verification_runs(capsys):
    """Verify print_residual_verification runs and prints expected output."""
    from stream_depletions import print_residual_verification

    print_residual_verification(2024)
    captured = capsys.readouterr()

    # Should contain stream names and values
    assert "Pojoaque" in captured.out
    assert "Tesuque" in captured.out
    assert "12.877" in captured.out  # Tesuque 2024 value
    assert "0.000" in captured.out   # Pojoaque 2024 value (exhausted)


def test_cfs_to_af_exists():
    """Verify cfs_to_af function exists and is callable."""
    from stream_depletions import cfs_to_af
    assert callable(cfs_to_af)


def test_cfs_to_af_january():
    """
    Verify cfs_to_af returns correct value for January.

    Hand calculation:
    - January has 31 days
    - 0.1 cfs * 31 days * 1.9835 = 6.14885 AF
    """
    from stream_depletions import cfs_to_af

    result = cfs_to_af(0.1, 0)  # January is month_index 0

    assert abs(result - 6.14885) < 0.001, f"Expected ~6.14885, got {result}"


def test_cfs_to_af_february_leap_year():
    """
    Verify cfs_to_af handles February leap year correctly.

    Hand calculation:
    - February 2024 has 29 days (leap year)
    - 1.0 cfs * 29 days * 1.9835 = 57.5215 AF
    """
    from stream_depletions import cfs_to_af

    result = cfs_to_af(1.0, 1)  # February is month_index 1

    assert abs(result - 57.5215) < 0.001, f"Expected ~57.5215, got {result}"


def test_cfs_to_af_raises_on_negative():
    """Verify cfs_to_af raises ValueError on negative cfs."""
    from stream_depletions import cfs_to_af

    with pytest.raises(ValueError, match="cfs_value must be >= 0"):
        cfs_to_af(-1.0, 0)


def test_cfs_to_af_raises_on_invalid_month():
    """Verify cfs_to_af raises ValueError on invalid month index."""
    from stream_depletions import cfs_to_af

    with pytest.raises(ValueError, match="month_index must be 0-11"):
        cfs_to_af(1.0, 12)

    with pytest.raises(ValueError, match="month_index must be 0-11"):
        cfs_to_af(1.0, -1)


def test_cfs_monthly_to_af_annual_exists():
    """Verify cfs_monthly_to_af_annual function exists and is callable."""
    from stream_depletions import cfs_monthly_to_af_annual
    assert callable(cfs_monthly_to_af_annual)


def test_cfs_monthly_to_af_annual_constant_flow():
    """
    Verify cfs_monthly_to_af_annual with constant 0.1 cfs all year.

    Hand calculation:
    - 0.1 cfs * 366 days * 1.9835 = 72.5961 AF (leap year)
    """
    from stream_depletions import cfs_monthly_to_af_annual

    result = cfs_monthly_to_af_annual([0.1] * 12)

    assert abs(result - 72.5961) < 0.01, f"Expected ~72.5961, got {result}"


def test_cfs_monthly_to_af_annual_raises_on_wrong_length():
    """Verify cfs_monthly_to_af_annual raises ValueError on non-12 element list."""
    from stream_depletions import cfs_monthly_to_af_annual

    with pytest.raises(ValueError, match="must have 12 elements"):
        cfs_monthly_to_af_annual([0.1] * 11)

    with pytest.raises(ValueError, match="must have 12 elements"):
        cfs_monthly_to_af_annual([0.1] * 13)


def test_cfs_monthly_to_af_annual_raises_on_negative():
    """Verify cfs_monthly_to_af_annual raises ValueError on negative cfs value."""
    from stream_depletions import cfs_monthly_to_af_annual

    cfs_list = [0.1] * 12
    cfs_list[5] = -0.1  # June is negative

    with pytest.raises(ValueError, match="cfs_list\\[5\\] must be >= 0"):
        cfs_monthly_to_af_annual(cfs_list)


def test_generate_table3_data_exists():
    """Verify generate_table3_data function exists and is callable."""
    from stream_depletions import generate_table3_data
    assert callable(generate_table3_data)


def test_generate_table3_data_with_mock():
    """
    Verify generate_table3_data correctly combines residuals and superposition.

    Uses mock data to test the calculation logic.
    """
    from stream_depletions import generate_table3_data

    # Create mock parsed data with constant 0.1 cfs for all months
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    mock_data: dict[int, dict[str, dict[str, float]]] = {
        2024: {
            "R POJOAQUE": {m: 0.1 for m in months},
            "R TESUQUE": {m: 0.1 for m in months},
        }
    }

    result = generate_table3_data(mock_data, 2024)

    # Check structure
    assert "pojoaque" in result
    assert "tesuque" in result
    assert "residual_af" in result["pojoaque"]
    assert "superposition_af" in result["pojoaque"]
    assert "total_impact_af" in result["pojoaque"]

    # Check Pojoaque residual is 0 for 2024 (exhausted after 2015)
    assert result["pojoaque"]["residual_af"] == 0.0

    # Check Tesuque residual is 12.877 for 2024
    assert abs(result["tesuque"]["residual_af"] - 12.877) < 0.001

    # Check superposition: 0.1 cfs * 366 days * 1.9835 = 72.596 AF
    assert abs(result["pojoaque"]["superposition_af"] - 72.596) < 0.1
    assert abs(result["tesuque"]["superposition_af"] - 72.596) < 0.1

    # Check total = residual + superposition
    assert abs(result["pojoaque"]["total_impact_af"] - result["pojoaque"]["superposition_af"]) < 0.001
    assert abs(result["tesuque"]["total_impact_af"] - (12.877 + 72.596)) < 0.1


def test_generate_table3_data_raises_on_missing_year():
    """Verify generate_table3_data raises KeyError when year not found."""
    from stream_depletions import generate_table3_data

    mock_data: dict[int, dict[str, dict[str, float]]] = {2023: {}}

    with pytest.raises(KeyError, match="Year 2024 not found"):
        generate_table3_data(mock_data, 2024)


def test_generate_table3_data_raises_on_missing_stream():
    """Verify generate_table3_data raises KeyError when stream data missing."""
    from stream_depletions import generate_table3_data

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    mock_data: dict[int, dict[str, dict[str, float]]] = {
        2024: {
            "R POJOAQUE": {m: 0.1 for m in months},
            # Missing R TESUQUE
        }
    }

    with pytest.raises(KeyError, match="R TESUQUE not found"):
        generate_table3_data(mock_data, 2024)


def test_print_table3_verification_exists():
    """Verify print_table3_verification function exists and is callable."""
    from stream_depletions import print_table3_verification
    assert callable(print_table3_verification)


def test_print_table3_verification_runs(capsys):
    """Verify print_table3_verification runs and prints expected output."""
    from stream_depletions import print_table3_verification

    table3_data = {
        "pojoaque": {
            "residual_af": 0.0,
            "superposition_af": 60.797,
            "total_impact_af": 60.797,
        },
        "tesuque": {
            "residual_af": 12.877,
            "superposition_af": 98.456,
            "total_impact_af": 111.333,
        },
    }

    print_table3_verification(table3_data, 2024)
    captured = capsys.readouterr()

    # Should contain stream names and values
    assert "Pojoaque" in captured.out
    assert "Tesuque" in captured.out
    assert "60.797" in captured.out
    assert "12.877" in captured.out


def test_buckman_wells_cell_constant():
    """Verify BUCKMAN_WELLS_CELL constant is defined correctly."""
    from stream_depletions import BUCKMAN_WELLS_CELL

    assert BUCKMAN_WELLS_CELL == (1, 13, 11), f"Expected (1, 13, 11), got {BUCKMAN_WELLS_CELL}"


def test_generate_table4_data_exists():
    """Verify generate_table4_data function exists and is callable."""
    from stream_depletions import generate_table4_data
    assert callable(generate_table4_data)


def test_generate_table4_data_with_mock():
    """
    Verify generate_table4_data correctly generates Table 4 structure.

    Uses mock data with constant 0.1 cfs for all cells and months.
    """
    from stream_depletions import (
        generate_table4_data,
        ABOVE_OTOWI_CELLS,
        BELOW_OTOWI_CELLS,
        BUCKMAN_WELLS_CELL,
    )

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    # Create mock data with all required cells
    mock_data: dict[int, dict[str, dict[str, float]]] = {2024: {}}

    # Add Above Otowi cells
    for lay, row, col in ABOVE_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        mock_data[2024][cell_key] = {m: 0.1 for m in months}

    # Add Below Otowi cells
    for lay, row, col in BELOW_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        mock_data[2024][cell_key] = {m: 0.1 for m in months}

    # Add stream summaries
    mock_data[2024]["RIO GRANDE"] = {m: 2.6 for m in months}  # 10 + 16 cells * 0.1
    mock_data[2024]["R POJOAQUE"] = {m: 0.1 for m in months}
    mock_data[2024]["LC SPRINGS"] = {m: 0.01 for m in months}
    mock_data[2024]["R TESUQUE"] = {m: 0.05 for m in months}
    mock_data[2024]["RIV TOTAL"] = {m: 2.76 for m in months}

    result = generate_table4_data(mock_data, 2024)

    # Check structure
    assert "cell_data" in result
    assert "stream_summaries" in result
    assert "days_per_month" in result
    assert "above_otowi_cfs" in result
    assert "below_otowi_cfs" in result
    assert "above_otowi_af" in result
    assert "below_otowi_af" in result
    assert "above_otowi_annual_af" in result
    assert "below_otowi_annual_af" in result
    assert "buckman_cfs" in result
    assert "buckman_af" in result
    assert "buckman_annual_af" in result

    # Check cell counts
    above_count = sum(1 for c in result["cell_data"] if c["otowi"] == "above")
    below_count = sum(1 for c in result["cell_data"] if c["otowi"] == "below")
    assert above_count == 10, f"Expected 10 Above Otowi cells, got {above_count}"
    assert below_count == 16, f"Expected 16 Below Otowi cells, got {below_count}"

    # Check Above Otowi sum: 10 cells * 0.1 cfs = 1.0 cfs/month
    assert abs(result["above_otowi_cfs"][0] - 1.0) < 0.001

    # Check Below Otowi sum: 16 cells * 0.1 cfs = 1.6 cfs/month
    assert abs(result["below_otowi_cfs"][0] - 1.6) < 0.001


def test_generate_table4_data_raises_on_missing_year():
    """Verify generate_table4_data raises KeyError when year not found."""
    from stream_depletions import generate_table4_data

    mock_data: dict[int, dict[str, dict[str, float]]] = {2023: {}}

    with pytest.raises(KeyError, match="Year 2024 not found"):
        generate_table4_data(mock_data, 2024)


def test_generate_table4_data_raises_on_missing_stream():
    """Verify generate_table4_data raises KeyError when stream data missing."""
    from stream_depletions import generate_table4_data, ABOVE_OTOWI_CELLS, BELOW_OTOWI_CELLS

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    mock_data: dict[int, dict[str, dict[str, float]]] = {2024: {}}

    # Add cells but not stream summaries
    for lay, row, col in ABOVE_OTOWI_CELLS + BELOW_OTOWI_CELLS:
        cell_key = f"{lay} {row} {col}"
        mock_data[2024][cell_key] = {m: 0.1 for m in months}

    with pytest.raises(KeyError, match="RIO GRANDE not found"):
        generate_table4_data(mock_data, 2024)


def test_print_table4_verification_exists():
    """Verify print_table4_verification function exists and is callable."""
    from stream_depletions import print_table4_verification
    assert callable(print_table4_verification)


def test_print_table4_verification_runs(capsys):
    """Verify print_table4_verification runs and prints expected output."""
    from stream_depletions import print_table4_verification

    # Create mock table4 data
    table4_data = {
        "cell_data": [
            {"key": 2107, "year": 2024, "lay": 1, "row": 1, "col": 16, "monthly_cfs": [0.1] * 12, "otowi": "above"},
        ] * 10 + [
            {"key": 2117, "year": 2024, "lay": 1, "row": 11, "col": 11, "monthly_cfs": [0.1] * 12, "otowi": "below"},
        ] * 16,
        "stream_summaries": {
            "RIO GRANDE": [2.6] * 12,
            "R POJOAQUE": [0.1] * 12,
        },
        "days_per_month": [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
        "above_otowi_cfs": [1.0] * 12,
        "below_otowi_cfs": [1.6] * 12,
        "above_otowi_af": [61.5] * 12,
        "below_otowi_af": [98.4] * 12,
        "above_otowi_annual_af": 276.5,
        "below_otowi_annual_af": 442.4,
        "total_rg_af": [159.9] * 12,
        "total_rg_annual_af": 718.9,
        "buckman_cfs": [0.5] * 12,
        "buckman_af": [30.0] * 12,
        "buckman_annual_af": 360.0,
    }

    print_table4_verification(table4_data, 2024)
    captured = capsys.readouterr()

    # Should contain key information
    assert "2024" in captured.out
    assert "Above Otowi" in captured.out
    assert "Below Otowi" in captured.out
    assert "Buckman" in captured.out
    assert "276.5" in captured.out or "276.500" in captured.out


# Note: Integration tests requiring actual files are skipped in smoke tests.
# The domain expert should run the full workflow and verify:
# 1. Post-processor output file is generated
# 2. Table 3 Pojoaque 2024 superposition matches validation
# 3. Table 4 Otowi Above/Below sums match validation
# 4. Table 5 La Cienega 2024 cumulative matches validation
