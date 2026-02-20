# MODFLOW Stream Cell Mapping Reference

**Purpose:** Document how the Buckman Wellfield depletion pipeline identifies which MODFLOW model cells correspond to each stream reach for Tables 3, 4, and 5.

**Critical for:** Understanding La Cienega Springs cell assignment (Table 5), troubleshooting depletion calculation errors, updating model geometry.

**Last Updated:** 2026-02-19

---

## Executive Summary

Stream depletion cells are identified through a **three-layer hardcoding system**:

1. **MODFLOW GHB/RIV Package Files** → Define physical cell locations (layer, row, column)
2. **FORTRAN Post-Processor (sfmodflx_2245.for)** → Hardcoded cell ranges extract and aggregate fluxes
3. **Python Parser (stream_depletions.py)** → Matches stream labels in post-processor output

**La Cienega Springs Example:**
- **MODFLOW:** 6 GHB cells at rows 28-35, columns 10-20
- **FORTRAN:** Hardcoded rectangle `IS=28, IX=35, JS=10, JX=20` → label "LC SPRINGS"
- **Python:** Looks for exact string `"LC SPRINGS"` in `CY{year}` file

**Critical Assumption:** FORTRAN cell ranges MUST match actual cell locations in GHB/RIV files, or depletion values will be wrong.

---

## 1. Overview: Three-Layer System

### Data Flow Chain

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: MODFLOW Input Files (Physical Cell Definitions)            │
├─────────────────────────────────────────────────────────────────────┤
│ Files:                                                               │
│  - input/modflow/2023/thruCY2165.riv (River Package - tributaries)  │
│  - input/modflow/2023/thruCY2165.ghb (GHB Package - La Cienega)     │
│                                                                      │
│ Format: LAYER ROW COL HEAD CONDUCTANCE                              │
│ Example GHB entry: 1 30 14 5449.0 100.0                            │
│                    ↑  ↑  ↑                                          │
│                    │  │  └─ Column 14                               │
│                    │  └──── Row 30                                  │
│                    └─────── Layer 1                                 │
│                                                                      │
│ Output: No labels or stream identifiers                             │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ MODFLOW96 Execution (wine modflow96.exe)                            │
├─────────────────────────────────────────────────────────────────────┤
│ Reads RIV and GHB package cells                                     │
│ Computes flux (cfs) for each cell per timestep (monthly)           │
│ Outputs binary flux files:                                          │
│  - output/modflow/{year}/CY{year}_riv.flx (~31 MB)                 │
│  - output/modflow/{year}/CY{year}_ghb.flx (~31 MB)                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: FORTRAN Post-Processor (sfmodflx_2245.exe)                 │
├─────────────────────────────────────────────────────────────────────┤
│ Source: output/modflow/{year}/depletions/sfmodflx_2245.for          │
│                                                                      │
│ Cell Extraction (SUBROUTINE FILL, lines 213-249):                   │
│  IF (JJ2 .EQ. 1) THEN       ! RIV Package (tributaries)            │
│      IS=9, IX=17, JS=14, JX=25                                      │
│  ELSE IF (JJ2 .EQ. 2) THEN  ! GHB Package (La Cienega)            │
│      IS=28, IX=35, JS=10, JX=20   ← HARDCODED RECTANGLE            │
│  END IF                                                              │
│                                                                      │
│ Stream Aggregation Logic (lines 143-157):                           │
│  - Cells assigned to streams based on row/column coordinates        │
│  - R POJOAQUE: row=9 AND col>13, OR row<13 AND col>21             │
│  - R TESUQUE: col>18                                                │
│  - RIO GRANDE: All other river cells                                │
│  - LC SPRINGS: Sum all GHB cells (no spatial logic, all GHB=La Cien)│
│                                                                      │
│ Output: CY{year} (formatted text file)                              │
│  Per-cell rows: "LAY ROW COL  12_monthly_cfs_values"               │
│  Stream rows:   "0  STREAM_NAME  12_monthly_cfs_values"            │
│    Example:     "0  LC SPRINGS    0.083581 0.083581 ..."           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: Python Parser (stream_depletions.py)                       │
├─────────────────────────────────────────────────────────────────────┤
│ parse_post_processor_output() (lines 456-617):                      │
│  - Reads CY{year} file line by line                                 │
│  - Regex match: "^0\s+(LC SPRINGS|R POJOAQUE|...)\s+(...)"         │
│  - Stores as: parsed_data[year]["LC SPRINGS"]["jan"] = 0.083581   │
│                                                                      │
│ generate_table5_data() (lines 1032-1107):                           │
│  - Verifies "LC SPRINGS" in parsed_data[year]                      │
│  - Extracts 12 monthly cfs values                                   │
│  - Converts cfs → acre-feet using calendar.isleap(year)            │
│  - Returns Table 5 data structure                                   │
│                                                                      │
│ Output: TABLE_5_La_Cienega_Springs_{year}.xlsx                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Insight

