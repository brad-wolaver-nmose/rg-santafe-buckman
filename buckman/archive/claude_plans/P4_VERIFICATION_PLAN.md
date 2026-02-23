# P4 Verification Plan: Layer 6 - Provenance and Reproducibility Logging

**Created:** 2026-02-17
**Status:** PENDING APPROVAL
**Layer:** 6 (Provenance)

---

## Objective
Plain English:  
A single JSON file that proves chain of custody for compliance work.  
Inputs: what data went in (with cryptographic fingerprints).  
Code: what software version produced this (git commit + executable dates).  
QA: what tests passed and what values were checked.  
Audit: when/where it ran, what needs human review.  


Create `pipeline_manifest.py` module that generates a comprehensive manifest file (JSON) alongside the 5 report tables, containing:
1. INPUT MANIFEST - File metadata with hashes
2. PIPELINE MANIFEST - Code/executable versioning
3. TEST RESULTS MANIFEST - Layer 0, 1, ballpark check results
4. FLAG REGISTER - Placeholder for Layer 2/3 flags
5. RUN METADATA - Timestamps, runtime, machine info

Plus a `print_manifest_summary()` function for console output.

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/pipeline_manifest.py` | Main manifest generation module (~400 lines) |
| `output/manifests/buckman_manifest_{year}.json` | Output manifest per year |

## Files to Modify

| File | Change |
|------|--------|
| `step5_verify_workflow.py` | Add manifest generation call at end of run |

---

## Implementation Steps

### Step 1: Create `src/` Directory Structure

```bash
mkdir -p src/
mkdir -p output/manifests/
```

### Step 2: Create `src/pipeline_manifest.py`

**Module structure:**

```python
"""
Pipeline Manifest Generator for Buckman Wellfield Depletion Pipeline.

Generates provenance and reproducibility metadata as JSON manifest.
Layer 6 of 8-prompt testing framework.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

@dataclass
class InputFile:
    """Metadata for an input file."""
    name: str
    full_path: str
    sha256: str
    size_bytes: int
    row_count: int | None
    date_range: str | None

@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    value_tested: Any
    threshold: Any
    timestamp: str

class PipelineManifest:
    """Main manifest generator."""

    def __init__(self, year: int, project_root: Path, allow_hash_mismatch: bool = False):
        self.year = year
        self.project_root = project_root
        self.allow_hash_mismatch = allow_hash_mismatch
        self.start_time = datetime.now()
        self.end_time: datetime | None = None

    def generate(self) -> dict:
        """Generate complete manifest."""

    def _collect_input_manifest(self) -> list[dict]:
        """Collect input file metadata."""

    def _verify_baseline_hashes(self) -> dict:
        """Verify historical baseline hashes. Raises HashMismatchError if mismatch and not allowed."""

    def _collect_pipeline_manifest(self) -> dict:
        """Collect pipeline versioning info."""

    def _collect_test_results(self) -> list[dict]:
        """Collect Layer 0, 1, ballpark results."""

    def _get_flag_register(self) -> list[dict]:
        """Return placeholder flag register."""

    def _get_run_metadata(self) -> dict:
        """Collect runtime metadata."""

    def save(self, manifest: dict) -> Path:
        """Save manifest to JSON file."""

def print_manifest_summary(manifest: dict) -> None:
    """Print one-page human-readable summary."""
```

### Step 3: INPUT MANIFEST Implementation

**Files to catalog:**

| Category | Files | Metadata |
|----------|-------|----------|
| Raw pumping data | `input/csv/Buckman_Well_Prod_{year}.csv` | hash, size, rows, date range |
| MODFLOW templates | `input/modflow/2023/thruCY2165.wel`, `.bas`, `.ghb`, `.riv`, `.bcf`, `.sip`, `.oc` | hash, size |
| NAM file template | `input/modflow/2023/CY2023.nam` | hash, size |
| Historical baselines | `validation/historical/Table_1_historical.xlsx` through `Table_5_historical.xlsx` | hash, size |
| Historical bounds | `validation/historical/bounds.yaml` | hash, size |
| 2024 regression inputs | `validation/2024/inputs/Buckman_Well_Prod_2024.csv` | hash, size |

**Hash Verification Behavior:**

- **Default**: FAIL pipeline if historical baseline hashes don't match `validation/historical/hashes.json`
- **Override**: `--allow-hash-mismatch` flag permits continuation with mismatched hashes
- **Audit trail**: Mismatches are prominently logged in manifest regardless of override

```
HASH MISMATCH DETECTED:
  File: validation/historical/Table_3_historical.xlsx
  Expected: cc0c3b2b70f93a29...
  Actual:   a7f8e2d1b3c94e56...

Pipeline stopped. To proceed with mismatched hashes:
  python step5_verify_workflow.py --year 2025 --allow-hash-mismatch

WARNING: Using --allow-hash-mismatch will be logged in manifest.
```

**Helper functions:**

```python
def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_csv_row_count(filepath: Path) -> int:
    """Count rows in CSV file (excluding header)."""
    with open(filepath) as f:
        return sum(1 for _ in f) - 1

def get_csv_date_range(filepath: Path) -> str:
    """Extract date range from pumping CSV (first/last date columns)."""
    import pandas as pd
    df = pd.read_csv(filepath, parse_dates=['Date'])
    return f"{df['Date'].min().date()} to {df['Date'].max().date()}"
```

### Step 4: PIPELINE MANIFEST Implementation

**Data to collect:**

| Item | Method |
|------|--------|
| Git commit hash | `subprocess.run(["git", "rev-parse", "HEAD"])` |
| Git status | `subprocess.run(["git", "status", "--porcelain"])` |
| Python version | `sys.version` |
| Pipeline script dates | `os.path.getmtime()` for step1-step5 |
| modflow96.exe date | `os.path.getmtime()` |
| sfmodflx_2245.exe date | `os.path.getmtime()` |

**Script list:**
- `step1_ingest_buckman_data.py`
- `step2_update_modflow.py`
- `step3_run_modflow.sh`
- `step4_generate_depletion_tables.py`
- `step5_verify_workflow.py`
- `stream_depletions.py`

### Step 5: TEST RESULTS MANIFEST Implementation

**Sources to aggregate:**

1. **Layer 0 (Smoke Tests)** - Run pytest and capture results:
   ```python
   result = subprocess.run(
       ["pytest", "tests/", "-v", "--tb=no", "-q"],
       capture_output=True, text=True
   )
   # Parse "X passed, Y failed" from output
   ```

2. **Layer 1 (Conservation)** - Read existing JSON:
   ```python
   # Read from .claude/plans/P3_conservation_results_{year}.json
   # Already in correct format
   ```

3. **Ballpark Check (P2.5)** - Run and capture:
   ```python
   result = subprocess.run(
       ["python3", "validation/ballpark_check.py", "--year", str(year), "--json"],
       capture_output=True, text=True
   )
   # Parse JSON output
   ```

**Result format (per test):**
```json
{
  "test_name": "budget_closure",
  "layer": 1,
  "status": "PASS",
  "value_tested": 0.01,
  "threshold": 0.1,
  "timestamp": "2026-02-17T13:55:55.778578"
}
```

### Step 6: FLAG REGISTER Implementation

**Placeholder structure:**
```json
{
  "flag_register": {
    "entries": [],
    "note": "Populated by Layer 2 (temporal) and Layer 3 (cross-comparison) checks"
  }
}
```

**Entry format (for future use):**
```json
{
  "test_name": "",
  "flagged_value": null,
  "threshold": null,
  "disposition": "",
  "analyst_initials": "",
  "date": ""
}
```

### Step 7: RUN METADATA Implementation

```python
def _get_run_metadata(self) -> dict:
    return {
        "pipeline_start": self.start_time.isoformat(),
        "pipeline_end": self.end_time.isoformat() if self.end_time else None,
        "total_runtime_seconds": (self.end_time - self.start_time).total_seconds(),
        "machine_name": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "python_executable": sys.executable
    }
```

### Step 8: print_manifest_summary() Function

**Output format (normal - all hashes match):**
```
================================================================================
BUCKMAN PIPELINE MANIFEST SUMMARY - 2025
================================================================================
Run completed: 2026-02-17 14:30:00 (runtime: 45m 23s)
Machine: DESKTOP-ABC123 (Linux 5.15.167.4-microsoft-standard-WSL2)

INPUT FILES:
  [OK] 21 baseline files verified (all hashes match)
  [OK] Pumping data: 2025-01-01 to 2025-12-31 (366 rows)

PIPELINE VERSION:
  Git: a1b2c3d4 (clean)
  Python: 3.11.5
  MODFLOW96: 2023-06-15
  sfmodflx_2245: 2023-06-15

TEST RESULTS:
  Layer 0 (Smoke):       152 passed, 0 failed
  Layer 1 (Conservation): 4 passed, 0 failed
  Ballpark Check:         PASS (0 hard fails, 0 soft flags)

  TOTAL: 156 tests passed, 0 failed

FLAG REGISTER:
  0 flags pending review

MANIFEST SAVED: output/manifests/buckman_manifest_2025.json
================================================================================
```

**Output format (mismatch with override):**
```
================================================================================
BUCKMAN PIPELINE MANIFEST SUMMARY - 2025
================================================================================
Run completed: 2026-02-17 14:30:00 (runtime: 45m 23s)
Machine: DESKTOP-ABC123 (Linux 5.15.167.4-microsoft-standard-WSL2)

INPUT FILES:
  [!!] HASH MISMATCH ACKNOWLEDGED (--allow-hash-mismatch flag used)
       Mismatched: Table_3_historical.xlsx
       Expected: cc0c3b2b70f93a29...
       Actual:   a7f8e2d1b3c94e56...
  [OK] Pumping data: 2025-01-01 to 2025-12-31 (366 rows)
...
```

### Step 9: Integrate into step5_verify_workflow.py

Add argument to `step5_verify_workflow.py`:
```python
parser.add_argument(
    "--allow-hash-mismatch",
    action="store_true",
    help="Continue even if baseline file hashes don't match (logged in manifest)"
)
```

Add to end of `step5_verify_workflow.py`:
```python
# Generate provenance manifest
from src.pipeline_manifest import PipelineManifest, print_manifest_summary

manifest_gen = PipelineManifest(
    year=args.year,
    project_root=Path(__file__).parent,
    allow_hash_mismatch=args.allow_hash_mismatch
)
manifest = manifest_gen.generate()  # Raises if hash mismatch and flag not set
manifest_path = manifest_gen.save(manifest)
print_manifest_summary(manifest)
```

---

## Output File Format

**`output/manifests/buckman_manifest_{year}.json`:**

```json
{
  "manifest_version": "1.0",
  "year": 2025,

  "input_manifest": [
    {
      "name": "Buckman_Well_Prod_2025.csv",
      "full_path": "/home/.../input/csv/Buckman_Well_Prod_2025.csv",
      "sha256": "abc123...",
      "size_bytes": 18432,
      "row_count": 366,
      "date_range": "2025-01-01 to 2025-12-31"
    }
  ],

  "hash_verification": {
    "status": "VERIFIED",
    "baseline_file": "validation/historical/hashes.json",
    "files_checked": 21,
    "mismatches": [],
    "override_flag_used": false
  },

  "pipeline_manifest": {
    "git_commit": "a1b2c3d4e5f6...",
    "git_status": "clean",
    "python_version": "3.11.5",
    "scripts": [
      {"name": "step1_ingest_buckman_data.py", "modified": "2026-02-15T10:30:00"},
      {"name": "step2_update_modflow.py", "modified": "2026-02-15T10:30:00"}
    ],
    "executables": [
      {"name": "modflow96.exe", "modified": "2023-06-15T12:00:00", "size_bytes": 941056},
      {"name": "sfmodflx_2245.exe", "modified": "2023-06-15T12:00:00", "size_bytes": 452608}
    ]
  },

  "test_results_manifest": {
    "layer_0_smoke": {
      "total": 152,
      "passed": 152,
      "failed": 0,
      "tests": []
    },
    "layer_1_conservation": {
      "total": 4,
      "passed": 4,
      "failed": 0,
      "tests": [
        {
          "test_name": "budget_closure",
          "status": "PASS",
          "value_tested": 0.01,
          "threshold": 0.1,
          "timestamp": "2026-02-17T13:55:55"
        }
      ]
    },
    "ballpark_check": {
      "status": "PASS",
      "hard_fails": 0,
      "soft_flags": 0,
      "timestamp": "2026-02-17T14:00:00"
    }
  },

  "flag_register": {
    "entries": [],
    "note": "Populated by Layer 2 and 3 checks"
  },

  "run_metadata": {
    "pipeline_start": "2026-02-17T13:15:00",
    "pipeline_end": "2026-02-17T14:00:23",
    "total_runtime_seconds": 2723,
    "machine_name": "DESKTOP-ABC123",
    "os": "Linux 5.15.167.4-microsoft-standard-WSL2",
    "python_executable": "/usr/bin/python3"
  }
}
```

---

## Tolerances & Acceptance Criteria

| Check | Criterion |
|-------|-----------|
| SHA-256 hashes | FAIL if mismatch (unless `--allow-hash-mismatch` flag used) |
| Hash override | If flag used, log `MISMATCH_ACKNOWLEDGED` in manifest |
| Git status | Report "dirty" if uncommitted changes (warning, not fail) |
| Layer 0 tests | All must pass |
| Layer 1 tests | All must pass |
| Ballpark check | No hard fails (exit code 0 or 1) |
| Manifest file | Must be valid JSON, parseable by `json.load()` |

---

## Flagged Uncertainties

1. **Ballpark check `--json` flag**: `validation/ballpark_check.py` may not have JSON output mode yet. May need to add `--json` flag or parse text output.

2. **Layer 0 pytest output parsing**: Need to handle different pytest output formats. Will use `--tb=no -q` for consistent parsing.

3. **Binary MODFLOW outputs**: Will NOT hash output flux files (31 MB each) - only input files for provenance.

---

## Success Criteria

1. `src/pipeline_manifest.py` module exists and is importable
2. `PipelineManifest.generate()` returns valid dict with all 5 sections
3. `buckman_manifest_{year}.json` is valid JSON
4. All historical baseline hashes verify against `validation/historical/hashes.json`
5. `print_manifest_summary()` produces readable one-page output
6. Module integrates with `step5_verify_workflow.py`
7. Expert witness ready: manifest documents complete chain of custody

---

## Expert Witness Considerations

This manifest supports legal/regulatory review by documenting:
- **Reproducibility**: Same inputs + same code = same outputs (hash verification)
- **Chain of custody**: Every input file traceable to source
- **Version control**: Exact code version used for each run
- **Validation evidence**: All automated tests passed with specific values
- **Analyst sign-off**: Flag register provides audit trail for manual review

---

## Dependencies

- Python 3.10+ (for `|` union types)
- `hashlib` (stdlib)
- `pandas` (for CSV date range extraction)
- `pytest` (for Layer 0 test execution)
- Existing: `tests/test_conservation.py`, `validation/ballpark_check.py`

---

**AWAITING APPROVAL TO IMPLEMENT**
