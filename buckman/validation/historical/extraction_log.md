# Historical Data Extraction Log

## Overview

This log documents the provenance of all historical data extracted for the Buckman Wellfield validation baseline (2022-2024).

---

## Source Documents

### 2022 Data
- **Source File:** `reports/Memo_bkmanISCWRD_2022_ANALYSIS.pdf`
- **Document Title:** Buckman Well Field 2022 Analysis
- **Extraction Date:** 2026-02-17
- **Extraction Method:** Manual extraction from PDF tables using Claude Code
- **Tables Extracted:** Tables 1-5

### 2023 Data
- **Source File:** `reports/MSC_2024_001_Buckman Well Field_2023_ANALYSIS.pdf`
- **Document Title:** Buckman Well Field 2023 Analysis (MSC-2024-001)
- **Extraction Date:** 2026-02-17
- **Extraction Method:** Manual extraction from PDF tables using Claude Code
- **Tables Extracted:** Tables 1-5

### 2024 Data
- **Source Files:** `validation/2024/expected_outputs/`
  - `expected_table1_annual_pumping.csv`
  - `expected_table2_monthly_pumping.csv`
  - `expected_table3_stream_depletions.csv`
  - `expected_table4_rio_grande_depletions.csv`
  - `expected_table5_la_cienega_depletions.csv`
- **Extraction Date:** 2026-02-17
- **Extraction Method:** Programmatic extraction from existing validation files
- **Tables Extracted:** Tables 1-5

---

## Raw Extraction Files

All raw extractions are stored in `validation/historical/raw_extractions/`:

| File | Source | Rows | Description |
|------|--------|------|-------------|
| `2022_Table_1_raw.csv` | 2022 PDF | 1 | Annual pumping by well (AF) |
| `2022_Table_2_raw.csv` | 2022 PDF | 14 | Monthly pumping by well (AF) |
| `2022_Table_3_raw.csv` | 2022 PDF | 1 | Stream depletions - Pojoaque/Tesuque (AF) |
| `2022_Table_4_raw.csv` | 2022 PDF | 2 | Rio Grande depletions Above/Below Otowi (AF) |
| `2022_Table_5_raw.csv` | 2022 PDF | 1 | La Cienega Spring depletions (AF) |
| `2023_Table_1_raw.csv` | 2023 PDF | 1 | Annual pumping by well (AF) |
| `2023_Table_2_raw.csv` | 2023 PDF | 14 | Monthly pumping by well (AF) |
| `2023_Table_3_raw.csv` | 2023 PDF | 1 | Stream depletions - Pojoaque/Tesuque (AF) |
| `2023_Table_4_raw.csv` | 2023 PDF | 2 | Rio Grande depletions Above/Below Otowi (AF) |
| `2023_Table_5_raw.csv` | 2023 PDF | 1 | La Cienega Spring depletions (AF) |
| `2024_Table_1_raw.csv` | validation files | 1 | Annual pumping by well (AF) |
| `2024_Table_2_raw.csv` | validation files | 14 | Monthly pumping by well (AF) |
| `2024_Table_3_raw.csv` | validation files | 1 | Stream depletions - Pojoaque/Tesuque (AF) |
| `2024_Table_4_raw.csv` | validation files | 2 | Rio Grande depletions Above/Below Otowi (AF) |
| `2024_Table_5_raw.csv` | validation files | 1 | La Cienega Spring depletions (AF) |

---

## Consolidated Historical Files

Multi-year consolidated files in `validation/historical/`:

| File | Years | Description |
|------|-------|-------------|
| `Table_1_historical.xlsx` | 2022-2024 | Annual pumping by well |
| `Table_2_historical.xlsx` | 2022-2024 | Monthly pumping (all wells, all months) |
| `Table_3_historical.xlsx` | 2022-2024 | Stream depletions (Pojoaque/Tesuque) |
| `Table_4_historical.xlsx` | 2022-2024 | Rio Grande depletions (Above/Below Otowi) |
| `Table_5_historical.xlsx` | 2022-2024 | La Cienega Spring depletions |

---

## Key Metrics Summary

### Table 1: Annual Total Pumping (AF)

| Year | Annual_Total |
|------|--------------|
| 2022 | 975.47 |
| 2023 | 866.48 |
| 2024 | 1372.90 |

**Statistics:**
- Min: 866.48 AF
- Max: 1372.90 AF
- Mean: 1071.62 AF
- Std: 266.95 AF

### Table 3: Stream Depletions (AF)

| Year | Rio_Pojoaque_Nambe | Rio_Tesuque |
|------|-------------------|-------------|
| 2022 | 59.844 | 33.490 |
| 2023 | 60.323 | 33.491 |
| 2024 | 60.797 | 33.583 |

**Observation:** Cumulative depletions increase monotonically (physically correct).

### Table 5: La Cienega Depletions (AF)

| Year | La_Cienega_Depletion |
|------|---------------------|
| 2022 | 3.37 |
| 2023 | 3.54 |
| 2024 | 3.74 |

**Observation:** Monotonically increasing (physically correct).

---

## Quality Control Notes

1. **2022 Table 2 discrepancy:** SUM row in extracted data (975.47) matches Table 1 annual total.
2. **2023 Table 2 discrepancy:** SUM row in extracted data (866.52) differs slightly from Table 1 (866.48). Difference: 0.04 AF (rounding).
3. **2024 Table 1 vs Table 2:** Table 1 shows 1372.90 AF, Table 2 SUM shows 1372.95 AF. Difference: 0.05 AF (rounding).
4. **Well naming:** B3 vs B3A naming varies across years. Consolidated as "Well_B3_3A" in Table 1.

---

## Transformations Applied

1. **PDF to CSV:** Manual transcription of table values
2. **Column renaming:** Standardized to snake_case (e.g., "Annual Total" → "Annual_Total")
3. **Well naming:** Unified well naming convention across years
4. **CSV to Excel:** Consolidated using pandas DataFrame

---

## Verification Checksums

See `hashes.json` for SHA-256 hashes of all files in this directory.

---

## Contact

- **Extracted by:** Claude Code (Anthropic)
- **Reviewed by:** [User review pending]
- **Date:** 2026-02-17
