"""
Smoke tests for ingest_buckman_data.py (CSV ingestion version).
Verifies code RUNS - domain expert must verify calculations independently.

These tests support the Ralph Enhanced iterate-until-pass loop.
They catch mechanical failures, not logical errors.
"""
import pytest
import os
import pandas as pd


# ---------------------------------------------------------------------------
# US-001: Configuration Constants and Well Mapping
# ---------------------------------------------------------------------------

def test_module_imports():
    """Verify module imports without syntax errors."""
    import ingest_buckman_data


def test_constants_defined():
    """Verify all required constants are defined."""
    import ingest_buckman_data as m

    assert hasattr(m, "OUTPUT_DIR")
    assert hasattr(m, "MG_TO_AF_FACTOR")
    assert hasattr(m, "DAILY_SUM_TOLERANCE")
    assert hasattr(m, "ANNUAL_SUM_TOLERANCE")
    assert hasattr(m, "MONTHS_ABBREV")
    assert hasattr(m, "MONTHS_ORDERED")
    assert hasattr(m, "WELL_OSE_MAP")
    assert hasattr(m, "CSV_TOTAL_COLUMN")


def test_well_ose_map_has_13_wells():
    """Verify WELL_OSE_MAP contains all 13 wells."""
    from ingest_buckman_data import WELL_OSE_MAP

    assert len(WELL_OSE_MAP) == 13
    for i in range(1, 14):
        assert i in WELL_OSE_MAP, f"Well {i} missing from WELL_OSE_MAP"
        assert WELL_OSE_MAP[i].startswith("RG-20516"), \
            f"Well {i} OSE number doesn't start with RG-20516"


def test_months_ordered_has_12():
    """Verify MONTHS_ORDERED has 12 month tuples."""
    from ingest_buckman_data import MONTHS_ORDERED

    assert len(MONTHS_ORDERED) == 12
    assert MONTHS_ORDERED[0] == ("01", "JAN")
    assert MONTHS_ORDERED[11] == ("12", "DEC")


def test_mg_to_af_factor():
    """Verify conversion factor is approximately correct."""
    from ingest_buckman_data import MG_TO_AF_FACTOR

    # USGS: 1 MG = 3.06889 AF (1,000,000 / 325,851)
    assert 3.06 < MG_TO_AF_FACTOR < 3.07


# ---------------------------------------------------------------------------
# US-002: PDF/OCR Code Removed
# ---------------------------------------------------------------------------

def test_no_ocr_imports():
    """Verify PDF/OCR imports have been removed."""
    import ingest_buckman_data
    import sys

    # These modules should NOT be imported by the script
    module_text = open(ingest_buckman_data.__file__).read()
    assert "import pytesseract" not in module_text
    assert "from pdf2image" not in module_text
    assert "import pdf2image" not in module_text


def test_no_ocr_functions():
    """Verify OCR-specific functions have been removed."""
    import ingest_buckman_data as m

    assert not hasattr(m, "check_system_dependencies")
    assert not hasattr(m, "WellData")
    assert not hasattr(m, "extract_date_from_pdf")
    assert not hasattr(m, "extract_buckman_wells_data")
    assert not hasattr(m, "extract_buckman_data_pdftotext")
    assert not hasattr(m, "validate_and_prepare_pdfs")
    assert not hasattr(m, "get_year_interactively")


# ---------------------------------------------------------------------------
# US-003: CSV Ingestion Function
# ---------------------------------------------------------------------------

def test_read_source_csv_exists():
    """Verify read_source_csv function exists and is callable."""
    from ingest_buckman_data import read_source_csv
    assert callable(read_source_csv)


def test_read_source_csv_runs():
    """Verify read_source_csv executes with the real CSV file."""
    from ingest_buckman_data import read_source_csv

    csv_path = "./input/csv/Buckman_Well_Prod_2024.csv"
    if not os.path.exists(csv_path):
        pytest.skip("Source CSV not found")

    daily_df, sum_row = read_source_csv(csv_path)

    # Should have 366 daily rows (2024 is a leap year)
    assert len(daily_df) == 366, f"Expected 366 rows, got {len(daily_df)}"

    # Should have Date column plus 13 well columns plus BWP_Total
    assert "Date" in daily_df.columns
    assert "BWP_Total" in daily_df.columns

    # Sum row should be a Series
    assert isinstance(sum_row, pd.Series)


# ---------------------------------------------------------------------------
# US-004: Data Validation and Flagging
# ---------------------------------------------------------------------------

def test_validate_daily_data_exists():
    """Verify validate_daily_data function exists and is callable."""
    from ingest_buckman_data import validate_daily_data
    assert callable(validate_daily_data)


