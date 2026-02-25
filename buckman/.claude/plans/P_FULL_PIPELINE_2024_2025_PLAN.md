# FULL PIPELINE RUN PLAN: 2024 V&V + 2025 Fresh Run
**Created:** 2026-02-25
**Scope:** Full pipeline steps 1-4 for both years; all V&V layers; generate Tables 1-5 for 2025

---

## Overview

Run the complete Buckman depletion pipeline for two years:

1. **2024** — Full pipeline re-run (steps 1-4) then all V&V layers including 2024 regression harness
2. **2025** — Full pipeline re-run from scratch (steps 1-4, including MODFLOW96 re-run via Wine) then all V&V layers

Final deliverable: Fresh Tables 1, 2, 3, 4, 5 for 2025.

---

## Phase 0: Pre-Run Checks

**0.1** Verify git status is clean (or note dirty state)
**0.2** Check input CSV files exist:
- `input/csv/2024/Buckman_Well_Prod_2024.csv`
- `input/csv/2025/Buckman_Well_Prod_2025.csv`

**0.3** Check baseline MODFLOW files exist in `input/modflow/2023/`:
- `modflow96.exe`, `sfmodflx_2245.exe`, `thruCY2165.wel`, `CY2023.nam`, etc.

**0.4** Note prior 2025 FLAGS issues — investigate as we run:
- Last FLAGS run (2026-02-19 14:05): 224 tests passed, 0 failed, but logged as FLAGS
- May 2025 check file (`2025_MAY_CHECK.xlsx`) exists — implies May data anomaly
- FAIL status from earlier runs appears to be unrelated to test counts (likely workflow-level issue)

---

## Phase 1: 2024 Full Pipeline Re-Run

### Step 1 — Ingest 2024 data
```bash
cd /home/bradwolaver/projects/rg/santafe/buckman
python3 step1_ingest_buckman_data.py --year 2024
```
**Expected outputs:**
- `output/ingested_data/2024/2024_Table_1_updated.xlsx`
- `output/ingested_data/2024/2024_Table_2_output.xlsx`
- `output/ingested_data/2024/2024_Table_2_output.csv`
- 12 monthly CSV files (`2024_01_JAN.csv` … `2024_12_DEC.csv`)

**Accept criteria:** Script exits 0; no ERROR lines in output; annual total plausible (900–1800 AF range)

### Step 2 — Update MODFLOW files for 2024
```bash
python3 step2_update_modflow.py --year 2024
```
**Expected outputs:**
- `output/modflow/2024/thruCY2165_2024.wel`
- `output/modflow/2024/CY2024.nam`

**Accept criteria:** WEL file size ~3.2 MB; exit 0

### Step 3 — Run MODFLOW96 for 2024 (via Wine)
```bash
bash step3_run_modflow.sh --year 2024
```
**Expected outputs:**
- `output/modflow/2024/CY2024.lst` (~9.7 MB)
- `output/modflow/2024/CY2024_riv.flx` (~31 MB)
- `output/modflow/2024/CY2024_ghb.flx` (~31 MB)

**Accept criteria:** LST file shows 0 errors; mass balance ≤ 0.01%; 2136 stress periods

### Step 4 — Generate depletion tables for 2024
```bash
python3 step4_generate_depletion_tables.py --year 2024
```
**Expected outputs:**
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx`
- `output/modflow/2024/depletions/CY2024` (post-processor text file)

**Accept criteria:** Exit 0; tables contain expected columns; depletion ≤ pumping

---

## Phase 2: 2024 V&V — All Layers

### V&V 2.1 — pytest Layers 0, 0.5, 1 (smoke, edge, conservation)
```bash
python3 run_all_tests.py --year 2024
```
- Runs: `tests/test_ingest_buckman_data.py`, `tests/test_update_modflow.py`,
  `tests/test_stream_depletions.py`, `tests/test_conservation.py`,
  `tests/test_edge_cases.py`, `tests/test_modflow_geometry.py`,
  `tests/test_generate_depletion_tables.py`
- **Accept criteria:** 0 failures; FLAGS are noted but not blocking

### V&V 2.2 — Ballpark / physics checks
```bash
python3 validation/ballpark_check.py --year 2024
```
- Checks depletion-to-pumping ratios, physical bounds

### V&V 2.3 — Temporal consistency
```bash
python3 validation/temporal_consistency.py --year 2024
```

### V&V 2.4 — 2024 Regression Harness (Layer 5 — highest value)
```bash
cd validation/2024
python3 run_regression_2024.py
cd ../..
```
- Compares freshly generated 2024 tables against frozen expected outputs in
  `validation/2024/expected_outputs/`
- **Accept criteria:** Exit 0; all cell-level comparisons within tolerances.yaml

### V&V 2.5 — step5_verify_workflow.py
```bash
python3 step5_verify_workflow.py --year 2024
```

---

## Phase 3: 2025 Full Pipeline Re-Run (from scratch)

### Step 1 — Ingest 2025 data
```bash
python3 step1_ingest_buckman_data.py --year 2025
```
**Expected outputs:** Same structure as 2024 but in `output/ingested_data/2025/`
**Flag to investigate:** May 2025 anomaly — check step 1 output and compare May vs adjacent months

### Step 2 — Update MODFLOW files for 2025
```bash
python3 step2_update_modflow.py --year 2025
```
**Note:** Must use freshly generated 2024 WEL file as prior year input (year chaining)

### Step 3 — Run MODFLOW96 for 2025 (via Wine) — SLOW ~5-10 min
```bash
bash step3_run_modflow.sh --year 2025
```
**Expected outputs:**
- `output/modflow/2025/CY2025.lst` (~9.7 MB)
- `output/modflow/2025/CY2025_riv.flx` (~31 MB)
- `output/modflow/2025/CY2025_ghb.flx` (~31 MB)

**Accept criteria:** LST shows 0 errors; mass balance ≤ 0.01%; 2148 stress periods (2136 + 12 new months)

### Step 4 — Generate depletion tables for 2025
```bash
python3 step4_generate_depletion_tables.py --year 2025
```
**Expected outputs:**
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2025.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_2025.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_2025.xlsx`

