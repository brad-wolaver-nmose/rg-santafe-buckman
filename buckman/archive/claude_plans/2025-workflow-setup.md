# Plan: Run 2024 Workflow + Setup 2025 Year-Agnostic Structure

> **STATUS: CORRECTED February 2026**
> - Directory renamed from `2024/` to `buckman/`
> - Scripts renamed with `step1_`, `step2_`, `step3_` prefixes
> - All CLI scripts now use consistent `--year` flag
> - Scripts now year-agnostic

## Objective
1. Run workflow from `santafe/buckman/` directory (renamed from `2024/`)
2. Scripts are now year-agnostic (work for any year)
3. WEL file chain handled by existing `update_modflow.py`
4. Handle missing validation data for 2025+

---

## Part 1: Manual 2024 Workflow Run

### Step 1: Ingest Pumping Data (Tables 1 & 2)
```bash
cd /home/bradwolaver/projects/rg/santafe/buckman
python3 step1_ingest_buckman_data.py --year 2024
```
**Input:** `input/csv/Buckman_Well_Prod_2024.csv` (single file with 366 daily rows)

**Outputs:**
- `output/ingested_data/2024_Table_1_updated.xlsx`
- `output/ingested_data/2024_Table_2_output.xlsx`
- `output/ingested_data/2024_MM_MON.csv` (12 monthly breakdown files)

### Step 2: Generate MODFLOW Files
```bash
python3 step2_update_modflow.py --year 2024
```
**Outputs:**
- `output/modflow/2024/thruCY2165_2024.wel`
- `output/modflow/2024/CY2024.nam`

### Step 3: Verify Tables 1 & 2 Against Validation
Compare against:
- `validation/Table_1_data_afy_2024.xlsx`
- `validation/Table_2_2024.xlsx`

### Step 4: Run MODFLOW (if needed)
Post-processor output already exists at `output/modflow/2024/depletions/CY2024`

### Step 5: Generate Tables 3, 4, 5
```bash
python3 step3_generate_depletion_tables.py --year 2024
```
**Outputs:**
- `output/depletion/TABLE_3_Rio_Pojoaque_Tesuque_2024.xlsx`
- `output/depletion/TABLE_4_Rio_Grande_Otowi_2024.xlsx`
- `output/depletion/TABLE_5_La_Cienega_Springs_2024.xlsx`

### Step 6: Validate Tables 3, 4, 5
Compare against validation files - script does this automatically.

---

## Part 2: Script Modifications for Year-Agnostic Operation

> **STATUS: COMPLETED**
> All scripts are now year-agnostic as of February 2026.

### Changes Made to `generate_depletion_tables.py`

Added year-parameterized functions:
```python
def get_modflow_output_dir(year: int) -> str:
    return f"./output/modflow/{year}/modflow/"

def get_depletions_dir(year: int) -> str:
    return f"./output/modflow/{year}/depletions/"

def get_flux_files(year: int) -> tuple[str, str]:
    return f"CY{year}_riv.flx", f"CY{year}_ghb.flx"

def get_output_file_prefix(year: int) -> str:
    return f"CY{year}"
```

Renamed function: `extract_stream_depletions_2024()` → `extract_stream_depletions(parsed_data, year)`

### Changes Made to `stream_depletions.py`

Added leap year handling:
```python
import calendar

def get_days_in_year(year: int) -> list[int]:
    """Return days per month for given year, handling leap years."""
    return [
        31,
        29 if calendar.isleap(year) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    ]
```

### Scripts Status

| Script | Year-Agnostic? | CLI Syntax |
|--------|---------------|------------|
| `step1_ingest_buckman_data.py` | YES | `python3 step1_ingest_buckman_data.py --year YYYY` |
| `step2_update_modflow.py` | YES | `python3 step2_update_modflow.py --year YYYY` |
| `step3_generate_depletion_tables.py` | YES | `python3 step3_generate_depletion_tables.py --year YYYY` |
| `stream_depletions.py` | YES | Library module (imported by step3) |

---

## Part 3: WEL File Chain (2024 → 2025)

> **STATUS: ALREADY IMPLEMENTED**
> `update_modflow.py` handles WEL file chaining automatically.

### How It Works

`update_modflow.py` uses `get_year_config(target_year)` to determine input paths:
- For 2024 (baseline): reads from `input/modflow/2023/thruCY2165.wel`
- For 2025+: reads from `output/modflow/{year-1}/thruCY2165_{year-1}.wel`

### Example: Processing 2025
```bash
python3 step2_update_modflow.py --year 2025
```

**Inputs (automatic):**
- `output/modflow/2024/thruCY2165_2024.wel` (from 2024 run)
- `output/ingested_data/2025_Table_2_output.csv` (from ingest step)

