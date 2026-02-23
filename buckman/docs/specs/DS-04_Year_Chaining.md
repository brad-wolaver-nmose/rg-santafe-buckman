# DS-04: Year-Chaining & Temporal Architecture

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Final
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Purpose & Scope

The Buckman Wellfield depletion pipeline processes years sequentially, building on prior results. Each year's MODFLOW simulation requires pumping data accumulated from all previous years (2003--present), and each year's depletion tables carry forward historical values from prior years' calculations. This specification documents the year-chaining architecture: how the pipeline connects year N-1 outputs to year N inputs, ensuring continuity of the cumulative record while allowing recalculation of current and future projections.

Year-chaining is critical for regulatory compliance because the OSE annual report contains cumulative depletion values that must be internally consistent across all reporting years. An error in the chaining logic would corrupt the historical record, requiring reprocessing of all subsequent years.

---

## 2. Scientific Basis

### 2.1 Superposition Principle and Cumulative Pumping

MODFLOW simulates groundwater flow using the principle of superposition: the aquifer response to pumping at time T equals the sum of responses to all pumping from all prior stress periods. Consequently, the well package (.wel) file must contain pumping records for every month from the model start (2003) through the current processing year. Each new year appends 12 months of pumping data to the cumulative record.

This is not a modeling convenience but a physical requirement. Stream depletions from pumping propagate through the aquifer over decades. The 2024 depletion at the Rio Pojoaque includes contributions from pumping in 2003, 2010, 2018, and every year in between. Removing any year's pumping from the simulation would produce physically incorrect results.

### 2.2 WEL File Accumulation

The MODFLOW well package (.wel) file grows by exactly 324 lines per year:

```
Lines per year = 12 months x 27 lines/month
               = 12 x (1 header + 26 well entries)
               = 12 x (1 + 13 wells x 2 layers)
               = 324 lines
```

Each well entry specifies: layer, row, column, pumping rate (ft^3/s), well name, month, year.

### 2.3 Key Equations

**Unit conversion (acre-feet to ft^3/s per layer):**

```
rate_ft3_per_s = -(AF / N_layers) x 43,560 / (days_in_month x 86,400)

Where:
  AF           = monthly pumping volume (acre-feet)
  N_layers     = 2 (pumping split equally between MODFLOW layers 1 and 2)
  43,560       = ft^3 per acre-foot
  days_in_month = calendar days (28/29 for Feb, 30/31 for others)
  86,400       = seconds per day
  Negative sign = MODFLOW convention (extraction is negative)
```

### 2.4 Worked Example

**Well B1, January 2024 (31 days, non-leap immaterial for January):**

```
Given:  AF = 16.887963 acre-feet, N_layers = 2, days = 31

Step 1: Volume per layer = 16.887963 / 2 = 8.443982 AF
Step 2: Convert to ft^3  = 8.443982 x 43,560 = 367,819.0 ft^3
Step 3: Seconds in Jan   = 31 x 86,400 = 2,678,400 s
Step 4: Rate             = 367,819.0 / 2,678,400 = 0.13730 ft^3/s
Step 5: MODFLOW sign     = -0.13730 ft^3/s

WEL file entry:
         1        13        11  -0.13730  BUCKMAN 1 JAN 2024
         2        13        11  -0.13730  BUCKMAN 1 JAN 2024
```

**Leap year effect (February 2024, 29 days vs. 28 days):**

For the same 10 AF pumped in February:

