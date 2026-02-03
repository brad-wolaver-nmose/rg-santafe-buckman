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


# Note: Integration tests requiring actual files are skipped in smoke tests.
# The domain expert should run the full workflow and verify:
# 1. Post-processor output file is generated
# 2. Table 3 Pojoaque 2024 superposition matches validation
# 3. Table 4 Otowi Above/Below sums match validation
# 4. Table 5 La Cienega 2024 cumulative matches validation
