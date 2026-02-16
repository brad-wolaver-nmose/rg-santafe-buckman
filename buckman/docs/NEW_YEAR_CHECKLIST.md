# New Year Processing Checklist

Use this checklist when processing a new year (e.g., moving from 2025 to 2026).

## Prerequisites (Before Starting)

- [ ] Previous year (N-1) fully processed through all 5 tables
- [ ] New year CSV available: `input/csv/Buckman_Well_Prod_{year}.csv`
- [ ] Baseline files still present in `input/modflow/2023/`

## Step 1: Ingest Pumping Data

```bash
python3 step1_ingest_buckman_data.py --year {YEAR}
```

**Verify:**
- [ ] Script reports which Table 1 template is being used
- [ ] Output files created:
  - [ ] `output/ingested_data/{year}_Table_1_updated.xlsx`
  - [ ] `output/ingested_data/{year}_Table_2_output.xlsx`
  - [ ] 12 monthly CSV files (`{year}_01_JAN.csv` through `{year}_12_DEC.csv`)

**What to check:**
- Table 1 should have one new row for the new year
- Table 2 should have 12 rows (monthly pumping data)
- Monthly CSVs should have data for all wells

## Step 2: Generate MODFLOW Input Files

```bash
python3 step2_update_modflow.py --year {YEAR}
```

**Verify:**
- [ ] Script reports source year and input file paths
- [ ] Script confirms chaining mode (or baseline if year 2024)
- [ ] Output directory created: `output/modflow/{year}/`
- [ ] WEL file created: `thruCY2165_{year}.wel`
- [ ] NAM file created: `CY{year}.nam`
- [ ] 10 baseline files copied:
  - [ ] `modflow96.exe`
  - [ ] `sflcs.bcf`
  - [ ] `sflcs.sip`
  - [ ] `thruCY2165.bas`
  - [ ] `thruCY2165.ghb`
  - [ ] `thruCY2165.oc`
  - [ ] `thruCY2165.riv`
  - [ ] `sfmodflx_2245.exe`
  - [ ] `verify_modflow_run.py`
  - [ ] `verify_depletion.py`
- [ ] NAM file verification passed (all referenced files exist)

**What to check:**
- WEL file should be larger than previous year (has 324 new lines)
- NAM file should reference CY{year} consistently

## Step 3: Run MODFLOW96 (Manual)

```bash
cd output/modflow/{year}
wine modflow96.exe CY{year}.nam
```

**Verify:**
- [ ] MODFLOW runs without errors
- [ ] No warnings about missing files
- [ ] Output files created:
  - [ ] `CY{year}.lst` (list file)
  - [ ] `CY{year}_riv.flx` (~30 MB)
  - [ ] `CY{year}_ghb.flx` (~30 MB)
- [ ] Run verification: `python3 verify_modflow_run.py {year}`
- [ ] Mass balance errors < 0.1%
- [ ] All stress periods converged (check .lst file)

**What to check:**
- List file should show successful completion
- Flux files should be similar size to previous year
- Convergence should occur in 3-6 iterations per stress period

## Step 4: Run Post-Processor (Manual)

```bash
cd output/modflow/{year}
wine sfmodflx_2245.exe
# When prompted, enter: CY{year}
```

**Verify:**
- [ ] Post-processor runs without errors
- [ ] Output file created: `CY{year}_dep` (depletion file)
- [ ] File size is reasonable (~30-40 KB for typical year)

**What to check:**
- Depletion file should have data for all stream segments
- File should be similar size to previous year

## Step 5: Generate Depletion Tables

```bash
cd ../../..  # Return to project root
python3 step3_generate_depletion_tables.py --year {YEAR}
```

**Verify:**
- [ ] Script reports directory structure (FLAT for 2025+)
- [ ] Script shows flux file sizes
- [ ] Output files created:
  - [ ] `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx`
  - [ ] `output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx`
  - [ ] `output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx`

**What to check:**
- Table 3: Rio Pojoaque-Nambe and Rio Tesuque depletions
- Table 4: Rio Grande above/below Otowi depletions
- Table 5: La Cienega Springs cumulative depletions

## Step 6: Comprehensive Verification

```bash
python3 verify_workflow.py --year {YEAR}
```

**Verify:**
- [ ] All file checks pass
- [ ] All pytest tests pass
- [ ] Custom verification scripts pass
- [ ] Overall summary shows all checks passed

## Step 7: Manual Spot-Check (Domain Expert Verification)

- [ ] Open Table 1: Verify new year row has reasonable AFY values
- [ ] Open Table 2: Verify monthly totals match input CSV
- [ ] Open Table 3: Check stream depletion trends vs previous years
- [ ] Open Table 4: Check Rio Grande depletion patterns
- [ ] Open Table 5: Check cumulative La Cienega trends
- [ ] Perform manual calculation to verify one cell in each table

**Domain expertise checks:**
- Do depletion values make physical sense?
- Are trends consistent with previous years?
- Are there any unexpected spikes or drops?

## Final Steps

- [ ] Archive results (optional): Copy tables to archive directory
- [ ] Update documentation if workflow changes discovered
- [ ] Commit results to git (if using version control):
  ```bash
  git add output/
  git commit -m "feat: Complete {year} Buckman wellfield depletion workflow"
  ```

## Common Issues and Solutions

### "Input .wel file not found"
**Solution:** Ensure year N-1 was processed through Step 2
```bash
python3 step2_update_modflow.py --year {N-1}
```

### "Table 2 CSV not found"
**Solution:** Run Step 1 for current year first
```bash
python3 step1_ingest_buckman_data.py --year {year}
```

### "Flux file not found"
**Solution:** Run MODFLOW96 (Step 3)
```bash
cd output/modflow/{year}
wine modflow96.exe CY{year}.nam
```

### "Post-processor output not found"
**Solution:** Run sfmodflx_2245.exe (Step 4)
```bash
cd output/modflow/{year}
wine sfmodflx_2245.exe
```

### MODFLOW fails to converge
**Check:**
1. Pumping rates are reasonable (not extreme values)
2. Input files match expected format
3. Baseline files are correct versions
4. No file corruption occurred

### Depletion values look wrong
**Check:**
1. MODFLOW ran successfully (check mass balance in .lst)
2. Post-processor used correct year designation
3. Previous year's baseline is correct
4. Units are correct throughout

## Time Estimates

- Step 1 (Ingest): ~1 minute
- Step 2 (MODFLOW Setup): ~1 minute
- Step 3 (Run MODFLOW96): ~5-10 minutes
- Step 4 (Post-processor): ~1 minute
- Step 5 (Depletion Tables): ~1 minute
- Step 6 (Verification): ~2 minutes
- Step 7 (Manual Spot-Check): ~15-30 minutes

**Total time:** ~30-45 minutes per year

## See Also

- `docs/BUCKMAN_WORKFLOW.md` - Complete workflow documentation
- `docs/FILE_DEPENDENCIES.md` - Visual file dependency diagram
- `verify_workflow.py --help` - Verification script usage
