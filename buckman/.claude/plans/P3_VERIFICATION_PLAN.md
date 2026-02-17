1# P3: Layer 1 — Conservation and Mass-Balance Checks

## Overview

Implement `tests/test_conservation.py` with four physics-based validation checks that run after every pipeline execution. These checks verify mass balance, unit consistency, and physical constraints.

---

## Context from Exploration

### Key Files & Formats

| Component | Location | Format |
|-----------|----------|--------|
| MODFLOW listing | `output/modflow/{year}/modflow/CY{year}.lst` (≤2024) or `output/modflow/{year}/CY{year}.lst` (≥2025) | Text, ~234K lines |
| Well input file | `output/modflow/{year}/thruCY2165_{year}.wel` | Text, 26 wells × 2 layers × 12 months |
| Post-processor output | `output/modflow/{year}/depletions/CY{year}` | Text, monthly cfs by cell/stream |
| Pumping tables | `output/ingested_data/{year}_Table_2_output.csv` | CSV, AF units (Well, JAN..DEC, Total) |
| Table 3 | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx` | XLSX, tributary depletions |
| Table 4 | `output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx` | XLSX, Rio Grande above/below Otowi |
| Table 5 | `output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx` | XLSX, La Cienega cumulative |

### Existing Parsing Code (Reusable)

- `verify_modflow_run.py`: Regex for `PERCENT DISCREPANCY =\s+([\d.]+)` and well rates
- `step4_generate_depletion_tables.py`: Post-processor output parsing (lines 457-618)
- `step2_update_modflow.py`: `ValidationResult` dataclass pattern

### Unit Conversions (Critical)

- **AF → ft³/s**: `rate = -(AF / 2 layers) × 43,560 / (days × 86,400)`
- **cfs → AF**: `AF = cfs × days × 86,400 / 43,560`
- **Precision**: 5 decimal places for pumping rates

---

## Check 1: Volumetric Budget Closure

**Objective**: Assert MODFLOW percent discrepancy < 0.1% for all stress periods.

### Implementation

```python
def check_budget_closure(lst_file: Path, tolerance: float = 0.1) -> ConservationResult:
    """Parse MODFLOW listing file and verify mass balance closure."""
```

**Steps:**
1. Read listing file content
2. Extract all percent discrepancies: `re.findall(r"PERCENT DISCREPANCY =\s+([\d.]+)", content)`
3. Find maximum discrepancy
4. Assert `max_discrepancy < tolerance`
5. Hard fail if no budget summaries found (indicates truncated/corrupt file)

**Output:**
- PASS: "Budget closure: max discrepancy 0.00% < 0.1% tolerance (N stress periods checked)"
- FAIL: "Budget closure FAILED: max discrepancy X.XX% at stress period N (threshold: 0.1%)"

---

## Check 2: Pumping-In = Pumping-Used

**Objective**: Verify pumping from input files matches MODFLOW-applied pumping.

### Unit Alignment Strategy

Both sources will be converted to **cubic feet per month** for comparison:
- Input (Table 2): AF/month → ft³/month (× 43,560)
- MODFLOW (.wel): ft³/s → ft³/month (× days × 86,400)

### Implementation

```python
def check_pumping_conservation(
    table2_file: Path,
    wel_file: Path,
    year: int,
    tolerance_pct: float = 0.1
) -> ConservationResult:
    """Verify pumping specified matches pumping applied."""
```

**Steps:**
1. Parse Table 2 CSV for monthly pumping by well (AF)
2. Parse .wel file for monthly pumping rates (ft³/s)
3. Convert both to ft³/month
4. Compare well-by-well, month-by-month
5. Assert differences < tolerance (relative)

**Edge Cases:**
- Handle negative sign convention in .wel (extraction = negative)
- Account for 2-layer well allocation (each layer gets half the total)
- Match well names between Table 2 and .wel file (use WELL_OSE_MAP from step2)

**Output:**
- PASS: "Pumping conservation: input 1234.56 AF = applied 1234.52 AF (Δ=0.03%)"
- FAIL: "Pumping conservation FAILED: Well 'Buckman 1' JAN - input 100.0 AF ≠ applied 95.2 AF (Δ=4.8%)"

---

## Check 3: Depletion ≤ Pumping

**Objective**: For every time step, cumulative depletion cannot exceed cumulative pumping.

### Physics Basis

Stream depletion is caused by pumping-induced drawdown intercepting groundwater that would have discharged to streams. Depletion cannot exceed the pumping that caused it (no water creation).

### Implementation

```python
def check_depletion_constraint(
    depletion_file: Path,
    table2_file: Path,
    year: int
) -> ConservationResult:
    """Assert cumulative depletion ≤ cumulative pumping at all times."""
```

**Steps:**
1. Parse post-processor output for "RIV TOTAL" stream summary (monthly cfs)
2. Convert to cumulative AF through each month
3. Parse Table 2 for cumulative pumping through each month
4. Assert: `cumulative_depletion[month] ≤ cumulative_pumping[month]` for all months

**Tolerance**: Allow 0.1% overshoot for numerical precision

**Output:**
- PASS: "Depletion constraint: max ratio 0.85 (depletion/pumping) - physics satisfied"
- FAIL: "Depletion constraint VIOLATED: Month 6 cumulative depletion 500.0 AF > pumping 450.0 AF (ratio 1.11)"

---

## Check 4: Table Sum Integrity

**Objective**: Verify internal consistency of computed sums in report tables.

### Checks by Table

| Table | Check | Expected Sum |
|-------|-------|--------------|
| Table 2 | Row totals = sum of monthly values | Per-well annual total |
| Table 2 | "Total" row = sum of all wells | Annual system total |
| Table 3 | Total Impact = Residual + Superposition | Per-stream check |
| Table 4 | Above + Below Otowi = RIO GRANDE total | Cross-check against stream summary |
| Table 4 | Cell sums = stream summary values | RIO GRANDE row vs cell totals |
| Table 5 | Cumulative = Previous + Annual increment | Temporal consistency |

### Implementation

```python
def check_table_sums(
    table_files: dict[str, Path],
    year: int,
    tolerance: float = 0.01  # AF
) -> ConservationResult:
    """Verify internal sum consistency across all report tables."""
