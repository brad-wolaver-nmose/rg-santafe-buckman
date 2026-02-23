# IS-02: CSV Ingestion & Table 2

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `step1_ingest_buckman_data.py` -- CSV parsing, daily data validation, monthly aggregation with pint dimensional analysis, Table 2 generation (CSV and formatted XLSX), and annual sum verification.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project Scaffold & Constants (provides `src/constants.py`)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| Source CSV | `input/csv/Buckman_Well_Prod_{year}.csv` | Daily MGD values for 13 wells, provided by City of Santa Fe |
| Table 1 template | `validation/Table_1_data_afy_{year}.xlsx` OR `output/ingested_data/{year-1}_Table_1_updated.xlsx` | Historical AFY data for Table 1 chaining (see IS-03) |

### Domain Knowledge
- See DS-01 for well numbering and CSV column format
- See DS-02 for MG-to-AF conversion and tolerance rationale

---

## 3. Context for Claude Code

The City of Santa Fe provides a CSV file each year with daily pumping data for the 13 Buckman wells. Each row is one day, each column is one well's flow in MGD (million gallons per day). The CSV also contains a "Sum" row with annual totals per well (in MG) and a "BWP|Flow Mgd|MGD|Formula" column with daily total production.

This script aggregates daily MGD into monthly MG (dimensional analysis: sum(MGD) * 1 day = MG), converts to acre-feet, and produces Table 2 (monthly AFY grid for 13 wells).

### Key Equations (Inline)

```
Monthly volume (MG):  MG = sum(daily_MGD_values) * 1 day
                      (pint: sum(MGD * ureg.day) -> million_gallon)

MG to AF:             AF = MG * 3.06889
                      (pint: mg_qty.to(ureg.acre_foot))

Three-tier daily verification:
  Tier 1 (Noise):     BWP > 0 and BWP < 0.0015 MGD -> INFO
  Tier 2 (Formula):   All wells = 0 and BWP >= 0.0015 MGD -> ERROR
  Tier 3 (Rounding):  |calc_sum - BWP| <= 0.001 -> OK
                      |calc_sum - BWP| <= 0.005 -> INFO
                      |calc_sum - BWP| > 0.005  -> ERROR
```

### Key Constants (Inline)

| Constant | Value | Units | Purpose |
|----------|-------|-------|---------|
| MG_TO_AF_FACTOR | 3.06889 | AF/MG | Volume conversion |
| NOISE_THRESHOLD_MGD | 0.0015 | MGD | Tier 1 database artifact threshold |
| DAILY_SUM_TOLERANCE_INFO_MGD | 0.001 | MGD | Tier 3 INFO threshold |
| DAILY_SUM_TOLERANCE_ERROR_MGD | 0.005 | MGD | Tier 3 ERROR threshold |
| ANNUAL_SUM_TOLERANCE_MG | 0.01 | MG | Annual sum verification tolerance |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `read_source_csv(csv_path) -> (daily_df, sum_series)` parses CSV, separates daily rows from summary rows | Returns DataFrame with 365/366 daily rows and Series with 13 annual MG totals |
| R2 | CSV first column (date range header) renamed to `Date`; daily rows have valid datetime; BWP total column renamed to `BWP_Total` | `daily_df['Date'].dtype == datetime64`, `'BWP_Total' in daily_df.columns` |
| R3 | `validate_daily_data(daily_df) -> flags_df` flags BLANK, NEGATIVE, NON_NUMERIC | flags_df has same shape as well columns; zero values are valid (not flagged) |
| R4 | `verify_daily_sums(daily_df) -> verification_df` applies three-tier severity | verification_df has columns: Date, Calculated_Sum, BWP_Total, Difference, Severity |
| R5 | `aggregate_monthly(daily_df, flags_df) -> dict[str, DataFrame]` groups by month | Returns dict with keys "01"-"12", each DataFrame has Well_Number, MG_Month (pint Quantity), Has_Flagged_Data |
| R6 | Monthly MG uses pint dimensional analysis: `sum(MGD * ureg.day)` | `monthly_data["01"].iloc[0]['MG_Month'].units == ureg.million_gallon` |
| R7 | `generate_table2_output(monthly_data, year, output_dir)` writes CSV and XLSX | CSV has 14 rows (13 wells + Total) x 14 columns (Well, JAN-DEC, Total) + summary rows |
| R8 | Table 2 XLSX uses Aptos font, `#,##0.00` number format, medium/hair borders | Visual comparison to validation/Table_2_2024.xlsx matches styling |
| R9 | `verify_annual_sums(monthly_data, sum_row)` checks 12-month totals vs CSV Sum row | All 13 wells within 0.01 MG tolerance |
| R10 | `generate_monthly_csv()` writes per-month CSV with OSE number, well name, MG, AF, data quality | 12 CSV files created in output directory |
| R11 | `generate_qa_summary()` writes input_summary.csv with flagged wells and daily mismatches | File created with two sections (or "No data quality issues found") |
| R12 | Main function accepts `--year` argument and orchestrates full pipeline | `python3 step1_ingest_buckman_data.py --year 2024` runs successfully |

---

## 5. Worked Example

### Input: Buckman #1, January 2024

```
Daily MGD values for 31 days (from CSV):
Day 1:  0.2057 MGD    Day 11: 0.1773 MGD    Day 21: 0.1832 MGD    Day 31: 0.1654 MGD
Day 2:  0.1925 MGD    Day 12: 0.0000 MGD    Day 22: 0.1745 MGD
...
(31 total daily values)
```

### Calculation Steps

