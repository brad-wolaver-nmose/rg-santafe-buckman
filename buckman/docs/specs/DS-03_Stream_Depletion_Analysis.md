# DS-03: Stream Depletion Analysis

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Draft
**Author:** Claude Code (Anthropic) + Brad Wolaver (NMOSE)
**Created:** 2026-02-20
**Last Updated:** 2026-02-23

---

## 1. Purpose & Scope

This specification documents the stream depletion analysis that converts MODFLOW boundary-condition fluxes into depletion tables for the OSE annual compliance report. The analysis quantifies how Buckman Wellfield pumping reduces flows in the Rio Grande, Rio Pojoaque-Nambe, Rio Tesuque, and La Cienega Springs. It combines numerical MODFLOW results (1988-present pumping via superposition) with analytical residuals from Core (2003) for pre-1988 pumping effects. The outputs are Tables 3, 4, and 5 of the annual depletion report.

---

## 2. Scientific Basis

### 2.1 Superposition Principle

The MODFLOW model calculates stream depletions from 1988 through the current year using the **superposition principle**: the model simulates only the change in heads and fluxes caused by Buckman pumping, relative to a no-pumping baseline. Stream depletion is the difference in boundary-condition flux between the pumping and no-pumping scenarios.

Because the aquifer flow equation is linear (for confined conditions or when head changes are small relative to saturated thickness), effects of different pumping periods can be superposed:

```
Total Depletion = Depletion(pre-1988 pumping) + Depletion(1988-present pumping)
                = Core (2003) Analytical Residuals + MODFLOW Superposition Results
```

### 2.2 Key Equations

**cfs to acre-feet conversion:**

```
AF = cfs * days * 86,400 s/day / 43,560 ft^3/AF
   = cfs * days * 1.9835

Where:
  cfs   = cubic feet per second (monthly average depletion rate)
  days  = number of days in the month
  1.9835 = 86,400 / 43,560 (exact conversion factor)
```

**Table 3 total impact:**

```
Total_Impact_AF = Residual_AF + Superposition_AF

Where:
  Residual_AF      = Core (2003) analytical model value for pre-1988 pumping
  Superposition_AF = SUM over 12 months of (cfs_month * days_month * 1.9835)
```

**Table 5 annual increment:**

```
Annual_Increment_AF = Cumulative_AF(year) - Cumulative_AF(year - 1)

Where cumulative values come from MODFLOW GHB flux output.
```

**Rio Tesuque residual (1988-2050):**

```
CORE_2003_TESUQUE dict contains explicit values for all 63 years (1988-2050).
No extrapolation formula is needed.
Residual reaches 0.117 AF in 2050 and is 0.0 for years beyond 2050.
```

### 2.3 Worked Example -- Table 3 (Rio Pojoaque, 2024)

```
Step 1: Look up Core (2003) residual for Rio Pojoaque in 2024
  Pojoaque residual exhausted after 2015 (dictionary ends at 2015: 0.316)
  For 2024: Residual_AF = 0.0 AF

Step 2: Extract MODFLOW superposition (R POJOAQUE monthly cfs)
  jan=0.083581, feb=0.083553, ..., dec=0.083xxx (12 values from post-processor)

Step 3: Convert each month from cfs to AF
  January: 0.083581 * 31 * 1.9835 = 5.137 AF
  February: 0.083553 * 29 * 1.9835 = 4.804 AF  (2024 is a leap year)
  ...sum all 12 months...

Step 4: Sum for annual superposition total
  Superposition_AF = SUM(monthly_AF) = ~60.797 AF (approximate)

Step 5: Calculate total impact
  Total_Impact_AF = 0.0 + 60.797 = 60.797 AF
```

### 2.4 Worked Example -- cfs to AF Conversion

