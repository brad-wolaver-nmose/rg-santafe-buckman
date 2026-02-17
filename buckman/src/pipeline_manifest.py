#!/usr/bin/env python3
"""
Pipeline Manifest Generator for Buckman Wellfield Depletion Pipeline.

Generates provenance and reproducibility metadata as JSON manifest.
Layer 6 of 8-prompt testing framework.

Plain English:
    A single JSON file that proves chain of custody for compliance work.
    Inputs: what data went in (with cryptographic fingerprints).
    Code: what software version produced this (git commit + executable dates).
    QA: what tests passed and what values were checked.
    Audit: when/where it ran, what needs human review.

Usage:
    from src.pipeline_manifest import PipelineManifest, print_manifest_summary

    manifest_gen = PipelineManifest(year=2025, project_root=Path("."))
    manifest = manifest_gen.generate()
    manifest_gen.save(manifest)
    print_manifest_summary(manifest)

Author: Claude Code (Anthropic)
Date: 2026-02-17
"""

import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class HashMismatchError(Exception):
    """Raised when baseline file hashes don't match and override not allowed."""

    pass


@dataclass
class InputFile:
    """Metadata for an input file."""

    name: str
    full_path: str
    sha256: str
    size_bytes: int
    row_count: int | None = None
    date_range: str | None = None


@dataclass
class TestResult:
    """Individual test result."""

    test_name: str
    layer: int | str
    status: str  # "PASS" | "FAIL" | "SKIP"
    value_tested: Any = None
    threshold: Any = None
    timestamp: str = ""


