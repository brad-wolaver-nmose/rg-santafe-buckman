# Code Review Checklist

**Generated:** 2026-01-27
**PRD:** PRD.md (24 user stories)
**Code files:** ingest_buckman_data.py (1756 lines)
**Review depth:** Thorough (30-60 minutes)
**Story count:** 50 atomic stories

---

## Instructions for Ralph

For each story:
1. Read ONLY the specified location
2. Check ONLY the specified criterion
3. Add ONE row to the specified table in REVIEW_FINDINGS.md
4. Mark [x] when documented

**Keep it focused.** Each story = one check = one finding row.

---

## Type Safety (Run First)

### US-R01: Run type checker [x]
**Check:** Run `mypy ingest_buckman_data.py` and capture output
**Location:** ingest_buckman_data.py
**Document:** Add to Type Safety section in REVIEW_FINDINGS.md
**Pass if:** Zero errors OR each error documented

---

### US-R02: Run syntax check [x]
**Check:** Run `python3 -m py_compile ingest_buckman_data.py`
**Location:** ingest_buckman_data.py
**Document:** Add to Type Safety section in REVIEW_FINDINGS.md
**Pass if:** Compiles without errors

---

## PRD Compliance (US-001 through US-024)

### US-R03: Verify PRD US-001 (Directory Structure) [x]
**Check:** Does create_project_directories() create ./output/ingested_data/ and verify ./input/pdfs/ exists?
**Location:** create_project_directories() lines 1653-1685
**Document:** Add row to PRD Compliance table
**Pass if:** Both directories handled, no errors if already present

---

### US-R04: Verify PRD US-002 (OCR Dependencies) [x]
**Check:** Are all dependencies in requirements.txt and system dependencies documented?
**Location:** requirements.txt, script header lines 1-16, check_system_dependencies() lines 73-133
**Document:** Add row to PRD Compliance table
**Pass if:** pdf2image, pytesseract, Pillow, pandas listed; Tesseract/Poppler checked with install instructions

---

### US-R05: Verify PRD US-003 (PDF to Image) [x]
**Check:** Does pdf_to_image() convert page 1 only, return Image or None, use 300 DPI?
**Location:** pdf_to_image() lines 215-263
**Document:** Add row to PRD Compliance table
**Pass if:** first_page=1, last_page=1, dpi=PDF_CONVERSION_DPI (300), None on error

---

### US-R06: Verify PRD US-004 (Date Extraction) [x]
**Check:** Does extract_date_from_pdf() extract year, month_string, month_numeric, month_abbrev with confidence check?
**Location:** extract_date_from_pdf() lines 266-362
**Document:** Add row to PRD Compliance table
**Pass if:** Returns tuple of 4 values, flags NOT_OK if confidence < 95%

---

### US-R07: Verify PRD US-005 (Wells Table Extraction) [x]
**Check:** Does extract_buckman_wells_data() locate BUCKMAN WELLS, extract 13 wells + total, normalize names, track confidence?
**Location:** extract_buckman_wells_data() lines 365-448, _parse_table_row() lines 549-644
**Document:** Add row to PRD Compliance table
**Pass if:** Well names normalized to "Buckman #N", OSE/name removed before number extraction

---

### US-R08: Verify PRD US-006 (OCR Confidence Tracking) [x]
**Check:** Is pytesseract.image_to_data() used with output_type=dict? Are confidence scores tracked per field?
**Location:** extract_date_from_pdf() line 296, extract_buckman_wells_data() line 397
**Document:** Add row to PRD Compliance table
**Pass if:** Uses image_to_data with dict output, confidence stored in WellData

---

### US-R09: Verify PRD US-007 (MG to AF Conversion) [x]
**Check:** Does mg_to_af() use factor 3.06889, return 5 decimals, handle None, include USGS citation?
**Location:** mg_to_af() lines 495-525
**Document:** Add row to PRD Compliance table
**Pass if:** Factor 1_000_000/325_851, round(...,5), USGS comment present

---

### US-R10: Verify PRD US-008 (AF Validation) [x]
**Check:** Does validate_af_conversion() round to 2 decimals for comparison, return OK/NOT_OK?
**Location:** validate_af_conversion() lines 451-492
**Document:** Add row to PRD Compliance table
**Pass if:** round(...,2) used, returns "OK" or "NOT_OK"

---

