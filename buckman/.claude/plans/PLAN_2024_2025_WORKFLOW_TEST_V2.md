# Plan: 2024 Workflow Comprehensive Verification (V2)

**Date:** 2026-02-18
**Status:** DRAFT - Awaiting Review
**Objective:** Post-fix comprehensive verification that 2024 workflow outputs are correct

---

## Background

Previous session completed:
- Bug fixes to `stream_depletions.py` (Table 3 historical preservation, Table 4 summary rows)
- Bug fixes to `step1_ingest_buckman_data.py` (Table 2 Total calculations)
- Updated expected files to match corrected outputs
- Regression test: All 5 tables PASS

This plan provides multi-layer verification to be "doubly sure" results are correct.

---

## Verification Strategy

| Layer | Type | Purpose |
|-------|------|---------|
| V1 | File Integrity | Expected files match generated files exactly |
| V2 | Clean Regeneration | Full pipeline from scratch produces same results |
| V3 | Spot-Check Values | Manual verification of key values against source |
| V4 | Cross-Table Consistency | Table relationships are internally consistent |
| V5 | Physical Reasonableness | Values within expected bounds |

---

## V1: File Integrity Check

### V1.1 Compare File Sizes
```bash
# Generated vs Expected should have identical sizes
ls -la output/ingested_data/2024_Table_1_updated.xlsx
ls -la validation/2024/expected_outputs/Table_1_expected.xlsx
# Repeat for Tables 2-5
```

### V1.2 Binary Comparison
```bash
diff <(xxd output/ingested_data/2024_Table_1_updated.xlsx) \
     <(xxd validation/2024/expected_outputs/Table_1_expected.xlsx)
# Or use md5sum
```

### V1.3 Regression Test
```bash
python3 validation/2024/run_regression_2024.py
# Expected: All 5 tables PASS
```

---

## V2: Clean Regeneration Test

Purpose: Verify pipeline produces identical results from scratch.

### V2.1 Backup Current Outputs
```bash
mkdir -p output/backup_2024
cp output/ingested_data/2024_Table_*.xlsx output/backup_2024/
cp output/depletion/TABLE_*_2024.xlsx output/backup_2024/
```

### V2.2 Clean Output Directory
```bash
rm output/ingested_data/2024_Table_*.xlsx
rm output/depletion/TABLE_*_2024.xlsx
```

### V2.3 Regenerate Full Pipeline
```bash
python3 step1_ingest_buckman_data.py --year 2024
python3 step2_update_modflow.py --year 2024
./step3_run_modflow.sh --year 2024  # ~40 min
python3 step4_generate_depletion_tables.py --year 2024
```

### V2.4 Compare Regenerated vs Backup
```bash
diff <(xxd output/ingested_data/2024_Table_1_updated.xlsx) \
     <(xxd output/backup_2024/2024_Table_1_updated.xlsx)
# Repeat for all tables
```

### V2.5 Re-run Regression
```bash
python3 validation/2024/run_regression_2024.py
# Must still PASS
```

---

## V3: Spot-Check Key Values

### V3.1 Table 1: Annual Pumping Totals
| Well | Source (CSV) | Generated | Expected | Match? |
|------|--------------|-----------|----------|--------|
| BK-01 | Input CSV total | Table 1 total | Expected total | ☐ |
| BK-07 | Input CSV total | Table 1 total | Expected total | ☐ |
| BK-08 | Input CSV total | Table 1 total | Expected total | ☐ |

**Verification:**
```python
# Read input CSV, sum BK-01 all months
import pandas as pd
csv = pd.read_csv('input/csv/Buckman_Well_Prod_2024/Buckman_Well_Prod_2024.csv')
csv[csv['Well'] == 'BK-01']['AF'].sum()
# Compare to Table 1 BK-01 2024 row total
```

### V3.2 Table 2: Monthly Distribution
- [ ] Row totals = sum of months
- [ ] Column totals = sum of wells
- [ ] Grand total matches Table 1 grand total

### V3.3 Table 3: Historical Values Preserved
| Year | Expected Pojoaque Total | Generated | Match? |
|------|-------------------------|-----------|--------|
| 1988 | 21.16019 | ? | ☐ |
| 2000 | ~30 | ? | ☐ |
| 2023 | ~59 | ? | ☐ |
| 2024 | ~61 | ? | ☐ (generated) |

