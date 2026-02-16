# File Dependency Chain: Year-to-Year Workflow

## Overview
The Buckman workflow chains years together, using outputs from year N-1 as inputs for year N.

## File Flow Diagram

```
Year 2024 (Baseline)                Year 2025 (Chained)              Year 2026 (Chained)
─────────────────────               ─────────────────────            ─────────────────────

INPUT:                              INPUT:                           INPUT:
  2023 baseline files               2024 outputs                     2025 outputs
  ├─ thruCY2165.wel (2003-2023)     ├─ thruCY2165_2024.wel          ├─ thruCY2165_2025.wel
  └─ Buckman_2024.csv               ├─ 2024_Table_1_updated.xlsx    ├─ 2025_Table_1_updated.xlsx
                                    └─ Buckman_2025.csv              └─ Buckman_2026.csv

STEP 1: Ingest                      STEP 1: Ingest                   STEP 1: Ingest
  ↓ Table 1 template from 2023      ↓ Table 1 from 2024 output       ↓ Table 1 from 2025 output
  ↓ Generate Tables 1 & 2           ↓ Generate Tables 1 & 2          ↓ Generate Tables 1 & 2

OUTPUT:                             OUTPUT:                          OUTPUT:
  ├─ 2024_Table_1_updated.xlsx      ├─ 2025_Table_1_updated.xlsx     ├─ 2026_Table_1_updated.xlsx
  └─ 2024_Table_2_output.csv        └─ 2025_Table_2_output.csv       └─ 2026_Table_2_output.csv

STEP 2: MODFLOW Setup               STEP 2: MODFLOW Setup            STEP 2: MODFLOW Setup
  ↓ Append 2024 to 2023 WEL         ↓ Append 2025 to 2024 WEL        ↓ Append 2026 to 2025 WEL
  ↓ Copy 10 baseline files          ↓ Copy 10 baseline files         ↓ Copy 10 baseline files
  ↓ Generate CY2024.nam             ↓ Generate CY2025.nam            ↓ Generate CY2026.nam

OUTPUT:                             OUTPUT:                          OUTPUT:
  └─ thruCY2165_2024.wel ────────>  └─ thruCY2165_2025.wel ──────>   └─ thruCY2165_2026.wel
     (2003-2024 pumping)               (2003-2025 pumping)              (2003-2026 pumping)

MANUAL: Run MODFLOW96               MANUAL: Run MODFLOW96            MANUAL: Run MODFLOW96

STEP 3: Depletion Tables            STEP 3: Depletion Tables         STEP 3: Depletion Tables
  ↓ Parse flux outputs              ↓ Parse flux outputs             ↓ Parse flux outputs
  ↓ Generate Tables 3-5             ↓ Generate Tables 3-5            ↓ Generate Tables 3-5
```

## Critical File Dependencies

### Step 1 Dependencies
- **Input:** `input/csv/Buckman_Well_Prod_{year}.csv`
- **Template (option 1):** `validation/Table_1_data_afy_{year}.xlsx`
- **Template (option 2):** `output/ingested_data/{year-1}/{year-1}_Table_1_updated.xlsx`
- **Output:** Tables 1 & 2 for current year

### Step 2 Dependencies
- **Input Table 2:** `output/ingested_data/{year}_Table_2_output.csv` (from Step 1)
- **Input WEL (baseline year 2024):** `input/modflow/2023/thruCY2165.wel`
- **Input WEL (year 2025+):** `output/modflow/{year-1}/thruCY2165_{year-1}.wel`
- **Baseline files (10 files):** Copied from `input/modflow/2023/` to `output/modflow/{year}/`
- **Output:** MODFLOW input files (.wel, .nam, and 10 baseline files)

**Baseline Files Copied:**
1. `modflow96.exe` - MODFLOW96 executable
2. `sflcs.bcf` - Block-Centered Flow package
3. `sflcs.sip` - Strongly Implicit Procedure solver
4. `thruCY2165.bas` - Basic package
5. `thruCY2165.ghb` - General Head Boundary package
6. `thruCY2165.oc` - Output Control
7. `thruCY2165.riv` - River package
8. `sfmodflx_2245.exe` - Stream flux post-processor
9. `verify_modflow_run.py` - MODFLOW verification script
10. `verify_depletion.py` - Depletion verification script

### Step 3 Dependencies
- **Input flux:** `output/modflow/{year}/CY{year}_riv.flx` (from MODFLOW96 run)
- **Input flux:** `output/modflow/{year}/CY{year}_ghb.flx` (from MODFLOW96 run)
- **Input post-processor:** `output/modflow/{year}/CY{year}_dep` (from sfmodflx_2245.exe)
- **Output:** Tables 3, 4, 5

## Directory Structure Changes

### Years 2024 and Earlier (Nested)
```
output/modflow/2024/
└── modflow/
    ├── CY2024.nam
    ├── thruCY2165_2024.wel
    ├── CY2024_riv.flx
    └── ...
```

### Years 2025 and Later (Flat)
```
output/modflow/2025/
├── CY2025.nam
├── thruCY2165_2025.wel
├── CY2025_riv.flx
└── ...
```

The scripts automatically detect and handle both structures.

## Troubleshooting File Dependencies

### "Input .wel file not found"
**Cause:** Year N-1 has not been processed through Step 2
**Solution:** Run `python3 step2_update_modflow.py --year {N-1}` first

### "Table 2 CSV not found"
**Cause:** Step 1 has not been run for current year
**Solution:** Run `python3 step1_ingest_buckman_data.py --year {year}` first

### "No template found for Table 1"
**Cause:** Missing validation file AND year N-1 not processed
**Solutions:**
1. Create validation file: `validation/Table_1_data_afy_{year}.xlsx`
2. OR process year N-1 first to generate template

### "Flux file not found"
**Cause:** MODFLOW96 has not been run
**Solution:**
```bash
cd output/modflow/{year}
wine modflow96.exe CY{year}.nam
```

### "Post-processor output not found"
**Cause:** sfmodflx_2245.exe has not been run
**Solution:**
```bash
cd output/modflow/{year}
wine sfmodflx_2245.exe
# Enter CY{year} when prompted
```

## Best Practices

1. **Always process years sequentially** (2024 → 2025 → 2026, etc.)
2. **Run verification after each year:** `python3 verify_workflow.py --year {year}`
3. **Check enhanced prerequisite messages** at each step for file source information
4. **Keep 2023 baseline files** - they are needed for all subsequent years

## See Also

- `docs/BUCKMAN_WORKFLOW.md` - Complete workflow guide
- `docs/NEW_YEAR_CHECKLIST.md` - Step-by-step processing checklist
- `verify_workflow.py` - Automated verification script
