# P1 VERIFICATION PLAN: Exploration & Understanding
## Buckman Wellfield Red Team Testing Framework

**Date:** 2026-02-16
**Prompt:** P1 of 8 (Exploration phase - NO IMPLEMENTATION)
**Status:** ✅ EXPLORATION COMPLETE - Awaiting approval to proceed to P2

---

## Executive Summary

Completed comprehensive exploration of Buckman wellfield pipeline per TESTING_FRAMEWORK.md requirements. This plan documents all findings and answers to clarifying questions. **NO CODE WILL BE WRITTEN** - this is exploration only.

**Next Step:** Upon approval, proceed to P2 (Layer 5: 2024 Regression Harness)

---

## User Clarifications Received

### Q1: 2024 Validation Data Source
**Answer:** File `validation/Table_1_data_afy_2024.xlsx` created by manual workflow (labor intensive). This is the independent ground truth for regression testing.

**Implication:** Layer 5 will use this as the "expected output" baseline. Pipeline must reproduce these values within tolerance.

### Q2: Historical Data Scope
**Answer:**
- Extract 2022 and 2023 data from PDFs in `docs/reports_prior_year/`
- No prior XLSX exists for those years - will need to create from PDFs
- Use 2022, 2023, 2024 to establish "reasonable" baseline metrics
- 2024 is the double-check year we've already validated

**Implication:** Layer 2 (temporal consistency) will need PDF extraction utility to build historical baselines.

### Q3: Implementation Priority
**Answer:** Follow sequential prompts P1→P2→P3→P4→P5→P6→P7→P8 from `dev/prompts/claude_testing_framework_prompts.md`

**Sequence:**
- P1: Exploration (current - COMPLETE)
- P2: Layer 5 - 2024 Regression Harness
- P3: Layer 1 - Conservation/Mass Balance
- P4: Layer 6 - Provenance Logging
- P5: Layer 2 - Temporal Consistency
- P6: Layer 3 - Cross-Comparison
- P7: Layer 4 - Perturbation (future/optional)
- P8: Integration - Wire Everything

### Q4: External Data Availability
**Answer:**
- No USGS gage data needed
- No SCADA data needed
- Source data: `input/csv/Buckman_Well_Prod_2025.xlsx` (note: XLSX format going forward, not CSV)

**Implication:** Layer 3 cross-comparison will skip USGS/SCADA stubs. Focus on 2024 retroactive validation only.

### Q5: Test Integration Approach
**Answer:** Option C - Enhance existing pytest smoke tests (integrate validation into existing framework)

**Implication:** Keep existing `tests/test_*.py` files, add new validation checks as additional test functions and/or new test modules.

---

## Exploration Findings

### Finding 1: Complete Directory Structure

**Project Size:** 354 MB total
- MODFLOW output: 218 MB (flux files dominate at 62 MB per year)
- Ingested data: 220 KB (Tables 1 & 2)
- Depletion tables: 116 KB (Tables 3-5)

