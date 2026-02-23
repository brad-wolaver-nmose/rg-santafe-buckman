# DS-02: MODFLOW96 Santa Fe Local-Scale Model

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Draft
**Author:** Claude Code (Anthropic) + Brad Wolaver (NMOSE)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Purpose & Scope

This specification documents the MODFLOW96 groundwater flow model used to simulate Buckman Wellfield pumping effects on streams and springs in the Santa Fe area. The model is a local-scale, two-layer finite-difference representation of the Santa Fe Group aquifer system. Each year, monthly pumping data from Table 2 (see DS-01) is converted to MODFLOW well package rates, the model is executed, and binary flux outputs are passed to a FORTRAN post-processor for stream depletion calculations (see DS-03). This is the computational engine at the center of the Buckman depletion compliance pipeline.

**Critical distinction**: This pipeline uses the original **MODFLOW96** executable (1996 release), not MODFLOW-2005, MODFLOW-6, or FloPy. The model was built in the early 2000s and has been maintained as a frozen configuration with annual well-package updates only. All file formats, solver settings, and package structures follow MODFLOW96 conventions.

---

## 2. Scientific Basis

### 2.1 Governing Equations

MODFLOW solves the three-dimensional groundwater flow equation:

```
d/dx(Kxx * dh/dx) + d/dy(Kyy * dh/dy) + d/dz(Kzz * dh/dz) + W = Ss * dh/dt

Where:
  Kxx, Kyy, Kzz = hydraulic conductivity along x, y, z axes [L/T]
  h              = hydraulic head [L]
  W              = volumetric flux per unit volume (sources/sinks) [1/T]
  Ss             = specific storage [1/L]
  t              = time [T]
```

For the Buckman model, this is discretized on a finite-difference grid and solved with the Strongly Implicit Procedure (SIP) iterative solver.

### 2.2 Key Equations -- Pumping Rate Conversion

Well pumping is converted from acre-feet per month (from Table 2) to cubic feet per second (MODFLOW internal units):

```
rate_ft3s = -(AF / N_layers) * 43,560 ft^3/AF / (days_in_month * 86,400 s/day)

Where:
  AF             = monthly pumping in acre-feet (from Table 2)
  N_layers       = 2 (pumping split equally between Layer 1 and Layer 2)
  43,560         = ft^3 per acre-foot
  days_in_month  = calendar days in the month (28-31)
  86,400         = seconds per day
  Negative sign  = MODFLOW convention for extraction (pumping OUT of aquifer)
```

### 2.3 Worked Example

**Convert Well 1 January 2024 pumping (16.887963 AF) to MODFLOW rate:**

```
Step 1: Split between layers
  AF_per_layer = 16.887963 / 2 = 8.443982 AF

Step 2: Convert to ft^3
  volume_ft3 = 8.443982 * 43,560 = 367,771.4 ft^3

Step 3: Convert to rate (ft^3/s)
  seconds_in_jan = 31 * 86,400 = 2,678,400 s
  rate = 367,771.4 / 2,678,400 = 0.13730 ft^3/s

Step 4: Apply sign convention
  MODFLOW_rate = -0.13730 ft^3/s

Each layer receives -0.13730 ft^3/s for January 2024.
```

### 2.4 Boundary Condition Physics

**River (RIV) Package -- Tributaries:**

```
Q_riv = C_riv * (h - h_riv)    when h > R_bot
Q_riv = C_riv * (R_bot - h_riv) when h <= R_bot

Where:
  Q_riv  = flux between aquifer and river [L^3/T]
  C_riv  = riverbed conductance [L^2/T]
  h      = aquifer head in the cell [L]
  h_riv  = river stage [L]
  R_bot  = riverbed bottom elevation [L]
```

**General Head Boundary (GHB) Package -- La Cienega Springs:**

```
Q_ghb = C_ghb * (h - h_ghb)

Where:
  Q_ghb  = flux between aquifer and boundary [L^3/T]
  C_ghb  = boundary conductance [L^2/T]
  h      = aquifer head in the cell [L]
  h_ghb  = specified head at boundary [L]
```

