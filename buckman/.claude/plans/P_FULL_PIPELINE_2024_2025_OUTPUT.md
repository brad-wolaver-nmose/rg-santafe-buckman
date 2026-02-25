# FULL PIPELINE OUTPUT: 2024 V&V + 2025 Fresh Run
**Run Date:** 2026-02-25
**Operator:** bradwolaver / Claude Code (claude-sonnet-4-6)
**Git:** master, clean (plan file only untracked)

---

## Executive Summary

| Year | Pipeline | V&V | Regression | Status |
|------|----------|-----|------------|--------|
| 2024 | PASS | PASS | PASS | ✅ CLEAN |
| 2025 | PASS | PASS | N/A (no baseline) | ✅ CLEAN |

Both years completed with **0 hard test failures**. One pre-existing bug in
`ballpark_check.py` (wrong column name for La Cienega) was fixed during this run.
Two path-stale issues in `step5_verify_workflow.py` and `temporal_consistency.py`
are noted (one fixed, one documented); none affect data integrity.

---

## Phase 1 + 2: 2024 Full Pipeline + V&V

### Step 1 — Ingest 2024
- **Exit code:** 0
- **Records:** 366 daily records (leap year), Jan–Dec 2024
- **Annual total:** 1372.92 AFY
- **2024 rank:** 12th of 37 years (1=lowest pumping)
- **Daily sum mismatches:** 6 INFO-level (rounding noise, all < 0.0015 MGD) — benign
- **Flagged well-months:** 0
- **Files created:** 15 (12 monthly CSVs, Table 1, Table 2, QA summary)

### Step 2 — Update MODFLOW for 2024
- **Exit code:** 0
- **Mode:** BASELINE (sourced from input/modflow/2023/thruCY2165.wel)
- **Validation:** 312/312 well-month rates validated; NAM and WEL byte-identical to reference
- **WEL file:** output/modflow/2024/thruCY2165_2024.wel

### Step 3 — Run MODFLOW96 for 2024
- **Exit code:** 0
- **Runtime:** 5 seconds
- **Stress periods:** 2136 (expected)
- **Mass balance:** ≤ 0.01%
- **Output files:** CY2024.lst (10.1 MB), CY2024_riv.flx (31.5 MB), CY2024_ghb.flx (31.5 MB)

### Step 4 — Generate Depletion Tables for 2024

| Table | Key Values | Validation |
|-------|-----------|------------|
| Table 3 - Pojoaque | 60.797 AF (0.000 residual + 60.797 superposition) | diff=0.000 ✅ |
| Table 3 - Tesuque | 33.583 AF (12.877 residual + 20.706 superposition) | diff=0.000 ✅ |
| Table 4 - Above Otowi | 101.427 AF | diff=0.000 ✅ |
| Table 4 - Below Otowi | 842.949 AF | diff<0.01 AF ✅ |
| Table 5 - La Cienega cumulative (2024) | 3.741 AF | diff<0.002 AF ✅ |
| Table 5 - La Cienega annual (2024) | 0.201 AF | diff<0.002 AF ✅ |

### V&V — 2024

| Layer | Result | Detail |
|-------|--------|--------|
| Ballpark (physics) | PASS | 8/8 checks — note: fixed pre-existing column name bug |
| Layer 0 (smoke) | PASS | 187 tests |
| Layer 0.5 (edge) | PASS | 30 tests |
| Layer 1 (conservation) | PASS | 1 test |
| Layer 2 (temporal) | PASS | No flags |
| Layer 3 (cross-comparison) | SKIPPED | Scientifically rejected in P6 |
| Layer 5 (regression harness) | PASS | 2889/2889 cells across all 5 tables |
| Layer 6 (provenance manifest) | Generated | output/manifests/buckman_manifest_2024.json |
| step5_verify_workflow.py | 218/218 hard tests PASS | 30/38 file path checks (8 misses = stale flat-path in script, not data errors) |
| **TOTAL** | **218 passed, 0 failed** | **WORKFLOW LOG: 2024_workflow_log_20260225_120545_PASS.md** |