**Directory Tree:**
```
/home/bradwolaver/projects/rg/santafe/buckman/
├── input/
│   ├── csv/
│   │   ├── Buckman_Well_Prod_2025.csv (18 KB) ← Will be .xlsx format
│   │   └── 2024/Buckman_Well_Prod_2024.csv
│   └── modflow/2023/ (baseline templates + executables)
│       ├── thruCY2165.wel (3.2 MB template)
│       ├── modflow96.exe (941 KB)
│       ├── sfmodflx_2245.exe (452 KB)
│       ├── verify_modflow_run.py
│       └── verify_depletion.py
│
├── output/
│   ├── ingested_data/ (220 KB)
│   │   ├── 2024_Table_1_updated.xlsx + .csv
│   │   ├── 2024_Table_2_output.xlsx + .csv
│   │   ├── 2024_01_JAN.csv through 2024_12_DEC.csv
│   │   ├── 2025_Table_1_updated.xlsx + .csv (MODIFIED)
│   │   ├── 2025_Table_2_output.xlsx + .csv (MODIFIED)
│   │   └── 2025_01_JAN.csv through 2025_12_DEC.csv
│   │
│   ├── modflow/ (218 MB)
│   │   ├── 2024/
│   │   │   ├── modflow/ (older structure)
│   │   │   │   ├── CY2024.lst (9.7 MB)
│   │   │   │   ├── CY2024_ghb.flx (31 MB)
│   │   │   │   ├── CY2024_riv.flx (31 MB)
│   │   │   │   └── thruCY2165_2024.wel (3.2 MB)
│   │   │   └── depletions/
│   │   │       ├── CY2024_ghb.flx (31 MB)
│   │   │       ├── CY2024_riv.flx (31 MB)
│   │   │       └── sfmodflx_2245.exe
│   │   └── 2025/ (cleaner flat structure)
│   │       ├── CY2025.lst (9.7 MB)
│   │       ├── CY2025_ghb.flx (31 MB)
│   │       ├── CY2025_riv.flx (31 MB)
│   │       ├── thruCY2165_2025.wel (3.2 MB)
│   │       ├── verify_modflow_run.py
│   │       ├── verify_depletion.py
│   │       └── VERIFICATION_RESULTS.md
│   │
│   └── depletion/ (116 KB)
│       ├── TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx + 2025.xlsx
│       ├── TABLE_4_Rio_Grande_Otowi_2024.xlsx + 2025.xlsx
│       └── TABLE_5_La_Cienega_Springs_2024.xlsx + 2025.xlsx
│
├── validation/ (2024 reference data)
│   ├── Table_1_data_afy_2024.xlsx ← GROUND TRUTH
│   ├── Table_2_2024.xlsx
│   ├── TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx
│   ├── TABLE 4 - Rio Grande, above below Otowi.xlsx
│   ├── Table 5 - La Cienega Spring.jpg (image)
│   └── modflow/2024/
│       ├── CY2024.nam
│       └── thruCY2165_2024.wel
│
├── tests/ (pytest suite)
│   ├── test_ingest_buckman_data.py (50+ smoke tests)
│   ├── test_update_modflow.py (30+ smoke tests)
│   ├── test_stream_depletions.py (40+ smoke tests)
│   └── test_generate_depletion_tables.py (32 smoke tests)
│
├── docs/
│   ├── BUCKMAN_WORKFLOW.md
│   ├── TESTING_FRAMEWORK.md.md ← Framework spec
│   └── reports_prior_year/ ← 2022, 2023, 2024 PDFs
│       ├── Memo_bkmanISCWRD_2022_ANALYSIS.pdf
│       ├── MSC_2024_001_Buckman Well Field_2023_ANALYSIS.pdf
│       └── MSC_2025_002_Buckman Depletions 2024_ANALYSIS.pdf
│
└── Pipeline Scripts (6 main files)
    ├── step1_ingest_buckman_data.py (77 KB, 1750 lines)
    ├── step2_update_modflow.py (52 KB, 1400 lines)
    ├── step3_run_modflow.sh (5.1 KB, bash)
    ├── step4_generate_depletion_tables.py (38 KB, 850 lines)
    ├── step5_verify_workflow.py (13 KB)
    └── stream_depletions.py (82 KB, 2100 lines - core library)
```

**Data Availability Matrix:**

| Data Type | 2022 | 2023 | 2024 | 2025 |
|-----------|------|------|------|------|
| Raw pumping CSV | PDF | PDF | ✓ | ✓ |
| Table 1 (Annual AF) | PDF | PDF | ✓ | ✓ |
| Table 2 (Monthly MGD) | PDF | PDF | ✓ | ✓ |
| MODFLOW run (.lst) | - | - | ✓ | ✓ |
| Flux files (.flx) | - | - | ✓ | ✓ |
| Tables 3-5 (Depletion) | PDF | PDF | ✓ | ✓ |
| Validation reference | - | - | ✓ | - |

---

### Finding 2: Pipeline Data Flow

