# IS-01: Project Scaffold & Constants

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-23

> **Implementation Note:** The current codebase does NOT use a centralized `src/constants.py` module. Constants are defined locally in each pipeline script: `step1_ingest_buckman_data.py` (MG_TO_AF_FACTOR, tolerances, WELL_OSE_MAP), `step2_update_modflow.py` (ACRE_FT_TO_FT3, WELL_GRID_MAP, WELL_NAME_MAP), `step4_generate_depletion_tables.py` (OUTPUT_DIR, VALIDATION_DIR), and `stream_depletions.py` (CORE_2003_\*, cell mappings, LA_CIENEGA_CUMULATIVE). This spec describes the aspirational centralized architecture; for the as-built state, refer to the individual IS-02 through IS-09 specs.

---

## 1. Session Goal

Set up the Buckman Wellfield depletion pipeline project directory structure, requirements.txt, pyproject.toml, and shared constants module (`src/constants.py`).

---

## 2. Prerequisites

### Prior Specs (must be complete)
- None -- this is the foundational scaffold.

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| None | N/A | This spec creates the project from scratch |

### Domain Knowledge
- See DS-01 for well field layout and OSE permit numbering
- See DS-02 for unit conversion factors (MG-to-AF, AF-to-ft3)
- See DS-03 for MODFLOW grid cell mapping

---

## 3. Context for Claude Code

The Buckman Wellfield depletion pipeline processes annual pumping data from the City of Santa Fe's 13 production wells. Data flows through 5 pipeline steps: CSV ingestion, MODFLOW update, MODFLOW execution, stream depletion post-processing, and depletion table generation.

All pipeline steps share conversion constants, well mappings, and tolerance thresholds. Centralizing these in `src/constants.py` prevents duplication and ensures consistency.

### Key Equations (Inline)

