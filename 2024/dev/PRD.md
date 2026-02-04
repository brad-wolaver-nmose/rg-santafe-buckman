# PRD: Stream Depletion Tables from MODFLOW Post-Processor

## Introduction

Process MODFLOW binary output files (CY2024_ghb.flx and CY2024_riv.flx) using the sfmodflx_2245 post-processor to generate stream depletion tables for the 2024 Buckman Well Field annual report. The post-processor calculates depletions to Rio Grande, tributaries (Rio Pojoaque, Rio Tesuque), and La Cienega Springs. Output tables (Tables 3, 4, 5) report depletions in acre-feet, combining superposition model results with analytical model residuals from Core (2003).

## Goals

- Run sfmodflx_2245.exe post-processor via Wine to generate depletion summary file
- Parse post-processor output to extract 2024 monthly depletions by stream/cell
- Combine superposition model results with Core (2003) analytical model residuals
- Convert cubic feet per second (cfs) to acre-feet using actual days per month
- Generate Table 3 (Rio Pojoaque-Nambe & Rio Tesuque) as formatted XLSX
- Generate Table 4 (Rio Grande above/below Otowi) as formatted XLSX
- Generate Table 5 (La Cienega Springs) as formatted XLSX
- Validate generated tables against provided validation files
- Save outputs to `output/depletion/` directory

## Module Structure

**CRITICAL:** If smoke tests import from a module, that module file MUST exist before tests run. Create module stubs with required constants/functions so tests fail on assertions, not `ModuleNotFoundError`.

| Module | Test File | Purpose |
|--------|-----------|---------|
| `generate_depletion_tables.py` | `tests/test_generate_depletion_tables.py` | Main entry point, orchestrates workflow |
| `stream_depletions.py` | `tests/test_stream_depletions.py` | Core calculations, constants, unit conversion |

**Module stub must include:** All constants and function signatures that tests import. Function bodies can be stubs (`pass` or `return {}`) until implemented.

## User Stories

### US-001: Copy Flux Files to Post-Processor Directory
**Description:** As a developer, I need to copy the MODFLOW flux files to the post-processor directory so sfmodflx_2245.exe can access them.

**Acceptance Criteria:**
- [x] Copy `output/modflow/2024/modflow/CY2024_riv.flx` to `output/modflow/2024/depletions/`
- [x] Copy `output/modflow/2024/modflow/CY2024_ghb.flx` to `output/modflow/2024/depletions/`
- [x] Verify both files exist after copy
- [x] Print confirmation message with file sizes
- [x] If source files not found, print forensic error message and exit
- [x] Typecheck passes

### US-002: Run Post-Processor via Wine
**Description:** As a developer, I need to execute sfmodflx_2245.exe via Wine with automated input so the depletion summary is generated.

**Acceptance Criteria:**
- [x] Check if Wine is installed; print installation instructions if missing
- [x] Change working directory to `output/modflow/2024/depletions/`
- [x] Run `wine sfmodflx_2245.exe` via subprocess
- [x] Pipe three inputs via stdin: "CY2024_riv.flx\nCY2024_ghb.flx\nCY2024\n"
- [x] Capture stdout/stderr for debugging
- [x] Verify output file `CY2024` is created
- [x] If Wine fails, print forensic error with command, exit code, and stderr
- [x] Typecheck passes

### US-003: Parse Post-Processor Output Structure
**Description:** As a developer, I need to understand and parse the sfmodflx_2245 output file structure so I can extract depletion data.

**Acceptance Criteria:**
- [x] Read the `CY2024` output file as text
- [x] Identify year blocks by "YEAR: NNNN" header pattern
- [x] Identify column headers: jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec
- [x] Parse cell rows with format: "LAY ROW COL" followed by 12 monthly values (cfs)
- [x] Parse stream summary rows: "R POJOAQUE", "R TESUQUE", "RIO GRANDE", "RIV TOTAL", "LC SPRINGS"
- [x] Store parsed data in nested dict: `{year: {identifier: {month: value_cfs}}}`
- [x] Print count of years parsed and sample 2024 values for verification
- [x] Typecheck passes

