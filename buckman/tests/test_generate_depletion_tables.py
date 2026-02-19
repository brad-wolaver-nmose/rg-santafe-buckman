"""
Smoke tests for generate_depletion_tables module.

Verifies code RUNS - hydrologist must verify calculations independently.
Tests focus on:
- Module imports without errors
- Functions exist and are callable
- Basic functionality executes without crashes
"""


import pytest

# Apply Layer 0 marker to all tests in this file
pytestmark = pytest.mark.layer0


def test_module_imports():
    """Verify module imports without syntax errors."""


def test_copy_flux_files_exists():
    """Verify copy_flux_files function exists and is callable."""
    from step4_generate_depletion_tables import copy_flux_files
    assert callable(copy_flux_files)


def test_print_error_exists():
    """Verify print_error function exists and is callable."""
    from step4_generate_depletion_tables import print_error
    assert callable(print_error)


def test_main_exists():
    """Verify main function exists and is callable."""
    from step4_generate_depletion_tables import main
    assert callable(main)


def test_constants_defined():
    """Verify configuration constants are defined."""
    from step4_generate_depletion_tables import (
        GHB_FLUX_FILE,
        RIV_FLUX_FILE,
        YEAR,
    )
    assert YEAR == 2024
    assert RIV_FLUX_FILE == "CY2024_riv.flx"
    assert GHB_FLUX_FILE == "CY2024_ghb.flx"


def test_print_error_runs_without_crash(capsys):
    """Verify print_error executes with sample inputs."""
    from step4_generate_depletion_tables import print_error

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
    from step4_generate_depletion_tables import copy_flux_files

    # This test assumes the source files exist (integration test)
    # If files don't exist, function should still return a bool (False)
    result = copy_flux_files()
    assert isinstance(result, bool)


# =============================================================================
# US-002 Tests: Run Post-Processor via Wine
# =============================================================================


def test_check_wine_installed_exists():
    """Verify check_wine_installed function exists and is callable."""
    from step4_generate_depletion_tables import check_wine_installed
    assert callable(check_wine_installed)


def test_run_post_processor_exists():
    """Verify run_post_processor function exists and is callable."""
    from step4_generate_depletion_tables import run_post_processor
    assert callable(run_post_processor)


def test_us002_constants_defined():
    """Verify US-002 configuration constants are defined."""
    from step4_generate_depletion_tables import (
        OUTPUT_FILE_PREFIX,
        POST_PROCESSOR_EXE,
    )
    assert POST_PROCESSOR_EXE == "sfmodflx_2245.exe"
    assert OUTPUT_FILE_PREFIX == "CY2024"


def test_check_wine_installed_returns_bool():
    """Verify check_wine_installed returns a boolean value."""
    from step4_generate_depletion_tables import check_wine_installed
    result = check_wine_installed()
    assert isinstance(result, bool)


def test_run_post_processor_returns_bool():
    """Verify run_post_processor returns a boolean value."""
    from step4_generate_depletion_tables import run_post_processor
    # This will return True if Wine is installed and files exist,
    # or False with error messages if prerequisites missing
    result = run_post_processor()
    assert isinstance(result, bool)


# =============================================================================
# US-003 Tests: Parse Post-Processor Output Structure
# =============================================================================


def test_parse_post_processor_output_exists():
    """Verify parse_post_processor_output function exists and is callable."""
    from step4_generate_depletion_tables import parse_post_processor_output
    assert callable(parse_post_processor_output)


def test_us003_constants_defined():
    """Verify US-003 configuration constants are defined."""
    from step4_generate_depletion_tables import MONTH_NAMES
    assert len(MONTH_NAMES) == 12
    assert MONTH_NAMES[0] == "jan"
    assert MONTH_NAMES[11] == "dec"


