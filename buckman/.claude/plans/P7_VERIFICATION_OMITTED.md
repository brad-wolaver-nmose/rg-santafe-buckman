# P7: Omitted Perturbation and Sensitivity Testing Framework

## Purpose of This Document

This document archives the **full perturbation testing framework** that was originally designed for Layer 4 of the Buckman testing harness but was **intentionally omitted** after critical review. It preserves the complete design for potential future use while explaining why it was not implemented for the operational compliance pipeline.

---

## Decision Summary

| Aspect | Original Plan | Decision |
|--------|---------------|----------|
| Scope | 5 perturbation scenarios, 72 MODFLOW runs | **OMITTED** |
| Runtime | ~54 hours | → 0 hours |
| What it tests | MODFLOW physics (superposition, linearity) | Already validated |
| What we do instead | Edge case tests (Layer 0.5) | ~30 seconds |

---

## Why We Did Not Implement This

### 1. Tests MODFLOW, Not Our Code

The perturbation framework verifies that MODFLOW96 correctly implements:
- Linear superposition principle
- Proportional response to input changes
- Spatial locality of well effects

**Problem:** MODFLOW96 is a 30-year-old, extensively validated USGS code. The physics of linear groundwater flow are well-established. We are not going to find bugs in MODFLOW by running it 72 times with perturbed inputs.

**Our actual risk:** Bugs in our Python pipeline code — unit conversions, file format errors, data handling issues. These are caught by Layers 0-3 and 5, not by perturbation testing.

### 2. Cost-Benefit Analysis

| Metric | Perturbation Testing | Layers 0-3 + 5 |
|--------|---------------------|----------------|
| Compute time | 54 hours | <10 minutes |
| Information gained | "MODFLOW works" | Pipeline correctness |
| Bugs likely caught | ~0 (MODFLOW is validated) | Data handling errors |
| Failure modes caught | Model instability (rare) | Common production issues |

### 3. Arbitrary Thresholds

The proposed thresholds (e.g., "proportionality ratio 0.8-1.2") are not scientifically grounded:
- For confined aquifers, MODFLOW is perfectly linear (ratio = 1.0 exactly)
- For unconfined conditions, nonlinearity is well-characterized and expected
- A 20% tolerance is too loose to detect actual problems

### 4. Not Appropriate for Compliance Pipeline

Perturbation/sensitivity analysis is appropriate for:
- Calibrating a new groundwater model
- Quantifying prediction uncertainty for management decisions
- Publishing a model study for peer review

It is **not** appropriate as a recurring pipeline test because:
- The model doesn't change year to year
- The physics don't change
- The compute cost cannot be justified for annual compliance runs

### 5. USGS Guidelines Perspective

From USGS Techniques and Methods 6-A35 (Groundwater Model Documentation), the emphasis for operational models is on:
1. **Mass balance verification** — Already covered by Layer 1/3
2. **Comparison to observed data** — Historical validation
3. **Reproducibility** — Layer 5 regression testing

Formal sensitivity analysis is a **one-time study**, not a per-run verification.

---

## The Complete Omitted Framework

Below is the full design that was NOT implemented. Preserved for potential future one-off sensitivity studies.

### Directory Structure (Not Created)

```
tests/
├── test_perturbation.py       # Main perturbation test module
└── perturbation/              # Perturbation support module
    ├── __init__.py
    ├── scenarios.py           # Perturbation scenario implementations
    ├── runner.py              # Pipeline execution wrapper
    ├── comparator.py          # Baseline vs perturbed comparison
    └── results.py             # PerturbationResult dataclass

output/
└── perturbation/              # Temporary working directory
    └── {scenario}_{well}_{timestamp}/
```

### PerturbationResult Dataclass (Not Implemented)

```python
@dataclass
class PerturbationResult:
    scenario: str                    # e.g., "noise", "time_shift"
    well_id: int | None             # Well perturbed (None for global perturbations)
    perturbation_factor: float      # Scale factor applied
    baseline_depletion: dict        # {stream: [monthly_values]}
    perturbed_depletion: dict       # {stream: [monthly_values]}
    delta_depletion: dict           # Absolute change per stream
    proportionality_ratio: float    # ΔD / ΔQ (should be ~1 for linear model)
    status: Literal["PASS", "FAIL", "FLAGGED"]
    flags: list[str]                # Physical reasonableness violations
    timestamp: str

    def to_dict(self) -> dict: ...
    def summary_row(self) -> dict: ...
```

