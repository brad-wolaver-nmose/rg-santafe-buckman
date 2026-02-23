# IS-07: Stream Depletion Library

> **Tier 2 Implementation Specification** — A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `stream_depletions.py` core functions — unit conversions (cfs to acre-feet), Core (2003) analytical residual lookups, post-processor output parsing, Otowi depletion extraction, and supporting constants.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-06: Post-Processor & Output Parsing (produces the `CY{year}` file that this library parses)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Post-processor output | `output/modflow/{year}/[depletions/]CY{year}` | Text file from sfmodflx_2245.exe with monthly cfs values per cell and stream |

### Domain Knowledge
- See DS-01 for unit conversion derivations and validation
- See DS-02 for Core (2003) analytical model residuals
- See `docs/MODFLOW_CELL_MAPPING.md` for stream cell identification and FORTRAN extraction logic

---

## 3. Context for Claude Code

This library is the computational core of the Buckman depletion pipeline. It converts raw MODFLOW post-processor output (monthly cfs flow rates for individual model cells) into acre-feet depletion values for compliance reporting.

### Superposition Principle

MODFLOW calculates depletions using superposition: the difference between a "pumping" scenario and a "no pumping" baseline, both starting in 1988. The residual effects of pre-1988 pumping (1972-1987) are added analytically from Core (2003) lookup tables.

```
Total Depletion = Analytical Residual (pre-1988) + Superposition (1988-present)
```

### Key Equations (Inline)

```
Unit conversion (cfs to acre-feet):
  AF = cfs * days * 86400 / 43560
     = cfs * days * 1.983471...

  Where:
    86400 = seconds per day (60 * 60 * 24)
    43560 = cubic feet per acre-foot
    1.983471 = 86400 / 43560 (conversion factor per day)

  Example: 1.0 cfs * 30 days = 1.0 * 30 * 86400 / 43560 = 59.5041... AF

Annual total from monthly values:
  Annual_AF = SUM(cfs[i] * days[i] * 86400/43560) for i=0..11
```

### Tesuque Extrapolation Formula

For years beyond 2030 (beyond the Core (2003) lookup table):
```
Tesuque residual = -0.4908 * year + 1006.2
  Capped at 0.0 (no negative residuals)

  Example: year 2035 → -0.4908 * 2035 + 1006.2 = 7.482 AF
  Example: year 2060 → -0.4908 * 2060 + 1006.2 = -5.248 → capped to 0.0 AF
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| Seconds per day | 86,400 | s/day |
| Cubic feet per acre-foot | 43,560 | ft^3/AF |
| Conversion factor | 1.983471... | AF/(cfs*day) |
| Days (non-leap Feb) | 28 | days |
| Days (leap Feb) | 29 | days |
| Total days (non-leap) | 365 | days |
| Total days (leap) | 366 | days |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `cfs_to_acre_feet(cfs, days)` — Convert cfs flow rate to acre-feet for a period of `days` | `cfs_to_acre_feet(1.0, 30)` = 59.504132... AF; raises `ValueError` for negative cfs or days < 1 |
| R2 | `cfs_to_af(cfs_value, month_index, year, use_leap_year)` — Month-specific conversion using appropriate days | `cfs_to_af(0.1, 0)` = 6.148760... AF (0.1 cfs * 31 Jan days); `cfs_to_af(0.1, 1, use_leap_year=True)` uses 29 days |
| R3 | `cfs_monthly_to_af_annual(cfs_list, year, use_leap_year)` — Sum 12 monthly cfs values to annual AF total | `cfs_monthly_to_af_annual([0.1]*12)` = 72.397... AF (non-leap); `cfs_monthly_to_af_annual([0.1]*12, use_leap_year=True)` = 72.596... AF (leap) |
| R4 | `get_analytical_residual(stream, year)` — Lookup Core (2003) residual for Pojoaque or Tesuque | `get_analytical_residual("pojoaque", 2024)` = 0.0; `get_analytical_residual("tesuque", 2024)` = 12.877; `get_analytical_residual("tesuque", 2035)` uses formula |
| R5 | `parse_postprocessor_output(file_path)` — Parse CY{year} output file into nested dict `{year: {identifier: {month: cfs}}}` | Correctly parses year headers, cell data rows, and stream summary rows; normalizes "RIV  TOTAL" to "RIV TOTAL" |
| R6 | `extract_otowi_depletions(parsed_data, year)` — Sum model cells above and below Otowi Gage | Returns `(above_cfs, below_cfs)` each as list of 12 monthly values; raises `KeyError` for missing cells |
| R7 | `ABOVE_OTOWI_CELLS` and `BELOW_OTOWI_CELLS` — Coordinate lists for Otowi classification | 10 cells above Otowi, 16 cells below Otowi; coordinates match MODFLOW model grid |
| R8 | `LA_CIENEGA_CUMULATIVE` — Historical cumulative depletion dict (2004-2030) | `LA_CIENEGA_CUMULATIVE[2024]` = 3.74; `LA_CIENEGA_CUMULATIVE[2004]` = 0.45 |
| R9 | `DAYS_VALIDATION` — Non-leap year days list; `DAYS_2024` — Leap year days list | `DAYS_VALIDATION[1]` = 28 (Feb non-leap); `DAYS_2024[1]` = 29 (Feb leap) |
| R10 | `CORE_2003_POJOAQUE` — Analytical residual lookup dict for Pojoaque (1988-2015) | Returns 0 after 2015 (residual exhausted); 40.432 for 1988 |
| R11 | `CORE_2003_TESUQUE` — Analytical residual lookup dict for Tesuque (1988-2030) with linear extrapolation beyond 2030 | 21.015 for 1988; 9.933 for 2030; extrapolation formula for 2031+ |

---

## 5. Worked Example

### Example 1: Unit Conversion — cfs to acre-feet

```
Input: cfs=0.083581, days=31 (January)