```
Given: 1.0 cfs flow for 30 days
  AF = 1.0 * 30 * 86400 / 43560
     = 1.0 * 30 * 1.9835
     = 59.505 AF

Verification: 1 cfs = 1 ft^3/s
  Volume = 1 ft^3/s * 30 days * 86400 s/day = 2,592,000 ft^3
  AF = 2,592,000 / 43,560 = 59.505 AF
```

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | Superposition is valid (aquifer response is linear) | Buckman pumping causes small head changes relative to total saturated thickness; aquifer behavior approximately linear | Non-linear effects would cause depletion estimates to be inaccurate | Model has been calibrated and validated against observed streamflow data since 2003 |
| 2 | Core (2003) analytical residuals are correct | Published technical report with peer review; values manually transcribed from PROJECTION.XLS | Transcription errors would affect Table 3 totals | Values are hardcoded constants verified against source document |
| 3 | Pojoaque residual is zero after 2015 | Core (2003) table ends at 2015: 0.316; physical basis is that pre-1988 pumping effects have fully propagated | If residual still exists, Table 3 slightly underestimates Pojoaque depletion | Conservative for compliance (reports lower depletion than actual) |
| 4 | Tesuque residual values are explicit through 2050 | `CORE_2003_TESUQUE` dict contains 63 entries (1988-2050) derived from Core (2003) PROJECTION.XLS; residual reaches 0.117 AF in 2050 and is 0.0 after | No extrapolation needed; values beyond 2050 return 0.0 | Dict values verified against source document; linear decline pattern is consistent with late-time analytical solution behavior |
| 5 | FORTRAN post-processor cell ranges match actual MODFLOW cells | Hardcoded rectangles in sfmodflx_2245.for must encompass all RIV and GHB cells | Cells outside rectangles are silently excluded from depletion totals | See docs/MODFLOW_CELL_MAPPING.md for validation procedure |
| 6 | All GHB cells represent La Cienega Springs | No other GHB features in the model | Adding other GHB features would corrupt La Cienega totals | Model geometry has been stable since 2003 |
| 7 | La Cienega MODFLOW output is cumulative from 2004 | Annual increment = cum(N) - cum(N-1) | Wrong reference point would produce incorrect annual values | Historical cumulative values validated against published Table 5 |
| 8 | Stream labels in FORTRAN output match Python parser expectations exactly | "R POJOAQUE", "R TESUQUE", "RIO GRANDE", "RIV TOTAL", "LC SPRINGS" | String mismatch causes ValueError at runtime (fail-fast) | Regex matching with whitespace normalization |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| MODFLOW binary flux files | `CY{year}_riv.flx` and `CY{year}_ghb.flx` | Output from Step 3 (MODFLOW run) | Annually | Convergence check in .lst file |
| FORTRAN post-processor output | `CY{year}` formatted text file | Output from `sfmodflx_2245.exe` | Annually | Parsed and validated in Python |
| Core (2003) PROJECTION.XLS | Analytical residual values for pre-1988 pumping | Hardcoded dictionaries in stream_depletions.py | Static (2003 publication) | Manual verification against source document |
| Historical Table 3 baseline | `validation/2024/expected_outputs/Table_3_expected.xlsx` | Local filesystem | Annual update with validated results | Cross-checked against prior year's published report |
| La Cienega cumulative values | `LA_CIENEGA_CUMULATIVE` dictionary | Hardcoded in stream_depletions.py | Annually (manually updated from Table 5 output) | Manual entry from validated Excel output |

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| cfs-to-AF factor | 1.9835 | AF/(cfs*day) | 86,400 s/day / 43,560 ft^3/AF | Standard unit conversion |
| SECONDS_PER_DAY | 86,400 | s/day | 24 * 60 * 60 | Standard |
| FT3_PER_AF | 43,560 | ft^3/AF | 1 acre * 1 foot | Standard |

### Dimensional Analysis -- cfs to AF

```
cfs --> AF (for N days)

AF = cfs * N_days * 86,400 s/day / 43,560 ft^3/AF

Cancel units:
  [ft^3/s] * [days] * [s/day] / [ft^3/AF]
= [ft^3] / [ft^3/AF]
= [AF]

Simplified: AF = cfs * N_days * 1.9835
```

---

## 6. Three-Layer Data Processing System

Stream depletions flow through three independent processing layers. Each layer defines cell-to-stream assignments independently, creating a fragile chain where consistency must be manually maintained.

### 6.1 Layer 1: MODFLOW Input Files

MODFLOW GHB and RIV package files define the physical locations of boundary condition cells:

- **RIV package** (`thruCY2165.riv`): Tributary stream cells at rows 9-17, columns 14-25
- **GHB package** (`thruCY2165.ghb`): La Cienega Springs cells at rows 30-32, columns 12-15

These files contain only `(layer, row, col, head, conductance)` -- no stream labels.

### 6.2 Layer 2: FORTRAN Post-Processor (sfmodflx_2245.exe)

The FORTRAN post-processor reads MODFLOW binary flux files and assigns cells to streams using hardcoded spatial rules.

