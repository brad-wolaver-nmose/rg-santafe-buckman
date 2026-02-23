# IS-06: Post-Processor & Output Parsing

> **Tier 2 Implementation Specification** — A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `step4_generate_depletion_tables.py` — the orchestrator script that copies flux files, runs the FORTRAN post-processor (`sfmodflx_2245.exe`), parses the output, and calls `stream_depletions.py` to generate Tables 3, 4, and 5.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-05: MODFLOW Execution (`step3_run_modflow.sh` must have produced flux files)
- IS-07: Stream Depletion Library (core functions called by this script)
- IS-08: Table 3 Generation (called during table generation phase)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| RIV flux file | `output/modflow/{year}/[modflow/]CY{year}_riv.flx` | MODFLOW river boundary binary flux output (~31 MB) |
| GHB flux file | `output/modflow/{year}/[modflow/]CY{year}_ghb.flx` | MODFLOW general head boundary binary flux output (~31 MB) |
| Post-processor | `output/modflow/{year}/[depletions/]sfmodflx_2245.exe` | FORTRAN post-processor executable (Win32) |
| GHB package | `input/modflow/2023/thruCY2165.ghb` | GHB cell definitions for geometry validation |

### Domain Knowledge
- See DS-03 for MODFLOW model structure
- See `docs/MODFLOW_CELL_MAPPING.md` for FORTRAN cell extraction logic and La Cienega Springs cell mapping
- The post-processor reads binary flux files and produces a formatted text file with monthly cfs values per cell and per stream

---

## 3. Context for Claude Code

The MODFLOW post-processor (`sfmodflx_2245.exe`) is a legacy FORTRAN program that reads binary MODFLOW flux output files and calculates stream depletions. It:

1. Reads river (RIV) package flux — contains flows for Rio Pojoaque, Rio Tesuque, and Rio Grande cells
2. Reads general head boundary (GHB) package flux — contains flows for La Cienega Springs cells
3. Assigns cells to streams using hardcoded row/column ranges (see `docs/MODFLOW_CELL_MAPPING.md`)
4. Outputs a formatted text file (`CY{year}`) with monthly cfs values for each cell and stream summary rows

### Directory Structure Evolution

The project underwent a directory restructuring between 2024 and 2025:

```
2024 (Legacy nested structure):
  output/modflow/2024/
    modflow/           ← MODFLOW output (flux files here)
      CY2024_riv.flx
      CY2024_ghb.flx
    depletions/        ← Post-processor working directory
      sfmodflx_2245.exe
      CY2024             ← Post-processor output

2025+ (Flat structure):
  output/modflow/2025/
    CY2025_riv.flx     ← Flux files here
    CY2025_ghb.flx
    sfmodflx_2245.exe   ← Post-processor here too
    CY2025              ← Output here too
```

### Key Constants (Inline)

| Constant | Value | Description |
|----------|-------|-------------|
| `POST_PROCESSOR_EXE` | `sfmodflx_2245.exe` | FORTRAN post-processor executable name |
| `OUTPUT_DIR` | `./output/depletion/` | Directory for generated XLSX tables |
| `VALIDATION_DIR` | `./validation/` | Directory for validation reference files |
| `DEFAULT_YEAR` | 2024 | Default processing year if not specified |

### Post-Processor Input Protocol

The post-processor reads three lines from stdin:
```
CY{year}_riv.flx      ← River flux file name
CY{year}_ghb.flx      ← GHB flux file name
CY{year}               ← Output file prefix
```

### Post-Processor Output Format

The output file `CY{year}` contains year-blocks like:

