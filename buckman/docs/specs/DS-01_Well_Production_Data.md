# DS-01: Buckman Wellfield & Well Production Data

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Draft
**Author:** Claude Code (Anthropic) + Brad Wolaver (NMOSE)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Purpose & Scope

This specification documents the Buckman Wellfield production data ingestion process for the City of Santa Fe's water rights compliance reporting. The Buckman Wellfield consists of 13 production wells operated under New Mexico Office of the State Engineer (OSE) permits. Daily pumping records in million gallons per day (MGD) are received as CSV files, aggregated to monthly and annual totals, converted to acre-feet (AF), validated against internal checksums, and formatted into Tables 1 and 2 for annual depletion reports submitted to the OSE. Accurate pumping data is the upstream input to all subsequent MODFLOW modeling and stream depletion calculations.

---

## 2. Scientific Basis

### 2.1 Key Equations

**Volume conversion (MG to AF):**

```
AF = MG * 3.06889

Derivation:
  1 acre-foot = 325,851 gallons   (USGS definition)
  1 MG        = 1,000,000 gallons

  AF/MG = 1,000,000 gal / 325,851 gal/AF = 3.06889 AF/MG
```

**Daily-to-monthly aggregation:**

```
Monthly_MG = SUM(Daily_MGD_i)   for i = 1..N_days

Dimensional analysis:
  MGD * day = (MG/day) * day = MG

  The numerical sum of daily MGD values IS the monthly MG total
  because summing MGD values over N days implicitly multiplies by
  1 day per record.
```

### 2.2 Worked Example

**Step 1: Sum daily MGD to monthly MG**

Suppose Buckman Well #1 pumps the following in January 2024 (31 days):
- Days 1-15: 1.200 MGD
- Days 16-31: 0.800 MGD (16 days)

```
Monthly_MG = (15 * 1.200) + (16 * 0.800)
           = 18.000 + 12.800
           = 30.800 MG
```

**Step 2: Convert monthly MG to AF**

```
Monthly_AF = 30.800 MG * 3.06889 AF/MG
           = 94.522 AF
```

**Step 3: Annual total**

Sum all 12 monthly AF values for the well's annual production.

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | Daily CSV values are in MGD (million gallons per day) | Column header format "BWell N\|Flow Mgd" and consistent with historical files | Wrong unit interpretation would produce values off by orders of magnitude | Cross-check monthly totals against CSV Sum row |
| 2 | Zero daily values are valid (well not pumping) | Wells are routinely shut down for maintenance or seasonal demand reduction | None -- zero is a physically valid state | Flagging system distinguishes zero from missing |
| 3 | Negative daily values are physically impossible | Flow meters measure only forward flow; negative values indicate data entry error | Negative values would corrupt monthly totals | Flagged as "NEGATIVE" in validation |
| 4 | Blank/NaN values indicate missing data, not zero pumping | Missing SCADA records differ from confirmed zero-production days | Treating blanks as zeros could undercount pumping if well was actually operating | Flagged as "BLANK"; months with any blanks marked Has_Flagged_Data=True |
| 5 | The CSV Sum row provides independent annual totals for each well | City database computes these sums independently from the daily values | If Sum row is also derived from daily values, it is not truly independent | Tolerance-based comparison (0.01 MG) catches discrepancies |
| 6 | Well 3 and Well 3A are reported as a single combined well ("3/3A") | Historical convention from OSE permit structure; permit RG-20516-S covers both | Separate accounting could yield different per-well totals | Documented in WELL_OSE_MAP and Table 1/2 headers |
| 7 | 1 MG = 3.06889 AF is the correct conversion factor | Derived from USGS definition: 1 AF = 325,851 gallons | Using incorrect factor would propagate error to all downstream tables | Factor is hardcoded and validated against USGS reference |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| City of Santa Fe SCADA | Daily well production CSV files | Email delivery to NMOSE | Annually (January-February for prior year) | Three-tier daily sum verification |
| CSV file | `Buckman_Well_Prod_{year}.csv` with 366 daily rows + 4 summary rows (Sum, Avg, Max, Min) | Local filesystem: `./input/csv/` | One file per calendar year | Column presence check, date range validation, annual sum comparison |
| USGS unit definitions | Gallon-to-AF conversion factor | Published standard (USGS NAWQA glossary) | Static | Hardcoded constant verified against source |

