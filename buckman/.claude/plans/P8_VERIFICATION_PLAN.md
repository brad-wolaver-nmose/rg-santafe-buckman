# P8 Verification Plan: Integration — Wire Everything Together

**Status:** DRAFT v2 — Revised after critical review
**Created:** 2026-02-17
**Revised:** 2026-02-17
**Purpose:** Wire all test layers (0, 0.5, 1, 2, 6) into a unified test runner with robust error handling

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
**Pytest Marker:** `@pytest.mark.layer0` (to be added)

**What it does:** Verifies that every piece of code executes without crashing. These tests check that:
- All Python modules import correctly
- Functions accept the expected inputs
- File formats are read correctly
- Unit conversions work (e.g., million gallons → acre-feet)

**Why it matters:** If you change a line of code and accidentally break something else, smoke tests catch it immediately, before running MODFLOW.

**Example failures caught:**
- Typo in a column name that would silently produce wrong results
- Missing file that would crash the pipeline mid-run
- Wrong units applied to a conversion factor

**Result:** HARD FAIL if any test fails (stop and fix before proceeding)

---

### Layer 0.5: Edge Case Tests — "What Happens With Bad Input?"
**Location:** `tests/test_edge_cases.py` (30 automated tests)
**Pytest Marker:** `@pytest.mark.edge_cases` (already exists)

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
**Pytest Marker:** `@pytest.mark.conservation` (to be added)
**Dependency:** Requires pipeline outputs to exist (MODFLOW listing file, depletion tables)

**What it does:** Verifies that fundamental physical laws are satisfied:

1. **Volumetric Budget Closure:** MODFLOW's mass balance should close to within 0.1%. If water is appearing or disappearing from the model, something is wrong.

2. **Pumping Conservation:** The pumping you put into the model should equal the pumping the model actually applied. This catches unit conversion errors or stress period misalignments.

3. **Depletion ≤ Pumping:** Stream depletion cannot exceed pumping. You can't deplete more water from a stream than you pumped out of the ground. If this happens, there's a calculation error.

4. **Table Sum Integrity:** Rows and columns that should sum to totals actually do. This catches arithmetic errors in report generation.

**Why it matters:** These are the checks that your expert reviewer would do manually. We automate them so every run is verified to the same standard.

**Example error message:**
```
PUMPING CONSERVATION CHECK: FAILED

What was checked:
    Input pumping from Table 2 (your raw data)
    vs. Applied pumping in MODFLOW listing file (what the model used)

Values found:
    Input pumping (Table 2):       1372.92 acre-feet
    Applied pumping (MODFLOW):     1250.00 acre-feet
    Difference:                    122.92 acre-feet (8.95%)

Threshold: Values must match within 0.1%

What this means:
    The model is not using the pumping rates you provided.
    This usually indicates a unit conversion error or stress
    period misalignment in step2_update_modflow.py.

Suggested action:
    1. Check the .wel file: are pumping rates in ft³/s?
    2. Verify stress period dates match calendar months
    3. Run: python step2_update_modflow.py --year 2024 --verbose
```

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

**IMPORTANT — First Year After Baseline:**
The first year after baseline establishment (2025) will likely produce flags on all Layer 2 checks. This is **expected and normal** — 2025 has no prior year in the baseline to compare against. After 2025 runs successfully and is verified by human review, it should be added to the baseline (update bounds.yaml).

**Result:** FLAGS ONLY — these are warnings for human review, not automatic failures. The pipeline continues, but the flags are recorded in the manifest for an analyst to review before finalizing the report.

---

### Layer 3: Cross-Comparison — "External Validation"
**Status:** NOT IMPLEMENTED (scientifically rejected)

**What it was supposed to do:** Compare model outputs against external data sources like USGS stream gages or City of Santa Fe water production records.

**Why we rejected it:** After evaluation in P6, we determined these checks are not scientifically valid for this application:
- **USGS gage comparison:** Buckman wellfield depletions are 1-2 cfs. Rio Grande flows are 500-1500 cfs. USGS measurement uncertainty is ±5-10%. We cannot detect our signal above the noise.
- **Municipal demand ratio:** This ratio varies based on drought, policy, and maintenance — not model accuracy. It validates operations, not calculations.