Positive flux indicates reduced spring discharge (depletion from pumping).

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | Pumping is constant throughout each month (steady-state stress periods) | Monthly-average pumping rates are sufficient for annual depletion reporting; daily transient effects average out | Underestimates peak depletion effects during high-pumping days | Acceptable for annual compliance; daily transient model would add complexity without regulatory benefit |
| 2 | Pumping is split equally between Layer 1 and Layer 2 | Well screens span both layers in the model; equal split is a simplification | Actual drawdown distribution may differ from modeled | Long-standing model convention; changing requires re-calibration |
| 3 | Model grid and boundary conditions are static (unchanged since 2003) | Only the well package is updated annually; all other packages use frozen 2003 calibration | Geological or hydrological changes not captured | Low risk for compliance-scale depletion estimates |
| 4 | MODFLOW96 solver convergence is adequate | SIP solver converges for the stress magnitudes typical of Buckman pumping | Non-convergence would produce invalid heads and fluxes | Listing file (.lst) checked for convergence warnings |
| 5 | CRLF line endings are required | MODFLOW96 is a DOS/Windows executable; expects Windows text format | Wrong line endings could cause parsing errors | All generated files use `\r\n` explicitly |
| 6 | Binary flux files (.flx) are correctly formatted for sfmodflx_2245.exe | The FORTRAN post-processor reads MODFLOW binary output | Format mismatch would produce wrong depletion values or crashes | Validated against historical results |
| 7 | Wine on Linux/WSL executes MODFLOW96 identically to native Windows | Binary is run via `wine modflow96.exe` on Linux/WSL environments | Floating-point differences could affect convergence | Results validated against native Windows runs |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| Table 2 CSV | Monthly pumping by well in AF (`{year}_Table_2_output.csv`) | Output from Step 1 (DS-01) | Annually | Validated in Step 1 before use |
| 2023 baseline files | Static MODFLOW input files (BCF, BAS, GHB, RIV, OC, SIP) | `input/modflow/2023/` directory | Never (frozen calibration) | Checksummed at pipeline deployment |
| Prior year WEL file | Well package from previous year's run | `output/modflow/{year-1}/thruCY2165_{year-1}.wel` | Annually (chained from prior run) | Structure validated during parsing |
| MODFLOW96.exe | Original 1996 MODFLOW executable | `input/modflow/2023/modflow96.exe` | Never (frozen executable) | Binary checksum |

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| ACRE_FT_TO_FT3 | 43,560 | ft^3/AF | 1 acre = 43,560 ft^2; 1 AF = 1 acre * 1 ft | Standard |
| SECONDS_PER_DAY | 86,400 | s/day | 24 * 60 * 60 | Standard |
| NUM_LAYERS | 2 | dimensionless | Model has 2 aquifer layers; pumping split equally | Model design (Core 2003) |
| WELLS_PER_MONTH | 26 | entries | 13 wells * 2 layers | Model structure |
| LINES_PER_MONTH | 27 | lines | 1 header + 26 well entries | WEL file format |
| BASELINE_YEAR | 2024 | year | First year using original 2023 input files | Pipeline convention |

### Dimensional Analysis -- AF to ft^3/s

```
AF --> ft^3/s (per layer)

rate = (AF / N_layers) * (43,560 ft^3/AF) / (days * 86,400 s/day)

Cancel units:
  [AF] * [ft^3/AF] / [day * s/day]
= [ft^3] / [s]
= ft^3/s

Example: 16.887963 AF, January (31 days), 2 layers
  = (16.887963/2) * 43560 / (31 * 86400)
  = 8.443982 * 43560 / 2678400
  = 367771.4 / 2678400
  = 0.13730 ft^3/s

Apply negative sign: -0.13730 ft^3/s (MODFLOW extraction convention)
```

---

## 6. Model Grid Specification

### 6.1 Grid Dimensions

```
Rows:    35
Columns: 25
Layers:  2

Total cells: 35 * 25 * 2 = 1,750
```

> **Note:** The Buckman Wellfield wells occupy rows 13-20, columns 11-16 within the
> active wellfield area. However, the full model domain extends to at least row 35
> to accommodate GHB (General Head Boundary) cells representing La Cienega Springs
> at rows 30-32, and the FORTRAN post-processor GHB extraction rectangle spans
> rows 28-35, columns 10-20. The RIV (River) package cells span rows 9-17,
> columns 14-25. Rio Grande cells extend from row 1 (Above Otowi) through row 23
> (Below Otowi). Not all cells in the 35x25 grid are necessarily active; inactive
> cells are defined in the BAS (Basic) package boundary array.

### 6.2 Well Locations (WELL_GRID_MAP)

Each well occupies two cells (Layer 1 and Layer 2) at the same row/column:

