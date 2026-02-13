# Depletion Output Verification (CY2025)

**Date:** 2026-02-12 09:55
**Target Year:** 2025
**Comparison Year:** 2024
**Input File:** `CY2025_dep`
**Comparison File:** `CY2024` (prior year)

---

## File Structure Checks

| File | Status |
|------|--------|
| CY2025_dep | File structure OK (timesteps=2136) |
| CY2024 | File structure OK (timesteps=2136) |

**File Sizes:** 2025=1,481,893 bytes, 2024=1,481,893 bytes
**Size Match:** PASS

---

## Summary Value Comparison

Depletion = reduced streamflow in CFS (positive values expected)

### Annual Average Depletion by Location

| Location | 2024 Avg (CFS) | 2025 Avg (CFS) | Diff % | Status |
|----------|----------------|----------------|--------|--------|
| R POJOAQUE | 0.0837 | 0.0846 | +1.0% | PASS |
| R TESUQUE | 0.0285 | 0.0293 | +2.7% | PASS |
| RIO GRANDE | 1.3028 | 1.3493 | +3.6% | PASS |
| RIV  TOTAL | 1.4150 | 1.4632 | +3.4% | PASS |
| LC SPRINGS | 0.0052 | 0.0054 | +5.0% | PASS |

### RIO GRANDE Monthly Depletion

| Month | 2024 (CFS) | 2025 (CFS) | Diff % |
|-------|------------|------------|--------|
| JAN | 1.0479 | 1.3690 | +30.6% |
| FEB | 1.0799 | 1.2405 | +14.9% |
| MAR | 1.0378 | 1.3828 | +33.2% |
| APR | 1.0804 | 1.4239 | +31.8% |
| MAY | 1.1658 | 1.2735 | +9.2% |
| JUN | 1.2639 | 1.2167 | -3.7% |
| JUL | 1.5243 | 1.2318 | -19.2% |
| AUG | 1.6426 | 1.6051 | -2.3% |
| SEP | 1.5594 | 1.5970 | +2.4% |
| OCT | 1.5332 | 1.4205 | -7.3% |
| NOV | 1.3635 | 1.2741 | -6.6% |
| DEC | 1.3346 | 1.1567 | -13.3% |

---

## Sign Check

All summary values positive: **PASS**

---

## Summary

### Depletion Results

- RIO GRANDE avg depletion 2025: **1.3493 CFS**
- RIO GRANDE avg depletion 2024: **1.3028 CFS**

### Overall Result: **PASS - All checks passed**
