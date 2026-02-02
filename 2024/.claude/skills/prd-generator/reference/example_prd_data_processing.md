# Example PRD: Data Processing Script

Here's an example PRD for a data processing project, showing code quality stories:

```markdown
# PRD: Monthly Sales Data Aggregator

## Introduction

Process monthly CSV files from multiple sources, validate data integrity, and generate consolidated reports with error tracking.

## Goals

- Aggregate sales data from 12 monthly CSV files
- Validate data consistency (totals, date ranges, SKU formats)
- Generate annual summary with flagged discrepancies
- Provide clear progress feedback during processing
- Handle missing or corrupted files gracefully

## User Stories

### US-001: Read and parse monthly CSV files
**Description:** As a developer, I need to read CSV files for each month so data can be processed.

**Acceptance Criteria:**
- [ ] Function accepts file path and returns DataFrame
- [ ] Parse columns: date, SKU, quantity, price, total
- [ ] Return None if file missing or unreadable (don't crash)
- [ ] Log warning for missing files
- [ ] Typecheck passes

### US-002: Validate individual row data
**Description:** As a user, I need each row validated so errors are caught early.

**Acceptance Criteria:**
- [ ] Check date format matches expected pattern (YYYY-MM-DD)
- [ ] Check SKU matches format (3 letters + 4 digits)
- [ ] Check quantity and price are positive numbers
- [ ] Check total = quantity × price (within 0.01 tolerance)
- [ ] Return validation status: OK | NOT_OK with reason
- [ ] Typecheck passes

### US-003: Aggregate data across all months
**Description:** As a user, I want all 12 months aggregated so I can see annual totals.

**Acceptance Criteria:**
- [ ] Process all files in input/ directory matching pattern YYYY_MM_*.csv
- [ ] Combine validated rows into single DataFrame
- [ ] Track validation failures per month
- [ ] Return (aggregated_df, validation_report) tuple
- [ ] Typecheck passes
- [ ] Run script end-to-end with sample data successfully

### US-004: Generate annual summary CSV
**Description:** As a user, I want a summary CSV with totals and validation status.

**Acceptance Criteria:**
- [ ] Create output/ directory if not exists
- [ ] Generate summary_YYYY.csv with: month, total_sales, row_count, validation_errors
- [ ] Sort by month (Jan-Dec)
- [ ] Include grand total row at bottom
- [ ] Typecheck passes

### US-005: Configuration Constants
**Description:** As a developer, I need configuration values defined as constants for maintainability.

**Acceptance Criteria:**
- [ ] Define SKU_PATTERN = r"[A-Z]{3}\d{4}"
- [ ] Define DATE_FORMAT = "%Y-%m-%d"
- [ ] Define PRICE_TOLERANCE = 0.01
- [ ] Define INPUT_DIR = "./input"
- [ ] Define OUTPUT_DIR = "./output"
- [ ] All hardcoded values replaced with constants
- [ ] Constants grouped at module level with comments
- [ ] Typecheck passes

### US-006: Enhanced Error Messages
**Description:** As a developer, I need detailed error messages for debugging file and parsing issues.

**Acceptance Criteria:**
- [ ] File errors include full file path
- [ ] Parse errors include row number and problematic value
- [ ] Validation errors include field name and expected format
- [ ] All exceptions print exception type and message
- [ ] Typecheck passes

### US-007: Atomic File Writes
**Description:** As a developer, I need output files written atomically to prevent corruption.

**Acceptance Criteria:**
- [ ] Write CSV to temporary file first
- [ ] Atomically move temp file to final destination
- [ ] No partial files remain if script interrupted
- [ ] Typecheck passes

### US-008: Progress Feedback
**Description:** As a user, I need progress indicators so I know processing status.

**Acceptance Criteria:**
- [ ] Display "(X/12) Processing: YYYY_MM_file.csv..." for each file
- [ ] Show validation summary after each file
- [ ] Display final summary with total rows processed and error count
- [ ] Typecheck passes

## Smoke Test File: test_sales_aggregator.py

Created alongside PRD to support Ralph Enhanced verification loop.

```python
"""
Smoke tests for sales_aggregator module.
Verifies code RUNS - user must verify calculations independently.

These tests support the Ralph Enhanced iterate-until-pass loop.
They catch mechanical failures, not logical errors.
"""
import pytest
import os


def test_module_imports():
    """Verify module imports without syntax errors."""
    import sales_aggregator


def test_parse_csv_exists():
    """Verify parse function exists."""
    from sales_aggregator import parse_monthly_csv
    assert callable(parse_monthly_csv)


def test_validate_row_exists():
    """Verify validation function exists."""
    from sales_aggregator import validate_row
    assert callable(validate_row)


def test_validate_row_runs():
    """Verify validate_row executes without crashing."""
    from sales_aggregator import validate_row

    # Simple valid row - realistic but not edge case
    test_row = {
        'date': '2024-01-15',
        'SKU': 'ABC1234',
        'quantity': 10,
        'price': 5.00,
        'total': 50.00
    }

    result = validate_row(test_row)
    assert result is not None
    # Should return tuple of (bool, str)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_aggregate_returns_tuple():
    """Verify aggregate function returns expected structure."""
    from sales_aggregator import aggregate_all_months

    # This may return empty results if no test files exist
    # We're just checking it doesn't crash and returns right type
    result = aggregate_all_months('./test_input/')

    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2  # (dataframe, validation_report)
```

## Non-Goals

- No database integration (CSV only)
- No automatic file download or fetching
- No email notifications
- No GUI interface (CLI only)

## Technical Considerations

### Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| SKU_PATTERN | `r"[A-Z]{3}\d{4}"` | Regex for valid SKU format |
| DATE_FORMAT | `"%Y-%m-%d"` | Expected date string format |
| PRICE_TOLERANCE | 0.01 | Tolerance for total = qty × price check |
| INPUT_DIR | `"./input"` | Directory containing monthly CSVs |
| OUTPUT_DIR | `"./output"` | Directory for generated reports |

### Error Handling Patterns

- Use atomic file writes (tempfile + shutil.move) for all outputs
- Return None from parse functions instead of raising exceptions
- Collect validation errors; don't stop on first error
- Log all issues to stderr; successful operations to stdout

### Helper Functions

```python
def validate_row(row: dict) -> Tuple[bool, str]:
    """
    Validate a single data row.

    Returns:
        (is_valid, error_message)
        If valid: (True, "")
        If invalid: (False, "reason for failure")
    """
```
```
