# IS-11: Validation Framework (Layers 2-5)

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement the validation framework covering Layer 2 (temporal consistency), Layer 4 (ballpark/perturbation checks), Layer 5 (2024 regression harness), and the `run_all_tests.py` orchestrator that coordinates all layers.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project scaffold (directory structure, constants)
- IS-09: Tables 4 & 5 generation (provides depletion data for validation)
- IS-10: Test suite Layers 0-1 (provides pytest infrastructure)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| bounds.yaml | `validation/historical/bounds.yaml` | Historical bounds for 2022-2024 |
| tolerances.yaml | `validation/2024/tolerances.yaml` | Per-table tolerance definitions |
| Frozen 2024 inputs | `validation/2024/inputs/` | Regression test input files |
| Expected 2024 outputs | `validation/2024/expected_outputs/` | Regression test expected outputs |
| hashes.json | `validation/2024/inputs/hashes.json` | SHA-256 hashes of frozen inputs |

### Domain Knowledge
- See DS-02 for unit definitions and conversion factors
- See DS-05 for historical data ranges (2022-2024 pumping and depletions)

---

## 3. Context for Claude Code

The validation framework provides multi-layer defense against errors in the compliance-critical pipeline:

**Layer 2 (Temporal Consistency):** Year-over-year checks that flag statistical anomalies. All checks produce soft flags requiring human review -- not hard failures. Thresholds are data-driven from 3 years of baseline (2022-2024).

**Layer 4 (Ballpark Check):** Fast (<5 second) sanity check against historical bounds. Hard fails on physics violations (negative values, non-monotonic depletions). Soft flags on statistical outliers (>2 sigma from mean).

**Layer 5 (2024 Regression):** Frozen-input regression test. Runs pipeline on known-good 2024 data and compares cell-by-cell against expected outputs. Highest-value test -- catches any code change that alters compliance numbers.

**run_all_tests.py:** Master orchestrator that runs all layers in priority order, collects results into structured dataclasses, generates JSON reports, and produces a provenance manifest.

### Key Equations (Inline)

```
Envelope bounds:  buffer = max(20%, 1.5 * CV)
                  lower = min(historical) * (1 - buffer)
                  upper = max(historical) * (1 + buffer)

Hybrid tolerance:  PASS if |actual - expected| <= absolute_tolerance
                   OR    if |actual - expected| / |expected| <= relative_tolerance

Pearson correlation:  r = cov(current_profile, historical_mean) / (std_c * std_h)
                     Low r (< 0.75) indicates possible stress period misalignment
```

### Key Constants (Inline)

