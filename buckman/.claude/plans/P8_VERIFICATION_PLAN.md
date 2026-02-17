# P8 Verification Plan: Integration — Wire Everything Together

**Status:** DRAFT — Awaiting user approval
**Created:** 2026-02-17
**Purpose:** Wire all test layers (0, 0.5, 1, 2, 6) into a unified test runner and integrate with the existing pipeline workflow.

---

## Understanding the Test Layers (for Hydrologists)

This section explains what each test layer does and why it matters. These layers form a **defense-in-depth** approach to catching errors before reports are submitted for regulatory compliance.

### What Are Test "Layers"?

Think of these layers as checkpoints that your data and calculations pass through. Each layer catches a different category of problems. If an error slips past Layer 0, it should be caught by Layer 1. If it slips past Layer 1, it should be caught by Layer 2, and so on.

The layers are numbered roughly by their computational complexity and specificity:
- **Low numbers (0, 0.5):** Fast, basic checks — "Does the code run at all?"
- **Middle numbers (1, 2):** Physical and temporal reasonableness — "Do the numbers make sense?"
- **High numbers (5, 6):** Gold-standard validation and documentation — "Can we prove this is correct?"

---

### Layer 0: Smoke Tests — "Does the Code Run?"
**Location:** `tests/test_*.py` (188+ automated tests)

**What it does:** Verifies that every piece of code executes without crashing. These tests check that:
- All Python modules import correctly
- Functions accept the expected inputs
- File formats are read correctly
- Unit conversions work (e.g., million gallons → acre-feet)

**Why it matters:** If you change a line of code and accidentally break something else, smoke tests catch it immediately — before you spend 45 minutes running MODFLOW.

**Example failures caught:**
- Typo in a column name that would silently produce wrong results
- Missing file that would crash the pipeline mid-run
- Wrong units applied to a conversion factor

**Result:** HARD FAIL if any test fails (stop and fix before proceeding)

---

### Layer 0.5: Edge Case Tests — "What Happens With Bad Input?"
**Location:** `tests/test_edge_cases.py` (30 automated tests)

**What it does:** Tests how the pipeline handles unusual, malformed, or boundary-condition inputs:
- Empty CSV files
- Missing columns in input data
- Negative pumping values (physically impossible)
- Leap year handling (366 vs 365 days)
- Zero pumping for all wells

**Why it matters:** Real-world data is messy. Someone might accidentally paste the wrong year's data, or a sensor might report a negative value. These tests ensure the pipeline either handles the problem gracefully or stops with a clear error message explaining what went wrong.

**Example failures caught:**
- CSV with missing "BWell 5" column → clear error: "Column 'BWell 5' not found in row 12"
- Negative pumping rate in February → clear error: "Negative pumping rate (-5.2 MGD) is physically impossible"

**Result:** HARD FAIL if any test fails

---

### Layer 1: Conservation Tests — "Do the Physics Check Out?"
**Location:** `tests/test_conservation.py` (4 physics checks)

**What it does:** Verifies that fundamental physical laws are satisfied:

1. **Volumetric Budget Closure:** MODFLOW's mass balance should close to within 0.1%. If water is appearing or disappearing from the model, something is wrong.

2. **Pumping Conservation:** The pumping you put into the model should equal the pumping the model actually applied. This catches unit conversion errors or stress period misalignments.

3. **Depletion ≤ Pumping:** Stream depletion cannot exceed pumping. You can't deplete more water from a stream than you pumped out of the ground. If this happens, there's a calculation error.

4. **Table Sum Integrity:** Rows and columns that should sum to totals actually do. This catches arithmetic errors in report generation.

**Why it matters:** These are the checks that your expert reviewer would do manually. We automate them so every run is verified to the same standard.

**Example failures caught:**
- Off-by-one month in stress period alignment → depletions shifted by one month
- Sign error in pumping conversion → pumping applied to wrong layer
- MODFLOW non-convergence → budget doesn't close

**Result:** HARD FAIL if any check fails

---