**Cell extraction rectangles (SUBROUTINE FILL):**

| Package | Start Row | End Row | Start Col | End Col | Streams |
|---------|-----------|---------|-----------|---------|---------|
| RIV (JJ2=1) | 9 | 17 | 14 | 25 | R POJOAQUE, R TESUQUE, RIO GRANDE |
| GHB (JJ2=2) | 28 | 35 | 10 | 20 | LC SPRINGS |

**Stream assignment logic (SUBROUTINE TOTAL):**

For RIV cells within rows 9-17, columns 14-25:
- **R POJOAQUE**: `(row == 9 AND col > 13) OR (row < 13 AND col > 21)`
- **R TESUQUE**: `col > 18` (and not already assigned to Pojoaque)
- **RIO GRANDE**: All other RIV cells
- **RIV TOTAL**: Sum of R POJOAQUE + R TESUQUE + RIO GRANDE

For GHB cells:
- **LC SPRINGS**: Sum of ALL GHB cells (no spatial logic; all GHB cells are La Cienega)

**Output format:**

```
YEAR: 2024        jan         feb        ...        dec
  LAY ROW COL
    1   9  14    0.025737    0.025725   ...    0.025xxx
    1   9  15    0.013421    0.013415   ...    0.013xxx
    ...
0  R POJOAQUE    0.083581    0.083553   ...    0.083xxx
0  R TESUQUE     0.141234    0.141198   ...    0.141xxx
0  RIO GRANDE    0.562847    0.562791   ...    0.562xxx
0  RIV  TOTAL    0.787662    0.787542   ...    0.787xxx
0  LC SPRINGS    0.083581    0.083581   ...    0.083xxx
```

### 6.3 Layer 3: Python Parser (stream_depletions.py)

The Python parser reads the FORTRAN output text file using regex matching:

**Stream name registry:**
```
"R POJOAQUE"   -- Rio Pojoaque-Nambe
"R TESUQUE"    -- Rio Tesuque
"RIO GRANDE"   -- Rio Grande main stem
"RIV TOTAL"    -- Total river depletions (sum of above 3)
"LC SPRINGS"   -- La Cienega Springs (GHB package)
```

**Parsing rules:**
- Cell data lines: `^\s+(\d+)\s+(\d+)\s+(\d+)\s+(12 float values)`
- Stream summary lines: `^0\s+(stream_name)\s+(12 float values)`
- Year headers: `^YEAR:\s+(\d{4})\s+jan`
- Whitespace in stream names normalized (e.g., `"RIV  TOTAL"` becomes `"RIV TOTAL"`)

### 6.4 Critical Risk: No Automatic Connection Between Layers

There is NO automated validation that FORTRAN cell ranges match actual MODFLOW cell locations. If the model geometry changes (e.g., a new GHB cell at row 27), the FORTRAN rectangle would miss it silently. See `docs/MODFLOW_CELL_MAPPING.md` for a complete analysis of this risk and mitigation procedures.

---

## 7. Core (2003) Analytical Residuals

### 7.1 Rio Pojoaque-Nambe Residuals

Decreasing residual effect from pre-1988 (specifically 1972-1987) Buckman pumping on Rio Pojoaque-Nambe. Values from Core (2003) PROJECTION.XLS:

| Year | Residual (AF) | | Year | Residual (AF) |
|------|--------------|---|------|--------------|
| 1988 | 40.432 | | 2002 | 17.753 |
| 1989 | 39.244 | | 2003 | 16.543 |
| 1990 | 37.971 | | 2004 | 15.429 |
| 1991 | 36.557 | | 2005 | 14.404 |
| 1992 | 34.928 | | 2006 | 13.462 |
| 1993 | 33.112 | | 2007 | 12.595 |
| 1994 | 31.185 | | 2008 | 11.797 |
| 1995 | 29.226 | | 2009 | 11.061 |
| 1996 | 27.296 | | 2010 | 10.383 |
| 1997 | 25.439 | | 2011 | 6.151 |
| 1998 | 23.678 | | 2012 | 4.693 |
| 1999 | 22.028 | | 2013 | 3.234 |
| 2000 | 20.491 | | 2014 | 1.775 |
| 2001 | 19.068 | | 2015 | 0.316 |

**After 2015:** Residual = 0.0 AF (effect fully exhausted).

### 7.2 Rio Tesuque Residuals