The checks that *do* validate the model are Layers 0, 1, 2, 5, and 6.

DO NOT IMPLEMENT LAYER 3 CROSS-COMPARISON

---

### Layer 5: Regression Harness — "Does It Match the Gold Standard?"
**Location:** `validation/2024/run_regression_2024.py` (standalone script)

**What it does:** Runs the entire pipeline using frozen 2024 input data and compares outputs cell-by-cell against verified 2024 results (the "gold standard").

**Why it matters:** This is the ultimate sanity check before deploying code changes. If you modify the pipeline and the 2024 results still match, you haven't broken anything. If they don't match, you know something changed — investigate before deploying.

**When to run it:**
- Before deploying any pipeline code changes (*.py files)
- Before deploying config changes (bounds.yaml, tolerances.yaml)
- When something seems "off" and you want to verify the baseline
- NOT as part of every production run (too slow)

**Why it's separate:** This test runs the full MODFLOW model (~45 minutes). It's too slow for every production run.

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

This is your chain of custody documentation.

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

**Exit codes (REVISED for robustness):**
- 0 = All clear, continue with full tests
- 1 = Script error/crash (NOT interpreted as soft flags)
- 2 = Soft flags (continue, but review)
- 3 = HARD FAIL — critical physics violation, stop immediately

---

## What P8 Builds

P8 wires all these layers together into a single command:

```bash
python run_all_tests.py --year 2024
```

This runs everything in the correct order:
1. Validate year parameter
2. Verify required scripts exist
3. Ballpark check (fast gate — stop if critical failure)
4. Layer 0 (smoke)
5. Layer 0.5 (edge cases)
6. Layer 1 (conservation) — only if outputs exist
7. Layer 2 (temporal) — flags only
8. Layer 6 (generates manifest)
9. Prints summary

---

## Files to Create

| File | Purpose |
|------|---------|
| `run_all_tests.py` | Master test runner — orchestrates all layers |
| `tests/README.md` | Documentation for test framework |

## Files to Modify

| File | Changes |
|------|---------|
| `step5_verify_workflow.py` | Remove manifest generation (delegate to run_all_tests.py) |
| `pytest.ini` | Add `layer0` and `conservation` markers |
| `tests/test_*.py` | Add `@pytest.mark.layer0` to smoke tests |
| `tests/test_conservation.py` | Add `@pytest.mark.conservation` marker |
| `validation/ballpark_check.py` | Update exit codes (1=error, 2=flags, 3=hard fail) |

---

## Implementation Plan

### 1. Create `run_all_tests.py` (~350-400 lines)

Location: `/home/bradwolaver/projects/rg/santafe/buckman/run_all_tests.py`

**Architecture:**
```python
#!/usr/bin/env python3
"""
Master test runner for Buckman wellfield depletion pipeline.

Orchestrates all test layers in priority order with robust error handling.

Exit codes:
    0 = All hard-stop tests passed (flags may exist)
    1 = Hard-stop test failure OR script error
    2 = Reserved (unused)
    3 = Ballpark check critical physics violation

Usage:
    python run_all_tests.py --year 2024
    python run_all_tests.py --year 2024 --skip-ballpark  # for development
    python run_all_tests.py --year 2024 --verbose
    python run_all_tests.py --year 2024 --dry-run  # show what would run
"""
```

**Critical Fix: Exit Code Handling**

