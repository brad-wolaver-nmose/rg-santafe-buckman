# IS-12: Provenance & Compliance (Layer 6)

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `src/pipeline_manifest.py` (JSON provenance manifest) and `src/workflow_logger.py` (MD + DOCX audit trail) for regulatory compliance documentation of the Buckman Wellfield depletion pipeline.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project scaffold (directory structure, `src/` package)
- IS-09: Tables 4 & 5 generation (outputs referenced in inventories)
- IS-10: Test suite (test results consumed by manifest)
- IS-11: Validation framework (ballpark check, temporal consistency results consumed)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Pumping CSV | `input/csv/Buckman_Well_Prod_{year}.csv` | Raw pumping input |
| MODFLOW templates | `input/modflow/2023/thruCY2165.*` | MODFLOW package files |
| Historical hashes | `validation/historical/hashes.json` | SHA-256 baseline hashes |
| Historical bounds | `validation/historical/bounds.yaml` | Validation bounds |
| Pipeline outputs | `output/depletion/TABLE_{3,4,5}_*_{year}.xlsx` | Generated depletion tables |
| Table 2 output | `output/ingested_data/{year}_Table_2_output.csv` | Monthly pumping summary |

### Domain Knowledge
- See DS-06 for regulatory compliance requirements (City of Santa Fe, OSE reporting)
- See DS-05 for Rio Grande Compact context

---

## 3. Context for Claude Code

Regulatory compliance for groundwater depletion calculations requires a complete chain of custody from raw data to final reports. Two artifacts serve this purpose:

**pipeline_manifest.py** generates a machine-readable JSON manifest containing:
1. Input file inventory with SHA-256 hashes (cryptographic provenance)
2. Baseline hash verification (detect unauthorized changes)
3. Pipeline version information (git commit, script mod dates, executable info)
4. Test results from Layers 0, 1, and ballpark check
5. Flag register for items requiring human review
6. Runtime metadata (timestamps, machine info)

**workflow_logger.py** generates a human-readable audit trail (Markdown + DOCX) containing:
1. Header metadata (timestamp, operator, machine, git info)
2. Executive summary (key pumping and depletion numbers)
3. Input/output file inventories with SHA-256 hashes
4. Step-by-step execution log
5. Verification results summary
6. Physical interpretation with regulatory context
7. Assumptions and limitations
8. Approval signature block

### Key Concepts (Inline)

```
SHA-256 Hash:     Cryptographic fingerprint of file contents.
                  Any change to the file produces a completely different hash.
                  Used to prove inputs/outputs haven't been tampered with.

Hash Verification: Compare computed hash against stored baseline.
                   Mismatch -> inputs changed since baseline was established.
                   Hard stop unless --allow-hash-mismatch flag is used.

Manifest vs Log:  Manifest = machine-readable JSON for automated verification.
                  Log = human-readable MD/DOCX for regulatory review.
```

### Key Constants (Inline)