**There is NO automatic connection between layers.** Each layer independently defines cell locations:

- **MODFLOW files** list cells by (layer, row, col) with no stream labels
- **FORTRAN code** hardcodes cell rectangles and assigns labels
- **Python code** matches hardcoded labels from FORTRAN

**If FORTRAN cell ranges don't match actual GHB/RIV cell locations, depletion values will be wrong.**

---

## 2. MODFLOW GHB Package Specification (La Cienega Springs)

### File Location
```
input/modflow/2023/thruCY2165.ghb
```

### File Format
```
   6    50  # Header: 6 GHB cells, 50 stress periods (not used)
#
# LAY ROW COL     HEAD  CONDUCTANCE
#
    1  30  14  5449.0        100.0
    1  31  12  5447.0        100.0
    1  31  14  5447.0        100.0
    1  31  15  5447.0        100.0
    1  32  13  5445.0        100.0
    1  32  12  5445.0        100.0
```

### La Cienega Springs Cell Inventory

| Cell # | Layer | Row | Column | Head (ft) | Conductance (ft²/day) | Purpose |
|--------|-------|-----|--------|-----------|----------------------|---------|
| 1 | 1 | 30 | 14 | 5449.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |
| 2 | 1 | 31 | 12 | 5447.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |
| 3 | 1 | 31 | 14 | 5447.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |
| 4 | 1 | 31 | 15 | 5447.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |
| 5 | 1 | 32 | 13 | 5445.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |
| 6 | 1 | 32 | 12 | 5445.0 | 100.0 | GHB node representing hydraulic connection to La Cienega Springs |

**Spatial extent:**
- Rows: 30-32 (3 rows)
- Columns: 12-15 (4 columns)
- All in Layer 1 (top layer of aquifer model)

**Physical Interpretation:**
- These 6 cells represent the spatial footprint of La Cienega Springs in the Santa Fe aquifer model
- GHB (General Head Boundary) condition allows groundwater to discharge to springs
- Flux (depletion) is computed as: `flux = conductance × (aquifer_head - specified_head)`
- Positive flux = reduced spring discharge (depletion)

---

## 3. FORTRAN Extraction Logic (sfmodflx_2245.for)

### Source Code Location
```
output/modflow/{year}/depletions/sfmodflx_2245.for
```

### Critical Hardcoded Cell Ranges (SUBROUTINE FILL)

**Lines 213-249:**
```fortran
C  EXTRACT CELLS FROM FLUX FILE BASED ON PACKAGE TYPE
      SUBROUTINE FILL(ITMUNI,IOUT,IS,IX,JS,JX,JJ2)
C
C  JJ2 = 1 FOR RIV (RIVER) PACKAGE
C  JJ2 = 2 FOR GHB (GENERAL HEAD BOUNDARY) PACKAGE
C
      ...
C
      IF (JJ2 .EQ. 1) THEN
C       RIV PACKAGE CELLS (Rio Pojoaque, Rio Tesuque, Rio Grande)
        IS=9    ! Start row
        IX=17   ! End row
        JS=14   ! Start column
        JX=25   ! End column
      ELSE IF (JJ2 .EQ. 2) THEN
C       GHB PACKAGE CELLS (La Cienega Springs)
        IS=28   ! Start row ← HARDCODED FOR LA CIENEGA
        IX=35   ! End row   ← HARDCODED FOR LA CIENEGA
        JS=10   ! Start column
        JX=20   ! End column
      END IF
```

**⚠️ CRITICAL ASSUMPTION:**

The rectangle `rows 28-35, columns 10-20` is **HARDCODED** and assumed to contain all La Cienega GHB cells.

**Current Reality:**
- **Actual GHB cells:** Rows 30-32, Columns 12-15 (6 cells)
- **FORTRAN rectangle:** Rows 28-35, Columns 10-20 (8 rows × 11 cols = 88 potential cells)
- **Status:** ✅ SAFE - All 6 GHB cells fall within FORTRAN rectangle
- **Risk:** If model adds GHB cells outside this rectangle, they will be IGNORED

### Stream Label Assignment (SUBROUTINE TOTAL)

**Lines 204-205:**
```fortran
C  WRITE LA CIENEGA SPRINGS SUMMARY ROW
      WRITE(IOUT,215) (GHBSUM(K),K=I1,I2)
  215 FORMAT(1H0,'  LC SPRINGS',12F12.6)
```

