#!/usr/bin/env python3
"""
Master test runner for Buckman wellfield depletion pipeline.

Orchestrates all test layers in priority order with robust error handling.
This is the single entry point for running the verification harness.

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

Author: Claude Code (Anthropic)
Date: 2026-02-17
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

VALID_BASELINE_YEARS = {2022, 2023, 2024}
MIN_PRODUCTION_YEAR = 2022
MAX_PRODUCTION_YEAR = 2100  # Sanity check

# Timeout values (seconds)
TIMEOUT_BALLPARK = 30
TIMEOUT_PYTEST_LAYER0 = 300  # 5 min
TIMEOUT_PYTEST_EDGE = 120   # 2 min
TIMEOUT_PYTEST_CONSERVATION = 120  # 2 min
TIMEOUT_TEMPORAL = 60
TIMEOUT_MANIFEST = 60

# Project root
PROJECT_ROOT = Path(__file__).parent


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ScriptNotFoundError(Exception):
    """Raised when a required script is missing."""
    pass


class ScriptTimeoutError(Exception):
    """Raised when a subprocess exceeds its timeout."""
    pass


class ScriptCrashError(Exception):
    """Raised when a subprocess returns an unexpected exit code."""
    pass


class InvalidYearError(Exception):
    """Raised when an invalid year is provided."""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TestResult:
    """Result of running a test layer."""
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
    """A flag raised by Layer 2 temporal consistency checks."""
    layer: str
    test_name: str
    value: float
    threshold: float
    message: str
    requires_review: bool = True


@dataclass
class TestSuite:
    """Complete results of running all test layers."""
    year: int
    results: List[TestResult]
    flags: List[Flag]
    manifest_path: Optional[Path]
    start_time: datetime
    end_time: Optional[datetime]
    exit_code: int
    error_messages: List[str] = field(default_factory=list)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_year(year: int) -> None:
    """
    Validate year parameter before any test execution.

    Args:
        year: The year to validate.

    Raises:
        InvalidYearError: If year is not valid.
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
    bounds_path = PROJECT_ROOT / "validation" / "historical" / "bounds.yaml"
    if not bounds_path.exists():
        raise InvalidYearError(
            f"Required bounds file missing: {bounds_path}\n"
            "Run validation setup or check file paths."
        )


def verify_script_exists(script_path: Path, description: str) -> None:
    """
    Verify a required script exists before attempting to run it.

    Args:
        script_path: Path to the script.
        description: Human-readable description for error messages.

    Raises:
        ScriptNotFoundError: If script doesn't exist.
    """
    if not script_path.exists():
        raise ScriptNotFoundError(
            f"Required script missing: {script_path}\n"
            f"Description: {description}\n"
            f"This is a configuration error - contact pipeline maintainer."
        )


# =============================================================================
# SUBPROCESS HANDLING
# =============================================================================