### V3.4 Table 4: Depletion Sums
- [ ] Above Otowi Total = sum of Above Otowi reaches
- [ ] Below Otowi Total = sum of Below Otowi reaches
- [ ] Total RG = Above + Below
- [ ] Buckman Wells row matches pumping

### V3.5 Table 5: La Cienega
- [ ] Values non-negative
- [ ] Within historical bounds

---

## V4: Cross-Table Consistency

### V4.1 Pumping Conservation
```
Table 1 Total Pumping (2024) = Table 2 Total Pumping (2024) = Table 4 Buckman Wells row
```

### V4.2 Depletion <= Pumping
```
Table 4 Total RG Depletion <= Table 1 Total Pumping
```

### V4.3 Year Progression
```
Table 3 years should be monotonically increasing from 1988 to 2030
Table 4 months should sum to ~annual depletion
```

---

## V5: Physical Reasonableness

### V5.1 Historical Bounds
| Metric | Historical Range | 2024 Value | In Range? |
|--------|------------------|------------|-----------|
| Annual pumping (AF) | 866-1373 | ? | ☐ |
| Rio Pojoaque depletion | 15-65 AF | ? | ☐ |
| Rio Tesuque depletion | 40-180 AF | ? | ☐ |
| La Cienega impact | 0-5 AF | ? | ☐ |

### V5.2 Year-over-Year Change
```
Δ pumping 2024 vs 2023 should be < 65%
```

### V5.3 Monotonicity
- [ ] Cumulative depletions increase over time (1988→2030)

---

## Execution Checklist

| # | Task | Status |
|---|------|--------|
| 1 | V1.1: Check file sizes match | ☐ |
| 2 | V1.3: Run regression test | ☐ |
| 3 | V2.1: Backup outputs | ☐ |
| 4 | V2.2: Clean outputs | ☐ |
| 5 | V2.3: Regenerate pipeline | ☐ |
| 6 | V2.4: Compare regenerated vs backup | ☐ |
| 7 | V2.5: Re-run regression | ☐ |
| 8 | V3.1: Spot-check Table 1 wells | ☐ |
| 9 | V3.2: Verify Table 2 totals | ☐ |
| 10 | V3.3: Verify Table 3 historical | ☐ |
| 11 | V3.4: Verify Table 4 summaries | ☐ |
| 12 | V4.1: Check pumping conservation | ☐ |
| 13 | V4.2: Check depletion <= pumping | ☐ |
| 14 | V5.1: Check historical bounds | ☐ |
| 15 | Commit all changes to git | ☐ |

---

## MODFLOW Re-run Decision

**DECIDED:** Full re-run (MODFLOW96 runs in ~3 seconds, fast enough to always include).

The clean regeneration will run the complete pipeline including MODFLOW.

---

## Files to Check

### Input Files
- `input/csv/Buckman_Well_Prod_2024/Buckman_Well_Prod_2024.csv`
- `input/modflow/2023/thruCY2165.wel`

### Generated Output Files
| Table | Generated Path |
|-------|----------------|
| 1 | `output/ingested_data/2024_Table_1_updated.xlsx` |
| 2 | `output/ingested_data/2024_Table_2_output.xlsx` |
| 3 | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx` |
| 4 | `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx` |
| 5 | `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx` |

### Expected Files
| Table | Expected Path |
|-------|---------------|
| 1 | `validation/2024/expected_outputs/Table_1_expected.xlsx` |
| 2 | `validation/2024/expected_outputs/Table_2_expected.xlsx` |
| 3 | `validation/2024/expected_outputs/Table_3_expected.xlsx` |
| 4 | `validation/2024/expected_outputs/Table_4_expected.xlsx` |
| 5 | `validation/2024/expected_outputs/Table_5_expected.xlsx` |

---

## Success Criteria

**All of the following must be true:**

1. Regression test: All 5 tables PASS
2. File sizes: Generated = Expected for all tables
3. Clean regeneration produces identical results
4. Spot-check values match source data
5. Cross-table consistency checks pass
6. Values within physical bounds
7. All changes committed to git

---

## Output File

Results will be saved to: `.claude/plans/PLAN_2024_2025_WORKFLOW_TEST_V2_OUTPUT.md`