### US-004: Extract 2024 Stream Depletions
**Description:** As a developer, I need to extract the 2024 monthly depletions for each stream and spring category.

**Acceptance Criteria:**
- [x] Extract "R POJOAQUE" 12 monthly values for 2024 (cfs)
- [x] Extract "R TESUQUE" 12 monthly values for 2024 (cfs)
- [x] Extract "RIO GRANDE" 12 monthly values for 2024 (cfs)
- [x] Extract "RIV TOTAL" 12 monthly values for 2024 (cfs)
- [x] Extract "LC SPRINGS" 12 monthly values for 2024 (cfs)
- [x] Store in dict: `stream_depletions_2024 = {stream_name: [jan, feb, ..., dec]}`
- [x] Print extracted values for verification
- [x] Typecheck passes

### US-005: Extract 2024 Model Cell Depletions for Otowi
**Description:** As a developer, I need to extract and aggregate model cell depletions for Rio Grande above and below Otowi Gage.

**Acceptance Criteria:**
- [x] Define Above Otowi cells: (1,1,16), (1,2,16), (1,3,16), (1,4,16), (1,5,15), (1,6,14), (1,7,14), (1,8,13), (1,9,13), (1,10,12)
- [x] Define Below Otowi cells: (1,11,11), (1,12,11), (1,13,11), (1,14,10), (1,15,9), (1,15,10), (1,16,9), (1,17,8), (1,18,6), (1,18,7), (1,19,6), (1,20,5), (1,21,4), (1,21,5), (1,22,4), (1,23,3)
- [x] Extract 2024 monthly values for each cell (cfs)
- [x] Sum Above Otowi cells for each month
- [x] Sum Below Otowi cells for each month
- [x] Store: `otowi_above_cfs = [jan, ..., dec]`, `otowi_below_cfs = [jan, ..., dec]`
- [x] Print aggregated sums for verification
- [x] Typecheck passes

### US-006: Load Core (2003) Analytical Model Residuals
**Description:** As a developer, I need to load the analytical model residual values from the Core (2003) projection table for combining with superposition results.

**Acceptance Criteria:**
- [ ] Define CORE_2003_POJOAQUE dict with values from PDF table (1988-2015, then 0)
- [ ] Define CORE_2003_TESUQUE dict with values from PDF table (1988-2050+)
- [ ] Values are annual acre-feet (already in correct units)
- [ ] For Pojoaque years after 2015: value = 0 (or use formula if value > 0)
- [ ] For Tesuque: use tabulated values through 2050
- [ ] Function `get_analytical_residual(stream, year)` returns value or 0 if not applicable
- [ ] Print 2024 residual values for both streams
- [ ] Typecheck passes

### US-007: Convert CFS to Acre-Feet
**Description:** As a developer, I need to convert monthly cfs values to acre-feet using actual days per month.

**Acceptance Criteria:**
- [ ] Define DAYS_PER_MONTH for 2024: [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] (leap year)
- [ ] Conversion: acre_feet = cfs * days * 86400 / 43560 = cfs * days * 1.9835
- [ ] Function `cfs_to_af(cfs_value, month_index)` returns acre-feet
- [ ] Function `cfs_monthly_to_af_annual(cfs_list)` converts 12 monthly cfs to annual AF total
- [ ] Include docstring with unit derivation
- [ ] Typecheck passes

### US-008: Generate Table 3 Data
**Description:** As a developer, I need to combine analytical residuals with superposition results to create Table 3 data structure.

**Acceptance Criteria:**
- [ ] For Rio Pojoaque-Nambe column:
  - [ ] Get 2024 analytical residual from Core (2003): 0 (Pojoaque residual ended 2015)
  - [ ] Get 2024 superposition impact: sum of R POJOAQUE monthly cfs → convert to AF
  - [ ] Total Impact = Residual + Superposition
- [ ] For Rio Tesuque column:
  - [ ] Get 2024 analytical residual from Core (2003): 12.877 AF
  - [ ] Get 2024 superposition impact: sum of R TESUQUE monthly cfs → convert to AF
  - [ ] Total Impact = Residual + Superposition
- [ ] Store as dict matching Table 3 structure
- [ ] Print calculated values for verification
- [ ] Typecheck passes

