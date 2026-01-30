# PRD: Refactor ingest_buckman_data.py — CSV Ingestion (Remove PDF/OCR)

## Introduction

Replace the PDF/OCR-based data ingestion pipeline in `ingest_buckman_data.py` with direct CSV ingestion from `Buckman_Well_Prod_2024.csv`. The current script (2,070 lines) extracts well production data from scanned PDF meter reports using Tesseract OCR and pdftotext. The new approach reads a single CSV file containing daily flow data (MGD) for 13 Buckman wells, aggregates by month, converts to MG and AF, and outputs monthly CSVs with data quality flags.

The source CSV has 366 daily data rows plus 4 summary rows (Sum, Avg, Max, Min), with columns for each of the 13 wells plus a formula-computed total (BWP). Missing/invalid data is flagged and original values are preserved.

## Goals

- Remove all PDF/OCR processing code (~1,500 lines) from `ingest_buckman_data.py`
- Ingest daily well production data from `input/csv/Buckman_Well_Prod_2024.csv`
- Aggregate daily MGD values into monthly totals (MG) per well
- Calculate acre-feet using USGS conversion factor (MG x 3.06889)
- Output monthly CSVs named `2024_01_JAN.csv` through `2024_12_DEC.csv`
- Flag missing/invalid data (blank, non-numeric, negative) while preserving original values
- Verify per-well daily sums against BWP total column (tolerance 0.001 MGD)
- Verify annual totals against CSV Sum row
- Generate annual summary and QA input summary files
- Accept year as command-line argument (no interactive prompts)
- Reduce dependencies to pandas only (remove pdf2image, pytesseract, Pillow)

## User Stories

### US-001: Configuration Constants and Well Mapping
**Description:** As a developer, I need all configuration values and the well-to-OSE-number mapping defined as module-level constants so the code is maintainable and self-documenting.

**Acceptance Criteria:**
- [x] Define `INPUT_CSV_PATH = "./input/csv/Buckman_Well_Prod_2024.csv"` (with year placeholder pattern)
- [x] Define `OUTPUT_DIR = "./output/ingested_data"`
- [x] Define `MG_TO_AF_FACTOR = 3.06889` (USGS: 1 MG = 3.06889 AF)
- [x] Define `DAILY_SUM_TOLERANCE = 0.001` (MGD tolerance for BWP verification)
- [x] Define `ANNUAL_SUM_TOLERANCE = 0.01` (tolerance for annual Sum row verification)
- [x] Define `MONTHS_ABBREV` tuple: `("JAN", "FEB", ..., "DEC")`
- [x] Define `MONTHS_ORDERED` tuple: `(("01", "JAN"), ("02", "FEB"), ..., ("12", "DEC"))`
- [x] Define `WELL_OSE_MAP` dictionary mapping well number (1-13) to OSE number:
  ```
  1: "RG-20516-S-5"
  2: "RG-20516-S-6"
  3: "RG-20516-S"
  4: "RG-20516-S-2"
  5: "RG-20516-S-3"
  6: "RG-20516-S-4"
  7: "RG-20516-S-7"
  8: "RG-20516-S-8"
  9: "RG-20516-S-9"
  10: "RG-20516-S-10"
  11: "RG-20516-S-11"
  12: "RG-20516-S-12"
  13: "RG-20516-S-13"
  ```
- [x] Define `CSV_WELL_COLUMNS` list mapping CSV header names to well numbers: `"BWell 1"` through `"BWell 13"`
- [x] Define `CSV_TOTAL_COLUMN = "BWP|Flow Mgd|MGD|Formula"` (the total/formula column name from the CSV header)
- [x] Constants grouped logically at module level with explanatory comments
- [x] Typecheck passes

### US-002: Remove All PDF/OCR Code and Imports
**Description:** As a developer, I need all PDF/OCR processing code removed so the script is clean and focused on CSV ingestion only.