**Complete Workflow:**

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: step1_ingest_buckman_data.py                           │
├─────────────────────────────────────────────────────────────────┤
│ Input:  input/csv/Buckman_Well_Prod_{year}.csv                 │
│         - 366 daily rows (365 + 1 header)                      │
│         - 4 summary rows at bottom                             │
│         - MGD units (million gallons per day)                  │
│ Process: CSV → pandas → aggregate monthly → convert MG to AF   │
│         - validate_daily_data() flags NaN/negative             │
│         - verify_daily_sums() 3-tier BWP validation            │
│         - convert MG to AF using 3.06889 factor                │
│ Output: output/ingested_data/                                  │
│         - {year}_Table_1_updated.xlsx + .csv (annual by well)  │
│         - {year}_Table_2_output.xlsx + .csv (monthly by well)  │
│         - {year}_01_JAN.csv through {year}_12_DEC.csv          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: step2_update_modflow.py                                │
├─────────────────────────────────────────────────────────────────┤
│ Input:  output/ingested_data/{year}_Table_2_output.csv         │
│         - 13 wells × 12 months grid                            │
│         - AF units (acre-feet)                                 │
│ Process: Parse AF → convert to ft³/s (MODFLOW units)           │
│         Formula: -(AF/2) × 43560 / (days × 86400)              │
│         - Negative sign: MODFLOW convention (extraction)       │
│         - Divide by 2: split between Layer 1 & Layer 2         │
│         - Generate 324 lines per year (12 months × 27 lines)   │
│ Output: output/modflow/{year}/                                 │
│         - thruCY2165_{year}.wel (updated well file)            │
│         - CY{year}.nam (MODFLOW name file)                     │
│         - Copies 10 baseline files from input/modflow/2023     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: step3_run_modflow.sh (BASH)                            │
├─────────────────────────────────────────────────────────────────┤
│ Process: Subprocess: wine modflow96.exe CY{year}.nam           │
│         - Runs MODFLOW96 via Wine (Windows executable on WSL)  │
│         - Captures exit code via ${PIPESTATUS[0]}              │
│         - Logs output to {year}_modflow_run.log                │
│         - Runtime: 20-45 minutes typically                     │
│         - Auto-runs verify_modflow_run.py after completion     │
│ Output: output/modflow/{year}/                                 │
│         - CY{year}.lst (9.7 MB listing file)                   │
│         - CY{year}_ghb.flx (31 MB GHB flux - binary)           │
│         - CY{year}_riv.flx (31 MB river flux - binary)         │
│         - VERIFICATION_RESULTS.md (verification report)        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: step4_generate_depletion_tables.py                     │
├─────────────────────────────────────────────────────────────────┤
│ Input:  output/modflow/{year}/CY{year}_ghb.flx + _riv.flx      │
│ Process: Copy flux files to depletions directory               │
│         Subprocess: wine sfmodflx_2245.exe                     │
│         - Input via stdin: riv_file, ghb_file, output_prefix   │
│         - Timeout: 300 seconds                                 │
│         - Generates CY{year}_dep text file (1.5 MB)            │
│         Parse post-processor output (regex-based):             │
│         - Extract cell depletions (LAY ROW COL + 12 cfs)       │
│         - Extract stream summaries (R POJOAQUE, etc.)          │
│         Generate Excel tables using stream_depletions.py:      │
│         - Table 3: Rio Pojoaque + Tesuque + Core 2003 residual │
│         - Table 4: Rio Grande above/below Otowi                │
│         - Table 5: La Cienega Springs cumulative               │
│ Output: output/depletion/                                      │
│         - TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx             │
│         - TABLE_4_Rio_Grande_Otowi_{year}.xlsx                 │
│         - TABLE_5_La_Cienega_Springs_{year}.xlsx               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: step5_verify_workflow.py                               │
├─────────────────────────────────────────────────────────────────┤
│ Process: Check all output files exist                          │
│         Run pytest suites:                                     │
│         - pytest tests/test_ingest_buckman_data.py             │
│         - pytest tests/test_update_modflow.py                  │
│         - pytest tests/test_generate_depletion_tables.py       │
│         Run custom verification:                               │
│         - verify_modflow_run.py (mass balance, stress periods) │
│ Output: Console report: PASS/FAIL summary                      │
│         Exit code: 0 = all checks passed, 1 = any failed       │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Hand-off Points (data transforms):**

1. **CSV → pandas DataFrame** (step1)
   - Daily MGD → monthly MG → AF conversion
   - Validation: 3-tier BWP formula check

2. **pandas DataFrame → MODFLOW WEL file** (step2)
   - AF → ft³/s conversion
   - Text formatting: 324 lines per year
   - Validation: byte-identical pre/post sections, ±0.0001 ft³/s tolerance

3. **MODFLOW WEL → Binary flux** (step3 - MODFLOW96 internal)
   - Text rates → binary flux arrays
   - Validation: PERCENT DISCREPANCY, stress period count

4. **Binary flux → Text depletion file** (step4 - sfmodflx_2245.exe)
   - Binary .flx → text CY{year}_dep (cell + stream summaries)
   - Validation: file existence, size > 0

5. **Text depletion → Excel tables** (step4 - stream_depletions.py)
   - Regex parsing → nested dict → pandas → Excel with formatting
   - Validation: cell counts, sample value checks