Longer-lasting residual effect on Rio Tesuque. Initial values increase (peaking around 1995-1996 at ~25.7 AF) before declining:

| Year | Residual (AF) | | Year | Residual (AF) |
|------|--------------|---|------|--------------|
| 1988 | 21.015 | | 2010 | 19.639 |
| 1989 | 22.333 | | 2011 | 19.258 |
| 1990 | 23.391 | | 2012 | 18.767 |
| 1991 | 24.227 | | 2013 | 18.276 |
| 1992 | 24.868 | | 2014 | 17.785 |
| 1993 | 25.327 | | 2015 | 17.295 |
| 1994 | 25.615 | | 2016 | 16.804 |
| 1995 | 25.747 | | 2017 | 16.313 |
| 1996 | 25.737 | | 2018 | 15.822 |
| 1997 | 25.608 | | 2019 | 15.331 |
| 1998 | 25.378 | | 2020 | 14.841 |
| 1999 | 25.067 | | 2021 | 14.350 |
| 2000 | 24.691 | | 2022 | 13.859 |
| 2001 | 24.265 | | 2023 | 13.368 |
| 2002 | 23.800 | | 2024 | 12.877 |
| 2003 | 23.308 | | 2025 | 12.387 |
| 2004 | 22.797 | | 2026 | 11.896 |
| 2005 | 22.273 | | 2027 | 11.405 |
| 2006 | 21.743 | | 2028 | 10.914 |
| 2007 | 21.212 | | 2029 | 10.424 |
| 2008 | 20.683 | | 2030 | 9.933 |
| 2009 | 20.157 | | | |

**2031-2050:** Explicit values continue in `CORE_2003_TESUQUE` dict (63 entries total, 1988-2050):

| Year | Residual (AF) | | Year | Residual (AF) |
|------|--------------|---|------|--------------|
| 2031 | 9.442 | | 2041 | 4.534 |
| 2032 | 8.951 | | 2042 | 4.043 |
| 2033 | 8.460 | | 2043 | 3.552 |
| 2034 | 7.970 | | 2044 | 3.062 |
| 2035 | 7.479 | | 2045 | 2.571 |
| 2036 | 6.988 | | 2046 | 2.080 |
| 2037 | 6.497 | | 2047 | 1.589 |
| 2038 | 6.006 | | 2048 | 1.098 |
| 2039 | 5.516 | | 2049 | 0.608 |
| 2040 | 5.025 | | 2050 | 0.117 |

**After 2050:** Residual = 0.0 AF (effect fully exhausted). The Tesuque residual reaches 0.117 AF in 2050, and `get_analytical_residual()` returns 0.0 for all years beyond 2050 via `.get(year, 0.0)`.

---

## 8. Otowi Gage Cell Definitions

Table 4 divides the Rio Grande into reaches above and below the Otowi Bridge stream gage:

### 8.1 Above Otowi Cells (10 cells)

| # | Layer | Row | Column |
|---|-------|-----|--------|
| 1 | 1 | 1 | 16 |
| 2 | 1 | 2 | 16 |
| 3 | 1 | 3 | 16 |
| 4 | 1 | 4 | 16 |
| 5 | 1 | 5 | 15 |
| 6 | 1 | 6 | 14 |
| 7 | 1 | 7 | 14 |
| 8 | 1 | 8 | 13 |
| 9 | 1 | 9 | 13 |
| 10 | 1 | 10 | 12 |

### 8.2 Below Otowi Cells (16 cells)

| # | Layer | Row | Column |
|---|-------|-----|--------|
| 1 | 1 | 11 | 11 |
| 2 | 1 | 12 | 11 |
| 3 | 1 | 13 | 11 |
| 4 | 1 | 14 | 10 |
| 5 | 1 | 15 | 9 |
| 6 | 1 | 15 | 10 |
| 7 | 1 | 16 | 9 |
| 8 | 1 | 17 | 8 |
| 9 | 1 | 18 | 6 |
| 10 | 1 | 18 | 7 |
| 11 | 1 | 19 | 6 |
| 12 | 1 | 20 | 5 |
| 13 | 1 | 21 | 4 |
| 14 | 1 | 21 | 5 |
| 15 | 1 | 22 | 4 |
| 16 | 1 | 23 | 3 |

### 8.3 Buckman Wells Cell

