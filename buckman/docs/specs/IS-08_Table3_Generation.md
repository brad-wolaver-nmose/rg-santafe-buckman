# IS-08: Table 3 Generation

> **Tier 2 Implementation Specification** — A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Draft
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-23

---

## 1. Session Goal

Implement Table 3 generation — combining MODFLOW superposition results with Core (2003) analytical residuals for Rio Pojoaque-Nambe and Rio Tesuque, preserving historical years via chaining from prior year's output, and exporting to a formatted XLSX file.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-06: Post-Processor & Output Parsing (produces parsed post-processor output)
- IS-07: Stream Depletion Library (provides `cfs_to_acre_feet()`, `cfs_to_af()`, `cfs_monthly_to_af_annual()`, `get_analytical_residual()`, and the `CORE_2003_POJOAQUE`/`CORE_2003_TESUQUE` lookup tables)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Post-processor output | `output/modflow/{year}/[depletions/]CY{year}` | Parsed text with monthly cfs values per stream |
| Prior year's Table 3 | `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year-1}.xlsx` | Historical depletion values for chaining |
| Validation baseline | `validation/2024/expected_outputs/Table_3_expected.xlsx` | Fallback if prior year's Table 3 not found |

### Domain Knowledge
- See DS-03 §2 for the superposition principle and analytical residual science
- See DS-04 §2 for year-chaining architecture and historical preservation rules
- See DS-03 §5 for the cfs-to-AF conversion factor derivation

---

## 3. Context for Claude Code

Table 3 reports annual stream depletion impacts to two tributaries: Rio Pojoaque-Nambe and Rio Tesuque. For each stream, the total impact is the sum of two components:

### Superposition Principle

```
Total_Impact_AF = Residual_AF + Superposition_AF

Where:
  Residual_AF     = Core (2003) analytical model value for pre-1988 pumping effects
  Superposition_AF = MODFLOW-calculated depletion from 1988-{year} pumping
```

- **Residual Impact (Analytical):** Pre-1988 pumping effects still propagating through the aquifer. Values decrease over time. Rio Pojoaque residuals reached zero by 2016; Rio Tesuque residuals continue through 2050 (0.117 AF), then 0.0.
- **Superposition Impact:** MODFLOW model calculates depletions from all pumping since 1988. Monthly cfs values are converted to annual AF.

### Historical Preservation (Year Chaining)

Years before the current processing year use values preserved verbatim from the prior year's Table 3 output. Only the current year and future projections are recalculated from the current MODFLOW run. This ensures historical values remain stable across annual updates.

Chaining resolution order:
1. Prior year's output: `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_{year-1}.xlsx`
2. Fallback: `validation/2024/expected_outputs/Table_3_expected.xlsx`

### Key Equations (Inline)

**cfs to AF conversion:**
```
AF = cfs × days × 86400 / 43560

Where:
  cfs   = cubic feet per second (monthly average from post-processor)
  days  = days in the month (accounts for leap years)
  86400 = seconds per day
  43560 = cubic feet per acre-foot

Simplified: AF = cfs × days × 1.9835
```