| Constant | Value | Context |
|----------|-------|---------|
| MANIFEST_VERSION | "1.0" | Manifest format version |
| RIO_GRANDE_COMPACT_NM_ALLOCATION | 405000 AF/yr | Approximate NM annual allocation |
| HISTORICAL_PUMPING_AVG_5YR | ~1050 AF (2024) | For year-over-year context |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `PipelineManifest` class generates JSON manifest | `generate()` returns dict with 6 sections: input_manifest, hash_verification, pipeline_manifest, test_results_manifest, flag_register, run_metadata. `save()` writes to `output/manifests/buckman_manifest_{year}.json`. |
| R2 | `PipelineManifest._collect_input_manifest()` inventories all inputs | Lists: pumping CSV (with row count and date range), MODFLOW templates (8 files), historical baselines, bounds.yaml, regression inputs. Each entry has name, full_path, sha256, size_bytes. |
| R3 | `PipelineManifest._verify_baseline_hashes()` validates file integrity | Reads `validation/historical/hashes.json`, computes SHA-256 for each listed file, compares. Returns status: VERIFIED/MISMATCH_ACKNOWLEDGED/SKIPPED. Raises `HashMismatchError` if mismatch and `allow_hash_mismatch=False`. |
| R4 | `PipelineManifest._collect_pipeline_manifest()` tracks code versions | Returns: git_commit (SHA), git_status (clean/dirty), python_version, script modification dates for 6 pipeline scripts, executable info for modflow96.exe and sfmodflx_2245.exe. |
| R5 | `PipelineManifest._collect_test_results()` aggregates test outcomes | Runs Layer 0 pytest (capturing pass/fail counts from output), loads Layer 1 results from JSON file, runs ballpark check. Returns structured results per layer. |
| R6 | `PipelineManifest._get_flag_register()` provides review placeholder | Returns empty entries list with documented entry_format: test_name, flagged_value, threshold, disposition, analyst_initials, date. |
| R7 | `print_manifest_summary()` formats one-page human-readable output | Prints: header with year, input files status, pipeline version (git + executables), test results (Layer 0/1/ballpark counts), flag register count, manifest save path. Fits on one terminal screen. |
| R8 | `WorkflowLogger` class generates MD + DOCX audit trail | `generate_and_save(status)` returns (md_path, docx_path). MD has 9 sections. DOCX conversion via pandoc. |
| R9 | `WorkflowLogger.collect_input_inventory()` hashes input files | Returns list of dicts with name, path, size_bytes, sha256, role for pumping CSV, MODFLOW templates, and bounds.yaml. |
| R10 | `WorkflowLogger.collect_output_inventory()` hashes output files | Returns list of dicts for Tables 1-5 and MODFLOW outputs (listing file, WEL file). |
| R11 | `WorkflowLogger.collect_pumping_data()` parses Table 2 | Extracts total_af, months_recorded, wells_active from Table 2 output (CSV or XLSX). |
| R12 | `WorkflowLogger.collect_depletion_data()` parses Tables 3-5 | Extracts: pojoaque_af, tesuque_af, above_otowi_af, below_otowi_af, la_cienega_cumulative_af. Handles NaN residuals (Pojoaque exhausted after 2015). |
| R13 | `WorkflowLogger.generate_interpretation()` fills physical context templates | Templates: pumping analysis (with 5-year average context), Rio Grande Compact (below Otowi as % of NM allocation), tributary impacts (Table 3 breakdown), La Cienega (Table 5 cumulative). |
| R14 | `WorkflowLogger._convert_to_docx()` converts MD to DOCX | Uses pandoc subprocess. Handles: pandoc not installed (RuntimeError with install instructions), timeout (60s), optional reference.docx template. |

---

## 5. Worked Example

### R1: PipelineManifest.generate()

#### Input
```python
manifest_gen = PipelineManifest(year=2024, project_root=Path("."))
manifest = manifest_gen.generate()
```

#### Expected Output Structure
```json
{
  "manifest_version": "1.0",
  "year": 2024,
  "input_manifest": [
    {
      "name": "Buckman_Well_Prod_2024.csv",
      "full_path": "/path/to/input/csv/Buckman_Well_Prod_2024.csv",
      "sha256": "a1b2c3d4...",
      "size_bytes": 45678,
      "row_count": 366,
      "date_range": "2024-01-01 to 2024-12-31"
    },
    {
      "name": "thruCY2165.wel",
      "full_path": "/path/to/input/modflow/2023/thruCY2165.wel",
      "sha256": "e5f6g7h8...",
      "size_bytes": 234567
    }
  ],
  "hash_verification": {
    "status": "VERIFIED",
    "baseline_file": "/path/to/validation/historical/hashes.json",
    "files_checked": 5,
    "mismatches": [],
    "override_flag_used": false
  },
  "pipeline_manifest": {
    "git_commit": "824d534abc...",
    "git_status": "clean",
    "python_version": "3.12.1",
    "scripts": [
      {"name": "step1_ingest_buckman_data.py", "modified": "2026-02-18T17:31:00"},
      {"name": "stream_depletions.py", "modified": "2026-02-20T16:02:00"}
    ],
    "executables": [
      {"name": "modflow96.exe", "modified": "2023-01-15T00:00:00", "size_bytes": 524288}
    ]
  },
  "test_results_manifest": {
    "layer_0_smoke": {"total": 152, "passed": 152, "failed": 0, "status": "PASS"},
    "layer_1_conservation": {"total": 4, "passed": 4, "failed": 0, "status": "PASS"},
    "ballpark_check": {"status": "PASS", "exit_code": 0, "hard_fails": 0, "soft_flags": 0}
  },
  "flag_register": {
    "entries": [],
    "note": "Populated by Layer 2 (temporal) and Layer 3 (cross-comparison) checks"
  },
  "run_metadata": {
    "pipeline_start": "2026-02-20T10:00:00",
    "pipeline_end": "2026-02-20T10:05:30",
    "total_runtime_seconds": 330.0,
    "machine_name": "water-modeling-01",
    "os": "Linux 5.15.167.4-microsoft-standard-WSL2",
    "python_executable": "/usr/bin/python3"
  }
}
```

