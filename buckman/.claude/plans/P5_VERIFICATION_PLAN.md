# P5: Layer 2 — Temporal Consistency and Stationarity Checks

**Status**: PLANNED (awaiting approval)

## Overview

Implement `validation/temporal_consistency.py` with three temporal validation checks that detect:
1. Year-over-year anomalies in pumping and depletion/pumping ratios
2. Seasonal pattern misalignment (e.g., stress periods shifted by one month)
3. Multi-year trend deviations (values outside 95% prediction interval)

All checks produce **FLAGS** (not hard fails) requiring human review.

---

## Prerequisite: Fix bounds.yaml (P2.5 Completion)

**Issue**: The P2.5 plan specified a `monthly_profile` section in bounds.yaml (lines 153-156) but it was not implemented.

**Fix Required**: Add the following section to `validation/historical/bounds.yaml`:

```yaml
# =============================================================================
# MONTHLY PROFILE (For P5 Seasonal Pattern Validation)
# =============================================================================
monthly_profile:
  description: "Normalized monthly pumping distribution (fraction of annual total)"
  correlation_threshold: 0.85  # Flag if r < 0.85

  # Mean monthly profile computed from 2022-2024 Table 2 data
  # Each value = average fraction of annual pumping in that month
  mean_profile:
    JAN: <computed>
    FEB: <computed>
    MAR: <computed>
    APR: <computed>
    MAY: <computed>
    JUN: <computed>
    JUL: <computed>
    AUG: <computed>
    SEP: <computed>
    OCT: <computed>
    NOV: <computed>
    DEC: <computed>
```

**Data Source**: Compute from `validation/historical/Table_2_historical.xlsx`:
1. For each year (2022, 2023, 2024), sum all wells per month
2. Normalize each year's monthly values (fraction of annual total)
3. Average the normalized profiles across years

---

## Step 0: Fix bounds.yaml

**Action**: Add `monthly_profile` section to bounds.yaml by:
1. Load Table_2_historical.xlsx
2. Compute mean monthly profile
3. Append to bounds.yaml
4. Update validation/historical/hashes.json

**Files Modified**:
- `validation/historical/bounds.yaml` (add ~25 lines)
- `validation/historical/hashes.json` (update hash)

---

## Check 1: Year-over-Year Rate of Change

**Objective**: Flag if annual pumping or depletion/pumping ratio changed dramatically from prior year.

### Thresholds (Configurable)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PUMPING_CHANGE_THRESHOLD_PCT` | 40% | Flag if annual pumping changed >40% from prior year |
| `RATIO_CHANGE_THRESHOLD_PCT` | 25% | Flag if depletion/pumping ratio shifted >25% year-over-year |

### Implementation

```python
def check_year_over_year_change(
    current_year: int,
    current_pumping_af: float,
    current_depletions: dict[str, float],
    bounds: dict,
    pumping_threshold_pct: float = 40.0,
    ratio_threshold_pct: float = 25.0,
) -> list[CheckResult]:
```

**Logic:**
1. Get prior year pumping from bounds.yaml -> time_series -> annual_pumping_af
2. Compute percent change: `(current - prior) / prior * 100`
3. Flag if `abs(pct_change) > pumping_threshold_pct`
4. Compute current depletion/pumping ratio
5. Compare to prior year ratio from bounds.yaml -> derived_ratios
6. Flag if ratio shift > ratio_threshold_pct

**Output Format:**
```
SOFT FLAG: Pumping changed +58.5% year-over-year (866.48 AF -> 1372.90 AF).
           Threshold: +/-40%. May indicate operational change.
```

---

## Check 2: Seasonal Pattern Validation

**Objective**: Detect if monthly pumping profile is misaligned (e.g., stress periods shifted by one month).

### Threshold (Configurable)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SEASONAL_CORRELATION_THRESHOLD` | 0.85 | Flag if Pearson r < 0.85 |

### Implementation

```python
def check_seasonal_pattern(
    current_year: int,
    monthly_pumping: dict[str, float],  # {JAN: 100.0, FEB: 120.0, ...}
    bounds: dict,
    correlation_threshold: float = 0.85,
) -> CheckResult:
```

**Logic:**
1. Load mean monthly profile from bounds.yaml -> monthly_profile -> mean_profile
2. Normalize current year profile (fraction of annual total per month)
3. Compute Pearson correlation between current and mean profile
4. Flag if r < 0.85

**Output Format:**
```
SOFT FLAG: Monthly profile correlation r=0.72 < 0.85 threshold.
           Possible stress period misalignment (check month ordering).
           Current peak: JUL (18.2%). Historical peak: JUN (17.8%).
```

---

## Check 3: Multi-Year Trend Check

**Objective**: Flag if current year falls outside the 95% prediction interval based on 2022-2024 trend.

### Implementation

```python
def check_multi_year_trend(
    current_year: int,
    current_values: dict[str, float],
    bounds: dict,
    confidence_level: float = 0.95,
) -> list[CheckResult]:
```

**Logic:**
1. For each metric in time_series (pumping, each depletion):
2. Fit linear regression: `y = mx + b` where x = [2022, 2023, 2024]
3. Compute 95% prediction interval at x = current_year
4. Flag if current value falls outside the interval

**Statistical Details:**
- Use scipy.stats.linregress for slope, intercept
- Prediction interval: `y_hat +/- t_{0.975, n-2} * s * sqrt(1 + 1/n + (x - x_mean)^2 / SS_x)`
- With only 3 points, intervals will be wide (expected)