```
Leap year (29 days):   rate = -(10/2) x 43560 / (29 x 86400) = -0.08695 ft^3/s
Non-leap (28 days):    rate = -(10/2) x 43560 / (28 x 86400) = -0.09006 ft^3/s

Difference: 3.5% -- significant enough to matter for compliance precision
```

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | Years must be processed sequentially (2024, 2025, 2026...) | Each year's WEL file, Table 1, Table 3, and Table 5 depend on prior year's output | Missing intermediate year corrupts cumulative record | Pipeline checks for prior year output before proceeding |
| 2 | Pumping is split equally between Layer 1 and Layer 2 | Buckman wells are completed across both model layers; equal split is the conventional assumption for this model | Under/overestimates depletion in individual layers | Conservative for total depletion (sum across layers is correct) |
| 3 | Pumping rate is constant within each monthly stress period | MODFLOW96 uses constant-rate stress periods; sub-monthly variation is smoothed | Seasonal peak effects underestimated within high-demand months | Monthly resolution matches OSE reporting requirements |
| 4 | The 2023 baseline WEL file contains correct pumping for 2003-2023 | File was produced by the prior (pre-automation) workflow and validated independently | All subsequent years would inherit the error | SHA-256 hash verification of baseline files in manifest system |
| 5 | Historical depletion values (pre-processing_year) should be preserved exactly from the year they were calculated | Each year's MODFLOW run is the authoritative source for that year's depletions | Re-running with different model inputs could change historical values | Chaining logic locks historical rows from prior year's output |
| 6 | BASELINE_YEAR = 2024 is the first automated year | 2024 uses original 2023 baseline files; 2025+ uses chained outputs | Incorrect baseline year would use wrong input files | Constant is explicitly defined and documented |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| input/modflow/2023/thruCY2165.wel | Baseline WEL file (2003-2023 pumping) | Static file, version-controlled | Never (frozen baseline) | SHA-256 hash verification |
| output/modflow/{year-1}/thruCY2165_{year-1}.wel | Prior year's cumulative WEL file | Generated by step2 for year-1 | Annual (one per processing year) | Line count validation (must be 324 lines longer than prior) |
| validation/Table_1_data_afy_{year}.xlsx | Table 1 template (baseline year only) | Manual provision for 2024 | One-time | Cross-check with OSE records |
| output/ingested_data/{year-1}/{year-1}_Table_1_updated.xlsx | Table 1 template (subsequent years) | Generated by step1 for year-1 | Annual | Row count = prior year + 1 |
| output/depletion/TABLE_3_*_{year-1}.xlsx | Prior year's Table 3 for chaining | Generated by step4 for year-1 | Annual | Monotonicity check on cumulative values |
| output/depletion/TABLE_5_*_{year-1}.xlsx | Prior year's Table 5 for chaining | Generated by step4 for year-1 | Annual | Monotonicity check on cumulative values |

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| BASELINE_YEAR | 2024 | year | First year using automated pipeline with 2023 inputs | Project convention |
| ACRE_FT_TO_FT3 | 43,560 | ft^3/AF | 1 acre = 43,560 ft^2, 1 AF = 1 ft depth | USGS definition |
| SECONDS_PER_DAY | 86,400 | s/day | 24 x 60 x 60 | Physical constant |
| NUM_LAYERS | 2 | dimensionless | Buckman wells completed in both model layers | Model design |
| LINES_PER_MONTH | 27 | lines | 1 header + 13 wells x 2 layers | WEL file format |
| LINES_PER_YEAR | 324 | lines | 12 months x 27 lines | WEL file format |
| WELLS_PER_MONTH | 26 | entries | 13 wells x 2 layers | WEL file format |

### Dimensional Analysis

**AF to ft^3/s conversion chain:**

```
acre-feet     1 AF       43,560 ft^3      1 day          1
--------- x -------- x ------------- x ------------ = -------
 month      2 layers      1 AF         86,400 sec      ft^3/s

Cancellation:  [AF] x [ft^3/AF] / [layers] / [s/month]
            =  ft^3 / (layers x s)
            =  ft^3/s per layer
```

---

## 6. Domain-Specific Constraints

### 6.1 Chaining Architecture by Pipeline Step

#### Step 1: Table 1 Chaining (Annual Pumping History)

Table 1 is a cumulative record of annual pumping by well (1988--present). Each year adds one row.

| Scenario | Template Source | Behavior |
|----------|---------------|----------|
| Baseline year (2024) | `validation/Table_1_data_afy_2024.xlsx` | Uses hand-prepared historical file |
| Subsequent years (2025+) | `output/ingested_data/{year-1}/{year-1}_Table_1_updated.xlsx` | Uses prior year's output as template |
| Neither exists | Error | Pipeline halts with diagnostic message |

**Chaining rule:** Read all existing rows from template, append new row with current year's annual totals per well. Statistics rows (Mean, Min, Max, Rank) are recalculated for the full series.

#### Step 2: WEL File Chaining (Cumulative MODFLOW Pumping)

The WEL file is the core chained artifact. It grows by exactly 324 lines each year.

| Scenario | Input WEL Source | Behavior |
|----------|-----------------|----------|
| Baseline year (2024) | `input/modflow/2023/thruCY2165.wel` | Original 2003-2023 pumping from pre-automation era |
| Subsequent years (2025+) | `output/modflow/{year-1}/thruCY2165_{year-1}.wel` | Prior year's output (contains 2003 through year-1) |

**Chaining rule:** Parse input WEL file to find target year boundaries (searches for "JAN {year}" and "DEC {year}" patterns), replace the target year section with newly generated entries from current year's Table 2 pumping data.

**Structural invariant:** After processing year N, the WEL file contains:
- Pre-target lines: all pumping from 2003 through year N-1 (unchanged)
- Target year lines: 324 lines of year N pumping (newly generated)
- Post-target lines: projected pumping for 2165 (unchanged, from baseline)

#### Step 4: Table 3 Chaining (Stream Depletions)

Table 3 reports cumulative stream depletions for Rio Pojoaque-Nambe and Rio Tesuque. Historical values must be preserved from the year they were computed.

| Scenario | Historical Source | Behavior |
|----------|-----------------|----------|
| First resolution | `output/depletion/TABLE_3_*_{year-1}.xlsx` | Prior year's Table 3 output |
| Fallback | `validation/2024/expected_outputs/Table_3_expected.xlsx` | Frozen 2024 baseline |
| Neither exists | Hardcoded constants | Uses LA_CIENEGA_CUMULATIVE dict |

