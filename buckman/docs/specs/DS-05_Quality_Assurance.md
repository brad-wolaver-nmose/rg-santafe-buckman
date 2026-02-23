# DS-05: Quality Assurance Framework

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Final
**Author:** Claude Code (Anthropic) + Brad Wolaver (NMOSE)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Purpose & Scope

The QA framework ensures the Buckman pipeline produces court-defensible, scientifically reproducible results through a 7-layer verification hierarchy. Each layer catches progressively subtler errors -- from outright pipeline crashes (Layer 0) through physics violations (Layer 1), statistical anomalies (Layer 2), known-good regression (Layer 5), and cryptographic chain-of-custody (Layer 6). The framework is designed around the principle that **the test harness is the product**: the pipeline produces answers; the harness produces confidence. A total of approximately 241 tests across 7 test files and standalone validation scripts enforce this hierarchy.

---

## 2. Scientific Basis

### 2.1 Testing Philosophy

Groundwater model outputs cannot be validated in the traditional sense because the true state of the aquifer is never fully known. Instead, the framework applies multiple independent lines of evidence:

1. **Internal consistency** -- Do outputs obey conservation of mass and known physical constraints?
2. **Historical plausibility** -- Are outputs within the envelope of prior observations?
3. **Reproducibility** -- Can the pipeline reproduce known-good results from frozen inputs?
4. **Provenance** -- Can every output be traced to specific inputs, code versions, and test results?

This multi-layered approach mirrors USGS guidance on model validation (Anderson & Woessner, 2015) and reflects legal standards for admissibility of scientific evidence (Daubert v. Merrell Dow Pharmaceuticals, 1993).

### 2.2 The 7-Layer Verification Hierarchy

| Layer | Name | What It Catches | Hard-fail? |
|-------|------|----------------|------------|
| 0 | Smoke Tests | Import errors, missing files, NaN/null outputs, pipeline crashes | Yes |
| 0.5 | Edge Cases | Boundary conditions, zero pumping wells, leap years, single-day months | Yes |
| 1 | Conservation | Mass balance violations, unit conversion errors, dropped records | Yes |
| 2 | Temporal Consistency | Year-over-year anomalies, stress period misalignment, chaining errors | Flag |
| 3 | Cross-Comparison | Systematic errors invisible to internal checks | Skipped (no external data source) |
| 4 | Perturbation Testing | Fragility -- disproportionate output changes from small input changes | Planned (not yet implemented) |
| 5 | Regression (2024 Baseline) | Pipeline drift -- code changes that subtly alter results | Flag |
| 6 | Provenance | Missing audit trail, hash mismatches, unreproducible runs | Flag |

### 2.3 Hard-Fail vs. Soft-Flag Policy

The framework distinguishes between conditions that invalidate outputs and conditions that require expert judgment:

| Category | Trigger | Exit Code | Response |
|----------|---------|-----------|----------|
| **Hard fail** | Physics violation (NaN, negative depletion, non-conservation) | 1 | Pipeline halts. Outputs must not be used. |
| **Soft flag** | Statistical outlier (>2 sigma from historical mean) | 2 | Pipeline continues. Analyst review required before submission. |
| **Ballpark critical** | Gross physics violation (non-monotonic cumulative depletion) | 3 | Immediate halt. Fundamental model error suspected. |
| **Pass** | All checks within bounds | 0 | Outputs cleared for use. |
| **Skip** | No validation baseline for this year | 4 | Ballpark check not applicable (normal for new years). |

**Regulatory rationale:** Layers 0--1 are hard failures because they detect physically impossible outputs that would be indefensible in court. Layers 2--6 produce flags because they detect conditions that may be unusual but valid -- regulatory requirements mandate human disposition before submission. An analyst must review each flag, document their judgment (e.g., "real operational change" vs. "data quality issue"), and sign off with initials and date.

### 2.4 Tolerance Model

The regression testing framework (Layer 5) uses a **hybrid tolerance model** that accommodates both small and large values:

```
PASS if |actual - expected| <= absolute_tolerance
  OR if |actual - expected| / |expected| <= relative_tolerance

Where both criteria are checked; passing EITHER one is sufficient.
```