```python
# CRITICAL: Distinguish script crashes from intentional exit codes
def run_subprocess_safely(
    cmd: List[str],
    description: str,
    timeout_sec: int = 120,
    expected_codes: Dict[int, str] = None
) -> Tuple[int, str, str]:
    """
    Run subprocess with timeout and robust error handling.

    Args:
        cmd: Command to run
        description: Human-readable description for error messages
        timeout_sec: Maximum runtime before killing process
        expected_codes: Dict mapping exit codes to meanings
                       e.g., {0: "pass", 2: "flags", 3: "hard_fail"}

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        ScriptNotFoundError: If script doesn't exist
        ScriptTimeoutError: If script exceeds timeout
        ScriptCrashError: If script returns unexpected exit code
    """
    # Verify script exists BEFORE running
    script_path = Path(cmd[1]) if cmd[0] == "python3" else Path(cmd[0])
    if not script_path.exists():
        raise ScriptNotFoundError(
            f"Required script missing: {script_path}\n"
            f"Expected location: {script_path.absolute()}\n"
            f"This is a configuration error — contact pipeline maintainer."
        )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
    except subprocess.TimeoutExpired:
        raise ScriptTimeoutError(
            f"{description} exceeded {timeout_sec}s timeout.\n"
            f"Command: {' '.join(cmd)}\n"
            f"This may indicate: hung process, infinite loop, or resource contention."
        )

    # Check if exit code is expected
    if expected_codes and result.returncode not in expected_codes:
        raise ScriptCrashError(
            f"{description} returned unexpected exit code {result.returncode}.\n"
            f"Expected codes: {list(expected_codes.keys())}\n"
            f"This usually means the script crashed.\n"
            f"stderr: {result.stderr[:500] if result.stderr else '(empty)'}"
        )

    return result.returncode, result.stdout, result.stderr
```

**Critical Fix: Year Validation**

```python
VALID_BASELINE_YEARS = {2022, 2023, 2024}
MIN_PRODUCTION_YEAR = 2022
MAX_PRODUCTION_YEAR = 2100  # Sanity check

def validate_year(year: int) -> None:
    """
    Validate year parameter before any test execution.

    Raises:
        InvalidYearError: If year is not valid
    """
    if not isinstance(year, int):
        raise InvalidYearError(f"Year must be integer, got {type(year)}")

    if year < MIN_PRODUCTION_YEAR:
        raise InvalidYearError(
            f"Year {year} is before baseline data exists.\n"
            f"Minimum valid year: {MIN_PRODUCTION_YEAR}\n"
            f"Baseline years with data: {sorted(VALID_BASELINE_YEARS)}"
        )

    if year > MAX_PRODUCTION_YEAR:
        raise InvalidYearError(
            f"Year {year} seems unreasonable (max: {MAX_PRODUCTION_YEAR}).\n"
            f"Did you mean {year % 100 + 2000}?"
        )

    # Check required files exist for this year
    required_paths = [
        f"validation/historical/bounds.yaml",  # Always needed
    ]

    for path in required_paths:
        if not Path(path).exists():
            raise InvalidYearError(
                f"Required file missing for year {year}: {path}\n"
                f"Run pipeline setup or check file paths."
            )
```

**Critical Fix: Test Result Aggregation with pytest-json-report**

```python
def run_pytest_layer(
    layer_name: str,
    pytest_args: List[str],
    timeout_sec: int = 300
) -> TestResult:
    """
    Run pytest layer and extract structured results.

    Uses pytest-json-report for reliable result extraction.
    """
    json_report_path = Path(f"output/test_results/{layer_name}.json")
    json_report_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pytest",
        "--json-report",
        f"--json-report-file={json_report_path}",
        "--json-report-indent=2",
        "-v",
    ] + pytest_args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            layer=layer_name,
            name=layer_name,
            passed=0,
            failed=0,
            skipped=0,
            duration_sec=timeout_sec,
            hard_fail=True,
            error_message=f"Timeout after {timeout_sec}s"
        )

    # Parse JSON report for accurate counts
    if json_report_path.exists():
        with open(json_report_path) as f:
            report = json.load(f)

        summary = report.get("summary", {})
        return TestResult(
            layer=layer_name,
            name=layer_name,
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            skipped=summary.get("skipped", 0),
            duration_sec=report.get("duration", 0),
            hard_fail=summary.get("failed", 0) > 0,
            error_message=None,
            failed_tests=[
                t["nodeid"] for t in report.get("tests", [])
                if t.get("outcome") == "failed"
            ]
        )
    else:
        # Fallback: parse exit code only
        return TestResult(
            layer=layer_name,
            name=layer_name,
            passed=0 if result.returncode != 0 else -1,  # Unknown
            failed=1 if result.returncode != 0 else 0,
            skipped=0,
            duration_sec=0,
            hard_fail=result.returncode != 0,
            error_message=f"JSON report not generated. Exit code: {result.returncode}"
        )
```

**Critical Fix: Check Outputs Exist Before Layer 1**