**Monthly-to-annual aggregation:**
```
Annual_AF = SUM(cfs_month[i] × days[i] × 1.9835)  for i = Jan..Dec
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| CFS_TO_AF factor | 86400/43560 = 1.9835 | AF/(cfs·day) |
| Year range | 1988–2050 | inclusive (Tesuque residuals extend through 2050) |
| Number format | `0.000` | 3 decimal places for AF |

### Core (2003) Analytical Residuals

**Rio Pojoaque-Nambe** (decreasing, exhausted after 2015):
```python
CORE_2003_POJOAQUE = {
    1988: 40.432, 1989: 39.244, 1990: 37.971, 1991: 36.557, 1992: 34.928,
    1993: 33.112, 1994: 31.185, 1995: 29.226, 1996: 27.296, 1997: 25.439,
    1998: 23.678, 1999: 22.028, 2000: 20.491, 2001: 19.068, 2002: 17.753,
    2003: 16.543, 2004: 15.429, 2005: 14.404, 2006: 13.462, 2007: 12.595,
    2008: 11.797, 2009: 11.061, 2010: 10.383, 2011: 6.151, 2012: 4.693,
    2013: 3.234, 2014: 1.775, 2015: 0.316,
    # 2016+: 0 (residual effect exhausted)
}
```

**Rio Tesuque** (longer-lasting, continues through 2050; 63 entries):
```python
CORE_2003_TESUQUE = {
    1988: 21.015, 1989: 22.333, 1990: 23.391, 1991: 24.227, 1992: 24.868,
    1993: 25.327, 1994: 25.615, 1995: 25.747, 1996: 25.737, 1997: 25.608,
    1998: 25.378, 1999: 25.067, 2000: 24.691, 2001: 24.265, 2002: 23.800,
    2003: 23.308, 2004: 22.797, 2005: 22.273, 2006: 21.743, 2007: 21.212,
    2008: 20.683, 2009: 20.157, 2010: 19.639, 2011: 19.258, 2012: 18.767,
    2013: 18.276, 2014: 17.785, 2015: 17.295, 2016: 16.804, 2017: 16.313,
    2018: 15.822, 2019: 15.331, 2020: 14.841, 2021: 14.350, 2022: 13.859,
    2023: 13.368, 2024: 12.877, 2025: 12.387, 2026: 11.896, 2027: 11.405,
    2028: 10.914, 2029: 10.424, 2030: 9.933, 2031: 9.442, 2032: 8.951,
    2033: 8.460, 2034: 7.970, 2035: 7.479, 2036: 6.988, 2037: 6.497,
    2038: 6.006, 2039: 5.516, 2040: 5.025, 2041: 4.534, 2042: 4.043,
    2043: 3.552, 2044: 3.062, 2045: 2.571, 2046: 2.080, 2047: 1.589,
    2048: 1.098, 2049: 0.608, 2050: 0.117,
    # 2051+: 0.0 (residual effect exhausted)
}
```

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `generate_table3_data()` shall accept parsed post-processor output and a year, and return a dict with `pojoaque` and `tesuque` sub-dicts each containing `residual_af`, `superposition_af`, and `total_impact_af` | Return structure matches documented schema |
| R2 | Superposition values shall be computed by extracting monthly cfs from `R POJOAQUE` and `R TESUQUE` stream labels, then converting to annual AF via `cfs_monthly_to_af_annual()` | Annual AF matches hand calculation within 0.001 AF |
| R3 | Residual values shall be looked up from `CORE_2003_POJOAQUE` and `CORE_2003_TESUQUE` via `get_analytical_residual()` | Pojoaque returns 0.0 for years > 2015; Tesuque returns dict value through 2050, then 0.0 |
| R4 | Total impact shall equal `residual_af + superposition_af` exactly (no rounding) | `total_impact_af == residual_af + superposition_af` |
| R5 | `load_historical_table3()` shall parse a prior year's Table 3 XLSX and return a nested dict keyed by year | Returns correct values for years 1988–2023 from baseline |
| R6 | Historical values (years < processing_year) shall be preserved verbatim from prior year's Table 3 | Byte-level comparison of historical rows |
| R7 | `write_table3_xlsx()` shall produce a formatted XLSX with merged headers, column structure, and 0.000 number format | File opens in Excel with correct formatting |
| R8 | Leap year handling: February shall use 29 days for leap years (2024, 2028, etc.) and 28 days for non-leap years | Feb cfs→AF conversion uses correct day count |
| R9 | Zero residuals shall render as empty cells (not "0.000") matching the validation file pattern | Cells for years > 2015 (Pojoaque) show blank |
| R10 | Column headers shall include dynamic year range: `"Impact of 1988–{processing_year} Pumping (Superposition)"` | Header text matches processing year |

---

## 5. Worked Example

### Input

Parsed post-processor output for 2025 (hypothetical monthly cfs values for R POJOAQUE):
```
jan: 0.08, feb: 0.08, mar: 0.08, apr: 0.08, may: 0.08,
jun: 0.08, jul: 0.08, aug: 0.08, sep: 0.08, oct: 0.08,
nov: 0.08, dec: 0.08
```

### Calculation Steps

```
Step 1: Convert monthly cfs to AF (2025 is non-leap year, Feb = 28 days)
  Jan: 0.08 * 31 * 86400 / 43560 = 0.08 * 31 * 1.9835 = 4.919 AF
  Feb: 0.08 * 28 * 86400 / 43560 = 0.08 * 28 * 1.9835 = 4.443 AF
  Mar: 0.08 * 31 * 1.9835 = 4.919 AF
  Apr: 0.08 * 30 * 1.9835 = 4.760 AF
  ... (remaining months)

Step 2: Sum monthly AF to annual superposition
  Annual_superposition_AF = SUM(all 12 months) ≈ 57.918 AF

Step 3: Look up analytical residual for Pojoaque 2025
  CORE_2003_POJOAQUE.get(2025, 0.0) = 0.0 (exhausted after 2015)

Step 4: Calculate total impact
  Total = 0.0 + 57.918 = 57.918 AF

Step 5: Look up analytical residual for Tesuque 2025
  CORE_2003_TESUQUE[2025] = 12.387 AF

Step 6: (Repeat steps 1-2 for R TESUQUE cfs values to get Tesuque superposition)
```

### Expected Output
```python
{
    "pojoaque": {
        "residual_af": 0.0,
        "superposition_af": 57.918,  # from monthly cfs conversion
        "total_impact_af": 57.918
    },
    "tesuque": {
        "residual_af": 12.387,
        "superposition_af": <from MODFLOW>,
        "total_impact_af": 12.387 + <superposition>
    }
}
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Modify | `stream_depletions.py` | Add/maintain `generate_table3_data()`, `load_historical_table3()`, `write_table3_xlsx()`, `print_table3_verification()` |
| Modify | `step4_generate_depletion_tables.py` | Call `write_table3_xlsx()` with proper chaining arguments |