---

### Finding 3: Existing Validation Coverage

**Overall Assessment: 60% Layer 0 Coverage**

**Strong Areas (✅):**
- File existence checks (comprehensive with forensic errors)
- Exit code validation (PIPESTATUS in bash, return codes in Python)
- Type checking (isinstance, try/except)
- Unit conversion validation (negative checks, range checks)
- Forensic error messaging (5-element format: what/location/actual/expected/context)

**Weak Areas (⚠️):**
- NaN/Inf detection (missing in most output tables)
- Outlier detection (no checks for 10× jumps)
- Temporal coherence (no month-to-month validation)
- Cross-well correlation (no systemic issue detection)

**Missing Areas (❌):**
- Binary file content checks (truncation detection)
- Post-processor output plausibility (cfs range validation)
- Integration tests (Step N output vs Step N+1 expectations)
- Depletion ≤ pumping physics check

**Detailed Validation Inventory:**

#### Step 1: step1_ingest_buckman_data.py

**Functions:**
- `validate_daily_data()`: Flags NaN (BLANK) and negative values (physical impossibility)
- `verify_daily_sums()`: 3-tier BWP validation
  - Tier 1 (Noise): 0 < BWP < 0.0015 MGD → INFO
  - Tier 2 (Formula): all wells = 0 but BWP ≥ 0.0015 → ERROR
  - Tier 3 (Precision):
    - ≤0.001 MGD → OK
    - 0.001-0.005 MGD → INFO
    - >0.005 MGD → ERROR
- Annual sum verification: ±0.01 MG tolerance per well

**Gaps:**
- ❌ No monthly outlier detection
- ❌ No year-over-year comparison
- ❌ No seasonal pattern validation
- ❌ No cross-well consistency check

#### Step 2: step2_update_modflow.py

**Functions:**
- `parse_wel_file()`: Validates 324-line structure per year
  - Header line = "26" for each month
  - First entry contains "BUCKMAN 1"
  - Last entry contains "BUCKMAN 13"
- `validate_wel_file()`: Compares to validation file (±0.0001 ft³/s)
- `validate_nam_file()`: Checks NAM file format
- `verify_nam_file_references()`: Cross-checks all referenced files exist
- `convert_af_to_ft3s()`: Negative check, days range check

**Gaps:**
- ❌ No rate magnitude sanity check (>1.0 ft³/s physically unrealistic)
- ❌ No well-to-grid-cell consistency
- ❌ No temporal coherence (rate jumps month-to-month)
- ❌ Graceful validation skip if validation file missing (risky)

#### Step 3: step3_run_modflow.sh

**Checks:**
- `set -euo pipefail` (exit on error, undefined vars, pipe failures)
- Year argument validation (numeric check)
- Directory existence (MODFLOW_DIR)
- Wine installation check
- NAM file existence
- Exit code capture: `${PIPESTATUS[0]}`
- Auto-runs verify_modflow_run.py

**Gaps:**
- ❌ No log file content validation
- ❌ No mass balance parsing (done in verify_modflow_run.py, not bash)
- ❌ No flux file size validation
- ❌ No stress period count check (in bash)

#### Step 4: step4_generate_depletion_tables.py

**Functions:**
- `check_prerequisites()`: Validates all inputs before post-processor
  - MODFLOW output directory exists
  - RIV/GHB flux files exist
  - Depletions directory exists
  - sfmodflx_2245.exe exists
  - Prints directory structure and flux file sizes
- `check_wine_installed()`: Wine availability check
- `copy_flux_files()`: Post-copy verification
- `run_post_processor()`: Post-run file existence check
- `parse_post_processor_output()`: Regex-based parsing with validation
  - Year header detection
  - 12 monthly values per cell/stream
- `extract_stream_depletions()`: KeyError checks for missing streams

**Gaps:**
- ❌ No Wine version check (just checks executable exists)
- ❌ No post-processor output size validation (truncation)
- ❌ No cfs plausibility check (all values accepted)
- ❌ No year continuity check (missing years silently skipped)
- ❌ No monthly completeness (< 12 months ignored)
- ❌ No rate unit validation (expected cfs range)

#### Step 5: step5_verify_workflow.py

**Checks:**
- File existence for all outputs (Tables 1-5, WEL, NAM, flux, listing)
- Runs pytest suites
- Runs verify_modflow_run.py

**Gaps:**
- ❌ No cross-file consistency checks
- ❌ No value plausibility checks
- ❌ File existence only, not content validation

