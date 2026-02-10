# Plan: Complete 2024 Buckman Wellfield Workflow

## Current State Assessment

### Tables 1 & 2: COMPLETE
- Output files exist: `output/ingested_data/2024_Table_1_updated.xlsx`, `2024_Table_2_output.xlsx`
- Generated today (Feb 10, 2026)
- Total: **1,372.92 AFY** (matches expected)
- All 13 wells verified, 4 minor daily rounding discrepancies (within tolerance)

### Tables 3, 4, 5: CODE COMPLETE, NOT EXECUTED
- All generation/formatting/validation code exists in `stream_depletions.py` (2,006 lines)
- Orchestration workflow exists in `generate_depletion_tables.py` (905 lines)
- **No output files exist** - `output/depletion/` directory does not exist

### Prerequisites Already Met
- Post-processor output exists: `output/modflow/2024/depletions/CY2024` (1.5 MB)
- Flux files exist: `CY2024_riv.flx`, `CY2024_ghb.flx` (31 MB each)
- Post-processor executable: `sfmodflx_2245.exe` present

---

## Gap Analysis

| Gap | Description | Resolution |
|-----|-------------|------------|
| **G1** | Tables 3,4,5 not generated | Run `generate_depletion_tables.py` |
| **G2** | Table 5 validation is JPG | Create Excel validation file OR manual comparison |
| **G3** | Tables 1,2 not formally validated | Compare against `validation/Table_1_data_afy_2024.xlsx`, `Table_2_2024.xlsx` |

---

## Execution Plan

### Phase 1: Create Table 5 Validation File
**Goal**: Create Excel validation file from JPG, get user confirmation

1. Create `validation/Table_5_La_Cienega_Springs.xlsx` with data extracted from JPG
2. **CHECKPOINT**: Pause for user to verify Excel matches JPG before proceeding

### Phase 2: Validate Tables 1 & 2
**Goal**: Confirm generated Tables 1 & 2 match validation data

1. Compare `output/ingested_data/2024_Table_2_output.xlsx` against `validation/Table_2_2024.xlsx`
   - Key values: 13 wells × 12 months grid, annual total = 1,372.92 AFY

2. Compare `output/ingested_data/2024_Table_1_updated.xlsx` against `validation/Table_1_data_afy_2024.xlsx`
   - Key values: 2024 row totals, well percentages

3. Report any discrepancies

### Phase 3: Generate Tables 3, 4, 5
**Goal**: Execute the depletion tables workflow

1. Run: `python3 generate_depletion_tables.py --year 2024`

2. Workflow executes these steps (US-001 through US-015):
   - Copy flux files (already present, will verify)
   - Run post-processor via Wine (sfmodflx_2245.exe)
   - Parse output → extract stream depletions → extract Otowi cells
   - Load Core (2003) analytical residuals
   - Generate Table 3, 4, 5 data
   - Write XLSX files to `output/depletion/`
   - Validate against Excel validation files (including new Table 5 validation file)

3. Expected output files:
   - `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx`
   - `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx`
   - `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx`

### Phase 4: Validate Tables 3, 4, 5
**Goal**: Confirm outputs match validation data

1. **Table 3** - Auto-validated against `validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx`
   - Expected 2024: Pojoaque 60.797 AF, Tesuque 33.583 AF

2. **Table 4** - Auto-validated against `validation/TABLE 4 - Rio Grande, above below Otowi.xlsx`
   - Expected 2024: Above Otowi 101.43 AF, Below Otowi 842.94 AF, Total 944.37 AF

3. **Table 5** - Auto-validated against new `validation/Table_5_La_Cienega_Springs.xlsx`
   - Expected 2024 cumulative: **3.74 AF**

### Phase 5: Address Validation Failures (if any)
- Debug any discrepancies
- Fix code if needed
- Re-run and re-validate

---

## Expected Validation Values (from JPG & PRD)

### Table 5 - La Cienega Springs (cumulative AF)
| Year | Total |
|------|-------|
| 2022 | 3.37 |
| 2023 | 3.54 |
| **2024** | **3.74** |
| 2025 | 3.92 |

---

## Critical Files

| File | Purpose |
|------|---------|
| `generate_depletion_tables.py` | Main orchestrator - run this |
| `stream_depletions.py` | Table 3,4,5 generation, formatting, validation |
| `ingest_buckman_data.py` | Table 1,2 generation (already run) |
| `validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx` | Table 3 validation reference |
| `validation/TABLE 4 - Rio Grande, above below Otowi.xlsx` | Table 4 validation reference |
| `validation/Table 5 - La Cienega Spring.jpg` | Table 5 validation source (image) |
| `validation/Table_5_La_Cienega_Springs.xlsx` | **TO CREATE** - Table 5 validation Excel |

---

## Table 5 Validation File Creation

The Table 5 validation file is a JPG image. Will create Excel validation file from JPG data.

**Data extracted from JPG (La Cienega Springs cumulative AF):**
| Year | Total | Year | Total |
|------|-------|------|-------|
| 2004 | 0.45 | 2018 | 2.75 |
| 2005 | 0.66 | 2019 | 2.90 |
| 2006 | 0.83 | 2020 | 3.06 |
| 2007 | 0.99 | 2021 | 3.21 |
| 2008 | 1.16 | 2022 | 3.37 |
| 2009 | 1.32 | 2023 | 3.54 |
| 2010 | 1.49 | **2024** | **3.74** |
| 2011 | 1.65 | 2025 | 3.92 |
| 2012 | 1.82 | 2026 | 4.10 |
| 2013 | 1.97 | 2027 | 4.27 |
| 2014 | 2.13 | 2028 | 4.46 |
| 2015 | 2.29 | 2029 | 4.62 |
| 2016 | 2.45 | 2030 | 4.80 |
| 2017 | 2.60 | | |

**CHECKPOINT**: After creating `validation/Table_5_La_Cienega_Springs.xlsx`, pause for user to confirm data is correct before proceeding.

---

## Commands to Execute

```bash
# Phase 1: Create Table 5 validation Excel from JPG data
# (will create validation/Table_5_La_Cienega_Springs.xlsx)
# **CHECKPOINT** - pause for user confirmation

# Phase 2: Verify Tables 1,2 (read-only comparison)
# (will use Python/pandas to compare Excel files)

# Phase 3: Generate Tables 3,4,5
python3 generate_depletion_tables.py --year 2024

# Phase 4: Review output
ls -la output/depletion/
```