```

**Steps per table:**
1. Load XLSX using openpyxl
2. Extract values and computed sums
3. Recompute sums independently
4. Assert `abs(stated_sum - computed_sum) < tolerance`

**Output:**
- PASS: "Table sum integrity: 15 checks passed across 5 tables"
- FAIL: "Table sum integrity FAILED: Table 4 Above Otowi JAN - stated 123.45 ≠ computed 123.89 (Δ=0.44 AF)"

---

## Structured Result Format

```python
from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime

@dataclass
class ConservationResult:
    """Structured result for conservation/mass-balance checks."""
    check_name: str
    status: Literal["PASS", "FAIL", "ERROR"]
    description: str
    actual_value: float | None = None
    expected_value: float | None = None
    tolerance: float | None = None
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dict for provenance manifest."""
        return {
            "check_name": self.check_name,
            "status": self.status,
            "description": self.description,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "tolerance": self.tolerance,
            "details": self.details,
            "timestamp": self.timestamp
        }
```

---

## Module Structure

```
tests/
└── test_conservation.py
    ├── ConservationResult (dataclass)
    ├── parse_budget_discrepancies(lst_file) → list[float]
    ├── parse_wel_pumping(wel_file, year) → dict[str, dict[str, float]]
    ├── parse_depletion_totals(depletion_file, year) → list[float]
    ├── check_budget_closure(lst_file, tolerance=0.1) → ConservationResult
    ├── check_pumping_conservation(table2, wel, year, tolerance=0.1) → ConservationResult
    ├── check_depletion_constraint(depletion, table2, year) → ConservationResult
    ├── check_table_sums(tables, year, tolerance=0.01) → ConservationResult
    ├── run_all_conservation_checks(year) → list[ConservationResult]
    └── main() → orchestrator for standalone execution
```

---

## Integration Points

### 1. Standalone Execution

```bash
python tests/test_conservation.py --year 2024
```

Output: Formatted console report + JSON results file

### 2. Pipeline Integration

Add to `step5_verify_workflow.py`:
```python
from tests.test_conservation import run_all_conservation_checks

def verify_step3(year: int) -> bool:
    # ... existing checks ...
    conservation_results = run_all_conservation_checks(year)
    all_passed = all(r.status == "PASS" for r in conservation_results)
    return existing_passed and all_passed
```

### 3. Pytest Integration

```python
# In test_conservation.py
import pytest

@pytest.mark.parametrize("year", [2024, 2025])
def test_budget_closure(year):
    result = check_budget_closure(get_lst_file(year))
    assert result.status == "PASS", result.description

# Similar for other checks
```

---

## File Paths (Parameterized by Year)

```python
def get_paths(year: int) -> dict:
    base = Path("/home/bradwolaver/projects/rg/santafe/buckman")
    modflow_dir = base / "output/modflow" / str(year)

    # Handle CY2024 vs CY2025 directory structure
    if year <= 2024:
        lst_file = modflow_dir / "modflow" / f"CY{year}.lst"
    else:
        lst_file = modflow_dir / f"CY{year}.lst"

    return {
        "lst_file": lst_file,
        "wel_file": modflow_dir / f"thruCY2165_{year}.wel",
        "depletion_file": modflow_dir / "depletions" / f"CY{year}",
        "table2_file": base / "output/ingested_data" / f"{year}_Table_2_output.csv",
        "table3_file": base / f"output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx",
        "table4_file": base / f"output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx",
        "table5_file": base / f"output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx",
    }
```

---

## Tolerances & Acceptance Criteria

| Check | Tolerance | Rationale |
|-------|-----------|-----------|
| Budget closure | 0.1% | MODFLOW standard; existing code uses 0.01% |
| Pumping conservation | 0.1% relative | Floating-point precision + unit conversion |
| Depletion ≤ Pumping | 0.1% overshoot | Numerical precision allowance |
| Table sums | 0.01 AF | Display precision (3 decimal places) |

---

## Success Criteria

1. All 4 checks return `ConservationResult` with proper status
2. Each check prints clear PASS/FAIL with specific values
3. Module runs standalone: `python tests/test_conservation.py --year 2024`
4. Module integrates with pytest: `pytest tests/test_conservation.py -v`
5. Results can be serialized to JSON for provenance manifest

---

## Uncertainties Flagged

1. ~~**Table output locations**~~: RESOLVED - Tables at `output/depletion/TABLE_{3,4,5}_*.xlsx`
2. **Depletion file structure**: Post-processor output contains all years (1988-2165); need to extract only target year's monthly values
3. **Well name mapping**: Table 2 uses well numbers (1-13), .wel file uses "BUCKMAN N" naming - straightforward mapping

---

## Estimated Complexity

- **Budget closure**: Simple regex, ~50 lines
- **Pumping conservation**: Moderate, unit conversion required, ~100 lines
- **Depletion constraint**: Moderate, needs cumulative tracking, ~80 lines
- **Table sums**: Higher complexity, 5 tables with different structures, ~150 lines
- **Total module**: ~400-500 lines including imports, docstrings, main()
