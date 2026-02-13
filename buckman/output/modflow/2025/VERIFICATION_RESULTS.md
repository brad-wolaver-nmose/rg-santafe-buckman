# MODFLOW96 CY2025 Run Verification Results

**Date:** 2025-02-12
**Model:** Buckman Well Field Depletion Model
**Input:** CY2025.nam with thruCY2165_2025.wel

---

## Output Files Check

| File | Size | Status |
|------|------|--------|
| CY2025.lst | 10.1 MB | PASS |
| CY2025_ghb.flx | 31,484,640 bytes | PASS (matches 2024) |
| CY2025_riv.flx | 31,484,640 bytes | PASS (matches 2024) |

---

## Listing File Analysis

| Metric | Value | Status |
|--------|-------|--------|
| Errors in log | 0 | PASS |
| Stress periods | 2136 | PASS (expected 2136) |
| Max mass balance discrepancy | 0.01% | PASS |
| Convergence | 3-6 iterations/period | PASS |

---

## 2025 Pumping Rates Verification

Verified pumping rates in stress periods 445-456 (JAN-DEC 2025):

| Month | Well | Expected (ft³/s) | Actual (ft³/s) | Status |
|-------|------|------------------|----------------|--------|
| JAN | BUCKMAN 1 | -0.59084 | -0.59084 | PASS |
| JAN | BUCKMAN 13 | -0.13109 | -0.13109 | PASS |
| SEP | BUCKMAN 1 | -0.52801 | -0.52801 | PASS |
| SEP | BUCKMAN 6 | -0.35063 | -0.35063 | PASS |
| SEP | BUCKMAN 10 | -0.17017 | -0.17017 | PASS |

---

## Summary

```
Output files:     PASS
Listing analysis: PASS
Pumping rates:    PASS

Overall: ALL CHECKS PASSED
```

---

## Files in Output Directory

```
CY2025.lst           - MODFLOW listing file (run log)
CY2025.nam           - MODFLOW name file (input)
CY2025_ghb.flx       - General Head Boundary flux (binary)
CY2025_riv.flx       - River flux (binary)
modflow96.exe        - MODFLOW96 executable
sflcs.bcf            - Block-Centered Flow package
sflcs.sip            - SIP solver parameters
thruCY2165.bas       - Basic package
thruCY2165.ghb       - General Head Boundary package
thruCY2165.oc        - Output Control
thruCY2165.riv       - River package
thruCY2165_2025.wel  - Well package (2025 pumping rates)
verify_modflow_run.py - This verification script
VERIFICATION_RESULTS.md - This results file
```

---

## Next Step

Ready for **Step 5: Generate Depletion Tables**

```bash
python3 step3_generate_depletion_tables.py --year 2025
```