def test_parse_post_processor_output_returns_dict():
    """Verify parse_post_processor_output returns a dict."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    assert isinstance(result, dict)


def test_parse_post_processor_output_has_years():
    """Verify parsed data contains year keys as integers."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    # If post-processor output exists, should have year data
    if result:
        # All keys should be integers (years)
        for key in result.keys():
            assert isinstance(key, int)
        # Should have 2024 if file exists
        assert 2024 in result


def test_parse_post_processor_output_has_stream_data():
    """Verify parsed data contains stream summary rows for 2024."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    if result and 2024 in result:
        year_data = result[2024]
        # Check expected stream names (normalized from source file)
        assert "R POJOAQUE" in year_data
        assert "R TESUQUE" in year_data
        assert "RIO GRANDE" in year_data
        assert "RIV TOTAL" in year_data  # Normalized from double space in source file
        assert "LC SPRINGS" in year_data


def test_parse_post_processor_output_has_monthly_values():
    """Verify parsed data contains all 12 months for streams."""
    from step4_generate_depletion_tables import MONTH_NAMES, parse_post_processor_output
    result = parse_post_processor_output()
    if result and 2024 in result:
        year_data = result[2024]
        if "R POJOAQUE" in year_data:
            stream_data = year_data["R POJOAQUE"]
            # Check all 12 months present
            for month in MONTH_NAMES:
                assert month in stream_data
                assert isinstance(stream_data[month], float)


def test_parse_post_processor_output_sample_values():
    """Verify parsed 2024 values match expected from file inspection."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    if result and 2024 in result:
        year_data = result[2024]
        # Values from grep of CY2024 file at line 2141-2145
        # R POJOAQUE jan: 0.083581
        if "R POJOAQUE" in year_data:
            assert abs(year_data["R POJOAQUE"]["jan"] - 0.083581) < 0.000001
        # R TESUQUE jan: 0.028195
        if "R TESUQUE" in year_data:
            assert abs(year_data["R TESUQUE"]["jan"] - 0.028195) < 0.000001
        # RIO GRANDE jan: 1.047860
        if "RIO GRANDE" in year_data:
            assert abs(year_data["RIO GRANDE"]["jan"] - 1.047860) < 0.000001
        # LC SPRINGS jan: 0.005030
        if "LC SPRINGS" in year_data:
            assert abs(year_data["LC SPRINGS"]["jan"] - 0.005030) < 0.000001