### Layer 2: Temporal Consistency — "Is This Year Weird?"
**Location:** `validation/temporal_consistency.py` (4 temporal checks)

**What it does:** Compares the current year's results against historical patterns (2022-2024):

1. **Year-over-Year Pumping Change:** Flags if annual pumping changed by more than 65% from the previous year. This catches data entry errors where someone might accidentally enter gallons instead of million gallons.

2. **Year-over-Year Ratio Change:** Flags if the depletion/pumping ratio changed dramatically. The physics of the aquifer don't change year-to-year, so large ratio changes suggest an error.

3. **Seasonal Pattern Correlation:** Checks if the monthly pumping pattern matches historical seasonality. This specifically catches stress period errors where months might be shifted by one.

4. **Multi-Year Envelope:** Checks if values fall within the range observed in prior years (plus a reasonable buffer). Detects gross errors like decimal point shifts.

**Why it matters:** These checks catch errors that might pass the physics tests but would be obvious to someone who has seen 20 years of these reports. "Wait, pumping tripled? That doesn't seem right..."

**Result:** FLAGS ONLY — these are warnings for human review, not automatic failures. The pipeline continues, but the flags are recorded in the manifest for an analyst to review before finalizing the report.

---

### Layer 3: Cross-Comparison — "External Validation"
**Status:** NOT IMPLEMENTED (scientifically rejected)

**What it was supposed to do:** Compare model outputs against external data sources like USGS stream gages or City of Santa Fe water production records.

**Why we rejected it:** After evaluation in P6, we determined these checks are not scientifically valid for this application:
- **USGS gage comparison:** Buckman wellfield depletions are 1-2 cfs. Rio Grande flows are 500-1500 cfs. USGS measurement uncertainty is ±5-10%. We cannot detect our signal above the noise.
- **Municipal demand ratio:** This ratio varies based on drought, policy, and maintenance — not model accuracy. It validates operations, not calculations.

The checks that *do* validate the model are Layers 0, 1, 2, 5, and 6.

---

### Layer 5: Regression Harness — "Does It Match the Gold Standard?"
**Location:** `validation/2024/run_regression_2024.py` (standalone script)

**What it does:** Runs the entire pipeline using frozen 2024 input data and compares outputs cell-by-cell against verified 2024 results (the "gold standard").

**Why it matters:** This is the ultimate sanity check before deploying code changes. If you modify the pipeline and the 2024 results still match, you haven't broken anything. If they don't match, you know something changed — investigate before deploying.

**Why it's separate:** This test runs the full MODFLOW model (~45 minutes). It's too slow for every production run, so it's used:
- Before deploying pipeline code changes
- When something seems "off" and you want to verify the baseline

**Result:** HARD FAIL if outputs don't match within tolerances (standalone script, not part of every run)

---

### Layer 6: Provenance Manifest — "Prove It's Reproducible"
**Location:** `src/pipeline_manifest.py`