```
MG to AF:  AF = MG * 3.06889
           (1 acre-foot = 325,851 gallons; 1,000,000 / 325,851 = 3.06889)

AF to ft3/s:  rate = -(AF / num_layers) * 43560 / (days_in_month * 86400)
              (1 acre-foot = 43,560 ft3; 1 day = 86,400 seconds)
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| MG_TO_AF_FACTOR | 3.06889 | AF/MG |
| ACRE_FT_TO_FT3 | 43560 | ft3/AF |
| SECONDS_PER_DAY | 86400 | s/day |
| NUM_LAYERS | 2 | dimensionless |
| NOISE_THRESHOLD_MGD | 0.0015 | MGD |
| DAILY_SUM_TOLERANCE_INFO_MGD | 0.001 | MGD |
| DAILY_SUM_TOLERANCE_ERROR_MGD | 0.005 | MGD |
| ANNUAL_SUM_TOLERANCE_MG | 0.01 | MG |
| RATE_TOLERANCE | 0.0001 | ft3/s |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | Create directory structure with all required directories | `ls` confirms all directories exist: `input/csv/`, `input/modflow/2023/`, `output/ingested_data/`, `output/modflow/`, `output/depletion/`, `validation/`, `tests/`, `src/`, `docs/` |
| R2 | Create `requirements.txt` with pinned minimum versions | File contains: `pandas>=1.5.0`, `pint>=0.20.0`, `openpyxl>=3.0.0`, `pytest>=7.0.0`, `ruff>=0.1.0`, `mypy>=1.0.0`. Note: `PyYAML` and `pytest-json-report` are not currently in requirements.txt. |
| R3 | Create `ruff.toml` and `mypy.ini` with linting/type-checking config | `ruff check src/` and `mypy src/` run without configuration errors. Note: the project uses `ruff.toml` and `mypy.ini`, not `pyproject.toml`. |
| R4 | Create `src/__init__.py` (empty) | Python can import from `src` package |
| R5 | Create `src/constants.py` with all shared constants | All constants importable: `from src.constants import MG_TO_AF_FACTOR` |
| R6 | Define WELL_OSE_MAP: well number (1-13) to OSE permit string | `WELL_OSE_MAP[1] == "RG-20516-S-5"` and `WELL_OSE_MAP[3] == "RG-20516-S"` |
| R7 | Define WELL_NAME_MAP: well number (1-13) to MODFLOW name | `WELL_NAME_MAP[3] == "BUCKMAN 3A"` (not "BUCKMAN 3") |
| R8 | Define WELL_GRID_MAP: MODFLOW name to (row, col) tuple | `WELL_GRID_MAP["BUCKMAN 1"] == (13, 11)` and `WELL_GRID_MAP["BUCKMAN 13"] == (20, 16)` |
| R9 | Define CSV_WELL_COLUMNS list (13 entries) | `len(CSV_WELL_COLUMNS) == 13` and `CSV_WELL_COLUMNS[0] == "BWell 1\|Flow Mgd"` |
| R10 | Define MONTHS_ABBREV tuple and MONTHS_ORDERED tuple | `MONTHS_ABBREV[0] == "JAN"` and `MONTHS_ORDERED[0] == ("01", "JAN")` |
| R11 | Define BASELINE_FILES_TO_COPY list (10 files) | List contains `modflow96.exe`, `sflcs.bcf`, `sfmodflx_2245.exe`, etc. |
| R12 | Define `print_error()` function with 5-element forensic format | Calling `print_error("msg", "loc", "act", "exp", "ctx")` prints structured error |
| R13 | Define ABOVE_OTOWI_CELLS and BELOW_OTOWI_CELLS sets | Sets contain MODFLOW cell coordinates for stream depletion grouping |
| R14 | Define CORE_2003_POJOAQUE and CORE_2003_TESUQUE dicts | Dicts map cell coordinates to 2003-baseline depletion fractions |
| R15 | Define LA_CIENEGA_CUMULATIVE list | List contains cumulative La Cienega Springs depletion data |

---

## 5. Worked Example

### WELL_OSE_MAP (complete mapping)

```python
WELL_OSE_MAP = {
    1: "RG-20516-S-5",
    2: "RG-20516-S-6",
    3: "RG-20516-S",       # Combined wells 3/3A
    4: "RG-20516-S-2",
    5: "RG-20516-S-3",
    6: "RG-20516-S-4",
    7: "RG-20516-S-7",
    8: "RG-20516-S-8",
    9: "RG-20516-S-9",
    10: "RG-20516-S-10",
    11: "RG-20516-S-11",
    12: "RG-20516-S-12",
    13: "RG-20516-S-13",
}
```

### WELL_GRID_MAP (complete mapping)

```python
WELL_GRID_MAP = {
    "BUCKMAN 1":  (13, 11),
    "BUCKMAN 2":  (14, 11),
    "BUCKMAN 3A": (14, 11),   # Same cell as BUCKMAN 2
    "BUCKMAN 4":  (14, 11),   # Same cell as BUCKMAN 2
    "BUCKMAN 5":  (15, 12),
    "BUCKMAN 6":  (14, 12),
    "BUCKMAN 7":  (13, 11),   # Same cell as BUCKMAN 1
    "BUCKMAN 8":  (13, 11),   # Same cell as BUCKMAN 1
    "BUCKMAN 9":  (14, 12),   # Same cell as BUCKMAN 6
    "BUCKMAN 10": (17, 13),
    "BUCKMAN 11": (19, 14),
    "BUCKMAN 12": (19, 15),
    "BUCKMAN 13": (20, 16),
}
```

### WELL_NAME_MAP (complete mapping)

```python
WELL_NAME_MAP = {
    1: "BUCKMAN 1",   2: "BUCKMAN 2",   3: "BUCKMAN 3A",
    4: "BUCKMAN 4",   5: "BUCKMAN 5",   6: "BUCKMAN 6",
    7: "BUCKMAN 7",   8: "BUCKMAN 8",   9: "BUCKMAN 9",
    10: "BUCKMAN 10", 11: "BUCKMAN 11", 12: "BUCKMAN 12",
    13: "BUCKMAN 13",
}
```

### print_error() usage

```python
>>> print_error(
...     "CSV file not found",
...     "./input/csv/Buckman_Well_Prod_2024.csv",
...     "File does not exist",
...     "CSV file with 366 daily records",
...     "Missing source data - cannot process 2024 pumping records"
... )
ERROR: CSV file not found
  Location: ./input/csv/Buckman_Well_Prod_2024.csv
  Actual: File does not exist
  Expected: CSV file with 366 daily records
  Physical context: Missing source data - cannot process 2024 pumping records
