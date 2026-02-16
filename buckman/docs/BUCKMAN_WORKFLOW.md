# Buckman Wellfield Annual Depletion Workflow

## Overview

This document describes the annual process to calculate stream depletion impacts from Buckman wellfield pumping. The workflow produces five regulatory tables required for Santa Fe water rights compliance.

## Output Tables

| Table | Description | Output Location |
|-------|-------------|-----------------|
| **Table 1** | Historical pumping by well (1988-present) | `output/ingested_data/` |
| **Table 2** | Current year monthly pumping detail | `output/ingested_data/` |
| **Table 3** | Rio Pojoaque-Nambe & Rio Tesuque depletions | `output/depletion/` |
| **Table 4** | Rio Grande above/below Otowi depletions | `output/depletion/` |
| **Table 5** | La Cienega Springs cumulative depletions | `output/depletion/` |

---

## Prerequisites

### Software
- Python 3.10+ with pandas, openpyxl
- Wine (for running MODFLOW post-processor on Linux)
- MODFLOW96 (optional - if re-running model)

### Input Data
- Monthly pumping XML reports from City of Santa Fe
- MODFLOW96 model files (in `output/modflow/`)

---

## Step-by-Step Process

### Step 1: Obtain Pumping Data

Get daily pumping data CSV from City of Santa Fe for the reporting year.

Place CSV in `input/csv/` directory with naming convention:
```
input/csv/Buckman_Well_Prod_YYYY.csv
```
Example: `input/csv/Buckman_Well_Prod_2025.csv`

The CSV contains 365/366 daily rows with MGD values for all 13 Buckman wells.

---

### Step 2: Generate Tables 1 & 2 (Pumping Data)

```bash
python3 step1_ingest_buckman_data.py --year YYYY
```

**Outputs:**
- `output/ingested_data/YYYY_Table_1_updated.xlsx` - Historical pumping by well
- `output/ingested_data/YYYY_Table_2_output.xlsx` - Monthly pumping detail
- `output/ingested_data/YYYY_MM_MON.csv` - Monthly breakdown files

**Verify:**
- Total pumping is within historical range (typically 500-6000 AFY)
- All 13 wells are present
- No negative or missing values

---

### Step 3: Generate MODFLOW Files

```bash
python3 step2_update_modflow.py --year YYYY
```

**Inputs:**
- For baseline year (2024): `input/modflow/2023/thruCY2165.wel`
- For subsequent years: `output/modflow/{YYYY-1}/thruCY2165_{YYYY-1}.wel`

**Outputs:**
- `output/modflow/YYYY/thruCY2165_YYYY.wel` - Updated well file
- `output/modflow/YYYY/CY{YYYY}.nam` - MODFLOW name file

**Verify WEL File:**
```bash
head -50 output/modflow/YYYY/thruCY2165_YYYY.wel
```
- Total pumping matches Table 2 annual total
- All 13 wells are present
- Monthly values look reasonable

---

### Step 4: Run MODFLOW96

*Note: This step may already be complete if flux files exist.*

Navigate to model directory and run MODFLOW:
```bash
cd output/modflow/YYYY
wine modflow96.exe CY{YYYY}.nam
```

**Outputs:**
- `CY{YYYY}_ghb.flx` (~31 MB)
- `CY{YYYY}_riv.flx` (~31 MB)
- `CY{YYYY}.lst` (listing file)

---

### Step 4a: Verify MODFLOW Run

Run the verification script to check MODFLOW output:
```bash
python3 verify_modflow_run.py
```

The script auto-detects the year from the directory name and checks:
- Output files exist (lst, ghb.flx, riv.flx)
- Listing file shows normal termination
- Pumping rates match Table 2 values

**Output:** `{YYYY}_verify_modflow.md` - Verification report

**If verification fails:** Check the markdown report for specific issues. Common problems:
- Missing flux files → MODFLOW didn't run to completion
- Pumping rate mismatch → Re-run Step 3 (step2_update_modflow.py)

---

### Step 5: Run Post-processor

Run the stream flux post-processor to extract depletion data:

```bash
cd output/modflow/YYYY
wine sfmodflx_2245.exe
```

**Output:**
- `CY{YYYY}_dep` text file (~1.5 MB)

---

### Step 5a: Verify Depletion Output

Run the verification script to check post-processor output:
```bash
python3 verify_depletion.py
```

