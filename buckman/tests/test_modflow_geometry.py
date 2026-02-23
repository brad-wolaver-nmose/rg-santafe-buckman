#!/usr/bin/env python3
"""
Unit tests for MODFLOW geometry validation.

Tests verify that MODFLOW model geometry (cell locations) matches assumptions
hardcoded in FORTRAN post-processor (sfmodflx_2245.for).

Critical for:
- Detecting model geometry changes that would invalidate depletion calculations
- Ensuring GHB cells fall within FORTRAN extraction rectangle
- Preventing silent underestimation of La Cienega Springs depletions

See docs/MODFLOW_CELL_MAPPING.md for complete cell mapping documentation.

Author: Claude Code (Anthropic)
Date: 2026-02-19
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import stream_depletions as sd  # noqa: E402


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def ghb_file():
    """Path to GHB package file (baseline from 2023)."""
    return PROJECT_ROOT / "input" / "modflow" / "2023" / "thruCY2165.ghb"


@pytest.fixture
def fortran_row_range():
    """FORTRAN hardcoded row extraction range (sfmodflx_2245.for lines 223-228)."""
    return (28, 35)


@pytest.fixture
def fortran_col_range():
    """FORTRAN hardcoded column extraction range (sfmodflx_2245.for lines 223-228)."""
    return (10, 20)


# =============================================================================
# GHB FILE PARSING TESTS
# =============================================================================

def test_parse_ghb_file_exists(ghb_file):
    """Verify parse_ghb_file function exists and is callable."""
    assert hasattr(sd, "parse_ghb_file")
    assert callable(sd.parse_ghb_file)


def test_parse_ghb_file_returns_list(ghb_file):
    """Verify parse_ghb_file returns a list of tuples."""
    cells = sd.parse_ghb_file(ghb_file)
    assert isinstance(cells, list)
    assert len(cells) > 0
    assert all(isinstance(cell, tuple) for cell in cells)
    assert all(len(cell) == 3 for cell in cells)  # (layer, row, col)


def test_parse_ghb_file_expected_count(ghb_file):
    """Verify GHB file contains expected 6 cells for La Cienega Springs."""
    cells = sd.parse_ghb_file(ghb_file)
    assert len(cells) == 6, (
        f"Expected 6 GHB cells for La Cienega Springs, got {len(cells)}. "
        "If model geometry changed, update this test and FORTRAN extraction range."
    )


def test_parse_ghb_file_cell_coordinates(ghb_file):
    """Verify GHB cells have expected coordinates (layer 1, rows 30-32, cols 12-15)."""
    cells = sd.parse_ghb_file(ghb_file)

    # Expected cells from thruCY2165.ghb
    expected = [
        (1, 30, 14),
        (1, 31, 12),
        (1, 31, 14),
        (1, 31, 15),
        (1, 32, 13),
        (1, 32, 12),
    ]

    assert cells == expected, (
        f"GHB cell coordinates changed.\n"
        f"  Expected: {expected}\n"
        f"  Got: {cells}\n"
        "If this is intentional, update test_parse_ghb_file_cell_coordinates() "
        "and verify FORTRAN extraction range covers new cells."
    )


def test_parse_ghb_file_missing_file():
    """Verify parse_ghb_file raises FileNotFoundError for missing file."""
    nonexistent = Path("/tmp/does_not_exist.ghb")
    with pytest.raises(FileNotFoundError, match="GHB file not found"):
        sd.parse_ghb_file(nonexistent)


# =============================================================================
# GEOMETRY VALIDATION TESTS
# =============================================================================

def test_validate_ghb_cells_in_fortran_range_exists():
    """Verify validate_ghb_cells_in_fortran_range function exists."""
    assert hasattr(sd, "validate_ghb_cells_in_fortran_range")
    assert callable(sd.validate_ghb_cells_in_fortran_range)


def test_validate_ghb_cells_in_fortran_range_passes(ghb_file, fortran_row_range, fortran_col_range):
    """Verify all GHB cells fall within FORTRAN extraction rectangle (happy path)."""
    # Should not raise exception
    result = sd.validate_ghb_cells_in_fortran_range(
        ghb_file,
        fortran_row_range=fortran_row_range,
        fortran_col_range=fortran_col_range,
    )
    assert result is True


def test_validate_ghb_cells_all_in_layer_1(ghb_file):
    """Verify all GHB cells are in Layer 1 (top aquifer layer)."""
    cells = sd.parse_ghb_file(ghb_file)
    layers = {cell[0] for cell in cells}
    assert layers == {1}, (
        f"Expected all GHB cells in Layer 1, found layers: {layers}. "
        "If model now uses multiple layers, update validation logic."
    )


def test_validate_ghb_cells_spatial_extent(ghb_file):
    """Verify GHB cells span expected spatial extent (rows 30-32, cols 12-15)."""
    cells = sd.parse_ghb_file(ghb_file)

    rows = {cell[1] for cell in cells}
    cols = {cell[2] for cell in cells}

    # Actual GHB cells occupy rows 30-32
    assert min(rows) == 30
    assert max(rows) == 32

    # Actual GHB cells occupy columns 12-15
    assert min(cols) == 12
    assert max(cols) == 15


def test_validate_ghb_cells_within_fortran_buffer(ghb_file, fortran_row_range, fortran_col_range):
    """Verify GHB cells have buffer room within FORTRAN extraction rectangle."""
    cells = sd.parse_ghb_file(ghb_file)

    rows = {cell[1] for cell in cells}
    cols = {cell[2] for cell in cells}

    min_fortran_row, max_fortran_row = fortran_row_range
    min_fortran_col, max_fortran_col = fortran_col_range

    # Check buffer: how much room between actual cells and FORTRAN boundaries
    row_buffer_below = min(rows) - min_fortran_row  # 30 - 28 = 2 rows
    row_buffer_above = max_fortran_row - max(rows)  # 35 - 32 = 3 rows
    col_buffer_left = min(cols) - min_fortran_col   # 12 - 10 = 2 cols
    col_buffer_right = max_fortran_col - max(cols)  # 20 - 15 = 5 cols

    # Assert minimum buffer of 1 cell in each direction
    assert row_buffer_below >= 1, "GHB cells too close to FORTRAN lower row bound"
    assert row_buffer_above >= 1, "GHB cells too close to FORTRAN upper row bound"
    assert col_buffer_left >= 1, "GHB cells too close to FORTRAN left column bound"
    assert col_buffer_right >= 1, "GHB cells too close to FORTRAN right column bound"


def test_validate_ghb_cells_outside_range_raises_error(tmp_path):
    """Verify validation raises ValueError when cells are outside FORTRAN range."""
    # Create temporary GHB file with cell outside range
    temp_ghb = tmp_path / "test.ghb"
    temp_ghb.write_text(
        "   1    50\n"
        "#\n"
        "# LAY ROW COL     HEAD  CONDUCTANCE\n"
        "#\n"
        "    1  27  14  5449.0        100.0\n"  # Row 27 < 28 (outside FORTRAN range)
    )

    with pytest.raises(ValueError, match="GHB cell.* outside FORTRAN extraction rectangle"):
        sd.validate_ghb_cells_in_fortran_range(
            temp_ghb,
            fortran_row_range=(28, 35),
            fortran_col_range=(10, 20),
        )


def test_validate_ghb_cells_error_message_includes_solution(tmp_path):
    """Verify error message provides actionable solutions."""
    temp_ghb = tmp_path / "test.ghb"
    temp_ghb.write_text(
        "   1    50\n"
        "    1  27  14  5449.0        100.0\n"  # Outside range
    )

    with pytest.raises(ValueError) as exc_info:
        sd.validate_ghb_cells_in_fortran_range(temp_ghb)

    error_message = str(exc_info.value)

    # Check error message contains critical information
    assert "outside FORTRAN extraction rectangle" in error_message
    assert "row 27 not in" in error_message  # Identifies specific problem
    assert "CONSEQUENCE" in error_message    # Explains impact
    assert "SOLUTION" in error_message       # Provides fix options
    assert "docs/MODFLOW_CELL_MAPPING.md" in error_message  # Links to documentation


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_integration_ghb_validation_with_step4(ghb_file):
    """
    Integration test: Verify validation works in context of step4 workflow.

    This test simulates what step4_generate_depletion_tables.py does:
    1. Load GHB file from input/modflow/2023/
    2. Validate against FORTRAN hardcoded ranges
    3. Proceed only if validation passes
    """
    # This should pass without raising exceptions
    try:
        result = sd.validate_ghb_cells_in_fortran_range(ghb_file)
        assert result is True
    except (ValueError, FileNotFoundError) as e:
        pytest.fail(
            f"GHB validation failed in integration test: {e}\n"
            "This will cause step4_generate_depletion_tables.py to fail. "
            "See docs/MODFLOW_CELL_MAPPING.md for troubleshooting."
        )


def test_fortran_rectangle_oversizing():
    """
    Verify FORTRAN rectangle is intentionally oversized for safety buffer.

    FORTRAN extraction range (rows 28-35, cols 10-20) is larger than actual
    GHB cell extent (rows 30-32, cols 12-15). This provides buffer against
    minor model geometry changes.
    """
    # Actual GHB cell extent
    actual_row_extent = (30, 32)  # 3 rows
    actual_col_extent = (12, 15)  # 4 columns

    # FORTRAN extraction range
    fortran_row_range = (28, 35)  # 8 rows
    fortran_col_range = (10, 20)  # 11 columns

    # Calculate oversizing factor
    row_oversize_factor = (fortran_row_range[1] - fortran_row_range[0]) / (actual_row_extent[1] - actual_row_extent[0])
    col_oversize_factor = (fortran_col_range[1] - fortran_col_range[0]) / (actual_col_extent[1] - actual_col_extent[0])

    # FORTRAN rectangle should be at least 2x the actual cell extent
    assert row_oversize_factor >= 2.0, (
        f"FORTRAN row range not sufficiently oversized (factor={row_oversize_factor:.1f}x). "
        "Increase buffer to protect against model geometry changes."
    )
    assert col_oversize_factor >= 2.0, (
        f"FORTRAN column range not sufficiently oversized (factor={col_oversize_factor:.1f}x). "
        "Increase buffer to protect against model geometry changes."
    )


# =============================================================================
# DOCUMENTATION LINK TESTS
# =============================================================================

def test_modflow_cell_mapping_doc_exists():
    """Verify MODFLOW_CELL_MAPPING.md documentation file exists."""
    doc_path = PROJECT_ROOT / "docs" / "MODFLOW_CELL_MAPPING.md"
    assert doc_path.exists(), (
        "Documentation file docs/MODFLOW_CELL_MAPPING.md not found. "
        "This file is critical for understanding cell identification mechanism."
    )


def test_modflow_cell_mapping_doc_mentions_fortran_range():
    """Verify documentation explains FORTRAN hardcoded cell ranges."""
    doc_path = PROJECT_ROOT / "docs" / "MODFLOW_CELL_MAPPING.md"
    content = doc_path.read_text()

    # Check key concepts are documented
    assert "IS=28" in content, "FORTRAN row start range not documented"
    assert "IX=35" in content, "FORTRAN row end range not documented"
    assert "JS=10" in content, "FORTRAN column start range not documented"
    assert "JX=20" in content, "FORTRAN column end range not documented"
    assert "sfmodflx_2245.for" in content, "FORTRAN source file not mentioned"
    assert "La Cienega" in content or "LC SPRINGS" in content, "La Cienega Springs not documented"