| Well Name | Well # | Row | Column | Notes |
|-----------|--------|-----|--------|-------|
| BUCKMAN 1 | 1 | 13 | 11 | Co-located with Wells 7, 8 |
| BUCKMAN 2 | 2 | 14 | 11 | Co-located with Wells 3A, 4 |
| BUCKMAN 3A | 3 | 14 | 11 | Co-located with Wells 2, 4 |
| BUCKMAN 4 | 4 | 14 | 11 | Co-located with Wells 2, 3A |
| BUCKMAN 5 | 5 | 15 | 12 | |
| BUCKMAN 6 | 6 | 14 | 12 | Co-located with Well 9 |
| BUCKMAN 7 | 7 | 13 | 11 | Co-located with Wells 1, 8 |
| BUCKMAN 8 | 8 | 13 | 11 | Co-located with Wells 1, 7 |
| BUCKMAN 9 | 9 | 14 | 12 | Co-located with Well 6 |
| BUCKMAN 10 | 10 | 17 | 13 | |
| BUCKMAN 11 | 11 | 19 | 14 | |
| BUCKMAN 12 | 12 | 19 | 15 | |
| BUCKMAN 13 | 13 | 20 | 16 | |

**Note on co-located wells:** Multiple wells in the same grid cell is a consequence of model resolution. The 35x25 grid represents the regional aquifer at a scale where some closely-spaced Buckman wells fall within the same cell. Pumping rates are additive within each cell.

### 6.3 Boundary Condition Cells

**River (RIV) Package -- Tributaries:**
- Spatial extent: Rows 9-17, Columns 14-25
- Streams represented: Rio Pojoaque, Rio Tesuque, Rio Grande
- Stream assignment determined by FORTRAN post-processor (see DS-03)

**General Head Boundary (GHB) Package -- La Cienega Springs:**
- 6 cells representing spring discharge zones:

| Cell # | Layer | Row | Column | Head (ft) | Conductance (ft^2/day) |
|--------|-------|-----|--------|-----------|----------------------|
| 1 | 1 | 30 | 14 | 5449.0 | 100.0 |
| 2 | 1 | 31 | 12 | 5447.0 | 100.0 |
| 3 | 1 | 31 | 14 | 5447.0 | 100.0 |
| 4 | 1 | 31 | 15 | 5447.0 | 100.0 |
| 5 | 1 | 32 | 13 | 5445.0 | 100.0 |
| 6 | 1 | 32 | 12 | 5445.0 | 100.0 |

Spatial extent: Rows 30-32, Columns 12-15, all in Layer 1.

---

## 7. Stress Period Structure

### 7.1 Monthly Stress Periods

The model uses 12 stress periods per year, one for each calendar month. Each stress period has a constant pumping rate for all wells.

Within the `.wel` file, each month is structured as:

```
        26                                    <-- Header: 26 well entries follow
         1        13        11  -0.13730  BUCKMAN 1 JAN 2024    <-- Layer 1
         2        13        11  -0.13730  BUCKMAN 1 JAN 2024    <-- Layer 2
         1        14        11  -0.31553  BUCKMAN 2 JAN 2024    <-- Layer 1
         2        14        11  -0.31553  BUCKMAN 2 JAN 2024    <-- Layer 2
         ...
         1        20        16  -0.00000  BUCKMAN 13 JAN 2024   <-- Layer 1
         2        20        16  -0.00000  BUCKMAN 13 JAN 2024   <-- Layer 2
```

**Entry format:** `{layer:10d}{row:10d}{col:10d}  {rate:8.5f}  {well_name} {month} {year}`

### 7.2 Annual Structure

- 12 months per year
- 27 lines per month (1 header + 26 entries)
- 324 lines per year (12 * 27)
- Wells ordered 1-13; each well has Layer 1 entry followed by Layer 2

### 7.3 Year Chaining

The `.wel` file is cumulative, containing data from 1988 through the current year plus projections through 2165. Each year, the target year's 324 lines are replaced with actual pumping data:

```
thruCY2165.wel structure:
  [Lines for 1988-{year-1}]   <-- Historical data (preserved from prior runs)
  [324 lines for {year}]      <-- Updated with actual pumping from Table 2
  [Lines for {year+1}-2165]   <-- Projection data (preserved from prior runs)
```

For the baseline year (2024), input comes from `input/modflow/2023/thruCY2165.wel`.
For subsequent years, input comes from `output/modflow/{year-1}/thruCY2165_{year-1}.wel`.

### 7.4 Zero Pumping Convention

When a well has zero pumping for a month, the rate is formatted as `-0.00000` (negative zero with 5 decimal places) to match the validation file format and maintain the MODFLOW sign convention.

---

## 8. Model Execution

### 8.1 Baseline Files

Ten files are copied from `input/modflow/2023/` to `output/modflow/{year}/` before each run:

| File | Package | Purpose |
|------|---------|---------|
| `modflow96.exe` | Executable | MODFLOW96 solver |
| `sflcs.bcf` | Block-Centered Flow | Hydraulic properties (K, Ss, layer types) |
| `sflcs.sip` | SIP Solver | Solver parameters (convergence criteria, iterations) |
| `thruCY2165.bas` | Basic | Grid dimensions, boundary array, initial heads |
| `thruCY2165.ghb` | General Head Boundary | La Cienega Springs cells |
| `thruCY2165.oc` | Output Control | What to save and when |
| `thruCY2165.riv` | River | Tributary stream cells |
| `sfmodflx_2245.exe` | Post-processor | FORTRAN depletion calculator |
| `verify_modflow_run.py` | Verification | Output validation script |
| `verify_depletion.py` | Verification | Depletion validation script |