**Outputs:**
- `output/modflow/2025/thruCY2165_2025.wel`
- `output/modflow/2025/CY2025.nam`

### WEL File Locations (All in buckman/)
```
2024 output: output/modflow/2024/thruCY2165_2024.wel
2025 output: output/modflow/2025/thruCY2165_2025.wel
2026 output: output/modflow/2026/thruCY2165_2026.wel
```

**No separate directory structure needed.** All years process from the same `buckman/` directory.

---

## Part 4: 2025 Directory Setup

> **DECISION: Stay in `buckman/` directory**
> No separate year directories needed. Scripts are year-parameterized.

### Working Directory
```
/home/bradwolaver/projects/rg/santafe/buckman/
```

### For 2025, Only Need to Add:
1. Input data: `input/csv/Buckman_Well_Prod_2025.csv`

That's it. Output directories are created automatically by the scripts.

### Output Structure After Running 2025
```
buckman/
├── input/csv/
│   ├── Buckman_Well_Prod_2024.csv
│   └── Buckman_Well_Prod_2025.csv    # NEW
│
├── output/
│   ├── ingested_data/
│   │   ├── 2024_Table_1_updated.xlsx
│   │   ├── 2025_Table_1_updated.xlsx # NEW
│   │   └── ...
│   │
│   ├── depletion/
│   │   ├── TABLE_3_..._2024.xlsx
│   │   ├── TABLE_3_..._2025.xlsx     # NEW
│   │   └── ...
│   │
│   └── modflow/
│       ├── 2024/                     # Existing
│       └── 2025/                     # Created automatically
│           ├── thruCY2165_2025.wel
│           ├── CY2025.nam
│           └── depletions/
│
└── validation/
    └── (2024 validation files only - no 2025 validation expected)
```

---

## Part 5: Handle No Validation Data for 2025

### Current Validation Flow
`generate_depletion_tables.py` calls:
```python
validation_results = sd.validate_all_tables(
    table3_validation,
    table4_validation,
    table5_cumulative_af,
    table3_data,
    table4_data,
    table5_data
)
```

### Modification: Optional Validation
```python
def main(year: int) -> int:
    ...
    # Check if validation files exist
    table3_validation = Path(VALIDATION_DIR) / "TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx"

    if table3_validation.exists():
        # Validate against files
        validation_results = sd.validate_all_tables(...)
    else:
        # Skip validation, run sanity checks instead
        print(f"\nNo validation files for {year} - running sanity checks only")
        sanity_results = run_sanity_checks(year, table3_data, table4_data, table5_data)
```

### Sanity Checks for Unvalidated Years
```python
def run_sanity_checks(year: int, table3, table4, table5) -> dict:
    """
    Sanity checks when no validation data available.
    """
    checks = {
        "pumping_reasonable": 500 <= total_pumping <= 6000,
        "pojoaque_reasonable": 40 <= table3["pojoaque"]["total_impact_af"] <= 80,
        "tesuque_reasonable": 25 <= table3["tesuque"]["total_impact_af"] <= 45,
        "la_cienega_increasing": table5["cumulative_af"] > table5["previous_cumulative_af"],
        "no_negative_values": all_values_positive(...),
    }
    return checks
```

---

## Part 6: Table Updates for New Year

### Table 1: Pumping Data Updates

**Current Structure (2024):**
```
Row 1-37:  Years 1988-2024 (individual year data)
Row 38:    "Average, 1988–2024"
Row 39:    "Average, 2022–2024" (3-year rolling average)
Row 40-44: Footer rows
```

**For 2025, need to:**
1. **Insert new row** for 2025 pumping data (after row 37, before averages)
2. **Update long-term average**: "Average, 1988–2025" (was 1988–2024)
3. **Update 3-year rolling average**: "Average, 2023–2025" (was 2022–2024)
4. Recalculate both average values for all 13 wells

**Implementation in `ingest_buckman_data.py`:**
```python
def update_table1_for_year(year: int, new_data: dict, base_table1_path: Path) -> pd.DataFrame:
    """
    Insert new year into Table 1 and recalculate averages.

    Steps:
    1. Read existing Table 1
    2. Insert new year row
    3. Update "Average, 1988–{year}" label and values
    4. Update "Average, {year-2}–{year}" label and values
    5. Return updated DataFrame
    """
```

### Table 3: Depletion Data Updates

**Current Structure:**
```
Rows 2-44: Years 1988-2030
  - 1988-2024: Have actual calculated values
  - 2025-2030: Have PROJECTED values (from previous MODFLOW run)
```

