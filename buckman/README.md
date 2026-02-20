# Buckman Wellfield Depletion Pipeline

Annual stream depletion calculations for Santa Fe water rights compliance.

---

## Quick Start

### Pipeline Flow

```
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ STEP 1        │──▶│ STEP 2        │──▶│ STEP 3        │──▶│ STEP 4a       │──▶│ STEP 4b       │
│ Ingest Data   │   │ MODFLOW Files │   │ Run MODFLOW96 │   │ Post-Process  │   │ Depletion Tbl │
├───────────────┤   ├───────────────┤   ├───────────────┤   ├───────────────┤   ├───────────────┤
│ IN:  CSV      │   │ IN:  .wel     │   │ IN:  .nam     │   │ IN:  .flx     │   │ IN:  CY{YYYY} │
│ OUT: T1, T2   │   │ OUT: .wel+nam │   │ OUT: .flx     │   │ OUT: CY{YYYY} │   │ OUT: T3,T4,T5 │
├───────────────┤   ├───────────────┤   ├───────────────┤   ├───────────────┤   ├───────────────┤
│    python3    │   │    python3    │   │ wine modflow96│   │wine sfmodflx  │   │    python3    │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

**Note:** Steps 4a and 4b are both run by `step4_generate_depletion_tables.py`:
- **4a:** Runs `sfmodflx_2245.exe` (FORTRAN post-processor) to extract depletions from binary `.flx` files
- **4b:** Parses post-processor output and generates Excel tables

### Commands

```bash
python3 step1_ingest_buckman_data.py --year 2024
python3 step2_update_modflow.py --year 2024
./step3_run_modflow.sh --year 2024
python3 step4_generate_depletion_tables.py --year 2024
```

### Verify

```bash
python3 step5_verify_workflow.py --year 2024    # Quick verification
python3 run_all_tests.py --year 2024            # Full test suite
```

### Inputs & Outputs

| Step | Input | Output | Executable |
|------|-------|--------|------------|
| 1 | `input/csv/Buckman_Well_Prod_YYYY.csv` | Tables 1 & 2 (XLSX) | python3 |
| 2 | Prior year `.wel` file | `.wel`, `.nam`, baseline files | python3 |
| 3 | `.nam` file | `.flx` flux files (~31 MB each) | wine modflow96.exe |
| 4a | `.flx` files | `CY{YYYY}` depletion file | wine sfmodflx_2245.exe |
| 4b | `CY{YYYY}` file | Tables 3, 4, 5 (XLSX) | python3 |

### Expected Outputs (2024)

| Table | File | Description |
|-------|------|-------------|
| 1 | `output/ingested_data/2024_Table_1_updated.xlsx` | Historical pumping by well (1988-2024) |
| 2 | `output/ingested_data/2024_Table_2_output.xlsx` | Monthly pumping detail |
| 3 | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx` | Rio Pojoaque & Rio Tesuque depletions |
| 4 | `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx` | Rio Grande above/below Otowi |
| 5 | `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx` | La Cienega Springs cumulative |

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
python3 step5_verify_workflow.py --year 2025       # Quick check
python3 verify_depletion.py --year 2025            # Cross-model depletion check
python3 run_all_tests.py --year 2025               # Full test suite (recommended)