---

## Phase 3 + 4: 2025 Full Pipeline + V&V

### Step 1 — Ingest 2025
- **Exit code:** 0
- **Records:** 365 daily records (standard year), Jan–Dec 2025
- **Annual total:** 1351.91 AFY
- **2025 rank:** 12th of 38 years (1=lowest pumping)
- **YoY change:** −1.5% vs 2024 (1372.92 → 1351.91 AF)
- **Daily sum mismatches:** 12 INFO-level (rounding noise) — benign
- **Flagged well-months:** 0

**⚠️ FLAG — May 2025 Anomaly:**
- May total: **4.05 AF** (expected ~100–175 AF based on neighbors)
- APR: 139.31 AF → MAY: 4.05 AF → JUN: 76.83 AF
- 97% drop from April — highly anomalous
- Consistent with existence of `2025_MAY_CHECK.xlsx` from Feb 2026 investigation
- Conservation law is NOT violated (low pumping = low depletion)
- **Interpretation:** Likely a data gap or operational maintenance shutdown in May 2025
- **Action required:** Verify with SFPUC operations records before final regulatory submission

### Step 2 — Update MODFLOW for 2025
- **Exit code:** 0
- **Mode:** CHAINED (sourced from output/modflow/2024/thruCY2165_2024.wel)
- **Validation:** Skipped (no 2025 reference files — expected)
- **WEL file:** output/modflow/2025/thruCY2165_2025.wel

### Step 3 — Run MODFLOW96 for 2025
- **Exit code:** 0
- **Runtime:** 5 seconds
- **Stress periods:** 2136 (expected)
- **Mass balance:** ≤ 0.01%
- **Output files:** CY2025.lst (10.1 MB), CY2025_riv.flx (31.5 MB), CY2025_ghb.flx (31.5 MB)

### Step 4 — Generate Depletion Tables for 2025

| Table | Key Values | Validation |
|-------|-----------|------------|
| Table 3 - Pojoaque | **61.252 AF** (0.000 residual + 61.252 superposition) | PROJECTED_WARN: diff=0.16 AF vs prior projection (expected for fresh run) |
| Table 3 - Tesuque | **33.595 AF** (12.387 residual + 21.208 superposition) | PROJECTED_WARN: diff=0.02 AF (expected) |
| Table 4 - Above Otowi | **102.372 AF** | No 2025 reference (expected) |
| Table 4 - Below Otowi | **874.901 AF** | No 2025 reference (expected) |
| Table 5 - La Cienega cumulative (2025) | **3.920 AF** | diff<0.001 AF ✅ |
| Table 5 - La Cienega annual (2025) | **0.180 AF** | diff<0.001 AF ✅ |

**Overall 2025 depletion status:** OK_WITH_SKIPPED (expected for new year)

### V&V — 2025

| Layer | Result | Detail |
|-------|--------|--------|
| Ballpark (physics) | SKIP (exit 4) | No 2025 baseline — expected and normal |
| Layer 0 (smoke) | PASS | 187 tests |
| Layer 0.5 (edge) | PASS | 30 tests |
| Layer 1 (conservation) | PASS | 1 test |
| Layer 2 (temporal) | 2 PASS, 1 FLAG | Annual total +/-: PASS; Envelope: PASS; Seasonal pattern: FLAG (r=0.546, threshold 0.75) — caused by May anomaly |
| Layer 3 (cross-comparison) | SKIPPED | Scientifically rejected in P6 |
| Layer 5 (regression harness) | N/A | No 2025 frozen expected outputs |
| Layer 6 (provenance manifest) | Generated | output/manifests/buckman_manifest_2025.json |
| step5_verify_workflow.py | 218/218 hard tests PASS | 35/39 file path checks (4 misses = stale flat-path for Table 1/2 in step5 script) |
| **TOTAL** | **218 passed, 0 failed** | **WORKFLOW LOG: 2025_workflow_log_20260225_120733_PASS.md** |