**Chaining rule:** For years before processing_year, values are copied verbatim from the prior year's Table 3. For years >= processing_year, values are recalculated from the current MODFLOW post-processor output. This ensures that 1988-2023 values remain locked to their respective MODFLOW runs while 2024+ values reflect the latest model.

#### Step 4: Table 5 Chaining (La Cienega Springs)

Table 5 follows the same chaining pattern as Table 3 but for La Cienega Springs cumulative depletions.

| Scenario | Historical Source | Behavior |
|----------|-----------------|----------|
| First resolution | `output/depletion/TABLE_5_*_{year-1}.xlsx` | Prior year's Table 5 output |
| Fallback | LA_CIENEGA_CUMULATIVE dict | Hardcoded historical values (2004-2030) |

**Chaining rule:** Years before processing_year use historical values from prior year's output. Years >= processing_year are recomputed from current MODFLOW output using cfs-to-AF conversion.

### 6.2 Directory Structure Evolution

The output directory structure changed between the pre-automation era and the automated pipeline:

| Year Range | Structure | Path Pattern |
|-----------|-----------|-------------|
| 2024 and earlier | Nested | `output/modflow/{year}/modflow/CY{year}.*` |
| 2025 and later | Flat | `output/modflow/{year}/CY{year}.*` |

All scripts auto-detect both structures. The flat structure was adopted for simplicity; the nested structure is preserved for backward compatibility with the 2024 baseline.

### 6.3 Leap Year Handling

Leap years affect the AF-to-ft^3/s conversion for February and any annual aggregation.

| Component | Leap Year Effect | Implementation |
|-----------|-----------------|----------------|
| WEL file rates | February: 29 vs 28 days in denominator | `calendar.isleap(year)` in `get_days_in_month()` |
| Table 3 superposition | cfs-to-AF conversion uses actual calendar days | `get_days_in_year(year)` returns 12-element list |
| Table 5 cumulative | Same cfs-to-AF conversion | `calendar.isleap(year)` passed to converter |

### 6.4 Physical Bounds

| Parameter | Min | Max | Units | Basis |
|-----------|-----|-----|-------|-------|
| Lines added per year | 324 | 324 | lines | WEL file format (invariant) |
| Wells per stress period | 26 | 26 | entries | 13 wells x 2 layers (invariant) |
| Total annual pumping | 0 | ~5,000 | AF | Engineering limit |
| Individual well rate | 0 | ~2 | ft^3/s | Well capacity |
| Pumping sign convention | -inf | 0 | ft^3/s | MODFLOW convention (negative = extraction) |

### Conservation Laws

- **Volumetric conservation:** Total pumping in WEL file must equal total pumping in Table 2 (within floating-point tolerance)
- **Monotonic accumulation:** WEL file line count must increase by exactly 324 per year
- **Historical preservation:** Pre-processing_year rows in Tables 3 and 5 must be byte-identical to prior year's output

### Regulatory Limits

- **Sequential integrity:** No year may be skipped; OSE report must show continuous annual record
- **Cumulative consistency:** Depletion values in Table 3 must be monotonically non-decreasing (you cannot "un-deplete" a stream)
- **Baseline immutability:** The 2023 baseline files (input/modflow/2023/) must never be modified after initial validation

---

## 7. References

### Publications
- Core, A.A. (2003). Santa Fe River Water Budget Model Technical Report. New Mexico Office of the State Engineer.
- Spinks, K.L. (1988). Buckman Wellfield Analytical Depletion Projections. NMBGMR.
- McDonald, M.G. & Harbaugh, A.W. (1988). A Modular Three-Dimensional Finite-Difference Ground-Water Flow Model. USGS TWRI Book 6, Chapter A1.

### Standards
- MODFLOW-96 Well Package (WEL) file format specification
- USGS Water-Use Data System (WUDS) volume conversion factors

### Data Sources
- City of Santa Fe daily pumping records (CSV format, annual delivery)
- OSE historical Buckman wellfield reports (1988--present)

---

## 8. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Pumping data ingestion (Step 1) that feeds into year chaining |
| DS-02 | MODFLOW model structure that consumes the chained WEL file |
| DS-03 | Stream depletion calculations that use chained Tables 3 and 5 |
| DS-05 | Quality assurance tests that verify chaining integrity |
| DS-06 | Provenance logging that documents chain-of-custody for each year |
| IS-01 | Implementation of step1_ingest_buckman_data.py (Table 1 chaining) |
| IS-02 | Implementation of step2_update_modflow.py (WEL file chaining) |
| IS-04 | Implementation of step4_generate_depletion_tables.py (Tables 3/5 chaining) |

---

*Document Maintenance:*
- *Next Review:* When a new baseline year is established or the chaining logic is modified
- *Change Triggers:* Addition of new wells, changes to WEL file format, modification of Table 3/5 chaining fallback sources, changes to BASELINE_YEAR constant
