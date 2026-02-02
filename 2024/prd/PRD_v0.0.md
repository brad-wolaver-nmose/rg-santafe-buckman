# PRD: Buckman Well Field PDF Data Ingestion Workflow

## Introduction

This workflow automates the ingestion of monthly meter report PDFs from the City of Santa Fe for the Buckman Well Field. The system uses OCR to extract pumping data for wells Buckman #1 through #13, validates the data through conversion checks, and produces structured CSV outputs for subsequent analysis steps in the annual depletion analysis workflow.

**Critical Principle:** Data integrity is paramount. When OCR confidence is low, values are flagged as "NOT_OK" for human review rather than inserting questionable data. This supports regulatory oversight by the New Mexico Office of the State Engineer (OSE).

## Goals

- Extract pumping data from 12 monthly PDF meter reports via OCR
- Produce 12 monthly CSV files with well-level pumping data and validation checks
- Produce 1 annual summary CSV consolidating all monthly data
- Flag uncertain OCR values conservatively (<95% confidence → "NOT_OK")
- Generate an input summary documenting all values requiring human review
- Enable human-in-the-loop QA/QC before data proceeds to analysis steps

## Technical Reference

### Conversion Factor

**1 million gallons (MG) = 3.06889 acre-feet (AF)**

Source: U.S. Geological Survey (USGS) — "Acre-foot: A volume of water equal to 1 foot in depth and covering 1 acre; equivalent to 43,560 cubic feet or 325,851 gallons."
Reference: https://water.usgs.gov/nawqa/glos.html

Calculation: 1,000,000 gallons ÷ 325,851 gallons/AF = 3.06889 AF

### File Locations

| Type | Path |
|------|------|
| Input PDFs | `./input/pdfs/` |
| Output CSVs | `./output/ingested_data/` |

### PDF Naming Convention

**Standard format (used by script):** `{year}_{month_numeric}_{MONTH_ABBREV}.pdf`

Examples:
- `2024_01_JAN.pdf`
- `2024_02_FEB.pdf`
- `2024_12_DEC.pdf`

**Note:** The script accepts PDFs with any naming convention. During the pre-flight validation phase, it OCRs each PDF to extract the actual year/month from the document header, then creates standardized copies with the format above. Original files are preserved unchanged.

### Input PDF Structure