**Acceptance Criteria:**
- [ ] Remove imports: `pdf2image`, `pytesseract`, `Pillow`/`PIL`, `subprocess` (if only used for OCR tools), `tempfile` (if only used for PDF processing)
- [ ] Remove `check_system_dependencies()` function
- [ ] Remove `WellData` class
- [ ] Remove all PDF date extraction functions: `extract_date_from_pdf()`, `extract_date_from_filename()`, `extract_date_pdftotext()`, `extract_date_from_pdf_quick()`
- [ ] Remove all PDF well data extraction functions: `extract_buckman_wells_data()`, `extract_buckman_data_pdftotext()`, `_parse_table_row()`, `_normalize_well_name()`
- [ ] Remove OCR-related helpers: `is_confident()`
- [ ] Remove all PDF validation/preflight functions: `validate_and_prepare_pdfs()`, `scan_input_pdfs()`, `get_year_interactively()`, `display_preflight_report()`
- [ ] Remove `create_project_directories()` function (will be replaced)
- [ ] Remove all OCR configuration constants: `OCR_CONFIDENCE_THRESHOLD`, `HEADER_CROP_RATIO`, `TABLE_CROP_RATIO`, `LINE_GROUPING_TOLERANCE_PX`, `PDF_CONVERSION_DPI`, `STANDARDIZED_PDF_PATTERN`
- [ ] Remove `validate_af_conversion()` function (no longer needed — no AF_Reported from CSV)
- [ ] Keep `mg_to_af()` function (still needed for AF calculation)
- [ ] Keep `MG_VERIFICATION_TOLERANCE` and `AF_VERIFICATION_TOLERANCE` only if still used; otherwise remove
- [ ] File should contain only: imports, constants (from US-001), and placeholder functions/main block
- [ ] Typecheck passes

### US-003: CSV Ingestion Function
**Description:** As a developer, I need a function that reads the source CSV, parses the header, extracts daily data rows, and returns a clean pandas DataFrame so downstream functions can aggregate by month.

**Acceptance Criteria:**
- [ ] Function signature: `def read_source_csv(csv_path: str) -> Tuple[pd.DataFrame, pd.Series]`
- [ ] Read CSV using first row as header
- [ ] Parse the date column (first column, header contains date range like `1/1/2024-12/31/2024`) as datetime
- [ ] Rename date column to `"Date"`
- [ ] Parse well columns (`BWell 1` through `BWell 13`) and total column (`BWP|Flow Mgd|MGD|Formula`)
- [ ] Separate daily data rows (rows with valid dates) from summary rows (Sum, Avg, Max, Min)
- [ ] Return tuple: `(daily_df, sum_row)` — daily DataFrame and the Sum row as a Series
- [ ] Daily DataFrame has columns: `Date`, `BWell 1` through `BWell 13`, `BWP_Total`
- [ ] BWP total column renamed to `BWP_Total` for clarity
- [ ] Summary rows (Sum, Avg, Max, Min) are excluded from daily_df
- [ ] Print count of daily rows read (e.g., "Read 366 daily records from CSV")
- [ ] Typecheck passes

### US-004: Data Validation and Flagging Function
**Description:** As a developer, I need a function that identifies missing/invalid data in the daily DataFrame and returns a flags DataFrame so original values are preserved while problems are tracked.

**Acceptance Criteria:**
- [ ] Function signature: `def validate_daily_data(daily_df: pd.DataFrame) -> pd.DataFrame`
- [ ] Return a flags DataFrame with same shape as daily_df well columns (BWell 1-13)
- [ ] Flag cells that are: blank/NaN, non-numeric (after initial parse), or negative values
- [ ] Flag values: `""` (empty string) for valid data, `"BLANK"` for missing/NaN, `"NEGATIVE"` for negative values, `"NON_NUMERIC"` for non-numeric strings
- [ ] Do NOT flag zero values (zero = well not pumping, which is valid)
- [ ] Print summary: count of flagged cells per well and total (e.g., "Flagged 3 invalid values across 2 wells")
- [ ] Typecheck passes

### US-005: Daily Sum Verification Function
**Description:** As a developer, I need a function that verifies each day's per-well sum matches the BWP total column so data integrity issues are caught early.

