# PRD Prompt Example: Buckman Wellfield Data Ingestion

This shows the template filled out for the Buckman project. Use this as a reference.

---

## 1. PROJECT CONTEXT

### What is this?
A Python script that extracts water production data from scanned PDF reports and converts it to structured CSV files.

### Who uses it and why?
City of Santa Fe water resources staff analyzing Buckman Wellfield depletion for regulatory compliance with the NM Office of State Engineer (OSE). Currently they manually transcribe data from PDFs - this automates that process.

### Stakes & Constraints
Regulatory reporting to OSE. Incorrect data could affect water rights compliance. Data integrity is more important than automation speed - better to flag questionable values for human review than to insert bad data.

### Workflow Position
Step 1 of a multi-step analysis pipeline. This step ingests raw PDFs. Later steps will perform depletion calculations and generate reports. Output CSVs from this step feed into Step 2.

---

## 2. CORE REQUIREMENTS

### Input → Output Summary
12 monthly PDF scans (one per month) containing water production tables → 12 monthly CSVs with validated data + 1 annual summary CSV + 1 flagged-values CSV for human QA/QC.

### Data Transformation Rules
- Extract date from PDF header line: "Re: Diversion Report for {Month} {Year}"
- Extract well production table (13 wells: Buckman #1 through #13)
- Convert MG (million gallons) to AF (acre-feet) using USGS factor
- Validate: compare calculated AF with City-reported AF
- Flag discrepancies as "NOT_OK" for human review

### Validation Requirements
- MG values must be positive numbers
- Calculated AF = MG × 3.06889 (USGS conversion)
- If |calculated_AF - reported_AF| > 0.01, flag as NOT_OK
- OCR confidence must be ≥95% or flag value

---

## 3. FILE & DATA SPECS

### Input
- **Location:** `./input/pdfs/`
- **Format:** Scanned PDF (first page only contains data table)
- **Naming pattern:** Varies - files may have arbitrary names
- **Example filename:** `Buckman_January_2024.pdf` or `scan001.pdf`

### Output
- **Location:** `./output/ingested_data/`
- **Format:** CSV
- **Naming pattern:** `buckman_{year}_{MM}_{MON}.csv`
- **Example filename:** `buckman_2024_01_JAN.csv`

### Sample Data
```
Input (from PDF table):
| OSE No. | Well Name   | MG    | AF    |
|---------|-------------|-------|-------|
| RG-85763| Buckman #1  | 12.345| 37.88 |

Output (CSV):
ose_number,well_name,mg,af,af_calculated,af_status,confidence
RG-85763,Buckman #1,12.345,37.88,37.88,OK,98
```

---

## 4. QUALITY & INTEGRITY

### Critical Invariants
DO NOT insert questionable values. If OCR confidence is low or values don't validate, flag as NOT_OK. A human must review flagged values. Bad data in regulatory reports is worse than delayed reports.

### Validation Strategy
- [x] **Strict:** Reject anything questionable, flag for human review

If in doubt, flag it. Create `input_summary.csv` listing all NOT_OK values for human review.

### Human Review Points
- Pre-flight: Show validation report, require user confirmation before processing
- Post-processing: Review `input_summary.csv` for all flagged values
- User creates `input_summary_corrected.csv` with manual corrections

---

## 5. TECHNICAL REFERENCES

### Constants & Conversion Factors
| Constant | Value | Source |
|----------|-------|--------|
| MG_TO_AF | 3.06889 | USGS Water Science School |
| OCR_CONFIDENCE_THRESHOLD | 95 | Project standard |
| AF_TOLERANCE | 0.01 | Acceptable rounding difference |

### External Standards
- USGS conversion: 1 million gallons = 3.06889 acre-feet
- Source: https://water.usgs.gov/water-resources/

### Existing Code to Integrate
None - greenfield project. Use standard Python libraries (pandas, pytesseract, pdf2image).

---

## 6. ROBUSTNESS CHECKLIST

### Dependencies
- [x] Requires external tools: Tesseract OCR, Poppler (pdf2image)
- [x] Requires Python packages: pandas, pytesseract, pdf2image, Pillow

### Error Handling
- [x] Continue processing, collect all errors

Process all 12 months even if some fail. Log all errors for review.

### User Experience
- [x] Needs progress feedback (OCR is slow)
- [x] Needs pre-flight validation before processing
- [x] Needs interactive prompts (confirm year, confirm proceed after validation)

### File Safety
- [x] Use atomic writes (prevent corruption on crash)
- [x] Preserve original inputs (work on copies during standardization)

### Code Quality
- [x] Extract magic numbers to named constants
- [x] Add detailed comments for beginners

---

## 7. NON-GOALS

### Explicitly Out of Scope
- Multi-page PDF support (data is always on page 1)
- Automatic correction of bad values (human must review)
- Historical data before 2020 (different format)
- Email/notification when complete

### Future Phases
- Step 2: Depletion calculations
- Step 3: Report generation
- ML-based OCR correction (maybe someday)

---

## 8. ADDITIONAL CONTEXT

### Known Edge Cases
- Some months may be missing (handle gracefully)
- PDF scan quality varies (hence strict OCR confidence threshold)
- Well names may have OCR errors ("Buckman #l" vs "#1")

### Examples of Similar Work
None provided.

### Questions for Claude
- Should we support command-line year override or always prompt interactively?
- How should we handle a month with zero production (all wells = 0)?

---

# Result

This prompt generated a 24-story PRD covering:
- Core data extraction (US-001 to US-015)
- Input validation & UX (US-016 to US-018)
- System robustness (US-019 to US-024)

The robustness checklist ensured Claude added:
- Dependency checking with install instructions
- Progress feedback during OCR
- Atomic file writes
- Configuration constants
- Pre-flight validation