### Scenario Functions (Not Implemented)

```python
# tests/perturbation/scenarios.py

def apply_noise(pumping_df: pd.DataFrame, magnitude: float = 0.05, seed: int = None) -> pd.DataFrame:
    """Add ±magnitude uniform random noise to all pumping values.

    Args:
        pumping_df: Table 2 pumping data (wells × months)
        magnitude: Noise magnitude as fraction (0.05 = ±5%)
        seed: Random seed for reproducibility

    Returns:
        Perturbed pumping DataFrame
    """
    ...

def apply_time_shift(pumping_df: pd.DataFrame, well_id: int, periods: int = 1) -> pd.DataFrame:
    """Shift one well's pumping data by N stress periods (months).

    Args:
        pumping_df: Table 2 pumping data
        well_id: Well to shift (1-13)
        periods: Number of months to shift forward

    Returns:
        Perturbed pumping DataFrame with one well time-shifted
    """
    ...

def apply_zero_well(pumping_df: pd.DataFrame, well_id: int) -> pd.DataFrame:
    """Zero out pumping for one well entirely.

    Args:
        pumping_df: Table 2 pumping data
        well_id: Well to zero (1-13)

    Returns:
        Perturbed pumping DataFrame with one well zeroed
    """
    ...

def apply_double_pump(pumping_df: pd.DataFrame, well_id: int, month: int) -> pd.DataFrame:
    """Double one well's pumping for one month.

    Args:
        pumping_df: Table 2 pumping data
        well_id: Well to double (1-13)
        month: Month to double (1-12)

    Returns:
        Perturbed pumping DataFrame
    """
    ...

def apply_swap_wells(pumping_df: pd.DataFrame, well_a: int, well_b: int) -> pd.DataFrame:
    """Swap pumping data between two wells.

    Args:
        pumping_df: Table 2 pumping data
        well_a: First well (1-13)
        well_b: Second well (1-13)

    Returns:
        Perturbed pumping DataFrame with wells swapped
    """
    ...
```

### Pipeline Runner (Not Implemented)

```python
# tests/perturbation/runner.py

def setup_perturbation_workspace(scenario_name: str, well_id: int | None) -> Path:
    """Create isolated workspace for perturbation run.

    Creates: output/perturbation/{scenario}_{well}_{timestamp}/
    Copies baseline MODFLOW files to workspace.

    Returns:
        Path to workspace directory
    """
    ...

def run_pipeline(workspace: Path, perturbed_table2_path: Path, year: int) -> Path:
    """Execute full pipeline in workspace.

    Runs:
        1. step2_update_modflow.py --year {year} --input {perturbed_table2}
        2. step3_run_modflow.sh --year {year}
        3. step4_generate_depletion_tables.py --year {year}

    Returns:
        Path to output depletion tables
    """
    ...

def cleanup_workspace(workspace: Path, keep_outputs: bool = False):
    """Remove temporary MODFLOW files after run.

    If keep_outputs=True, keeps depletion tables but removes:
        *.flx, *.lst, *.cbc (large binary files)

    If keep_outputs=False, removes entire workspace.
    """
    ...
```

### Output Comparator (Not Implemented)

```python
# tests/perturbation/comparator.py

def load_depletion_tables(output_dir: Path, year: int) -> dict:
    """Load Tables 3-5 from XLSX files.

    Returns:
        {
            "table3": {"R POJOAQUE": [monthly_values], ...},
            "table4": {"RIO GRANDE": [monthly_values], ...},
            "table5": {"LC SPRINGS": [monthly_values], ...}
        }
    """
    ...

def compare_depletions(baseline: dict, perturbed: dict) -> dict:
    """Compare baseline vs perturbed depletion tables.

    Returns:
        {
            "delta": {stream: [monthly_deltas]},
            "percent_change": {stream: [monthly_pct]},
            "total_delta": float,
            "max_delta": float
        }
    """
    ...

def check_proportionality(delta_input: float, delta_output: float, tolerance: float = 0.2) -> bool:
    """Check if output change is proportional to input change.

    Returns True if: 1-tolerance < (delta_output/delta_input) < 1+tolerance
    """
    ...

def check_physical_reasonableness(result: PerturbationResult) -> list[str]:
    """Check for physical reasonableness violations.

    Flags:
        - Sign inversion: pumping increase causes depletion decrease
        - Amplification: small input change causes large output change
        - Non-locality: distant reaches change more than local
        - Negative depletion: output goes negative
        - Conservation violation: total depletion > total pumping

    Returns:
        List of flag descriptions (empty if no violations)
    """
    ...
```

