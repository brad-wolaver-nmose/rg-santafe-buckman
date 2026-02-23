# IS-04: WEL File Management

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `step2_update_modflow.py` -- WEL file parsing, pumping rate conversion (acre-feet to ft3/s), stress period well entry generation, WEL file assembly, NAM file generation, and baseline file copying.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project Scaffold & Constants (provides `src/constants.py` with WELL_GRID_MAP, WELL_NAME_MAP, conversion constants)
- IS-02: CSV Ingestion & Table 2 (produces `{year}_Table_2_output.csv`)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Table 2 CSV | `output/ingested_data/{year}_Table_2_output.csv` | Monthly AFY grid from step 1 |
| Source WEL file (baseline) | `input/modflow/2023/thruCY2165.wel` | Original MODFLOW well file (for year 2024) |
| Source WEL file (chained) | `output/modflow/{year-1}/thruCY2165_{year-1}.wel` | Prior year's output WEL file (for year 2025+) |
| Source NAM file | `input/modflow/2023/CY2023.nam` | Baseline MODFLOW name file |
| Baseline MODFLOW files | `input/modflow/2023/` | 10 static files required by MODFLOW96 |

### Domain Knowledge
- See DS-02 for AF-to-ft3/s conversion and MODFLOW conventions
- See DS-03 for MODFLOW grid cell assignments

---

## 3. Context for Claude Code

MODFLOW96 uses a WEL (well) package file to specify pumping rates at each well for each stress period (month). The WEL file is a large text file spanning years 1947-2165, with each month containing 26 well entries (13 wells x 2 model layers). This script reads the existing WEL file, replaces the target year's 324 lines (12 months x 27 lines/month) with new pumping data converted from Table 2's acre-feet values to MODFLOW's ft3/s convention, and writes the updated file.

Pumping rates are negative in MODFLOW convention (extraction from aquifer). Each well's monthly pumping volume in acre-feet is split equally between two model layers and converted to a continuous rate in ft3/s.

### Key Equations (Inline)

```
AF to ft3/s (per layer):
  rate = -(AF / num_layers) * ACRE_FT_TO_FT3 / (days_in_month * SECONDS_PER_DAY)
  rate = -(AF / 2) * 43560 / (days * 86400)

Example: Well 1, JAN 2024 (16.887963 AF, 31 days):
  rate = -(16.887963 / 2) * 43560 / (31 * 86400)
  rate = -8.443982 * 43560 / 2678400
  rate = -367,819.86 / 2678400
  rate = -0.13733 ft3/s
```

### Key Constants (Inline)