### US-R11: Verify PRD US-009 (Monthly CSV Format) [x]
**Check:** Does generate_monthly_csv() use correct filename, column order, decimal precision, sort by well?
**Location:** generate_monthly_csv() lines 724-913
**Document:** Add row to PRD Compliance table
**Pass if:** buckman_{year}_{month_numeric}_{month_abbrev}.csv, columns: OSE_Number, Well_Name, MG_Month(3dp), AF_Calculated(5dp), AF_Reported(2dp), AF_Verification, Meter_Reading

---

### US-R12: Verify PRD US-010 (Totals Rows) [x]
**Check:** Are Calculated_Sum, PDF_Total, and Total_Verification rows added to CSV?
**Location:** generate_monthly_csv() lines 833-878
**Document:** Add row to PRD Compliance table
**Pass if:** All three rows present, MG tolerance 0.01, AF tolerance 0.001

---

### US-R13: Verify PRD US-011 (Single Month Processing) [x]
**Check:** Does process_single_month() construct correct paths, return (success, not_ok_values)?
**Location:** process_single_month() lines 1174-1247
**Document:** Add row to PRD Compliance table
**Pass if:** Paths ./input/pdfs/{year}_{month}_{abbrev}.pdf and ./output/ingested_data/buckman_...

---

### US-R14: Verify PRD US-012 (All Months Processing) [x]
**Check:** Does process_all_months() iterate 01-12, collect all NOT_OK values, continue on missing?
**Location:** process_all_months() lines 1133-1171
**Document:** Add row to PRD Compliance table
**Pass if:** Uses MONTHS_ORDERED constant, logs skipped months

---

### US-R15: Verify PRD US-013 (Annual Summary CSV) [x]
**Check:** Does generate_annual_summary_csv() produce correct structure with 6 decimal AF values?
**Location:** generate_annual_summary_csv() lines 996-1130
**Document:** Add row to PRD Compliance table
**Pass if:** Filename buckman_{year}_table_2_data.csv, headers Well/JAN-DEC/Total, 6 decimal places

---

### US-R16: Verify PRD US-014 (Input Summary CSV) [x]
**Check:** Does generate_input_summary_csv() list all NOT_OK values with location details?
**Location:** generate_input_summary_csv() lines 916-993
**Document:** Add row to PRD Compliance table
**Pass if:** Columns Year/Month/Well/Field/Issue, creates file with headers if no issues

---

### US-R17: Verify PRD US-015 (Main Entry Point) [x]
**Check:** Does main block accept year arg, create dirs, process all, generate summaries, print QA message?
**Location:** if __name__ == "__main__": lines 1687-1755
**Document:** Add row to PRD Compliance table
**Pass if:** All steps present, QA/QC message printed at end

---

### US-R18: Verify PRD US-016 (PDF Validation) [x]
**Check:** Does validate_and_prepare_pdfs() scan all PDFs, extract dates, create standard copies, detect issues?
**Location:** validate_and_prepare_pdfs() lines 1350-1484
**Document:** Add row to PRD Compliance table
**Pass if:** Creates {year}_{month}_{abbrev}.pdf copies, reports missing/duplicate/wrong_year/unreadable

---

### US-R19: Verify PRD US-017 (Interactive Year Selection) [x]
**Check:** Does get_year_interactively() auto-detect years from PDFs, prompt user, validate 1990-2100?
**Location:** get_year_interactively() lines 1487-1548
**Document:** Add row to PRD Compliance table
**Pass if:** Scans PDFs, shows detected years, validates range

---

### US-R20: Verify PRD US-018 (Pre-Flight Report) [x]
**Check:** Does display_preflight_report() show coverage, sources, prompt Y/n or y/N based on issues?
**Location:** display_preflight_report() lines 1551-1650
**Document:** Add row to PRD Compliance table
**Pass if:** Shows month-by-month status, prompts correctly for issues/no issues

---

### US-R21: Verify PRD US-019 (System Dependency Check) [x]
**Check:** Does check_system_dependencies() verify Tesseract and Poppler with install instructions?
**Location:** check_system_dependencies() lines 73-133
**Document:** Add row to PRD Compliance table
**Pass if:** Checks both, shows apt-get and brew commands, exits non-zero if missing

---