---

## Bugs Fixed During This Run

| Script | Bug | Fix |
|--------|-----|-----|
| `validation/ballpark_check.py:348` | `get_table5_la_cienega()` looked for column `"Total (AF)"` but Table 5 uses `"Total"` — caused hard exit-3 for 2024 | Added `"Total"` as first entry in `la_cienega_cols` list |
| `validation/temporal_consistency.py:161` | Looked for `output/ingested_data/{year}_Table_2_output.csv` (flat) but files now in `output/ingested_data/{year}/{year}_Table_2_output.csv` (nested) | Added nested path as primary, flat as fallback |

---

## Pre-Existing Issues (Not Fixed — Noted Only)

| Script | Issue | Impact |
|--------|-------|--------|
| `step5_verify_workflow.py` | Step 1 file checks use flat paths (`output/ingested_data/2024_Table_1_updated.xlsx`) instead of nested (`output/ingested_data/2024/2024_Table_1_updated.xlsx`) | 4 false-negative ✗ for Table 1/2 files; step still shows 218/0 pass/fail on hard tests |

---

## Root Cause: Prior FAIL Log Status

Prior 2025 workflow logs (2026-02-19) showed FAIL status despite 224/0 pass/fail.
Investigation: The `ballpark_check.py` column name bug (Table 5 `"Total"` vs `"Total (AF)"`)
triggered exit code 3 for 2024 but exit code 4 (skip) for 2025 (no baseline).
The FAIL logs were from 2024 ballpark check exits, not 2025 test failures.
**Resolution:** Fixed by this run.

---

## Output Files — 2025 Final Tables

| File | Path | Size |
|------|------|------|
| Table 1 — Historical pumping (1988–2025) | output/ingested_data/2025/2025_Table_1_updated.xlsx | 9.3 KB |
| Table 2 — Monthly pumping detail 2025 | output/ingested_data/2025/2025_Table_2_output.xlsx | 6.6 KB |
| Table 3 — Rio Pojoaque & Rio Tesuque | output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2025.xlsx | 7.9 KB |
| Table 4 — Rio Grande above/below Otowi | output/depletion/TABLE_4_Rio_Grande_Otowi_2025.xlsx | 12.0 KB |
| Table 5 — La Cienega Springs cumulative | output/depletion/TABLE_5_La_Cienega_Springs_2025.xlsx | 6.1 KB |

---

## Key 2025 Numbers (Regulatory Context)

| Metric | Value |
|--------|-------|
| Total pumping | **1351.91 AF** |
| Rio Grande below Otowi (compact charge) | **874.90 AF** |
| Rio Grande above Otowi | **102.37 AF** |
| Rio Pojoaque depletion | **61.25 AF** (0.00 residual + 61.25 superposition) |
| Rio Tesuque depletion | **33.60 AF** (12.39 residual + 21.21 superposition) |
| La Cienega cumulative (since 2004) | **3.92 AF** |
| La Cienega annual increment | **0.18 AF** |

---

## Flags Requiring Human Review Before Regulatory Submission

1. **May 2025 Near-Zero Pumping (HIGH PRIORITY)**
   - May 2025 total: 4.05 AF vs. typical 100–175 AF
   - Verify with SFPUC operations records
   - If data gap: determine how to handle (zero fill vs. interpolate vs. report as-is)
   - If legitimate shutdown: document operational basis

2. **Seasonal Pattern Flag (SOFT — caused by May anomaly)**
   - Layer 2 FLAG: r=0.546 < 0.75 threshold
   - Root cause is the May anomaly above — resolves if May is corrected
   - Not an independent issue

---

## Workflow Logs Generated

| Log | Status |
|-----|--------|
| output/logs/2024_workflow_log_20260225_120545_PASS.md | PASS |
| output/logs/2025_workflow_log_20260225_120733_PASS.md | PASS |