The script auto-detects the year from the directory name and checks:
- File structure (timesteps, year sections)
- Summary values for all locations (R POJOAQUE, R TESUQUE, RIO GRANDE, LC SPRINGS)
- Reasonableness vs. prior year (within 50% tolerance)
- All values are positive (depletion reduces streamflow)

**Output:** `{YYYY}_verify_depletion.md` - Verification report with monthly comparison

**If verification fails:** Check the markdown report for specific issues:
- File structure error → Re-run sfmodflx_2245.exe
- Large deviation from prior year → Verify pumping data is correct

---

### Step 6: Generate Tables 3, 4, 5 (Depletion Tables)

```bash
python3 step4_generate_depletion_tables.py --year YYYY
```

**Outputs:**
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_YYYY.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_YYYY.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_YYYY.xlsx`

---

### Step 7: Validate Results

#### If Validation Files Available
Compare outputs against validation files in `validation/` directory.

#### If No Validation Files (future years)
Apply sanity checks:

| Metric | Expected Range | Notes |
|--------|----------------|-------|
| Total pumping | 500-6000 AFY | Historical range |
| Pojoaque depletion | 50-70 AF | Proportional to pumping |
| Tesuque depletion | 32-40 AF | Residual component decreasing |
| La Cienega cumulative | Increasing ~0.2 AF/year | Must exceed prior year |
| All values | ≥ 0 | No negative depletions |

---

## Quick Reference: Command Summary

```bash
# Step 2: Generate Tables 1 & 2
python3 step1_ingest_buckman_data.py --year 2025

# Step 3: Generate MODFLOW files (copies 10 support files)
python3 step2_update_modflow.py --year 2025

# Steps 4-5a: Run MODFLOW and post-processor
cd output/modflow/2025
wine modflow96.exe CY2025.nam        # Step 4: Run MODFLOW
python3 verify_modflow_run.py        # Step 4a: Verify MODFLOW output
wine sfmodflx_2245.exe               # Step 5: Run post-processor
python3 verify_depletion.py          # Step 5a: Verify depletion output

# Step 6: Generate Tables 3, 4, 5
cd ../../..
python3 step4_generate_depletion_tables.py --year 2025
```

### Example: Processing 2025 Data (Full Workflow)
```bash
# After getting Buckman_Well_Prod_2025.csv in input/csv/:
python3 step1_ingest_buckman_data.py --year 2025
python3 step2_update_modflow.py --year 2025

cd output/modflow/2025
wine modflow96.exe CY2025.nam
python3 verify_modflow_run.py
wine sfmodflx_2245.exe
python3 verify_depletion.py

