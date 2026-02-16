# Verification Plan: 2025 Workflow & Year-to-Year File Propagation

## Executive Summary

**Current Status:** The 2025 workflow is COMPLETE - all 5 tables generated successfully. The year-to-year file propagation system is already working correctly, but lacks visibility and integrated verification.

**Objective:** Enhance workflow robustness through:
1. Manual spot-checking of 2025 tables (user-driven)
2. Enhanced file dependency visibility in prerequisite checks
3. Automated verification via new `verify_workflow.py` script
4. Comprehensive documentation of file dependencies

---

## Phase 1: Manual Spot-Check of 2025 Tables (User-Driven)

**User will manually verify:**
- Tables 1-5 data quality ("make sense")
- Manual calculations to verify formulas
- Identify any anomalies or concerns

**Files to review:**
- `output/ingested_data/2025_Table_1_updated.xlsx` - Historical AFY by well (1988-2025)
- `output/ingested_data/2025_Table_2_output.xlsx` - 2025 monthly pumping
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2025.xlsx` - Stream depletions
- `output/depletion/TABLE_4_Rio_Grande_Otowi_2025.xlsx` - Rio Grande depletions
- `output/depletion/TABLE_5_La_Cienega_Springs_2025.xlsx` - Springs cumulative

**Outcome:** User identifies any specific issues to fix, or confirms data quality.

---

## Phase 2: Code Audit - File Propagation Verification

### Current Year-to-Year File Handling (VERIFIED WORKING)

| File Type | Year N-1 → Year N Behavior | Script Location | Status |
|-----------|---------------------------|-----------------|--------|
| **Table 1** | Fallback from `output/{N-1}/{N-1}_Table_1_updated.xlsx` if no validation file | `step1:1053-1074` | ✓ CORRECT |
| **Table 2** | Generated fresh (no carryover) | `step1` | ✓ CORRECT |
| **WEL file** | Reads `output/modflow/{N-1}/thruCY2165_{N-1}.wel` (chained) | `step2:43-81` | ✓ CORRECT |
| **NAM file** | Generated fresh with updated references | `step2` | ✓ CORRECT |
| **Baseline files** | Copied from `input/modflow/2023/` (10 files) | `step2:786-836` | ✓ CORRECT |

**Files copied by `copy_baseline_files()` (step2:163-174):**
1. `modflow96.exe` - MODFLOW96 executable
2. `sflcs.bcf` - Block-Centered Flow package
3. `sflcs.sip` - Strongly Implicit Procedure solver
4. `thruCY2165.bas` - Basic package
5. `thruCY2165.ghb` - General Head Boundary package
6. `thruCY2165.oc` - Output Control
7. `thruCY2165.riv` - River package
8. `sfmodflx_2245.exe` - Stream flux post-processor
9. `verify_modflow_run.py` - MODFLOW verification script
10. `verify_depletion.py` - Depletion verification script

### Year Anonymity (VERIFIED)

All three scripts use `--year` CLI argument correctly. No hardcoded years in logic:
- `BASELINE_YEAR = 2024` in step2 - INTENTIONAL (marks transition from 2023 baseline)
- `DEFAULT_YEAR = 2024` in step3 - CLI default only (not logic hardcoding)

---

## Phase 3: Code Enhancements

### 3.1 Enhanced Prerequisite Checks (Checklist Integration)

**Approach:** Hybrid - Documentation + Enhanced Logging

**Rationale (Senior Dev Perspective):**
- Users need context-aware guidance at each step
- Checklist.md provides comprehensive reference
- Enhanced prerequisite checks provide just-in-time information
- Non-intrusive (no new flags to remember)
- Doesn't slow down workflow

**Implementation:**

#### 3.1.1 Enhance step1_ingest_buckman_data.py

**File:** `step1_ingest_buckman_data.py`
**Function:** `check_prerequisites()` (lines 1674-1704)

**Add after line 1703 (before `return True`):**

```python
# Print checklist-style prerequisite status
print("\n" + "="*70)
print(f"STEP 1: INGEST PUMPING DATA - YEAR {year}")
print("="*70)
print("✓ Prerequisites:")
print(f"  - Input CSV: input/csv/Buckman_Well_Prod_{year}.csv [FOUND]")