Calculation:
  AF = 0.083581 * 31 * 86400 / 43560
     = 0.083581 * 31 * 1.983471
     = 0.083581 * 61.4876
     = 5.13857... AF

Verification:
  0.083581 * 31 = 2.590011 (cfs-days)
  2.590011 * 86400 = 223,777,000 (ft^3)
  223,777,000 / 43560 = 5138.57... wait, this is wrong

Correct: 0.083581 * 31 * 86400 / 43560
  = 0.083581 * 31 * 1.9835
  = 0.083581 * 61.4885
  = 5.1393 AF (approximately)
```

### Example 2: Annual Total from Monthly CFS

```
Input: R POJOAQUE 2024 monthly cfs (from post-processor):
  jan=0.083581, feb=0.083486, mar=0.083596, apr=0.083635,
  may=0.083692, jun=0.083753, jul=0.083791, aug=0.083829,
  sep=0.083862, oct=0.083886, nov=0.083905, dec=0.083916

Days (leap year 2024): [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

Step-by-step:
  Jan: 0.083581 * 31 * 86400/43560 = 5.139 AF
  Feb: 0.083486 * 29 * 86400/43560 = 4.801 AF
  Mar: 0.083596 * 31 * 86400/43560 = 5.140 AF
  ...
  Dec: 0.083916 * 31 * 86400/43560 = 5.160 AF

  Annual total = SUM = ~61.05 AF (approximate; actual depends on precise values)
```

### Example 3: Analytical Residual Lookup

```
Input: stream="tesuque", year=2024
  CORE_2003_TESUQUE[2024] = 12.877 AF

Input: stream="pojoaque", year=2024
  CORE_2003_POJOAQUE.get(2024, 0.0) → 0.0 (not in dict, exhausted after 2015)

Input: stream="tesuque", year=2035 (beyond lookup table)
  value = -0.4908 * 2035 + 1006.2 = -998.778 + 1006.2 = 7.422 AF
  max(0.0, 7.422) = 7.422 AF

Input: stream="tesuque", year=2060 (extrapolation goes negative)
  value = -0.4908 * 2060 + 1006.2 = -1011.048 + 1006.2 = -4.848 AF
  max(0.0, -4.848) = 0.0 AF (capped)
```

### Example 4: Post-Processor Output Parsing

```
Input file fragment (CY2024):
  "YEAR:      2024     jan         feb     ..."
  "    1   9  14    0.025737    0.025725    0.025738 ..."
  "0  R POJOAQUE    0.083581    0.083486    0.083596 ..."
  "0  RIV  TOTAL    0.340618    0.340277    0.340674 ..."

Parsing results:
  Year header regex: r"YEAR:\s+(\d{4})\s+jan" → matches "2024"
  Cell regex: r"\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+(?:\s+[\d.]+){11})" → (1, 9, 14) + 12 values
  Stream regex: r"0\s+(R POJOAQUE|R TESUQUE|RIO GRANDE|RIV\s+TOTAL|LC SPRINGS)\s+(12 floats)"

  "RIV  TOTAL" → normalized via re.sub(r"\s+", " ", ...) → "RIV TOTAL"

Output:
  parsed_data[2024]["1 9 14"]["jan"] = 0.025737
  parsed_data[2024]["R POJOAQUE"]["jan"] = 0.083581
  parsed_data[2024]["RIV TOTAL"]["jan"] = 0.340618
```

### Example 5: Otowi Depletion Extraction

```
ABOVE_OTOWI_CELLS = [
  (1,1,16), (1,2,16), (1,3,16), (1,4,16), (1,5,15),
  (1,6,14), (1,7,14), (1,8,13), (1,9,13), (1,10,12)
]

For month "jan", year 2024:
  above_jan = sum of parsed_data[2024]["1 1 16"]["jan"] +
              parsed_data[2024]["1 2 16"]["jan"] + ... +
              parsed_data[2024]["1 10 12"]["jan"]

BELOW_OTOWI_CELLS = [
  (1,11,11), (1,12,11), (1,13,11), (1,14,10), (1,15,9),
  (1,15,10), (1,16,9), (1,17,8), (1,18,6), (1,18,7),
  (1,19,6), (1,20,5), (1,21,4), (1,21,5), (1,22,4), (1,23,3)
]

For month "jan", year 2024:
  below_jan = sum of 16 cells

Returns: ([above_jan, ..., above_dec], [below_jan, ..., below_dec])
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `stream_depletions.py` | Core library: constants, unit conversions, residual lookups, parsing, Otowi extraction |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_stream_depletions.py -v --tb=short -k "cfs_to or residual or parse or otowi"
ruff check stream_depletions.py
mypy stream_depletions.py
```

Key test cases:

```python
# R1: cfs_to_acre_feet
assert abs(cfs_to_acre_feet(1.0, 30) - 59.50413223) < 0.001
assert abs(cfs_to_acre_feet(0.0, 30) - 0.0) < 0.001
# ValueError for negative cfs
# ValueError for days < 1

# R2: cfs_to_af (month-specific)
assert abs(cfs_to_af(0.1, 0) - 6.14885...) < 0.001  # Jan, 31 days, non-leap
assert abs(cfs_to_af(0.1, 1, use_leap_year=True) - 5.75207...) < 0.001  # Feb, 29 days

# R3: cfs_monthly_to_af_annual
assert abs(cfs_monthly_to_af_annual([0.1]*12) - 72.397...) < 0.01  # non-leap
assert abs(cfs_monthly_to_af_annual([0.1]*12, use_leap_year=True) - 72.596...) < 0.01  # leap

# R4: get_analytical_residual
assert get_analytical_residual("pojoaque", 1988) == 40.432
assert get_analytical_residual("pojoaque", 2024) == 0.0  # exhausted
assert get_analytical_residual("tesuque", 2024) == 12.877
assert get_analytical_residual("tesuque", 2035) > 0  # extrapolation

# R8: LA_CIENEGA_CUMULATIVE
assert LA_CIENEGA_CUMULATIVE[2024] == 3.74
assert LA_CIENEGA_CUMULATIVE[2004] == 0.45
assert LA_CIENEGA_CUMULATIVE[2030] == 4.80
```

---

## 8. Known Gotchas

- [ ] **Two days lists serve different purposes** — `DAYS_VALIDATION` (28 for Feb, 365 total) is used by Table 4, which matches the validation file's non-leap assumption. `DAYS_2024` (29 for Feb, 366 total) is used by Table 3, which uses actual calendar days. The `use_leap_year` parameter selects between them. For future years, use `calendar.isleap(year)` to determine the correct list.
- [ ] **Cell key format** — Parsed cell identifiers use space-separated coordinates: `"1 9 14"` (layer, row, col). This matches the post-processor output format. When constructing keys for Otowi extraction, use f-strings: `f"{lay} {row} {col}"`.
- [ ] **Stream name normalization** — The FORTRAN post-processor writes "RIV  TOTAL" with two spaces. The parser normalizes this to "RIV TOTAL" with a single space using `re.sub(r"\s+", " ", stream_name)`. All downstream code uses the normalized form.
- [ ] **Pojoaque residual exhaustion** — `CORE_2003_POJOAQUE` has no entry for years after 2015. The `get_analytical_residual()` function uses `.get(year, 0.0)` to return 0 for these years, representing the exhaustion of the pre-1988 pumping effect.
- [ ] **Tesuque extrapolation cap** — The linear extrapolation formula for Tesuque residuals beyond 2030 can produce negative values for far-future years. The function caps at 0.0 with `max(0.0, value)` since negative residuals are physically meaningless.
- [ ] **Post-processor output has no file extension** — The file is named `CY2024`, not `CY2024.txt`. Python reads it as a text file with `path.read_text()` or `open(file_path)`.
- [ ] **Year header regex** — The regex `r"YEAR:\s+(\d{4})\s+jan"` requires "jan" after the year number to distinguish year headers from other lines that might contain "YEAR:". This is intentional.
- [ ] **Stream regex is explicitly enumerated** — The stream match regex uses `(R POJOAQUE|R TESUQUE|RIO GRANDE|RIV\s+TOTAL|LC SPRINGS)` rather than a generic pattern. This prevents false matches on unexpected lines and makes the expected stream names explicit in the code.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| `CORE_2003_POJOAQUE` | Static lookup dict | Same dict (returns 0 after 2015) |
| `CORE_2003_TESUQUE` | Static lookup dict | Same dict (or extrapolation after 2030) |
| `LA_CIENEGA_CUMULATIVE` | Static lookup dict | Same dict (extends to 2030) |
| `DAYS_VALIDATION` / `DAYS_2024` | Static constants | Use `calendar.isleap(year)` for dynamic selection |
| Post-processor output | Parsed fresh each year | Parsed fresh each year |

No chaining at this level. All functions are stateless and operate on the data passed to them. Year-chaining for historical preservation happens at the Table writing layer (IS-08 for Table 3, IS-06 for Table 5).

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 -c "
from stream_depletions import (
    cfs_to_acre_feet, cfs_to_af, cfs_monthly_to_af_annual,
    get_analytical_residual, ABOVE_OTOWI_CELLS, BELOW_OTOWI_CELLS,
    LA_CIENEGA_CUMULATIVE, CORE_2003_POJOAQUE, CORE_2003_TESUQUE,
    DAYS_VALIDATION, DAYS_2024
)

# Unit conversion
assert abs(cfs_to_acre_feet(1.0, 30) - 59.5041) < 0.01
assert abs(cfs_monthly_to_af_annual([0.1]*12) - 72.3978) < 0.01

# Residuals
assert get_analytical_residual('pojoaque', 2024) == 0.0
assert get_analytical_residual('tesuque', 2024) == 12.877
assert get_analytical_residual('pojoaque', 1988) == 40.432

# Constants
assert len(ABOVE_OTOWI_CELLS) == 10
assert len(BELOW_OTOWI_CELLS) == 16
assert LA_CIENEGA_CUMULATIVE[2024] == 3.74
assert DAYS_VALIDATION[1] == 28
assert DAYS_2024[1] == 29

print('All stream_depletions.py verification checks passed')
"
```

Expected result: All assertions pass, "All stream_depletions.py verification checks passed" printed.

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Unit conversion derivations, validation values |
| DS-02 | Core (2003) analytical model residual tables |
| DS-03 | MODFLOW model grid, cell coordinates, boundary packages |
| IS-06 | Upstream dependency: produces CY{year} output file parsed by this library |
| IS-08 | Downstream dependency: Table 3 generation uses residuals and unit conversions |
| `docs/MODFLOW_CELL_MAPPING.md` | Stream cell identification, FORTRAN extraction ranges |
