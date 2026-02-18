# Buckman Wellfield Depletion Pipeline

Annual stream depletion calculations for Santa Fe water rights compliance.

---

## Quick Start

### Full Workflow (4 commands)

```bash
python3 step1_ingest_buckman_data.py --year 2024
python3 step2_update_modflow.py --year 2024
./step3_run_modflow.sh --year 2024          # ~5 seconds
python3 step4_generate_depletion_tables.py --year 2024
```

### Verify Results

```bash
python3 step5_verify_workflow.py --year 2024
```

### Expected Outputs

| Table | File | Description |
|-------|------|-------------|
| 1 | `output/ingested_data/2024_Table_1_updated.xlsx` | Historical pumping by well (1988-2024) |
| 2 | `output/ingested_data/2024_Table_2_output.xlsx` | Monthly pumping detail |
| 3 | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx` | Rio Pojoaque & Rio Tesuque depletions |
| 4 | `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx` | Rio Grande above/below Otowi |
| 5 | `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx` | La Cienega Springs cumulative |

---

## Workflow Details

### Step 1: Ingest Pumping Data

```bash
python3 step1_ingest_buckman_data.py --year YYYY
```

**Input:** `input/csv/Buckman_Well_Prod_YYYY.csv` (daily pumping data from City of Santa Fe)

**Outputs:**
- `output/ingested_data/YYYY_Table_1_updated.xlsx` - Historical pumping by well
- `output/ingested_data/YYYY_Table_2_output.xlsx` - Current year monthly pumping

**What it does:**
- Reads daily pumping CSV (365/366 rows per year)
- Converts MGD (million gallons/day) to AF (acre-feet)
- Generates Table 1 (historical by well) and Table 2 (monthly breakdown)

### Step 2: Generate MODFLOW Files

```bash
python3 step2_update_modflow.py --year YYYY
```

**Input:** Prior year's WEL file (e.g., `output/modflow/2023/thruCY2165_2023.wel`)

**Outputs:**
- `output/modflow/YYYY/thruCY2165_YYYY.wel` - Updated well pumping file
- `output/modflow/YYYY/CY{YYYY}.nam` - MODFLOW name file
- 10 baseline support files copied from `input/modflow/2023/`

**What it does:**
- Extends WEL file with new year's monthly pumping rates
- Creates NAM file pointing to all MODFLOW inputs
- Copies baseline files (BAS, BCF, RIV, GHB, OC, SIP, executables)

### Step 3: Run MODFLOW96

```bash
./step3_run_modflow.sh --year YYYY
```

**Runtime:** ~5 seconds

**Outputs:**
- `output/modflow/YYYY/CY{YYYY}.lst` - Listing file
- `output/modflow/YYYY/CY{YYYY}_ghb.flx` - GHB flux (~31 MB)
- `output/modflow/YYYY/CY{YYYY}_riv.flx` - River flux (~31 MB)
- `output/modflow/YYYY/YYYY_verify_modflow.md` - Verification report

**What it does:**
- Runs MODFLOW96 via Wine (on Linux)
- Verifies convergence and output files
- Generates verification markdown report

### Step 4: Generate Depletion Tables

```bash
python3 step4_generate_depletion_tables.py --year YYYY
```

**Input:** MODFLOW flux files from Step 3

**Outputs:**
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_YYYY.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_YYYY.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_YYYY.xlsx`

**What it does:**
- Runs `sfmodflx_2245.exe` post-processor to extract stream depletions
- Parses depletion data by reach (Pojoaque, Tesuque, Rio Grande, La Cienega)
- Generates Tables 3, 4, 5 with cumulative depletions

---

## Prerequisites

### Software

- Python 3.10+ with pandas, openpyxl
- Wine (for running MODFLOW96 and post-processor on Linux)

### Input Data

- Daily pumping CSV from City of Santa Fe: `input/csv/Buckman_Well_Prod_YYYY.csv`
- Format: 365/366 daily rows with MGD values for all 13 Buckman wells

### Installation

```bash
pip install pandas openpyxl
```

---

## Output Tables