### CSV File Structure

```
Header row:   "1/1/2024-12/31/2024", "BWell 1|Flow Mgd", ..., "BWell 13|Flow Mgd", "BWP|Flow Mgd|MGD|Formula"
Row 1-366:    Date, Well_1_MGD, Well_2_MGD, ..., Well_13_MGD, BWP_Total_MGD
Row 367:      "Sum", annual_MG_1, annual_MG_2, ..., annual_MG_13, annual_MG_total
Row 368:      "Avg", avg_MGD_1, ..., avg_MGD_total
Row 369:      "Max", max_MGD_1, ..., max_MGD_total
Row 370:      "Min", min_MGD_1, ..., min_MGD_total
```

**Column naming convention:**
- Individual wells: `"BWell N|Flow Mgd"` where N = 1-13
- Total column: `"BWP|Flow Mgd|MGD|Formula"` (BWP = Buckman Well Production, formula-computed sum)

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| MG_TO_AF_FACTOR | 3.06889 | AF/MG | 1,000,000 gal / 325,851 gal/AF | USGS |
| NOISE_THRESHOLD_MGD | 0.0015 | MGD | 1,500 gal/day; below flow meter precision for production wells | Observed database rounding artifacts (900-1,500 gal range) |
| DAILY_SUM_TOLERANCE_INFO_MGD | 0.001 | MGD | 1,000 gal/day; typical Excel formula rounding | Empirical from historical CSV files |
| DAILY_SUM_TOLERANCE_ERROR_MGD | 0.005 | MGD | 5,000 gal/day; ~0.2% of average daily production | Engineering judgment |
| ANNUAL_SUM_TOLERANCE_MG | 0.01 | MG | 10,000 gal; accumulated rounding from 366 daily values | Empirical from historical CSV files |

### Dimensional Analysis

**MGD to monthly MG:**

```
MGD --> MG (monthly)

SUM_{day=1}^{N} (MGD_day) = MG_month

Units: [MG/day] * [day] = [MG]
       The sum of N daily MGD values = N-day volume in MG
```

**MG to AF:**

```
MG --> AF

AF = MG * (1,000,000 gal/MG) / (325,851 gal/AF)
   = MG * 3.06889 AF/MG
```

**Complete chain: Daily MGD to Annual AF**

```
Daily MGD --> Monthly MG --> Monthly AF --> Annual AF

Step 1: Monthly_MG = SUM(Daily_MGD)         [sum over days in month]
Step 2: Monthly_AF = Monthly_MG * 3.06889   [unit conversion]
Step 3: Annual_AF  = SUM(Monthly_AF)         [sum over 12 months]
```

---

## 6. Domain-Specific Constraints

### Physical Bounds

| Parameter | Min | Max | Units | Basis |
|-----------|-----|-----|-------|-------|
| Daily well production | 0.0 | ~10.0 | MGD | Zero when shut down; max based on pump capacity |
| Daily total production (BWP) | 0.0 | ~30.0 | MGD | Sum of 13 wells; historical max ~25 MGD |
| Monthly well production | 0.0 | ~310.0 | MG | 10 MGD * 31 days = 310 MG theoretical max |
| Annual well production | 0.0 | ~3,650.0 | MG | 10 MGD * 365 days theoretical max per well |
| Annual total production | 0.0 | ~5,000.0 | AF | Historical range: 1,500-4,000 AF/year |

### Conservation Laws

