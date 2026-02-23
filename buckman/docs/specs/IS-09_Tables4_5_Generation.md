# IS-09: Tables 4 & 5 Generation

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement Table 4 (Rio Grande depletions above/below Otowi Gage) and Table 5 (La Cienega Springs cumulative depletions) data generation and XLSX writing in `stream_depletions.py`.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-07: Stream depletion parsing and Table 3 generation (provides `parse_postprocessor_output()`, `cfs_to_af()`, `cfs_monthly_to_af_annual()`, and Otowi cell constants)
- IS-08: Table 3 XLSX writing (provides `write_table3_xlsx()` and the chaining pattern)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Post-processor output | `output/modflow/{year}/depletions/CY{year}` | FORTRAN sfmodflx output with cell-level cfs |
| Validation Table 4 | `validation/TABLE 4 - Rio Grande, above below Otowi.xlsx` | Expected 2024 Table 4 output |
| Validation Table 5 | `validation/Table 5 - La Cienega Spring.jpg` | Expected 2024 Table 5 image |
| Prior year Table 5 | `output/depletion/TABLE_5_La_Cienega_Springs_{year-1}.xlsx` | Chaining source for historical years |

### Domain Knowledge
- See DS-03 Section 3 for Otowi cell classification (above/below)
- See DS-03 Section 4 for La Cienega Springs GHB cell mapping
- See DS-02 Section 2 for cfs-to-AF conversion factor derivation

---

## 3. Context for Claude Code

Table 4 reports Rio Grande stream depletions caused by Buckman wellfield pumping, classified as above or below Otowi Gage. Otowi Gage is the accounting point for New Mexico's Rio Grande Compact delivery obligations to Texas -- depletions below Otowi are chargeable against NM's allocation.

Table 5 reports cumulative La Cienega Springs depletions since 2004. These are small values (3-5 AF total) representing long-distance aquifer propagation effects. Values are cumulative, meaning each year's value equals the previous year's cumulative plus the annual increment.

### Key Equations (Inline)

```
CFS to AF (monthly):  AF = cfs * days_in_month * 86400 / 43560
                       (1 cfs-day = 1.9835 AF)

Annual AF from monthly cfs:  total_af = SUM over 12 months of (cfs_i * days_i * 1.9835)

Table 5 annual increment:  increment = cumulative(year) - cumulative(year-1)
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| DAYS_VALIDATION | [31,28,31,30,31,30,31,31,30,31,30,31] | days (non-leap) |
| ABOVE_OTOWI_CELLS | 10 cells: (1,1,16) through (1,10,12) | (layer, row, col) |
| BELOW_OTOWI_CELLS | 16 cells: (1,11,11) through (1,23,3) | (layer, row, col) |
| BUCKMAN_WELLS_CELL | (1, 13, 11) | (layer, row, col) |
| Key counter start | 2089 | integer |
| Stream summary keys | [2135, 2133, 2137, 2134, 2136] | for RIO GRANDE, R POJOAQUE, LC SPRINGS, R TESUQUE, RIV TOTAL |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `generate_table4_data(parsed_data, year)` returns cell-level + aggregated Rio Grande depletions | Returns dict with `cell_data` (44 entries), `stream_summaries` (5 streams), above/below AF totals, and Buckman cell data |
| R2 | `write_table4_xlsx(parsed_data, output_path, year)` writes complex Excel with cell data, stream summaries, AF calculations, and cross-check formulas | Output file has: Row 1 headers, Rows 2-45 cell data (6-decimal cfs), Rows 46-50 stream summaries, days row, cfs section, AF section, cross-check formula rows. Font: Aptos 11. |
| R3 | `generate_table5_data(parsed_data, year)` returns La Cienega Springs cumulative depletion | Returns dict with `monthly_cfs` (12 values), `annual_af`, `previous_cumulative_af`, `cumulative_af` |
| R4 | `write_table5_xlsx(output_path, parsed_data, processing_year, years, historical_baseline)` writes Table 5 with year-chaining | Years < processing_year from prior year's Table 5; years >= processing_year from parsed_data. Cross-check columns: annual delta, cumulative check, delta B-D (should be 0). Format: 0.00. |
| R5 | `load_historical_table5(baseline_path)` loads prior year's Table 5 cumulative values | Returns dict mapping year (int) to cumulative AF (float). Falls back to LA_CIENEGA_CUMULATIVE dict if file missing. |

---

## 5. Worked Example

### R1: generate_table4_data

#### Input
```python
# parsed_data from parse_postprocessor_output("output/modflow/2024/depletions/CY2024")
# Contains year_data[2024] with cell keys like "1 9 14" and stream names like "RIO GRANDE"
```

#### Calculation Steps
```
Step 1: Collect all cells from parsed_data[2024], excluding stream names
        -> 44 cells total

Step 2: Classify cells by Otowi status
        - above_keys = {"1 1 16", "1 2 16", ..., "1 10 12"}  (10 cells)
        - below_keys = {"1 11 11", "1 12 11", ..., "1 23 3"}  (16 cells)
        - non_otowi = remaining 18 cells

Step 3: Sort: non-Otowi by (row,col), then above by (row,col), then below by (row,col)
        -> ordered_cells list of 44 tuples

Step 4: Assign keys starting at 2089
        - Cell 0 -> key 2089, Cell 1 -> key 2090, ..., Cell 43 -> key 2132

Step 5: Extract stream summaries for RIO GRANDE, R POJOAQUE, LC SPRINGS, R TESUQUE, RIV TOTAL
        - Each has 12 monthly cfs values