### 8.2 NAM File (Name File)

The `.nam` file tells MODFLOW96 which packages and files to use:

```
# File Type      Unit File Name
LIST            23    CY{year}.lst
BAS             21    thruCY2165.bas
BCF             11    sflcs.bcf
OC              10    thruCY2165.oc
RIV             14    thruCY2165.riv
GHB             15    thruCY2165.ghb
SIP             17    sflcs.sip
WEL             12    thruCY2165_{year}.wel
DATA(BINARY)    24    CY{year}_riv.flx
DATA(BINARY)    34    CY{year}_ghb.flx
```

**Year-specific files:** `.lst` (listing), `.wel` (wells), `_riv.flx` and `_ghb.flx` (binary flux outputs).
**Static files:** `.bas`, `.bcf`, `.oc`, `.riv`, `.ghb`, `.sip` (unchanged between years).

### 8.3 Execution Environment

- **Platform**: Windows executable run via Wine on Linux/WSL
- **Command**: `wine modflow96.exe < CY{year}.nam`
- **Runtime**: Approximately 30-45 minutes for full simulation (1988-2165)
- **Output**: `.lst` listing file + binary flux files (`_riv.flx`, `_ghb.flx`)

### 8.4 Model Outputs

| Output File | Format | Size | Content |
|-------------|--------|------|---------|
| `CY{year}.lst` | Text | ~50 MB | Listing file with convergence info, water budget |
| `CY{year}_riv.flx` | Binary | ~31 MB | River package cell-by-cell flux for all stress periods |
| `CY{year}_ghb.flx` | Binary | ~31 MB | GHB package cell-by-cell flux for all stress periods |

The binary `.flx` files are read by the FORTRAN post-processor (`sfmodflx_2245.exe`) to extract stream depletions (see DS-03).

---

## 9. Domain-Specific Constraints

### Physical Bounds

| Parameter | Min | Max | Units | Basis |
|-----------|-----|-----|-------|-------|
| Well pumping rate (per layer) | -10.0 | 0.0 | ft^3/s | Negative = extraction; magnitude limited by pump capacity |
| Days in month | 28 | 31 | days | Calendar |
| Stress periods per year | 12 | 12 | count | Monthly time steps |
| Well entries per stress period | 26 | 26 | count | 13 wells * 2 layers |
| GHB head values | 5445.0 | 5449.0 | ft | La Cienega Springs elevation range |
| GHB conductance | 100.0 | 100.0 | ft^2/day | Calibrated value (all cells identical) |

### Conservation Laws

- **Water budget**: MODFLOW internally enforces mass balance. The listing file reports total inflow, total outflow, and percent discrepancy for each stress period. Discrepancy > 1% indicates convergence problems.
- **Flux sign convention**: Positive flux = flow INTO aquifer; Negative flux = flow OUT of aquifer (pumping).

### File Format Constraints

- **Line endings**: CRLF (`\r\n`) required for Windows/MODFLOW96 compatibility
- **Column alignment**: Well entry fields must be exactly formatted (`{layer:10d}{row:10d}{col:10d}`) for MODFLOW96's fixed-format reader
- **Rate precision**: 5 decimal places (`{rate:8.5f}`) matching historical file format

---

## 10. References

### Publications
- McDonald, M.G., and Harbaugh, A.W., 1988, A modular three-dimensional finite-difference ground-water flow model: U.S. Geological Survey Techniques of Water-Resources Investigations, Book 6, Chapter A1, 586 p.
- Core, F., 2003, Santa Fe River and Tributaries Stream Depletion Projections: Wright Water Engineers Report.

### Standards
- USGS MODFLOW-96, Open-File Report 96-485

### Data Sources
- City of Santa Fe, Buckman Wellfield pumping records (via DS-01 ingestion)
- NMOSE, well permit records (RG-20516-S series)

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Table 2 output provides monthly AF values that become MODFLOW well rates |
| DS-03 | MODFLOW binary flux outputs are input to stream depletion analysis |
| IS-02 | Implementation spec for `step2_update_modflow.py` |

---

*Document Maintenance:*
- *Next Review:* If model grid changes, solver is upgraded, or additional wells are drilled
- *Change Triggers:* New well added to WELL_GRID_MAP; model re-calibration; MODFLOW version upgrade; change in layer structure