**Acceptance Criteria:**
- [ ] Function signature: `def verify_daily_sums(daily_df: pd.DataFrame, tolerance: float = 0.001) -> pd.DataFrame`
- [ ] For each daily row, sum BWell 1 through BWell 13 (treating NaN as 0)
- [ ] Compare calculated sum to `BWP_Total` column
- [ ] Return a DataFrame with columns: `Date`, `Calculated_Sum`, `BWP_Total`, `Difference`, `Verification` ("OK" or "NOT_OK")
- [ ] Only flag as NOT_OK if absolute difference exceeds tolerance
- [ ] Print count of mismatched days (e.g., "Daily sum verification: 366 OK, 0 NOT_OK")
- [ ] Typecheck passes

### US-006: Monthly Aggregation Function
**Description:** As a developer, I need a function that aggregates daily MGD values into monthly totals per well so monthly CSVs can be generated.

**Acceptance Criteria:**
- [ ] Function signature: `def aggregate_monthly(daily_df: pd.DataFrame, flags_df: pd.DataFrame) -> Dict[str, pd.DataFrame]`
- [ ] Group daily data by calendar month (1-12)
- [ ] For each month, sum daily MGD values per well to get monthly MG total
- [ ] Result dict keyed by month string `"01"` through `"12"`
- [ ] Each month DataFrame has columns: `Well_Number` (1-13), `MG_Month` (3 decimal places), `Has_Flagged_Data` (bool — True if any day in that month had a flag for that well)
- [ ] If a well has any flagged days in a month, still calculate the sum from available valid data but set `Has_Flagged_Data = True`
- [ ] Typecheck passes

### US-007: Generate Monthly CSV Files
**Description:** As a user, I need monthly CSV output files with well production data, AF calculations, and data quality flags so I can review and use the data downstream.

**Acceptance Criteria:**
- [ ] Function signature: `def generate_monthly_csv(month_num: str, month_abbrev: str, month_df: pd.DataFrame, year: int, output_dir: str) -> List[Dict]`
- [ ] Output filename pattern: `{year}_{month_num}_{month_abbrev}.csv` (e.g., `2024_01_JAN.csv`)
- [ ] CSV columns: `OSE_Number`, `Well_Name`, `MG_Month`, `AF_Calculated`, `Data_Quality`
- [ ] Map well numbers to OSE numbers using `WELL_OSE_MAP` constant
- [ ] Map well numbers to names: `"Buckman #1"` through `"Buckman #13"`
- [ ] `MG_Month`: monthly total in million gallons (3 decimal places)
- [ ] `AF_Calculated`: `MG_Month * 3.06889` (5 decimal places)
- [ ] `Data_Quality`: `"OK"` if no flagged days for that well in that month, `"FLAGGED"` if any flagged days exist
- [ ] Add `Calculated_Sum` row at bottom with totals for MG_Month and AF_Calculated
- [ ] Add `BWP_Verification` row comparing our monthly well sum to the sum of BWP_Total values for that month (from daily data)
- [ ] Create output directory if it does not exist
- [ ] Return list of dicts describing any flagged wells (for QA summary)
- [ ] Print confirmation: `"Wrote 2024_01_JAN.csv (13 wells, 2 flagged)"`
- [ ] Typecheck passes

### US-008: Generate Annual Summary CSV
**Description:** As a user, I need a consolidated annual summary showing AF values for all wells across all months so I can see the full year at a glance.