**What it does:** Generates a JSON file documenting everything needed to reproduce and verify a run:
- SHA-256 cryptographic hashes of all input files (proves inputs weren't modified)
- Git commit hash (proves which code version was used)
- All test results (proves tests were run and passed)
- Timestamps, machine info, runtime (audit trail)

**Why it matters:** If you're ever questioned about a report — by a regulator, an expert witness in a water rights case, or a colleague three years from now — the manifest proves:
1. What data went in
2. What code processed it
3. That all verification checks passed
4. When and where it was run

This is your chain of custody documentation for regulatory compliance.

**Result:** Generated automatically at the end of every test run

---

### Ballpark Check — "Fast Sanity Check"
**Location:** `validation/ballpark_check.py`

**What it does:** A lightning-fast (<5 second) check that catches gross errors before running the full test suite:
- Total pumping within historical envelope
- Depletions monotonically increasing (cumulative)
- Depletion/pumping ratios within bounds
- No NaN or negative values

**Why it matters:** If someone pasted the wrong year's data or there's a file corruption issue, this catches it in 5 seconds instead of after running through all the tests.

**Exit codes:**
- 0 = All clear, continue with full tests
- 1 = Soft flags (continue, but review)
- 2 = HARD FAIL — critical physics violation, stop immediately

---

## What P8 Builds

P8 wires all these layers together into a single command:

```bash
python run_all_tests.py --year 2024
```

This runs everything in the correct order:
1. Ballpark check (fast gate — stop if critical failure)
2. Layer 0 (smoke)
3. Layer 0.5 (edge cases)
4. Layer 1 (conservation)
5. Layer 2 (temporal) — flags only
6. Layer 6 (generates manifest)
7. Prints summary

---

## Files to Create

| File | Purpose |
|------|---------|
| `run_all_tests.py` | Master test runner — orchestrates all layers |
| `tests/README.md` | Documentation for test framework |

## Files to Modify

| File | Changes |
|------|---------|
| `step5_verify_workflow.py` | Call `run_all_tests.py` instead of ad-hoc test execution |

---

## Implementation Plan

### 1. Create `run_all_tests.py` (~250-300 lines)

Location: `/home/bradwolaver/projects/rg/santafe/buckman/run_all_tests.py`

**Architecture:**
```python
#!/usr/bin/env python3
"""
Master test runner for Buckman wellfield depletion pipeline.

Orchestrates all test layers in priority order:
1. Ballpark check (fast sanity, <5 sec) — HARD FAIL stops execution
2. Layer 0 (smoke) — HARD FAIL
3. Layer 0.5 (edge cases) — HARD FAIL
4. Layer 1 (conservation) — HARD FAIL
5. Layer 2 (temporal consistency) — FLAGS only (human review)
6. Layer 6 (provenance manifest) — generated at end

Exit codes:
    0 = All hard-stop tests passed (flags may exist)
    1 = Hard-stop test failure
    2 = Ballpark check HARD FAIL (critical physics violation)

Usage:
    python run_all_tests.py --year 2024
    python run_all_tests.py --year 2024 --skip-ballpark  # for development
    python run_all_tests.py --year 2024 --verbose
"""
```

**Test Execution Order:**

```
┌────────────────────────────────────────────────────────────┐
│ 1. BALLPARK CHECK (validation/ballpark_check.py)          │
│    • Runtime: <5 seconds                                   │
│    • Exit 2 = HARD FAIL → stop immediately                 │
│    • Exit 1 = soft flags → continue                        │
│    • Exit 0 = all clear → continue                         │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 2. LAYER 0: SMOKE TESTS (pytest tests/test_*.py)          │
│    • Excludes: test_edge_cases.py, test_conservation.py   │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 3. LAYER 0.5: EDGE CASES (pytest -m edge_cases)           │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 4. LAYER 1: CONSERVATION (pytest test_conservation.py)    │
│    • Budget closure, pumping conservation, depletion ≤    │
│      pumping, table sums                                   │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 5. LAYER 2: TEMPORAL CONSISTENCY                           │
│    (validation/temporal_consistency.py --year YYYY)        │
│    • Year-over-year checks, seasonal patterns              │
│    • Results = FLAGS only (do NOT cause non-zero exit)     │
│    • Flags recorded for human review                       │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 6. LAYER 3: CROSS-COMPARISON                               │
│    • SKIPPED (scientifically rejected in P6)               │
│    • Log: "Layer 3 not applicable — see P6 rationale"      │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 7. LAYER 6: PROVENANCE MANIFEST (src/pipeline_manifest.py)│
│    • Generate buckman_manifest_{year}.json                 │
│    • Include all test results + flags                      │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 8. FINAL SUMMARY                                           │
│    • Total tests: X                                        │
│    • Passed: Y                                             │
│    • Failed: Z (hard fails)                                │
│    • Flagged: W (require human review)                     │
│    • Manifest: path/to/manifest.json                       │
└────────────────────────────────────────────────────────────┘
```

**Key Functions:**

```python
def run_ballpark_check(year: int) -> Tuple[int, List[str]]:
    """Run fast sanity check. Returns (exit_code, flags)."""

def run_pytest_layer(layer_name: str, test_spec: str) -> TestResult:
    """Run pytest with given spec, return structured result."""

def run_temporal_consistency(year: int) -> List[Flag]:
    """Run Layer 2 temporal checks, return flags (not failures)."""

def generate_manifest(year: int, test_results: TestSuite) -> Path:
    """Generate Layer 6 provenance manifest."""

def print_summary(results: TestSuite) -> None:
    """Print final summary to console."""

def main() -> int:
    """Main entry point. Returns exit code."""
```

**Data Classes:**

```python
@dataclass
class TestResult:
    layer: str           # e.g., "Layer 0", "Layer 1"
    name: str            # e.g., "smoke_tests", "conservation"
    passed: int
    failed: int
    duration_sec: float
    hard_fail: bool      # If True, contributes to non-zero exit

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
    results: List[TestResult]
    flags: List[Flag]
    manifest_path: Optional[Path]
    start_time: datetime
    end_time: datetime
```

---

### 2. Modify `step5_verify_workflow.py`

Location: `/home/bradwolaver/projects/rg/santafe/buckman/step5_verify_workflow.py`

**Current behavior:** Runs ad-hoc pytest calls for each step, generates manifest.

**New behavior:**
1. Keep file existence checks (quick sanity before running tests)
2. Call `run_all_tests.py` via subprocess (or import as module)
3. Pass through `--allow-hash-mismatch` and `--verbose` flags
4. Print WARNING if any hard-stop tests fail

**Changes (~50 lines):**

```python
# After file existence checks in verify_step3():
def run_full_test_suite(year: int, allow_hash_mismatch: bool, verbose: bool) -> int:
    """
    Run the full test suite via run_all_tests.py.

    Returns:
        Exit code (0=pass, 1=fail, 2=ballpark hard fail)
    """
    cmd = ["python3", "run_all_tests.py", "--year", str(year)]
    if allow_hash_mismatch:
        cmd.append("--allow-hash-mismatch")
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode

# In main(), after all step verifications:
print_section("RUNNING FULL TEST SUITE")
test_exit_code = run_full_test_suite(
    args.year,
    args.allow_hash_mismatch,
    args.verbose
)

if test_exit_code == 2:
    print("\n" + "="*70)
    print("CRITICAL: BALLPARK CHECK HARD FAIL")
    print("   Outputs should NOT be used until failure is investigated.")
    print("="*70)
elif test_exit_code == 1:
    print("\n" + "="*70)
    print("WARNING: TEST FAILURES DETECTED")
    print("   Review failures before using outputs for compliance.")
    print("="*70)
else:
    print("\nAll hard-stop tests passed.")
```

---

### 3. Create `tests/README.md` (~150 lines)

Location: `/home/bradwolaver/projects/rg/santafe/buckman/tests/README.md`

**Contents:**

```markdown
# Buckman Wellfield Test Framework

## Test Layers

| Layer | Purpose | Type | Location |
|-------|---------|------|----------|
| **Layer 0** | Smoke tests — does code run? | Hard fail | `tests/test_*.py` |
| **Layer 0.5** | Edge cases — input validation, boundaries | Hard fail | `tests/test_edge_cases.py` |
| **Layer 1** | Conservation — mass balance, physics | Hard fail | `tests/test_conservation.py` |
| **Layer 2** | Temporal — year-over-year consistency | Flags only | `validation/temporal_consistency.py` |
| **Layer 3** | Cross-comparison | Not implemented | N/A (see P6 rationale) |
| **Layer 5** | Regression — 2024 frozen baseline | Standalone | `validation/2024/run_regression_2024.py` |
| **Layer 6** | Provenance — audit trail manifest | Generated | `src/pipeline_manifest.py` |

## Running Tests

### Full Test Suite (Production)
```bash
python run_all_tests.py --year 2024
```

### Individual Layers
```bash
# Layer 0 (smoke)
pytest tests/ -v --ignore=tests/test_edge_cases.py --ignore=tests/test_conservation.py

# Layer 0.5 (edge cases)
pytest tests/test_edge_cases.py -v -m edge_cases

# Layer 1 (conservation)
pytest tests/test_conservation.py -v

# Layer 2 (temporal)
python validation/temporal_consistency.py --year 2024
```

### Regression Harness (Before Deployment)
```bash
python validation/2024/run_regression_2024.py
```

**IMPORTANT:** The regression harness runs the FULL pipeline (~45 min).
Run manually before deploying pipeline changes, NOT as part of every production run.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All hard-stop tests passed (flags may exist) |
| 1 | Hard-stop test failure |
| 2 | Ballpark check critical failure (physics violation) |

## What to Do When Tests Flag

1. **Hard Fail (exit 1 or 2):**
   - DO NOT use outputs for compliance reporting
   - Review specific failure in test output
   - Fix underlying issue before re-running

2. **Flags (Layer 2 temporal checks):**
   - Review flagged values in manifest
   - Document disposition in FLAG_REGISTER section
   - Flags require analyst sign-off but do not block output use

## Manifest Location

Provenance manifests are written to:
```
output/manifests/buckman_manifest_{year}.json
```

## Test Statistics

- **Layer 0:** ~188 smoke tests
- **Layer 0.5:** 30 edge case tests
- **Layer 1:** 4 conservation checks
- **Layer 2:** 4 temporal checks (flags)
- **Total runtime:** <60 seconds (excluding regression harness)
```

---

## Implementation Sequence

1. **Create `run_all_tests.py`**
   - Implement ballpark check integration (subprocess call)
   - Implement pytest layer runners
   - Implement temporal consistency integration
   - Implement manifest generation integration
   - Implement summary printer
   - Add CLI argument parsing

2. **Modify `step5_verify_workflow.py`**
   - Add `run_full_test_suite()` function
   - Replace ad-hoc pytest calls with single call to `run_all_tests.py`
   - Keep file existence checks (fast pre-flight)
   - Add WARNING messages for failures

3. **Create `tests/README.md`**
   - Document all layers
   - Document run commands
   - Document flag handling procedure

4. **Verification**
   - Run `python run_all_tests.py --year 2024`
   - Verify all layers execute in order
   - Verify exit codes are correct
   - Verify manifest includes test results
   - Run `python step5_verify_workflow.py --year 2024`
   - Verify integration works end-to-end

---

## Critical Files Referenced

| File | Purpose |
|------|---------|
| `validation/ballpark_check.py` | Fast sanity check, exit codes 0/1/2 |
| `validation/temporal_consistency.py` | Layer 2 temporal checks |
| `validation/2024/run_regression_2024.py` | Layer 5 regression (standalone) |
| `src/pipeline_manifest.py` | Layer 6 manifest generation |
| `tests/test_*.py` | Layer 0 smoke tests |
| `tests/test_edge_cases.py` | Layer 0.5 edge cases |
| `tests/test_conservation.py` | Layer 1 conservation |
| `pytest.ini` | pytest configuration with `edge_cases` marker |

---

## Layer 3 Note

Layer 3 (cross-comparison checks) was evaluated in P6 and **scientifically rejected**:
- Municipal demand ratio does not validate model physics
- USGS gage signal-to-noise failure (Buckman depletions are 2-3 orders of magnitude below measurement uncertainty)

`run_all_tests.py` will log: `"Layer 3: SKIPPED (not applicable — see .claude/plans/P6_VERIFICATION_PLAN.md)"`

---

## Success Criteria

- [ ] `python run_all_tests.py --year 2024` executes all layers in order
- [ ] Ballpark hard fail (exit 2) stops execution immediately
- [ ] Layer 2 flags do NOT cause non-zero exit code
- [ ] Manifest includes all test results and flags
- [ ] `step5_verify_workflow.py` calls `run_all_tests.py` after file checks
- [ ] WARNING printed when hard-stop tests fail
- [ ] `tests/README.md` documents all layers and procedures
- [ ] Total runtime <60 seconds (excluding regression harness)