**Key Insight:** Table 3 already has rows for 2025-2030 with projected values from the last MODFLOW run. When we run MODFLOW with 2025 pumping data:

1. **Years 1988-2024**: Values should remain the same (historical)
2. **Year 2025**: Replace projected values with actual calculated values
3. **Years 2026-2030**: Will have new projected values from the updated MODFLOW run

**For 2025, need to:**
1. Run MODFLOW with 2025 WEL file (includes 1988-2025 pumping)
2. Parse new post-processor output
3. Replace 2025 row with actual calculated values
4. Update 2026-2030 rows with new projections

**Implementation in `stream_depletions.py`:**
- Already handles this via `generate_table3_data(parsed_data, year=2025)`
- The parsed_data from new MODFLOW run will have updated values for all years
- Table 3 XLSX writer just needs to write all years 1988-2030

### Summary: Year-to-Year Updates

| Table | What Changes | How |
|-------|--------------|-----|
| Table 1 | Insert new year, update two averages | Modify `ingest_buckman_data.py` |
| Table 2 | Completely new (current year only) | Already year-parameterized |
| Table 3 | Update year N and projections N+1 to 2030 | Automatic from MODFLOW |
| Table 4 | Update year N and projections | Automatic from MODFLOW |
| Table 5 | Update cumulative through year N | Automatic from MODFLOW |

---

## Part 7: Execution Plan

> **STATUS: UPDATED**
> Scripts are now year-agnostic. Simpler workflow.

### Run 2024 Workflow (Verification)
```bash
cd /home/bradwolaver/projects/rg/santafe/buckman

# Step 1: Ingest pumping data
python3 step1_ingest_buckman_data.py --year 2024

# Step 2: Generate MODFLOW files
python3 step2_update_modflow.py --year 2024

# Step 3: Generate depletion tables
python3 step3_generate_depletion_tables.py --year 2024
```

### Run 2025 Workflow (When Data Arrives)
```bash
cd /home/bradwolaver/projects/rg/santafe/buckman

# Prerequisites: Buckman_Well_Prod_2025.csv in input/csv/

# Step 1: Ingest 2025 pumping data
python3 step1_ingest_buckman_data.py --year 2025

# Step 2: Generate 2025 MODFLOW files (chains from 2024 automatically)
python3 step2_update_modflow.py --year 2025

# Step 3: Run MODFLOW96 (via Wine)
# ... (produces CY2025_riv.flx, CY2025_ghb.flx)

# Step 4: Generate 2025 depletion tables
python3 step3_generate_depletion_tables.py --year 2025
```

### No Directory Setup Needed

The scripts automatically:
- Create `output/modflow/2025/` directory
- Chain WEL files from previous year
- Generate year-specific output files

---

## Critical Path Dependencies

```
2024 WEL file (has 1988-2024 data)
         │
         ▼
Add 2025 pumping data → 2025 WEL file (has 1988-2025 data)
         │
         ▼
Run MODFLOW with 2025 WEL → flux files
         │
         ▼
Run post-processor → CY2025 output
         │
         ▼
Run step3_generate_depletion_tables.py --year 2025 → Tables 3, 4, 5
```

---

## Files Modified (COMPLETED)

| File | Changes Made |
|------|--------------|
| `step3_generate_depletion_tables.py` | Added `get_modflow_output_dir()`, `get_depletions_dir()`, `get_flux_files()`, `get_output_file_prefix()`; renamed `extract_stream_depletions_2024()` to generic version |
| `stream_depletions.py` | Added `get_days_in_year(year)` for leap year handling |
| `step2_update_modflow.py` | Already year-agnostic (no changes needed) |
| `step1_ingest_buckman_data.py` | Changed `year` from positional to `--year` flag |

### Key Functions Now Available

**`step3_generate_depletion_tables.py`:**
```python
get_modflow_output_dir(year)   # Returns "./output/modflow/{year}/modflow/"
get_depletions_dir(year)       # Returns "./output/modflow/{year}/depletions/"
get_flux_files(year)           # Returns ("CY{year}_riv.flx", "CY{year}_ghb.flx")
get_output_file_prefix(year)   # Returns "CY{year}"
extract_stream_depletions(parsed_data, year)  # Generic version
```

**`stream_depletions.py`:**
```python
get_days_in_year(year)         # Handles leap years (2024=29 Feb, 2025=28 Feb)
```

**`step2_update_modflow.py`:**
```python
get_year_config(target_year)   # Chains WEL files automatically
```

---

## Next Steps When 2025 Data Arrives

1. Place `Buckman_Well_Prod_2025.csv` in `input/csv/`
2. Run the 3-step workflow shown above
3. No directory setup or script modifications needed