---

## Phase 4: 2025 V&V — All Layers

### V&V 4.1 — pytest Layers 0, 0.5, 1
```bash
python3 run_all_tests.py --year 2025
```

### V&V 4.2 — Ballpark / physics checks
```bash
python3 validation/ballpark_check.py --year 2025
```

### V&V 4.3 — Temporal consistency
```bash
python3 validation/temporal_consistency.py --year 2025
```

### V&V 4.4 — step5_verify_workflow.py
```bash
python3 step5_verify_workflow.py --year 2025
```

**Note:** No independent regression harness exists for 2025 (no frozen expected_outputs).
The 2024 regression harness (Phase 2) serves as the code-level regression test.

---

## Phase 5: Investigate FLAGS / Anomalies

After each year's pipeline run, check for:
1. **May 2025 anomaly** — compare May pumping rate vs April/June; flag if outlier > 2σ
2. **Workflow log FAIL causes** — prior FAIL logs had 224/0 pass/fail but FAIL status; investigate source
3. **Year-over-year comparison** — 2025 total 1351.91 AF vs prior 5-yr avg 1100 AF (+22.9%); confirm physically plausible

---

## Phase 6: Output Documentation

Create output file: `.claude/plans/P_FULL_PIPELINE_2024_2025_OUTPUT.md` with:
- All step exit codes and stdout summaries
- Final table values (totals from each table)
- V&V pass/fail summary per layer
- Any FLAGS or anomalies with physical interpretation
- File inventory with sizes

---

## Tolerances and Acceptance Criteria

| Check | Threshold | Source |
|-------|-----------|--------|
| Annual pumping total | ±0.01 MG (10,000 gal) | `src/constants.py` ANNUAL_SUM_TOLERANCE_MG |
| Daily sum closure | ±0.001 MGD (INFO), ±0.005 MGD (ERROR) | `src/constants.py` |
| MODFLOW mass balance | ≤ 0.01% | MODFLOW96 standard |
| Depletion ≤ pumping | Conservation law | Layer 1 test |
| Regression cell match | Per tolerances.yaml | `validation/2024/tolerances.yaml` |

---

## Known Risks

1. **Wine/MODFLOW96 step 3** is the slowest step (~5-10 min per year); non-interactive
2. **Year chaining** — 2025 WEL file depends on 2024 WEL output; order matters
3. **FLAGS vs FAIL** — prior FAIL logs may reflect a workflow-logging bug, not data error; investigate
4. **May 2025** — unknown anomaly; will flag but not halt unless conservation law violated

---

## Flagged Uncertainties

- [ ] What caused the "FAIL" log status when tests show 0 failures? (likely a step-level non-zero exit code unrelated to pytest)
- [ ] Is the +22.9% year-over-year increase in 2025 pumping physically expected or a data issue?
- [ ] Does `run_all_tests.py` include the regression harness as a layer, or is it separate?

---

## Success Criteria

- [ ] Steps 1-4 complete with exit 0 for both 2024 and 2025
- [ ] All pytest layers pass (0 failures) for 2024
- [ ] 2024 regression harness passes (cell-level comparison within tolerances)
- [ ] All pytest layers pass (0 failures) for 2025
- [ ] Tables 1, 2, 3, 4, 5 generated fresh for 2025
- [ ] Any FLAGS documented with physical interpretation
- [ ] Output file created with complete audit trail