### CLI Interface (Not Implemented)

```python
# tests/test_perturbation.py

def main():
    parser = argparse.ArgumentParser(
        description="Run perturbation/sensitivity tests on Buckman pipeline"
    )
    parser.add_argument(
        "--scenario",
        choices=["noise", "time_shift", "zero_well", "double_pump", "swap_wells", "all"],
        required=True,
        help="Perturbation scenario to run"
    )
    parser.add_argument(
        "--well",
        type=int,
        choices=range(1, 14),
        help="Well ID (1-13) for single-well scenarios"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Baseline year for comparison"
    )
    parser.add_argument(
        "--keep-outputs",
        action="store_true",
        help="Keep depletion tables after run (for inspection)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/perturbation"),
        help="Directory for perturbation outputs"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible noise tests"
    )
    args = parser.parse_args()

    # ... run scenarios
```

**Usage Examples (Never Implemented):**

```bash
# Run single scenario on single well
python tests/test_perturbation.py --scenario noise --well 1

# Run all scenarios on all wells (full matrix - 54 hours!)
python tests/test_perturbation.py --scenario all

# Debug mode: keep outputs for inspection
python tests/test_perturbation.py --scenario zero_well --well 5 --keep-outputs

# Reproducible noise test
python tests/test_perturbation.py --scenario noise --seed 42
```

### 5 Perturbation Scenarios (Not Implemented)

#### Scenario 1: NOISE TEST
```python
def test_noise_perturbation():
    """Add ±5% uniform random noise to all pumping values.

    Acceptance Criteria:
        - Proportionality ratio: 0.8 < ΔD/ΔQ < 1.2
        - No single-reach amplification > 2x
        - All stream depletions change in expected direction
    """
    perturbed = apply_noise(baseline_pumping, magnitude=0.05)
    outputs = run_pipeline(perturbed)

    # Assert proportional response
    assert 0.8 < proportionality_ratio < 1.2
    # Assert no amplification
    assert max_amplification < 2.0
```

#### Scenario 2: TIME-SHIFT TEST
```python
def test_time_shift():
    """Shift one well's pumping by one stress period (month).

    Acceptance Criteria:
        - Local effect dominates (>80% of change in nearby reaches)
        - Distant reaches change by <10% relative to baseline
        - No physically impossible values
    """
    for well_id in selected_wells:
        perturbed = apply_time_shift(baseline_pumping, well_id, periods=1)
        outputs = run_pipeline(perturbed)

        # Assert locality
        assert local_effect_fraction > 0.8
        assert distant_change_fraction < 0.10
```

#### Scenario 3: ZERO-WELL TEST
```python
def test_zero_well():
    """Zero out pumping for one well entirely.

    Acceptance Criteria:
        - Total depletion decrease ≈ well's fraction of total pumping (±20%)
        - No distant reach shows depletion increase
        - Flag if minor well (<5% pumping) causes >15% depletion change
    """
    for well_id in selected_wells:
        perturbed = apply_zero_well(baseline_pumping, well_id)
        outputs = run_pipeline(perturbed)

        # Assert proportional decrease
        assert abs(depletion_decrease - well_fraction) < 0.20
```

#### Scenario 4: DOUBLE-PUMP TEST
```python
def test_double_pump():
    """Double one well's pumping for one month.

    Acceptance Criteria:
        - Monthly depletion increase proportional to pumping increase
        - Spillover to adjacent months < 20% of direct effect
        - Linear superposition holds
    """
    for well_id in selected_wells:
        for month in [1, 6, 12]:  # Jan, Jun, Dec samples
            perturbed = apply_double_pump(baseline_pumping, well_id, month)
            outputs = run_pipeline(perturbed)

            # Assert linearity
            assert doubling_response_ratio > 0.9
```

