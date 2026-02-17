# P7: Layer 0.5 — Pipeline Edge Case Testing Output

**Execution Date:** 2026-02-17
**Status:** PASSED

---

## Summary

Implemented Layer 0.5 edge case testing for the Buckman Wellfield pipeline. All 30 tests pass in <1 second with no MODFLOW dependency.

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_edge_cases.py` | 455 | All edge case tests (5 categories + integration) |

## Files Modified

| File | Change |
|------|--------|
| `pytest.ini` | Added `edge_cases` marker |

---

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-9.0.2
rootdir: /home/bradwolaver/projects/rg/santafe/buckman
configfile: pytest.ini

tests/test_edge_cases.py::TestInputValidation::test_missing_input_file_step2 PASSED
tests/test_edge_cases.py::TestInputValidation::test_empty_csv_step2 PASSED
tests/test_edge_cases.py::TestInputValidation::test_csv_missing_well_step2 PASSED
tests/test_edge_cases.py::TestInputValidation::test_csv_with_extra_columns PASSED
tests/test_edge_cases.py::TestInputValidation::test_missing_wel_file_step2 PASSED
tests/test_edge_cases.py::TestDataQuality::test_negative_pumping_value PASSED
tests/test_edge_cases.py::TestDataQuality::test_negative_rate_conversion PASSED
tests/test_edge_cases.py::TestDataQuality::test_invalid_days_in_month PASSED
tests/test_edge_cases.py::TestDataQuality::test_nan_in_dataframe PASSED
tests/test_edge_cases.py::TestDataQuality::test_unreasonably_large_pumping PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_zero_pumping_all_wells PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_zero_pumping_one_well PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_leap_year_february_days PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_non_leap_year_february_days PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_year_config_leap_year PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_conversion_zero_acre_feet PASSED
tests/test_edge_cases.py::TestBoundaryConditions::test_very_small_pumping_value PASSED
tests/test_edge_cases.py::TestFileOperations::test_output_directory_created PASSED
tests/test_edge_cases.py::TestFileOperations::test_output_file_overwrite PASSED
tests/test_edge_cases.py::TestFileOperations::test_unreadable_input_file PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_generate_well_entries_line_count PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_wel_file_crlf_endings PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_wel_file_column_alignment PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_well_name_mapping_well3 PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_pumping_rate_sign_negative PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_layer_split_two_entries PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_well_grid_mapping PASSED
tests/test_edge_cases.py::TestWelFileIntegrity::test_month_header_format PASSED
tests/test_edge_cases.py::TestIntegration::test_full_step2_pipeline_with_valid_data PASSED
tests/test_edge_cases.py::TestIntegration::test_conversion_roundtrip_consistency PASSED

============================== 30 passed in 0.31s ==============================
```

---

## Test Categories Breakdown

### 1. TestInputValidation (5 tests)
- Missing input files produce `FileNotFoundError` with path
- Empty CSV produces clear error
- Missing well column detected
- Extra columns ignored gracefully
- Missing .wel file produces error

### 2. TestDataQuality (5 tests)
- Negative pumping values rejected
- Negative acre-feet conversion rejected
- Invalid days_in_month (0 or >31) rejected
- NaN values in data detected
- Large values accepted (no current max limit - documented)

### 3. TestBoundaryConditions (7 tests)
- Zero pumping for all wells handled
- Zero pumping for single well handled
- Leap year February (29 days) correct
- Non-leap year February (28 days) correct
- YearConfig leap year detection
- Zero acre-feet conversion
- Very small pumping values

### 4. TestFileOperations (3 tests)
- Missing output directory created automatically
- Existing output file overwritten
- Unreadable input file produces PermissionError

### 5. TestWelFileIntegrity (8 tests)
- 324 lines per year (12 months x 27 lines)
- CRLF line endings for MODFLOW96
- Fixed-width column alignment
- Well 3 maps to "BUCKMAN 3A"
- Pumping rates are negative (MODFLOW convention)
- Layer 1 and Layer 2 entries present
- Grid coordinates valid for all wells
- Month header format correct

### 6. TestIntegration (2 tests)
- Full step2 pipeline runs on valid data
- Conversion consistency across wells/months

---

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| All tests run without MODFLOW execution | PASSED |
| Complete in <30 seconds total | PASSED (0.31s) |
| Use pytest fixtures for test data | PASSED |
| Clear error messages | PASSED |
| All 5 test categories implemented | PASSED |
| Minimum 20 test cases total | PASSED (30 tests) |

---

## Success Criteria Status

| Criterion | Status |
|-----------|--------|
| `tests/test_edge_cases.py` exists with all test categories | PASSED |
| All tests pass on valid input data | PASSED |
| Invalid input produces clear errors | PASSED |
| Tests run in <30 seconds | PASSED (0.31s) |
| pytest marker `edge_cases` allows selective execution | PASSED |

---

## Usage

```bash
# Run all edge case tests
pytest tests/test_edge_cases.py -v

# Run with marker filter
pytest tests/test_edge_cases.py -v -m edge_cases

# Quick check
pytest tests/test_edge_cases.py --tb=short
```

---

## Notes

1. **No pipeline script modifications required** - The existing `step2_update_modflow.py` already has sufficient input validation for:
   - Missing files
   - Negative pumping values
   - Missing wells
   - Invalid days_in_month

2. **Documentation gap identified**: Large pumping values (>100 MGD) are accepted without warning. This is documented but not enforced.

3. **Test runtime**: 0.31 seconds vs. original P7 perturbation approach (~54 hours)

---

## Runtime Comparison

| Approach | Runtime | MODFLOW Runs | Coverage |
|----------|---------|--------------|----------|
| Original P7 (perturbation) | ~54 hours | 72 | MODFLOW physics |
| **Implemented P7 (edge cases)** | **0.31 sec** | **0** | **Input handling, data quality, file format** |
