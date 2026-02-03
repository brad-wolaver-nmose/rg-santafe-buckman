# PRD: Update MODFLOW Buckman Depletion Model from CY2023 to CY2024

## Introduction

Update the existing MODFLOW Buckman Depletion Model input files from calendar year 2023 to 2024. The 2023 `.nam` and `.wel` files serve as templates — the `.wel` file already contains 2024 stress periods populated with zero pumping rates. This task replaces those zeros with actual 2024 monthly pumping data from Table 2 (ingested CSV), converts acre-feet to ft³/s, splits each well's pumping equally between Layer 1 and Layer 2, and updates the `.nam` file year references. The result is validated against known-good 2024 files.

## Goals

- Read 2024 monthly pumping data (acre-feet) for Wells 1–13 from `output/ingested_data/2024_Table_2_output.csv`
- Convert acre-feet/month to ft³/s using: `rate = (acre_feet / 2) * 43560 / (days_in_month * 86400)`
- Replace zero-valued 2024 stress periods (JAN–DEC 2024) in `thruCY2165.wel` with converted pumping rates
- Split each well's monthly pumping equally between Layer 1 and Layer 2
- Update `CY2023.nam` to reference year 2024 file names
- Validate output files match validation files in `validation/modflow/2024/` exactly (or within rounding tolerance)
- Write output files to `output/modflow/2024/`

## User Stories

### US-001: Configuration Constants and File Path Mapping
**Description:** As a developer, I need all file paths, well mappings, and conversion constants defined as module-level constants so the script is maintainable and self-documenting.

**Acceptance Criteria:**
- [ ] Define `INPUT_WEL_PATH = "input/modflow/2023/thruCY2165.wel"`
- [ ] Define `INPUT_NAM_PATH = "input/modflow/2023/CY2023.nam"`
- [ ] Define `TABLE2_CSV_PATH = "output/ingested_data/2024_Table_2_output.csv"`
- [ ] Define `VALIDATION_WEL_PATH = "validation/modflow/2024/thruCY2165_2024.wel"`
- [ ] Define `VALIDATION_NAM_PATH = "validation/modflow/2024/CY2024.nam"`
- [ ] Define `OUTPUT_DIR = "output/modflow/2024"`
- [ ] Define `OUTPUT_WEL_FILENAME = "thruCY2165_2024.wel"`
- [ ] Define `OUTPUT_NAM_FILENAME = "CY2024.nam"`
- [ ] Define `ACRE_FT_TO_FT3 = 43560` (1 acre-foot = 43,560 ft³)
- [ ] Define `SECONDS_PER_DAY = 86400`
- [ ] Define `NUM_LAYERS = 2` (pumping split equally between Layer 1 and Layer 2)
- [ ] Define well-name-to-MODFLOW-name mapping dict:
  - Table 2 "Well 1" → "BUCKMAN 1", "Well 2" → "BUCKMAN 2", "Well 3" → "BUCKMAN 3A", "Well 4" → "BUCKMAN 4", "Well 5" → "BUCKMAN 5", "Well 6" → "BUCKMAN 6", "Well 7" → "BUCKMAN 7", "Well 8" → "BUCKMAN 8", "Well 9" → "BUCKMAN 9", "Well 10" → "BUCKMAN 10", "Well 11" → "BUCKMAN 11", "Well 12" → "BUCKMAN 12", "Well 13" → "BUCKMAN 13"
- [ ] Define well-to-grid mapping dict (row, col per well):
  - BUCKMAN 1: row=13, col=11
  - BUCKMAN 2: row=14, col=11
  - BUCKMAN 3A: row=14, col=11
  - BUCKMAN 4: row=14, col=11
  - BUCKMAN 5: row=15, col=12
  - BUCKMAN 6: row=14, col=12
  - BUCKMAN 7: row=13, col=11
  - BUCKMAN 8: row=13, col=11
  - BUCKMAN 9: row=14, col=12
  - BUCKMAN 10: row=17, col=13
  - BUCKMAN 11: row=19, col=14
  - BUCKMAN 12: row=19, col=15
  - BUCKMAN 13: row=20, col=16
- [ ] Define `MONTH_ABBREVS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]`
- [ ] Define `TARGET_YEAR = 2024`
- [ ] Typecheck passes

