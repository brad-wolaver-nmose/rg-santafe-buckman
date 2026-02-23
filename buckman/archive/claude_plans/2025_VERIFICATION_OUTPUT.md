# 2025 Buckman Workflow Verification Output

**Date:** 2026-02-18
**Status:** PASS

## Pipeline Execution

| Step | Script | Status |
|------|--------|--------|
| Step 1 | step1_ingest_buckman_data.py --year 2025 | COMPLETE |
| Step 2 | step2_update_modflow.py --year 2025 | COMPLETE |
| Step 3 | step3_run_modflow.sh --year 2025 | COMPLETE |
| Step 4 | step4_generate_depletion_tables.py --year 2025 | COMPLETE (re-run) |

**Note:** Step 4 was re-run after reboot to ensure complete table generation.

## Generated Files

- `output/ingested_data/2025_Table_1_updated.xlsx`
- `output/ingested_data/2025_Table_2_output.xlsx`
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2025.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_2025.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_2025.xlsx`

## Verification Summary

| Metric | 2025 Value | 2024 Value | YoY Change | Status |
|--------|------------|------------|------------|--------|
| Total Pumping | 1,351.91 AF | 1,372.92 AF | -1.5% | PASS |
| Rio Pojoaque | 61.42 AF | 60.80 AF | +1.0% | PASS |
| Rio Tesuque | 33.65 AF | 33.58 AF | +0.2% | PASS |
| Otowi (BK 1,7,8) | 493.80 AF | 469.90 AF | +5.1% | PASS |
| La Cienega Springs | 3.92 AF | 3.74 AF | +4.8% | PASS |

## Verification Checks

1. **S1 - File Completeness:** PASS - All 5 output tables exist with reasonable sizes
2. **S2 - Cross-Table Consistency:** PASS - Depletions < Pumping
3. **S3 - Physical Bounds:** PASS - All YoY changes < 65%
4. **S4 - MODFLOW Sanity:** PASS - Convergence verified

## Overall Result: PASS