| Constant | Value | Source |
|----------|-------|--------|
| PUMPING_CHANGE_THRESHOLD_PCT | 65.0% | max observed (58.5%) + 10% buffer |
| RATIO_CHANGE_THRESHOLD_PCT | 45.0% | max observed (36.5%) + 10% buffer |
| SEASONAL_CORRELATION_THRESHOLD | 0.75 | month-shift detection simulation |
| ENVELOPE_MIN_BUFFER | 0.20 | measurement uncertainty floor |
| ENVELOPE_CV_MULTIPLIER | 1.5 | scales with observed variability |
| Table 3 absolute tolerance | 0.001 AF | 3-decimal place precision |
| Table 4 absolute tolerance | 0.1 AF | FLAG: may need adjustment |
| Table 5 absolute tolerance | 0.01 AF | 2-decimal place precision |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `validation/ballpark_check.py` -- fast sanity check | Loads bounds.yaml, checks pumping within soft_max/hard_max, checks per-well bounds, checks depletion monotonicity. Exit codes: 0=pass, 2=soft flags, 3=hard fail, 4=skip. Completes in < 5 seconds. |
| R2 | `validation/temporal_consistency.py` -- year-over-year checks | Checks: YoY pumping change rate (65% threshold), YoY depletion/pumping ratio change (45%), seasonal correlation (r >= 0.75), envelope bounds (CV-adjusted). All soft flags. Exit codes: 0=pass, 1=flags. |
| R3 | `validation/2024/run_regression_2024.py` -- frozen 2024 regression | Step 1: verify input SHA-256 hashes. Step 2: run pipeline on frozen inputs. Step 3: compare all 5 tables cell-by-cell with hybrid tolerance. Reports pass/fail with cell-level detail. Exit codes: 0=pass, 1=fail. |
| R4 | `validation/2024/tolerances.yaml` format | Per-table entries with `tolerance_type: hybrid`, `absolute_tolerance`, `relative_tolerance`. Global: `nan_handling: fail`, `empty_cell_handling: match`. |
| R5 | `validation/historical/bounds.yaml` format | Sections: `table1_annual_pumping` (total + per-well bounds), `table3_stream_depletions` (per-stream bounds), `time_series` (raw values for regression), `monthly_profile` (12-month normalized distribution), `thresholds` (sigma multipliers, monotonic tolerance). |
| R6 | `run_all_tests.py` orchestration | Dataclasses: `TestResult`, `Flag`, `TestSuite`. Runs: ballpark check -> Layer 0 pytest -> Layer 0.5 pytest -> Layer 1 pytest -> temporal consistency -> manifest generation. JSON report parsing. Summary output. Exit codes: 0=pass, 1=hard fail, 3=physics violation. |

---

## 5. Worked Example

### R1: ballpark_check -- pumping bounds

#### Input
```yaml
# From bounds.yaml:
table1_annual_pumping:
  total_annual:
    min: 866.48
    max: 1372.90
    mean: 1071.62
    std: 266.95
    soft_max: 2745.80   # 2x max
    hard_max: 4118.70   # 3x max
thresholds:
  soft_flag_sigma: 2.0
```

#### Calculation Steps
```
Step 1: Load 2024 total pumping from Table 1 -> 1372.90 AF

Step 2: Check negative: 1372.90 >= 0 -> PASS

Step 3: Check hard_max: 1372.90 <= 4118.70 -> PASS

Step 4: Check soft_max: 1372.90 <= 2745.80 -> PASS

Step 5: Check 2-sigma range:
        upper = 1071.62 + 2.0 * 266.95 = 1605.52
        lower = 1071.62 - 2.0 * 266.95 = 537.72
        1372.90 in [537.72, 1605.52] -> PASS

Result: Exit code 0 (all checks passed)
```

### R2: temporal_consistency -- seasonal pattern

#### Input
```python
# Current year monthly pumping (AF): JAN=7.5, FEB=73.0, MAR=83.4, ...
# Historical mean profile from bounds.yaml: JAN=0.5%, FEB=5.3%, ...
```

#### Calculation Steps
```
Step 1: Normalize current year to fractions
        total = sum(monthly) = 1372.90 AF
        JAN_frac = 7.5 / 1372.90 = 0.0055
        FEB_frac = 73.0 / 1372.90 = 0.0532
        ...

Step 2: Compute Pearson correlation with historical mean profile
        r = pearsonr(current_fractions, mean_profile)

Step 3: Compare to threshold
        If r >= 0.75 -> PASS (monthly pattern consistent)
        If r < 0.75 -> FLAG (possible stress period misalignment)
```

### R3: run_regression_2024 -- hybrid tolerance

#### Input
```yaml
# From tolerances.yaml:
Table_3:
  absolute_tolerance: 0.001   # 3-decimal AF
  relative_tolerance: 0.001   # 0.1%
```

#### Calculation Steps
```
Step 1: Load expected Table 3, row for 2024
        Expected: Pojoaque total = 60.797 AF

Step 2: Load actual Table 3 from pipeline output
        Actual: Pojoaque total = 60.796 AF

Step 3: Hybrid tolerance check
        |60.796 - 60.797| = 0.001
        Absolute: 0.001 <= 0.001 -> PASS
        (Would also check relative: 0.001 / 60.797 = 0.0000164 <= 0.001 -> PASS)

Step 4: Either condition PASS -> cell PASSES
```