```python
def check_layer1_prerequisites(year: int) -> Tuple[bool, str]:
    """
    Check if Layer 1 conservation tests can run.

    Layer 1 requires MODFLOW outputs to exist.

    Returns:
        Tuple of (can_run, message)
    """
    # Determine output directory
    if year <= 2024:
        modflow_dir = Path(f"output/modflow/{year}/modflow")
    else:
        modflow_dir = Path(f"output/modflow/{year}")

    required_files = [
        modflow_dir / f"CY{year}.lst",  # MODFLOW listing file
    ]

    optional_files = [
        Path(f"output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx"),
        Path(f"output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx"),
        Path(f"output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx"),
    ]

    missing_required = [f for f in required_files if not f.exists()]

    if missing_required:
        return False, (
            f"Layer 1 (conservation) SKIPPED: pipeline outputs not found.\n"
            f"Missing: {[str(f) for f in missing_required]}\n"
            f"Run the full pipeline first:\n"
            f"  python step1_ingest_buckman_data.py --year {year}\n"
            f"  python step2_update_modflow.py --year {year}\n"
            f"  ./step3_run_modflow.sh --year {year}\n"
            f"  python step4_generate_depletion_tables.py --year {year}"
        )

    return True, "All prerequisites found"
```

**Test Execution Order with Timeouts:**

```
┌────────────────────────────────────────────────────────────┐
│ 0. VALIDATION                                              │
│    • Validate year parameter                               │
│    • Verify required scripts exist                         │
│    • Timeout: N/A (instant)                                │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 1. BALLPARK CHECK (validation/ballpark_check.py)          │
│    • Timeout: 30 seconds                                   │
│    • Exit 1 = CRASH → stop with error                      │
│    • Exit 2 = soft flags → continue                        │
│    • Exit 3 = HARD FAIL → stop immediately                 │
│    • Exit 0 = all clear → continue                         │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 2. LAYER 0: SMOKE TESTS (pytest -m layer0)                │
│    • Timeout: 300 seconds (5 min)                          │
│    • Uses pytest-json-report for result extraction         │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 3. LAYER 0.5: EDGE CASES (pytest -m edge_cases)           │
│    • Timeout: 120 seconds (2 min)                          │
│    • Uses pytest-json-report for result extraction         │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 4. LAYER 1: CONSERVATION (pytest -m conservation)         │
│    • PRE-CHECK: verify outputs exist                       │
│    • If outputs missing: SKIP with message                 │
│    • Timeout: 120 seconds (2 min)                          │
│    • Any failure = HARD FAIL                               │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 5. LAYER 2: TEMPORAL CONSISTENCY                           │
│    (validation/temporal_consistency.py --year YYYY)        │
│    • Timeout: 60 seconds                                   │
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
│    • Timeout: 60 seconds                                   │
│    • Generate buckman_manifest_{year}.json                 │
│    • Include all test results + flags                      │
│    • ALWAYS generated (even on failure — documents state)  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 8. FINAL SUMMARY                                           │
│    • Layer-by-layer breakdown with timing                  │
│    • Total tests: X                                        │
│    • Passed: Y                                             │
│    • Failed: Z (with names of failed tests)                │
│    • Flagged: W (with flag descriptions)                   │
│    • Manifest: path/to/manifest.json                       │
└────────────────────────────────────────────────────────────┘
```

**Data Classes (Enhanced):**

```python
@dataclass
class TestResult:
    layer: str           # e.g., "Layer 0", "Layer 1"
    name: str            # e.g., "smoke_tests", "conservation"
    passed: int
    failed: int
    skipped: int
    duration_sec: float
    hard_fail: bool      # If True, contributes to non-zero exit
    error_message: Optional[str] = None
    failed_tests: List[str] = field(default_factory=list)

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
    exit_code: int
    error_messages: List[str] = field(default_factory=list)
```

**Verbose Flag Semantics:**