| Constant | Value | Units | Purpose |
|----------|-------|-------|---------|
| ACRE_FT_TO_FT3 | 43560 | ft3/AF | Volume conversion |
| SECONDS_PER_DAY | 86400 | s/day | Time conversion |
| NUM_LAYERS | 2 | dimensionless | Pumping split between 2 model layers |
| LINES_PER_MONTH | 27 | lines | 1 header + 26 well entries per stress period |
| WELLS_PER_MONTH | 26 | entries | 13 wells x 2 layers |
| BASELINE_YEAR | 2024 | year | First year that uses 2023 baseline input |
| RATE_TOLERANCE | 0.0001 | ft3/s | Validation tolerance for rate comparison |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `YearConfig` dataclass with all year-specific paths | `config.target_year == 2024`, `config.source_year == 2023`, paths resolve correctly |
| R2 | `get_year_config(target_year)` resolves input paths: baseline (2024) vs chained (2025+) | For 2024: `input_wel_path == "input/modflow/2023/thruCY2165.wel"`; for 2025: `input_wel_path == "output/modflow/2024/thruCY2165_2024.wel"` |
| R3 | `parse_wel_file(wel_path, target_year) -> WelFileData` splits into pre/target/post sections | `len(target_year_lines) == 324` (12 months x 27 lines) |
| R4 | `find_year_boundaries()` searches for "JAN {year}" and "DEC {year}" patterns | Start index points to header line before first JAN entry; end index is exclusive |
| R5 | WEL file validation: each month has header "26", first entry is BUCKMAN 1, last is BUCKMAN 13 | `ValueError` raised if structure doesn't match |
| R6 | `read_table2_pumping_data(csv_path) -> dict[int, dict[str, float]]` reads Table 2 | Returns `{1: {"JAN": 16.887963, "FEB": 38.805796, ...}, ...}` for all 13 wells |
| R7 | `convert_af_to_ft3s(acre_feet, days_in_month, num_layers=2) -> float` returns negative rate | `convert_af_to_ft3s(16.887963, 31, 2)` returns `-0.13733` (within 0.00001) |
| R8 | `generate_well_entries(pumping_data, target_year) -> list[str]` produces 324 lines | Well order: BUCKMAN 1 through 13; Layer 1 before Layer 2 for each well |
| R9 | Well entry line format: `"{layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}\r\n"` | Exact format match with CRLF line endings |
| R10 | `write_updated_wel_file()` assembles pre-target + new target + post-target | Total line count = original line count; pre and post sections byte-identical |
| R11 | `generate_nam_file(target_year, output_dir, output_filename)` writes MODFLOW name file | NAM file references correct year-specific filenames (WEL, LST, flux files) |
| R12 | `copy_baseline_files(output_dir)` copies 10 static files from `input/modflow/2023/` | All 10 files exist in output directory after copy |
| R13 | `verify_nam_file_references()` checks all NAM-referenced files exist | Returns True when all referenced files are present |
| R14 | CRLF line endings (`\r\n`) throughout generated WEL file content | Matches MODFLOW96 Windows convention |
| R15 | Zero pumping rates formatted as `-0.00000` (negative zero) | Matches validation file format for inactive wells |
| R16 | Leap year handling: February has 29 days in leap years, 28 in non-leap | `convert_af_to_ft3s(10.0, 29)` uses 29 days for February 2024 (leap year) |

---

## 5. Worked Example

### Input: Table 2 CSV for Well 1, January 2024

```csv
Well,JAN,FEB,MAR,...,DEC,Total
1,16.887963,38.805796,41.370397,...,0.000000,601.276042
```

### Calculation Steps

```
Step 1: Read pumping data
  Well 1, JAN = 16.887963 AF

Step 2: Get days in month
  JAN 2024 = 31 days (2024 is a leap year, but January is unaffected)

Step 3: Convert AF to ft3/s per layer
  rate = -(16.887963 / 2) * 43560 / (31 * 86400)
  rate = -(8.4439815) * 43560 / (2678400)
  rate = -367,819.83 / 2678400
  rate = -0.13733 ft3/s

Step 4: Generate well entry lines (Layer 1 and Layer 2)
  BUCKMAN 1 is at grid position (row=13, col=11)

  Layer 1: "         1        13        11  -0.13733  BUCKMAN 1 JAN 2024\r\n"
  Layer 2: "         2        13        11  -0.13733  BUCKMAN 1 JAN 2024\r\n"

Step 5: Generate month header
  "        26\r\n"

Step 6: Assemble January block (27 lines)
  Line 1: "        26\r\n"                                          (header)
  Line 2: "         1        13        11  -0.13733  BUCKMAN 1 JAN 2024\r\n"  (Well 1, Layer 1)
  Line 3: "         2        13        11  -0.13733  BUCKMAN 1 JAN 2024\r\n"  (Well 1, Layer 2)
  Line 4: "         1        14        11  -0.00000  BUCKMAN 2 JAN 2024\r\n"  (Well 2, Layer 1)
  Line 5: "         2        14        11  -0.00000  BUCKMAN 2 JAN 2024\r\n"  (Well 2, Layer 2)
  ...
  Line 26: "         1        20        16  -0.14716  BUCKMAN 13 JAN 2024\r\n" (Well 13, Layer 1)
  Line 27: "         2        20        16  -0.14716  BUCKMAN 13 JAN 2024\r\n" (Well 13, Layer 2)
```