# Check Table 1 template availability
validation_path = Path(VALIDATION_DIR) / f"Table_1_data_afy_{year}.xlsx"
fallback_path = Path(OUTPUT_DIR) / f"{year - 1}" / f"{year - 1}_Table_1_updated.xlsx"

print("\n📋 Table 1 Template Source:")
if validation_path.exists():
    print(f"  ✓ Using validation file: {validation_path.name}")
elif fallback_path.exists():
    print(f"  ✓ Using {year - 1} output as template: {fallback_path.name}")
else:
    print(f"  ⚠ WARNING: No template found!")
    print(f"    - Primary: {validation_path.name} [NOT FOUND]")
    print(f"    - Fallback: {fallback_path} [NOT FOUND]")
    print(f"    ⚠ Table 1 generation will fail unless template is created.")

print("\n📦 Outputs (after completion):")
print(f"  - {year}_Table_1_updated.xlsx (historical AFY by well)")
print(f"  - {year}_Table_2_output.xlsx (monthly pumping)")
print(f"  - 12 monthly CSV files")

print("\n➡️  Next Step:")
print(f"  python3 step2_update_modflow.py --year {year}")
print("="*70 + "\n")
```

#### 3.1.2 Enhance step2_update_modflow.py

**File:** `step2_update_modflow.py`
**Location:** In `main()` function, after `config = get_year_config(target_year)` (around line 1350)

**Add before prerequisite checks:**

```python
# Print checklist-style input sources
print("\n" + "="*70)
print(f"STEP 2: UPDATE MODFLOW - YEAR {target_year}")
print("="*70)
print(f"📋 Input Sources:")
print(f"  - Source year: {config.source_year}")
if target_year == BASELINE_YEAR:
    print(f"  - Mode: BASELINE (using 2023 input files)")
    print(f"  - WEL file: {config.input_wel_path}")
else:
    print(f"  - Mode: CHAINED (using {config.source_year} outputs)")
    print(f"  - WEL file: {config.input_wel_path}")
print(f"  - Table 2: {config.table2_csv_path}")

print("\n📦 Outputs (after completion):")
print(f"  - thruCY2165_{target_year}.wel (extended well file)")
print(f"  - CY{target_year}.nam (MODFLOW name file)")
print(f"  - 10 baseline files copied from 2023")

print("\n➡️  Next Step (MANUAL):")
print(f"  cd output/modflow/{target_year}")
print(f"  wine modflow96.exe CY{target_year}.nam")
print(f"  wine sfmodflx_2245.exe  # Enter CY{target_year} when prompted")
print("="*70 + "\n")
```

#### 3.1.3 Enhance step3_generate_depletion_tables.py

**File:** `step3_generate_depletion_tables.py`
**Function:** `check_prerequisites()` (lines 745-810)

**Add at start of function, after line 760:**

```python
# Print checklist-style directory structure detection
print("\n" + "="*70)
print(f"STEP 3: GENERATE DEPLETION TABLES - YEAR {year}")
print("="*70)

# Detect structure
if year <= 2024:
    structure = "NESTED (output/modflow/{year}/modflow/)"
else:
    structure = "FLAT (output/modflow/{year}/)"
print(f"📋 Directory Structure: {structure}")
print(f"  - MODFLOW output: {modflow_dir}")
print(f"  - Depletions dir: {depletions_dir}")

# Check file sizes
import os
print(f"\n📋 Flux Files:")
riv_path = modflow_dir / riv_flux
ghb_path = modflow_dir / ghb_flux
if riv_path.exists() and ghb_path.exists():
    riv_size = os.path.getsize(riv_path) / (1024*1024)
    ghb_size = os.path.getsize(ghb_path) / (1024*1024)
    print(f"  ✓ {riv_flux}: {riv_size:.1f} MB")
    print(f"  ✓ {ghb_flux}: {ghb_size:.1f} MB")
else:
    print(f"  ⚠ Flux files not found (will fail later)")

print("\n📦 Outputs (after completion):")
print(f"  - TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx")
print(f"  - TABLE_4_Rio_Grande_Otowi_{year}.xlsx")
print(f"  - TABLE_5_La_Cienega_Springs_{year}.xlsx")