Step 6: Sum above-Otowi cells per month -> above_cfs[12]
        Sum below-Otowi cells per month -> below_cfs[12]

Step 7: Convert to AF:
        above_af[0] = above_cfs[0] * 31 * 86400 / 43560  (January)
        2024 example: above_otowi_annual_af ~ 101.43 AF
                      below_otowi_annual_af ~ 842.94 AF
```

#### Expected Output
```python
{
    "cell_data": [44 dicts with key, year, lay, row, col, monthly_cfs, otowi],
    "stream_summaries": {"RIO GRANDE": [12 floats], ...},
    "days_per_month": [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
    "above_otowi_cfs": [12 floats],
    "below_otowi_cfs": [12 floats],
    "above_otowi_af": [12 floats],
    "below_otowi_af": [12 floats],
    "above_otowi_annual_af": 101.43,   # approximate
    "below_otowi_annual_af": 842.94,  # approximate
    "total_rg_af": [12 floats],
    "total_rg_annual_af": 944.37,     # approximate
    "buckman_cfs": [12 floats],
    "buckman_af": [12 floats],
    "buckman_annual_af": float,
}
```

### R3: generate_table5_data

#### Input
```python
# parsed_data[2024]["LC SPRINGS"] contains monthly cfs values
# e.g., {"jan": 0.000052, "feb": 0.000053, ..., "dec": 0.000058}
```

#### Calculation Steps
```
Step 1: Extract LC SPRINGS monthly cfs -> lc_springs_cfs = [0.000052, 0.000053, ...]

Step 2: Convert to annual AF using calendar days for 2024 (leap year):
        cumulative_af = sum(cfs_i * days_i * 86400 / 43560 for i in 0..11)
        = sum(cfs_i * days_i * 1.9835)
        ~ 3.74 AF (this is CUMULATIVE from all pumping since 1988)

Step 3: Get previous cumulative from LA_CIENEGA_CUMULATIVE[2023] = 3.54

Step 4: annual_af = cumulative_af - previous_cumulative = 3.74 - 3.54 = 0.20 AF
```

#### Expected Output
```python
{
    "year": 2024,
    "monthly_cfs": [0.000052, 0.000053, ..., 0.000058],
    "annual_af": 0.20,
    "previous_cumulative_af": 3.54,
    "cumulative_af": 3.74,
}
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Modify | `stream_depletions.py` | Add `generate_table4_data()`, `write_table4_xlsx()`, `generate_table5_data()`, `write_table5_xlsx()`, `load_historical_table5()` |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_stream_depletions.py -v --tb=short -k "table4 or table5"
ruff check stream_depletions.py
mypy stream_depletions.py
```

Expected output:
- `generate_table4_data()` returns dict with 44 cell entries and correct above/below AF totals
- `write_table4_xlsx()` creates XLSX with ~70 rows including cell data, summaries, AF sections, and cross-check formulas
- `generate_table5_data()` returns correct cumulative AF matching LA_CIENEGA_CUMULATIVE[year]
- `write_table5_xlsx()` creates XLSX with years 2004-2030 and cross-check columns

---

## 8. Known Gotchas

- [ ] Table 4 uses DAYS_VALIDATION (non-leap year: Feb=28) for the days-per-month row, NOT the actual calendar days for the processing year. This matches the validation file convention.
- [ ] Stream name splits in Table 4 XLSX are cosmetic artifacts of FORTRAN fixed-width output. "RIO GRANDE" becomes "0  RI" / "O GRA" / "NDE" across columns 3-5. These must be reproduced exactly.
- [ ] Table 5 cumulative values from MODFLOW are already cumulative from all pumping since 1988, not annual increments. The annual_af is computed by subtraction from the prior year.
- [ ] Table 5 chaining: years before processing_year are preserved from the prior year's output, not recomputed. This locks in historical values at the time they were produced.
- [ ] Buckman wells cell (1,13,11) is also a BELOW_OTOWI cell -- it appears both in the cell_data list and is extracted separately for the Buckman row.
- [ ] Cross-check formula rows use Calibri 9pt italic gray font, not Aptos 11pt.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Table 4 cell data | Computed from current MODFLOW run | Computed fresh (no chaining) |
| Table 5 years < N | Prior year's Table 5 XLSX | Prior year's Table 5 XLSX |
| Table 5 year >= N | Current MODFLOW run via `cfs_monthly_to_af_annual()` | Current MODFLOW run |
| Table 5 fallback | LA_CIENEGA_CUMULATIVE dict | LA_CIENEGA_CUMULATIVE dict |

Table 4 does NOT chain -- it is fully computed from the current year's MODFLOW output. Table 5 chains cumulative values to ensure historical years remain locked.

---

## 10. Verification

```bash
python step4_generate_depletion_tables.py --year 2024
diff <(python -c "
import openpyxl
wb = openpyxl.load_workbook('output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx', data_only=True)
ws = wb.active
for row in ws.iter_rows(min_row=56, max_row=58, min_col=18, max_col=18, values_only=True):
    print(f'{row[0]:.3f}')
") <(echo -e "101.430\n842.940\n944.370")
```

Expected result: Above/below/total Otowi AF values within 0.01 AF of validation reference.

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-03 | Otowi cell classification and La Cienega GHB cell mapping |
| DS-02 | CFS-to-AF conversion factor derivation |
| IS-07 | Provides parse_postprocessor_output() and extract_otowi_depletions() |
| IS-08 | Table 3 XLSX writing pattern (chaining, styling) |
| IS-10 | Test coverage for generate_table4_data and generate_table5_data |