### US-R22: Verify PRD US-020 (Configuration Constants) [x]
**Check:** Are all 9 constants defined with comments: OCR_CONFIDENCE_THRESHOLD, HEADER_CROP_RATIO, TABLE_CROP_RATIO, LINE_GROUPING_TOLERANCE_PX, PDF_CONVERSION_DPI, MG_VERIFICATION_TOLERANCE, AF_VERIFICATION_TOLERANCE, MONTHS_ABBREV, MONTHS_ORDERED?
**Location:** Lines 35-70
**Document:** Add row to PRD Compliance table
**Pass if:** All 9 constants defined with comments

---

### US-R23: Verify PRD US-021 (is_confident Helper) [x]
**Check:** Does is_confident() handle -1 as invalid, compare >= threshold, use default threshold?
**Location:** is_confident() lines 168-195
**Document:** Add row to PRD Compliance table
**Pass if:** Returns False for -1, uses >= comparison, default OCR_CONFIDENCE_THRESHOLD

---

### US-R24: Verify PRD US-022 (Atomic File Writes) [x]
**Check:** Does generate_monthly_csv() use tempfile + shutil.move for atomic writes?
**Location:** generate_monthly_csv() lines 880-897
**Document:** Add row to PRD Compliance table
**Pass if:** tempfile.NamedTemporaryFile then shutil.move

---

### US-R25: Verify PRD US-023 (Enhanced Error Messages) [x]
**Check:** Do exception handlers print type, message, and abbreviated traceback?
**Location:** pdf_to_image() lines 252-262, extract_date_from_pdf() lines 358-362
**Document:** Add row to PRD Compliance table
**Pass if:** Shows exception type, message, last 2 traceback frames

---

### US-R26: Verify PRD US-024 (Progress Feedback) [x]
**Check:** Is progress shown as (current/total) during PDF scanning?
**Location:** validate_and_prepare_pdfs() line 1414
**Document:** Add row to PRD Compliance table
**Pass if:** Format "(3/12) Scanning: filename..."

---

## Error Handling

### US-R27: Check pdf_to_image error handling [x]
**Check:** Does pdf_to_image() handle missing file, conversion failure?
**Location:** pdf_to_image() lines 215-263
**Document:** Add row to Error Handling table
**Pass if:** Checks path.exists(), catches Exception, returns None, logs with file path

---

### US-R28: Check extract_date_from_pdf error handling [x]
**Check:** Does it handle OCR failure, no pattern match, invalid month?
**Location:** extract_date_from_pdf() lines 266-362
**Document:** Add row to Error Handling table
**Pass if:** Returns (0, "NOT_OK", "NOT_OK", "NOT_OK") on all error paths

---

### US-R29: Check extract_buckman_wells_data error handling [x]
**Check:** Does it handle OCR failure, no table found?
**Location:** extract_buckman_wells_data() lines 365-448
**Document:** Add row to Error Handling table
**Pass if:** Returns ([], None) on error, logs exception

---

### US-R30: Check _parse_table_row error handling [x]
**Check:** Does it handle missing fields, parse failures?
**Location:** _parse_table_row() lines 549-644
**Document:** Add row to Error Handling table
**Pass if:** Uses try/except for float/int parsing, leaves fields as None if missing

---

### US-R31: Check generate_monthly_csv error handling [x]
**Check:** Does it handle write failures, clean up temp files?
**Location:** generate_monthly_csv() lines 724-913
**Document:** Add row to Error Handling table
**Pass if:** Catches Exception, logs error, temp file in output dir for same-device move

---

### US-R32: Check validate_and_prepare_pdfs error handling [x]
**Check:** Does it handle missing dir, copy failures?
**Location:** validate_and_prepare_pdfs() lines 1350-1484
**Document:** Add row to Error Handling table
**Pass if:** scan_input_pdfs handles missing dir, shutil.copy2 in try block

---

## Edge Cases

### US-R33: Check confidence threshold boundary [x]
**Check:** Is confidence of exactly 95 treated as passing?
**Location:** is_confident() lines 168-195
**Document:** Add row to Edge Cases table
**Pass if:** Uses >= not > so 95 passes

---

### US-R34: Check well number boundary values [x]
**Check:** Are wells #1 and #13 correctly sorted as first and last?
**Location:** well_sort_key() in generate_monthly_csv() lines 762-768
**Document:** Add row to Edge Cases table
**Pass if:** Extracts number, sorts correctly

---

### US-R35: Check zero MG value handling [x]
**Check:** Is MG=0.000 (well not pumped) handled as valid?
**Location:** _parse_table_row() lines 608-618, mg_to_af() lines 495-525
**Document:** Add row to Edge Cases table
**Pass if:** 0.0 is valid input, converts to 0.00000 AF