#### Library: stream_depletions.py

**Validation:**
- `cfs_to_acre_feet()`: ValueError on negative cfs or days < 1
- `cfs_to_af()`: ValueError on negative cfs or invalid month index
- `cfs_monthly_to_af_annual()`: ValueError on len ≠ 12 or negative values
- `get_analytical_residual()`: ValueError on unknown stream name

**Test Suite Coverage:**
- `tests/test_ingest_buckman_data.py`: 50+ smoke tests
- `tests/test_update_modflow.py`: 30+ smoke tests
- `tests/test_stream_depletions.py`: 40+ smoke tests
- `tests/test_generate_depletion_tables.py`: 32 smoke tests

**Test Philosophy:** "Smoke tests verify code RUNS, not domain correctness. Domain expert must validate calculations independently."

---

### Finding 4: MODFLOW Listing File Format

**File:** `output/modflow/2025/CY2025.lst` (9.7 MB, 233,660 lines)

**Volumetric Budget Section (appears once per stress period):**

```
  VOLUMETRIC BUDGET FOR ENTIRE MODEL AT END OF TIME STEP  1 IN STRESS PERIOD  1
  -----------------------------------------------------------------------------

     CUMULATIVE VOLUMES      L**3       RATES FOR THIS TIME STEP      L**3/T
     ------------------                 ------------------------

           IN:                                      IN:
           ---                                      ---
             STORAGE =     8806152.0000               STORAGE =           3.2878
       CONSTANT HEAD =           0.0000         CONSTANT HEAD =           0.0000
               WELLS =           0.0000                 WELLS =           0.0000
       RIVER LEAKAGE =      312017.7190         RIVER LEAKAGE =           0.1165
     HEAD DEP BOUNDS =       2.1191E-05       HEAD DEP BOUNDS =       7.9118E-12

            TOTAL IN =     9118170.0000              TOTAL IN =           3.4043

          OUT:                                     OUT:
          ----                                     ----
             STORAGE =       6.8390E-10               STORAGE =       2.5534E-16
       CONSTANT HEAD =           0.0000         CONSTANT HEAD =           0.0000
               WELLS =     9118184.0000                 WELLS =           3.4043
       RIVER LEAKAGE =           0.0000         RIVER LEAKAGE =           0.0000
     HEAD DEP BOUNDS =           0.0000       HEAD DEP BOUNDS =           0.0000

           TOTAL OUT =     9118184.0000             TOTAL OUT =           3.4043

            IN - OUT =         -14.2812              IN - OUT =      -5.3570E-06

 PERCENT DISCREPANCY =           0.00     PERCENT DISCREPANCY =           0.00
```

**Key Parsing Targets for Layer 1:**
- Line: `PERCENT DISCREPANCY =` (appears twice per stress period)
- Budget components: STORAGE, CONSTANT HEAD, WELLS, RIVER LEAKAGE, HEAD DEP BOUNDS
- Values: Fixed-width columns, scientific notation (e.g., 2.1191E-05)
- Units: L³ (cumulative), L³/T (rates)

**Regex Pattern for PERCENT DISCREPANCY:**
```python
discrepancy_pattern = re.compile(r"PERCENT DISCREPANCY\s*=\s*([\d\.\-]+)")
```

**Well Budget Format:**
```
 26 WELLS

 LAYER   ROW   COL   STRESS RATE   WELL NO.
 ------------------------------------------
    1     13    11     0.0000          1
    2     13    11     0.0000          2
    ...
    2     20    16     0.0000         26
```

**Parsing Strategy:**
- Search for "PERCENT DISCREPANCY" in final budget summary
- Extract value, assert < 0.1%
- Search for "WELLS" in OUT section to get total pumping
- Sum WELLS from stress periods, compare to input Table 2 totals

---

### Finding 5: Post-Processor Output Format

**File:** `output/modflow/2024/depletions/CY2024` (1.5 MB text, 10,325 lines)

**Header:**
```
 number of timesteps in file =  2136  +1
1 PUMPAGE EFFECT ON RIV. BUDGET                    CFS (+ INDICATES REDUCED STREAM FLOW)
+_________________________________________________________________________________________________________________________________
```