### US-002: Read and Parse Table 2 CSV Pumping Data
**Description:** As a groundwater modeler, I need to read the 2024 monthly pumping data from Table 2 so I have the source acre-feet values to convert for MODFLOW.

**Acceptance Criteria:**
- [ ] Read `2024_Table_2_output.csv` using pandas
- [ ] Parse 13 rows (Wells 1–13) with 12 monthly columns (JAN–DEC)
- [ ] Store as a dict keyed by well number (int 1–13), value is dict of month abbreviation → acre-feet (float)
- [ ] Verify all 13 wells are present; raise clear error if any missing
- [ ] Verify no negative pumping values (acre-feet must be ≥ 0)
- [ ] Log total annual pumping per well for sanity check
- [ ] Typecheck passes

### US-003: Unit Conversion — Acre-Feet to ft³/s with Layer Split
**Description:** As a groundwater modeler, I need to convert monthly acre-feet pumping values to MODFLOW pumping rates (ft³/s) split equally between two layers so the rates match MODFLOW conventions.

**Acceptance Criteria:**
- [ ] Implement function `convert_af_to_ft3s(acre_feet: float, days_in_month: int, num_layers: int = 2) -> float`
- [ ] Formula: `rate = (acre_feet / num_layers) * 43560 / (days_in_month * 86400)`
- [ ] Account for 2024 being a leap year (February = 29 days)
- [ ] Return value as negative float (MODFLOW convention: pumping is negative)
- [ ] Format output to 5 decimal places (matching validation file precision)
- [ ] Hand-check: Well 1 JAN 2024 = 16.887963 AF → per-layer rate ≈ -0.13730 ft³/s (31 days)
- [ ] Hand-check: Well 6 FEB 2024 = 0.199476 AF → per-layer rate ≈ -0.00173 ft³/s (29 days)
- [ ] Hand-check: Well 10 DEC 2024 = 12.235564 AF → per-layer rate ≈ -0.09950 ft³/s (31 days)
- [ ] Typecheck passes

### US-004: Parse the 2023 .wel File Structure
**Description:** As a developer, I need to parse the existing thruCY2165.wel file so I can identify and replace the 2024 zero-pumping stress periods while preserving all other data exactly.

**Acceptance Criteria:**
- [ ] Read entire `thruCY2165.wel` file as lines
- [ ] Identify the line range containing 2024 data (JAN 2024 through DEC 2024)
  - 2024 data starts at the `26` header line before "BUCKMAN 1 JAN 2024" (line ~8798)
  - 2024 data ends after "BUCKMAN 13 DEC 2024" (line ~9121)
  - Each month has: one header line (`26`) followed by 26 well entries (13 wells × 2 layers)
  - Total: 12 months × 27 lines = 324 lines for all of 2024
- [ ] Preserve all lines before 2024 data exactly as-is (1988–2023 historical data)
- [ ] Preserve all lines after 2024 data exactly as-is (2025–2165 future zeros)
- [ ] Verify 2024 section contains exactly 12 months × 26 well entries
- [ ] Typecheck passes

### US-005: Generate Updated 2024 Well Entries
**Description:** As a groundwater modeler, I need to generate the 26 well-entry lines for each month of 2024 with the converted pumping rates so they replace the zero-value placeholders.

**Acceptance Criteria:**
- [ ] For each month (JAN–DEC 2024), generate 26 lines: 13 wells × 2 layers
- [ ] Each line follows the exact format: `{layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}`
  - Match the whitespace/column alignment of the existing file exactly
- [ ] Well order within each month matches the validation file:
  1. BUCKMAN 1, 2. BUCKMAN 2, 3. BUCKMAN 3A, 4. BUCKMAN 4, 5. BUCKMAN 5, 6. BUCKMAN 6, 7. BUCKMAN 7, 8. BUCKMAN 8, 9. BUCKMAN 9, 10. BUCKMAN 10, 11. BUCKMAN 11, 12. BUCKMAN 12, 13. BUCKMAN 13
- [ ] For each well, Layer 1 line comes before Layer 2 line
- [ ] Each month block is preceded by a header line: `        26`
- [ ] Rates are negative (MODFLOW pumping convention)
- [ ] Zero pumping values formatted as `-0.00000`
- [ ] Typecheck passes