### R3: Hash Verification

#### Input
```json
// validation/historical/hashes.json
{
  "files": {
    "Table_1_historical.xlsx": "abc123...",
    "bounds.yaml": "def456..."
  }
}
```

#### Calculation Steps
```
Step 1: Load hashes.json -> stored_hashes

Step 2: For each file in stored_hashes:
        Compute SHA-256 of validation/historical/{filename}

Step 3: Compare:
        If match -> increment files_checked
        If mismatch -> append to mismatches list

Step 4: If mismatches AND NOT allow_hash_mismatch:
        Raise HashMismatchError with:
        - Which files mismatched
        - How to override (--allow-hash-mismatch)
        - Warning that override will be logged in manifest
```

### R13: Physical Interpretation -- Rio Grande Compact

#### Input
```python
below_otowi_af = 842.94
above_otowi_af = 277.50
year = 2024
```

#### Calculation Steps
```
Step 1: Compute percentage of NM allocation
        pct = 842.94 / 405000 * 100 = 0.2082%

Step 2: Fill template:
        "Depletions below Otowi Bridge (842.94 AF) are chargeable against
         New Mexico's Rio Grande Compact delivery obligation to Texas."
        "This represents 0.2082% of typical annual NM allocation"
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create/Modify | `src/pipeline_manifest.py` | PipelineManifest class, print_manifest_summary(), HashMismatchError |
| Create/Modify | `src/workflow_logger.py` | WorkflowLogger class, interpretation templates, DOCX conversion |
| Create/Modify | `src/generate_workflow_log.py` | CLI wrapper for WorkflowLogger (if exists) |

---

## 7. Acceptance Criteria

```bash
# Generate manifest:
python -c "
from src.pipeline_manifest import PipelineManifest, print_manifest_summary
m = PipelineManifest(year=2024, project_root='.', allow_hash_mismatch=True)
manifest = m.generate()
path = m.save(manifest)
print_manifest_summary(manifest)
print(f'Saved to: {path}')
"

# Generate workflow log:
python -c "
from src.workflow_logger import WorkflowLogger
logger = WorkflowLogger(year=2024)
md, docx = logger.generate_and_save(status='PASS')
print(f'MD: {md}')
print(f'DOCX: {docx}')
"

# Code quality:
ruff check src/pipeline_manifest.py src/workflow_logger.py
mypy src/pipeline_manifest.py src/workflow_logger.py
```

Expected output: Manifest JSON saved with all 6 sections populated. Workflow log MD generated with 9 sections. DOCX generated if pandoc is installed.

---

## 8. Known Gotchas

- [ ] **HashMismatchError is a hard stop by default.** The manifest generator raises this exception if baseline hashes don't match and `allow_hash_mismatch=False`. The override flag (`--allow-hash-mismatch`) is logged in the manifest as `override_flag_used: true` for audit trail.
- [ ] **_run_layer_0_tests() invokes pytest as a subprocess**, not via `pytest.main()`. This isolates test execution from the manifest generator's Python process. Parse pass/fail counts from stdout using regex `(\d+) passed`.
- [ ] **WorkflowLogger.collect_depletion_data() parses XLSX files with complex column structures.** Table 3 has merged headers -- the year column is `df.columns[0]` (often "Unnamed: 0"), Pojoaque total is column index 3, Tesuque total is column index 6. Handle NaN values for exhausted residuals.
- [ ] **DOCX conversion requires pandoc** (`sudo apt install pandoc`). If pandoc is not installed, the logger returns (md_path, md_path) -- the MD path is returned for both slots with a warning. Do NOT crash.
- [ ] **The manifest's _get_csv_date_range() uses pandas** to parse the date column. The CSV may use different date formats ("1/1/2024", "2024-01-01", "Jan 1, 2024"). Use `pd.to_datetime(errors='coerce')` to handle all formats.
- [ ] **Git subprocess calls must specify `cwd=self.project_root`** to ensure they run in the correct repository, not wherever the Python process was launched from.
- [ ] **HISTORICAL_PUMPING_AVG_5YR is a hardcoded dict** with approximate values. These are used for context only (not validation) and should be updated annually.
- [ ] **Workflow log timestamps include seconds** in filenames: `{year}_workflow_log_{YYYYMMDD_HHMMSS}_{status}.md`. Multiple runs in the same session produce unique files.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Input manifest | Current year's input files | Current year's input files |
| Hash verification | validation/historical/hashes.json (static) | Same file (updated if baselines change) |
| Pipeline manifest | Current git state + script mod dates | Current git state |
| Test results | Live pytest + ballpark execution | Live execution |
| Workflow log | Current outputs + manifest | Current outputs + manifest |

There is no chaining in provenance -- each year's manifest and log are self-contained snapshots of the pipeline state at execution time.

---

## 10. Verification

```bash
# Quick verification (generates manifest only):
python src/pipeline_manifest.py --year 2024 --allow-hash-mismatch