```
Step 1: Sum daily MGD values for January
  sum(daily_mgd) = 5.503 MGD*days = 5.503 MG
  (Using pint: sum(0.2057 + 0.1925 + ... ) * ureg.MGD * ureg.day = 5.503 * ureg.MG)

Step 2: Convert MG to AF
  AF = 5.503 MG * 3.06889 AF/MG = 16.887963 AF
  (Using pint: (5.503 * ureg.million_gallon).to(ureg.acre_foot) = 16.887963 AF)

Step 3: Verify daily sum for January 1
  Calculated_Sum = BWell1 + BWell2 + ... + BWell13 = 0.2057 + 0 + ... = 0.4523 MGD
  BWP_Total = 0.4523 MGD (from CSV formula column)
  Difference = |0.4523 - 0.4523| = 0.0000 MGD
  Severity = OK (within 0.001 MGD)
```

### Expected Output: Table 2 CSV (2024_Table_2_output.csv)

```csv
Well,JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC,Total
1,16.887963,38.805796,41.370397,...,162.488610,...,0.000000,601.276042
2,0.000000,0.006135,0.000000,...,0.000000,...,0.000000,0.009202
...
13,18.099940,0.000000,4.293040,...,55.001150,...,0.000000,212.020480
Total,19.393860,39.388656,41.629337,...,302.058090,...,65.677300,1372.954123

Wells 10-13,386.860000,28.2%
Wells 1,7,8,713.750000,52.0%
```

### Three-Tier Daily Verification Example

```
Tier 1 (Noise): 2024-06-23 BWP=0.0009 MGD, all wells=0 -> INFO (below 0.0015 threshold)
Tier 2 (Formula): 2024-07-15 BWP=0.05 MGD, all wells=0 -> ERROR (formula inconsistency)
Tier 3 (Rounding): 2024-03-10 calc=4.523, BWP=4.524, diff=0.001 -> OK (within 0.001)
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `step1_ingest_buckman_data.py` | Main ingestion script with all functions |
| Create | `tests/test_step1.py` | Unit tests for CSV parsing, validation, aggregation |

### Output files generated at runtime
| File | Path | Description |
|------|------|-------------|
| Monthly CSVs | `output/ingested_data/{year}_{MM}_{MON}.csv` | 12 monthly per-well production files |
| Table 2 CSV | `output/ingested_data/{year}_Table_2_output.csv` | Monthly AFY grid |
| Table 2 XLSX | `output/ingested_data/{year}_Table_2_output.xlsx` | Formatted Excel version |
| QA summary | `output/ingested_data/input_summary.csv` | Flagged data and mismatches |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_step1.py -v --tb=short
ruff check step1_ingest_buckman_data.py
mypy step1_ingest_buckman_data.py

# End-to-end run (requires input CSV):
python3 step1_ingest_buckman_data.py --year 2024
```

Expected output:
- `2024_Table_2_output.csv` with 14 data rows + 3 summary rows
- `2024_Table_2_output.xlsx` with Aptos font formatting
- 12 monthly CSV files
- Annual verification: 13 wells OK
- Total annual pumping: ~1372.95 AFY (2024 data)

---

## 8. Known Gotchas

- [ ] Pint unit registry must define custom units: `million_gallon = 1e6 * gallon = MG` and `million_gallon_per_day = million_gallon / day = MGD`. These are not built into pint.
- [ ] CSV first column header contains a date range (e.g., "1/1/2024-12/31/2024"), not "Date". Must rename to "Date" after reading.
- [ ] Summary rows (Sum, Avg, Max, Min) are identified by non-parseable dates. Use `pd.to_datetime(errors='coerce')` to separate daily rows from summary rows.
- [ ] The BWP formula column header varies: `"BWP|Flow Mgd|MGD|Formula"`. Must use `CSV_TOTAL_COLUMN` constant.
- [ ] Zero values (0.0 MGD) are valid -- they mean the well was not pumping. Only NaN, negative, and non-numeric values get flagged.
- [ ] Table 2 XLSX: Well column contains integers (1-13), not strings. Summary rows use "Wells 10-13" string in Well column.
- [ ] The Table 2 XLSX summary area (Wells 10-13, Wells 1,7,8) is placed in columns Q-T, rows 14-15 -- separate from the main data grid.
- [ ] MG-to-AF conversion: use pint's `.to(ureg.acre_foot)` for dimensional safety, not manual multiplication. Both approaches should give the same result.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| Input CSV | `input/csv/Buckman_Well_Prod_{N}.csv` | `input/csv/Buckman_Well_Prod_{N+1}.csv` |
| Table 2 output | Computed from year N CSV | Computed from year N+1 CSV |
| Table 1 template | `validation/Table_1_data_afy_{N}.xlsx` | `output/ingested_data/{N}_Table_1_updated.xlsx` (output from year N) |

Table 2 is computed fresh each year from that year's CSV data. No chaining is needed for Table 2 itself. Table 1 chaining is handled by IS-03.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
python3 step1_ingest_buckman_data.py --year 2024 && \
  python3 -c "
import pandas as pd
df = pd.read_csv('output/ingested_data/2024_Table_2_output.csv')
wells = df[df['Well'].apply(lambda x: str(x).isdigit())]
total_row = df[df['Well'] == 'Total']
print(f'Wells: {len(wells)}, Total AFY: {float(total_row.iloc[0][\"Total\"]):.2f}')
assert len(wells) == 13, f'Expected 13 wells, got {len(wells)}'
print('PASS')
"
```

Expected result: `Wells: 13, Total AFY: 1372.95` followed by `PASS`

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Well numbering, CSV column format |
| DS-02 | MG-to-AF conversion factor, tolerance thresholds |
| IS-01 | Constants module (MG_TO_AF_FACTOR, CSV_WELL_COLUMNS, WELL_OSE_MAP, tolerances) |
| IS-03 | Table 1 chaining consumes Table 2 annual totals |
| IS-04 | WEL file generation reads Table 2 CSV output |