### US-006: Write Updated .wel File
**Description:** As a developer, I need to assemble and write the complete updated .wel file so it can be used by MODFLOW.

**Acceptance Criteria:**
- [ ] Create `output/modflow/2024/` directory if it doesn't exist
- [ ] Concatenate: pre-2024 lines + generated 2024 lines + post-2024 lines
- [ ] Write to `output/modflow/2024/thruCY2165_2024.wel`
- [ ] Total line count matches validation file (54,805 lines)
- [ ] File uses consistent line endings (match input file)
- [ ] Typecheck passes

### US-007: Generate Updated .nam File
**Description:** As a groundwater modeler, I need to update the CY2023.nam file to reference 2024 file names so MODFLOW reads the correct files for the 2024 simulation.

**Acceptance Criteria:**
- [ ] Read `CY2023.nam` as template
- [ ] Replace `CY2023.lst` → `CY2024.lst`
- [ ] Replace `thruCY2165.wel` → `thruCY2165_2024.wel`
- [ ] Replace `CY2023_riv.flx` → `CY2024_riv.flx`
- [ ] Replace `CY2023_ghb.flx` → `CY2024_ghb.flx`
- [ ] Do NOT add redundant suffixes (e.g., do not create `CY2024_riv.riv` — the `.flx` extension suffices)
- [ ] Add header comment with generation timestamp (matching validation format)
- [ ] Uppercase package type names to match validation format (LIST, BAS, BCF, OC, RIV, GHB, SIP, WEL, DATA(BINARY))
- [ ] Align columns to match validation file whitespace exactly
- [ ] Write to `output/modflow/2024/CY2024.nam`
- [ ] Typecheck passes

### US-008: Validate Output Against 2024 Validation Files
**Description:** As a groundwater modeler, I need to compare my generated files against the known-good validation files to confirm correctness before using them in MODFLOW.

**Acceptance Criteria:**
- [ ] Compare generated `CY2024.nam` against `validation/modflow/2024/CY2024.nam`
  - Ignore comment lines (lines starting with `#`) since timestamps will differ
  - All non-comment lines must match exactly
- [ ] Compare generated `thruCY2165_2024.wel` against `validation/modflow/2024/thruCY2165_2024.wel`
  - All lines outside the 2024 section must be byte-identical
  - 2024 pumping rates must match within ±0.00002 ft³/s tolerance (rounding from CSV precision)
- [ ] Report per-well, per-month comparison: generated rate vs. validation rate vs. difference
- [ ] Flag any differences exceeding tolerance with well name, month, and both values
- [ ] Print summary: total wells checked, total months checked, pass/fail count
- [ ] If all pass: print "Validation PASSED — generated files match validation files"
- [ ] If any fail: print detailed failure report with actionable context
- [ ] Typecheck passes
- [ ] Run script end-to-end with actual data successfully

### US-009: Main Script Entry Point and CLI
**Description:** As a user, I need a single command to run the full pipeline (read CSV → convert → write .wel → write .nam → validate) so the process is repeatable.

**Acceptance Criteria:**
- [ ] Script runs as `python3 update_modflow_2024.py` with no required arguments
- [ ] Optionally accept `--year 2024` argument (default: 2024)
- [ ] Print progress for each major step:
  1. "Reading Table 2 pumping data..."
  2. "Converting acre-feet to ft³/s..."
  3. "Parsing 2023 .wel file..."
  4. "Generating 2024 well entries..."
  5. "Writing updated .wel file..."
  6. "Generating updated .nam file..."
  7. "Validating against known-good files..."
- [ ] Print per-well monthly pumping summary table (acre-feet and ft³/s side by side)
- [ ] Exit code 0 on success, non-zero on validation failure
- [ ] Typecheck passes
- [ ] Run script end-to-end with actual data successfully

## Non-Goals

- No changes to the MODFLOW executable or other input files (.bas, .bcf, .oc, .riv, .ghb, .sip)
- No changes to historical data (1988–2023) or future projection data (2025–2165)
- No GUI or interactive mode — CLI script only
- No automatic downloading or fetching of pumping data
- No modification of the Table 2 CSV source file
- No running of the MODFLOW model itself — only input file generation
- No support for years other than 2024 (though the design accommodates future extension)

## Technical Considerations

### Unit Conversion

The core conversion from monthly acre-feet to MODFLOW pumping rate (ft³/s per layer):

