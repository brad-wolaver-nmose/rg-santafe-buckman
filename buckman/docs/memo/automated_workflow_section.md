## AUTOMATED WORKFLOW: BUCKMAN WELL FIELD DEPLETION PIPELINE CALCULATIONS

New for 2025, the evaluation was conducted using an automated data processing
pipeline executed in Python and FORTRAN, replacing the prior manual Excel-based
workflow. The pipeline ingests daily pumping records for the 13 Buckman wells,
runs the MODFLOW-96 groundwater flow model, and generates the depletion tables
(Tables 1 through 5) used for compliance reporting. The pipeline was subjected to
rigorous verification and validation (V&V) testing as documented in Appendix A.
All source code, specifications, and test results are version-controlled on
GitHub at
<https://github.com/brad-wolaver-nmose/santafe-buckman/tree/master/buckman>.

The pipeline consists of five sequential steps:

- **Step 1 — Ingest Pumping Data.** Daily pumping records (365 days for 13 wells)
  are read from the City of Santa Fe CSV file (`Buckman_Well_Prod_2025.csv`).
  Volumes reported in million gallons per day (MGD) are converted to acre-feet
  (AF) using the USGS conversion factor 1 MG = 3.06889 AF. The step produces
  Table 1 (historical annual pumping by well) and Table 2 (monthly pumping
  breakdown). *(Python)*

- **Step 2 — Generate MODFLOW Input Files.** The cumulative well (`.wel`) file is
  extended to include the current reporting year, maintaining the continuous
  pumping record from 1988 through 2025. A MODFLOW name (`.nam`) file and 10
  baseline model files are assembled into the run directory. *(Python)*

- **Step 3 — Run MODFLOW-96 Groundwater Flow Model.** The MODFLOW-96 executable
  (`modflow96.exe`) solves the groundwater flow equations and produces binary flux
  (`.flx`) files containing cell-by-cell flow budgets. *(MODFLOW-96)*

- **Step 4 — Run Stream Depletion Post-Processor.** The FORTRAN post-processor
  `sfmodflx_2245.exe` reads the binary flux files and extracts stream depletions
  by reach, writing the results to a calendar-year summary file (`CY2025`).
  *(sfmodflx_2245)*

- **Step 5 — Generate Depletion Tables.** The calendar-year summary is parsed to
  produce Tables 3, 4, and 5. Pre-1988 analytical residuals from Core (2003) are
  applied to each reach. Stream depletion flows in cubic feet per second (cfs) are
  converted to acre-feet using the relation cfs × days × 86,400 / 43,560 = AF.
  The five stream reaches reported are Rio Pojoaque, Rio Tesuque, Rio Grande above
  Otowi Bridge, Rio Grande below Otowi Bridge, and La Cienega Springs. Final
  tables are written to Excel (`.xlsx`) format. *(Python)*

Figure X shows the pipeline workflow from raw pumping data through final
depletion tables.

Input data for the 2025 analysis:

- Daily pumping CSV from the City of Santa Fe (`Buckman_Well_Prod_2025.csv`) —
  365 daily records for 13 Buckman wells
- Baseline MODFLOW model files calibrated through 2023

The following items are also maintained on the GitHub repository:

1. **Specification Suite** — After-the-fact documentation of the pipeline design
   and verification procedures, created February 20 and 23, 2026 using Claude
   Code v2.0.61 / Opus 4.5, and subsequently manually edited for accuracy and
   completeness.

2. **`requirements.txt`** — Python package dependencies and version pins used to
   run the pipeline.
