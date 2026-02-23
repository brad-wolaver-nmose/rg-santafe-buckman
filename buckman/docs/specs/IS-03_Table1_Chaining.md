# IS-03: Table 1 Chaining

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement Table 1 generation -- load a prior-year XLSX template containing the historical annual pumping record (1988-present), append a new row with the current year's well-by-well annual AF totals from Table 2 output, preserve all historical rows unchanged, add statistics and ranking rows, and export to both CSV and formatted XLSX.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project Scaffold & Constants (provides `src/constants.py` with WELL_OSE_MAP, WELL_NAME_MAP)
- IS-02: CSV Ingestion & Table 2 (produces `{year}_Table_2_output.csv` with monthly AFY grid and annual totals per well)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Table 1 template (primary) | `validation/Table_1_data_afy_{year}.xlsx` | Historical AFY data Excel file (1988-{year-1}) for first-time processing |
| Table 1 template (fallback) | `output/ingested_data/{year-1}_Table_1_updated.xlsx` | Prior year's Table 1 output (used for year-chaining when no validation file exists). **Known issue:** The write path is flat (`output/ingested_data/{year}_Table_1_updated.xlsx`), but the fallback lookup path in code uses a subdirectory (`output/ingested_data/{year-1}/{year-1}_Table_1_updated.xlsx`). This path discrepancy is a known code bug. |
| Table 2 output | `output/ingested_data/{year}_Table_2_output.csv` | Current year's monthly AFY grid -- the `Total` column provides annual well totals consumed here |

### Domain Knowledge
- See DS-01 for well numbering conventions (Well 3 is labeled "3/3A" in Table 1)
- See DS-02 for AFY volume units and conversion factors
- See DS-04 Section 6.1 for Table 1 chaining architecture and year-chaining rules

---

## 3. Context for Claude Code

Table 1 is the historical annual pumping record for the Buckman Well Field, spanning 1988 to the present year. It is the single authoritative registry of how much water each well pumped in each year. Every year, the pipeline loads the prior year's Table 1 output, appends one new row for the current year, recalculates statistics, and writes updated CSV and XLSX files.

**Structure:**
- **Data rows:** Years 1988 through current year (one row per year, one column per well)
- **Average rows:** "Average, 1988-{year}" and "Average, 2022-{year}" (using Excel AVERAGE formulas, not static values)
- **Statistics rows:** Per-well percentage of annual total, Wells 10-13 group sum and percentage, Wells 1,7,8 group sum and percentage
- **Sort column:** All years' totals sorted descending (column T), with ranks for 2013+ years (column U) since Wells 10-13 came online in 2013

