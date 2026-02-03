"""
Smoke tests for generate_depletion_tables module.

Verifies code RUNS - hydrologist must verify calculations independently.
Tests focus on:
- Module imports without errors
- Functions exist and are callable
- Basic functionality executes without crashes
"""

import pytest
import shutil
from pathlib import Path


def test_module_imports():
    """Verify module imports without syntax errors."""
    import generate_depletion_tables


def test_copy_flux_files_exists():
    """Verify copy_flux_files function exists and is callable."""
    from generate_depletion_tables import copy_flux_files
    assert callable(copy_flux_files)


def test_print_error_exists():
    """Verify print_error function exists and is callable."""
    from generate_depletion_tables import print_error
    assert callable(print_error)


def test_main_exists():
    """Verify main function exists and is callable."""
    from generate_depletion_tables import main
    assert callable(main)


def test_constants_defined():
    """Verify configuration constants are defined."""
    from generate_depletion_tables import (
        MODFLOW_OUTPUT_DIR,
        DEPLETIONS_DIR,
        OUTPUT_DIR,
        VALIDATION_DIR,
        YEAR,
        RIV_FLUX_FILE,
        GHB_FLUX_FILE,
    )
    assert YEAR == 2024
    assert RIV_FLUX_FILE == "CY2024_riv.flx"
    assert GHB_FLUX_FILE == "CY2024_ghb.flx"


def test_print_error_runs_without_crash(capsys):
    """Verify print_error executes with sample inputs."""
    from generate_depletion_tables import print_error

    print_error(
        "Test failure",
        "/path/to/file",
        "got 42",
        "expected 0",
        "Testing error message format"
    )

    captured = capsys.readouterr()
    assert "ERROR: Test failure" in captured.out
    assert "Location: /path/to/file" in captured.out


def test_copy_flux_files_returns_bool():
    """Verify copy_flux_files returns a boolean value."""
    from generate_depletion_tables import copy_flux_files

    # This test assumes the source files exist (integration test)
    # If files don't exist, function should still return a bool (False)
    result = copy_flux_files()
    assert isinstance(result, bool)
