# P7: Layer 0.5 — Pipeline Edge Case Testing Plan

## Overview

Implement input validation and edge case testing for the pipeline's Python code. These tests verify that the pipeline handles unexpected, malformed, or boundary-condition inputs correctly — either by processing them gracefully or failing with clear, diagnostic error messages.

**Key change from original P7:** Removed MODFLOW perturbation testing (54 hours compute, tests MODFLOW physics not our code). Edge case tests run in seconds and catch actual production failure modes.

See `P7_VERIFICATION_OMITTED.md` for documentation of the omitted perturbation testing framework and rationale.

## Why "Layer 0.5"

- **Layer 0:** Smoke tests (does code run?)
- **Layer 0.5:** Edge cases (does code handle bad input?) ← NEW
- **Layer 1:** Conservation checks (are physics constraints met?)

Edge case tests validate input handling BEFORE MODFLOW execution. They run in <30 seconds with no MODFLOW dependency.

---

## Directory Structure

```
tests/
├── test_edge_cases.py         # Main edge case test module (NEW)
├── test_conservation.py       # Existing Layer 1
├── test_update_modflow.py     # Existing
└── ...
```

No new subdirectories needed. Single flat test file.

---

## Test Categories

### 1. Input Validation Tests

```python
class TestInputValidation:
    """Verify pipeline handles malformed input files correctly."""

    def test_missing_input_file(self):
        """step1 with nonexistent CSV raises FileNotFoundError with path"""

    def test_empty_csv(self):
        """CSV with headers but no data rows produces clear error"""

    def test_malformed_csv_missing_columns(self):
        """CSV missing required column (e.g., 'BWell 5') identifies which column"""

    def test_csv_wrong_encoding(self):
        """Non-UTF-8 file either handled or rejected with encoding error"""

    def test_csv_with_extra_columns(self):
        """Extra columns ignored without crashing"""
```

### 2. Data Quality Tests

```python
class TestDataQuality:
    """Verify pipeline detects data quality issues."""

    def test_missing_days_in_input(self):
        """CSV with <365 rows produces warning with specific count"""

    def test_duplicate_dates(self):
        """Duplicate date entries detected and reported"""

    def test_out_of_order_dates(self):
        """Unsorted dates either handled or rejected with message"""

    def test_negative_pumping_value(self):
        """Negative MGD rejected as physically impossible"""

    def test_unreasonably_large_pumping(self):
        """Value >100 MGD flagged as likely data error"""

    def test_nan_values_in_input(self):
        """NaN/blank cells produce error identifying row/column"""
```

### 3. Boundary Condition Tests

```python
class TestBoundaryConditions:
    """Verify pipeline handles edge cases at valid input boundaries."""

    def test_zero_pumping_all_wells(self):
        """All wells = 0 for full year completes without error"""

    def test_zero_pumping_one_well(self):
        """Single well = 0 handled correctly in Table 2"""

    def test_single_day_of_pumping(self):
        """Only Jan 1 has data, rest = 0, monthly aggregation correct"""

    def test_leap_year_handling(self):
        """Leap year (366 days) vs non-leap (365) handled correctly"""

    def test_february_days(self):
        """Feb has 28 or 29 days depending on year"""
```

### 4. File Operation Tests

```python
class TestFileOperations:
    """Verify pipeline handles filesystem edge cases."""

    def test_output_directory_missing(self):
        """Missing output dir either created or clear error"""

    def test_output_file_exists(self):
        """Existing output file overwritten without error"""

    def test_input_file_permissions(self):
        """Unreadable input file produces permission error"""
```

### 5. WEL File Integrity Tests

```python
class TestWelFileIntegrity:
    """Verify step2 produces valid MODFLOW input format."""

    def test_wel_file_line_count(self):
        """Exactly 324 lines per year (12 months × 27 lines)"""

    def test_wel_file_crlf_endings(self):
        """Windows CRLF line endings for MODFLOW96 compatibility"""

    def test_wel_file_column_alignment(self):
        """Fixed-width columns match MODFLOW spec"""

    def test_well_name_mapping(self):
        """Well 3 maps to 'BUCKMAN 3A' (special case)"""

    def test_pumping_rate_sign(self):
        """All pumping rates negative (MODFLOW extraction convention)"""

    def test_layer_split(self):
        """Pumping split equally between Layer 1 and Layer 2"""
```

---

## Implementation Approach

### Test Fixtures

```python
@pytest.fixture
def sample_valid_csv(tmp_path):
    """Create minimal valid input CSV for testing."""
    ...

@pytest.fixture
def sample_csv_missing_column(tmp_path):
    """CSV missing BWell 5 column."""
    ...
```

### Parameterized Tests

```python
@pytest.mark.parametrize("bad_value,expected_error", [
    (-1.5, "negative pumping"),
    (float('nan'), "NaN value"),
    (999.9, "exceeds maximum"),
])
def test_invalid_pumping_values(bad_value, expected_error):
    ...
```

---

## Files to Create

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `tests/test_edge_cases.py` | All edge case tests | 300-400 |

## Files to Modify

| File | Change |
|------|--------|
| `pytest.ini` | Add marker: `edge_cases` |
| `step1_ingest_buckman_data.py` | Add input validation (if not present) |
| `step2_update_modflow.py` | Add input validation (if not present) |

---

## Acceptance Criteria

- [ ] All tests run without MODFLOW execution
- [ ] Complete in <30 seconds total
- [ ] Use pytest fixtures for test data (no hardcoded paths)
- [ ] Clear error messages identify: what failed, where, actual vs expected, how to fix
- [ ] All 5 test categories implemented
- [ ] Minimum 20 test cases total

---

## Success Criteria

1. [ ] `tests/test_edge_cases.py` exists with all test categories
2. [ ] All tests pass on valid 2024 input data
3. [ ] Invalid input produces clear, diagnostic errors
4. [ ] Tests run in <30 seconds
5. [ ] pytest marker `edge_cases` allows selective execution

---

## Implementation Order

1. Create `tests/test_edge_cases.py` with test class stubs
2. Implement fixtures for valid and invalid test data
3. Implement TestInputValidation (missing files, bad format)
4. Implement TestDataQuality (bad values, missing data)
5. Implement TestBoundaryConditions (zeros, leap year)
6. Implement TestFileOperations (permissions, existing files)
7. Implement TestWelFileIntegrity (format validation)
8. Add input validation to pipeline scripts if needed
9. Add pytest marker to pytest.ini
10. Run and verify all tests

---

## Runtime Comparison

| Approach | Runtime | MODFLOW Runs | Bugs Caught |
|----------|---------|--------------|-------------|
| Original P7 (perturbation) | ~54 hours | 72 | MODFLOW physics (already known) |
| **Revised P7 (edge cases)** | **<30 sec** | **0** | **Input handling, data quality, file format** |