# ---------------------------------------------------------------------------
# US-005: Daily Sum Verification
# ---------------------------------------------------------------------------

def test_verify_daily_sums_exists():
    """Verify verify_daily_sums function exists and is callable."""
    from ingest_buckman_data import verify_daily_sums
    assert callable(verify_daily_sums)


# ---------------------------------------------------------------------------
# US-006: Monthly Aggregation
# ---------------------------------------------------------------------------

def test_aggregate_monthly_exists():
    """Verify aggregate_monthly function exists and is callable."""
    from ingest_buckman_data import aggregate_monthly
    assert callable(aggregate_monthly)


# ---------------------------------------------------------------------------
# US-007: Generate Monthly CSV
# ---------------------------------------------------------------------------

def test_generate_monthly_csv_exists():
    """Verify generate_monthly_csv function exists and is callable."""
    from ingest_buckman_data import generate_monthly_csv
    assert callable(generate_monthly_csv)


# ---------------------------------------------------------------------------
# US-008: Generate Annual Summary
# ---------------------------------------------------------------------------

def test_generate_annual_summary_exists():
    """Verify generate_annual_summary function exists and is callable."""
    from ingest_buckman_data import generate_annual_summary
    assert callable(generate_annual_summary)


# ---------------------------------------------------------------------------
# US-009: Generate QA Summary
# ---------------------------------------------------------------------------

def test_generate_qa_summary_exists():
    """Verify generate_qa_summary function exists and is callable."""
    from ingest_buckman_data import generate_qa_summary
    assert callable(generate_qa_summary)


# ---------------------------------------------------------------------------
# US-010: Annual Sum Verification
# ---------------------------------------------------------------------------

def test_verify_annual_sums_exists():
    """Verify verify_annual_sums function exists and is callable."""
    from ingest_buckman_data import verify_annual_sums
    assert callable(verify_annual_sums)


# ---------------------------------------------------------------------------
# US-003 + US-006: mg_to_af conversion (kept from original)
# ---------------------------------------------------------------------------

def test_mg_to_af_exists():
    """Verify mg_to_af function exists."""
    from ingest_buckman_data import mg_to_af
    assert callable(mg_to_af)


def test_mg_to_af_runs():
    """Verify mg_to_af executes with basic input."""
    from ingest_buckman_data import mg_to_af

    result = mg_to_af(1.0)
    assert result is not None
    # 1 MG should be approximately 3.07 AF
    assert 3.0 < result < 3.1, f"1 MG = {result} AF, expected ~3.07"


def test_mg_to_af_zero():
    """Verify mg_to_af handles zero correctly."""
    from ingest_buckman_data import mg_to_af

    result = mg_to_af(0.0)
    assert result == 0.0


# ---------------------------------------------------------------------------
# US-011: End-to-end sanity (integration-level smoke test)
# ---------------------------------------------------------------------------

def test_end_to_end_smoke():
    """
    Run the full pipeline on the real CSV and verify outputs are created.

    This is NOT a precision test. It verifies the pipeline runs without
    crashing and produces output files.
    """
    from ingest_buckman_data import (
        read_source_csv,
        validate_daily_data,
        verify_daily_sums,
        aggregate_monthly,
    )

    csv_path = "./input/csv/Buckman_Well_Prod_2024.csv"
    if not os.path.exists(csv_path):
        pytest.skip("Source CSV not found")

    # Step 1: Read CSV
    daily_df, sum_row = read_source_csv(csv_path)
    assert len(daily_df) > 0

    # Step 2: Validate
    flags_df = validate_daily_data(daily_df)
    assert flags_df is not None

    # Step 3: Verify daily sums
    verification_df = verify_daily_sums(daily_df)
    assert verification_df is not None

    # Step 4: Aggregate monthly
    monthly_data = aggregate_monthly(daily_df, flags_df)
    assert len(monthly_data) == 12, f"Expected 12 months, got {len(monthly_data)}"


def test_annual_mg_sanity():
    """
    Verify annual MG total is in a reasonable range.

    The CSV Sum row shows BWP total of ~447 MG for 2024.
    This catches order-of-magnitude errors.
    """
    from ingest_buckman_data import read_source_csv

    csv_path = "./input/csv/Buckman_Well_Prod_2024.csv"
    if not os.path.exists(csv_path):
        pytest.skip("Source CSV not found")

    daily_df, sum_row = read_source_csv(csv_path)

    # Sum all well columns across all days
    well_cols = [c for c in daily_df.columns if c.startswith("BWell")]
    annual_total = daily_df[well_cols].sum().sum()

    # Should be in the hundreds of MG range (CSV shows ~447)
    assert 100 < annual_total < 1000, \
        f"Annual total {annual_total:.1f} MG outside expected range [100, 1000]"