# 4. Commit results
git add output/
git commit -m "Complete 2025 Buckman workflow"
```

**File Dependency Chain:** Each year chains from the previous year:
- WEL file: Extends from prior year
- Table 1: Extends from prior year
- Always process years sequentially (2024 → 2025 → 2026)

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

**Input:** Prior year's WEL file (critical chaining dependency)
- **2024 (baseline):** `input/modflow/2023/thruCY2165.wel` (no year suffix)
- **2025+:** `output/modflow/{year-1}/thruCY2165_{year-1}.wel`

**⚠️ Year Chaining:** WEL files are cumulative (1988-YYYY). Each year extends the prior year. You MUST process years sequentially—skipping a year breaks the chain.

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

### Step 4b: Verify Depletion Tables (Cross-Model)

```bash
python3 verify_depletion.py --year YYYY
```

**Input:** Post-processor output from current and prior year (`CY{YYYY}` and `CY{YYYY-1}`)

**Output:** `output/depletion/Table_3_verify_depletion_{YYYY-1}_{YYYY}.xlsx`

**What it does:**
- Parses both CY files and computes R POJOAQUE and R TESUQUE superposition AF for the full 1988-2030 series directly from each post-processor output
- Compares values side-by-side with diff columns
- Yellow-highlights any historical year where |diff| > 0.001 AF

**How to interpret:**
- **Years 1988 to YYYY-1** should show zero diff (same model, same pumping data)
- **Year YYYY and beyond** will differ (new pumping data incorporated)
- Any non-zero diff in historical years indicates a problem with the MODFLOW run or post-processor

**Table 3 chaining:** Step 4 automatically chains Table 3 from the prior year's output. Years before YYYY are copied exactly from `TABLE_3_Rio_Pojoaque_Tesuque_{YYYY-1}.xlsx`; only years YYYY-2030 are recomputed from fresh MODFLOW output.

### Core Libraries

**`stream_depletions.py`** - Core depletion calculation library (~2,700 lines)
- Parses `sfmodflx_2245.exe` post-processor output (`CY{YYYY}` file)
- Converts cfs → acre-feet with proper unit handling
- Applies Core (2003) analytical residuals for pre-1988 pumping
- Called by `step4_generate_depletion_tables.py`

### Supporting Modules (`src/`)

| Module | Purpose |
|--------|---------|
| `pipeline_manifest.py` | Generate SHA-256 manifest of all pipeline input/output files |
| `workflow_logger.py` | Generate regulatory compliance logs (MD + DOCX) |
| `generate_workflow_log.py` | CLI wrapper for standalone log generation |

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

## Understanding Stream Cell Assignments

**How does the pipeline know which MODFLOW cells correspond to each stream reach?**

The pipeline uses a **three-layer hardcoding system** to identify which model cells contribute to stream depletions:

1. **MODFLOW Input Files** (`input/modflow/2023/thruCY2165.riv`, `thruCY2165.ghb`)
   - Define physical cell locations (layer, row, column) with no stream labels
   - Example: La Cienega Springs = 6 GHB cells at rows 30-32, columns 12-15

2. **FORTRAN Post-Processor** (`sfmodflx_2245.exe`)
   - Hardcoded cell rectangles extract and aggregate fluxes
   - Example: La Cienega extraction range = rows 28-35, columns 10-20 (hardcoded in FORTRAN source)
   - Assigns stream labels: "LC SPRINGS", "R POJOAQUE", "R TESUQUE", "RIO GRANDE"

3. **Python Parser** (`stream_depletions.py`)
   - Matches exact stream label strings from FORTRAN output
   - Extracts monthly cfs values for each stream

**⚠️ Critical Assumption:** FORTRAN cell ranges MUST match actual cell locations in MODFLOW input files, or depletion values will be wrong.

**For full details:** See [`docs/MODFLOW_CELL_MAPPING.md`](docs/MODFLOW_CELL_MAPPING.md)
- Complete documentation of cell identification mechanism
- ASCII diagrams showing cell locations on model grid
- Instructions for updating if model geometry changes
- Validation procedures to detect mismatches

---

## Verification & Testing

Verification ensures that workflow outputs are correct and physically plausible. This is critical for year N+1 (i.e., year 2025 and later) when you have no prior results to compare against.

### Quick Verification (step5)

```bash
python3 step5_verify_workflow.py --year 2024
```

**Purpose:** Fast sanity check after running the workflow.

**What it checks:**
- All expected output files exist with reasonable sizes
- MODFLOW converged (no solver failures)
- Cross-table consistency (Table 1 annual total = Table 2 annual total)
- Physical bounds (pumping within historical range)

**Interpreting results:**
- `PASS`: All checks passed, outputs look valid
- `FAIL`: Something is wrong—read the error message for which check failed

**Advanced options:**
```bash
python3 step5_verify_workflow.py --year 2024 --step 3    # Run specific step only
python3 step5_verify_workflow.py --year 2024 --verbose   # Detailed output
```

**If it fails:**
| Error | Likely Cause | Fix |
|-------|--------------|-----|
| "File not found" | Step didn't run or failed | Re-run the failing step |
| "MODFLOW did not converge" | Model numerical issues | Check .lst file for details |
| "Table totals don't match" | Bug in ingestion | Check input CSV formatting |

---

### Full Test Suite (run_all_tests.py)

```bash
python3 run_all_tests.py --year 2024
```

**Purpose:** Comprehensive validation before committing results. **Use this for production.**

**8-Layer Framework:**

| Layer | Name | What It Catches | Failure Action |
|-------|------|-----------------|----------------|
| 0 | Smoke | Import errors, basic function failures, MODFLOW geometry validation | Fix code bugs |
| 1 | Conservation | Mass not conserved (pumping ≠ sum of parts) | Check unit conversions |
| 2 | Temporal | Unreasonable YoY changes (>65%) | Verify input data |
| 3 | Ballpark | Values outside physical bounds | Check model inputs |
| 4 | Cross-comparison | Tables inconsistent with each other | Debug table generation |
| 5 | Regression | Results differ from 2024 baseline | Intentional? Update baseline |
| 6 | Provenance | Output files not logged | Run manifest generator |

**Interpreting output:**
```
Layer 0 (Smoke Tests): PASS
Layer 1 (Conservation): PASS
Layer 2 (Temporal): PASS
Layer 3 (Ballpark): PASS
Layer 4 (Cross-comparison): PASS
Layer 5 (Regression): PASS
Layer 6 (Provenance): PASS
===============================
ALL LAYERS PASSED
```

**If any layer fails:** The test will report which layer and specific check failed. Address the root cause before proceeding.

---

### Unit Tests (pytest)

Unit tests are automated checks that verify each function in the code works correctly. Think of them like a checklist that the computer runs through to confirm nothing is broken. If all tests pass, the code is working as expected.

```bash
pytest tests/ -v                           # All unit tests
pytest tests/test_conservation.py -v       # Conservation/mass-balance only
pytest tests/test_stream_depletions.py -v  # Depletion calculations
```

| Command | What It Tests |
|---------|---------------|
| `pytest tests/ -v` | Runs all 240 tests across all modules. Use this for a complete code health check. |
| `pytest tests/test_conservation.py -v` | Verifies that water mass is conserved (pumping in = depletion out). Catches unit conversion errors. |
| `pytest tests/test_stream_depletions.py -v` | Tests the core depletion calculation functions (cfs→AF conversion, table generation, XLSX formatting). |

**Purpose:** Verify individual functions work correctly (useful after code changes).

**When to run:** After modifying any Python script.

---

### Regression Testing

```bash
python3 validation/2024/run_regression_2024.py
```

**Purpose:** Ensure code changes don't alter results.

**How it works:** Compares each cell in Tables 1-5 against `validation/2024/expected_outputs/`.

**Interpreting output:**
```
Table 1: PASS (0 differences)
Table 2: PASS (0 differences)
Table 3: PASS (0 differences)
Table 4: PASS (0 differences)
Table 5: PASS (0 differences)
```

**If regression fails:**
- **Intentional change?** Update expected outputs: `cp output/depletion/*.xlsx validation/2024/expected_outputs/`
- **Unintentional?** You broke something—revert and debug

---

### Physical Bounds (for QA/QC)

These bounds are derived from 1988-2023 historical data and hydrologic constraints.

| Metric | Expected Range | 2024 Actual | Why This Range |
|--------|----------------|-------------|----------------|
| Annual pumping | 866-1,373 AF | 1,372.92 AF | Historical min/max |
| Rio Pojoaque depletion | 15-65 AF | 60.80 AF | Based on model sensitivity |
| Rio Tesuque depletion | 40-180 AF | 33.58 AF* | Historical range |
| YoY pumping change | < 65% | +58.4% | Operational constraint |

*Note: 2024 Rio Tesuque below historical range due to pumping distribution changes.

**Out-of-bounds values:** Investigate input data quality or model parameter drift.

---

### Verifying Year N+1 Results

When processing a new year (e.g., 2025), you have no prior results to compare against. Use this approach:

**1. Check pumping data quality:**
- Does total pumping fall within historical range (866-1,373 AF)?
- Are there any months with zero pumping (unusual)?
- Do well-by-well values make sense?

**2. Check depletion reasonableness:**
- Depletions should be proportional to pumping (higher pumping → higher depletion)
- Compare to previous year: changes >50% warrant investigation

**3. Look for red flags:**
| Red Flag | Possible Cause |
|----------|----------------|
| Depletion > pumping | Unit conversion error |
| Negative depletion | Model instability |
| Identical values to prior year | Workflow used wrong input |
| Zero depletion | Post-processor failed |

**4. Cross-check with State Engineer expectations:**
- Annual reports typically show gradual trends
- Sudden jumps require explanation in the report narrative

**5. Cross-model depletion verification:**
```bash
python3 verify_depletion.py --year 2025
```
Confirms that `sfmodflx_2245` post-processor produces consistent results across model runs. Years 1988-2024 should show zero difference between CY2024 and CY2025. If historical years differ, the MODFLOW run or post-processor may have a problem.

---

### 2024 Regression Baseline

The 2024 outputs serve as the regression baseline for validating code changes:
- **Expected outputs:** `validation/2024/expected_outputs/Table_*_expected.xlsx`
- **Tolerances:** `validation/2024/tolerances.yaml`
- **Rule:** Any code change must reproduce 2024 outputs within tolerances

**Why 2024?** This was the first year fully processed with the automated pipeline. All outputs were manually verified against legacy Excel spreadsheets.

---

### Workflow Logging (Compliance Documentation)

After `run_all_tests.py` completes, a regulatory-grade log is automatically generated for City of Santa Fe compliance inquiries.

**Location:** `output/logs/`

**File naming:**
```
{YYYY}_workflow_log_{YYYYMMDD}_{HHMMSS}_{STATUS}.md
{YYYY}_workflow_log_{YYYYMMDD}_{HHMMSS}_{STATUS}.docx
```

**Status codes:**
| Code | Meaning |
|------|---------|
| `PASS` | All tests passed |
| `FLAGS` | Passed but soft flags require review |
| `FAIL` | One or more hard failures |

**Log contents (9 sections):**
1. **Metadata** - Timestamp, git commit, Python version, operator
2. **Executive Summary** - Total pumping, key depletions, verification status
3. **Input File Inventory** - Files with SHA-256 hashes
4. **Step-by-Step Execution** - Results from each pipeline step
5. **Output File Inventory** - Tables 1-5 with hashes
6. **Verification Summary** - Layer 0-6 test results
7. **Physical Interpretation** - Rio Grande Compact context, tributary significance
8. **Assumptions & Limitations** - MODFLOW96 constraints, Core 2003 residuals
9. **Approval Block** - Signature lines for review

**Standalone log generation (without running full test suite):**

```bash
python3 src/generate_workflow_log.py --year 2024
python3 src/generate_workflow_log.py --year 2024 --status FLAGS
python3 src/generate_workflow_log.py --year 2024 --status FAIL
```

Use when you need to regenerate a log after the fact, or document a run without re-running all tests.

**Note:** `step5_verify_workflow.py` does NOT generate logs (console-only). Compliance logs are generated by `run_all_tests.py` (automatically) or `src/generate_workflow_log.py` (standalone).

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
│   ├── logs/                           # Workflow logs (MD + DOCX)
│   └── modflow/YYYY/                   # MODFLOW files per year
│
├── tests/                              # Unit tests (pytest)
│   ├── test_conservation.py
│   ├── test_ingest_buckman_data.py
│   ├── test_update_modflow.py
│   └── ...
│
├── validation/
│   ├── ballpark_check.py               # Physical bounds validation
│   ├── temporal_consistency.py         # YoY anomaly detection
│   └── 2024/
│       ├── expected_outputs/           # Reference files
│       └── run_regression_2024.py      # Regression test
│
├── step1_ingest_buckman_data.py        # Tables 1 & 2
├── step2_update_modflow.py             # MODFLOW WEL/NAM
├── step3_run_modflow.sh                # Run MODFLOW96
├── step4_generate_depletion_tables.py  # Tables 3, 4, 5
├── verify_depletion.py                # Cross-model depletion check
├── step5_verify_workflow.py            # Comprehensive verify
├── run_all_tests.py                    # Full test suite orchestrator
└── stream_depletions.py                # Depletion library
```

---

## Known Limitations

1. **Step 4 default year:** If `--year` is omitted, step4 defaults to 2024. Always specify `--year` explicitly.

2. **Validation files:** Only 2024 has expected output files in `validation/2024/expected_outputs/`. Processing 2025+ runs in "degraded" mode (skips table comparisons, relies on physics checks).

3. **FORTRAN cell ranges:** La Cienega Springs extraction is hardcoded in `sfmodflx_2245.exe` (rows 28-35, cols 10-20). Changing model geometry requires recompiling FORTRAN. See `docs/MODFLOW_CELL_MAPPING.md`.

4. **Wine dependency:** MODFLOW96 and sfmodflx_2245.exe are Windows executables. Linux requires Wine.

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
