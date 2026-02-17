# P5: Layer 2 — Temporal Consistency and Stationarity Checks

**Completed:** 2026-02-17
**Status:** IMPLEMENTED
**Layer:** 2 (Temporal Consistency)

---

## Summary

Successfully implemented Layer 2 temporal consistency checks. The `temporal_consistency.py` module validates year N outputs against historical temporal patterns (2022-2024) using data-driven thresholds.

---

## Decisions with Rationale

### 1. bounds.yaml Format

| Decision | Rationale |
|----------|-----------|
| **Keep as YAML** (not convert to JSON) | YAML is more human-readable for configuration files. JSON decision in P4 was for machine-generated output manifests. bounds.yaml already exists and is referenced by ballpark_check.py. |

### 2. Threshold Derivation Methodology

| Decision | Rationale |
|----------|-----------|
| **Data-driven thresholds** | With only 3 years of baseline (2022-2024), traditional statistical methods (mean +/- 2 sigma, 95% PI) are unreliable. Thresholds derived from observed variability + buffer are defensible in expert witness context. |

### 3. Multi-Year Trend Method

| Decision | Rationale |
|----------|-----------|
| **Range envelope with CV-adjusted buffer** (not 95% PI) | Traditional regression PI with n=3 is methodologically unsound: df=1, t_0.025=12.71 makes intervals meaninglessly wide (e.g., [-500, 3500] AF). Range envelope is honest about data limitations and scales buffer with observed variability. |

---

## Threshold Derivations (DATA-DRIVEN)

All thresholds are derived from historical data variability. This is documented in the code module header and in each check's output.

### Historical Data Used

| Metric | 2022 | 2023 | 2024 | Mean | Std | CV |
|--------|------|------|------|------|-----|-----|
| Annual Pumping (AF) | 975.47 | 866.48 | 1372.90 | 1071.62 | 266.95 | 24.9% |
| Depletion/Pumping Ratio | 0.0956 | 0.1083 | 0.0688 | 0.0909 | 0.020 | 22.0% |

### Year-over-Year Changes Observed

| Transition | Pumping Change | Ratio Change |
|------------|----------------|--------------|
| 2022 -> 2023 | -11.2% | +13.3% |
| 2023 -> 2024 | +58.5% | -36.5% |
| **Max Absolute** | **58.5%** | **36.5%** |

### Computed Thresholds

| Check | Threshold | Derivation Formula | Code Constant |
|-------|-----------|-------------------|---------------|
| YoY Pumping | **65%** | max_observed (58.5%) + 10% buffer | `PUMPING_CHANGE_THRESHOLD_PCT = 65.0` |
| YoY Ratio | **45%** | max_observed (36.5%) + 10% buffer | `RATIO_CHANGE_THRESHOLD_PCT = 45.0` |
| Seasonal r | **0.75** | Simulated month-shift produces r~0.5-0.7 | `SEASONAL_CORRELATION_THRESHOLD = 0.75` |
| Envelope buffer | **max(20%, 1.5*CV)** | Minimum 20% + scales with variability | `ENVELOPE_MIN_BUFFER = 0.20`, `ENVELOPE_CV_MULTIPLIER = 1.5` |

---

## Files Created/Modified

### Created

| File | Size | Description |
|------|------|-------------|
| `validation/temporal_consistency.py` | 785 lines | Main module with 4 temporal checks, CLI, full threshold documentation |

### Modified

| File | Changes |
|------|---------|
| `validation/historical/bounds.yaml` | Added `monthly_profile` section with mean normalized profile (JAN-DEC fractions) |
| `validation/historical/hashes.json` | Updated bounds.yaml hash: `27645f14c927ee3002c93e6cf329f27575a3ae4b2f29cf8d389d302240ff95f3` |

---

## Testing Results

### 2024 Validation (Exit Code 0 = PASS)