```python
# --verbose levels:
#   (default): Layer summaries only, failures in brief
#   --verbose: Layer summaries + all failure details + flag details
#   --very-verbose: All of above + individual test names + timing

def print_summary(results: TestSuite, verbose: int = 0) -> None:
    """
    Print test suite summary.

    Args:
        results: TestSuite with all results
        verbose: 0=brief, 1=detailed, 2=exhaustive
    """
    print("\n" + "="*70)
    print(f"TEST SUITE SUMMARY — YEAR {results.year}")
    print("="*70)

    # Layer-by-layer breakdown (always shown)
    for r in results.results:
        status = "PASS" if not r.hard_fail else "FAIL"
        if r.skipped > 0:
            status = "SKIP"
        print(f"\n{r.layer}: {status} ({r.passed} passed, {r.failed} failed, {r.skipped} skipped) [{r.duration_sec:.1f}s]")

        # Show failures (if any)
        if r.failed > 0 and verbose >= 1:
            for test in r.failed_tests:
                print(f"  ✗ {test}")

    # Flags section
    if results.flags:
        print(f"\n{'='*70}")
        print(f"FLAGS REQUIRING HUMAN REVIEW: {len(results.flags)}")
        print("="*70)
        for flag in results.flags:
            print(f"\n  [{flag.layer}] {flag.test_name}")
            print(f"    Value: {flag.value}")
            print(f"    Threshold: {flag.threshold}")
            print(f"    {flag.message}")

    # Totals
    total_passed = sum(r.passed for r in results.results)
    total_failed = sum(r.failed for r in results.results)
    total_skipped = sum(r.skipped for r in results.results)
    total_duration = sum(r.duration_sec for r in results.results)

    print(f"\n{'='*70}")
    print(f"TOTALS: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")
    print(f"FLAGS: {len(results.flags)} (require human review)")
    print(f"DURATION: {total_duration:.1f} seconds")
    print(f"MANIFEST: {results.manifest_path}")
    print("="*70)

    if results.exit_code == 0:
        print("\n✓ All hard-stop tests passed.")
        if results.flags:
            print("  (Review flags before using outputs for compliance)")
    elif results.exit_code == 3:
        print("\n✗ CRITICAL: Ballpark check detected physics violation.")
        print("  DO NOT use outputs. Investigate immediately.")
    else:
        print(f"\n✗ {total_failed} test(s) failed.")
        print("  DO NOT use outputs until failures are resolved.")
```

---

### 2. Modify `step5_verify_workflow.py`

**Critical Fix: Remove duplicate manifest generation**

```python
# REMOVE these lines (approximately lines 393-416):
#     # Generate provenance manifest (Layer 6)
#     if not args.no_manifest:
#         ...manifest generation code...

# REPLACE WITH:
def run_full_test_suite(year: int, allow_hash_mismatch: bool, verbose: bool) -> int:
    """
    Run the full test suite via run_all_tests.py.

    Manifest generation is handled by run_all_tests.py — do NOT duplicate here.

    Returns:
        Exit code (0=pass, 1=fail, 3=ballpark critical)
    """
    cmd = ["python3", "run_all_tests.py", "--year", str(year)]
    if allow_hash_mismatch:
        cmd.append("--allow-hash-mismatch")
    if verbose:
        cmd.append("--verbose")

    # Let output go to console (capture_output=False)
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


# In main(), after file existence checks:
print_section("RUNNING FULL TEST SUITE")
test_exit_code = run_full_test_suite(
    args.year,
    args.allow_hash_mismatch,
    args.verbose
)

# Interpret exit codes
if test_exit_code == 3:
    print("\n" + "="*70)
    print("CRITICAL: BALLPARK CHECK PHYSICS VIOLATION")
    print("   Outputs should NOT be used.")
    print("   This indicates a fundamental error in input data or model setup.")
    print("="*70)
    return 3
elif test_exit_code == 1:
    print("\n" + "="*70)
    print("WARNING: TEST FAILURES DETECTED")
    print("   Review failures before using outputs for compliance.")
    print("   See test output above for details.")
    print("="*70)
    return 1
else:
    print("\n✓ All hard-stop tests passed.")
    return 0
```

---

### 3. Update `pytest.ini`

```ini
[pytest]
testpaths = tests
markers =
    layer0: Layer 0 smoke tests (basic functionality)
    edge_cases: Layer 0.5 edge case tests (input validation, boundaries)
    conservation: Layer 1 conservation tests (mass balance, physics)
```

---

### 4. Update `validation/ballpark_check.py` Exit Codes

