# Adversarial Review Output: Leap Year Fix & Table Validation Audit

**Reviewer**: Independent audit (40+ yr groundwater modeling, software engineering)
**Date**: 2026-02-20
**Scope**: All changes from the Table 3 leap year bug fix

---

## Audit Results Summary

| Audit | Description | Result |
|-------|-------------|--------|
| **7** | Full test suite (224 tests + ruff + mypy) | **PASS** |
| **5** | Tolerance system integrity (hardcoded + YAML) | **PASS** |
| **6** | Dangling references to deleted files | **PASS** |
| **1B** | Cell-by-cell Table 3 (2024): 237 cells | **PASS** — max diff 0.0000615 AF |
| **8** | Tables 4 & 5 regression | **PASS** — both OK at 0.01 AF |
| **1A** | Hand calculation of February delta | **PASS** — exact to 10 decimal places |
| **4** | MODFLOW PERLEN leap year consistency | **PASS** — .bas file confirms 29d/28d |
| **2** | Table 5 La Cienega leap year | **FLAG** — see findings below |
| **3** | Table 4 consistency | **PASS** — intentional 28-day convention |
| **1C** | Year 2025 spot check | **PASS** — headers "1988-2025", values correct |

**Overall verdict: 9 PASS, 1 FLAG**

---

## Audit 1A: Hand Calculation — PASS

Proved the leap year fix is mathematically correct by computing the exact AF delta from 1 extra February day.

**Year 2025 (non-leap)**:
- R POJOAQUE Feb cfs = 0.0842370000
- Hand-computed delta = 0.0842370 * 1 day * 86400/43560 = **0.1670816529 AF**
- Actual (buggy - fixed) = **0.1670816529 AF** — exact match to 10 decimal places

**Year 2028 (leap)**:
- Fix uses `isleap(2028) = True`, same as old code → delta = **0.000000** — correct

---

## Audit 1B: Cell-by-Cell Table 3 (2024) — PASS

- **237 numeric cells** compared (43 years × ~6 columns, minus None residuals)
- **0 failures** at 0.001 AF tolerance
- **Max absolute diff**: 0.0000615 AF (year 2029, Pojoaque Superposition)
- Cause of non-zero diff: floating-point accumulation in 12-month cfs→AF summation (expected, physically insignificant)

---

## Audit 1C: Year 2025 Spot Check — PASS

- Column header: `"Impact of\n1988–2025 Pumping\n(Superposition)"` — correct
- Historical years (1988-2024): loaded from `Table_3_expected.xlsx`, match exactly
- Generated years (2025-2030): computed from MODFLOW post-processor with correct leap year handling
- Year 2024 values in 2025 xlsx match expected file to full precision

---

## Audit 2: Table 5 (La Cienega Springs) — FLAG

### Finding

`stream_depletions.py:1092` uses implicit `use_leap_year=False`:
```python
cumulative_af = cfs_monthly_to_af_annual(lc_springs_cfs)
```

This means Table 5 uses **28 days for February in ALL years**, even leap years.

### Impact Analysis

| Year | Leap? | AF (28-day) | AF (29-day) | Delta | Expected | Better Match |
|------|-------|-------------|-------------|-------|----------|-------------|
| 2004 | Yes | 0.445866 | 0.446969 | 0.001103 | 0.45 | 29-day |
| 2008 | Yes | 1.159428 | 1.162435 | 0.003007 | 1.16 | **28-day** |
| 2012 | Yes | 1.812260 | 1.817058 | 0.004798 | 1.82 | 29-day |
| 2016 | Yes | 2.445959 | 2.452500 | 0.006541 | 2.45 | 29-day |
| 2020 | Yes | 3.055533 | 3.063747 | 0.008214 | 3.06 | 29-day |
| 2024 | Yes | 3.731391 | 3.741412 | 0.010020 | 3.74 | 29-day |
| 2028 | Yes | 4.443312 | 4.455302 | 0.011990 | 4.446 | **28-day** |

**Score**: 5 of 7 leap years favor the leap-year-aware calculation. However, the expected values have only **2-3 decimal places** of precision, making this analysis **inconclusive** — the rounding noise is comparable to the delta magnitude.

### Recommendation

**DO NOT fix Table 5 now.** Rationale:
1. Expected validation data has insufficient precision (2 decimal places) to discriminate
2. All current values pass validation at the existing 0.01 AF tolerance
3. The delta (0.001-0.012 AF) is at or near the tolerance boundary
4. Fixing this could break the existing match for 2008 and 2028
5. A fix should only be applied when higher-precision expected data is available

**Action**: Add an explicit comment at line 1092 documenting this design decision:
```python
# NOTE: Uses non-leap year days (28 for Feb) for all years.
# Table 5 expected values have only 2-3 decimal places of precision,
# which is insufficient to determine the correct leap year convention.
# See ADVERSARIAL_REVIEW_OUTPUT.md for analysis. (2026-02-20)
```

---

## Audit 3: Table 4 — PASS

Table 4 intentionally uses `DAYS_VALIDATION` (28-day February) per the comment at line 978:
```python
"days_per_month": DAYS_VALIDATION,  # Table 4 uses non-leap year days
```

The expected validation file matches this convention. No fix needed.

---

## Audit 4: MODFLOW PERLEN — PASS

MODFLOW .bas file (`input/modflow/2023/thruCY2165.bas`) correctly encodes leap years:
- 2024 Feb PERLEN = 2505600 s (29 days × 86400) ✓
- 2025 Feb PERLEN = 2419200 s (28 days × 86400) ✓
- 2028 Feb PERLEN = 2505600 s (29 days × 86400) ✓

Python `calendar.isleap()` is consistent with what MODFLOW computes.

---

## Audit 5: Tolerance Integrity — PASS

| Table | Hardcoded | YAML abs | YAML rel | Consistent? |
|-------|-----------|----------|----------|-------------|
| 3 | 0.001 (TABLE3_AF) | 0.001 | 0.001 | Yes |
| 4 | 0.01 (general AF) | 0.1 | 0.01 | Yes (YAML looser) |
| 5 | 0.01 (general AF) | 0.01 | 0.005 | Yes |

No tolerance was accidentally tightened or loosened.

---

## Audit 6: Dangling References — PASS

No references to `validation/TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx` in any `.py` or `.yaml` file. Only mentions in `.claude/plans/` documentation (harmless).

No references to `INCORRECT` in any `.py` or `.yaml` file.

---

## Audit 7: Full Test Suite — PASS

- **224 tests passed** in 3.79s
- **ruff**: All checks passed
- **mypy**: Success, no issues in 2 source files

---

## Audit 8: Tables 4 & 5 Regression — PASS

`step4_generate_depletion_tables.py --year 2024` output:
- Table 3: OK (all 6 fields diff=0.000000)
- Table 4: OK (max diff 0.009084 AF, within 0.01 tolerance)
- Table 5: OK (diff 0.008609 AF, within 0.01 tolerance)
- **OVERALL STATUS: OK**

---

## Open Items

1. **Table 5 leap year comment** — Add documentation comment at `stream_depletions.py:1092` explaining why `use_leap_year=False` is used (inconclusive expected data). **LOW PRIORITY**.

2. **Table 5 expected data precision** — If/when higher-precision Table 5 expected values become available (4+ decimal places), revisit the leap year convention. This would conclusively resolve whether `use_leap_year=calendar.isleap(year)` should be applied to Table 5.