**Acceptance Criteria:**
- [ ] Function signature: `def generate_annual_summary(monthly_data: Dict[str, pd.DataFrame], year: int, output_dir: str) -> None`
- [ ] Output filename: `{year}_annual_summary.csv` (e.g., `2024_annual_summary.csv`)
- [ ] CSV structure: rows = wells (Buckman #1 through #13 + Total), columns = months (JAN through DEC + Total)
- [ ] Cell values are AF_Calculated (5 decimal places)
- [ ] If a well-month has flagged data, append `"*"` to the value (e.g., `"16.88502*"`)
- [ ] Total row = sum of all wells per month
- [ ] Total column = sum of all months per well
- [ ] Include footnote row: `"* = contains flagged data (missing or invalid source values)"`
- [ ] Typecheck passes

### US-009: Generate QA Input Summary CSV
**Description:** As a user, I need a summary of all flagged data so I can review potential data quality issues in one place.

**Acceptance Criteria:**
- [ ] Function signature: `def generate_qa_summary(all_flags: List[Dict], daily_verification: pd.DataFrame, year: int, output_dir: str) -> None`
- [ ] Output filename: `input_summary.csv`
- [ ] Section 1 — Flagged well-month data: columns `Month`, `Well_Name`, `Flag_Type`, `Flagged_Days_Count`, `Monthly_MG_Total` (calculated from available valid data)
- [ ] Section 2 — Daily sum mismatches: columns `Date`, `Calculated_Sum`, `BWP_Total`, `Difference` (only rows where Verification = NOT_OK)
- [ ] If no flags and no mismatches, write a single row: `"No data quality issues found"`
- [ ] Print summary: `"QA summary: 5 flagged well-months, 0 daily sum mismatches"`
- [ ] Typecheck passes

### US-010: Annual Sum Verification
**Description:** As a developer, I need to verify our calculated annual totals against the CSV's Sum row so we know our aggregation is correct.

**Acceptance Criteria:**
- [ ] Function signature: `def verify_annual_sums(monthly_data: Dict[str, pd.DataFrame], sum_row: pd.Series, tolerance: float = 0.01) -> Dict[str, str]`
- [ ] For each well (BWell 1-13), sum all 12 monthly MG totals
- [ ] Compare against corresponding value in the CSV Sum row
- [ ] Return dict mapping well name to verification status: `"OK"` or `"NOT_OK (calculated=X, source=Y)"`
- [ ] Print verification results: per-well status and overall pass/fail
- [ ] Typecheck passes

### US-011: Main Function and CLI Interface
**Description:** As a user, I need to run the script with a year argument to process the CSV and generate all outputs without interactive prompts.

**Acceptance Criteria:**
- [ ] Usage: `python3 ingest_buckman_data.py [year]` (default: 2024)
- [ ] Accept year as optional positional argument via `argparse`
- [ ] Construct CSV input path from year: `./input/csv/Buckman_Well_Prod_{year}.csv`
- [ ] Validate input CSV file exists; print clear error and exit if not
- [ ] Create output directory if it does not exist
- [ ] Call functions in order: `read_source_csv` -> `validate_daily_data` -> `verify_daily_sums` -> `aggregate_monthly` -> loop `generate_monthly_csv` for 12 months -> `generate_annual_summary` -> `verify_annual_sums` -> `generate_qa_summary`
- [ ] Print overall summary at end: total wells, total months, flagged count, verification status
- [ ] Exit code 0 on success, 1 on fatal error (missing file, parse failure)
- [ ] No interactive prompts (no `input()` calls)
- [ ] Typecheck passes
- [ ] Run script end-to-end with the real CSV successfully

### US-012: Update requirements.txt
**Description:** As a developer, I need requirements.txt to reflect the simplified dependencies.

**Acceptance Criteria:**
- [ ] Remove `pdf2image`, `pytesseract`, `Pillow` from requirements.txt
- [ ] Keep `pandas>=1.5.0`
- [ ] No other dependencies needed
- [ ] Typecheck passes

### US-013: Enhanced Error Messages
**Description:** As a developer, I need error messages to include sufficient context for debugging when CSV parsing or validation fails.

**Acceptance Criteria:**
- [ ] CSV read errors include the file path attempted
- [ ] Parse errors include row number and problematic value
- [ ] Validation errors include well name, date, and the invalid value
- [ ] All exception handlers print exception type and message
- [ ] Missing file error includes expected path and suggestion to check directory
- [ ] Typecheck passes

### US-014: Progress Feedback
**Description:** As a user, I need progress indicators during processing so I know the script is working.

**Acceptance Criteria:**
- [ ] Display `"Reading CSV: {path}"` at start
- [ ] Display `"Validating {N} daily records..."` during validation
- [ ] Display `"(X/12) Generating: {filename}"` for each monthly CSV
- [ ] Display `"Generating annual summary..."` before annual summary
- [ ] Display `"Verifying annual totals..."` before annual verification
- [ ] Display final summary block with: files created, flags found, verification status
- [ ] Typecheck passes
- [ ] Run script end-to-end with the real CSV successfully

## Non-Goals

- No PDF processing of any kind (removed entirely)
- No OCR or image processing
- No system dependency checks (Tesseract, Poppler, ocrmypdf)
- No interactive prompts or user confirmation dialogs
- No AF_Reported column (source CSV does not contain AF values)
- No Meter_Reading column (source CSV does not contain meter readings)
- No pre-flight PDF validation or standardized PDF copy creation
- No support for multiple CSV files (single file per year)
- No GUI or web interface

## Technical Considerations

### Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `INPUT_CSV_PATH` | `"./input/csv/Buckman_Well_Prod_{year}.csv"` | Source CSV path pattern |
| `OUTPUT_DIR` | `"./output/ingested_data"` | Output directory for all generated files |
| `MG_TO_AF_FACTOR` | `3.06889` | USGS conversion: 1 MG = 3.06889 AF |
| `DAILY_SUM_TOLERANCE` | `0.001` | MGD tolerance for daily BWP total verification |
| `ANNUAL_SUM_TOLERANCE` | `0.01` | MG tolerance for annual Sum row verification |
| `CSV_TOTAL_COLUMN` | `"BWP\|Flow Mgd\|MGD\|Formula"` | Header name for the total column in source CSV |

### Well-to-OSE Number Mapping

| Well # | CSV Column | Well Name | OSE Number |
|--------|-----------|-----------|------------|
| 1 | BWell 1 | Buckman #1 | RG-20516-S-5 |
| 2 | BWell 2 | Buckman #2 | RG-20516-S-6 |
| 3 | BWell 3 | Buckman #3 | RG-20516-S |
| 4 | BWell 4 | Buckman #4 | RG-20516-S-2 |
| 5 | BWell 5 | Buckman #5 | RG-20516-S-3 |
| 6 | BWell 6 | Buckman #6 | RG-20516-S-4 |
| 7 | BWell 7 | Buckman #7 | RG-20516-S-7 |
| 8 | BWell 8 | Buckman #8 | RG-20516-S-8 |
| 9 | BWell 9 | Buckman #9 | RG-20516-S-9 |
| 10 | BWell 10 | Buckman #10 | RG-20516-S-10 |
| 11 | BWell 11 | Buckman #11 | RG-20516-S-11 |
| 12 | BWell 12 | Buckman #12 | RG-20516-S-12 |
| 13 | BWell 13 | Buckman #13 | RG-20516-S-13 |

### CSV Source Format

- **Header row:** `1/1/2024-12/31/2024,BWell 1|Flow Mgd,BWell 2|Flow Mgd,...,BWP|Flow Mgd|MGD|Formula`
- **Data rows:** `1/1/2024,0,0,0,...,0.6838` (366 daily rows for 2024)
- **Summary rows:** Sum, Avg, Max, Min (4 rows at bottom, date column contains the label)
- **Units:** MGD (million gallons per day) — summing daily values for a month gives monthly MG directly
- **Zeros:** Valid data meaning "well not pumped that day"

### Conversion

```python
def mg_to_af(mg_value: float) -> float:
    """Convert million gallons to acre-feet using USGS standard.

    1 acre-foot = 325,851 gallons
    1 MG = 1,000,000 / 325,851 = 3.06889 AF
    """
    return round(mg_value * 3.06889, 5)
```

### Error Handling Patterns

- Return early with clear error message if CSV file not found
- Use pandas `errors="coerce"` for numeric parsing to convert invalid values to NaN
- Track flags in a parallel DataFrame (same shape as data, stores flag reasons)
- Never silently drop data — preserve original and flag for review
- Print progress to stdout; print errors to stderr

### Data Flow

```
Input: ./input/csv/Buckman_Well_Prod_2024.csv
  |
  v
[read_source_csv] --> daily_df (366 rows x 15 cols), sum_row
  |
  v
[validate_daily_data] --> flags_df (366 rows x 13 cols, flag strings)
  |
  v
[verify_daily_sums] --> daily_verification_df (366 rows, OK/NOT_OK per day)
  |
  v
[aggregate_monthly] --> monthly_data dict (12 months, each with 13 wells)
  |
  v
[generate_monthly_csv] x12 --> 2024_01_JAN.csv ... 2024_12_DEC.csv
  |
  v
[generate_annual_summary] --> 2024_annual_summary.csv
  |
  v
[verify_annual_sums] --> per-well verification results (printed)
  |
  v
[generate_qa_summary] --> input_summary.csv
```