**Rationale:** Pure absolute tolerance fails for large values (0.01 AF tolerance is meaningless for an 800 AF depletion). Pure relative tolerance fails for near-zero values (0.1% of 0.01 AF is 0.00001 AF, which is below floating-point noise). The hybrid approach handles both regimes.

**Per-table tolerance definitions** (from `validation/2024/tolerances.yaml`):

| Table | Description | Abs. Tolerance | Rel. Tolerance | Precision Basis |
|-------|------------|---------------|---------------|----------------|
| Table 1 | Annual pumping by well (AF/yr) | 0.01 AF | 0.001 (0.1%) | 2 decimal places in report |
| Table 2 | Monthly pumping by well (AF/mo) | 0.01 AF | 0.001 (0.1%) | 2 decimal places in report |
| Table 3 | Stream depletions (cumulative AF) | 0.001 AF | 0.001 (0.1%) | 3 decimal places in report |
| Table 4 | Rio Grande above/below Otowi (AF) | 0.1 AF | 0.01 (1%) | Larger tolerance; may need adjustment |
| Table 5 | La Cienega cumulative (AF) | 0.01 AF | 0.005 (0.5%) | 2 decimal places; only through 2024 |

**Global policies** (from `tolerances.yaml`):
- `nan_handling: "fail"` -- Any NaN value is an immediate hard failure
- `empty_cell_handling: "match"` -- Empty cells must match exactly between actual and expected

### 2.5 Worked Example: Tolerance Check

**Table 3, Rio Pojoaque Total Impact, 2024:**

```
Expected value:  60.797 AF
Actual value:    60.798 AF
Difference:      0.001 AF

Table 3 tolerances:
  Absolute: 0.001 AF
  Relative: 0.001 (0.1%)

Check 1 (absolute): |60.798 - 60.797| = 0.001 <= 0.001  --> PASS
Check 2 (relative): 0.001 / 60.797 = 0.0000164 <= 0.001 --> PASS

Result: PASS (satisfies both criteria)
```

**Edge case: near-zero value (Well B5, annual pumping = 0.00 AF):**