Cell (1, 13, 11) -- the MODFLOW cell containing the Buckman wellfield cluster (Wells 1, 7, 8). This cell's depletion is reported separately in Table 4 to show the direct impact at the wellfield location on the Rio Grande.

---

## 9. La Cienega Springs (Table 5)

### 9.1 Cumulative Depletion Baseline

La Cienega Springs depletion is tracked as a **cumulative** value starting from 2004. The MODFLOW GHB flux output represents cumulative impact from all 1988-present pumping. Annual increment is computed by differencing:

```
Annual_Increment(year) = Cumulative(year) - Cumulative(year - 1)
```

### 9.2 Historical Cumulative Values (LA_CIENEGA_CUMULATIVE)

These values are manually entered from official Table 5 outputs:

| Year | Cumulative AF | Annual Increment AF |
|------|--------------|-------------------|
| 2004 | 0.45 | 0.45 (first year) |
| 2005 | 0.66 | 0.21 |
| 2006 | 0.83 | 0.17 |
| 2007 | 0.99 | 0.16 |
| 2008 | 1.16 | 0.17 |
| 2009 | 1.32 | 0.16 |
| 2010 | 1.49 | 0.17 |
| 2011 | 1.65 | 0.16 |
| 2012 | 1.82 | 0.17 |
| 2013 | 1.97 | 0.15 |
| 2014 | 2.13 | 0.16 |
| 2015 | 2.29 | 0.16 |
| 2016 | 2.45 | 0.16 |
| 2017 | 2.60 | 0.15 |
| 2018 | 2.75 | 0.15 |
| 2019 | 2.90 | 0.15 |
| 2020 | 3.06 | 0.16 |
| 2021 | 3.21 | 0.15 |
| 2022 | 3.37 | 0.16 |
| 2023 | 3.54 | 0.17 |
| 2024 | 3.74 | 0.20 |
| 2025 | 3.92 | 0.18 |
| 2026 | 4.10 | 0.18 |
| 2027 | 4.27 | 0.17 |
| 2028 | 4.46 | 0.19 |
| 2029 | 4.62 | 0.16 |
| 2030 | 4.80 | 0.18 |

**Key observations:**
- Annual increments are small (0.15-0.20 AF/yr), reflecting the distance from the wellfield to La Cienega Springs
- Cumulative depletion is growing slowly and approximately linearly
- Total cumulative depletion through 2030 is less than 5 AF -- very small in hydrologic terms

### 9.3 GHB Cell Configuration

Six GHB cells represent La Cienega Springs (see DS-02, Section 6.3):
- Rows 30-32, Columns 12-15, all Layer 1
- Conductance: 100.0 ft^2/day (all cells)
- Head elevation: 5,445-5,449 ft (decreasing southward)

### 9.4 Year Chaining for Table 5

Table 5 uses the prior year's cumulative value to compute the current year's annual increment. This creates a dependency chain:

```
Table 5 for year N requires:
  1. MODFLOW flux output for year N (cumulative cfs from GHB cells)
  2. LA_CIENEGA_CUMULATIVE[N-1] (prior year's cumulative AF)

The cumulative AF for year N is computed from the MODFLOW output,
then the annual increment = cumulative(N) - cumulative(N-1).

After validation, cumulative(N) is manually added to LA_CIENEGA_CUMULATIVE
for use in the following year.
```

---

## 10. Output Products

### 10.1 Table 3: Tributary Stream Depletions

- **Content**: Rio Pojoaque-Nambe and Rio Tesuque depletion impacts (AF/year)
- **Structure per stream**: Residual (Analytical) + Superposition (MODFLOW) = Total Impact
- **Time series**: 1988 through current year (rows extended annually)
- **Historical preservation**: Years 1988 through (year-1) use values from baseline file to ensure exact reproduction
- **File**: `TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx`

### 10.2 Table 4: Rio Grande Depletions Above and Below Otowi

- **Content**: Cell-level and aggregated Rio Grande depletions
- **Above Otowi**: 10 cells aggregated (monthly cfs + annual AF)
- **Below Otowi**: 16 cells aggregated (monthly cfs + annual AF)
- **Total Rio Grande**: Sum of above + below (monthly cfs + annual AF)
- **Buckman cell**: Cell (1,13,11) depletion reported separately
- **Stream summaries**: RIO GRANDE, R POJOAQUE, LC SPRINGS, R TESUQUE, RIV TOTAL
- **Days per month**: Uses non-leap year (365-day) convention for Table 4
- **File**: `TABLE_4_Rio_Grande_{year}.xlsx`