```
======================================================================
TEMPORAL CONSISTENCY CHECKS - Year 2024
======================================================================

PASSED CHECKS:
  [PASS] yoy_pumping_change
         PASS: Pumping changed +58.4% year-over-year (within +/-65.0% threshold)
         Derivation: Threshold: max_observed_change (58.5%) + 10% buffer = 65.0%. Prior year: 866.48 AF

  [PASS] yoy_ratio_change
         PASS: Ratio changed -36.5% year-over-year (within +/-45.0% threshold)
         Derivation: Threshold: max_observed_change (36.5%) + 10% buffer = 45.0%. Prior ratio: 0.1083, Current ratio: 0.0687

  [PASS] seasonal_pattern
         PASS: Monthly profile correlation r=0.888 >= 0.75 threshold
         Derivation: Threshold: r >= 0.75 (catches month-shifts producing r~0.5-0.7). Current peak: AUG (24.3%), Historical peak: AUG (19.1%)

  [PASS] envelope_annual_pumping_af
         PASS: Annual Pumping 1372.92 AF within envelope [602.52, 1791.14] AF
         Derivation: Method: Range envelope (not 95% PI - unsound with n=3). Buffer = max(20%, 1.5*CV) = max(20%, 30.5%) = 30.5%. Historical range: [866.48, 1372.90] AF

  [PASS] envelope_rio_pojoaque_nambe_depletion_af
         PASS: Rio Pojoaque/Nambe Depletion 60.80 AF within envelope [47.88, 72.96] AF
         Derivation: Method: Range envelope (not 95% PI - unsound with n=3). Buffer = max(20%, 1.5*CV) = max(20%, 1.0%) = 20.0%. Historical range: [59.84, 60.80] AF

  [PASS] envelope_rio_tesuque_depletion_af
         PASS: Rio Tesuque Depletion 33.58 AF within envelope [26.79, 40.30] AF
         Derivation: Method: Range envelope (not 95% PI - unsound with n=3). Buffer = max(20%, 1.5*CV) = max(20%, 0.2%) = 20.0%. Historical range: [33.49, 33.58] AF

======================================================================
SUMMARY: 6 passed, 0 flags
======================================================================
```

### Code Quality

```bash
$ ruff check validation/temporal_consistency.py
All checks passed!
```

---

## Module Structure

```
validation/temporal_consistency.py (785 lines)
  |
  |-- THRESHOLD DOCUMENTATION HEADER (lines 1-82)
  |     Explains derivation methodology for each threshold
  |
  |-- CONSTANTS (lines 95-107)
  |     PUMPING_CHANGE_THRESHOLD_PCT = 65.0
  |     RATIO_CHANGE_THRESHOLD_PCT = 45.0
  |     SEASONAL_CORRELATION_THRESHOLD = 0.75
  |     ENVELOPE_MIN_BUFFER = 0.20
  |     ENVELOPE_CV_MULTIPLIER = 1.5
  |
  |-- DATA LOADING
  |     load_bounds() - Load bounds.yaml
  |     load_current_year_pumping() - Load Table 2 output
  |     load_current_year_depletions() - Load Table 3 output
  |
  |-- CHECK IMPLEMENTATIONS
  |     check_year_over_year_pumping() - YoY pumping change check
  |     check_year_over_year_ratio() - YoY depletion/pumping ratio check
  |     check_seasonal_pattern() - Pearson correlation check
  |     check_envelope_bounds() - CV-adjusted range envelope check
  |
  |-- ORCHESTRATOR
  |     run_all_temporal_checks() - Run all checks, return results
  |
  |-- CLI
  |     main() - Command-line entry point
```

---

## Relevant Code Sections

### Threshold Documentation
`validation/temporal_consistency.py:1-82` - Full derivation documentation in module docstring

### Threshold Constants
`validation/temporal_consistency.py:95-107` - All configurable thresholds with comments

### Check Implementations
- **YoY Pumping**: `validation/temporal_consistency.py:265-325`
- **YoY Ratio**: `validation/temporal_consistency.py:328-395`
- **Seasonal Pattern**: `validation/temporal_consistency.py:398-470`
- **Envelope Bounds**: `validation/temporal_consistency.py:473-545`

### Monthly Profile (bounds.yaml)
`validation/historical/bounds.yaml:185-207` - Added monthly_profile section

---

## CLI Usage

```bash
# Run temporal consistency checks for a specific year
python validation/temporal_consistency.py --year 2025

# Exit codes:
#   0 = All checks passed
#   1 = Soft flags raised (human review recommended)
```

---

## Integration with Layer 6 (Provenance)

Results integrate with the provenance manifest via `run_all_temporal_checks()`:

```python
from validation.temporal_consistency import run_all_temporal_checks

# Returns list[CheckResult] with:
#   - name: check identifier
#   - passed: bool
#   - is_hard_fail: False (all Layer 2 checks are soft flags)
#   - message: human-readable result
#   - actual_value: measured value
#   - expected_range: threshold/envelope
#   - derivation: how threshold was computed
```

---

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| bounds.yaml has complete monthly_profile section | PASS |
| Module runs standalone: `python temporal_consistency.py --year 2024` | PASS |
| All threshold derivations documented in code comments | PASS |
| Flag messages include: flagged value, threshold, derivation method | PASS |
| Results can be aggregated into Layer 6 provenance manifest | PASS |
| All checks pass for 2024 (part of baseline) | PASS |
| ruff check passes | PASS |

---

## Notes

1. **2024 passes all checks** as expected, since it's part of the 2022-2024 baseline used to compute thresholds.

2. **Future years** will flag if values exceed the observed historical variability + 10% buffer.

3. **Seasonal correlation** for 2024 is r=0.888, well above the 0.75 threshold. A stress period misalignment (months shifted by 1) would produce r~0.5-0.7.

4. **Monthly profile computed from Table_2_historical.xlsx**: Peak pumping is in August (19.1% of annual), minimum in January (0.55%) and November (0.67%).