### R6: run_all_tests.py -- orchestration flow

#### Execution Order
```
1. Validate year parameter (MIN=2022, MAX=2100)
2. Ballpark check (exit 3 -> abort immediately)
3. Layer 0 pytest -m layer0 (JSON report)
4. Layer 0.5 pytest -m edge_cases (JSON report)
5. Layer 1 pytest -m conservation (JSON report, skip if no outputs)
6. Temporal consistency (collect flags)
7. Generate provenance manifest (Layer 6)
8. Print summary, return exit code
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create/Modify | `validation/ballpark_check.py` | Fast sanity check against historical bounds |
| Create/Modify | `validation/temporal_consistency.py` | Year-over-year temporal consistency flags |
| Create/Modify | `validation/2024/run_regression_2024.py` | Frozen 2024 regression harness |
| Create/Modify | `validation/2024/tolerances.yaml` | Per-table hybrid tolerance definitions |
| Create/Modify | `validation/historical/bounds.yaml` | Historical bounds and time series data |
| Create/Modify | `run_all_tests.py` | Master test orchestrator |

---

## 7. Acceptance Criteria

```bash
# Ballpark check (requires validation outputs):
python validation/ballpark_check.py --year 2024
# Expected: Exit code 0 or 4 (pass or skip)

# Temporal consistency (requires pipeline outputs):
python validation/temporal_consistency.py --year 2024
# Expected: Exit code 0 (no flags for baseline year)

# Full test orchestrator:
python run_all_tests.py --year 2024 --dry-run
# Expected: Prints execution plan without running

# Full run (requires pipeline completion):
python run_all_tests.py --year 2024
# Expected: Exit code 0, manifest generated in output/manifests/
```

---

## 8. Known Gotchas

- [ ] **Ballpark exit code 1 is reserved for Python crashes**, not intentional failures. Intentional failures use 2 (soft) or 3 (hard). The orchestrator must distinguish crash (code 1) from expected exit codes (0, 2, 3, 4).
- [ ] **Temporal consistency thresholds are derived from only 3 data points (2022-2024).** Traditional 95% prediction intervals require t-distribution with df=1, yielding useless bounds. The CV-adjusted envelope method is explicitly documented as "honest about n=3 limitations."
- [ ] **The regression harness runs the FULL pipeline** including MODFLOW96 via Wine. It takes 30-45 minutes. It should NOT be included in `run_all_tests.py` default execution -- only via `--include-regression` flag or standalone.
- [ ] **bounds.yaml monthly_profile values must sum to 1.0.** A profile that sums to 0.98 or 1.02 will produce incorrect correlation calculations. Validate on load.
- [ ] **tolerances.yaml hybrid tolerance uses OR logic**, not AND. A cell passes if EITHER the absolute OR relative tolerance is met. This handles both near-zero values (where relative tolerance is meaningless) and large values (where absolute tolerance is too tight).
- [ ] **pytest-json-report plugin is required** for `run_all_tests.py` JSON report parsing. Install via `pip install pytest-json-report`. The orchestrator falls back to exit-code-only parsing if the plugin is missing.
- [ ] **TestResult.passed can be -1** (unknown count) when JSON report generation fails. Handle this in summary calculations.
- [ ] **Layer 3 (cross-comparison) was scientifically rejected** in the P6 review and is explicitly skipped with a log message.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N Validation | Notes |
|-------------|------------------------------|-------|
| Historical bounds | bounds.yaml (2022-2024 baseline) | Static file, updated annually |
| Temporal consistency | bounds.yaml time_series + Table 2 output | Compares against all historical years |
| Regression baseline | validation/2024/ frozen inputs/outputs | Never changes (2024 locked) |
| Run-time validation | Current pipeline outputs | Checked against bounds.yaml |

---

## 10. Verification

```bash
# Quick verification (no pipeline dependency):
python run_all_tests.py --year 2024 --dry-run

