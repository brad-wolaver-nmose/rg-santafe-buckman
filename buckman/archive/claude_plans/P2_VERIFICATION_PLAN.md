# P2: 2024 Regression Harness Implementation Plan

## Overview

Layer 5 (Regression Testing Against 2024 Harness Year) - The single highest-value test for the Buckman wellfield pipeline. This plan creates a frozen, version-controlled archive of 2024 data and a standalone regression runner.

---

## Directory Structure

```
validation/
└── 2024/
    ├── inputs/                    # Frozen copies of 2024 raw input files
    │   ├── Buckman_Well_Prod_2024.csv    (18 KB - raw daily pumping)
    │   └── hashes.json                    (SHA-256 hashes)
    │
    ├── expected_outputs/          # 2024 validation spreadsheets
    │   ├── Table_1_expected.xlsx          (annual pumping by well)
    │   ├── Table_2_expected.xlsx          (monthly pumping by well)
    │   ├── Table_3_expected.xlsx          (Rio Pojoaque-Tesuque depletions)
    │   ├── Table_4_expected.xlsx          (Rio Grande depletions)
    │   └── Table_5_expected.xlsx          (La Cienega Springs - created from OCR)
    │
    └── tolerances.yaml            # Acceptance criteria per table/value type
```

---

## Implementation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p validation/2024/inputs
mkdir -p validation/2024/expected_outputs
```

### Step 2: Copy and Hash Input Files
This freezes 2024 data used for validation (a known-good copy) so that it is not accidentally edited and corrupted.  A hash is a cryptographic tracer that is used to determine if file is edited; if it were edited, it would have a different hash.

**Files to freeze:**


| Source Path | Destination | Size |
|-------------|-------------|------|
| `input/csv/2024/Buckman_Well_Prod_2024.csv` | `validation/2024/inputs/` | 18 KB |

**Generate `hashes.json`:**
```json
{
    "Buckman_Well_Prod_2024.csv": {
        "sha256": "<computed hash>",
        "size_bytes": 17937,
        "frozen_date": "2025-02-17"
    }
}
```

### Step 3: Copy Expected Output Files

**Map validation files to expected outputs:**

| Current Location | Expected Name | Purpose |
|------------------|---------------|---------|
| `validation/Table_1_data_afy_2024.xlsx` | `Table_1_expected.xlsx` | Annual pumping (1988-2024) |
| `validation/Table_2_2024.xlsx` | `Table_2_expected.xlsx` | Monthly pumping 2024 |
| `validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx` | `Table_3_expected.xlsx` | Pojoaque/Tesuque depletions |
| `validation/TABLE 4 - Rio Grande, above below Otowi.xlsx` | `Table_4_expected.xlsx` | Rio Grande depletions |

### Step 4: Create Table 5 from OCR

**Table 5 is a JPG image.** Create `Table_5_expected.xlsx` from OCR'd data:

**La Cienega Spring Cumulative Depletions (extracted from image):**

| Year | Total (AF) |
|------|------------|
| 2004 | 0.45 |
| 2005 | 0.66 |
| 2006 | 0.83 |
| 2007 | 0.99 |
| 2008 | 1.16 |
| 2009 | 1.32 |
| 2010 | 1.49 |
| 2011 | 1.65 |
| 2012 | 1.82 |
| 2013 | 1.97 |
| 2014 | 2.13 |
| 2015 | 2.29 |
| 2016 | 2.45 |
| 2017 | 2.60 |
| 2018 | 2.75 |
| 2019 | 2.90 |
| 2020 | 3.06 |
| 2021 | 3.21 |
| 2022 | 3.37 |
| 2023 | 3.54 |
| 2024 | 3.74 |
| 2025 | 3.92 |
| 2026 | 4.10 |
| 2027 | 4.27 |
| 2028 | 4.46 |
| 2029 | 4.62 |
| 2030 | 4.80 |

**Note:** For 2024 regression, only compare rows through 2024.

### Step 5: Create tolerances.yaml
Define how close is close enough: This file sets the acceptable margin of error when comparing your pipeline's output to the expected 2024 values  
Also says: if any cell contains NaN or unexpected empty values, fail the test immediately.

```yaml
tables:
  Table_1:
    description: "Annual pumping by well (acre-feet/year)"
    tolerance_type: hybrid
    absolute_tolerance: 0.01  # 0.01 AF
    relative_tolerance: 0.001  # 0.1%

  Table_2:
    description: "Monthly pumping by well (acre-feet/month)"
    tolerance_type: hybrid
    absolute_tolerance: 0.01
    relative_tolerance: 0.001

  Table_3:
    description: "Rio Pojoaque-Nambe & Rio Tesuque depletions"
    tolerance_type: hybrid
    absolute_tolerance: 0.1   # FLAG: May need adjustment
    relative_tolerance: 0.01

  Table_4:
    description: "Rio Grande above/below Otowi depletions"
    tolerance_type: hybrid
    absolute_tolerance: 0.1   # FLAG: May need adjustment
    relative_tolerance: 0.01

  Table_5:
    description: "La Cienega Springs cumulative depletions"
    tolerance_type: hybrid
    absolute_tolerance: 0.01
    relative_tolerance: 0.005
    max_year: 2024

global:
  nan_handling: "fail"
  empty_cell_handling: "match"
```

### Step 6: Create run_regression_2024.py
Build the automated test runner, a Python script that does everything automatically.  
Bottom line: One command (python run_regression_2024.py) runs the entire pipeline and tells you if it still produces the correct 2024 results.  
Why This Matters:  This is compliance-critical water rights data. If a code change accidentally shifts a depletion calculation by 0.5 acre-feet, you need to catch that immediately; not discover it after reporting is submitted.

**Location:** `validation/2024/run_regression_2024.py`

**Key functions:**
1. `verify_input_hashes()` - Check SHA-256 hashes match
2. `run_pipeline_2024()` - Execute steps 1-4 + sfmodflx_2245.exe
3. `compare_tables()` - Cell-by-cell comparison with tolerances
4. `generate_report()` - PASS/FAIL report with failure details
5. `main()` - Orchestrate and return exit code

---

## Files to Create

| File | Action |
|------|--------|
| `validation/2024/inputs/Buckman_Well_Prod_2024.csv` | Copy |
| `validation/2024/inputs/hashes.json` | Create |
| `validation/2024/expected_outputs/Table_1_expected.xlsx` | Copy & rename |
| `validation/2024/expected_outputs/Table_2_expected.xlsx` | Copy & rename |
| `validation/2024/expected_outputs/Table_3_expected.xlsx` | Copy & rename |
| `validation/2024/expected_outputs/Table_4_expected.xlsx` | Copy & rename |
| `validation/2024/expected_outputs/Table_5_expected.xlsx` | Create from OCR |
| `validation/2024/tolerances.yaml` | Create |
| `validation/2024/run_regression_2024.py` | Create (~15 KB) |

---

## Pipeline Execution Order

```
1. step1_ingest_buckman_data.py --year 2024
2. step2_update_modflow.py --year 2024
3. step3_run_modflow.sh --year 2024 (runs modflow96.exe)
4. sfmodflx_2245.exe (FORTRAN stream depletion post-processor)
5. step4_generate_depletion_tables.py --year 2024
```

---

## Flagged Items

- Tables 3/4 tolerances may need adjustment after first run
- Table 5: only compare through 2024 (future years are projections)
- MODFLOW - add timeout handling
- sfmodflx_2245.exe runs between step3 and step4

---

## Success Criteria

PASS if:
1. All input hashes match
2. Pipeline completes without errors
3. All 5 tables match within tolerances
4. No NaN/Inf values