```
1 PUMPAGE EFFECT ON BOUNDARY FLOW (CFS)    CY2024_riv.flx
YEAR:      2024     jan         feb         mar    ...
LAY ROW COL
+_________________________________...
    1   9  14    0.025737    0.025725    0.025738  ...
    1   9  15    0.019555    0.019547    0.019556  ...
    ...
0  R POJOAQUE    0.083581    0.083486    0.083596  ...
0  R TESUQUE     0.078939    0.078843    0.078957  ...
0  RIO GRANDE    0.178098    0.177948    0.178121  ...
0  RIV  TOTAL    0.340618    0.340277    0.340674  ...

[GHB section follows with similar format]
0  LC SPRINGS    0.005137    0.005134    0.005137  ...
```

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `get_modflow_output_dir(year)` — Returns correct directory based on year: 2024 and earlier: `output/modflow/{year}/modflow/`; 2025+: `output/modflow/{year}/` | `get_modflow_output_dir(2024)` returns `./output/modflow/2024/modflow/`; `get_modflow_output_dir(2025)` returns `./output/modflow/2025/` |
| R2 | `get_depletions_dir(year)` — Returns post-processor working directory: 2024 and earlier: `output/modflow/{year}/depletions/`; 2025+: `output/modflow/{year}/` | `get_depletions_dir(2024)` returns `./output/modflow/2024/depletions/`; `get_depletions_dir(2025)` returns `./output/modflow/2025/` |
| R3 | `copy_flux_files(year)` — Copies `CY{year}_riv.flx` and `CY{year}_ghb.flx` from modflow dir to depletions dir; skips copy if source and destination resolve to same directory (flat structure) | For 2024: files copied from `modflow/` to `depletions/`; for 2025+: skip message printed, no copy |
| R4 | `run_post_processor(year)` — Executes `sfmodflx_2245.exe` via Wine, pipes stdin with riv file, ghb file, and output prefix; verifies output file created | Post-processor creates `CY{year}` text file; returns True on success |
| R5 | `check_prerequisites(year)` — Verifies flux files, depletions directory, and post-processor exe exist before processing | Missing any prerequisite prints forensic error and returns False |
| R6 | `check_wine_installed()` — Verifies Wine is installed and accessible | Returns True when `wine --version` succeeds; returns False otherwise |
| R7 | `main(year)` orchestrates full pipeline: check_prerequisites -> copy_flux_files -> validate GHB geometry -> run_post_processor -> parse output -> extract depletions -> generate Tables 3, 4, 5 -> validate | Returns 0 on success, 1 on any failure |
| R8 | `--year YYYY` command-line argument with argparse; defaults to `DEFAULT_YEAR` (2024) | `python3 step4_generate_depletion_tables.py --year 2025` processes year 2025 |
| R9 | GHB geometry validation — call `sd.validate_ghb_cells_in_fortran_range()` before running post-processor to ensure all GHB cells fall within FORTRAN extraction rectangle | Geometry mismatch produces forensic error referencing `docs/MODFLOW_CELL_MAPPING.md` |
| R10 | Forensic error messages using 5-element format: what failed, location, actual, expected, physical context | All error messages follow `print_error()` format |

---

## 5. Worked Example

### Input

```bash
python3 step4_generate_depletion_tables.py --year 2024
```

### Calculation Steps

```
Step 1: check_prerequisites(2024)
  - MODFLOW dir: ./output/modflow/2024/modflow/ → exists
  - RIV flux: CY2024_riv.flx → exists (31,484,640 bytes)
  - GHB flux: CY2024_ghb.flx → exists (31,484,640 bytes)
  - Depletions dir: ./output/modflow/2024/depletions/ → exists
  - Post-processor: sfmodflx_2245.exe → exists
  Result: True

Step 2: copy_flux_files(2024)
  - Source: ./output/modflow/2024/modflow/
  - Dest: ./output/modflow/2024/depletions/
  - Source != Dest (nested structure) → copy both files
  - CY2024_riv.flx: 31,484,640 bytes -> depletions/
  - CY2024_ghb.flx: 31,484,640 bytes -> depletions/
  Result: True

Step 3: validate_ghb_cells_in_fortran_range()
  - Parse input/modflow/2023/thruCY2165.ghb → 6 cells
  - All cells in rows 30-32, cols 12-15
  - FORTRAN rectangle: rows 28-35, cols 10-20
  - All 6 cells within rectangle → passes

Step 4: run_post_processor(2024)
  - stdin_input = "CY2024_riv.flx\nCY2024_ghb.flx\nCY2024\n"
  - wine ./sfmodflx_2245.exe with cwd=depletions/
  - Output: CY2024 created (text file with depletion data)
  Result: True

Step 5: parse_post_processor_output(year=2024)
  - File: output/modflow/2024/depletions/CY2024
  - Years parsed: 37 (1988-2024)
  - Sample: parsed_data[2024]["R POJOAQUE"]["jan"] = 0.083581

Step 6-13: Generate and write Tables 3, 4, 5 (see IS-07, IS-08)
  - TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx
  - TABLE_4_Rio_Grande_Otowi_2024.xlsx
  - TABLE_5_La_Cienega_Springs_2024.xlsx

Step 14: Validate against reference files
  - Table 3: OK (all 6 fields within 0.001 AF)
  - Table 4: OK (annual totals within 0.01 AF)
  - Table 5: OK (cumulative within 0.01 AF)
  Overall: OK
```

### Expected Output

```
=== Stream Depletion Table Generator for 2024 ===

[prerequisite checklist output]

Copying flux files to post-processor directory for year 2024...
  CY2024_riv.flx: 31,484,640 bytes -> output/modflow/2024/depletions/
  CY2024_ghb.flx: 31,484,640 bytes -> output/modflow/2024/depletions/
Flux files copied successfully.

=== US-001 Complete ===

=== Validating MODFLOW Geometry ===
All 6 GHB cells within FORTRAN rectangle (rows 28-35, cols 10-20)

Running post-processor via Wine for year 2024...
  Wine version: wine-8.0
  Command: wine sfmodflx_2245.exe
  Working directory: output/modflow/2024/depletions/
  Inputs: CY2024_riv.flx, CY2024_ghb.flx, CY2024
Post-processor completed successfully.
  Output file: CY2024 (1,234,567 bytes)

[... parsing, extraction, table generation output ...]

FINAL SUMMARY
Year processed: 2024
Generated files:
  - output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx
  - output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx
  - output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx

Validation status: OK
All validations passed!
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `step4_generate_depletion_tables.py` | Orchestrator: copy flux files, run post-processor, parse output, generate tables |

Dependencies imported at runtime:
- `stream_depletions` (IS-07) — unit conversions, parsing, table generation, validation
- `shutil` — file copying
- `subprocess` — Wine execution
- `argparse` — CLI argument parsing

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_generate_depletion_tables.py -v --tb=short
ruff check step4_generate_depletion_tables.py
mypy step4_generate_depletion_tables.py

# Unit tests for path functions:
python3 -c "
from step4_generate_depletion_tables import get_modflow_output_dir, get_depletions_dir
assert get_modflow_output_dir(2024) == './output/modflow/2024/modflow/'
assert get_modflow_output_dir(2025) == './output/modflow/2025/'
assert get_depletions_dir(2024) == './output/modflow/2024/depletions/'
assert get_depletions_dir(2025) == './output/modflow/2025/'
print('Path function tests passed')
"

# Full end-to-end (requires Wine + flux files):
python3 step4_generate_depletion_tables.py --year 2024
# Expected: 3 XLSX files created, validation passes
```

