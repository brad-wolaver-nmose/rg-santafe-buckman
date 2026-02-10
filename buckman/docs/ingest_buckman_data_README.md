# Buckman Well Field Data Ingestion

## Quick Start

```bash
python3 ingest_buckman_data.py <year>
```

**Example:**
```bash
python3 ingest_buckman_data.py 2024
python3 ingest_buckman_data.py 2025
```

The year argument is **required** - the script will not run without it.

---

## Required Input Files

For each year you want to process, you need two files:

| File | Location | Description |
|------|----------|-------------|
| Source CSV | `input/csv/Buckman_Well_Prod_{year}.csv` | Daily MGD pumping data from SCADA |
| Validation Excel | `validation/Table_1_data_afy_{year}.xlsx` | Historical Table 1 data through previous year |

**Example for 2025:**
- `input/csv/Buckman_Well_Prod_2025.csv`
- `validation/Table_1_data_afy_2025.xlsx`

---

## Creating the Validation File for a New Year

When processing a new year (e.g., 2025), create the validation file by:

1. **Copy previous year's output:**
   ```bash
   cp output/ingested_data/2024_Table_1_updated.xlsx validation/Table_1_data_afy_2025.xlsx
   ```

2. Or copy the previous validation file:
   ```bash
   cp validation/Table_1_data_afy_2024.xlsx validation/Table_1_data_afy_2025.xlsx
   ```

The validation file contains historical pumping data (1988-present) that the new year's data gets appended to.

---

## Output Files

All outputs go to `output/ingested_data/`:

| Output | Filename | Description |
|--------|----------|-------------|
| Monthly CSVs | `{year}_01_JAN.csv` ... `{year}_12_DEC.csv` | Monthly well data with AF conversions |
| Table 2 CSV | `{year}_Table_2_output.csv` | Monthly AFY grid (wells × months) |
| Table 2 Excel | `{year}_Table_2_output.xlsx` | Formatted Table 2 for OSE reporting |
| Table 1 CSV | `{year}_Table_1_updated.csv` | Historical data with new year added |
| Table 1 Excel | `{year}_Table_1_updated.xlsx` | Formatted Table 1 for OSE reporting |
| QA Summary | `input_summary.csv` | Data quality flags and verification |

---

## Workflow for Processing a New Year

```bash
# 1. Place source CSV in input folder
cp /path/to/Buckman_Well_Prod_2025.csv input/csv/

# 2. Create validation file from previous year's output
cp output/ingested_data/2024_Table_1_updated.xlsx validation/Table_1_data_afy_2025.xlsx

# 3. Run the script
python3 ingest_buckman_data.py 2025

# 4. Review outputs in output/ingested_data/
ls output/ingested_data/2025_*
```

---

## What Changed (Feb 2025)

The script was updated to support **any year** instead of being hardcoded to 2024:

- Year is now a **required** command-line argument (no default)
- Validation file path uses the year: `Table_1_data_afy_{year}.xlsx`
- Table 1 output files now include year prefix: `{year}_Table_1_updated.csv/xlsx`
- Clear error messages guide you when files are missing