**Key Points:**
- Label is `"  LC SPRINGS"` (literal: zero, two spaces, "LC SPRINGS")
- No spatial logic for La Cienega — ALL GHB cells are summed as one stream
- FORTRAN assumes GHB package contains ONLY La Cienega cells

---

## 4. Python Parsing (stream_depletions.py)

### Stream Name Registry

**Lines 625-631:**
```python
# CRITICAL: These strings must match EXACTLY what FORTRAN writes
STREAM_NAMES = [
    "R POJOAQUE",   # Rio Pojoaque-Nambe
    "R TESUQUE",    # Rio Tesuque
    "RIO GRANDE",   # Rio Grande main stem
    "RIV  TOTAL",   # Total river depletions (sum of above 3)
    "LC SPRINGS",   # La Cienega Springs (GHB package)
]
```

**⚠️ String Matching Dependency:**
- Python looks for exact string `"LC SPRINGS"` (no leading spaces in list)
- FORTRAN writes `"  LC SPRINGS"` with two leading spaces
- Regex handles whitespace: `r"^0\s+(LC SPRINGS)\s+"`

### La Cienega Data Extraction

**generate_table5_data() function (lines 1032-1107):**

```python
def generate_table5_data(parsed_data: dict, year: int) -> dict:
    """
    Generate Table 5 data structure from parsed post-processor output.

    Critical inputs:
    - parsed_data[year]["LC SPRINGS"]: Dict with 12 monthly cfs values
    - LA_CIENEGA_CUMULATIVE[year]: Pre-computed cumulative AF for validation

    Returns:
    - Table 5 data dict with cumulative AF, annual increment AF, ...
    """
    # Verify year exists in parsed data
    if year not in parsed_data:
        raise ValueError(f"Year {year} not found in parsed post-processor data")

    year_data = parsed_data[year]

    # Verify "LC SPRINGS" stream exists
    if "LC SPRINGS" not in year_data:
        raise ValueError(
            f"'LC SPRINGS' not found in {year} parsed data. "
            f"Available streams: {list(year_data.keys())}"
        )

    months = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]

    # Extract monthly cfs values
    lc_springs_cfs = [year_data["LC SPRINGS"][m] for m in months]

    # Convert to annual acre-feet using actual calendar days
    is_leap = calendar.isleap(year)
    cumulative_af = cfs_monthly_to_af_annual(
        lc_springs_cfs,
        year=year,
        use_leap_year=is_leap
    )

    # Get previous year's cumulative to compute annual increment
    previous_year = year - 1
    if previous_year in LA_CIENEGA_CUMULATIVE:
        previous_cumulative = LA_CIENEGA_CUMULATIVE[previous_year]
        annual_increment_af = cumulative_af - previous_cumulative
    else:
        annual_increment_af = cumulative_af  # First year, no prior data

    return {
        "cumulative_af": cumulative_af,
        "annual_increment_af": annual_increment_af,
        # ... more fields
    }
```

### Hardcoded Cumulative Values (Historical Baseline)

**Lines 78-100:**
```python
# LA CIENEGA SPRINGS CUMULATIVE DEPLETION (ACRE-FEET)
# These values are manually entered from official Table 5 outputs
# Cumulative depletion represents total impact from 1988-{year} pumping
LA_CIENEGA_CUMULATIVE = {
    2004: 0.45,   # First year La Cienega included (Barroll & Keyes 2005)
    2005: 0.66,
    # ... [years 2006-2023 omitted for brevity]
    2024: 3.74,   # Most recent validated year
    2025: 3.95,   # Projected (not yet submitted)
}
```

**⚠️ Manual Entry Risk:**
- These values are TYPED BY HAND from Excel files
- No automated check that they match source documents
- Typos would propagate to validation logic

---

## 5. Assumptions and Failure Modes

### Critical Assumptions

| # | Assumption | Consequence if Violated | Likelihood |
|---|------------|------------------------|------------|
| 1 | **All GHB cells represent La Cienega Springs** | Adding other GHB features (e.g., Galisteo Dam seepage) would corrupt La Cienega totals | Low (model geometry stable since 2003) |
| 2 | **GHB cells fall within rows 28-35, cols 10-20** | Cells outside this rectangle are ignored by FORTRAN → silent underestimation of depletion | Low (current cells in rows 30-32, cols 12-15) |
| 3 | **FORTRAN label "LC SPRINGS" never changes** | Typo or reformatting in FORTRAN would break Python parsing → runtime error | Very Low (frozen code since 2003) |
| 4 | **LA_CIENEGA_CUMULATIVE values are correct** | Typo in manual entry → false validation failures or acceptance of wrong values | Medium (manual process, no automated check) |
| 5 | **Model grid geometry unchanged** | Resizing/re-projecting model would invalidate hardcoded row/column ranges | Low (major undertaking, would trigger full re-validation) |