# Full verification (generates manifest + workflow log):
python run_all_tests.py --year 2024
```

Expected result: Manifest JSON at `output/manifests/buckman_manifest_2024.json` with all sections populated. Workflow log at `output/logs/{year}_workflow_log_*.md` with 9 sections.

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-05 | Rio Grande Compact context for interpretation templates |
| DS-06 | Regulatory compliance requirements driving manifest design |
| IS-09 | Tables 4 & 5 outputs inventoried in output manifest |
| IS-10 | Layer 0-1 test results consumed by PipelineManifest |
| IS-11 | Ballpark check and temporal consistency results consumed |

---

## Appendix A: Interpretation Templates

### Pumping Analysis Template
```markdown
**Total Pumping: {total_af:.2f} AF** in calendar year {year}.
- 5-year average: {avg_5yr:.0f} AF
- Year-over-year change: {yoy_change:+.1f}%
- {context_statement}
```

### Rio Grande Compact Template
```markdown
Depletions below Otowi Bridge ({below_otowi_af:.2f} AF) are chargeable against
New Mexico's Rio Grande Compact delivery obligation to Texas.

- Below Otowi depletion: {below_otowi_af:.2f} AF
- Above Otowi depletion: {above_otowi_af:.2f} AF (does not affect compact)
- This represents {pct_of_allocation:.4f}% of typical annual NM allocation
```

### Tributary Template
```markdown
**Rio Pojoaque:**
- {year} Depletion: {pojoaque_af:.2f} AF
- Residual Component: {pojoaque_residual:.2f} AF (pre-1988 pumping tail)
- Superposition Component: {pojoaque_super:.2f} AF (1988-{year} pumping)
- Note: Pojoaque residual reached zero in 2015

**Rio Tesuque:**
- {year} Depletion: {tesuque_af:.2f} AF
- Residual Component: {tesuque_residual:.2f} AF (pre-1988 pumping tail)
- Note: Tesuque residual continues through ~2050
```

### La Cienega Template
```markdown
**{year} Status:**
- Cumulative impact since 2004: {cumulative_af:.2f} AF
- Annual increment: {annual_af:.2f} AF
- La Cienega Springs lies ~15 km south of Buckman Wellfield
```

## Appendix B: Workflow Log 9-Section Structure

| Section | Title | Content |
|---------|-------|---------|
| 1 | Header / Metadata | Timestamp, operator, machine, git commit |
| 2 | Executive Summary | Total pumping, key depletions, verification status |
| 3 | Input File Inventory | Files with SHA-256 hashes and roles |
| 4 | Step-by-Step Execution | What each pipeline step produced |
| 5 | Output File Inventory | Generated files with SHA-256 hashes |
| 6 | Verification Summary | Layer-by-layer test results |
| 7 | Physical Interpretation | Regulatory context from templates |
| 8 | Assumptions & Limitations | MODFLOW model caveats |
| 9 | Approval Block | Prepared/Reviewed/Approved signature lines |