- **Mass balance**: Sum of 13 individual well daily totals must equal BWP daily total (within tolerance). This is verified at three tiers: noise (0.0015 MGD), info (0.001 MGD), and error (0.005 MGD).
- **Temporal consistency**: Monthly MG totals summed over 12 months must equal the CSV annual Sum row value for each well (within 0.01 MG).

### Regulatory Limits

- Buckman Wellfield operates under OSE permit RG-20516-S (base permit) and supplemental permits -S-2 through -S-13.
- Annual reporting to the OSE requires Table 1 (historical annual pumping) and Table 2 (monthly pumping for current year), both in acre-feet.

---

## 7. Well Inventory

### 7.1 Buckman Wells and OSE Permit Numbers

| Well # | OSE Permit Number | MODFLOW Name | Report Label | Notes |
|--------|-------------------|--------------|--------------|-------|
| 1 | RG-20516-S-5 | BUCKMAN 1 | Buckman #1 | Primary production well |
| 2 | RG-20516-S-6 | BUCKMAN 2 | Buckman #2 | |
| 3 | RG-20516-S | BUCKMAN 3A | Buckman #3/3A | Combined wells 3 and 3A; base permit |
| 4 | RG-20516-S-2 | BUCKMAN 4 | Buckman #4 | |
| 5 | RG-20516-S-3 | BUCKMAN 5 | Buckman #5 | |
| 6 | RG-20516-S-4 | BUCKMAN 6 | Buckman #6 | |
| 7 | RG-20516-S-7 | BUCKMAN 7 | Buckman #7 | Primary production well |
| 8 | RG-20516-S-8 | BUCKMAN 8 | Buckman #8 | Primary production well |
| 9 | RG-20516-S-9 | BUCKMAN 9 | Buckman #9 | |
| 10 | RG-20516-S-10 | BUCKMAN 10 | Buckman #10 | High-capacity production well |
| 11 | RG-20516-S-11 | BUCKMAN 11 | Buckman #11 | High-capacity production well |
| 12 | RG-20516-S-12 | BUCKMAN 12 | Buckman #12 | High-capacity production well |
| 13 | RG-20516-S-13 | BUCKMAN 13 | Buckman #13 | High-capacity production well |

### 7.2 CSV Column Mapping

Each well maps to a CSV column with the header format `"BWell N|Flow Mgd"`:

```
"BWell 1|Flow Mgd"   --> Well 1  (RG-20516-S-5)
"BWell 2|Flow Mgd"   --> Well 2  (RG-20516-S-6)
"BWell 3|Flow Mgd"   --> Well 3  (RG-20516-S, reported as 3/3A)
"BWell 4|Flow Mgd"   --> Well 4  (RG-20516-S-2)
...
"BWell 13|Flow Mgd"  --> Well 13 (RG-20516-S-13)

"BWP|Flow Mgd|MGD|Formula"  --> Total (formula-computed sum of all wells)
```

---

## 8. Data Validation Framework

### 8.1 Three-Tier Daily Sum Verification

Each day, the sum of 13 individual well values is compared to the BWP total column from the CSV. The BWP column is the City's own formula, not an external reference.

**Tier 1 -- Noise Floor (database precision artifacts):**
- Condition: 0 < BWP < 0.0015 MGD
- Interpretation: Below instrument precision; 1,500 gal/day is within the 100-gallon rounding range of the SCADA system
- Action: Log as INFO; no impact on monthly totals
- Physical meaning: Database stores values with ~100-gallon precision, producing artifacts in the 900-1,500 gal/day range

**Tier 2 -- Formula Error (logical inconsistency):**
- Condition: All 13 wells = 0 but BWP >= 0.0015 MGD
- Interpretation: Impossible physical state; BWP should be zero when no wells are pumping
- Action: Flag as ERROR; requires CSV review
- Physical meaning: The City's formula column has a bug or data entry error

**Tier 3 -- Precision Tolerance (Excel rounding):**
- Condition: |SUM(wells) - BWP| evaluated against thresholds
- OK: difference <= 0.001 MGD (1,000 gal/day)
- INFO: 0.001 < difference <= 0.005 MGD
- ERROR: difference > 0.005 MGD (5,000 gal/day, ~0.2% of average daily production)
- Physical meaning: Expected rounding differences from Excel formula precision