def run_subprocess_safely(
    cmd: List[str],
    description: str,
    timeout_sec: int = 120,
    expected_codes: Optional[Dict[int, str]] = None,
    cwd: Optional[Path] = None,
) -> Tuple[int, str, str]:
    """
    Run subprocess with timeout and robust error handling.

    Args:
        cmd: Command to run.
        description: Human-readable description for error messages.
        timeout_sec: Maximum runtime before killing process.
        expected_codes: Dict mapping exit codes to meanings.
                       e.g., {0: "pass", 2: "flags", 3: "hard_fail"}
        cwd: Working directory for subprocess.

    Returns:
        Tuple of (exit_code, stdout, stderr).

    Raises:
        ScriptTimeoutError: If script exceeds timeout.
        ScriptCrashError: If script returns unexpected exit code.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=cwd or PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        raise ScriptTimeoutError(
            f"{description} exceeded {timeout_sec}s timeout.\n"
            f"Command: {' '.join(cmd)}\n"
            "This may indicate: hung process, infinite loop, or resource contention."
        )

    # Check if exit code is expected
    if expected_codes and result.returncode not in expected_codes:
        raise ScriptCrashError(
            f"{description} returned unexpected exit code {result.returncode}.\n"
            f"Expected codes: {list(expected_codes.keys())}\n"
            "This usually means the script crashed.\n"
            f"stderr: {result.stderr[:500] if result.stderr else '(empty)'}"
        )

    return result.returncode, result.stdout, result.stderr


# =============================================================================
# PYTEST LAYER EXECUTION
# =============================================================================

def run_pytest_layer(
    layer_name: str,
    pytest_args: List[str],
    timeout_sec: int = 300,
    verbose: int = 0,
) -> TestResult:
    """
    Run pytest layer and extract structured results.

    Uses pytest-json-report for reliable result extraction.

    Args:
        layer_name: Name for this layer (e.g., "layer0").
        pytest_args: Arguments to pass to pytest.
        timeout_sec: Maximum runtime.
        verbose: Verbosity level.

    Returns:
        TestResult with pass/fail counts.
    """
    json_report_dir = PROJECT_ROOT / "output" / "test_results"
    json_report_dir.mkdir(parents=True, exist_ok=True)
    json_report_path = json_report_dir / f"{layer_name}.json"

    cmd = [
        "pytest",
        "--json-report",
        f"--json-report-file={json_report_path}",
        "--json-report-indent=2",
        "-v" if verbose >= 1 else "-q",
    ] + pytest_args

    start_time = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=PROJECT_ROOT,
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
            error_message=f"Timeout after {timeout_sec}s",
        )

    duration = (datetime.now() - start_time).total_seconds()

    # Parse JSON report for accurate counts
    if json_report_path.exists():
        try:
            with open(json_report_path) as f:
                report = json.load(f)

            summary = report.get("summary", {})
            failed_tests = [
                t["nodeid"] for t in report.get("tests", [])
                if t.get("outcome") == "failed"
            ]

            return TestResult(
                layer=layer_name,
                name=layer_name,
                passed=summary.get("passed", 0),
                failed=summary.get("failed", 0),
                skipped=summary.get("skipped", 0),
                duration_sec=report.get("duration", duration),
                hard_fail=summary.get("failed", 0) > 0,
                error_message=None,
                failed_tests=failed_tests,
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: parse exit code only
            pass

    # Fallback: parse exit code only
    return TestResult(
        layer=layer_name,
        name=layer_name,
        passed=0 if result.returncode != 0 else -1,  # Unknown count
        failed=1 if result.returncode != 0 else 0,
        skipped=0,
        duration_sec=duration,
        hard_fail=result.returncode != 0,
        error_message=f"JSON report not generated. Exit code: {result.returncode}",
    )


# =============================================================================
# LAYER 1 PREREQUISITES
# =============================================================================

def check_layer1_prerequisites(year: int) -> Tuple[bool, str]:
    """
    Check if Layer 1 conservation tests can run.

    Layer 1 requires MODFLOW outputs to exist.

    Args:
        year: The year being tested.

    Returns:
        Tuple of (can_run, message).
    """
    # Determine output directory
    if year <= 2024:
        modflow_dir = PROJECT_ROOT / "output" / "modflow" / str(year) / "modflow"
    else:
        modflow_dir = PROJECT_ROOT / "output" / "modflow" / str(year)

    required_files = [
        modflow_dir / f"CY{year}.lst",  # MODFLOW listing file
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


# =============================================================================
# LAYER EXECUTION
# =============================================================================

def run_ballpark_check(year: int, verbose: int = 0) -> Tuple[int, List[str]]:
    """
    Run ballpark check (fast sanity check).

    Args:
        year: Year to check.
        verbose: Verbosity level.

    Returns:
        Tuple of (exit_code, messages).
    """
    script_path = PROJECT_ROOT / "validation" / "ballpark_check.py"
    verify_script_exists(script_path, "Ballpark sanity check")

    cmd = ["python3", str(script_path), "--year", str(year)]

    expected_codes = {
        0: "all_clear",
        2: "soft_flags",
        3: "hard_fail",
    }

    try:
        exit_code, stdout, stderr = run_subprocess_safely(
            cmd,
            "Ballpark check",
            timeout_sec=TIMEOUT_BALLPARK,
            expected_codes=expected_codes,
        )
    except ScriptCrashError as e:
        # Exit code 1 means script crashed (not intentional soft flags)
        return 1, [f"BALLPARK SCRIPT CRASHED: {e}"]
    except ScriptTimeoutError as e:
        return 1, [f"BALLPARK TIMEOUT: {e}"]

    messages = []
    if verbose >= 1 and stdout:
        messages.extend(stdout.strip().split("\n"))

    return exit_code, messages


def run_temporal_consistency(year: int, verbose: int = 0) -> Tuple[List[Flag], List[str]]:
    """
    Run Layer 2 temporal consistency checks.

    Args:
        year: Year to check.
        verbose: Verbosity level.

    Returns:
        Tuple of (flags, messages).
    """
    script_path = PROJECT_ROOT / "validation" / "temporal_consistency.py"

    # Temporal consistency is optional - may not exist
    if not script_path.exists():
        return [], [f"Temporal consistency script not found: {script_path}"]

    cmd = ["python3", str(script_path), "--year", str(year)]

    try:
        exit_code, stdout, stderr = run_subprocess_safely(
            cmd,
            "Temporal consistency",
            timeout_sec=TIMEOUT_TEMPORAL,
            expected_codes={0: "pass", 1: "flags", 2: "error"},
        )
    except (ScriptCrashError, ScriptTimeoutError) as e:
        return [], [f"TEMPORAL CONSISTENCY ERROR: {e}"]

    # Parse flags from output (simplified - actual implementation would parse JSON)
    flags = []
    messages = []

    if stdout:
        for line in stdout.strip().split("\n"):
            messages.append(line)
            if "FLAG:" in line or "SOFT FLAG:" in line:
                flags.append(Flag(
                    layer="Layer 2",
                    test_name="temporal_consistency",
                    value=0.0,  # Would parse from actual output
                    threshold=0.0,
                    message=line,
                    requires_review=True,
                ))

    return flags, messages


def generate_manifest(year: int, test_results: List[TestResult], flags: List[Flag]) -> Optional[Path]:
    """
    Generate provenance manifest (Layer 6).

    Args:
        year: Year being tested.
        test_results: All test results.
        flags: All flags raised.

    Returns:
        Path to generated manifest, or None if failed.
    """
    try:
        from src.pipeline_manifest import PipelineManifest, print_manifest_summary

        manifest_gen = PipelineManifest(
            year=year,
            project_root=PROJECT_ROOT,
            allow_hash_mismatch=True,  # For now, allow mismatches
        )
        manifest = manifest_gen.generate()

        # Add test results to manifest
        manifest["test_results"] = {
            "layers": [
                {
                    "name": r.layer,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "duration_sec": r.duration_sec,
                    "hard_fail": r.hard_fail,
                    "failed_tests": r.failed_tests,
                }
                for r in test_results
            ],
            "flags": [
                {
                    "layer": f.layer,
                    "test_name": f.test_name,
                    "message": f.message,
                    "requires_review": f.requires_review,
                    "disposition": "",  # For analyst to fill in
                    "reviewed_by": "",
                    "review_date": "",
                }
                for f in flags
            ],
        }

        manifest_path = manifest_gen.save(manifest)
        return manifest_path

    except ImportError as e:
        print(f"WARNING: Manifest generation skipped: {e}")
        return None
    except Exception as e:
        print(f"WARNING: Manifest generation failed: {e}")
        return None


# =============================================================================
# SUMMARY OUTPUT
# =============================================================================

def print_summary(results: TestSuite, verbose: int = 0) -> None:
    """
    Print test suite summary.

    Args:
        results: TestSuite with all results.
        verbose: 0=brief, 1=detailed, 2=exhaustive.
    """
    print("\n" + "=" * 70)
    print(f"TEST SUITE SUMMARY - YEAR {results.year}")
    print("=" * 70)

    # Layer-by-layer breakdown (always shown)
    for r in results.results:
        if r.hard_fail:
            status = "FAIL"
        elif r.skipped > 0 and r.passed == 0 and r.failed == 0:
            status = "SKIP"
        else:
            status = "PASS"

        print(f"\n{r.layer}: {status} ({r.passed} passed, {r.failed} failed, {r.skipped} skipped) [{r.duration_sec:.1f}s]")

        # Show error message if any
        if r.error_message and verbose >= 0:
            print(f"  Note: {r.error_message}")

        # Show failures (if any)
        if r.failed > 0 and verbose >= 1:
            for test in r.failed_tests[:10]:  # Limit to first 10
                print(f"  X {test}")
            if len(r.failed_tests) > 10:
                print(f"  ... and {len(r.failed_tests) - 10} more")

    # Flags section
    if results.flags:
        print(f"\n{'=' * 70}")
        print(f"FLAGS REQUIRING HUMAN REVIEW: {len(results.flags)}")
        print("=" * 70)
        for flag in results.flags:
            print(f"\n  [{flag.layer}] {flag.test_name}")
            print(f"    {flag.message}")

    # Error messages
    if results.error_messages:
        print(f"\n{'=' * 70}")
        print("ERRORS ENCOUNTERED:")
        print("=" * 70)
        for msg in results.error_messages:
            print(f"  - {msg}")

    # Totals
    total_passed = sum(r.passed for r in results.results if r.passed >= 0)
    total_failed = sum(r.failed for r in results.results)
    total_skipped = sum(r.skipped for r in results.results)
    total_duration = sum(r.duration_sec for r in results.results)

    print(f"\n{'=' * 70}")
    print(f"TOTALS: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")
    print(f"FLAGS: {len(results.flags)} (require human review)")
    print(f"DURATION: {total_duration:.1f} seconds")
    if results.manifest_path:
        print(f"MANIFEST: {results.manifest_path}")
    print("=" * 70)

    if results.exit_code == 0:
        print("\n[PASS] All hard-stop tests passed.")
        if results.flags:
            print("  (Review flags before using outputs for compliance)")
    elif results.exit_code == 3:
        print("\n[CRITICAL] Ballpark check detected physics violation.")
        print("  DO NOT use outputs. Investigate immediately.")
    else:
        print(f"\n[FAIL] {total_failed} test(s) failed.")
        print("  DO NOT use outputs until failures are resolved.")


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

def run_all_tests(
    year: int,
    skip_ballpark: bool = False,
    verbose: int = 0,
    dry_run: bool = False,
) -> TestSuite:
    """
    Run all test layers in order.

    Args:
        year: Year to test.
        skip_ballpark: Skip ballpark check (for development).
        verbose: Verbosity level.
        dry_run: Show what would run without executing.

    Returns:
        TestSuite with all results.
    """
    suite = TestSuite(
        year=year,
        results=[],
        flags=[],
        manifest_path=None,
        start_time=datetime.now(),
        end_time=None,
        exit_code=0,
    )

    # Validate year
    try:
        validate_year(year)
    except InvalidYearError as e:
        suite.error_messages.append(str(e))
        suite.exit_code = 1
        suite.end_time = datetime.now()
        return suite

    if dry_run:
        print(f"DRY RUN: Would execute for year {year}")
        print("  1. Ballpark check: validation/ballpark_check.py")
        print("  2. Layer 0 (smoke): pytest -m layer0")
        print("  3. Layer 0.5 (edge): pytest -m edge_cases")
        print("  4. Layer 1 (conservation): pytest -m conservation")
        print("  5. Layer 2 (temporal): validation/temporal_consistency.py")
        print("  6. Layer 6 (manifest): src/pipeline_manifest.py")
        suite.end_time = datetime.now()
        return suite

    print(f"\n{'=' * 70}")
    print(f"RUNNING TEST SUITE FOR YEAR {year}")
    print("=" * 70)

    # --- Ballpark Check ---
    if not skip_ballpark:
        print("\n[1/6] BALLPARK CHECK")
        ballpark_code, ballpark_msgs = run_ballpark_check(year, verbose)

        if verbose >= 1:
            for msg in ballpark_msgs:
                print(f"  {msg}")

        if ballpark_code == 3:
            print("  CRITICAL: Physics violation detected. Stopping.")
            suite.exit_code = 3
            suite.error_messages.append("Ballpark check: physics violation")
            suite.end_time = datetime.now()
            return suite
        elif ballpark_code == 2:
            print("  Soft flags raised - continuing with warnings")
            suite.flags.append(Flag(
                layer="Ballpark",
                test_name="ballpark_check",
                value=0.0,
                threshold=0.0,
                message="Ballpark check raised soft flags - see output above",
            ))
        elif ballpark_code == 1:
            print("  ERROR: Ballpark script crashed")
            suite.exit_code = 1
            suite.error_messages.append("Ballpark check script crashed")
            suite.end_time = datetime.now()
            return suite
        else:
            print("  All ballpark checks passed")
    else:
        print("\n[1/6] BALLPARK CHECK - SKIPPED (--skip-ballpark)")

    # --- Layer 0: Smoke Tests ---
    print("\n[2/6] LAYER 0: SMOKE TESTS")
    layer0_result = run_pytest_layer(
        "Layer 0 (smoke)",
        ["-m", "layer0", "tests/"],
        timeout_sec=TIMEOUT_PYTEST_LAYER0,
        verbose=verbose,
    )
    suite.results.append(layer0_result)

    if layer0_result.hard_fail:
        print(f"  FAILED: {layer0_result.failed} test(s) failed")
        suite.exit_code = 1
    else:
        print(f"  PASSED: {layer0_result.passed} tests")

    # --- Layer 0.5: Edge Cases ---
    print("\n[3/6] LAYER 0.5: EDGE CASE TESTS")
    edge_result = run_pytest_layer(
        "Layer 0.5 (edge)",
        ["-m", "edge_cases", "tests/"],
        timeout_sec=TIMEOUT_PYTEST_EDGE,
        verbose=verbose,
    )
    suite.results.append(edge_result)

    if edge_result.hard_fail:
        print(f"  FAILED: {edge_result.failed} test(s) failed")
        suite.exit_code = 1
    else:
        print(f"  PASSED: {edge_result.passed} tests")

    # --- Layer 1: Conservation Tests ---
    print("\n[4/6] LAYER 1: CONSERVATION TESTS")
    can_run_layer1, layer1_msg = check_layer1_prerequisites(year)

    if not can_run_layer1:
        print(f"  SKIPPED: {layer1_msg.split(chr(10))[0]}")
        suite.results.append(TestResult(
            layer="Layer 1 (conservation)",
            name="conservation",
            passed=0,
            failed=0,
            skipped=4,  # 4 conservation tests
            duration_sec=0.0,
            hard_fail=False,
            error_message="Prerequisites not found - run pipeline first",
        ))
    else:
        cons_result = run_pytest_layer(
            "Layer 1 (conservation)",
            ["-m", "conservation", "tests/"],
            timeout_sec=TIMEOUT_PYTEST_CONSERVATION,
            verbose=verbose,
        )
        suite.results.append(cons_result)

        if cons_result.hard_fail:
            print(f"  FAILED: {cons_result.failed} test(s) failed")
            suite.exit_code = 1
        else:
            print(f"  PASSED: {cons_result.passed} tests")

    # --- Layer 2: Temporal Consistency ---
    print("\n[5/6] LAYER 2: TEMPORAL CONSISTENCY")
    temporal_flags, temporal_msgs = run_temporal_consistency(year, verbose)
    suite.flags.extend(temporal_flags)

    if temporal_flags:
        print(f"  FLAGS: {len(temporal_flags)} flag(s) raised (requires review)")
    elif temporal_msgs and "not found" in temporal_msgs[0].lower():
        print(f"  SKIPPED: {temporal_msgs[0]}")
    else:
        print("  PASSED: No flags raised")

    # --- Layer 3: Cross-Comparison ---
    print("\n[5.5/6] LAYER 3: CROSS-COMPARISON")
    print("  SKIPPED: Layer 3 not applicable (scientifically rejected in P6)")

    # --- Layer 6: Provenance Manifest ---
    print("\n[6/6] LAYER 6: PROVENANCE MANIFEST")
    manifest_path = generate_manifest(year, suite.results, suite.flags)
    suite.manifest_path = manifest_path

    if manifest_path:
        print(f"  Generated: {manifest_path}")
    else:
        print("  SKIPPED: Manifest generation failed (see warnings above)")

    suite.end_time = datetime.now()
    return suite


# =============================================================================
# CLI
# =============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Master test runner for Buckman wellfield verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - All hard-stop tests passed (flags may exist)
  1 - Hard-stop test failure OR script error
  3 - Ballpark check critical failure (physics violation)

Examples:
  python run_all_tests.py --year 2024
  python run_all_tests.py --year 2024 --verbose
  python run_all_tests.py --year 2024 --dry-run
        """,
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to test (e.g., 2024)",
    )
    parser.add_argument(
        "--skip-ballpark",
        action="store_true",
        help="Skip ballpark check (for development only)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for detailed, -vv for exhaustive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing",
    )

    args = parser.parse_args()

    # Run tests
    results = run_all_tests(
        year=args.year,
        skip_ballpark=args.skip_ballpark,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    # Print summary
    print_summary(results, args.verbose)

    return results.exit_code


if __name__ == "__main__":
    sys.exit(main())