### Additional Conversion Examples

```
Well 1, FEB 2024 (38.805796 AF, 29 days -- leap year):
  rate = -(38.805796 / 2) * 43560 / (29 * 86400)
  rate = -(19.402898) * 43560 / (2505600)
  rate = -845,190.24 / 2505600
  rate = -0.33732 ft3/s

Well 13, JUL 2024 (55.001150 AF, 31 days):
  rate = -(55.001150 / 2) * 43560 / (31 * 86400)
  rate = -(27.500575) * 43560 / (2678400)
  rate = -1,197,925.05 / 2678400
  rate = -0.44725 ft3/s

Well 2, JAN 2024 (0.000000 AF, 31 days):
  rate = -(0.0 / 2) * 43560 / (31 * 86400)
  rate = -0.00000 ft3/s  (formatted as negative zero)
```

> **Note:** Values shown use rounded inputs; actual pipeline results may differ slightly.

### NAM File Content

```
# MODFLOW Name File for Buckman Depletion Model - Year 2024
# Automatically generated by Python script on 2026-02-20 10:30:00
# File Type      Unit File Name
#------------------------------------
LIST            23    CY2024.lst
BAS             21    thruCY2165.bas
BCF             11    sflcs.bcf
OC              10    thruCY2165.oc
RIV             14    thruCY2165.riv
GHB             15    thruCY2165.ghb
SIP             17    sflcs.sip
WEL             12    thruCY2165_2024.wel
DATA(BINARY)    24    CY2024_riv.flx
DATA(BINARY)    34    CY2024_ghb.flx
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `step2_update_modflow.py` | Main MODFLOW update script with all functions |
| Create | `tests/test_update_modflow.py` | Unit tests for conversion, parsing, entry generation |

### Output files generated at runtime
| File | Path | Description |
|------|------|-------------|
| Updated WEL | `output/modflow/{year}/thruCY2165_{year}.wel` | WEL file with target year's pumping data |
| NAM file | `output/modflow/{year}/CY{year}.nam` | MODFLOW name file for target year |
| Baseline copies | `output/modflow/{year}/*.{bcf,sip,bas,ghb,oc,riv,exe,py}` | 10 static MODFLOW support files |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_update_modflow.py -v --tb=short
ruff check step2_update_modflow.py
mypy step2_update_modflow.py

# End-to-end run (requires step1 output):
python3 step2_update_modflow.py --year 2024
```

Expected output:
- `thruCY2165_2024.wel` with same total line count as input
- `CY2024.nam` with correct file references
- 10 baseline files copied to `output/modflow/2024/`
- Validation against `validation/modflow/2024/` (if validation files exist):
  - Pre-2024 section: byte-identical
  - 2024 pumping rates: within 0.0001 ft3/s tolerance
  - Post-2024 section: byte-identical

---

## 8. Known Gotchas

- [ ] Well 3 maps to "BUCKMAN 3A" (not "BUCKMAN 3"). The WELL_NAME_MAP handles this: `WELL_NAME_MAP[3] == "BUCKMAN 3A"`.
- [ ] Line format uses fixed-width fields: `{layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}`. Two spaces separate col from rate, and rate from well_name.
- [ ] Zero pumping must be formatted as `-0.00000` (negative zero), not `0.00000` or `-0.0`. Use `rate = -0.0` when `abs(rate) < 1e-10`.
- [ ] CRLF line endings (`\r\n`) are critical. MODFLOW96 is a DOS/Windows program. Use `newline=""` when writing to prevent Python from adding extra CR.
- [ ] The WEL file spans 1947-2165. The target year section is a small portion in the middle. Pre-target and post-target sections must be preserved byte-for-byte.
- [ ] Multiple wells share grid cells (e.g., BUCKMAN 1, 7, 8 all at row=13, col=11). This is correct -- different physical wells in the same MODFLOW cell.
- [ ] Leap year handling is automatic via `calendar.isleap()`. February 2024 has 29 days, February 2025 has 28 days. This affects the ft3/s rate conversion.
- [ ] Rate tolerance for validation is 0.0001 ft3/s (not 0.00002 as originally stated in PRD). Actual differences can reach 0.00008 due to rounding between CSV precision and validation file.
- [ ] The `find_year_boundaries()` function searches for the first occurrence of "JAN {year}" and the last occurrence of "DEC {year}". The WEL file may contain these strings in well comments, so the search must find the correct structural boundaries.
- [ ] NAM file comment lines start with `#` and are ignored during validation comparison. Only non-comment lines must match.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N (2024) | Source for Year N+1 (2025) |
|-------------|--------------------------|---------------------------|
| Input WEL file | `input/modflow/2023/thruCY2165.wel` (baseline) | `output/modflow/2024/thruCY2165_2024.wel` (prior year output) |
| Input NAM file | `input/modflow/2023/CY2023.nam` (baseline) | `output/modflow/2024/CY2024.nam` (prior year output) |
| Table 2 CSV | `output/ingested_data/2024_Table_2_output.csv` | `output/ingested_data/2025_Table_2_output.csv` |
| Output WEL file | `output/modflow/2024/thruCY2165_2024.wel` | `output/modflow/2025/thruCY2165_2025.wel` |
| Baseline files | Copied from `input/modflow/2023/` | Copied from `input/modflow/2023/` (always same source) |

**Critical chaining logic:**
- `BASELINE_YEAR = 2024` uses original 2023 files from `input/modflow/2023/`
- Years > 2024 use prior year's output: `output/modflow/{year-1}/thruCY2165_{year-1}.wel`
- The WEL file grows cumulatively: 2024 output contains actual pumping for 2024 (replacing placeholder data), and 2025 output contains actual data for both 2024 and 2025
- Baseline support files (BCF, SIP, BAS, etc.) are always copied fresh from the 2023 directory -- they do not change between years

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 step2_update_modflow.py --year 2024 && \
  python3 -c "
from pathlib import Path
wel = Path('output/modflow/2024/thruCY2165_2024.wel')
nam = Path('output/modflow/2024/CY2024.nam')
assert wel.exists(), 'WEL file not created'
assert nam.exists(), 'NAM file not created'
lines = wel.read_text().splitlines()
jan_lines = [l for l in lines if 'BUCKMAN 1 JAN 2024' in l]
assert len(jan_lines) == 2, f'Expected 2 BUCKMAN 1 JAN lines (L1+L2), got {len(jan_lines)}'
rate = float(jan_lines[0].split()[3])
assert abs(rate - (-0.13733)) < 0.001, f'Rate mismatch: {rate}'
print(f'WEL: {len(lines)} lines, BUCKMAN 1 JAN rate: {rate:.5f} ft3/s')
baseline_count = sum(1 for f in Path('output/modflow/2024').iterdir() if f.is_file())
print(f'Files in output dir: {baseline_count}')
print('PASS')
"
```

Expected result: `WEL: XXXXX lines, BUCKMAN 1 JAN rate: -0.13733 ft3/s`, `Files in output dir: 12`, `PASS`

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-02 | AF-to-ft3/s conversion, MODFLOW pumping conventions |
| DS-03 | MODFLOW grid cell assignments (WELL_GRID_MAP) |
| IS-01 | Constants (WELL_GRID_MAP, WELL_NAME_MAP, ACRE_FT_TO_FT3, NUM_LAYERS, BASELINE_FILES_TO_COPY) |
| IS-02 | Table 2 CSV output consumed as input |
| IS-05 | MODFLOW execution reads the WEL and NAM files produced here |
| IS-06 | Stream depletion post-processing depends on MODFLOW run completing successfully |