**Year Section:**
```
YEAR: 2024        jan         feb         mar         apr         may         jun         jul         aug         sep         oct         nov         dec
  LAY ROW COL
+_________________________________________________________________________________________________________________________________

    1  13  11    1.239402    1.248156    1.257633    1.266503    1.275544    1.284116    1.292818    1.301097    1.309072    1.316841    1.324378    1.331750
    1  14  10    0.296715    0.300785    0.305308    0.309602    0.313980    0.317999    0.322090    0.325851    0.329346    0.332635    0.335688    0.338568
    [... more cell rows ...]

0  R POJOAQUE    0.127645    0.129515    0.131691    0.133723    0.135894    0.137912    0.139990    0.141877    0.143656    0.145344    0.146918    0.148443
0   R TESUQUE    0.008883    0.009080    0.009323    0.009556    0.009797    0.010027    0.010268    0.010497    0.010718    0.010927    0.011122    0.011319
0  RIO GRANDE    1.504848    1.521656    1.541123    1.559572    1.579074    1.597177    1.616051    1.633896    1.650931    1.667448    1.682651    1.697531
0  RIV  TOTAL    1.641376    1.660251    1.682137    1.702851    1.724765    1.745116    1.766309    1.786269    1.805305    1.823719    1.840691    1.857293
0  LC SPRINGS    0.000347    0.000352    0.000358    0.000363    0.000369    0.000374    0.000380    0.000385    0.000391    0.000396    0.000402    0.000407
```

**Regex Patterns (from step4_generate_depletion_tables.py):**
```python
# Year header (line 541)
year_pattern = re.compile(r"YEAR:\s+(\d{4})")

# Cell row (line 545)
cell_pattern = re.compile(r"^\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.\s-]+)$")

# Stream summary row (line 549)
stream_pattern = re.compile(r"^0\s+([A-Z][A-Z\s]+?)\s{2,}([\d\.\s-]+)$")
```

**Stream Names (exact spelling):**
- "R POJOAQUE" (with leading space)
- "R TESUQUE" (with leading space - note spacing)
- "RIO GRANDE" (with two spaces between RIO and GRANDE)
- "RIV  TOTAL" (with two spaces between RIV and TOTAL)
- "LC SPRINGS" (with leading space)

**Month Names:**
```python
MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun",
               "jul", "aug", "sep", "oct", "nov", "dec"]
```

**Units:** CFS (cubic feet per second)

**Data Structure:**
```python
ParsedData = dict[int, dict[str, dict[str, float]]]
# {year: {identifier: {month: cfs_value}}}
# Example: {2024: {"R POJOAQUE": {"jan": 0.127645, "feb": 0.129515, ...}}}
```

---

## Recommendations for P2-P8 Implementation

Based on exploration findings, here are key implementation notes for subsequent prompts:

### P2 (Layer 5: 2024 Regression Harness)

**Input Files to Freeze:**
- `input/csv/Buckman_Well_Prod_2024.csv` (18 KB)
- Template not needed (step2 chains from prior year)

**Expected Outputs (validation/ directory):**
- `Table_1_data_afy_2024.xlsx` ← Ground truth
- `Table_2_2024.xlsx`
- `TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx`
- `TABLE 4 - Rio Grande, above below Otowi.xlsx`
- `Table 5 - La Cienega Spring.jpg` (image - may need special handling)

**Tolerances to Define:**
- Table 1 (annual AF): Suggest ±0.01 AF (similar to step1 annual sum tolerance)
- Table 2 (monthly MGD): Suggest ±0.001 MGD (similar to step1 BWP tier 1)
- Tables 3-5 (depletion AF): Suggest ±0.01 AF or 1% relative (whichever is larger)

**SHA-256 Hash Storage:** Use `hashes.json` format:
```json
{
  "Buckman_Well_Prod_2024.csv": "abc123...",
  "last_updated": "2024-02-16T10:00:00Z"
}
```

### P3 (Layer 1: Conservation/Mass Balance)

**MODFLOW Listing Parser:**
- Use regex: `r"PERCENT DISCREPANCY\s*=\s*([\d\.\-]+)"`
- Assert value < 0.1%
- Parse final budget summary (not per-stress-period)

**Pumping Sum Check:**
- Input sum: Load Table 2, sum all wells all months, convert AFsum to ft³/s-cumulative
- MODFLOW sum: Parse "WELLS" from OUT section cumulative volumes
- Tolerance: ±0.1% or ±1 ft³ (whichever is larger)