### Function Inventory

| Function | Lines | Purpose |
|----------|-------|---------|
| `load_historical_table3()` | ~100 | Parse prior year's Table 3 XLSX into nested dict |
| `generate_table3_data()` | ~90 | Combine residuals + superposition for one year |
| `print_table3_verification()` | ~20 | Console output for verification |
| `write_table3_xlsx()` | ~200 | Full XLSX generation with formatting and chaining |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_stream_depletions.py -v --tb=short -k "table3"
pytest tests/test_generate_depletion_tables.py -v --tb=short
ruff check stream_depletions.py step4_generate_depletion_tables.py
mypy stream_depletions.py step4_generate_depletion_tables.py
```

Expected output:
- All `table3`-related tests pass
- Table 3 XLSX matches validation baseline within tolerance (±0.001 AF)
- No ruff or mypy errors

---

## 8. Known Gotchas

- [ ] **Annotated cell values:** Historical Table 3 files may contain annotated strings like `"57.182** (57.185)"` with asterisk markers. The parser must extract the first numeric value via regex.
- [ ] **NaN residuals:** In the baseline XLSX, residual cells for years after 2015 (Pojoaque) may be NaN or empty. Treat as 0.0 when loading, and render as empty cells when writing.
- [ ] **Leap year awareness:** `generate_table3_data()` uses `calendar.isleap(year)` to select the correct days-per-month list. The `cfs_monthly_to_af_annual()` function's `use_leap_year` parameter must match.
- [ ] **Year range 1988–2050:** Table 3 includes projections through 2050 (matching the extent of `CORE_2003_TESUQUE`), even when processing year is earlier. Future years use MODFLOW projections from the same run. Tesuque residuals reach 0.117 AF in 2050 and are 0.0 beyond.
- [ ] **Chaining fallback order:** Try prior year's output first (`TABLE_3_..._2024.xlsx`), then fall back to validation baseline (`Table_3_expected.xlsx`). This two-tier fallback is critical for first-time runs.
- [ ] **Zero vs empty:** Pojoaque residual = 0 renders as an empty cell (no value), not as "0.000". This matches the validation file's visual pattern.
- [ ] **Dynamic column headers:** The "Impact of 1988–{year} Pumping" header must reflect the processing year, not a hardcoded value.
- [ ] **Excel styling:** Font is Aptos, headers use 12pt bold, data uses 11pt, totals are bold. Number format is `0.000`. Borders use medium for headers and hair for data rows.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Historical rows (1988 to N-1) | Prior year's Table 3 XLSX (verbatim) | Year N's Table 3 XLSX (includes N's fresh row) |
| Current year row (year N) | `generate_table3_data()` from MODFLOW run | `generate_table3_data()` from new MODFLOW run |
| Projection rows (N+1 to 2030) | `generate_table3_data()` from same MODFLOW run | `generate_table3_data()` from new MODFLOW run |
| Residual values | `CORE_2003_POJOAQUE` / `CORE_2003_TESUQUE` dicts | Same dicts (static) |
| Column header year range | "1988–N" | "1988–(N+1)" |

**Key principle:** Historical rows are never recalculated. They are loaded from the prior year's output and written verbatim. Only the processing year and future projections use current MODFLOW results.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 -c "
from stream_depletions import parse_postprocessor_output, generate_table3_data, write_table3_xlsx
data = parse_postprocessor_output('output/modflow/2024/modflow/depletions/CY2024')
t3 = generate_table3_data(data, 2024)
print(f'Pojoaque total: {t3[\"pojoaque\"][\"total_impact_af\"]:.3f} AF')
print(f'Tesuque total:  {t3[\"tesuque\"][\"total_impact_af\"]:.3f} AF')
"
```

Expected result:
- Pojoaque total ≈ 60.797 AF (for 2024)
- Tesuque total ≈ values matching `validation/2024/expected_outputs/Table_3_expected.xlsx`

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-03 | Stream depletion science: superposition principle, Core (2003) residuals, cfs→AF conversion |
| DS-04 | Year-chaining architecture: historical preservation rules, chaining resolution order |
| IS-06 | Upstream dependency: provides parsed post-processor output (`parse_postprocessor_output()`) |
| IS-07 | Library dependency: provides `cfs_to_acre_feet()`, `cfs_to_af()`, `cfs_monthly_to_af_annual()`, `get_analytical_residual()` |
| IS-09 | Sibling: Tables 4 & 5 follow similar chaining and XLSX export patterns |
| IS-10 | Downstream: test suite includes Table 3 verification tests |