def test_parse_post_processor_output_has_cell_data():
    """Verify parsed data contains cell rows for 2024."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    if result and 2024 in result:
        year_data = result[2024]
        # Check for Buckman wells cell (1,13,11)
        assert "1 13 11" in year_data
        # Check for Above Otowi cell (1,1,16)
        assert "1 1 16" in year_data


def test_parse_post_processor_output_cell_sample_value():
    """Verify parsed cell value for Buckman wells matches file."""
    from step4_generate_depletion_tables import parse_post_processor_output
    result = parse_post_processor_output()
    if result and 2024 in result:
        year_data = result[2024]
        # Cell 1 13 11 (Buckman wells) jan value from line 2127: 0.400578
        if "1 13 11" in year_data:
            assert abs(year_data["1 13 11"]["jan"] - 0.400578) < 0.000001


# =============================================================================
# US-004 Tests: Extract 2024 Stream Depletions
# =============================================================================


def test_extract_stream_depletions_2024_exists():
    """Verify extract_stream_depletions_2024 function exists and is callable."""
    from step4_generate_depletion_tables import extract_stream_depletions_2024
    assert callable(extract_stream_depletions_2024)


def test_us004_constants_defined():
    """Verify US-004 configuration constants are defined."""
    from step4_generate_depletion_tables import STREAM_NAMES
    assert len(STREAM_NAMES) == 5
    assert "R POJOAQUE" in STREAM_NAMES
    assert "R TESUQUE" in STREAM_NAMES
    assert "RIO GRANDE" in STREAM_NAMES
    assert "RIV TOTAL" in STREAM_NAMES  # Normalized from double space in source file
    assert "LC SPRINGS" in STREAM_NAMES


def test_extract_stream_depletions_2024_returns_dict():
    """Verify extract_stream_depletions_2024 returns a dict."""
    from step4_generate_depletion_tables import (
        extract_stream_depletions_2024,
        parse_post_processor_output,
    )
    parsed_data = parse_post_processor_output()
    result = extract_stream_depletions_2024(parsed_data)
    assert isinstance(result, dict)


def test_extract_stream_depletions_2024_has_all_streams():
    """Verify result contains all 5 stream names."""
    from step4_generate_depletion_tables import (
        STREAM_NAMES,
        extract_stream_depletions_2024,
        parse_post_processor_output,
    )
    parsed_data = parse_post_processor_output()
    if parsed_data and 2024 in parsed_data:
        result = extract_stream_depletions_2024(parsed_data)
        for stream_name in STREAM_NAMES:
            assert stream_name in result


def test_extract_stream_depletions_2024_has_12_months():
    """Verify each stream has exactly 12 monthly values."""
    from step4_generate_depletion_tables import (
        extract_stream_depletions_2024,
        parse_post_processor_output,
    )
    parsed_data = parse_post_processor_output()
    if parsed_data and 2024 in parsed_data:
        result = extract_stream_depletions_2024(parsed_data)
        for stream_name, monthly_values in result.items():
            assert len(monthly_values) == 12, f"{stream_name} should have 12 months"
            for value in monthly_values:
                assert isinstance(value, float), "Values should be float"


def test_extract_stream_depletions_2024_sample_values():
    """Verify sample values match known values from post-processor output."""
    from step4_generate_depletion_tables import (
        extract_stream_depletions_2024,
        parse_post_processor_output,
    )
    parsed_data = parse_post_processor_output()
    if parsed_data and 2024 in parsed_data:
        result = extract_stream_depletions_2024(parsed_data)
        # R POJOAQUE jan: 0.083581 (index 0)
        assert abs(result["R POJOAQUE"][0] - 0.083581) < 0.000001
        # R TESUQUE jan: 0.028195 (index 0)
        assert abs(result["R TESUQUE"][0] - 0.028195) < 0.000001
        # RIO GRANDE jan: 1.047860 (index 0)
        assert abs(result["RIO GRANDE"][0] - 1.047860) < 0.000001
        # LC SPRINGS jan: 0.005030 (index 0)
        assert abs(result["LC SPRINGS"][0] - 0.005030) < 0.000001


def test_extract_stream_depletions_2024_empty_parsed_data():
    """Verify function handles empty parsed data gracefully."""
    from step4_generate_depletion_tables import extract_stream_depletions_2024
    result = extract_stream_depletions_2024({})
    assert result == {}


def test_extract_stream_depletions_2024_missing_year():
    """Verify function handles missing 2024 year gracefully."""
    from step4_generate_depletion_tables import extract_stream_depletions_2024
    # Create parsed data with wrong year
    fake_data = {2023: {"R POJOAQUE": {"jan": 0.1}}}
    result = extract_stream_depletions_2024(fake_data)
    assert result == {}


# =============================================================================
# US-015 Tests: Main Script Entry Point
# =============================================================================


def test_main_accepts_year_parameter():
    """Verify main function accepts year parameter."""
    import inspect

    from step4_generate_depletion_tables import main
    sig = inspect.signature(main)
    assert 'year' in sig.parameters
    # Default should be None (uses global YEAR)
    assert sig.parameters['year'].default is None


def test_main_returns_int():
    """Verify main returns an integer exit code."""
    import inspect

    from step4_generate_depletion_tables import main
    # Check return type annotation
    sig = inspect.signature(main)
    assert sig.return_annotation is int


def test_main_docstring_mentions_workflow_steps():
    """Verify main has docstring documenting workflow steps."""
    from step4_generate_depletion_tables import main
    assert main.__doc__ is not None
    assert "US-001" in main.__doc__
    assert "US-014" in main.__doc__
    assert "workflow" in main.__doc__.lower() or "Workflow" in main.__doc__