**Depletion ≤ Pumping:**
- Parse post-processor output for stream summaries
- For each year in file:
  - Cumulative depletion = sum(stream cfs × days_in_month) over all months
  - Cumulative pumping = sum(Table 2 AF) converted to ft³
  - Assert: depletion_ft3 ≤ pumping_ft3 × safety_factor (suggest 1.1 for numerical tolerance)

**Table Sum Integrity:**
- Table 1: Sum of wells = "Total" row
- Table 2: Sum of months = annual total, sum of wells = "Total" column
- Table 3: R POJOAQUE + R TESUQUE should match combined total
- Table 4: Above Otowi + Below Otowi should match RIO GRANDE total
- Table 5: Cumulative values should be monotonically increasing

### P4 (Layer 6: Provenance Logging)

**Git Commit Hash:**
```python
subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
```

**Python Version:**
```python
import sys
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
```

**File Modification Dates:**
```python
from pathlib import Path
import datetime
mod_time = datetime.datetime.fromtimestamp(Path(file).stat().st_mtime)
```

**Manifest Format:** JSON (human-readable with indentation):
```json
{
  "run_metadata": {
    "timestamp_start": "2025-02-16T10:00:00Z",
    "timestamp_end": "2025-02-16T10:45:32Z",
    "runtime_seconds": 2732,
    "machine": "hostname",
    "os": "Linux 5.15.167.4-WSL2"
  },
  "inputs": {
    "Buckman_Well_Prod_2025.csv": {
      "path": "input/csv/Buckman_Well_Prod_2025.csv",
      "sha256": "abc123...",
      "size_bytes": 18432,
      "rows": 370,
      "date_range": "2025-01-01 to 2025-12-31"
    }
  },
  "pipeline": {
    "git_commit": "aad28425f...",
    "python_version": "3.10.12",
    "scripts": {
      "step1_ingest_buckman_data.py": {"modified": "2025-02-15T12:34:56Z"},
      "modflow96.exe": {"modified": "2023-01-01T00:00:00Z"}
    }
  },
  "tests": {
    "layer0_smoke": {"status": "PASSED", "tests_run": 150, "failures": 0},
    "layer1_conservation": {
      "volumetric_budget": {"status": "PASSED", "discrepancy_pct": 0.00, "threshold_pct": 0.1},
      "pumping_sum": {"status": "PASSED", "input_af": 1234.56, "modflow_af": 1234.57, "diff_af": 0.01}
    }
  },
  "flags": []
}
```

### P5 (Layer 2: Temporal Consistency)

**Historical Data Needed:**
- Extract from PDFs: `docs/reports_prior_year/Memo_bkmanISCWRD_2022_ANALYSIS.pdf`
- Extract from PDFs: `docs/reports_prior_year/MSC_2024_001_Buckman Well Field_2023_ANALYSIS.pdf`
- Tables needed: Table 1 (annual pumping), Table 2 (monthly pumping)
- Format: Create `historical_baseline.json`:
```json
{
  "2022": {
    "annual_pumping_af": {"BUCKMAN 1": 601.28, "BUCKMAN 2": 123.45, ...},
    "monthly_pattern_normalized": [0.05, 0.06, 0.08, ..., 0.12]
  },
  "2023": {...},
  "2024": {...}
}
```

**PDF Extraction Utility:**
- Create `extract_historical_data.py` to parse PDFs
- Use PyPDF2 or pdfplumber
- Extract Table 1 and Table 2 data
- Output to JSON format

**Thresholds (configurable in `temporal_config.yaml`):**
```yaml
year_over_year_change_pct: 40  # Flag if well pumping changes > 40%
depletion_ratio_change_pct: 25  # Flag if depletion/pumping shifts > 25%
seasonal_correlation_threshold: 0.85  # Flag if r < 0.85
prediction_interval_confidence: 0.95  # 95% PI
```

### P6 (Layer 3: Cross-Comparison)

**2024 Retroactive Validation:**
- Already covered by Layer 5 regression harness
- Cross-reference: Log Layer 5 results in Layer 3 manifest section

**External Data Stubs:**
- Skip USGS gage stub (per user answer Q4)
- Skip SCADA stub (per user answer Q4)
- Focus solely on 2024 retroactive validation

### P7 (Layer 4: Perturbation) - FUTURE/OPTIONAL

**Computational Cost:**
- Each scenario requires full MODFLOW run (20-45 minutes)
- 5 scenarios × 13 wells = 65 runs minimum
- Total time: ~20-50 hours
- Design for batch execution (overnight runs)