### 10.3 Table 5: La Cienega Springs

- **Content**: Cumulative and annual increment depletion (AF)
- **Monthly detail**: 12 monthly cfs values converted to AF
- **Cumulative**: Running total from 2004 through current year
- **Annual increment**: Current year minus prior year cumulative
- **Uses leap year**: Calendar-accurate days for conversion (unlike Table 4)
- **File**: `TABLE_5_La_Cienega_Springs_{year}.xlsx`

---

## 11. Domain-Specific Constraints

### Physical Bounds

| Parameter | Min | Max | Units | Basis |
|-----------|-----|-----|-------|-------|
| Stream depletion rate | 0.0 | ~1.0 | cfs | Pumping-induced reduction in stream baseflow |
| Pojoaque annual depletion | 0.0 | ~100.0 | AF/yr | Historical range including residuals |
| Tesuque annual depletion | 0.0 | ~80.0 | AF/yr | Historical range including residuals |
| Rio Grande annual depletion | 0.0 | ~500.0 | AF/yr | Largest depletion (closest to wellfield) |
| La Cienega annual increment | 0.0 | ~0.5 | AF/yr | Very small due to distance from wellfield |
| La Cienega cumulative | 0.0 | ~10.0 | AF | Slow accumulation since 2004 |

### Conservation Laws

- **Depletion non-negativity**: Stream depletion from pumping cannot be negative (pumping cannot increase streamflow in a superposition model)
- **Flux consistency**: RIV TOTAL = R POJOAQUE + R TESUQUE + RIO GRANDE (sum of stream components)
- **Above + Below = RIO GRANDE**: Sum of Above Otowi cells + Below Otowi cells should equal the RIO GRANDE stream summary
- **Cumulative monotonicity**: La Cienega cumulative depletion should increase each year (pumping causes ongoing depletion that accumulates)

### Regulatory Context

- Stream depletion values are reported to the New Mexico OSE as part of the annual Buckman Wellfield compliance report
- Depletions to Rio Pojoaque-Nambe and Rio Tesuque affect water rights of Pueblo nations
- Depletions to the Rio Grande affect federal and interstate compact obligations
- La Cienega Springs depletions are tracked as part of the Aamodt Settlement monitoring

---

## 12. Leap Year Handling

The pipeline handles leap years differently for different tables:

| Table | February Days | Total Days | Rationale |
|-------|-------------|------------|-----------|
| Table 3 | Calendar-accurate (28 or 29) | 365 or 366 | Superposition conversion uses actual year |
| Table 4 | 28 (always) | 365 | Validation file convention uses non-leap year |
| Table 5 | Calendar-accurate (28 or 29) | 365 or 366 | La Cienega uses actual year |

This inconsistency is inherited from the original Excel-based workflow and preserved for backward compatibility with validation files.

---

## 13. References

### Publications
- Core, A.A. (F.), 2003, Santa Fe River and Tributaries Stream Depletion Projections: Wright Water Engineers Report.
- Barroll, M.W., and Keyes, E., 2005, La Cienega Springs Depletion Analysis: Technical Memorandum to Santa Fe County.
- McDonald, M.G., and Harbaugh, A.W., 1988, A modular three-dimensional finite-difference ground-water flow model: USGS TWR Book 6, Chapter A1.

### Standards
- USGS Water-Use Conversion Factors (cfs, AF, ft^3)
- New Mexico OSE Stream Depletion Reporting Requirements

### Data Sources
- MODFLOW binary flux files from Step 3 model execution
- Core (2003) PROJECTION.XLS (analytical residual tables)
- Historical Table 5 outputs (La Cienega cumulative values)

---

## 14. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Well production data is the ultimate input to the MODFLOW model |
| DS-02 | MODFLOW model execution produces the binary flux files consumed here |
| IS-03 | Implementation spec for `stream_depletions.py` |
| docs/MODFLOW_CELL_MAPPING.md | Detailed documentation of the three-layer cell identification system |

---

*Document Maintenance:*
- *Next Review:* When Core (2003) residuals are updated, new streams are added, or model geometry changes
- *Change Triggers:* New analytical residual model replacing Core (2003); Otowi gage cell reclassification; La Cienega GHB cell changes; FORTRAN post-processor modification; change in OSE reporting requirements