# Full verification:
python run_all_tests.py --year 2024 -v
```

Expected result for `--dry-run`:
```
DRY RUN: Would execute for year 2024
  1. Ballpark check: validation/ballpark_check.py
  2. Layer 0 (smoke): pytest -m layer0
  3. Layer 0.5 (edge): pytest -m edge_cases
  4. Layer 1 (conservation): pytest -m conservation
  5. Layer 2 (temporal): validation/temporal_consistency.py
  6. Layer 6 (manifest): src/pipeline_manifest.py
```

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-05 | Historical data ranges used in bounds.yaml |
| IS-09 | Tables 4 & 5 outputs validated by ballpark check |
| IS-10 | Layer 0-1 tests invoked by run_all_tests.py orchestrator |
| IS-12 | Provenance manifest generated as Layer 6 of orchestration |

---

## Appendix A: bounds.yaml Structure

```yaml
metadata:
  generated: "2026-02-17"
  years_included: [2022, 2023, 2024]
  units: "acre-feet (AF)"

table1_annual_pumping:
  total_annual:
    min: 866.48       # Historical minimum
    max: 1372.90      # Historical maximum
    mean: 1071.62     # Historical mean
    std: 266.95       # Standard deviation
    soft_max: 2745.80 # 2x max (soft flag)
    hard_max: 4118.70 # 3x max (hard fail)
  wells:
    Well_B1: {min: 224.06, max: 601.27, mean: 427.82}
    # ... 12 more wells

table3_stream_depletions:
  rio_pojoaque_nambe: {min: 59.844, max: 60.797, mean: 60.321, std: 0.477}
  rio_tesuque: {min: 33.490, max: 33.583, mean: 33.521, std: 0.053}

time_series:
  years: [2022, 2023, 2024]
  annual_pumping_af: {values: [975.47, 866.48, 1372.90]}
  rio_pojoaque_nambe_depletion_af: {values: [59.844, 60.323, 60.797]}
  rio_tesuque_depletion_af: {values: [33.490, 33.491, 33.583]}
  la_cienega_depletion_af: {values: [3.37, 3.54, 3.74]}

monthly_profile:
  mean_profile:
    JAN: 0.005463
    FEB: 0.053194
    # ... 10 more months (sum = 1.0)

thresholds:
  soft_flag_sigma: 2.0
  monotonic_tolerance_af: 0.01
```

## Appendix B: tolerances.yaml Structure

```yaml
tables:
  Table_1:
    description: "Annual pumping by well (acre-feet/year)"
    tolerance_type: hybrid
    absolute_tolerance: 0.01
    relative_tolerance: 0.001

  Table_3:
    absolute_tolerance: 0.001   # Strict: 3-decimal AF
    relative_tolerance: 0.001

  Table_5:
    absolute_tolerance: 0.01
    relative_tolerance: 0.005
    max_year: 2024  # Only compare through 2024

global:
  nan_handling: "fail"
  empty_cell_handling: "match"
```

## Appendix C: run_all_tests.py Dataclasses

```python
@dataclass
class TestResult:
    layer: str           # "Layer 0", "Layer 1", etc.
    name: str            # "smoke_tests", "conservation"
    passed: int
    failed: int
    skipped: int
    duration_sec: float
    hard_fail: bool
    error_message: str | None = None
    failed_tests: list[str] = field(default_factory=list)

@dataclass
class Flag:
    layer: str
    test_name: str
    value: float
    threshold: float
    message: str
    requires_review: bool = True

@dataclass
class TestSuite:
    year: int
    results: list[TestResult]
    flags: list[Flag]
    manifest_path: Path | None
    start_time: datetime
    end_time: datetime | None
    exit_code: int
    error_messages: list[str] = field(default_factory=list)
```