### US-009: Generate Table 4 Data
**Description:** As a developer, I need to create Table 4 data structure with cell-level and aggregated Rio Grande depletions.

**Acceptance Criteria:**
- [ ] Create detailed cell data section (rows 1-44 in validation):
  - [ ] Each Otowi cell: KEY, YEAR, LAY, ROW, COL, 12 monthly cfs values, "above"/"below" label
- [ ] Create stream summary section:
  - [ ] RIO GRANDE, R POJOAQUE, LC SPRINGS, R TESUQUE, RIV TOTAL rows with monthly cfs
- [ ] Create calculation section:
  - [ ] Row with days per month: [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  - [ ] Rio Grande above Otowi: sum of above cells (cfs), then convert to AF
  - [ ] Rio Grande below Otowi: sum of below cells (cfs), then convert to AF
  - [ ] Total RG (sum): above + below AF with annual total
  - [ ] Total RG reported: RIO GRANDE converted to AF (for cross-check)
  - [ ] Buckman 1,7,8 wells (Row 13, Col 11): cell (1,13,11) monthly AF with annual total
- [ ] Typecheck passes

### US-010: Generate Table 5 Data
**Description:** As a developer, I need to create Table 5 data structure for La Cienega Springs cumulative depletions.

**Acceptance Criteria:**
- [ ] Get LC SPRINGS 2024 monthly cfs values
- [ ] Convert to annual acre-feet total
- [ ] Add to cumulative total from previous years (2004-2023)
- [ ] Load previous cumulative totals from validation file pattern
- [ ] Structure: Year, Annual Total (AF), Cumulative Total (AF)
- [ ] For 2024: calculate annual from monthly, add to 2023 cumulative
- [ ] Print 2024 annual and cumulative values
- [ ] Typecheck passes

### US-011: Write Table 3 XLSX with Formatting
**Description:** As a developer, I need to write Table 3 as a formatted Excel file matching the validation format.

**Acceptance Criteria:**
- [ ] Create workbook with openpyxl
- [ ] Column headers: Year, Rio Pojoaque-Nambe (3 sub-columns), Rio Tesuque (3 sub-columns)
- [ ] Sub-columns: Residual Impact (Analytical), Impact of 1988-2024 Pumping (Superposition), Total Impact
- [ ] Write data rows for years 1988-2030 (or as in validation)
- [ ] Apply formatting: Font (Aptos 11), alignment, number format (#,##0.000000)
- [ ] Apply borders matching validation file pattern
- [ ] Save to `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx`
- [ ] Typecheck passes

### US-012: Write Table 4 XLSX with Formatting
**Description:** As a developer, I need to write Table 4 as a formatted Excel file matching the validation format.

**Acceptance Criteria:**
- [ ] Create workbook with openpyxl
- [ ] Write cell detail section (KEY, YEAR, LAY, ROW, COL, JAN-DEC, Otowi label)
- [ ] Write stream summary section (RIO GRANDE, R POJOAQUE, etc.)
- [ ] Write calculation section with days row, cfs-to-AF conversions
- [ ] Write summary rows: Above Otowi AF, Below Otowi AF, Total, Buckman wells
- [ ] Apply formatting matching validation file
- [ ] Include formulas for SUM calculations where appropriate
- [ ] Save to `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx`
- [ ] Typecheck passes

### US-013: Write Table 5 XLSX with Formatting
**Description:** As a developer, I need to write Table 5 as a formatted Excel file matching the validation format.

**Acceptance Criteria:**
- [ ] Create workbook with openpyxl
- [ ] Column headers: Year, Total (cumulative AF)
- [ ] Write rows for years 2004-2030 (or as in validation)
- [ ] Apply formatting: Font, alignment, number format (#,##0.00)
- [ ] Apply borders matching validation file pattern
- [ ] Save to `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx`
- [ ] Typecheck passes

### US-014: Validate Generated Tables Against Validation Files
**Description:** As a developer, I need to compare generated 2024 values against validation files to verify accuracy.

**Acceptance Criteria:**
- [ ] Load validation Table 3 XLSX, extract 2024 row values
- [ ] Load validation Table 4 XLSX, extract 2024 calculation section (rows 55-59)
- [ ] Load validation Table 5 (from image data), extract 2024 value
- [ ] Compare generated values to validation values
- [ ] Tolerance: 0.01 AF for totals, 0.000001 cfs for monthly values
- [ ] Print comparison table to console:
  ```
  === VALIDATION RESULTS ===
  Table 3 - Rio Pojoaque-Nambe:
    Superposition: calc=60.797, valid=60.797, diff=0.000 [OK]
    Total Impact:  calc=60.797, valid=60.797, diff=0.000 [OK]
  Table 3 - Rio Tesuque:
    Residual:      calc=12.877, valid=12.877, diff=0.000 [OK]
    ...
  ```
- [ ] If any NOT_OK, print detailed forensic error
- [ ] Return validation status dict
- [ ] Typecheck passes

### US-015: Main Script Entry Point
**Description:** As a developer, I need a main entry point that orchestrates the complete workflow.

**Acceptance Criteria:**
- [ ] Parse command-line argument for year (default: 2024)
- [ ] Create output directory `output/depletion/` if not exists
- [ ] Execute workflow steps in order:
  1. Copy flux files (US-001)
  2. Run post-processor (US-002)
  3. Parse output (US-003)
  4. Extract stream depletions (US-004)
  5. Extract Otowi cells (US-005)
  6. Load Core (2003) residuals (US-006)
  7. Generate Table 3 data (US-008)
  8. Generate Table 4 data (US-009)
  9. Generate Table 5 data (US-010)
  10. Write Table 3 XLSX (US-011)
  11. Write Table 4 XLSX (US-012)
  12. Write Table 5 XLSX (US-013)
  13. Validate (US-014)
- [ ] Print final summary with file paths and validation status
- [ ] Return exit code 0 if all validations pass, 1 otherwise
- [ ] Typecheck passes

## Non-Goals

- No GUI interface (CLI only)
- No automatic MODFLOW model execution (flux files already generated)
- No modification of source flux files
- No generation of Tables 1 or 2 (handled by ingest_buckman_data.py)
- No historical year reprocessing (2024 only for this workflow)
- No PDF report generation (tables only)

## Technical Considerations

### Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| MODFLOW_OUTPUT_DIR | `output/modflow/2024/modflow/` | Location of MODFLOW binary output |
| DEPLETIONS_DIR | `output/modflow/2024/depletions/` | Location of post-processor and output |
| OUTPUT_DIR | `output/depletion/` | Location for generated XLSX tables |
| VALIDATION_DIR | `validation/` | Location of validation files |
| YEAR | 2024 | Processing year |
| DAYS_2024 | [31,29,31,30,31,30,31,31,30,31,30,31] | Days per month (leap year) |

### Otowi Gage Cell Definitions

```python
ABOVE_OTOWI_CELLS = [
    (1, 1, 16), (1, 2, 16), (1, 3, 16), (1, 4, 16), (1, 5, 15),
    (1, 6, 14), (1, 7, 14), (1, 8, 13), (1, 9, 13), (1, 10, 12)
]

BELOW_OTOWI_CELLS = [
    (1, 11, 11), (1, 12, 11), (1, 13, 11), (1, 14, 10), (1, 15, 9),
    (1, 15, 10), (1, 16, 9), (1, 17, 8), (1, 18, 6), (1, 18, 7),
    (1, 19, 6), (1, 20, 5), (1, 21, 4), (1, 21, 5), (1, 22, 4), (1, 23, 3)
]

BUCKMAN_WELLS_CELL = (1, 13, 11)  # Row 13, Column 11 - Buckman 1, 7, 8
```

### Core (2003) Analytical Model Residuals

```python
# Rio Pojoaque-Nambe: decreasing residuals from 1972-1987 pumping
# Values from Core (2003) PROJECTION.XLS, ends ~2015
CORE_2003_POJOAQUE = {
    1988: 40.432, 1989: 39.244, 1990: 37.971, 1991: 36.557, 1992: 34.928,
    1993: 33.112, 1994: 31.185, 1995: 29.226, 1996: 27.296, 1997: 25.439,
    1998: 23.678, 1999: 22.028, 2000: 20.491, 2001: 19.068, 2002: 17.753,
    2003: 16.543, 2004: 15.429, 2005: 14.404, 2006: 13.462, 2007: 12.595,
    2008: 11.797, 2009: 11.061, 2010: 10.383, 2011: 6.151, 2012: 4.693,
    2013: 3.234, 2014: 1.775, 2015: 0.316,
    # 2016+: 0 (residual effect exhausted)
}

# Rio Tesuque: longer-lasting residuals
# Values from Core (2003) PROJECTION.XLS, continues through 2050+
CORE_2003_TESUQUE = {
    1988: 21.015, 1989: 22.333, 1990: 23.391, 1991: 24.227, 1992: 24.868,
    1993: 25.327, 1994: 25.615, 1995: 25.747, 1996: 25.737, 1997: 25.608,
    1998: 25.378, 1999: 25.067, 2000: 24.691, 2001: 24.265, 2002: 23.800,
    2003: 23.308, 2004: 22.797, 2005: 22.273, 2006: 21.743, 2007: 21.212,
    2008: 20.683, 2009: 20.157, 2010: 19.639, 2011: 19.258, 2012: 18.767,
    2013: 18.276, 2014: 17.785, 2015: 17.295, 2016: 16.804, 2017: 16.313,
    2018: 15.822, 2019: 15.331, 2020: 14.841, 2021: 14.350, 2022: 13.859,
    2023: 13.368, 2024: 12.877, 2025: 12.387, 2026: 11.896, 2027: 11.405,
    2028: 10.914, 2029: 10.424, 2030: 9.933,
    # Formula for years beyond table: y = -0.4908 * year + 1006.2
}
```

### Unit Conversion

```python
def cfs_to_acre_feet(cfs: float, days: int) -> float:
    """
    Convert cubic feet per second to acre-feet for a given period.

    Scientific basis:
    - 1 cfs = 1 ft³/s
    - 1 acre-foot = 43,560 ft³
    - 1 day = 86,400 seconds

    Conversion: AF = cfs * days * 86400 / 43560 = cfs * days * 1.9835

    Args:
        cfs: Flow rate in cubic feet per second
        days: Number of days in the period

    Returns:
        Volume in acre-feet
    """
    return cfs * days * 1.9835
```

### Error Handling Patterns

Follow `print_error()` pattern from ingest_buckman_data.py:
```python
def print_error(what_failed: str, location: str, actual: str, expected: str, context: str) -> None:
    """Print forensic-quality error message."""
    print(f"ERROR: {what_failed}")
    print(f"  Location: {location}")
    print(f"  Actual: {actual}")
    print(f"  Expected: {expected}")
    print(f"  Physical context: {context}")
```

### Excel Formatting (from ingest_buckman_data.py patterns)

```python
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

font_normal = Font(name='Aptos', size=11)
font_bold = Font(name='Aptos', size=11, bold=True)
align_center = Alignment(horizontal='center')
num_fmt_6 = '#,##0.000000'  # 6 decimal places for cfs
num_fmt_2 = '#,##0.00'      # 2 decimal places for AF
medium_border = Border(top=Side(style='medium'), bottom=Side(style='medium'))
hair_border = Border(top=Side(style='hair'), bottom=Side(style='hair'))
```

### Validation Tolerance

```python
VALIDATION_TOLERANCE_AF = 0.01      # Acre-feet comparison tolerance
VALIDATION_TOLERANCE_CFS = 0.000001  # CFS comparison tolerance
```

### File Paths

| File | Path |
|------|------|
| RIV flux input | `output/modflow/2024/modflow/CY2024_riv.flx` |
| GHB flux input | `output/modflow/2024/modflow/CY2024_ghb.flx` |
| Post-processor | `output/modflow/2024/depletions/sfmodflx_2245.exe` |
| Post-processor output | `output/modflow/2024/depletions/CY2024` |
| Table 3 validation | `validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx` |
| Table 4 validation | `validation/TABLE 4 - Rio Grande, above below Otowi.xlsx` |
| Table 5 validation | `validation/Table 5 - La Cienega Spring.jpg` |
| Table 3 output | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx` |
| Table 4 output | `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx` |
| Table 5 output | `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx` |