print("\n➡️  Next Step:")
print(f"  python3 verify_workflow.py --year {year}")
print("="*70 + "\n")
```

#### 3.1.4 Add NAM File Reference Verification

**File:** `step2_update_modflow.py`
**Location:** Add new function after `generate_nam_file()` (around line 650)

```python
def verify_nam_file_references(nam_path: str, output_dir: str) -> bool:
    """
    Verify all files referenced in .nam file exist.

    Scientific basis: MODFLOW96 requires all package files referenced in the
    name file to exist in the same directory for successful model execution.

    Assumptions:
        1. NAM file follows MODFLOW96 format (PACKAGE_CODE UNIT filename)
        2. All referenced files should be in output_dir
        3. Comment lines start with '#'

    Args:
        nam_path: Path to generated .nam file
        output_dir: Directory where referenced files should exist

    Returns:
        True if all files exist, False otherwise

    Raises:
        None (returns False for missing files)

    Example:
        >>> verify_nam_file_references("output/modflow/2025/CY2025.nam", "output/modflow/2025")
        ✓ NAM file verified: all 8 referenced files exist
        True
    """
    from pathlib import Path

    nam_file = Path(nam_path)
    output_path = Path(output_dir)

    if not nam_file.exists():
        print(f"✗ NAM file not found: {nam_path}")
        return False

    referenced_files = []
    missing_files = []

    with open(nam_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and blank lines
            if not line or line.startswith('#'):
                continue
            # Extract filename from MODFLOW package lines (format: "PACKAGE_CODE UNIT filename")
            parts = line.split()
            if len(parts) >= 3:
                filename = parts[2]
                referenced_files.append(filename)
                file_path = output_path / filename
                if not file_path.exists():
                    missing_files.append(filename)

    if missing_files:
        print(f"\n✗ NAM file references {len(missing_files)} missing file(s):")
        for f in missing_files:
            print(f"    - {f}")
        print(f"  Total referenced: {len(referenced_files)}")
        return False

    print(f"  ✓ NAM file verified: all {len(referenced_files)} referenced files exist")
    return True
```

**Call this function in `main()`** after `generate_nam_file()` call (around line 1410):
```python
# After generating NAM file
print(f"\n[8/8] Verifying NAM file references...")
verify_nam_file_references(output_nam, config.output_dir)
```

---

### 3.2 Create verify_workflow.py Script (Automated Testing Integration)

**Approach:** Standalone verification script

**Rationale (Senior Dev Perspective):**
- Centralized verification (one command after workflow completes)
- Runs pytest + custom verification scripts
- Doesn't slow down individual steps
- Clear pass/fail summary
- Can verify specific steps or entire year
- Can be integrated into CI/CD later
- Best balance of convenience vs performance

**File:** `verify_workflow.py` (NEW)

```python
#!/usr/bin/env python3
"""
Comprehensive workflow verification for Buckman wellfield depletion analysis.

Verifies that all outputs exist and are valid for a given year's workflow.
Runs pytest tests and custom verification scripts to ensure data quality.

Usage:
    python3 verify_workflow.py --year 2025
    python3 verify_workflow.py --year 2025 --step 1  # Verify specific step only
    python3 verify_workflow.py --year 2025 --verbose  # Show detailed output

Scientific basis: Verification ensures workflow outputs meet data quality
standards and computational accuracy requirements for regulatory reporting.

Assumptions:
    1. Workflow steps 1-3 have been completed for the target year
    2. pytest and all dependencies are installed
    3. Verification scripts (verify_modflow_run.py, verify_depletion.py) exist
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print('='*70)


def check_file_exists(filepath: str, description: str) -> bool:
    """
    Check if a file exists and print status.

    Args:
        filepath: Path to file to check
        description: Human-readable description

    Returns:
        True if file exists, False otherwise
    """
    exists = Path(filepath).exists()
    status = "✓" if exists else "✗"
    size = ""
    if exists:
        size_bytes = Path(filepath).stat().st_size
        if size_bytes > 1024*1024:
            size = f" ({size_bytes / (1024*1024):.1f} MB)"
        elif size_bytes > 1024:
            size = f" ({size_bytes / 1024:.1f} KB)"
    print(f"  {status} {description}: {filepath}{size}")
    return exists


def verify_step1(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 1 outputs (Tables 1-2).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 1: INGEST PUMPING DATA - {year}")

    checks_passed = 0
    total_checks = 0

    # Check output files exist
    files = [
        (f"output/ingested_data/{year}_Table_1_updated.xlsx", "Table 1 (Excel)"),
        (f"output/ingested_data/{year}_Table_1_updated.csv", "Table 1 (CSV)"),
        (f"output/ingested_data/{year}_Table_2_output.xlsx", "Table 2 (Excel)"),
        (f"output/ingested_data/{year}_Table_2_output.csv", "Table 2 (CSV)"),
    ]

    # Check monthly files
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for i, month in enumerate(months, 1):
        files.append((f"output/ingested_data/{year}_{i:02d}_{month}.csv",
                     f"Monthly data: {month}"))

    print("\n📋 File Checks:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_ingest_buckman_data.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_ingest_buckman_data.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_ingest_buckman_data.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 1 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def verify_step2(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 2 outputs (MODFLOW input files).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 2: UPDATE MODFLOW - {year}")

    checks_passed = 0
    total_checks = 0

    # Determine directory structure
    if year <= 2024:
        modflow_dir = f"output/modflow/{year}/modflow"
    else:
        modflow_dir = f"output/modflow/{year}"

    # Check MODFLOW input files
    files = [
        (f"{modflow_dir}/thruCY2165_{year}.wel", "WEL file"),
        (f"{modflow_dir}/CY{year}.nam", "NAM file"),
        (f"{modflow_dir}/modflow96.exe", "MODFLOW96 executable"),
        (f"{modflow_dir}/sflcs.bcf", "BCF package"),
        (f"{modflow_dir}/sflcs.sip", "SIP solver"),
        (f"{modflow_dir}/thruCY2165.bas", "BAS package"),
        (f"{modflow_dir}/thruCY2165.ghb", "GHB package"),
        (f"{modflow_dir}/thruCY2165.oc", "OC package"),
        (f"{modflow_dir}/thruCY2165.riv", "RIV package"),
        (f"{modflow_dir}/sfmodflx_2245.exe", "Post-processor"),
        (f"{modflow_dir}/verify_modflow_run.py", "Verification script"),
        (f"{modflow_dir}/verify_depletion.py", "Depletion verification"),
    ]

    print("\n📋 File Checks:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_update_modflow.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_update_modflow.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_update_modflow.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 2 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def verify_step3(year: int, verbose: bool = False) -> Tuple[bool, int, int]:
    """
    Verify Step 3 outputs (Tables 3-5 and MODFLOW outputs).

    Args:
        year: Year to verify
        verbose: Print detailed output

    Returns:
        Tuple of (success, passed_count, total_count)
    """
    print_section(f"STEP 3: GENERATE DEPLETION TABLES - {year}")

    checks_passed = 0
    total_checks = 0

    # Determine directory structure
    if year <= 2024:
        modflow_dir = f"output/modflow/{year}/modflow"
    else:
        modflow_dir = f"output/modflow/{year}"

    # Check depletion table outputs
    files = [
        (f"output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx", "Table 3"),
        (f"output/depletion/TABLE_4_Rio_Grande_Otowi_{year}.xlsx", "Table 4"),
        (f"output/depletion/TABLE_5_La_Cienega_Springs_{year}.xlsx", "Table 5"),
    ]

    # Check MODFLOW outputs (should exist if step 3 ran)
    modflow_files = [
        (f"{modflow_dir}/CY{year}.lst", "MODFLOW list file"),
        (f"{modflow_dir}/CY{year}_riv.flx", "River flux output"),
        (f"{modflow_dir}/CY{year}_ghb.flx", "GHB flux output"),
        (f"{modflow_dir}/CY{year}_dep", "Depletion file"),
    ]

    print("\n📋 Depletion Tables:")
    for filepath, description in files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    print("\n📋 MODFLOW Outputs:")
    for filepath, description in modflow_files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1

    # Run pytest tests
    print("\n🧪 Running Tests:")
    test_result = subprocess.run(
        ["pytest", "tests/test_generate_depletion_tables.py", "-v", "--tb=short"],
        capture_output=not verbose,
        text=True
    )
    total_checks += 1
    if test_result.returncode == 0:
        print("  ✓ pytest: test_generate_depletion_tables.py PASSED")
        checks_passed += 1
    else:
        print("  ✗ pytest: test_generate_depletion_tables.py FAILED")
        if verbose and test_result.stdout:
            print(test_result.stdout)

    # Run custom verification scripts if they exist
    verify_modflow_script = Path(modflow_dir) / "verify_modflow_run.py"
    if verify_modflow_script.exists():
        print(f"\n🔍 Running Custom Verification:")
        result = subprocess.run(
            ["python3", str(verify_modflow_script), str(year)],
            capture_output=not verbose,
            text=True,
            cwd=modflow_dir
        )
        total_checks += 1
        if result.returncode == 0:
            print("  ✓ verify_modflow_run.py PASSED")
            checks_passed += 1
        else:
            print("  ✗ verify_modflow_run.py FAILED")
            if verbose and result.stdout:
                print(result.stdout)

    success = checks_passed == total_checks
    print(f"\n📊 Step 3 Summary: {checks_passed}/{total_checks} checks passed")
    return success, checks_passed, total_checks


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Buckman wellfield depletion workflow outputs"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to verify (e.g., 2025)"
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="Verify only specific step (default: all steps)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed test output"
    )

    args = parser.parse_args()

    print_section(f"BUCKMAN WORKFLOW VERIFICATION - YEAR {args.year}")

    total_passed = 0
    total_checks = 0
    steps_run = []

    if args.step is None or args.step == 1:
        success, passed, total = verify_step1(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 1", success))

    if args.step is None or args.step == 2:
        success, passed, total = verify_step2(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 2", success))

    if args.step is None or args.step == 3:
        success, passed, total = verify_step3(args.year, args.verbose)
        total_passed += passed
        total_checks += total
        steps_run.append(("Step 3", success))

    # Print final summary
    print_section(f"FINAL SUMMARY - YEAR {args.year}")
    for step_name, success in steps_run:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {step_name}")

    print(f"\n📊 Overall: {total_passed}/{total_checks} checks passed")

    if total_passed == total_checks:
        print("\n🎉 All verifications passed!")
        return 0
    else:
        print(f"\n⚠️  {total_checks - total_passed} verification(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Phase 4: Documentation Enhancements

### 4.1 Create FILE_DEPENDENCIES.md

**File:** `docs/FILE_DEPENDENCIES.md` (NEW)

See original plan for full content - includes visual ASCII diagram of year-to-year file flow.

### 4.2 Update BUCKMAN_WORKFLOW.md

**File:** `docs/BUCKMAN_WORKFLOW.md`

Add new section after existing workflow steps:

```markdown
## File Dependency Chain

The workflow chains years together - each year depends on outputs from the previous year.

### First Year (2024 Baseline)
- Uses 2023 baseline files from `input/modflow/2023/`
- Table 1 starts from validation template
- Creates foundation for all subsequent years

### Subsequent Years (2025+)
- WEL file: Extends from year N-1 output
- Table 1: Extends from year N-1 output (if no validation file)
- Baseline files: Copied fresh from 2023 baseline

**Important:** Always process years sequentially (2024 → 2025 → 2026, etc.)

### Troubleshooting Missing Files

| Error | Cause | Solution |
|-------|-------|----------|
| "Input .wel file not found" | Year N-1 not processed | Run step2 for year N-1 first |
| "Table 2 CSV not found" | Step 1 not run | Run step1 for current year |
| "No template found for Table 1" | Missing validation file AND year N-1 not processed | Create validation file OR run year N-1 first |
| "Flux file not found" | MODFLOW96 not run | Run MODFLOW96 with CY{year}.nam |

### Verification

After completing all steps for a year, run:

```bash
python3 verify_workflow.py --year 2025
```

This will:
- Check all output files exist
- Run pytest test suite
- Run custom verification scripts
- Provide pass/fail summary

See `docs/FILE_DEPENDENCIES.md` for visual diagram.
```

### 4.3 Create NEW_YEAR_CHECKLIST.md

**File:** `docs/NEW_YEAR_CHECKLIST.md` (NEW)

**Purpose:** Comprehensive manual reference (not automated)

See original plan for full content - provides step-by-step checklist for processing new years.

---

## Phase 5: Testing Plan

### 5.1 Run Existing Test Suite

```bash
pytest tests/ -v --tb=short
```

**Tests to verify:**
- `tests/test_ingest_buckman_data.py` - Step 1 smoke tests
- `tests/test_update_modflow.py` - Step 2 tests
- `tests/test_generate_depletion_tables.py` - Step 3 tests
- `tests/test_stream_depletions.py` - Library function tests

### 5.2 Manual Workflow Verification

**Test 1: Verify enhanced logging works**
```bash
# Re-run step1 for 2025 and check enhanced output
python3 step1_ingest_buckman_data.py --year 2025
# Should see: Table 1 template source, outputs, next steps
```

**Test 2: Verify verify_workflow.py**
```bash
# Test full verification
python3 verify_workflow.py --year 2025

# Test specific step
python3 verify_workflow.py --year 2025 --step 3

# Test verbose mode
python3 verify_workflow.py --year 2025 --verbose
```

**Test 3: Verify NAM file reference check**
```bash
# Re-run step2 and check NAM verification
python3 step2_update_modflow.py --year 2025
# Should see: "✓ NAM file verified: all X referenced files exist"
```

---

## Summary of Changes

### Code Modifications

1. **step1_ingest_buckman_data.py**
   - Enhanced `check_prerequisites()` - add checklist-style logging
   - Location: lines 1674-1704, add ~25 lines before `return True`

2. **step2_update_modflow.py**
   - Enhanced prerequisite logging in `main()` - add input source reporting
   - Location: around line 1350, add ~15 lines after `get_year_config()`
   - New function: `verify_nam_file_references()` - verify NAM file integrity
   - Location: after line 650, add ~60 line function
   - Call verification in `main()` after NAM generation
   - Location: around line 1410, add 2 lines

3. **step3_generate_depletion_tables.py**
   - Enhanced `check_prerequisites()` - add directory structure detection
   - Location: lines 745-810, add ~25 lines after line 760

### New Files

1. **verify_workflow.py** - Comprehensive verification script (~300 lines)
2. **docs/FILE_DEPENDENCIES.md** - Visual file flow diagram
3. **docs/NEW_YEAR_CHECKLIST.md** - Step-by-step manual reference

### Updated Files

1. **docs/BUCKMAN_WORKFLOW.md** - Add file dependency + verification sections

---

## Updated Workflow (After Implementation)

```bash
# For year 2025:

# Step 1: Ingest pumping data
python3 step1_ingest_buckman_data.py --year 2025
# NEW: Prints prerequisites, Table 1 source, outputs, next steps

# Step 2: Generate MODFLOW inputs
python3 step2_update_modflow.py --year 2025
# NEW: Prints input sources, chaining mode, outputs, next steps
# NEW: Verifies NAM file references

# Step 3: Manual MODFLOW execution (unchanged)
cd output/modflow/2025
wine modflow96.exe CY2025.nam
wine sfmodflx_2245.exe  # Enter CY2025 when prompted

# Step 4: Generate depletion tables
cd ../../..
python3 step3_generate_depletion_tables.py --year 2025
# NEW: Prints directory structure, flux file sizes, next steps

# Step 5: Comprehensive verification (NEW!)
python3 verify_workflow.py --year 2025
# Runs all tests, checks all outputs, prints summary
```

---

## Benefits

1. **Transparency:** Users see which files are being used at each step
2. **Debuggability:** Clear messages point to missing dependencies
3. **Automation:** Single command to verify entire workflow
4. **Documentation:** Visual diagrams + checklists for reference
5. **Maintainability:** Centralized verification logic
6. **No Breaking Changes:** All enhancements are additive
7. **Performance:** Verification is optional (doesn't slow down workflow)

---

## Implementation Priority

**High Priority (Immediate Value):**
1. Enhanced prerequisite checks (step1, step2, step3) - Provides immediate clarity
2. `verify_workflow.py` script - Automates testing workflow

**Medium Priority (Documentation):**
3. `FILE_DEPENDENCIES.md` - Visual reference
4. Update `BUCKMAN_WORKFLOW.md` - Add verification section

**Low Priority (Reference):**
5. `NEW_YEAR_CHECKLIST.md` - Manual checklist for first-time users

---

## Senior Developer Design Decisions

### Decision 1: Checklist Integration
**Chosen:** Hybrid (documentation + enhanced prerequisite checks)
**Rejected:** Orchestrator script (hides details, loses step control)
**Rejected:** `--check` flag (extra complexity, bifurcates UX)

### Decision 2: Test Integration
**Chosen:** Standalone `verify_workflow.py` script
**Rejected:** Auto-run tests in each step (too slow)
**Rejected:** `--verify` flags (users skip to save time)
**Rejected:** Keep separate (users forget to test)

### Decision 3: MODFLOW Automation
**Chosen:** Keep manual (user maintains control + visibility)
**Future consideration:** Could add optional `--run-modflow` flag later