### Failure Modes

#### Scenario 1: New GHB Cell Outside FORTRAN Rectangle

**Event:** Model adds GHB cell at (1, 27, 13) to represent expanded La Cienega area

**Failure Chain:**
1. MODFLOW computes flux for new cell normally
2. FORTRAN extraction skips row 27 (outside IS=28)
3. New cell flux is **NOT included** in "LC SPRINGS" total
4. Table 5 **underestimates** depletion
5. No error message — silent failure
6. Compliance report submitted with incorrect values

**Detection:** Would require manual cross-check or automated validation (see Phase 3)

#### Scenario 2: FORTRAN Label Typo

**Event:** FORTRAN source typo changes `"  LC SPRINGS"` → `"  LS SPRINGS"`

**Failure Chain:**
1. FORTRAN writes `"  LS SPRINGS"` to CY{year} file
2. Python regex looks for `"LC SPRINGS"` — no match found
3. `ValueError` raised: `"'LC SPRINGS' not found in 2024 parsed data"`
4. Workflow crashes immediately

**Detection:** ✅ Automatic — Python raises clear error message

**Resolution:** Fix FORTRAN typo, recompile sfmodflx_2245.exe, re-run post-processor

#### Scenario 3: LA_CIENEGA_CUMULATIVE Manual Entry Error

**Event:** Typing error: 2023 value should be 3.54 but entered as 3.45

**Failure Chain:**
1. 2024 annual increment computed as: `3.74 - 3.45 = 0.29 AF`
2. Actual increment should be: `3.74 - 3.54 = 0.20 AF`
3. Table 5 shows **incorrect annual increment**
4. Validation passes (wrong baseline used for comparison)
5. Compliance report submitted with incorrect trend data

**Detection:** Manual review of year-over-year trends, or automated source document checks

---

## 6. Model Grid Visualization

### La Cienega Springs Cell Locations

```
    Model Grid (Layer 1, Rows 25-40, Columns 8-22)

    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │              FORTRAN EXTRACTION RECTANGLE          │
    │              Rows 28-35, Columns 10-20             │
    │  ┌─────────────────────────────────────────────┐   │
    │  │   Col: 10  11  12  13  14  15  16  17  18   │   │
    │  │ Row                                          │   │
    │  │  28 │   .   .   .   .   .   .   .   .   .  │   │
    │  │  29 │   .   .   .   .   .   .   .   .   .  │   │
    │  │  30 │   .   .   .   .  [G]  .   .   .   .  │   │ ← GHB cell (1,30,14)
    │  │  31 │   .   .  [G]  .  [G] [G]  .   .   .  │   │ ← GHB cells (1,31,12), (1,31,14), (1,31,15)
    │  │  32 │   .   .  [G] [G]  .   .   .   .   .  │   │ ← GHB cells (1,32,12), (1,32,13)
    │  │  33 │   .   .   .   .   .   .   .   .   .  │   │
    │  │  34 │   .   .   .   .   .   .   .   .   .  │   │
    │  │  35 │   .   .   .   .   .   .   .   .   .  │   │
    │  └─────────────────────────────────────────────┘   │
    │                                                    │
    └────────────────────────────────────────────────────┘

Legend:
  [G] = GHB cell (La Cienega Springs)
  .   = Inactive or non-La Cienega cell

  ┌───┐ = FORTRAN hardcoded extraction rectangle
          (IS=28, IX=35, JS=10, JX=20)
```

**Key Observations:**
1. All 6 GHB cells are **safely inside** the FORTRAN rectangle ✅
2. FORTRAN rectangle is **oversized** (88 cells vs 6 actual GHB cells)
3. Oversizing provides buffer against minor model geometry changes
4. If GHB cells added at row 27 or row 36, FORTRAN would miss them ❌

---

## 7. How to Update Model Geometry

### If La Cienega GHB Cells Change Location

**Example:** Add new GHB cell at (1, 29, 13) to expand La Cienega Springs representation

**Update Procedure:**

#### Step 1: Update MODFLOW GHB File
```bash
# Edit: input/modflow/2023/thruCY2165.ghb
# Change line 1 from:
   6    50
# To:
   7    50

# Add new cell entry:
    1  29  13  5448.0        100.0
```