**Template resolution order:**
1. Primary: `validation/Table_1_data_afy_{year}.xlsx` (hand-prepared file for baseline year 2024)
2. Fallback: `output/ingested_data/{year-1}_Table_1_updated.xlsx` (chained from prior year's run)
3. Neither: pipeline halts with forensic error message

**Current-year data source:** Annual AFY totals per well are computed by summing all 12 monthly MG values from the IS-02 monthly aggregation, converting each to AF via pint, and passing the 13-well dict to `generate_table1_output()`.

### Key Equations (Inline)

```
Well percentage:      pct_i = (well_i_AFY / total_AFY) * 100
                      where total_AFY = sum of all 13 wells for current year

Wells 10-13 sum:      sum_10_13 = well_10 + well_11 + well_12 + well_13
Wells 10-13 pct:      pct_10_13 = sum_10_13 / total_AFY * 100

Wells 1,7,8 sum:      sum_1_7_8 = well_1 + well_7 + well_8
Wells 1,7,8 pct:      pct_1_7_8 = sum_1_7_8 / total_AFY * 100

Year rank:            Rank all years by Total AFY ascending (1 = lowest pumping year)
                      All years get a rank; Sort column T displays totals descending;
                      Column U shows rank only for years >= 2013
```

### Key Constants (Inline)

| Constant | Value | Notes |
|----------|-------|-------|
| Well 3 column header | `"3/3A"` | String, not integer 3 -- historical convention for combined wells 3 and 3A |
| Year column header | `"Well:"` | First column in Table 1 template DataFrame |
| Wells 10-13 start year | 2013 | Wells 10-13 came online in 2013; ranking in column U is limited to 2013+ |
| MG_TO_AF_FACTOR | 3.06889 | AF/MG -- used upstream in IS-02 for the conversion that feeds Table 1 |
| Total column | `"Total"` | Annual sum across all 13 wells |
| Sort column | `"Total, Sort"` | Rank index for year ordering |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `generate_table1_output(year_afy_data, year, output_dir)` loads Table 1 template from validation file (primary) or prior year output (fallback) | Template loads successfully; `table1_df` has all historical year rows; function returns `None` on success, `1` on failure |
| R2 | Read annual totals per well from `year_afy_data` dict (13 wells, AFY values) | `year_afy_data = {1: 601.276042, 2: 0.009202, ..., 13: 212.020480}` with all 13 keys present |
| R3 | Append new row for current year with Well 3 mapped to column `"3/3A"` | New row has `Well:` = year; `row_2024["3/3A"]` contains Well 3 value; all 13 well columns populated |
| R4 | If current year already exists in template, update in place (no duplicates) | Running twice for same year does not create duplicate rows; second run updates values |
| R5 | Preserve all historical rows exactly as they appear in the template | Compare rows 1988-{year-1}: values unchanged within floating-point precision (no rounding, no truncation) |
| R6 | Calculate Total column as sum of all 13 well values | `row_2024["Total"] == sum(year_afy_data.values())` rounded to 6 decimal places |
| R7 | Detect and recalculate missing Total values (NaN) in historical rows from well columns | Any year with NaN Total gets recalculated as `sum(wells 1-13)` with warning printed |
| R8 | Calculate Sort column: rank all years by Total AFY (1 = lowest pumping) | Year with lowest total gets rank 1; highest gets rank N; all years ranked |
| R9 | Add "% of Total" row: each well's percentage of current year's annual total | `sum(all_well_pcts) == "100.0%"`; row label is `"Pecent"` in XLSX (matching validation typo) |
| R10 | Add "Wells 10-13" sum row and "Wells 10-13 %" percentage row | Sum placed in well 10 column; percentage placed in well 10 column |
| R11 | Add "Wells 1,7,8" sum row and "Wells 1,7,8 %" percentage row | Sum placed in well 1 column; percentage placed in well 1 column |
| R12 | Write CSV: `{year}_Table_1_updated.csv` | CSV readable by `pd.read_csv()`; contains year data rows + statistics rows |
| R13 | Write XLSX: `{year}_Table_1_updated.xlsx` with Aptos font, medium/hair borders, `#,##0.00` number format | Visual comparison to `validation/Table_1_data_afy_2024.xlsx` matches styling |
| R14 | XLSX includes Average rows with Excel formulas (not static values) | "Average, 1988-{year}" uses `=AVERAGE(B2:B{last_row})`; "Average, 2022-{year}" uses last 3 rows |
| R15 | XLSX includes repeat header row and percentage row with Excel formulas | Percentage row formulas: `=B{last_year_row}/$O${last_year_row}` referencing current year data |
| R16 | XLSX column T: all years' totals sorted descending; column U: rank for years >= 2013 only | Sorted list is independent of data row order; column U populated only for 2013+ entries |
| R17 | Row count validation: output has exactly (prior year rows + 1) data rows | If template has 36 year rows (1988-2023), output has 37 year rows (1988-2024) |

---

## 5. Worked Example

### Input: Table 1 Template (1988-2023, 36 year rows)

```
Well:   1        2      3/3A     4      5      6      7       8       9      10      11      12     13     Total
1988    0.00     0.00   0.00     0.00   0.00   0.00   598.44  326.41  323.87 0.00    0.00    0.00   0.00   1248.72
1989    0.00     0.00   0.00     0.00   0.00   0.00   1142.91 585.99  326.80 0.00    0.00    0.00   0.00   2055.70
...
2023    451.22   0.00   77.80    0.00   0.00   0.00   17.22   0.37    53.57  211.08  185.44  103.37 195.30 1295.48
```

### Input: Table 2 Annual Totals for 2024 (from IS-02 output)

```python
year_afy_data = {
    1: 601.276042,   2: 0.009202,   3: 0.033721,
    4: 0.000000,     5: 0.000000,   6: 0.000000,
    7: 57.637710,    8: 54.836285,  9: 60.279885,
    10: 101.200850,  11: 73.639045, 12: 0.000000,
    13: 212.020480
}
total_afy = sum(year_afy_data.values())  # = 1372.954123 AF
```

### Calculation Steps

```
Step 1: Load template
  Read validation/Table_1_data_afy_2024.xlsx
  -> 36 year rows (1988-2023), columns: Well:, 1, 2, 3/3A, 4-13, Total

Step 2: Build new row
  row_2024 = {
      "Well:": 2024,
      1: 601.276042,  2: 0.009202,  "3/3A": 0.033721,
      4: 0.000000,    5: 0.000000,  6: 0.000000,
      7: 57.637710,   8: 54.836285, 9: 60.279885,
      10: 101.200850, 11: 73.639045, 12: 0.000000,
      13: 212.020480,
      "Total": 1372.954123
  }
  Note: Well 3 value goes to column "3/3A" (not column 3)

Step 3: Check for duplicate
  2024 not in existing years -> append (not update)
  Result: 37 year rows (1988-2024)

Step 4: Calculate Sort column (rank by Total ascending, 1 = lowest)
  Rank all 37 years by Total AFY:
  Rank 1 = lowest total (~748 AF, e.g., 2020)
  ...
  Rank 37 = highest total (~2648 AF, e.g., 2002)
  2024 rank ~= 21 of 37

Step 5: Calculate statistics for 2024
  % of Total:  Well 1 = 601.28 / 1372.95 * 100 = 43.8%
               Well 2 = 0.01 / 1372.95 * 100 = 0.0%
               ...
               Well 13 = 212.02 / 1372.95 * 100 = 15.4%
  Wells 10-13: 101.20 + 73.64 + 0.00 + 212.02 = 386.860375 AF (28.2%)
  Wells 1,7,8: 601.28 + 57.64 + 54.84 = 713.750037 AF (52.0%)
```

### Expected Output: Table 1 CSV (2024_Table_1_updated.csv)

```csv
Well:,1,2,3/3A,4,5,6,7,8,9,10,11,12,13,Total,"Total, Sort"
1988,0.00,0.00,0.00,0.00,0.00,0.00,598.44,326.41,323.87,0.00,0.00,0.00,0.00,1248.72,1
...
2023,451.22,0.00,77.80,0.00,0.00,0.00,17.22,0.37,53.57,211.08,185.44,103.37,195.30,1295.48,20
2024,601.276042,0.009202,0.033721,0.0,0.0,0.0,57.63771,54.836285,60.279885,101.20085,73.639045,0.0,212.02048,1372.954123,21
% of Total,43.8%,0.0%,0.0%,0.0%,0.0%,0.0%,4.2%,4.0%,4.4%,7.4%,5.4%,0.0%,15.4%,100.0%,
Wells 10-13,,,,,,,,,,386.860375,,,,
Wells 10-13 %,,,,,,,,,,28.2%,,,,
"Wells 1,7,8",713.750037,,,,,,,,,,,,,
"Wells 1,7,8 %",52.0%,,,,,,,,,,,,,
```

### XLSX Average Row Formulas

```
Row 39 (Average, 1988-2024):
  Cell B39 = =AVERAGE(B2:B38)      -- averages well 1 across all 37 years
  Cell O39 = =AVERAGE(O2:O38)      -- averages Total column

Row 40 (Average, 2022-2024):
  Cell B40 = =AVERAGE(B36:B38)     -- averages well 1 across last 3 years
  Cell O40 = =AVERAGE(O36:O38)     -- averages Total column
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Modify | `step1_ingest_buckman_data.py` | Contains `generate_table1_output()` and `write_table1_xlsx()` functions |
| Create | `tests/test_ingest_buckman_data.py` | Unit tests for Table 1 chaining, row preservation, statistics, and duplicate handling. Note: Table 1 tests are in `tests/test_ingest_buckman_data.py`, not a separate `tests/test_table1.py`. |

### Output files generated at runtime
| File | Path | Description |
|------|------|-------------|
| Table 1 CSV | `output/ingested_data/{year}_Table_1_updated.csv` | Historical AFY data with new year appended + statistics rows |
| Table 1 XLSX | `output/ingested_data/{year}_Table_1_updated.xlsx` | Formatted Excel with Aptos font, borders, formulas |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_ingest_buckman_data.py -v --tb=short
ruff check step1_ingest_buckman_data.py
mypy step1_ingest_buckman_data.py

# End-to-end run (requires IS-02 output and template file):
python3 step1_ingest_buckman_data.py --year 2024
```

Expected output:
- Table 1 contains all historical years (1988-2023) plus 2024 = 37 data rows
- 2024 row total = 1372.95 AFY (matching Table 2 annual total)
- Statistics rows: Wells 10-13 = 386.86 AF (28.2%), Wells 1,7,8 = 713.75 AF (52.0%)
- XLSX formatting matches validation file styling (Aptos font, medium/hair borders, `#,##0.00`)
- Sort column ranks 37 years; column U shows ranks only for 2013+ (12 years)
- Chaining test: process year 2024, then process year 2025 using 2024's output as template

---

## 8. Known Gotchas

- [ ] Well 3 column header is `"3/3A"` (string), not integer `3`. The DataFrame has mixed column types: `"Well:"` (string), `1`, `2` (int), `"3/3A"` (string), `4`-`13` (int), `"Total"` (string). This requires careful handling when building `row_2024` dict: use `col_name = '3/3A' if well_num == 3 else well_num`.
- [ ] The validation file's "Pecent" row label is a deliberate match to the original hand-built file's typo. Do not correct to "Percent" -- the XLSX must match the validation file exactly.
- [ ] Average rows use Excel formulas (`=AVERAGE(...)`), not pre-computed values. When openpyxl writes these formulas, Excel must open the file and recalculate before the values appear. The CSV contains the computed static values from Python.
- [ ] When the template already has the current year (re-run scenario), the code detects the existing row via `lambda x: isinstance(x, (int, float)) and not pd.isna(x) and int(x) == year` and updates in place. This prevents duplicate year rows.
- [ ] NaN values in the Total column for historical years can occur when the template was exported from Excel without recalculating formulas. The code detects these and recalculates from well columns with a warning.
- [ ] The XLSX Sort column (column T) contains all years' totals sorted descending, independently of the data row order. Column U contains rank integers only for the last N entries corresponding to years >= 2013 (when wells 10-13 came online). Rank is "position from bottom" in the sorted list.
- [ ] The XLSX average rows reference dynamic ranges: "Average, 1988-{year}" uses `B2:B{last_year_row}` (the full range), while "Average, 2022-{year}" uses only the last 3 year rows: `B{last_year_row-2}:B{last_year_row}`.
- [ ] The `year_afy_data` dict passed to `generate_table1_output()` must have AFY values rounded to 6 decimal places to match the precision of Table 2 output. The Total is calculated as `sum(year_afy_data.values())`, also rounded to 6 places.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Table 1 template | `validation/Table_1_data_afy_{N}.xlsx` (first time) OR `output/ingested_data/{N-1}_Table_1_updated.xlsx` (chained) | `output/ingested_data/{N}_Table_1_updated.xlsx` |
| Current year AFY | Computed from year N's Table 2 monthly aggregation | Computed from year N+1's Table 2 monthly aggregation |
| Historical rows (1988 through N-1) | Preserved verbatim from template | Preserved verbatim from year N output |
| Statistics rows | Recalculated for year N's totals | Recalculated for year N+1's totals |
| Sort/rank column | All years re-ranked including year N | All years re-ranked including year N+1 |
| Average row ranges | Extend to include year N | Extend to include year N+1 |

**Critical chaining logic:**
1. For the baseline year (2024): try `validation/Table_1_data_afy_2024.xlsx` (contains 1988-2023, 36 rows)
2. For subsequent years (2025+): try `validation/Table_1_data_afy_2025.xlsx` first, then fall back to `output/ingested_data/2024_Table_1_updated.xlsx` (contains 1988-2024, 37 rows)
3. Each year's output becomes the next year's input template, accumulating the full historical record
4. Row count invariant: `output_rows = template_year_rows + 1` (unless template already had the current year, in which case `output_rows = template_year_rows`)

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 step1_ingest_buckman_data.py --year 2024 && \
python3 -c "
import pandas as pd
df = pd.read_csv('output/ingested_data/2024_Table_1_updated.csv')

# Count year rows (filter out stats rows)
year_rows = df[df['Well:'].apply(lambda x: str(x).replace('.0','').isdigit())]
print(f'Historical years: {len(year_rows)}')
assert len(year_rows) == 37, f'Expected 37 years, got {len(year_rows)}'

# Check 2024 row
row_2024 = year_rows[year_rows['Well:'].astype(float).astype(int) == 2024]
assert len(row_2024) == 1, f'Expected 1 row for 2024, got {len(row_2024)}'
total = float(row_2024.iloc[0]['Total'])
print(f'2024 Total: {total:.2f} AFY')
assert abs(total - 1372.95) < 1.0, f'Total mismatch: {total}'

# Check no duplicate years
years = year_rows['Well:'].astype(float).astype(int).tolist()
assert len(years) == len(set(years)), 'Duplicate year rows found'

print('PASS')
"
```

Expected result: `Historical years: 37`, `2024 Total: 1372.95 AFY`, `PASS`

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Well numbering conventions, "3/3A" historical naming |
| DS-02 | AFY volume units, MG-to-AF conversion factor |
| DS-04 | Year-chaining architecture (Section 6.1: Table 1 chaining rules) |
| IS-01 | Constants module (WELL_OSE_MAP, WELL_NAME_MAP for well numbering) |
| IS-02 | Table 2 output provides annual totals per well consumed by Table 1 |
| IS-04 | WEL file reads Table 2 CSV directly (not Table 1), but Table 1 provides historical pumping context |
