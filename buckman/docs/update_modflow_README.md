# MODFLOW Buckman Depletion Model Update

## Quick Start

```bash
python3 update_modflow.py --year <year>
```

**Example:**
```bash
python3 update_modflow.py --year 2024
python3 update_modflow.py --year 2025
```

The `--year` argument is **required** - the script will not run without it.

---

## What It Does

Updates the MODFLOW Buckman Depletion Model by:

1. Reading monthly pumping data from Table 2 CSV (acre-feet)
2. Converting acre-feet to ft³/s (MODFLOW's rate units)
3. Updating the `.wel` file with actual pumping rates for each well
4. Generating the `.nam` control file for the target year
5. Validating output against known-good files (if they exist)

---

## Required Input Files

| File | Location | Description |
|------|----------|-------------|
| Table 2 CSV | `output/ingested_data/{year}_Table_2_output.csv` | Monthly pumping by well (from `ingest_buckman_data.py`) |
| Source .wel | Determined by year (see below) | Previous year's well file |

**Source file logic:**
- **2024** (baseline): Uses `input/modflow/2023/thruCY2165.wel`
- **2025+**: Uses `output/modflow/{year-1}/thruCY2165_{year-1}.wel`

---

## Output Files

All outputs go to `output/modflow/{year}/`:

| Output | Filename | Description |
|--------|----------|-------------|
| Well file | `thruCY2165_{year}.wel` | Updated pumping rates for all years through target |
| Name file | `CY{year}.nam` | MODFLOW control file pointing to updated files |

---

## Year-Agnostic Design

The script was refactored from a 2024-only version to work with **any year**:

### Incremental Processing

Each year builds on the previous:

```
2023 baseline  →  2024 processing  →  2025 processing  →  ...
     ↓                  ↓                   ↓
input/modflow/    output/modflow/    output/modflow/
  2023/             2024/               2025/
```

### Dynamic Year Detection

Instead of hardcoded line numbers, the script searches the `.wel` file for year markers:
- Finds `JAN {year}` to locate year start
- Finds `DEC {year}` to locate year end
- Validates expected 324 lines per year (12 months × 27 lines)

### Leap Year Handling

February days calculated automatically:
- Leap years (2024, 2028): 29 days
- Non-leap years (2025, 2026): 28 days

---

## Workflow for Processing a New Year

```bash
# 1. Run ingestion first (creates Table 2 CSV)
python3 ingest_buckman_data.py 2025

# 2. Run MODFLOW update
python3 update_modflow.py --year 2025

# 3. Review outputs
ls output/modflow/2025/
```

**Full pipeline from scratch:**
```bash
# Process 2024 first (baseline year)
python3 ingest_buckman_data.py 2024
python3 update_modflow.py --year 2024

# Then process 2025 (uses 2024's output)
python3 ingest_buckman_data.py 2025
python3 update_modflow.py --year 2025
```

---

## Validation

The script validates output against known-good files if they exist:

| Validation File | Location |
|-----------------|----------|
| Expected .wel | `validation/modflow/{year}/thruCY2165_{year}.wel` |
| Expected .nam | `validation/modflow/{year}/CY{year}.nam` |

**Behavior:**
- **Files exist**: Validates and reports PASS/FAIL
- **Files missing**: Warns and skips validation (graceful degradation)

---

## Unit Conversion

Pumping rates convert from acre-feet (Table 2) to ft³/s (MODFLOW):

```
rate (ft³/s) = -(AF/2) × 43,560 / (days_in_month × 86,400)
```

Where:
- `AF` = monthly pumping in acre-feet
- `÷ 2` = split between Layer 1 and Layer 2
- `43,560` = ft³ per acre-foot
- `86,400` = seconds per day
- Negative sign = extraction (MODFLOW convention)

---

## What Changed (Feb 2025)

The script was refactored from `update_modflow_2024.py` to `update_modflow.py`:

| Before | After |
|--------|-------|
| Hardcoded for 2024 only | Works with any year |
| `--year` optional (default 2024) | `--year` required |
| Hardcoded line numbers (8798-9121) | Dynamic search via `find_year_boundaries()` |
| `DAYS_IN_MONTH_2024` constant | `get_days_in_month(year)` function |
| Fails if validation missing | Warns and continues |