| Table | Description | Key Metrics |
|-------|-------------|-------------|
| **Table 1** | Historical pumping by well (1988-present) | Annual totals (AF) by well |
| **Table 2** | Current year monthly pumping | Monthly breakdown (AF) |
| **Table 3** | Rio Pojoaque & Rio Tesuque | Cumulative depletion (AF) 1988-2030 |
| **Table 4** | Rio Grande above/below Otowi | Monthly depletion by reach |
| **Table 5** | La Cienega Springs | Cumulative spring impact (AF) |

### 2024 Key Values

| Metric | Value |
|--------|-------|
| Total pumping | 1,372.92 AF |
| BK-01 (main well) | 601.28 AF |
| Rio Pojoaque depletion | 60.80 AF |
| Rio Tesuque depletion | 33.58 AF |

---

## Verification & Testing

### Comprehensive Verification

```bash
python3 step5_verify_workflow.py --year 2024
```

This script verifies:
- All output files exist with expected sizes
- MODFLOW convergence
- Cross-table consistency (Table 1 total = Table 2 total)
- Physical reasonableness bounds

### Regression Testing

```bash
python3 validation/2024/run_regression_2024.py
```

Cell-by-cell comparison against expected outputs. All 5 tables must PASS.

### Physical Bounds

| Metric | Expected Range | 2024 Actual |
|--------|----------------|-------------|
| Annual pumping | 866-1,373 AF | 1,372.92 AF |
| Rio Pojoaque depletion | 15-65 AF | 60.80 AF |
| Rio Tesuque depletion | 40-180 AF | 33.58 AF* |
| YoY pumping change | < 65% | +58.4% |

*Note: 2024 Rio Tesuque below historical range due to pumping distribution changes.

---

## Directory Structure

```
.
├── input/
│   ├── csv/                            # Daily pumping CSV
│   │   └── Buckman_Well_Prod_YYYY.csv
│   └── modflow/2023/                   # Baseline MODFLOW files
│
├── output/
│   ├── ingested_data/                  # Tables 1 & 2
│   ├── depletion/                      # Tables 3, 4, 5
│   └── modflow/YYYY/                   # MODFLOW files per year
│
├── validation/
│   └── 2024/
│       ├── expected_outputs/           # Reference files
│       └── run_regression_2024.py      # Regression test
│
├── step1_ingest_buckman_data.py        # Tables 1 & 2
├── step2_update_modflow.py             # MODFLOW WEL/NAM
├── step3_run_modflow.sh                # Run MODFLOW96
├── step4_generate_depletion_tables.py  # Tables 3, 4, 5
├── step5_verify_workflow.py            # Comprehensive verify
└── stream_depletions.py                # Depletion library
```

---

## Processing a New Year

When annual pumping data arrives (e.g., 2025):

```bash
# 1. Place input CSV
#    input/csv/Buckman_Well_Prod_2025.csv

# 2. Run full workflow
python3 step1_ingest_buckman_data.py --year 2025
python3 step2_update_modflow.py --year 2025
./step3_run_modflow.sh --year 2025
python3 step4_generate_depletion_tables.py --year 2025

# 3. Verify results
python3 step5_verify_workflow.py --year 2025

# 4. Commit results
git add output/
git commit -m "Complete 2025 Buckman workflow"
```

**File Dependency Chain:** Each year chains from the previous year:
- WEL file: Extends from prior year
- Table 1: Extends from prior year
- Always process years sequentially (2024 → 2025 → 2026)

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Input .wel file not found" | Prior year not processed | Run step2 for year N-1 first |
| "Table 2 CSV not found" | Step 1 not run | Run step1 for current year |
| "Flux file not found" | MODFLOW not run | Run step3 for current year |
| Regression test fails | Code or data issue | Check specific cell differences |

---

## Documentation

### Methodology

- [Tables 1 & 2 Methodology](output/ingested_data/METHODOLOGY_Tables_1_2.md)
- [Tables 3, 4, 5 Methodology](output/depletion/METHODOLOGY_Tables_3_4_5.md)

### Reference

- [File Dependencies Diagram](docs/FILE_DEPENDENCIES.md)
- [New Year Processing Checklist](docs/NEW_YEAR_CHECKLIST.md)
- [Excel Format Specifications](docs/EXCEL_FORMAT_SPECIFICATIONS.md)

---

*Last updated: February 2026*