---

### US-R36: Check well name normalization variations [x]
**Check:** Are "Buckman#1", "Buckman # 1", "Buckman 1", "buckman #1" all normalized?
**Location:** _normalize_well_name() lines 528-546
**Document:** Add row to Edge Cases table
**Pass if:** Regex extracts number, returns "Buckman #{N}"

---

### US-R37: Check empty wells list handling [x]
**Check:** What happens if OCR returns zero wells?
**Location:** process_single_month() line 1228
**Document:** Add row to Edge Cases table
**Pass if:** Checks "if not wells:", returns (False, [])

---

### US-R38: Check None values in WellData [x]
**Check:** Are None field values handled throughout pipeline?
**Location:** generate_monthly_csv() lines 776-820
**Document:** Add row to Edge Cases table
**Pass if:** Checks "is not None" before formatting

---

## Input Validation

### US-R39: Check year argument validation [x]
**Check:** Is command-line year validated as integer and within range?
**Location:** main block lines 1695-1708, get_year_interactively() line 1539
**Document:** Add row to Input Validation table
**Pass if:** int() conversion with ValueError handling, 1990-2100 range check

---

### US-R40: Check OCR output sanitization [x]
**Check:** Are extracted patterns validated before use (month name, year, OSE number)?
**Location:** extract_date_from_pdf() line 318, _parse_table_row() line 576
**Document:** Add row to Input Validation table
**Pass if:** Month name checked against MONTH_NAME_TO_NUMERIC, OSE pattern validated

---

### US-R41: Check interactive input validation [x]
**Check:** Is Y/N input validated in display_preflight_report()?
**Location:** display_preflight_report() lines 1635-1650
**Document:** Add row to Input Validation table
**Pass if:** Handles y/yes/n/no/empty, loops on invalid

---

## Security

### US-R42: Check path construction safety [x]
**Check:** Are file paths constructed safely without user-controlled path components?
**Location:** Lines 1205, 1234, 1462-1467
**Document:** Add row to Security table
**Pass if:** Year is integer (no path traversal), filenames from os.basename()

---

### US-R43: Check subprocess safety [x]
**Check:** Is subprocess.run() called safely without shell=True?
**Location:** check_system_dependencies() lines 100-103
**Document:** Add row to Security table
**Pass if:** List form ["pdftoppm", "-v"], no shell=True

---

### US-R44: Check temp file handling [x]
**Check:** Are temp files created securely and cleaned up?
**Location:** generate_monthly_csv() lines 887-897
**Document:** Add row to Security table
**Pass if:** NamedTemporaryFile in output dir, moved atomically

---

## Performance

### US-R45: Check duplicate OCR processing [x]
**Check:** Are PDFs OCRed twice (validation phase and processing phase)?
**Location:** validate_and_prepare_pdfs() line 1417, process_single_month() line 1215
**Document:** Add row to Performance table
**Pass if:** Document if this is intentional (different crop regions)

---

### US-R46: Check CSV re-reading [x]
**Check:** Are monthly CSVs re-read multiple times in summary generation?
**Location:** generate_input_summary_csv() line 956, generate_annual_summary_csv() line 1035
**Document:** Add row to Performance table
**Pass if:** Document observation (acceptable for 12 small files)

---

## Code Quality

### US-R47: Check for unused imports [x]
**Check:** Are all imports used in the code?
**Location:** Lines 18-32
**Document:** Add row to Code Quality table
**Pass if:** All imports have usage

---

### US-R48: Check for magic numbers [x]
**Check:** Are there any hardcoded numbers that should be constants?
**Location:** Entire file - search for numeric literals
**Document:** Add row to Code Quality table
**Pass if:** All thresholds/tolerances use named constants

---

### US-R49: Check type hint coverage [x]
**Check:** Do all functions have type hints for parameters and return values?
**Location:** All function definitions
**Document:** Add row to Code Quality table
**Pass if:** All functions typed, mypy passes

---

## Final Summary

### US-R50: Compile executive summary [x]
**Check:** Count all findings by severity, identify top 3 issues, provide overall assessment
**Location:** Review all findings documented in previous stories
**Document:** Fill in Executive Summary section in REVIEW_FINDINGS.md
**Pass if:** Totals accurate, top issues identified, overall assessment provided

---

## Completion

When all stories are complete, output: <promise>COMPLETE</promise>