```python
# CHANGE exit codes for clarity:
# OLD: 0=pass, 1=flags, 2=hard_fail
# NEW: 0=pass, 1=error/crash (reserved), 2=flags, 3=hard_fail

# At end of main():
if hard_fails:
    print_hard_fail_summary(hard_fails)
    sys.exit(3)  # Changed from 2
elif soft_flags:
    print_flag_summary(soft_flags)
    sys.exit(2)  # Changed from 1
else:
    print_success_summary()
    sys.exit(0)
```

---

### 5. Add Pytest Markers to Test Files

**tests/test_ingest_buckman_data.py, test_update_modflow.py, etc.:**
```python
import pytest

pytestmark = pytest.mark.layer0  # Apply to all tests in file
```

**tests/test_conservation.py:**
```python
import pytest

pytestmark = pytest.mark.conservation
```

---

### 6. Create `tests/README.md` (~200 lines)

```markdown
# Buckman Wellfield Test Framework

## Quick Start

```bash
# Run full test suite
python run_all_tests.py --year 2024

# Run with verbose output
python run_all_tests.py --year 2024 --verbose

# Dry run (show what would execute)
python run_all_tests.py --year 2024 --dry-run
```

## Test Layers

| Layer | Purpose | Type | Marker | Timeout |
|-------|---------|------|--------|---------|
| **Ballpark** | Fast sanity check | Hard fail | N/A | 30s |
| **Layer 0** | Smoke tests — does code run? | Hard fail | `layer0` | 300s |
| **Layer 0.5** | Edge cases — bad input handling | Hard fail | `edge_cases` | 120s |
| **Layer 1** | Conservation — mass balance | Hard fail | `conservation` | 120s |
| **Layer 2** | Temporal — year-over-year | Flags only | N/A | 60s |
| **Layer 5** | Regression — 2024 baseline | Standalone | N/A | ~45min |
| **Layer 6** | Provenance manifest | Generated | N/A | 60s |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All hard-stop tests passed (flags may exist) |
| 1 | Hard-stop test failure OR script error |
| 3 | Ballpark check critical failure (physics violation) |

## Running Individual Layers

```bash
# Layer 0 (smoke tests)
pytest -m layer0 -v

# Layer 0.5 (edge cases)
pytest -m edge_cases -v

# Layer 1 (conservation)
pytest -m conservation -v

# Layer 2 (temporal)
python validation/temporal_consistency.py --year 2024

# Ballpark check only
python validation/ballpark_check.py --year 2024
```

## Layer 1 Prerequisites

Layer 1 (conservation) requires pipeline outputs to exist. If you see:
```
Layer 1 (conservation) SKIPPED: pipeline outputs not found
```

Run the full pipeline first:
```bash
python step1_ingest_buckman_data.py --year 2024
python step2_update_modflow.py --year 2024
./step3_run_modflow.sh --year 2024
python step4_generate_depletion_tables.py --year 2024
```

## First Year After Baseline (2025+)

The first year after baseline establishment (2025) will likely produce **flags on all Layer 2 checks**. This is **expected and normal**.

Why: Layer 2 compares against historical patterns (2022-2024). 2025 has no prior year in the baseline to compare against.

What to do:
1. Review the flags manually
2. If values are reasonable, document review in FLAG_REGISTER
3. After verification, add 2025 to baseline (update bounds.yaml)

## Regression Harness (Layer 5)

```bash
python validation/2024/run_regression_2024.py
```

**When to run:**
- Before deploying pipeline code changes (any .py file)
- Before deploying config changes (bounds.yaml, tolerances.yaml)
- When something seems wrong and you want to verify baseline

**Runtime:** ~45 minutes (runs full MODFLOW model)

## What to Do When Tests Fail

### Hard Fail (exit 1 or 3)

1. **DO NOT use outputs for compliance reporting**
2. Read the error message — it explains what failed
3. Check the specific value vs. expected value
4. Fix the underlying issue
5. Re-run tests

### Flags (Layer 2 temporal checks)

1. Flags do NOT block output use
2. Review each flag in the manifest
3. Document your review decision:
   - Open `output/manifests/buckman_manifest_{year}.json`
   - Find the `flag_register` section
   - Fill in `disposition`, `reviewed_by`, `review_date`
4. Flags require analyst sign-off before finalizing report

## Flag Review Workflow

When Layer 2 produces flags:

1. Open the manifest: `output/manifests/buckman_manifest_{year}.json`
2. Find the `flag_register` section
3. For each flag, document:
   ```json
   {
     "flag_id": "yoy_pumping_change",
     "disposition": "ACCEPTED - Drought year caused reduced pumping",
     "reviewed_by": "J. Smith",
     "review_date": "2026-02-17"
   }
   ```
4. Save the manifest (this is your audit trail)

## Manifest Location

```
output/manifests/buckman_manifest_{year}.json
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
- name: Run verification tests
  run: python run_all_tests.py --year ${{ env.YEAR }}