Expected output: Ruff/mypy clean; path function tests pass; end-to-end generates three XLSX files with validation status OK.

---

## 8. Known Gotchas

- [ ] **Directory structure varies by year** — The 2024/pre-2024 nested structure (`modflow/` + `depletions/` subdirectories) differs from the 2025+ flat structure (everything in one directory). Both `get_modflow_output_dir()` and `get_depletions_dir()` use the `year <= 2024` threshold to select the correct path.
- [ ] **Same-directory skip for flat structure** — When source and destination resolve to the same directory (2025+), `copy_flux_files()` must skip the copy entirely. It compares `source_dir.resolve() == dest_dir.resolve()` to handle this correctly.
- [ ] **Post-processor stdin protocol** — `sfmodflx_2245.exe` reads three lines from stdin: (1) RIV flux filename, (2) GHB flux filename, (3) output prefix. The `\n` separators are critical. Using `subprocess.run(input=...)` with text mode handles this correctly.
- [ ] **Post-processor working directory** — The FORTRAN executable expects flux files in its working directory (the `cwd` parameter). It does NOT accept full paths; it opens files by name only.
- [ ] **Wine timeout** — The post-processor timeout is 300 seconds (5 minutes). This is generous for the small flux files; sfmodflx_2245 typically completes in seconds. If it hangs, it is likely a Wine configuration issue.
- [ ] **GHB geometry validation** — The geometry check (`validate_ghb_cells_in_fortran_range()`) runs BEFORE the post-processor to catch cell mismatches early. If the FORTRAN code's hardcoded rectangle doesn't contain all GHB cells, depletion values would be silently wrong.
- [ ] **Output file has no extension** — The post-processor output file is named `CY{year}` with NO file extension. This is the FORTRAN convention. Python reads it as a text file.
- [ ] **Two different parsing functions exist** — `parse_post_processor_output()` (with underscores: `post_processor`) in `step4_generate_depletion_tables.py` is used by the step4 pipeline. `parse_postprocessor_output()` (no underscore: `postprocessor`) in `stream_depletions.py` is used by the stream depletion library. These are separate implementations with slightly different regex patterns but produce equivalent results. Be careful not to confuse them when importing or testing.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Flux files | Generated by step3 for year N | Generated by step3 for year N+1 |
| Post-processor output | `CY{N}` in depletions dir | `CY{N+1}` in depletions dir |
| Table 3 historical baseline | `validation/2024/expected_outputs/Table_3_expected.xlsx` or prior year output | Year N's `TABLE_3_Rio_Pojoaque_Tesuque_N.xlsx` |
| Table 5 historical baseline | `LA_CIENEGA_CUMULATIVE` dict or prior year output | Year N's `TABLE_5_La_Cienega_Springs_N.xlsx` |
| Validation files | `validation/2024/expected_outputs/Table_3_expected.xlsx` + `validation/TABLE 4 - Rio Grande...xlsx` | Same files (2024-specific); Table 4 validation skipped for non-2024 years |

Key chaining logic:
- **Table 3**: For years < processing_year, values come from the prior year's output Table 3 (chaining). Falls back to 2024 validation baseline.
- **Table 5**: For years < processing_year, cumulative values come from the prior year's output Table 5. Falls back to `LA_CIENEGA_CUMULATIVE` dict.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 step4_generate_depletion_tables.py --year 2024
```

Expected result:
- Three XLSX files in `output/depletion/`:
  - `TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx`
  - `TABLE_4_Rio_Grande_Otowi_2024.xlsx`
  - `TABLE_5_La_Cienega_Springs_2024.xlsx`
- Validation status: `OK` (all tables match reference within tolerances)
- Exit code: 0

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-03 | MODFLOW model structure, boundary packages |
| IS-05 | Upstream dependency: generates flux files consumed by post-processor |
| IS-07 | Dependency: unit conversions, parsing, table data generation functions |
| IS-08 | Dependency: Table 3 generation logic |
| `docs/MODFLOW_CELL_MAPPING.md` | FORTRAN cell extraction logic, geometry validation rationale |