class PipelineManifest:
    """
    Main manifest generator for Buckman Wellfield pipeline.

    Generates comprehensive provenance manifest containing:
    1. INPUT MANIFEST - File metadata with SHA-256 hashes
    2. PIPELINE MANIFEST - Code/executable versioning
    3. TEST RESULTS MANIFEST - Layer 0, 1, ballpark check results
    4. FLAG REGISTER - Placeholder for Layer 2/3 flags
    5. RUN METADATA - Timestamps, runtime, machine info
    """

    MANIFEST_VERSION = "1.0"

    # Pipeline scripts to track
    PIPELINE_SCRIPTS = [
        "step1_ingest_buckman_data.py",
        "step2_update_modflow.py",
        "step3_run_modflow.sh",
        "step4_generate_depletion_tables.py",
        "step5_verify_workflow.py",
        "stream_depletions.py",
    ]

    # MODFLOW template files (relative to input/modflow/2023/)
    MODFLOW_TEMPLATES = [
        "thruCY2165.wel",
        "thruCY2165.bas",
        "thruCY2165.ghb",
        "thruCY2165.riv",
        "thruCY2165.oc",
        "sflcs.bcf",
        "sflcs.sip",
        "CY2023.nam",
    ]

    def __init__(
        self,
        year: int,
        project_root: Path,
        allow_hash_mismatch: bool = False,
    ):
        """
        Initialize manifest generator.

        Args:
            year: Calendar year being processed.
            project_root: Root directory of the Buckman project.
            allow_hash_mismatch: If True, continue even if baseline hashes don't match.
        """
        self.year = year
        self.project_root = Path(project_root).resolve()
        self.allow_hash_mismatch = allow_hash_mismatch
        self.start_time = datetime.now()
        self.end_time: datetime | None = None
        self._hash_mismatches: list[dict] = []

    def generate(self) -> dict:
        """
        Generate complete manifest.

        Returns:
            Dictionary containing all manifest sections.

        Raises:
            HashMismatchError: If baseline hashes don't match and allow_hash_mismatch=False.
        """
        self.end_time = datetime.now()

        manifest = {
            "manifest_version": self.MANIFEST_VERSION,
            "year": self.year,
            "input_manifest": self._collect_input_manifest(),
            "hash_verification": self._verify_baseline_hashes(),
            "pipeline_manifest": self._collect_pipeline_manifest(),
            "test_results_manifest": self._collect_test_results(),
            "flag_register": self._get_flag_register(),
            "run_metadata": self._get_run_metadata(),
        }

        return manifest

    def _compute_sha256(self, filepath: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_csv_row_count(self, filepath: Path) -> int | None:
        """Count rows in CSV file (excluding header)."""
        try:
            with open(filepath) as f:
                return sum(1 for _ in f) - 1
        except Exception:
            return None

    def _get_csv_date_range(self, filepath: Path) -> str | None:
        """Extract date range from pumping CSV."""
        try:
            import pandas as pd

            df = pd.read_csv(filepath)
            # Try common date column names
            date_cols = ["Date", "date", "DATE"]
            for col in date_cols:
                if col in df.columns:
                    dates = pd.to_datetime(df[col], errors="coerce").dropna()
                    if len(dates) > 0:
                        return f"{dates.min().date()} to {dates.max().date()}"
            return None
        except Exception:
            return None

    def _collect_input_manifest(self) -> list[dict]:
        """Collect input file metadata with hashes."""
        inputs = []

        # 1. Raw pumping data for this year
        pumping_csv = self.project_root / f"input/csv/Buckman_Well_Prod_{self.year}.csv"
        if pumping_csv.exists():
            inputs.append(
                asdict(
                    InputFile(
                        name=pumping_csv.name,
                        full_path=str(pumping_csv),
                        sha256=self._compute_sha256(pumping_csv),
                        size_bytes=pumping_csv.stat().st_size,
                        row_count=self._get_csv_row_count(pumping_csv),
                        date_range=self._get_csv_date_range(pumping_csv),
                    )
                )
            )

        # 2. MODFLOW template files
        modflow_dir = self.project_root / "input/modflow/2023"
        for template in self.MODFLOW_TEMPLATES:
            template_path = modflow_dir / template
            if template_path.exists():
                inputs.append(
                    asdict(
                        InputFile(
                            name=template,
                            full_path=str(template_path),
                            sha256=self._compute_sha256(template_path),
                            size_bytes=template_path.stat().st_size,
                        )
                    )
                )

        # 3. Historical baseline files
        historical_dir = self.project_root / "validation/historical"
        for i in range(1, 6):
            hist_file = historical_dir / f"Table_{i}_historical.xlsx"
            if hist_file.exists():
                inputs.append(
                    asdict(
                        InputFile(
                            name=hist_file.name,
                            full_path=str(hist_file),
                            sha256=self._compute_sha256(hist_file),
                            size_bytes=hist_file.stat().st_size,
                        )
                    )
                )

        # 4. Historical bounds.yaml
        bounds_file = historical_dir / "bounds.yaml"
        if bounds_file.exists():
            inputs.append(
                asdict(
                    InputFile(
                        name="bounds.yaml",
                        full_path=str(bounds_file),
                        sha256=self._compute_sha256(bounds_file),
                        size_bytes=bounds_file.stat().st_size,
                    )
                )
            )

        # 5. 2024 regression inputs (if exist)
        regression_input = self.project_root / "validation/2024/inputs/Buckman_Well_Prod_2024.csv"
        if regression_input.exists():
            inputs.append(
                asdict(
                    InputFile(
                        name="Buckman_Well_Prod_2024.csv (regression)",
                        full_path=str(regression_input),
                        sha256=self._compute_sha256(regression_input),
                        size_bytes=regression_input.stat().st_size,
                        row_count=self._get_csv_row_count(regression_input),
                    )
                )
            )

        return inputs

    def _verify_baseline_hashes(self) -> dict:
        """
        Verify historical baseline hashes against stored values.

        Returns:
            Dictionary with verification status and any mismatches.

        Raises:
            HashMismatchError: If mismatches found and allow_hash_mismatch=False.
        """
        hashes_file = self.project_root / "validation/historical/hashes.json"
        historical_dir = self.project_root / "validation/historical"

        if not hashes_file.exists():
            return {
                "status": "SKIPPED",
                "reason": "hashes.json not found",
                "baseline_file": str(hashes_file),
                "files_checked": 0,
                "mismatches": [],
                "override_flag_used": False,
            }

        with open(hashes_file) as f:
            stored_hashes = json.load(f)

        files_data = stored_hashes.get("files", {})
        mismatches = []
        files_checked = 0

        for rel_path, expected_hash in files_data.items():
            file_path = historical_dir / rel_path
            if file_path.exists():
                files_checked += 1
                actual_hash = self._compute_sha256(file_path)
                if actual_hash != expected_hash:
                    mismatches.append(
                        {
                            "file": rel_path,
                            "expected": expected_hash,
                            "actual": actual_hash,
                        }
                    )

        self._hash_mismatches = mismatches

        if mismatches and not self.allow_hash_mismatch:
            mismatch_files = [m["file"] for m in mismatches]
            raise HashMismatchError(
                f"Hash mismatch detected for: {', '.join(mismatch_files)}\n"
                f"Pipeline stopped. To proceed with mismatched hashes:\n"
                f"  python step5_verify_workflow.py --year {self.year} --allow-hash-mismatch\n"
                f"WARNING: Using --allow-hash-mismatch will be logged in manifest."
            )

        if mismatches:
            status = "MISMATCH_ACKNOWLEDGED"
        else:
            status = "VERIFIED"

        return {
            "status": status,
            "baseline_file": str(hashes_file),
            "files_checked": files_checked,
            "mismatches": mismatches,
            "override_flag_used": self.allow_hash_mismatch and len(mismatches) > 0,
        }

    def _collect_pipeline_manifest(self) -> dict:
        """Collect pipeline versioning information."""
        # Git information
        git_commit = "not under version control"
        git_status = "unknown"
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0:
                git_status = "clean" if not result.stdout.strip() else "dirty"
        except FileNotFoundError:
            pass

        # Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Pipeline script modification dates
        scripts = []
        for script_name in self.PIPELINE_SCRIPTS:
            script_path = self.project_root / script_name
            if script_path.exists():
                mtime = datetime.fromtimestamp(script_path.stat().st_mtime)
                scripts.append(
                    {
                        "name": script_name,
                        "modified": mtime.isoformat(),
                    }
                )

        # Executables
        executables = []
        modflow_dir = self.project_root / "input/modflow/2023"

        modflow_exe = modflow_dir / "modflow96.exe"
        if modflow_exe.exists():
            mtime = datetime.fromtimestamp(modflow_exe.stat().st_mtime)
            executables.append(
                {
                    "name": "modflow96.exe",
                    "modified": mtime.isoformat(),
                    "size_bytes": modflow_exe.stat().st_size,
                }
            )

        sfmodflx_exe = modflow_dir / "sfmodflx_2245.exe"
        if sfmodflx_exe.exists():
            mtime = datetime.fromtimestamp(sfmodflx_exe.stat().st_mtime)
            executables.append(
                {
                    "name": "sfmodflx_2245.exe",
                    "modified": mtime.isoformat(),
                    "size_bytes": sfmodflx_exe.stat().st_size,
                }
            )

        return {
            "git_commit": git_commit,
            "git_status": git_status,
            "python_version": python_version,
            "scripts": scripts,
            "executables": executables,
        }

    def _collect_test_results(self) -> dict:
        """Collect test results from Layer 0, Layer 1, and ballpark check."""
        results = {
            "layer_0_smoke": self._run_layer_0_tests(),
            "layer_1_conservation": self._load_layer_1_results(),
            "ballpark_check": self._run_ballpark_check(),
        }
        return results

    def _run_layer_0_tests(self) -> dict:
        """Run pytest smoke tests and capture results."""
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "status": "SKIPPED",
                "reason": "tests/ directory not found",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            result = subprocess.run(
                ["pytest", str(tests_dir), "-v", "--tb=no", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Parse pytest output for pass/fail counts
            # Look for pattern like "152 passed" or "150 passed, 2 failed"
            output = result.stdout + result.stderr
            passed = 0
            failed = 0

            passed_match = re.search(r"(\d+) passed", output)
            if passed_match:
                passed = int(passed_match.group(1))

            failed_match = re.search(r"(\d+) failed", output)
            if failed_match:
                failed = int(failed_match.group(1))

            total = passed + failed

            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "status": "PASS" if failed == 0 else "FAIL",
                "timestamp": datetime.now().isoformat(),
            }
        except FileNotFoundError:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "status": "SKIPPED",
                "reason": "pytest not found",
                "timestamp": datetime.now().isoformat(),
            }

    def _load_layer_1_results(self) -> dict:
        """Load Layer 1 conservation results from JSON file."""
        results_file = self.project_root / f".claude/plans/P3_conservation_results_{self.year}.json"

        if not results_file.exists():
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "status": "SKIPPED",
                "reason": f"P3_conservation_results_{self.year}.json not found",
                "tests": [],
                "timestamp": datetime.now().isoformat(),
            }

        with open(results_file) as f:
            data = json.load(f)

        results = data.get("results", [])
        passed = sum(1 for r in results if r.get("status") == "PASS")
        failed = sum(1 for r in results if r.get("status") == "FAIL")

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "status": "PASS" if failed == 0 else "FAIL",
            "tests": [
                {
                    "test_name": r.get("check_name"),
                    "status": r.get("status"),
                    "value_tested": r.get("actual_value"),
                    "threshold": r.get("tolerance"),
                    "timestamp": r.get("timestamp"),
                }
                for r in results
            ],
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
        }

    def _run_ballpark_check(self) -> dict:
        """Run ballpark check and capture results."""
        ballpark_script = self.project_root / "validation/ballpark_check.py"

        if not ballpark_script.exists():
            return {
                "status": "SKIPPED",
                "reason": "ballpark_check.py not found",
                "hard_fails": 0,
                "soft_flags": 0,
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # Run ballpark check
            result = subprocess.run(
                ["python3", str(ballpark_script), "--year", str(self.year)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Parse output for hard fails and soft flags
            output = result.stdout + result.stderr
            hard_fails = 0
            soft_flags = 0

            # Look for SUMMARY line
            summary_match = re.search(
                r"SUMMARY:\s*(\d+)\s*passed,\s*(\d+)\s*soft flags,\s*(\d+)\s*hard fails",
                output,
            )
            if summary_match:
                soft_flags = int(summary_match.group(2))
                hard_fails = int(summary_match.group(3))

            if result.returncode == 0:
                status = "PASS"
            elif result.returncode == 1:
                status = "SOFT_FLAGS"
            else:
                status = "HARD_FAIL"

            return {
                "status": status,
                "exit_code": result.returncode,
                "hard_fails": hard_fails,
                "soft_flags": soft_flags,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "reason": str(e),
                "hard_fails": 0,
                "soft_flags": 0,
                "timestamp": datetime.now().isoformat(),
            }

    def _get_flag_register(self) -> dict:
        """Return placeholder flag register for Layer 2/3 checks."""
        return {
            "entries": [],
            "note": "Populated by Layer 2 (temporal) and Layer 3 (cross-comparison) checks",
            "entry_format": {
                "test_name": "",
                "flagged_value": None,
                "threshold": None,
                "disposition": "",
                "analyst_initials": "",
                "date": "",
            },
        }

    def _get_run_metadata(self) -> dict:
        """Collect runtime metadata."""
        end = self.end_time or datetime.now()
        runtime_seconds = (end - self.start_time).total_seconds()

        return {
            "pipeline_start": self.start_time.isoformat(),
            "pipeline_end": end.isoformat(),
            "total_runtime_seconds": runtime_seconds,
            "machine_name": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "os_version": platform.version(),
            "python_executable": sys.executable,
        }

    def save(self, manifest: dict) -> Path:
        """
        Save manifest to JSON file.

        Args:
            manifest: Manifest dictionary to save.

        Returns:
            Path to saved manifest file.
        """
        output_dir = self.project_root / "output/manifests"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"buckman_manifest_{self.year}.json"
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2, default=str)

        return output_path


def print_manifest_summary(manifest: dict) -> None:
    """
    Print one-page human-readable summary of manifest.

    Args:
        manifest: Manifest dictionary to summarize.
    """
    year = manifest.get("year", "?")
    run_meta = manifest.get("run_metadata", {})
    pipeline = manifest.get("pipeline_manifest", {})
    inputs = manifest.get("input_manifest", [])
    hash_verify = manifest.get("hash_verification", {})
    tests = manifest.get("test_results_manifest", {})
    flags = manifest.get("flag_register", {})

    # Calculate runtime
    runtime_sec = run_meta.get("total_runtime_seconds", 0)
    if runtime_sec >= 3600:
        runtime_str = f"{runtime_sec / 3600:.1f}h"
    elif runtime_sec >= 60:
        runtime_str = f"{runtime_sec / 60:.1f}m"
    else:
        runtime_str = f"{runtime_sec:.1f}s"

    print("=" * 72)
    print(f"BUCKMAN PIPELINE MANIFEST SUMMARY - {year}")
    print("=" * 72)
    print(f"Run completed: {run_meta.get('pipeline_end', 'N/A')[:19]} (runtime: {runtime_str})")
    print(f"Machine: {run_meta.get('machine_name', 'N/A')} ({run_meta.get('os', 'N/A')})")
    print()

    # Input files
    print("INPUT FILES:")
    hash_status = hash_verify.get("status", "UNKNOWN")
    files_checked = hash_verify.get("files_checked", 0)
    mismatches = hash_verify.get("mismatches", [])

    if hash_status == "VERIFIED":
        print(f"  [OK] {files_checked} baseline files verified (all hashes match)")
    elif hash_status == "MISMATCH_ACKNOWLEDGED":
        print("  [!!] HASH MISMATCH ACKNOWLEDGED (--allow-hash-mismatch flag used)")
        for m in mismatches:
            print(f"       Mismatched: {m['file']}")
    elif hash_status == "SKIPPED":
        print(f"  [--] Hash verification skipped: {hash_verify.get('reason', 'unknown')}")
    else:
        print(f"  [??] Hash verification status: {hash_status}")

    # Find pumping data info
    for inp in inputs:
        if "Well_Prod" in inp.get("name", "") and "regression" not in inp.get("name", ""):
            date_range = inp.get("date_range", "N/A")
            row_count = inp.get("row_count", "?")
            print(f"  [OK] Pumping data: {date_range} ({row_count} rows)")
            break

    print()

    # Pipeline version
    print("PIPELINE VERSION:")
    git_commit = pipeline.get("git_commit", "N/A")
    git_status = pipeline.get("git_status", "N/A")
    if len(git_commit) > 8:
        git_commit = git_commit[:8]
    print(f"  Git: {git_commit} ({git_status})")
    print(f"  Python: {pipeline.get('python_version', 'N/A')}")

    executables = pipeline.get("executables", [])
    for exe in executables:
        mod_date = exe.get("modified", "")[:10]
        print(f"  {exe.get('name', 'N/A')}: {mod_date}")

    print()

    # Test results
    print("TEST RESULTS:")
    layer0 = tests.get("layer_0_smoke", {})
    layer1 = tests.get("layer_1_conservation", {})
    ballpark = tests.get("ballpark_check", {})

    l0_passed = layer0.get("passed", 0)
    l0_failed = layer0.get("failed", 0)
    l1_passed = layer1.get("passed", 0)
    l1_failed = layer1.get("failed", 0)

    print(f"  Layer 0 (Smoke):        {l0_passed} passed, {l0_failed} failed")
    print(f"  Layer 1 (Conservation): {l1_passed} passed, {l1_failed} failed")

    bp_status = ballpark.get("status", "N/A")
    bp_hard = ballpark.get("hard_fails", 0)
    bp_soft = ballpark.get("soft_flags", 0)
    print(f"  Ballpark Check:         {bp_status} ({bp_hard} hard fails, {bp_soft} soft flags)")

    total_passed = l0_passed + l1_passed
    total_failed = l0_failed + l1_failed
    print()
    print(f"  TOTAL: {total_passed} tests passed, {total_failed} failed")

    print()

    # Flag register
    flag_entries = flags.get("entries", [])
    print("FLAG REGISTER:")
    print(f"  {len(flag_entries)} flags pending review")

    print()
    print(f"MANIFEST SAVED: output/manifests/buckman_manifest_{year}.json")
    print("=" * 72)


def main():
    """Command-line entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate pipeline manifest")
    parser.add_argument("--year", type=int, required=True, help="Year to process")
    parser.add_argument(
        "--allow-hash-mismatch",
        action="store_true",
        help="Continue even if baseline hashes don't match",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    manifest_gen = PipelineManifest(
        year=args.year,
        project_root=project_root,
        allow_hash_mismatch=args.allow_hash_mismatch,
    )

    try:
        manifest = manifest_gen.generate()
        manifest_path = manifest_gen.save(manifest)
        print_manifest_summary(manifest)
        print(f"\nManifest saved to: {manifest_path}")
    except HashMismatchError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