cd ../../..
python3 step4_generate_depletion_tables.py --year 2025
```

---

## Directory Structure

```
.
├── input/
│   ├── csv/                            # Daily pumping CSV (input)
│   │   └── Buckman_Well_Prod_YYYY.csv  # 365/366 daily rows
│   └── modflow/                        # Baseline MODFLOW files
│       └── 2023/                       # Original baseline year
│           ├── thruCY2165.wel          # Well file template
│           ├── thruCY2165.bas          # Basic package
│           ├── thruCY2165.ghb          # General Head Boundary
│           ├── thruCY2165.oc           # Output Control
│           ├── thruCY2165.riv          # River package
│           ├── sflcs.bcf               # Block-Centered Flow
│           ├── sflcs.sip               # Solver
│           ├── modflow96.exe           # MODFLOW96 executable
│           ├── sfmodflx_2245.exe       # Post-processor executable
│           ├── verify_modflow_run.py   # MODFLOW verification script
│           └── verify_depletion.py     # Depletion verification script
│
├── output/
│   ├── ingested_data/                  # Tables 1 & 2
│   │   ├── YYYY_Table_1_updated.xlsx   # Historical pumping
│   │   ├── YYYY_Table_2_output.xlsx    # Monthly pumping detail
│   │   ├── YYYY_01_JAN.csv             # Monthly breakdown (output)
│   │   └── ...
│   │
│   ├── depletion/                      # Tables 3, 4, 5
│   │   ├── TABLE_3_Rio_Pojoaque_Tesuque_YYYY.xlsx
│   │   ├── TABLE_4_Rio_Grande_Otowi_YYYY.xlsx
│   │   ├── TABLE_5_La_Cienega_Springs_YYYY.xlsx
│   │   └── METHODOLOGY_Tables_3_4_5.md
│   │
│   └── modflow/                        # MODFLOW files (per year)
│       └── YYYY/
│           ├── thruCY2165_YYYY.wel     # Well file (generated)
│           ├── CY{YYYY}.nam            # NAM file (generated)
│           ├── CY{YYYY}.lst            # Listing file (MODFLOW output)
│           ├── CY{YYYY}_ghb.flx        # GHB flux file (MODFLOW output)
│           ├── CY{YYYY}_riv.flx        # RIV flux file (MODFLOW output)
│           ├── CY{YYYY}_dep            # Depletion file (post-processor)
│           ├── {YYYY}_verify_modflow.md    # MODFLOW verification report
│           ├── {YYYY}_verify_depletion.md  # Depletion verification report
│           ├── modflow96.exe           # (copied from baseline)
│           ├── sfmodflx_2245.exe       # (copied from baseline)
│           ├── verify_modflow_run.py   # (copied from baseline)
│           └── verify_depletion.py     # (copied from baseline)
│
├── validation/                         # Reference validation files
│   ├── Table_1_data_afy_2024.xlsx
│   ├── Table_2_2024.xlsx
│   ├── TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx
│   ├── TABLE 4 - Rio Grande, above below Otowi.xlsx
│   └── Table 5 - La Cienega Spring.jpg
│
├── step1_ingest_buckman_data.py        # Tables 1 & 2 generator
├── step2_update_modflow.py             # MODFLOW WEL/NAM file generator
├── step4_generate_depletion_tables.py  # Tables 3, 4, 5 generator
└── stream_depletions.py                # Library: depletion calculations
```

---

## Troubleshooting

### "Year YYYY not found in parsed data"
The post-processor output doesn't contain the requested year. Ensure:
1. WEL file includes the year
2. MODFLOW was run with updated WEL file
3. Post-processor was run after MODFLOW

### "LC SPRINGS not found"
The post-processor output is missing La Cienega Springs data. Check:
1. GHB flux file was processed correctly
2. Post-processor version is correct (sfmodflx_2245.exe)

### Validation mismatch
If calculated values don't match validation:
1. Check input data (pumping totals)
2. Verify post-processor output is current
3. Compare intermediate calculations (CFS values)

---

## File Dependency Chain

The workflow chains years together - each year depends on outputs from the previous year.

### First Year (2024 Baseline)
- Uses 2023 baseline files from `input/modflow/2023/`
- Table 1 starts from validation template
- Creates foundation for all subsequent years

### Subsequent Years (2025+)
- WEL file: Extends from year N-1 output
- Table 1: Extends from year N-1 output (if no validation file)
- Baseline files: Copied fresh from 2023 baseline

**Important:** Always process years sequentially (2024 → 2025 → 2026, etc.)

### Troubleshooting Missing Files

| Error | Cause | Solution |
|-------|-------|----------|
| "Input .wel file not found" | Year N-1 not processed | Run step2 for year N-1 first |
| "Table 2 CSV not found" | Step 1 not run | Run step1 for current year |
| "No template found for Table 1" | Missing validation file AND year N-1 not processed | Create validation file OR run year N-1 first |
| "Flux file not found" | MODFLOW96 not run | Run MODFLOW96 with CY{year}.nam |

### Workflow Verification

After completing all steps for a year, run comprehensive verification:

```bash
python3 step5_verify_workflow.py --year 2025
```

This automated script will:
- Check all output files exist
- Run pytest test suite
- Run custom verification scripts (verify_modflow_run.py, verify_depletion.py)
- Provide pass/fail summary

**Usage examples:**
```bash
# Verify entire workflow for 2025
python3 step5_verify_workflow.py --year 2025

# Verify only step 3 (depletion tables)
python3 step5_verify_workflow.py --year 2025 --step 3

# Show detailed test output
python3 step5_verify_workflow.py --year 2025 --verbose
```

See `docs/FILE_DEPENDENCIES.md` for visual dependency diagram and `docs/NEW_YEAR_CHECKLIST.md` for detailed processing checklist.

---

## Technical Documentation

For detailed methodology:
- [Tables 1 & 2 Methodology](../output/ingested_data/METHODOLOGY_Tables_1_2.md)
- [Tables 3, 4, 5 Methodology](../output/depletion/METHODOLOGY_Tables_3_4_5.md)

For workflow reference:
- [File Dependencies](FILE_DEPENDENCIES.md) - Visual diagram of year-to-year file flow
- [New Year Checklist](NEW_YEAR_CHECKLIST.md) - Step-by-step processing guide

---

*Last updated: February 2026*