**Perturbation Generator:**
```python
def generate_perturbed_input(base_csv, well_id, perturbation_type, magnitude):
    # Load base CSV
    # Apply perturbation to specified well
    # Write to temp CSV
    # Return temp file path
```

### P8 (Integration)

**Master Test Runner (`run_all_tests.py`):**
```python
def main():
    results = {}
    results['layer0'] = run_smoke_tests()
    results['layer1'] = run_conservation_checks()
    results['layer2'] = run_temporal_checks()
    results['layer3'] = run_cross_comparison()
    generate_manifest(results)
    print_summary(results)
    return 0 if all_hard_stops_passed(results) else 1
```

**Integration with Main Pipeline:**
- Modify `step5_verify_workflow.py` to call `run_all_tests.py`
- Or create new `step6_comprehensive_tests.py`

**Regression Harness Separation:**
- Keep `run_regression_2024.py` standalone
- Document: "Run before deploying pipeline changes"
- Add to CI/CD if using version control automation

---

## File Paths Reference

**Critical Files for P2-P8:**

```
# Frozen 2024 inputs (to be created in P2)
validation/2024/inputs/Buckman_Well_Prod_2024.csv
validation/2024/inputs/hashes.json

# Expected outputs (already exist)
validation/Table_1_data_afy_2024.xlsx
validation/Table_2_2024.xlsx
validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx
validation/TABLE 4 - Rio Grande, above below Otowi.xlsx
validation/Table 5 - La Cienega Spring.jpg

# Tolerances (to be created in P2)
validation/2024/tolerances.yaml

# MODFLOW listing (for Layer 1 parsing)
output/modflow/2025/CY2025.lst

# Post-processor output (for Layer 1 parsing)
output/modflow/2024/depletions/CY2024

# Historical data sources (for Layer 2)
docs/reports_prior_year/Memo_bkmanISCWRD_2022_ANALYSIS.pdf
docs/reports_prior_year/MSC_2024_001_Buckman Well Field_2023_ANALYSIS.pdf
docs/reports_prior_year/MSC_2025_002_Buckman Depletions 2024_ANALYSIS.pdf

# Test modules (to be enhanced)
tests/test_ingest_buckman_data.py
tests/test_update_modflow.py
tests/test_stream_depletions.py
tests/test_generate_depletion_tables.py

# New test modules (to be created)
tests/test_conservation.py (P3)
tests/test_temporal.py (P5)
tests/test_cross_comparison.py (P6)
tests/test_perturbation.py (P7)

# Utility modules (to be created)
pipeline_manifest.py (P4)
extract_historical_data.py (P5)
run_regression_2024.py (P2)
run_all_tests.py (P8)

# Configuration files (to be created)
validation/2024/tolerances.yaml (P2)
config/temporal_config.yaml (P5)

# Documentation (to be created)
tests/README.md (P8)
```

---

## Next Steps

**Upon Approval of P1 Plan:**
1. User reviews this exploration summary
2. User confirms understanding is correct
3. User approves proceeding to P2

**P2 Will Implement:**
- Create `validation/2024/inputs/` directory structure
- Copy and hash 2024 input files
- Copy 2024 validation outputs to `expected_outputs/`
- Create `tolerances.yaml` with initial values
- Build `run_regression_2024.py` script
- Test regression harness against actual 2024 data
- Document results and tolerances that may need adjustment

**Estimated Time:**
- P2: 2-3 hours (directory setup + regression script)
- P3: 3-4 hours (MODFLOW parser + conservation checks)
- P4: 2-3 hours (manifest generator + SHA-256 hashing)
- P5: 4-5 hours (PDF extraction + temporal checks)
- P6: 1-2 hours (link Layer 5 to Layer 3)
- P7: 6-8 hours (perturbation framework - FUTURE)
- P8: 2-3 hours (integration + README)

**Total Framework:** ~20-30 hours (excluding P7)

---

## Summary

✅ **P1 Exploration Complete**

- 354 MB project fully mapped
- 6-script pipeline data flow documented
- Existing validation: 60% Layer 0 coverage identified
- MODFLOW/post-processor formats extracted for parsing
- 2024 validation baseline confirmed
- Historical data extraction plan defined (2022-2023 PDFs)
- Ready to proceed to P2 (Layer 5 regression harness)

**User Approval Needed:**
1. Confirm exploration findings are accurate
2. Approve proceeding to P2 implementation
3. Review any corrections or clarifications needed

---

**END OF P1 PLAN**