- name: Upload manifest artifact
  uses: actions/upload-artifact@v3
  with:
    name: verification-manifest
    path: output/manifests/buckman_manifest_*.json

- name: Upload test results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: output/test_results/*.json
```

Exit codes in CI:
- Exit 0: Proceed with deployment
- Exit 1: Block deployment, review failures
- Exit 3: Block deployment, critical issue

## Test Statistics

- **Layer 0:** ~188 smoke tests
- **Layer 0.5:** 30 edge case tests
- **Layer 1:** 4 conservation checks
- **Layer 2:** 4 temporal checks (flags)
- **Total runtime:** <60 seconds (excluding regression harness)
```

---

## Implementation Sequence

1. **Update `validation/ballpark_check.py`** — Change exit codes (1→error, 2→flags, 3→hard fail)

2. **Update `pytest.ini`** — Add layer0 and conservation markers

3. **Add markers to test files** — `@pytest.mark.layer0` / `@pytest.mark.conservation`

4. **Create `run_all_tests.py`** — Master orchestrator with:
   - Year validation
   - Script existence checks
   - Timeout handling
   - pytest-json-report integration
   - Layer 1 prerequisite checks
   - Robust error handling

5. **Modify `step5_verify_workflow.py`** — Remove manifest generation, call run_all_tests.py

6. **Create `tests/README.md`** — Full documentation

7. **Verification**
   - Run `python run_all_tests.py --year 2024`
   - Verify all layers execute with correct timeouts
   - Test error handling: rename a script, verify graceful failure
   - Test timeout: add `time.sleep(1000)` to a test, verify timeout works
   - Run `python step5_verify_workflow.py --year 2024`
   - Verify single manifest generated (no duplicates)

---

## Critical Files Referenced

| File | Purpose | Modifications |
|------|---------|---------------|
| `validation/ballpark_check.py` | Fast sanity check | Update exit codes |
| `validation/temporal_consistency.py` | Layer 2 temporal | No changes |
| `validation/2024/run_regression_2024.py` | Layer 5 regression | No changes |
| `src/pipeline_manifest.py` | Layer 6 manifest | No changes |
| `tests/test_*.py` | Layer 0 smoke tests | Add markers |
| `tests/test_edge_cases.py` | Layer 0.5 edge cases | Already has marker |
| `tests/test_conservation.py` | Layer 1 conservation | Add marker |
| `pytest.ini` | pytest configuration | Add markers |
| `step5_verify_workflow.py` | Verification workflow | Remove manifest gen |

---

## Dependencies to Install

```bash
pip install pytest-json-report
```

---

## Success Criteria

- [ ] `python run_all_tests.py --year 2024` executes all layers in order
- [ ] Year validation rejects invalid years with clear message
- [ ] Script existence is verified before execution
- [ ] Timeouts work: hung tests are killed after timeout
- [ ] Ballpark exit code 3 stops execution immediately
- [ ] Ballpark exit code 1 (crash) is treated as error, not "flags"
- [ ] Layer 1 skipped gracefully if outputs don't exist
- [ ] Layer 2 flags do NOT cause non-zero exit code
- [ ] Manifest includes all test results with counts
- [ ] Only ONE manifest generated (run_all_tests.py, not step5)
- [ ] `pytest-json-report` provides accurate test counts
- [ ] `tests/README.md` documents all layers and procedures
- [ ] Verbose flag shows appropriate detail level
- [ ] Total runtime <60 seconds (excluding regression harness)
