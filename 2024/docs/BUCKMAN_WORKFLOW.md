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

Get monthly XML reports from City of Santa Fe for the reporting year.

Place CSV exports in `input/` directory with naming convention:
```
input/YYYY_MM_MON.csv
```
Example: `input/2024_01_JAN.csv`, `input/2024_02_FEB.csv`, etc.

---

### Step 2: Generate Tables 1 & 2 (Pumping Data)

```bash
python3 ingest_buckman_data.py --year YYYY
```

**Outputs:**
- `output/ingested_data/YYYY_Table_1_updated.xlsx`
- `output/ingested_data/YYYY_Table_2_output.xlsx`
- `output/modflow/YYYY/thruCY2165_YYYY.wel` (MODFLOW well file)

**Verify:**
- Total pumping is within historical range (typically 500-6000 AFY)
- All 13 wells are present
- No negative or missing values

---

### Step 3: Verify WEL File

Manually inspect the generated WEL file to ensure:
- Total pumping matches Table 2 annual total
- All 13 wells are present
- Monthly values look reasonable

```bash
# Quick check of WEL file
head -50 output/modflow/YYYY/thruCY2165_YYYY.wel
```

---

### Step 4: Run MODFLOW96

*Note: This step may already be complete if flux files exist.*

Navigate to model directory and run MODFLOW:
```bash
cd output/modflow/YYYY
# Run MODFLOW with appropriate NAM file
```

**Outputs:**
- `CYYYYY_ghb.flx` (~31 MB)
- `CYYYYY_riv.flx` (~31 MB)

---

### Step 5: Run Post-processor

Run the stream flux post-processor to extract depletion data:

```bash
cd output/modflow/YYYY/depletions
wine sfmodflx_2245.exe
```

**Output:**
- `CYYYYY` text file (~1.5 MB)

**Verify:** File contains data through the reporting year with LC SPRINGS, R POJOAQUE, R TESUQUE, and RIO GRANDE sections.

---

### Step 6: Generate Tables 3, 4, 5 (Depletion Tables)

```bash
python3 generate_depletion_tables.py --year YYYY
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
python3 ingest_buckman_data.py --year 2024

# Step 5: Run post-processor (if needed)
cd output/modflow/2024/depletions && wine sfmodflx_2245.exe

# Step 6: Generate Tables 3, 4, 5
python3 generate_depletion_tables.py --year 2024
```

---

## Directory Structure

```
.
├── input/                              # Monthly pumping CSV files
│   ├── 2024_01_JAN.csv
│   ├── 2024_02_FEB.csv
│   └── ...
│
├── output/
│   ├── ingested_data/                  # Tables 1 & 2
│   │   ├── 2024_Table_1_updated.xlsx
│   │   ├── 2024_Table_2_output.xlsx
│   │   └── METHODOLOGY_Tables_1_2.md
│   │
│   ├── depletion/                      # Tables 3, 4, 5
│   │   ├── TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx
│   │   ├── TABLE_4_Rio_Grande_Otowi_2024.xlsx
│   │   ├── TABLE_5_La_Cienega_Springs_2024.xlsx
│   │   └── METHODOLOGY_Tables_3_4_5.md
│   │
│   └── modflow/                        # MODFLOW files
│       └── 2024/
│           ├── thruCY2165_2024.wel     # Well file
│           └── depletions/
│               ├── CY2024              # Post-processor output
│               ├── CY2024_ghb.flx      # GHB flux file
│               └── CY2024_riv.flx      # RIV flux file
│
├── validation/                         # Reference validation files
│   ├── Table_1_data_afy_2024.xlsx
│   ├── Table_2_2024.xlsx
│   ├── TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx
│   ├── TABLE 4 - Rio Grande, above below Otowi.xlsx
│   └── Table 5 - La Cienega Spring.jpg
│
├── ingest_buckman_data.py              # Tables 1 & 2 generator
├── generate_depletion_tables.py        # Tables 3, 4, 5 generator
└── stream_depletions.py                # Core depletion calculations
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

## Technical Documentation

For detailed methodology:
- [Tables 1 & 2 Methodology](../output/ingested_data/METHODOLOGY_Tables_1_2.md)
- [Tables 3, 4, 5 Methodology](../output/depletion/METHODOLOGY_Tables_3_4_5.md)

---

*Last updated: February 2026*