```

### BASELINE_FILES_TO_COPY (complete list)

```python
BASELINE_FILES_TO_COPY = [
    "modflow96.exe",
    "sflcs.bcf",
    "sflcs.sip",
    "thruCY2165.bas",
    "thruCY2165.ghb",
    "thruCY2165.oc",
    "thruCY2165.riv",
    "sfmodflx_2245.exe",
    "verify_modflow_run.py",
    "verify_depletion.py",
]
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `src/__init__.py` | Empty init file for Python package |
| Create | `src/constants.py` | All shared constants, mappings, and `print_error()` |
| Create | `requirements.txt` | Python dependencies with minimum versions |
| Create | `ruff.toml` and `mypy.ini` | Ruff and mypy configuration (not `pyproject.toml`) |
| Create | `tests/__init__.py` | Empty init file for test package |
| Create | `tests/test_constants.py` | Unit tests for constants module. Note: no dedicated `tests/test_constants.py` exists in the current codebase; constants are tested as part of individual module tests (e.g., `tests/test_ingest_buckman_data.py`, `tests/test_update_modflow.py`). |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_constants.py -v --tb=short    # See note below
ruff check src/constants.py
mypy src/constants.py
```

> **Note:** No dedicated `tests/test_constants.py` exists in the current codebase. Constants are tested as part of individual module tests (e.g., `tests/test_ingest_buckman_data.py`, `tests/test_update_modflow.py`).

Expected output:
- All tests pass (verifying constant values, mapping completeness, print_error output)
- No ruff lint errors
- No mypy type errors

---

## 8. Known Gotchas

- [ ] Well 3 maps to "BUCKMAN 3A" (not "BUCKMAN 3") -- historical naming convention for combined wells 3/3A
- [ ] Multiple wells share the same MODFLOW grid cell (e.g., BUCKMAN 1, 7, 8 all at row=13, col=11). This is intentional -- they are separate physical wells in the same model cell.
- [ ] CSV_WELL_COLUMNS uses pipe separator: `"BWell 1|Flow Mgd"` not `"BWell 1 Flow Mgd"`
- [ ] WELL_OSE_MAP well 3 is `"RG-20516-S"` (no suffix), while all others have `-S-N` format
- [ ] BASELINE_FILES_TO_COPY has exactly 10 files -- includes both executables (modflow96.exe, sfmodflx_2245.exe) and two Python verification scripts

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Constants | `src/constants.py` (static) | Same `src/constants.py` |
| Directory structure | Created once | Reused |

Constants do not change between years. This module is year-independent.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 -c "from src.constants import MG_TO_AF_FACTOR, WELL_OSE_MAP, WELL_GRID_MAP, WELL_NAME_MAP, CSV_WELL_COLUMNS, MONTHS_ABBREV; print(f'MG_TO_AF={MG_TO_AF_FACTOR}, wells={len(WELL_OSE_MAP)}, grid={len(WELL_GRID_MAP)}, cols={len(CSV_WELL_COLUMNS)}')"
```

Expected result: `MG_TO_AF=3.06889, wells=13, grid=13, cols=13`

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Well field layout, OSE permits, physical well locations |
| DS-02 | Unit conversion factors (MG-to-AF, AF-to-ft3) |
| DS-03 | MODFLOW grid cell assignments |
| IS-02 | Uses constants for CSV ingestion (CSV_WELL_COLUMNS, MG_TO_AF_FACTOR, tolerances) |
| IS-03 | Uses constants for Table 1 generation (WELL_OSE_MAP, WELL_NAME_MAP) |
| IS-04 | Uses constants for WEL file management (WELL_GRID_MAP, ACRE_FT_TO_FT3, NUM_LAYERS) |