### 8.2 Annual Sum Verification

For each well, the sum of 12 monthly MG values is compared to the CSV Sum row:

```
|SUM(monthly_MG) - CSV_Sum_MG| <= 0.01 MG  (10,000 gallons)
```

This catches systematic rounding accumulation across the year.

### 8.3 Data Quality Flags

Each daily value receives a quality flag:

| Flag | Meaning | Action |
|------|---------|--------|
| (empty) | Valid data point | Use in aggregation |
| BLANK | Missing/NaN value | Include in sum as 0; mark month as Has_Flagged_Data |
| NEGATIVE | Negative flow value | Include in sum; mark month as Has_Flagged_Data |

If any day in a month has a flag, the entire month is marked `Has_Flagged_Data=True` and the monthly CSV output shows `Data_Quality=FLAGGED` for that well.

---

## 9. Output Products

### 9.1 Table 1: Historical Annual Pumping

- **Content**: Annual pumping by well in acre-feet per year (AF/yr)
- **Format**: Wells 1-13 as columns, years as rows (one row added per year)
- **Well 3 label**: "3/3A" in the column header (combined wells)
- **File**: `{year}_Table_1_output.xlsx`
- **Purpose**: Historical trend analysis for OSE annual report

### 9.2 Table 2: Monthly Pumping for Current Year

- **Content**: Monthly pumping by well in acre-feet per month (AF/month)
- **Format**: Wells 1-13 as rows, months JAN-DEC as columns, with Total column
- **File**: `{year}_Table_2_output.csv`
- **Purpose**: Input to MODFLOW well package update (Step 2); OSE annual report
- **Downstream dependency**: `step2_update_modflow.py` reads this file directly

### 9.3 Monthly CSVs

- **Content**: Per-well MG and AF values with data quality flags for one month
- **Format**: 13 well rows + Calculated_Sum row
- **Files**: `{year}_{MM}_{MON}.csv` (e.g., `2024_07_JUL.csv`)
- **Purpose**: Intermediate data verification

### 9.4 Input Summary

- **Content**: Data quality summary across all wells and months
- **File**: `{year}_input_summary.csv`
- **Purpose**: Audit trail for flagged data

---

## 10. Dimensional Safety

The pipeline uses the Python `pint` library for unit tracking:

```python
ureg = UnitRegistry()
ureg.define('million_gallon = 1e6 * gallon = MG')
ureg.define('million_gallon_per_day = million_gallon / day = MGD')
```

This ensures that:
1. Daily MGD values multiplied by day units yield MG volumes
2. MG-to-AF conversion uses the pint library's built-in gallon-to-acre-foot relationship
3. Unit mismatches raise `DimensionalityError` at runtime rather than producing silent numerical errors

---

## 11. References

### Publications
- USGS, "National Water-Quality Assessment (NAWQA) Glossary," https://water.usgs.gov/nawqa/glos.html (definition: 1 acre-foot = 325,851 gallons)

### Standards
- New Mexico Office of the State Engineer, Water Rights Reporting Requirements for Municipal Wells
- USGS Water-Use Terminology (MGD, AF, cfs)

### Data Sources
- City of Santa Fe, Buckman Wellfield SCADA System, daily production CSV files delivered annually

---

## 12. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-02 | Table 2 output (AF/month) is the input to MODFLOW well package update |
| DS-03 | Pumping data drives all stream depletion calculations downstream |
| IS-01 | Implementation spec for `step1_ingest_buckman_data.py` |

---

*Document Maintenance:*
- *Next Review:* When CSV format changes or new wells are added to the Buckman Wellfield
- *Change Triggers:* New well drilled (update WELL_OSE_MAP); CSV column format change; USGS conversion factor revision; change in OSE reporting requirements