```
Expected: 0.00 AF
Actual:   0.001 AF
Difference: 0.001 AF

Table 1 tolerances:
  Absolute: 0.01 AF
  Relative: 0.001 (0.1%)

Check 1 (absolute): 0.001 <= 0.01            --> PASS
Check 2 (relative): 0.001 / 0.00 = undefined --> N/A (division by zero)

Result: PASS (absolute criterion sufficient)
```

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | 2024 validation data is the authoritative ground truth | Independently produced by prior (non-automated) workflow and verified by domain expert | Regression tests pass despite pipeline errors | Cross-check against prior-year PDF reports (2022, 2023) |
| 2 | Historical bounds (2022-2024) are representative of future operations | 3-year window captures recent operational patterns | Bounds too tight for changing conditions | Soft flags (not hard fails) for statistical outliers; bounds updated annually |
| 3 | Cumulative depletions are physically monotonic | Groundwater depletion effects propagate outward and do not reverse under continued pumping | Flags valid aquifer recovery as an error | Monotonic tolerance of 0.01 AF allows for floating-point noise |
| 4 | MODFLOW mass-balance discrepancy < 0.1% indicates valid simulation | Standard USGS practice for MODFLOW model acceptance | Convergence errors masked by compensating budget terms | Layer 1 tests parse individual budget components, not just totals |
| 5 | NaN/Inf values are always errors, never valid data | Physical quantities are always finite and defined | None identified | Hard fail on any NaN/Inf in output tables |
| 6 | Layer 3 (cross-comparison) is not applicable to this pipeline | Rejected during P6 development: no independent external data source available | Systematic errors undetected by internal checks | Layers 1, 2, and 5 provide overlapping coverage |
| 7 | The hybrid tolerance model is appropriate for all tables | Both absolute and relative error matter depending on value magnitude | Tolerance too loose for some cells, too tight for others | Per-table tolerance tuning with domain expert review |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| validation/historical/bounds.yaml | Physical bounds from 2022-2024 data (2 sigma/3 sigma thresholds) | YAML file, version-controlled | When new baseline years are added | Manual extraction from historical tables, documented in extraction_log.md |
| validation/2024/tolerances.yaml | Tolerance definitions for regression testing (hybrid model) | YAML file, version-controlled | When tolerance policy changes | Reviewed by domain expert |
| validation/2024/expected_outputs/ | Frozen 2024 expected output tables (Tables 1-5) | Excel files, version-controlled | Never (frozen baseline) | SHA-256 hash verification before each regression run |
| validation/2024/inputs/ | Frozen 2024 input files (pumping CSV, MODFLOW templates) | CSV/Excel files, version-controlled | Never (frozen baseline) | SHA-256 hash verification |
| output/test_results/*.json | JSON test reports from pytest-json-report | Generated by run_all_tests.py | Each pipeline run | Automated parsing of pass/fail counts |
| archive/ralph/ | Historical Ralph test automation logs and state snapshots (v0-v6) | Archived from ralph/ | Never (historical) | Preserved for audit trail; active ralph logs remain in ralph/ |
| output/manifests/buckman_manifest_{year}.json | Provenance manifest (Layer 6) | Generated by pipeline_manifest.py | Each pipeline run | SHA-256 hashes of all inputs and outputs |

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| soft_flag_sigma | 2.0 | sigma | Flag if > 2 standard deviations from historical mean | Statistical convention (95.4% coverage) |
| hard_fail_sigma | 3.0 | sigma | Fail if > 3 standard deviations from historical mean | Statistical convention (99.7% coverage) |
| monotonic_tolerance_af | 0.01 | AF | Floating-point noise floor for cumulative values | Empirical (observed rounding in MODFLOW output) |
| min_pumping_af | 0.0 | AF | Cannot extract negative water | Physics |
| max_pumping_af | 5,000 | AF | Engineering limit (all 13 wells at full capacity) | Operational knowledge |
| modflow_budget_tolerance | 0.1 | % | Maximum volumetric budget discrepancy | USGS MODFLOW convention |

### Ballpark Threshold Derivation

The ballpark check uses two tiers derived from the 2022-2024 historical total annual pumping:

```
Historical total annual pumping:
  2022: 975.47 AF
  2023: 866.48 AF
  2024: 1,372.90 AF
  Mean: 1,071.62 AF
  Std:  266.95 AF
  Max:  1,372.90 AF

Soft flag threshold: 2x historical max = 2,745.80 AF
Hard fail threshold: 3x historical max = 4,118.70 AF
Hard minimum:        0.0 AF (physics floor)
```

### Dimensional Analysis

All tolerance comparisons operate on values in acre-feet. No unit conversion is required within the tolerance check itself because all output tables report in AF. The tolerance values themselves have units of AF (absolute) or dimensionless ratios (relative).

---

## 6. Domain-Specific Constraints

### 6.1 Layer 0: Smoke Tests

**Purpose:** Verify the pipeline does not crash and produces structurally valid output.

**What it catches:** Missing files, NaN/null values, wrong column counts, empty tables, pipeline crashes.

**Tests include:**
- All 5 output Excel files created and non-empty
- No NaN, Inf, or null values in any output cell
- Expected columns/rows present in each table
- MODFLOW96 listing file contains "NORMAL TERMINATION"
- Post-processor output file exists and has expected structure

**Policy:** Hard fail (exit code 1). If smoke tests fail, no subsequent layers run.

### 6.2 Layer 0.5: Edge Cases

**Purpose:** Verify boundary conditions and extreme inputs are handled correctly.

**What it catches:** Zero-pumping wells, first/last month of year, leap year edge cases, wells at grid boundaries.

**Tests include:**
- Well B5 (historically zero pumping) handled correctly
- February 29 in leap years produces correct conversion
- All 13 wells present in output regardless of pumping volume
- Single-day months and 31-day months handled identically

**Policy:** Hard fail (exit code 1). Edge case failures indicate logic errors.

### 6.3 Layer 1: Conservation and Mass-Balance Checks

**Purpose:** Verify that water is neither created nor destroyed at pipeline hand-off points.

**What it catches:** Physics violations -- sign errors, dropped records, unit conversion mistakes, stress period misalignment.

**Tests include:**
- **Volumetric budget closure:** MODFLOW listing file percent discrepancy < 0.1%
- **Pumping-in = pumping-used:** Sum of WEL file pumping matches Table 2 totals within tolerance
- **Depletion <= pumping:** For every stream reach, cumulative depletion does not exceed cumulative pumping
- **Table sum integrity:** Row/column sums in report tables match expected totals

**Prerequisites:** Requires MODFLOW outputs to exist (full pipeline must have been run).

**Policy:** Hard fail (exit code 1). Conservation violations indicate fundamental errors.

### 6.4 Layer 2: Temporal Consistency

**Purpose:** Flag values that are physically possible but historically implausible.

**What it catches:** Stress period misalignment (months shifted by one), data entry errors, unusual operational patterns.

**Tests include:**
- **Year-over-year rate of change:** Flag if annual pumping changes by more than threshold relative to prior year
- **Seasonal pattern validation:** Compare normalized monthly profile against historical mean; flag if Pearson correlation < 0.85
- **Multi-year trend continuity:** Current year within 95% prediction interval of historical linear regression

**Monthly Profile Validation:**

The historical mean monthly pumping profile (normalized fraction of annual total, from `bounds.yaml`):

| Month | Mean Fraction | Physical Interpretation |
|-------|--------------|------------------------|
| JAN | 0.005 (0.5%) | Winter minimum -- low municipal demand |
| FEB | 0.053 (5.3%) | Late winter |
| MAR | 0.061 (6.1%) | Early spring |
| APR | 0.041 (4.1%) | Spring |
| MAY | 0.120 (12.0%) | Summer ramp-up |
| JUN | 0.162 (16.2%) | Summer peak begins |
| JUL | 0.178 (17.8%) | Summer peak |
| AUG | 0.191 (19.1%) | Annual maximum -- peak irrigation + municipal |
| SEP | 0.079 (7.9%) | Fall decline |
| OCT | 0.059 (5.9%) | Autumn |
| NOV | 0.007 (0.7%) | Winter minimum |
| DEC | 0.044 (4.4%) | Winter |

A significantly different seasonal pattern (low Pearson r against this profile) likely indicates stress period misalignment -- the most insidious bug where values look reasonable individually but months are shifted.

**Policy:** Soft flag (exit code 2). Outputs may still be valid but require human review before submission.

### 6.5 Layer 3: Cross-Comparison

**Status:** Scientifically rejected during P6 development.

**Rationale:** No independent external data source is available for cross-comparison. Municipal demand records, USGS gage data, and SCADA logs were evaluated but found to be either unavailable or not comparable to MODFLOW depletion outputs at the required precision.

**Future:** If City of Santa Fe total water production data becomes available, this layer could compare Buckman pumping as a fraction of total production against historical ratios.

### 6.6 Layer 4: Perturbation Testing

**Status:** Planned but not yet implemented.

**Design:** Create controlled perturbations of current year's pumping data:
- Add +/-5% uniform noise to all pumping values
- Shift one well's data by one stress period (time offset)
- Zero out one well entirely
- Double one well's pumping for one month

Assert that output changes are proportional and physically reasonable. If zeroing out one minor well causes 40% change in depletion at a distant reach, something is wrong.

### 6.7 Layer 5: 2024 Regression Harness

**Purpose:** Verify the pipeline reproduces known-good results from frozen inputs. This is the single highest-value layer.

**What it catches:** Pipeline drift -- code changes that subtly alter results.

**Architecture:**
1. Verify SHA-256 hashes of all 2024 input files match stored values (via `validation/historical/hashes.json`)
2. Run full pipeline on frozen 2024 inputs
3. Compare every cell in all 5 output tables against expected values using the hybrid tolerance model
4. Report pass/fail with cell-level detail on any failures

**Policy:** The regression must pass before any code change is accepted. If the pipeline cannot reproduce 2024, it cannot be trusted for any year.

**Extension plan:** When independent validation for 2025 or later years becomes available, add them to the regression suite. The harness grows harder to pass and more trustworthy over time.

> **Integration note:** Layer 5 is NOT currently integrated into the `run_all_tests.py` master test runner. It is run separately via `validation/2024/run_regression_2024.py`. The master runner orchestrates Layers 0, 0.5, 1, 2, and 6 only.

### 6.8 Layer 6: Provenance Logging

**Purpose:** Produce an audit trail that can withstand legal challenge.

**What it produces** (via `src/pipeline_manifest.py`):
- **Input manifest:** File names, SHA-256 hashes, row counts, date ranges for every input file
- **Pipeline manifest:** Git commit hash, git working tree status (clean/dirty), Python version, script modification dates, MODFLOW/FORTRAN executable metadata
- **Test results manifest:** Pass/fail per layer with specific values tested and thresholds applied
- **Flag register:** Analyst disposition workflow -- each flag has fields for disposition text, analyst initials, and review date
- **Run metadata:** Machine name, OS, timestamps, total runtime

**Manifest schema version:** 1.0

**Policy:** Generated on every pipeline run. Accompanies the 5 report tables in the project file. The manifest transforms "I checked the numbers" into "N automated tests passed, M flags were reviewed and dispositioned, the pipeline reproduced the independently validated 2024 dataset within tolerance, and here is the hash of every input file."

### 6.9 Physical Bounds from Historical Data (2022-2024)

Extracted from `validation/historical/bounds.yaml`.

#### Table 1: Annual Pumping by Well

| Well | Min (AF) | Max (AF) | Mean (AF) | Notes |
|------|---------|---------|----------|-------|
| B1 | 224.06 | 601.27 | 427.82 | Primary production well |
| B2 | 0.01 | 0.01 | 0.01 | Essentially inactive |
| B3/3A | 0.40 | 56.23 | 18.95 | Variable usage |
| B4 | 38.18 | 63.35 | 49.62 | Moderate, steady |
| B5 | 0.00 | 0.00 | 0.00 | Inactive (zero pumping) |
| B6 | 7.92 | 152.22 | 56.02 | Highly variable |
| B7 | 0.31 | 1.00 | 0.54 | Near-zero |
| B8 | 111.46 | 196.50 | 139.81 | Major production |
| B9 | 0.52 | 11.81 | 4.29 | Minor, variable |
| B10 | 45.17 | 151.41 | 80.66 | Significant |
| B11 | 13.62 | 89.00 | 38.75 | Variable |
| B12 | 0.18 | 9.80 | 3.39 | Minor |
| B13 | 127.85 | 212.02 | 152.57 | Major production |
| **Total** | **866.48** | **1,372.90** | **1,071.62** | Std: 266.95 AF |

**Threshold policy for total annual pumping:**
- Historical range: 866--1,373 AF
- Soft flag: > 2x historical max (2,746 AF)
- Hard fail: > 3x historical max (4,119 AF) or < 0 AF

#### Table 3: Cumulative Stream Depletions

| Stream | Min (AF) | Max (AF) | Mean (AF) | Std (AF) | Monotonic? |
|--------|---------|---------|----------|---------|-----------|
| Rio Pojoaque-Nambe | 59.844 | 60.797 | 60.321 | 0.477 | Yes (required) |
| Rio Tesuque | 33.490 | 33.583 | 33.521 | 0.053 | Yes (required) |

#### Table 4: Rio Grande Depletions

| Location | Min (AF) | Max (AF) | Mean (AF) | Std (AF) |
|----------|---------|---------|----------|---------|
| Above Otowi (annual) | 101.21 | 101.43 | 101.29 | 0.12 |
| Below Otowi (annual) | 783.23 | 842.94 | 809.50 | 30.67 |

#### Table 5: La Cienega Springs

| Parameter | Min (AF) | Max (AF) | Mean (AF) | Std (AF) | Monotonic? |
|-----------|---------|---------|----------|---------|-----------|
| Cumulative depletion | 3.37 | 3.74 | 3.55 | 0.19 | Yes (required) |

#### Derived Ratios

| Ratio | Min | Max | Mean | Interpretation |
|-------|-----|-----|------|---------------|
| Depletion/Pumping | 0.069 | 0.108 | 0.091 | Varies inversely with pumping intensity |

### 6.10 Test Runner Architecture

The master test runner (`run_all_tests.py`, 894 lines) orchestrates all layers with subprocess isolation and structured JSON reporting:

```
run_all_tests.py --year YYYY [--skip-ballpark] [--verbose] [--dry-run]
  |
  +-- [1/6] Ballpark check (validation/ballpark_check.py)
  |     Exit 0 --> pass
  |     Exit 2 --> soft flags, continue
  |     Exit 3 --> STOP (physics violation)
  |     Exit 4 --> skip (no baseline for this year)
  |
  +-- [2/6] Layer 0: Smoke tests (pytest -m layer0, timeout 300s)
  +-- [3/6] Layer 0.5: Edge cases (pytest -m edge_cases, timeout 120s)
  +-- [4/6] Layer 1: Conservation (pytest -m conservation, timeout 120s)
  |     Prerequisite check: MODFLOW outputs must exist
  |
  +-- [5/6] Layer 2: Temporal consistency (timeout 60s)
  |     Produces flags (not hard fails)
  |
  +-- [5.5/6] Layer 3: Cross-comparison (omitted from orchestration sequence; not explicitly skipped at runtime)
  |
  +-- [6/6] Layer 6: Provenance manifest (src/pipeline_manifest.py)
  |
  +-- Summary + workflow log generation (src/workflow_logger.py)
```

**Exit code semantics (master runner `run_all_tests.py`):**
- Exit 0: All hard-stop tests passed (flags may exist requiring review)
- Exit 1: Hard-stop test failure or script error
- Exit 3: Ballpark check critical physics violation

> **Note:** Exit code 2 (soft flag) is used *internally* by the `ballpark_check.py` subprocess, not by the master runner itself. When `ballpark_check.py` returns exit code 2, the master runner records the soft flags but continues execution and returns exit code 0 if no hard failures occurred. The master runner returns only 0, 1, or 3.

**Subprocess timeouts:**
- Ballpark check: 30 seconds
- Layer 0 (smoke): 300 seconds (5 minutes)
- Layer 0.5 (edge): 120 seconds
- Layer 1 (conservation): 120 seconds
- Layer 2 (temporal): 60 seconds
- Layer 6 (manifest): 60 seconds

**JSON reporting:** Each pytest layer writes structured results to `output/test_results/{layer_name}.json` via pytest-json-report, enabling programmatic parsing of pass/fail counts for the manifest and workflow log.

---

## 7. References

### Publications
- Anderson, M.P. & Woessner, W.W. (2015). Applied Groundwater Modeling, 2nd ed. Academic Press.
- McDonald, M.G. & Harbaugh, A.W. (1988). A Modular Three-Dimensional Finite-Difference Ground-Water Flow Model. USGS TWRI Book 6, Chapter A1.
- Reilly, T.E. & Harbaugh, A.W. (2004). Guidelines for Evaluating Ground-Water Flow Models. USGS Scientific Investigations Report 2004-5038.

### Standards
- USGS Groundwater Modeling Guidelines (Reilly & Harbaugh, 2004)
- ASTM D5447 -- Guide for Application of a Numerical Ground-Water Flow Model
- ASTM D5490 -- Guide for Comparing Ground-Water Flow Model Simulations to Site-Specific Information
- Daubert v. Merrell Dow Pharmaceuticals, 509 U.S. 579 (1993) -- legal standard for scientific evidence admissibility

### Data Sources
- validation/historical/bounds.yaml -- Physical bounds derived from 2022-2024 data
- validation/2024/tolerances.yaml -- Regression tolerance definitions
- validation/historical/extraction_log.md -- Documentation of bounds extraction process

---

## 8. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Well production data -- Layer 0 verifies ingestion outputs are valid; Layer 1 checks pumping sums |
| DS-02 | MODFLOW model -- Layer 1 checks mass balance from MODFLOW listing file |
| DS-03 | Stream depletions -- Layer 5 regression verifies depletion table values against 2024 baseline |
| DS-04 | Year chaining -- Layer 2 temporal checks verify chaining consistency across years |
| DS-06 | Regulatory compliance -- Layer 6 provenance logging produces audit artifacts required for OSE submission |
| IS-10 | Test implementation -- pytest test files implementing Layers 0, 0.5, 1 |
| IS-11 | Validation framework -- ballpark_check.py, temporal_consistency.py, bounds.yaml, tolerances.yaml |
| IS-12 | Provenance implementation -- pipeline_manifest.py, workflow_logger.py |

---

*Document Maintenance:*
- *Next Review:* When historical bounds are updated with new baseline years, or when new test layers are implemented (Layer 4 perturbation)
- *Change Triggers:* Addition of new validation years to regression suite, changes to tolerance definitions, implementation of Layer 3 or Layer 4, modification of exit code semantics, changes to the hybrid tolerance model