#### Step 2: Verify Cell Falls Within FORTRAN Rectangle
- Check new cell row: 29 ✅ (within IS=28 to IX=35)
- Check new cell column: 13 ✅ (within JS=10 to JX=20)
- **If cell is OUTSIDE rectangle:** Must update FORTRAN code (see Step 3)

#### Step 3: Update FORTRAN Code (Only if Necessary)
**File:** `output/modflow/{year}/depletions/sfmodflx_2245.for`

**Lines 223-228:** Expand rectangle to include new cells
```fortran
      ELSE IF (JJ2 .EQ. 2) THEN
        IS=27   ! Changed from 28 to include row 27
        IX=35   ! No change
        JS=10   ! No change
        JX=20   ! No change
      END IF
```

**Recompile:**
```bash
# Requires FORTRAN 77 compiler
gfortran -o sfmodflx_2245.exe sfmodflx_2245.for
```

**⚠️ WARNING:** Recompiling FORTRAN post-processor requires:
1. Bit-for-bit validation against all historical years (1988-{current year})
2. Verification that new executable produces identical output for existing cells
3. Documentation of compiler version and flags used
4. Update of this document to reflect new cell ranges

#### Step 4: Update Python Validation (Recommended)
Add validation check in `stream_depletions.py`:
```python
def validate_ghb_cells_in_fortran_range():
    """Verify all GHB cells fall within FORTRAN extraction rectangle."""
    ghb_file = Path("input/modflow/2023/thruCY2165.ghb")
    ghb_cells = parse_ghb_file(ghb_file)  # Returns list of (layer, row, col)

    fortran_row_range = (28, 35)  # Update if FORTRAN changed
    fortran_col_range = (10, 20)  # Update if FORTRAN changed

    for cell in ghb_cells:
        layer, row, col = cell
        if not (fortran_row_range[0] <= row <= fortran_row_range[1]):
            raise ValueError(
                f"GHB cell row {row} outside FORTRAN range {fortran_row_range}. "
                f"Update sfmodflx_2245.for lines 223-228 or move GHB cell."
            )
        if not (fortran_col_range[0] <= col <= fortran_col_range[1]):
            raise ValueError(
                f"GHB cell col {col} outside FORTRAN range {fortran_col_range}. "
                f"Update sfmodflx_2245.for lines 223-228 or move GHB cell."
            )

    print(f"✓ All {len(ghb_cells)} GHB cells within FORTRAN rectangle")
    return True
```

Call before running sfmodflx_2245.exe in `step4_generate_depletion_tables.py`.

#### Step 5: Re-Run Workflow and Validate
```bash
# Process current year with updated geometry
python3 step1_ingest_buckman_data.py --year 2025
python3 step2_update_modflow.py --year 2025
./step3_run_modflow.sh --year 2025
python3 step4_generate_depletion_tables.py --year 2025  # Includes validation

# Verify Table 5 values are reasonable
python3 step5_verify_workflow.py --year 2025
```

#### Step 6: Update Regression Baselines
If validation fails due to intentional geometry change:
```bash
# Copy new outputs as expected values
cp output/depletion/TABLE_5_La_Cienega_Springs_2025.xlsx \
   validation/2025/expected_outputs/Table_5_expected.xlsx

# Update validation/2025/tolerances.yaml if needed
```

#### Step 7: Document Changes
Update this file (`docs/MODFLOW_CELL_MAPPING.md`) with:
- New GHB cell count and coordinates (Section 2)
- Revised FORTRAN cell ranges (Section 3)
- Updated ASCII grid diagram (Section 6)
- Date stamp and change rationale at top of file

---

## References

### Source Files
- MODFLOW GHB package: `input/modflow/2023/thruCY2165.ghb`
- FORTRAN source: `output/modflow/{year}/depletions/sfmodflx_2245.for`
- Python parser: `stream_depletions.py`
- Python driver: `step4_generate_depletion_tables.py`

### Key Publications
- Barroll, M.W., and Keyes, E., 2005, *La Cienega Springs Depletion Analysis*: Technical Memorandum to Santa Fe County
- Core, F., 2003, *Santa Fe River and Tributaries Stream Depletion Projections*: Wright Water Engineers Report

### Related Documentation
- `README.md` - Main pipeline documentation
- `docs/FILE_DEPENDENCIES.md` - File dependency chain
- `validation/2024/tolerances.yaml` - Validation thresholds

---

**Document Maintenance:**
- **Author:** Claude Code (Anthropic) + Brad Wolaver (NMOSE)
- **Created:** 2026-02-19
- **Last Updated:** 2026-02-19
- **Next Review:** When model geometry changes or La Cienega cell assignments updated