- **Format:** Scanned images (requires true OCR)
- **Layout:** Highly consistent template across all months
- **Target Section:** Lower half of page 1, below "BUCKMAN WELLS" header
- **Data Rows:** 13 wells (Buckman #1 through #13) + Total row
- **Date Reference:** Line 5 of page 1, format "Re: Diversion Report for {Month} {Year}"

### Source Data Columns (from PDF)

| Column | Content | Example |
|--------|---------|---------|
| A | OSE state well number | RG-20516-S |
| B | City well name (normalized to "Buckman #N") | Buckman #3 |
| C | Monthly pumping (MG) | 0.000 |
| D | Monthly pumping (AF) | 0.00 |
| E | Meter reading | 16351 |

### Total Row (from PDF)

| Field | Content |
|-------|---------|
| Label | "Total Buckman Wells" |
| MG Total | Monthly total in million gallons |
| AF Total | Monthly total in acre-feet |

## User Stories

### US-001: Create Project Directory Structure
**Description:** As a developer, I need the output directory structure to exist so the workflow can write files.

**Acceptance Criteria:**
- [x] Create `./output/ingested_data/` directory if it does not exist
- [x] Verify `./input/pdfs/` directory exists (error if missing)
- [x] Script handles existing directories gracefully (no errors if already present)
- [x] Typecheck passes

---

### US-002: Install and Configure OCR Dependencies
**Description:** As a developer, I need OCR libraries installed so the workflow can read scanned PDFs.

**Acceptance Criteria:**
- [x] Create `requirements.txt` with: `pdf2image`, `pytesseract`, `Pillow`, `pandas`
- [x] Document system dependency: Tesseract OCR must be installed (`tesseract-ocr` package)
- [x] Document system dependency: Poppler must be installed for pdf2image (`poppler-utils` package)
- [x] Include brief installation instructions in script header comments
- [x] Typecheck passes

---

### US-003: Implement PDF to Image Conversion
**Description:** As a developer, I need to convert PDF page 1 to an image for OCR processing.

**Acceptance Criteria:**
- [x] Function accepts PDF file path as input
- [x] Converts only page 1 of PDF to image (ignore pages 2+)
- [x] Returns image object suitable for pytesseract
- [x] Handles missing PDF file gracefully (returns None, logs error)
- [x] Uses resolution suitable for OCR accuracy (300 DPI recommended)
- [x] Typecheck passes

---

### US-004: Extract Date Information from PDF
**Description:** As a developer, I need to extract year and month from the PDF header line.

**Acceptance Criteria:**
- [x] OCR the header area of page 1
- [x] Parse line matching pattern "Re: Diversion Report for {Month} {Year}"
- [x] Extract and return: `year` (int), `month_string` (str, e.g., "January"), `month_numeric` (str, e.g., "01")
- [x] Map month names to numeric: January→01, February→02, ..., December→12
- [x] Map month names to abbreviations: January→JAN, February→FEB, ..., December→DEC
- [x] If date cannot be parsed with >95% confidence, flag as NOT_OK
- [x] Typecheck passes

---

### US-005: Extract Buckman Wells Table Data via OCR
**Description:** As a developer, I need to extract the well pumping data table from the lower portion of page 1.

**Acceptance Criteria:**
- [x] Locate "BUCKMAN WELLS" section in lower half of page 1
- [x] Extract 13 data rows (Buckman #1 through #13)
- [x] Extract total row ("Total Buckman Wells")
- [x] For each row, extract: OSE number, well name, MG value, AF value, meter reading
- [x] Normalize well names to consistent "Buckman #N" format (handles OCR variations like "Buckman#1", "Buckman # 1", etc.)
- [x] Extract fields in order: OSE number first, then well name, then numeric values (MG, AF, meter)
- [x] Remove OSE number and well name from text before extracting numeric values to avoid capturing embedded digits
- [x] Track OCR confidence for each extracted value
- [x] Flag any value with <95% OCR confidence as potentially unreliable
- [x] Return structured data with confidence flags
- [x] Typecheck passes

---

### US-006: Implement OCR Confidence Tracking
**Description:** As a developer, I need to track OCR confidence scores to flag uncertain values.

**Acceptance Criteria:**
- [x] Use pytesseract's `image_to_data()` with output_type=dict to get confidence scores
- [x] Track confidence at the word/number level
- [x] Threshold: values with <95% confidence are flagged
- [x] Store confidence alongside extracted values for later validation
- [x] Typecheck passes

---

### US-007: Calculate MG to AF Conversion
**Description:** As a developer, I need to convert million gallons to acre-feet using the USGS standard factor.

**Acceptance Criteria:**
- [x] Function accepts MG value (float)
- [x] Returns AF value using: `AF = MG × 3.06889`
- [x] Return value has 5 decimal places precision (e.g., 1.23456)
- [x] Handle None/invalid input gracefully
- [x] Include USGS citation in code comments
- [x] Typecheck passes

---

### US-008: Validate Reported vs Calculated AF Values
**Description:** As a developer, I need to verify that the City's reported AF values match our calculated conversions.

**Acceptance Criteria:**
- [x] Compare reported AF (from PDF) with calculated AF (from MG × 3.06889)
- [x] Round both values to 2 decimal places for comparison
- [x] If values match when rounded: return "OK"
- [x] If values differ when rounded: return "NOT_OK"
- [x] Typecheck passes

---

### US-009: Generate Monthly CSV File
**Description:** As a developer, I need to create a monthly CSV file with extracted data and validation columns.

**Acceptance Criteria:**
- [x] Filename format: `buckman_{year}_{month_numeric}_{month_abbrev}.csv` (e.g., `buckman_2024_01_JAN.csv`)
- [x] Column order: OSE_Number, Well_Name, MG_Month, AF_Calculated, AF_Reported, AF_Verification, Meter_Reading
- [x] Sort rows by well name: Buckman #1 first, Buckman #2 second, ..., Buckman #13 last
- [x] MG values: 3 decimal places (e.g., 0.000)
- [x] AF_Calculated values: 5 decimal places (e.g., 0.00000)
- [x] AF_Reported values: 2 decimal places (e.g., 0.00)
- [x] AF_Verification: "OK" or "NOT_OK"
- [x] Any value with low OCR confidence replaced with "NOT_OK"
- [x] Typecheck passes

---

### US-010: Add Calculated Totals Row to Monthly CSV
**Description:** As a developer, I need to add a row summing all well values and comparing to the PDF total.

**Acceptance Criteria:**
- [x] Add row after Buckman #13 with label "Calculated_Sum"
- [x] Sum MG values from Buckman #1 through #13
- [x] Sum AF_Calculated values from Buckman #1 through #13
- [x] Add row with label "PDF_Total" containing values extracted from PDF total row
- [x] Add row with label "Total_Verification"
- [x] Compare Calculated_Sum to PDF_Total:
  - MG: if match within 2 decimal places → "OK", else → "NOT_OK"
  - AF: if match within 3 decimal places → "OK", else → "NOT_OK"
- [x] Typecheck passes

---

### US-011: Process Single Month End-to-End
**Description:** As a developer, I need a function that processes one PDF and produces one monthly CSV.

**Acceptance Criteria:**
- [x] Function accepts: year (int), month_numeric (str), month_abbrev (str)
- [x] Constructs input path: `./input/pdfs/{year}_{month_numeric}_{month_abbrev}.pdf`
- [x] Constructs output path: `./output/ingested_data/buckman_{year}_{month_numeric}_{month_abbrev}.csv`
- [x] Calls PDF conversion, OCR extraction, validation, and CSV generation
- [x] Returns list of any NOT_OK values encountered (for summary tracking)
- [x] Handles missing PDF: logs warning, returns indication of missing month
- [x] Typecheck passes

---

### US-012: Process All 12 Months
**Description:** As a developer, I need to process all monthly PDFs for a given year.

**Acceptance Criteria:**
- [x] Function accepts: year (int)
- [x] Iterates through months 01-12 (JAN through DEC)
- [x] Calls single-month processing for each
- [x] Collects all NOT_OK values across all months
- [x] Continues processing if a month is missing (skip and log)
- [x] Returns comprehensive list of issues for input_summary.csv
- [x] Typecheck passes

---

### US-013: Generate Annual Summary CSV
**Description:** As a developer, I need to create the annual summary table consolidating all monthly data.

**Acceptance Criteria:**
- [x] Filename: `buckman_{year}_table_2_data.csv`
- [x] Row 1 (headers): Well, JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC, Total
- [x] Rows 2-14: Wells 1-13, with AF values from each monthly CSV
- [x] Row 15: "Total" row with column sums
- [x] Column N (Total): Row sums (annual total per well)
- [x] AF values: 6 decimal places in this summary table
- [x] If monthly CSV missing or value is NOT_OK, carry forward "NOT_OK" string
- [x] Typecheck passes

---

### US-014: Generate Input Summary CSV
**Description:** As a developer, I need to create a summary of all values flagged for human review.

**Acceptance Criteria:**
- [x] Filename: `input_summary.csv`
- [x] Columns: Year, Month, Well, Field, Issue
- [x] List every cell marked as "NOT_OK" with location details
- [x] Include reason if available (low OCR confidence, verification mismatch, missing PDF)
- [x] If no issues found, create file with headers only and note "No issues detected"
- [x] Typecheck passes

---

### US-015: Create Main Entry Point Script
**Description:** As a developer, I need a main script that orchestrates the complete workflow.

**Acceptance Criteria:**
- [x] Script name: `ingest_buckman_data.py`
- [x] Accepts command-line argument for year (e.g., `python3 ingest_buckman_data.py 2024`)
- [x] Creates output directory if needed
- [x] Processes all 12 months
- [x] Generates annual summary CSV
- [x] Generates input_summary.csv
- [x] Prints summary of processing results to console
- [x] Prints clear message about human QA/QC step required
- [x] Includes detailed comments suitable for Python beginners
- [x] Typecheck passes

---

### US-016: PDF Validation and Standardization
**Description:** As a user, I need the script to validate input PDFs and standardize filenames before processing, so that I can catch issues early and ensure consistent naming.

**Acceptance Criteria:**
- [x] Scan `./input/pdfs/` for all PDF files regardless of naming convention
- [x] OCR each PDF's header to extract year and month (line matching "Re: Diversion Report for {Month} {Year}")
- [x] Create copies of PDFs with standardized names `{year}_{month_numeric}_{MONTH_ABBREV}.pdf`
- [x] Preserve original files unchanged
- [x] Detect and report missing months (gaps in JAN-DEC coverage)
- [x] Detect and report duplicate months (multiple PDFs for same month/year)
- [x] Detect and report wrong-year files (PDF content doesn't match expected year)
- [x] Detect and report unreadable files (OCR failed to extract date)
- [x] Return validation report with all issues found
- [x] Typecheck passes

---

### US-017: Interactive Year Selection
**Description:** As a user, I want the script to prompt me for the year if not provided on command line, so that I can run the script without remembering the exact syntax.

**Acceptance Criteria:**
- [x] If no command-line year argument, scan PDFs and auto-detect available years
- [x] Display detected years to user and prompt for selection
- [x] Suggest most common year found as default
- [x] Validate user input is a reasonable year (1990-2100)
- [x] Allow user to override detected year if needed
- [x] Typecheck passes

---

### US-018: Pre-Flight Validation Report
**Description:** As a user, I need to see a validation report before processing begins, so that I can review any issues and decide whether to proceed.

**Acceptance Criteria:**
- [x] Display pre-flight report showing:
  - Target year
  - Number of original files found
  - Number of standardized copies created
  - Month-by-month coverage status (OK/MISSING/DUPLICATE/WRONG_YEAR)
  - Total issues found
- [x] For each month, show standardized filename and original source file
- [x] Prompt user for confirmation before processing (Y/n for no issues, y/N if issues found)
- [x] If user declines, exit gracefully without processing
- [x] Typecheck passes

---

### US-019: System Dependency Check
**Description:** As a user, I need the script to check for required system dependencies at startup and display helpful installation instructions if they are missing.

**Acceptance Criteria:**
- [x] Check for Tesseract OCR installation at startup
- [x] Check for Poppler (pdftoppm) installation at startup
- [x] If dependencies missing, display clear error message listing missing packages
- [x] Provide installation commands for Ubuntu/Debian (`apt-get`)
- [x] Provide installation commands for macOS (`brew`)
- [x] Exit gracefully with non-zero exit code if dependencies missing
- [x] Typecheck passes

---

### US-020: Configuration Constants
**Description:** As a developer, I need all magic numbers and configuration values defined as module-level constants so the code is maintainable and self-documenting.

**Acceptance Criteria:**
- [x] Define `OCR_CONFIDENCE_THRESHOLD = 95` for OCR quality filtering
- [x] Define `HEADER_CROP_RATIO = 0.25` for header region extraction
- [x] Define `TABLE_CROP_RATIO = 0.50` for table region extraction
- [x] Define `LINE_GROUPING_TOLERANCE_PX = 20` for OCR line reconstruction
- [x] Define `PDF_CONVERSION_DPI = 300` for image conversion quality
- [x] Define `MG_VERIFICATION_TOLERANCE = 0.01` for MG total verification
- [x] Define `AF_VERIFICATION_TOLERANCE = 0.001` for AF total verification
- [x] Define `MONTHS_ABBREV` tuple with all 12 month abbreviations
- [x] Define `MONTHS_ORDERED` tuple with (numeric, abbrev) pairs
- [x] All constants have explanatory comments
- [x] Typecheck passes

---

### US-021: OCR Confidence Helper Function
**Description:** As a developer, I need a helper function to properly evaluate OCR confidence scores, including handling Tesseract's -1 "invalid" value.

**Acceptance Criteria:**
- [x] Create `is_confident(confidence, threshold)` function
- [x] Return `False` if confidence is -1 (Tesseract's "invalid/no data" marker)
- [x] Return `False` if confidence is below threshold
- [x] Return `True` only if confidence >= 0 AND confidence >= threshold
- [x] Default threshold uses `OCR_CONFIDENCE_THRESHOLD` constant
- [x] Include docstring with examples
- [x] Replace all `>= 95` confidence checks with `is_confident()` calls
- [x] Typecheck passes

---

### US-022: Atomic File Writes
**Description:** As a developer, I need CSV files to be written atomically to prevent corrupted partial files if the script is interrupted.

**Acceptance Criteria:**
- [x] Write CSV data to a temporary file first
- [x] Use `tempfile.NamedTemporaryFile` in the output directory
- [x] Atomically move temp file to final destination using `shutil.move`
- [x] Ensures no partial/corrupted CSV files remain after interruption
- [x] Typecheck passes

---

### US-023: Enhanced Error Messages
**Description:** As a developer, I need error messages to include sufficient context for debugging when OCR or file operations fail.

**Acceptance Criteria:**
- [x] All exception handlers print the exception type (e.g., `ValueError`, `FileNotFoundError`)
- [x] All exception handlers print the exception message
- [x] PDF processing errors include abbreviated traceback (last 2 frames)
- [x] File-related errors include the relevant file path
- [x] Errors are formatted with indentation for readability
- [x] Typecheck passes

---

### US-024: Progress Feedback During OCR
**Description:** As a user, I need to see progress indicators during the slow OCR scanning phase so I know the script is working.

**Acceptance Criteria:**
- [x] Display progress as `(current/total)` when scanning PDFs
- [x] Example: `(3/12) Scanning: filename.pdf...`
- [x] Progress shown during pre-flight validation phase
- [x] Filenames truncated to fit display without line wrapping
- [x] Typecheck passes

---

## Non-Goals

The following are explicitly **out of scope** for this PRD:

- **Subsequent analysis steps:** Stream depletion calculations, memo generation, and other downstream processing will be separate PRDs
- **Automated learning from corrections:** The `input_summary_corrected.csv` feedback loop is noted but implementation deferred to future steps
- **PDF preprocessing:** Deskewing, contrast enhancement, or other image cleanup (assuming consistent scan quality)
- **GUI or web interface:** This is a command-line Python script
- **Database storage:** Outputs are CSV files only
- **Multi-year batch processing:** Process one year at a time
- **Email integration:** PDFs are manually placed in `./input/pdfs/` by user
- **Automatic verification against historical data:** Each year processed independently

## Technical Considerations

### System Dependencies

The script automatically checks for these dependencies at startup and displays helpful installation instructions if they are missing.

| Dependency | Purpose | Ubuntu/Debian | macOS |
|------------|---------|---------------|-------|
| Tesseract OCR | Text extraction from images | `tesseract-ocr` | `tesseract` |
| Poppler | PDF to image conversion | `poppler-utils` | `poppler` |

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils

# macOS
brew install tesseract poppler
```

### Python Dependencies

```
pdf2image>=1.16.0
pytesseract>=0.3.10
Pillow>=9.0.0
pandas>=1.5.0
```

### Code Quality & Testing Requirements

All code changes must pass the following checks before being considered complete:

| Check | Command | Purpose |
|-------|---------|---------|
| Syntax validation | `python3 -m py_compile ingest_buckman_data.py` | Verify Python syntax is valid |
| Type checking | `mypy ingest_buckman_data.py` | Verify type hints are correct and consistent |

**Running all checks:**
```bash
# Run both checks (both must pass with no errors)
python3 -m py_compile ingest_buckman_data.py && mypy ingest_buckman_data.py
```

**mypy configuration** (`mypy.ini`):
```ini
[mypy]
python_version = 3.12
```

**Note:** Every user story includes "Typecheck passes" as an acceptance criterion. This refers to passing both `py_compile` (syntax) and `mypy` (type checking) with zero errors.

### OCR Configuration

- Use Tesseract with `--psm 6` (assume uniform block of text) for table extraction
- Consider `--oem 3` (default LSTM engine) for best accuracy
- 300 DPI conversion from PDF provides good OCR accuracy

### Configuration Constants

All magic numbers are defined as module-level constants for maintainability:

| Constant | Value | Description |
|----------|-------|-------------|
| `OCR_CONFIDENCE_THRESHOLD` | 95 | Minimum OCR confidence % to accept a value |
| `HEADER_CROP_RATIO` | 0.25 | Top 25% of page contains date/header info |
| `TABLE_CROP_RATIO` | 0.50 | Bottom 50% of page contains well data table |
| `LINE_GROUPING_TOLERANCE_PX` | 20 | Pixels tolerance for grouping OCR words into lines |
| `PDF_CONVERSION_DPI` | 300 | Resolution for PDF to image conversion |
| `MG_VERIFICATION_TOLERANCE` | 0.01 | Tolerance for MG total verification (2 decimal places) |
| `AF_VERIFICATION_TOLERANCE` | 0.001 | Tolerance for AF total verification (3 decimal places) |

### OCR Confidence Handling

Tesseract returns confidence scores as integers:
- **0-100**: Valid confidence percentage
- **-1**: Invalid/no data (word not recognized)

The `is_confident()` helper function properly handles the -1 case:

```python
def is_confident(confidence: int, threshold: int = 95) -> bool:
    if confidence < 0:  # -1 means invalid
        return False
    return confidence >= threshold
```

### Atomic File Writes

CSV files are written using an atomic pattern to prevent corruption:

1. Write data to a temporary file in the output directory
2. Atomically rename/move temp file to final destination
3. If script is interrupted, no partial files remain

### Well Name Standardization

Well names are normalized to a consistent format during extraction:

| OCR Variation | Normalized Format |
|---------------|-------------------|
| `Buckman#1` | `Buckman #1` |
| `Buckman # 1` | `Buckman #1` |
| `Buckman 1` | `Buckman #1` |
| `buckman #1` | `Buckman #1` |

This ensures consistent matching when generating annual summaries and sorting well data.

### Known Limitations

1. **Scanned PDF quality:** OCR accuracy depends on scan quality; poor scans will generate more NOT_OK flags
2. **Table structure assumptions:** Code assumes consistent table format; major format changes would require updates
3. **Tesseract limitations:** Handwritten annotations or stamps may cause false readings

### Human QA/QC Workflow

After running the script:

1. Review `input_summary.csv` for all flagged values
2. Open each flagged monthly CSV alongside the source PDF
3. Manually verify and correct NOT_OK values
4. Update `input_summary.csv` → save as `input_summary_corrected.csv`
5. Re-run annual summary generation if corrections made (future enhancement)

### File Output Summary

| File | Count | Description |
|------|-------|-------------|
| `buckman_{year}_{MM}_{MON}.csv` | 12 | Monthly well data with validation |
| `buckman_{year}_table_2_data.csv` | 1 | Annual summary table |
| `input_summary.csv` | 1 | NOT_OK values for human review |

---

## Appendix: Month Reference

| Numeric | Abbreviation | Full Name |
|---------|--------------|-----------|
| 01 | JAN | January |
| 02 | FEB | February |
| 03 | MAR | March |
| 04 | APR | April |
| 05 | MAY | May |
| 06 | JUN | June |
| 07 | JUL | July |
| 08 | AUG | August |
| 09 | SEP | September |
| 10 | OCT | October |
| 11 | NOV | November |
| 12 | DEC | December |