#### Scenario 5: SWAPPED-WELL TEST
```python
def test_swapped_wells():
    """Swap pumping between two wells of similar magnitude.

    Acceptance Criteria:
        - Total annual depletion change < 5%
        - Local reach depletions redistribute according to well locations
        - No non-physical amplification
    """
    well_pairs = find_similar_wells(baseline_pumping)  # ±20% annual pumping

    for well_a, well_b in well_pairs:
        perturbed = apply_swap_wells(baseline_pumping, well_a, well_b)
        outputs = run_pipeline(perturbed)

        # Assert minimal total change
        assert total_depletion_change < 0.05
```

### Sensitivity Summary Table (Not Generated)

Output format that would have been written to `output/perturbation/sensitivity_summary_{timestamp}.csv`:

```
| Scenario    | Well | Input Δ | Output Δ | Ratio | Status  | Flags              |
|-------------|------|---------|----------|-------|---------|---------------------|
| noise       | ALL  | ±5%     | ±4.8%    | 0.96  | PASS    |                     |
| time_shift  | BW-1 | 1 month | local    | -     | PASS    |                     |
| zero_well   | BW-5 | -100%   | -8.2%    | 0.98  | PASS    |                     |
| zero_well   | BW-3 | -100%   | -45%     | 1.02  | FLAGGED | Large distant effect|
| double_pump | BW-7 | +100%   | +12.1%   | 1.01  | PASS    |                     |
| swap_wells  | 2↔4  | 0%      | +1.2%    | -     | PASS    |                     |
```

### Configuration (Not Used)

```python
DEFAULT_CONFIG = {
    "year": 2024,
    "noise_magnitude": 0.05,        # ±5%
    "time_shift_periods": 1,        # 1 month
    "representative_wells": [1, 5, 10],  # Quick mode subset
    "double_pump_months": [1, 6, 12],    # Jan, Jun, Dec
    "proportionality_tolerance": 0.2,    # 20%
    "amplification_threshold": 2.0,
    "distant_change_threshold": 0.10,    # 10%
    "random_seed": None,            # Set for reproducibility
    "keep_outputs": False,
    "output_dir": Path("output/perturbation"),
}
```

### Proportionality Thresholds (Not Applied)

| Metric | Threshold | Interpretation |
|--------|-----------|----------------|
| Proportionality ratio | 0.8 - 1.2 | Linear response |
| Amplification factor | < 2.0 | No chaotic behavior |
| Distant reach change | < 10% | Spatial locality |
| Total depletion change | ±20% of pumping Δ | Mass conservation |

### Physical Reasonableness Flags (Not Checked)

- Sign inversion: Pumping increase causes depletion decrease
- Amplification: Small input change causes large output change
- Non-locality: Distant reaches show larger changes than local
- Negative depletion: Output goes negative
- Conservation violation: Total depletion > total pumping

### Computational Cost (Not Incurred)

| Scenario | Wells | Runs | Time (est.) |
|----------|-------|------|-------------|
| Noise | 1 (global) | 1 | 45 min |
| Time-shift | 13 | 13 | 10 hrs |
| Zero-well | 13 | 13 | 10 hrs |
| Double-pump | 13 × 3 months | 39 | 29 hrs |
| Swap-wells | ~6 pairs | 6 | 4.5 hrs |
| **TOTAL** | - | **72** | **~54 hrs** |

---

## When This Framework WOULD Be Appropriate

If in the future you need formal sensitivity analysis, this framework could be implemented for:

1. **Model recalibration** — If the MODFLOW model is updated with new parameters
2. **Uncertainty quantification** — For management decisions requiring confidence intervals
3. **Peer review** — If publishing the model methodology
4. **New well additions** — To understand how adding well 14 would affect depletion patterns

In these cases, run the sensitivity analysis **once** as a dedicated study, archive the results, and cite them in future reports. Do not run as part of annual compliance pipeline.

---

## What We Implemented Instead

See `P7_VERIFICATION_PLAN.md` for the actual Layer 0.5 implementation:

- **Edge case tests** for input validation and data quality
- **Runtime:** <30 seconds (not 54 hours)
- **MODFLOW runs:** 0 (not 72)
- **Bugs caught:** Actual production failure modes (bad input, file format errors)

---

## References

- USGS Techniques and Methods 6-A35: Guidelines for Evaluating Ground-Water Flow Models
- MODFLOW-96 Documentation (McDonald & Harbaugh, 1996)
- Hill, M.C., & Tiedeman, C.R. (2007). Effective Groundwater Model Calibration