**Output Format:**
```
SOFT FLAG: Annual pumping 1500.00 AF outside 95% PI [780.2, 1420.5].
           Based on 2022-2024 trend: +133.9 AF/year.
```

---

## Module Structure

```
validation/
  temporal_consistency.py (~300 lines)
    - CONSTANTS (configurable thresholds at module top)
        PUMPING_CHANGE_THRESHOLD_PCT = 40.0
        RATIO_CHANGE_THRESHOLD_PCT = 25.0
        SEASONAL_CORRELATION_THRESHOLD = 0.85
        TREND_CONFIDENCE_LEVEL = 0.95

    - load_bounds(bounds_path) -> dict
    - load_current_year_data(year, outputs_dir) -> dict

    - check_year_over_year_change(...) -> list[CheckResult]
    - check_seasonal_pattern(...) -> CheckResult
    - check_multi_year_trend(...) -> list[CheckResult]

    - run_all_temporal_checks(year, outputs_dir) -> list[CheckResult]
    - main() -> CLI entry point
```

---

## Integration: Layer 6 Flag Register

All flags wire into the provenance manifest:

```python
from validation.ballpark_check import CheckResult

def run_all_temporal_checks(year: int, outputs_dir: Path) -> list[CheckResult]:
    """Run all Layer 2 temporal consistency checks."""
    results = []
    results.extend(check_year_over_year_change(...))
    results.append(check_seasonal_pattern(...))
    results.extend(check_multi_year_trend(...))
    return results
```

---

## File Paths

### Input Files (Read-Only)

| File | Purpose |
|------|---------|
| `validation/historical/bounds.yaml` | Time series, monthly profile, derived ratios |
| `validation/historical/Table_2_historical.xlsx` | Monthly pumping (for Step 0) |
| `output/ingested_data/{year}_Table_2_output.csv` | Current year monthly pumping |
| `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx` | Current year depletions |

### Files Created/Modified

| File | Action |
|------|--------|
| `validation/historical/bounds.yaml` | Add monthly_profile section |
| `validation/historical/hashes.json` | Update bounds.yaml hash |
| `validation/temporal_consistency.py` | Create (~300 lines) |

---

## Implementation Steps

1. **Step 0: Fix bounds.yaml**
   - Load Table_2_historical.xlsx
   - Compute mean monthly profile (normalized fractions)
   - Append monthly_profile section to bounds.yaml
   - Update hashes.json

2. **Create module skeleton** with imports and constants

3. **Implement check_year_over_year_change()** for pumping and ratio checks

4. **Implement check_seasonal_pattern()** with Pearson correlation

5. **Implement check_multi_year_trend()** with linear regression and prediction interval

6. **Implement run_all_temporal_checks()** orchestrator

7. **Add CLI entry point** (`python validation/temporal_consistency.py --year 2024`)

8. **Test against 2024 data** to verify flags are raised appropriately

---

## Tolerances & Acceptance Criteria

| Check | Threshold | Flag Condition |
|-------|-----------|----------------|
| Year-over-year pumping | 40% | `abs((current - prior) / prior) > 0.40` |
| Year-over-year ratio | 25% | `abs((current_ratio - prior_ratio) / prior_ratio) > 0.25` |
| Seasonal correlation | r = 0.85 | `pearson_r < 0.85` |
| Multi-year trend | 95% PI | `value < lower_bound OR value > upper_bound` |

---

## Expected Flags for 2024 (Based on Historical Data)

Given historical data:
- Pumping 2023->2024: +58.5% change (866.48 -> 1372.90)
- Ratio 2023->2024: -36.5% shift (0.1083 -> 0.0688)

**Expected flags:**
1. **YES**: Pumping change exceeds 40% threshold
2. **YES**: Ratio shift exceeds 25% threshold
3. **Seasonal**: TBD after profile computed
4. **Trend**: Pumping 1372.90 AF likely outside PI (high variance in 3-point regression)

---

## Success Criteria

1. bounds.yaml has complete monthly_profile section
2. Module runs standalone: `python validation/temporal_consistency.py --year 2024`
3. Returns structured `CheckResult` list
4. All three check types implemented
5. Thresholds are configurable (named constants at module top)
6. Flag messages include: flagged value, threshold, plain-English explanation
7. Results can be aggregated into Layer 6 provenance manifest

---

## Uncertainties / Decisions Made

1. **Monthly profile missing**: Fixed as Step 0 (compute from Table_2_historical.xlsx)
2. **Depletion/pumping ratio definition**: Using (Rio Pojoaque + Rio Tesuque) / Total Pumping to match bounds.yaml -> derived_ratios
3. **Trend regression with 3 points**: Intervals will be wide; documented in flag messages
4. **All flags are SOFT FLAGS**: `is_hard_fail=False` for all checks

---

## Dependencies

- `pandas` (data loading)
- `numpy` (calculations)
- `scipy.stats` (linregress, pearsonr, t-distribution)
- `PyYAML` (bounds.yaml loading)
- `openpyxl` (Excel file reading)

---

## P4 Impact Assessment

**P4 does NOT need updating.** The P4 manifest plan references bounds.yaml only for hash verification. Adding the monthly_profile section will:
- Change the hash in hashes.json (expected)
- Not break any P4 functionality