```
rate_ft3_per_s = -(acre_feet / NUM_LAYERS) * ACRE_FT_TO_FT3 / (days_in_month * SECONDS_PER_DAY)
```

Where:
- `ACRE_FT_TO_FT3 = 43560` (1 acre-foot = 43,560 ft³)
- `SECONDS_PER_DAY = 86400`
- `NUM_LAYERS = 2` (pumping split equally between Layer 1 and Layer 2)
- 2024 is a leap year: February has 29 days

### Verification Values

| Well | Month | Acre-Feet | Per-Layer ft³/s | Days |
|------|-------|-----------|-----------------|------|
| 1 | JAN | 16.887963 | -0.13730 | 31 |
| 6 | FEB | 0.199476 | -0.00173 | 29 |
| 10 | DEC | 12.235564 | -0.09950 | 31 |
| 8 | DEC | 47.502959 | -0.38623 | 31 |

### Well Name Mapping (Table 2 → MODFLOW)

| Table 2 | MODFLOW Name | Row | Col |
|---------|-------------|-----|-----|
| Well 1 | BUCKMAN 1 | 13 | 11 |
| Well 2 | BUCKMAN 2 | 14 | 11 |
| Well 3 | BUCKMAN 3A | 14 | 11 |
| Well 4 | BUCKMAN 4 | 14 | 11 |
| Well 5 | BUCKMAN 5 | 15 | 12 |
| Well 6 | BUCKMAN 6 | 14 | 12 |
| Well 7 | BUCKMAN 7 | 13 | 11 |
| Well 8 | BUCKMAN 8 | 13 | 11 |
| Well 9 | BUCKMAN 9 | 14 | 12 |
| Well 10 | BUCKMAN 10 | 17 | 13 |
| Well 11 | BUCKMAN 11 | 19 | 14 |
| Well 12 | BUCKMAN 12 | 19 | 15 |
| Well 13 | BUCKMAN 13 | 20 | 16 |

### .wel File Structure

Each month's stress period in the .wel file has this structure:
```
        26                              ← header: 26 well entries follow (13 wells × 2 layers)
         1        13        11  -0.13730  BUCKMAN 1 JAN 2024     ← Layer 1
         2        13        11  -0.13730  BUCKMAN 1 JAN 2024     ← Layer 2
         1        14        11  -0.00000  BUCKMAN 2 JAN 2024
         2        14        11  -0.00000  BUCKMAN 2 JAN 2024
         ...                              ← continues for all 13 wells
```

- Lines 1–8797: Historical data (1988–DEC 2023) — preserve exactly
- Lines 8798–9121: Year 2024 data (12 months × 27 lines) — replace zeros with converted rates
- Lines 9122–54805: Future data (2025–2165) — preserve exactly

### .nam File Changes (CY2023 → CY2024)

| Line | 2023 Value | 2024 Value |
|------|-----------|-----------|
| LIST | `CY2023.lst` | `CY2024.lst` |
| WEL | `thruCY2165.wel` | `thruCY2165_2024.wel` |
| DATA(BINARY) | `CY2023_riv.flx` | `CY2024_riv.flx` |
| DATA(BINARY) | `CY2023_ghb.flx` | `CY2024_ghb.flx` |

Unchanged files: `thruCY2165.bas`, `sflcs.bcf`, `thruCY2165.oc`, `thruCY2165.riv`, `thruCY2165.ghb`, `sflcs.sip`

### Formatting Notes

- The validation `.nam` file uses uppercase package types (LIST, BAS, BCF) and column-aligned whitespace with a header comment block
- The validation `.wel` file uses 5 decimal places for pumping rates (e.g., `-0.13730`)
- The 2023 `.nam` has mixed case and tighter spacing — the 2024 output should match the validation format

### Dependencies

- Python 3 with pandas (for CSV reading)
- Standard library: `calendar` (days-in-month), `pathlib`, `argparse`, `datetime`
- No external MODFLOW tools required

### Error Handling

- If Table 2 CSV is missing or malformed: raise FileNotFoundError with path
- If well count ≠ 13 or month count ≠ 12: raise ValueError with actual counts
- If 2024 section not found in .wel file: raise ValueError with search pattern used
- If validation fails: print detailed diff, do NOT raise — let user inspect
