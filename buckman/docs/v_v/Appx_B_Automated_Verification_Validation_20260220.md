# Appendix B: Automated Verification and Validation of the Buckman Wellfield Depletion Pipeline

**Prepared for:** New Mexico Office of the State Engineer

**Date:** February 2026

**Analysis Year:** 2025

---

## 1. Introduction

This appendix documents the automated verification and validation (V&V) procedures built into the Python pipeline that computes stream depletion impacts from Buckman Wellfield pumping. These automated checks execute every time the pipeline runs, without manual intervention, and produce a machine-readable record of what was checked and whether it passed.

**Verification** asks: *Did we compute correctly?* It confirms that unit conversions are accurate, that MODFLOW converged, that the numbers in the output tables are internally consistent, and that the code has not introduced arithmetic errors.

**Validation** asks: *Does the model output match physical reality?* It compares pipeline results against independently verified baseline values, checks whether year-over-year changes are physically reasonable, and detects statistical outliers that warrant investigation.

This appendix covers only the automated checks. Manual verification procedures (visual inspection of output tables, comparison to historical reports, expert review of physical reasonableness) are documented separately.

All tolerance values, thresholds, and acceptance criteria referenced in this appendix are defined in configuration files within the pipeline codebase and are reproduced in the summary table at the end of this document (Section 16).

---

## 2. Pipeline Overview

The Buckman Wellfield depletion pipeline converts daily groundwater pumping records into annual stream depletion estimates reported to the New Mexico Office of the State Engineer. The pipeline consists of five steps:

```
Step 1               Step 2               Step 3               Step 4a              Step 4b
Ingest Data    --->   MODFLOW Files  --->  Run MODFLOW96  --->  Post-Process   --->  Depletion Tables
(Python)              (Python)             (MODFLOW96.exe)      (sfmodflx.exe)       (Python)
IN: CSV               IN: .wel             IN: .nam             IN: .flx             IN: CY{YYYY}
OUT: Tables 1,2       OUT: .wel, .nam      OUT: .flx files      OUT: CY{YYYY}        OUT: Tables 3,4,5
```

**Step 1** reads daily pumping data from a CSV file provided by the City of Santa Fe, converts million-gallons-per-day to acre-feet, and produces Tables 1 (historical pumping by well) and 2 (current year monthly pumping).

**Step 2** generates MODFLOW input files. It reads the prior year's well-pumping file (`.wel`), appends the current year's monthly pumping rates, and creates a MODFLOW name file (`.nam`) that points to all required model inputs.

**Step 3** executes MODFLOW96 via Wine (on Linux). MODFLOW96 is the USGS finite-difference groundwater flow model. It solves the groundwater flow equation for each monthly stress period and produces binary flux files (`.flx`) containing cell-by-cell water budgets.

**Step 4a** runs `sfmodflx_2245.exe`, a FORTRAN post-processor that reads the binary flux files and extracts stream depletion values for each reach. This post-processor uses hardcoded cell rectangles to identify which model cells contribute to each stream.

**Step 4b** parses the post-processor output and generates Excel tables: Table 3 (Rio Pojoaque-Nambe and Rio Tesuque cumulative depletions), Table 4 (Rio Grande above and below Otowi Bridge), and Table 5 (La Cienega Springs cumulative impact).

**Year-over-year chaining.** Tables 3 and 5 use a chaining mechanism: when processing year N, years prior to N are copied directly from the prior year's output file rather than recomputed. Only year N and beyond are calculated from the current MODFLOW run. This ensures that historical values, once established by their respective MODFLOW runs, are locked in and cannot drift due to code changes. If no prior-year output exists (first-time run), the pipeline falls back to independently verified baseline values.

---

# Part I: Verification

Verification confirms that the pipeline computes correctly — that formulas are implemented accurately, that units are converted properly, and that the numerical model converged to a stable solution.

## 3. Input Data Quality Validation

Before any computation begins, the pipeline validates the raw daily pumping data received from the City of Santa Fe. These checks run during Step 1 (data ingestion) and prevent bad data from propagating into MODFLOW input files and downstream depletion tables.

**Daily record screening.** Every daily pumping value for all 13 Buckman wells is checked for three categories of invalid data: negative values (physically impossible — a well cannot produce negative flow), blank or NaN entries (missing data), and non-numeric entries (data entry errors). Zero values are treated as valid, since wells are routinely shut down for maintenance. Any flagged value is recorded in a quality flag register that propagates through the monthly aggregation, ensuring that months containing suspect data are marked in the output tables.

**Three-tier daily sum verification.** For each day, the pipeline independently sums the 13 individual well values and compares the result to the Buckman Well Field (BWP) total column provided in the source CSV. Discrepancies are classified into three severity tiers:

- *Tier 1 (noise):* BWP total is nonzero but below 0.0015 MGD. These values fall below the database precision threshold (100-gallon rounding in the City's SCADA system) and are flagged as informational only.
- *Tier 2 (formula error):* All 13 well values are zero but the BWP total exceeds 0.0015 MGD. This indicates a formula error in the source CSV — the total is computing a nonzero value from zero inputs.
- *Tier 3 (rounding):* The absolute difference between the computed sum and the BWP total is compared against two thresholds: differences below 0.001 MGD pass silently, differences between 0.001 and 0.005 MGD are flagged as informational (expected Excel rounding), and differences exceeding 0.005 MGD are flagged as errors requiring CSV review.

**Annual sum verification.** After monthly aggregation, the pipeline sums all 12 monthly totals for each well and compares the result to the annual sum row in the source CSV. The tolerance is 0.01 MG (10,000 gallons). A mismatch indicates either a missing month in the aggregation or a discrepancy in the source data.

## 4. Unit Conversion Accuracy

The pipeline converts between three unit systems: cubic feet per second (cfs, the native unit of the MODFLOW post-processor), acre-feet (AF, the reporting unit for the State Engineer), and cubic feet per second used in MODFLOW well input files. A conversion error at any stage would propagate through all downstream tables.

The core conversion formula is:

```
Acre-feet = cfs x days_in_month x 86,400 seconds/day / 43,560 ft³/acre-foot
```

This formula is implemented in `stream_depletions.py` and is calendar-aware: February uses 29 days in leap years (2024) and 28 days in non-leap years (2025). The pipeline uses Python's `calendar.isleap()` function to determine the correct day count for each year.

**Hand-calculable verification example.** For a constant flow of 1.0 cfs over a 30-day month:

```
1.0 cfs x 30 days x 86,400 s/day = 2,592,000 ft³
2,592,000 ft³ / 43,560 ft³/AF = 59.504 AF
```

The automated test suite includes this exact calculation (and dozens of variants) to confirm the conversion function returns the expected value. A total of 240 automated tests verify that every calculation function in the pipeline executes without error and returns values of the correct type and magnitude.

**Leap year sensitivity.** The difference between using 28 and 29 days for February in a leap year is approximately 2% of February's contribution. For a representative monthly depletion of 0.5 cfs, this amounts to approximately 1.0 AF. The pipeline's leap year handling was verified by running both the 2024 (leap) and 2025 (non-leap) analyses and confirming that February day counts are correct in each case.

## 5. MODFLOW Numerical Integrity

MODFLOW96 solves the groundwater flow equation iteratively using the Strongly Implicit Procedure (SIP). At the end of each stress period, the model computes a volumetric water budget and reports the percent discrepancy between water entering and leaving the model domain.

The pipeline automatically extracts every percent discrepancy value from the MODFLOW listing file (`.lst`) and verifies that the maximum discrepancy across all stress periods is less than 0.1%. A discrepancy exceeding this threshold indicates that the iterative solver did not converge to an acceptable solution, and the model results should not be used for regulatory reporting.

This check is a hard stop: if it fails, the pipeline halts and reports the stress period where convergence was inadequate. For the 2024 baseline run, all stress periods converged with discrepancies well below 0.1%.

## 6. Internal Consistency Checks

Four automated consistency checks verify that data flows correctly through the pipeline without loss, corruption, or arithmetic error.

**Pumping conservation.** The total annual pumping read from the input CSV (via Table 2) must equal the total annual pumping applied in the MODFLOW well file, after unit conversion. The pipeline parses both files independently, converts the well file rates from ft³/s back to acre-feet, and compares the totals. The acceptable difference is 0.1% relative, which accommodates floating-point rounding in the unit conversion. This check catches errors such as a well being omitted from the MODFLOW file, a unit conversion applied twice, or a month being skipped.

**Depletion constraint.** Stream depletion in any year cannot exceed total pumping in that year. This is a physical law: the aquifer cannot lose more water to streams than was extracted by wells. The pipeline computes the annual depletion-to-pumping ratio and verifies it does not exceed 1.0 (with a 0.1% buffer for numerical precision). For the Buckman Wellfield, this ratio typically ranges from 0.07 to 0.11, well below the physical limit.

**Table sum integrity.** Within each output table, row totals must equal the sum of monthly values, and column totals must equal the sum of individual entries. The pipeline checks every summation in Table 2 (CSV format) and, when the openpyxl library is available, in Tables 3-5 (Excel format). The acceptable difference is 0.01 AF, which accommodates display rounding in Excel.

**Missing data detection.** If any cell in the input data or output tables contains NaN (not a number) or is unexpectedly empty, the pipeline fails immediately rather than propagating a silent error. This catches problems such as a corrupted input file, a parsing failure in the post-processor output, or a division by zero in the conversion logic.

## 7. Spreadsheet Cross-Check Formulas

The output Excel files contain embedded formulas that allow an independent reviewer to verify the pipeline's arithmetic without running any Python code. These formulas are computed by Excel (or LibreOffice Calc) when the file is opened, providing a second independent calculation path.

**Table 4 (Rio Grande at Otowi) contains eight cross-check formula rows:**

The first four verify that the CFS totals for above-Otowi and below-Otowi reaches are the correct sums of individual MODFLOW cell values. Two use Excel's SUMIF function to sum all cells labeled "above" or "below" in column R. Two use explicit SUM formulas over the known contiguous cell ranges. Each formula computes the difference between the formula result and the Python-computed total. If the pipeline computed correctly, all eight values display as 0.000000.

The remaining four verify the acre-feet conversion. Each formula multiplies the monthly CFS value by the number of days in that month, by 86,400 seconds per day, and divides by 43,560 cubic feet per acre-foot. The result is compared to the Python-computed AF value. Again, a correct computation produces 0.000000.

**Table 5 (La Cienega Springs) contains three cross-check formula columns:**

Column C ("Annual Change") computes the year-over-year change in cumulative depletion. Column D ("Cumulative Check") sums all annual changes from 2004 through the current row to independently reconstruct the cumulative value. Column E ("Difference") computes the difference between the stated cumulative value (column B) and the reconstructed value (column D). A correct table produces 0.000000 in every row of column E.

These embedded formulas serve as an audit mechanism: any reviewer with Excel can verify the pipeline's arithmetic by simply opening the file and inspecting the cross-check rows and columns.

## 8. Historical Chaining Verification

When the pipeline processes year N, it produces depletion values for all years from the model start (1988 for Tables 3-4, 2004 for Table 5) through the projection horizon (2030). Values for years before N are not recomputed from the current MODFLOW run; instead, they are copied from the prior year's output file. This chaining mechanism ensures that historical values, once established, remain fixed regardless of code changes or reprocessing.

The chaining verification has two components:

**Within-table chaining.** The pipeline reads the prior year's Excel output, extracts historical values, and writes them directly into the current year's table. For the 2025 analysis, years 1988-2024 in Table 3 were copied from the 2024 output, and years 2004-2024 in Table 5 were copied from the 2024 output. Only years 2025-2030 were recomputed from the CY2025 MODFLOW run.

**Cross-model verification.** A separate verification script (`verify_depletion.py`) parses the raw post-processor output from both the CY2024 and CY2025 MODFLOW runs and computes superposition acre-feet for every year from 1988 through 2030. For historical years (1988-2024), the two model runs should produce identical values because the pumping data and model parameters are the same. The script flags any historical year where the absolute difference exceeds 0.001 AF. Differences in years 2025-2030 are expected and reported for informational purposes, since these years incorporate different pumping data.

The output of this verification is an Excel file with side-by-side values and a difference column. Cells exceeding the 0.001 AF threshold are highlighted in yellow. For the 2024-2025 comparison, all historical years agreed within the threshold, confirming that the two MODFLOW runs are consistent for the overlapping period.

## 9. Geometry Validation

The FORTRAN post-processor (`sfmodflx_2245.exe`) uses hardcoded cell rectangles to determine which MODFLOW cells contribute to each stream reach. For La Cienega Springs, the extraction rectangle covers model rows 28-35 and columns 10-20. Only cells within this rectangle are included in the "LC SPRINGS" depletion total.

La Cienega Springs is represented in the MODFLOW model by six General Head Boundary (GHB) cells. The pipeline reads the GHB input file, extracts the (layer, row, column) coordinates of all GHB cells, and verifies that every cell falls within the FORTRAN extraction rectangle.

This check guards against a specific failure mode: if the MODFLOW grid geometry were ever modified such that a La Cienega GHB cell moved outside the extraction rectangle, that cell's flux contribution would be silently excluded from the depletion total, resulting in an underestimate of the spring impact. Because this underestimate would not produce any error message from either MODFLOW or the post-processor, it could go undetected without an explicit geometry check.

The current six GHB cells are located at rows 30-32, columns 12-15 — comfortably within the extraction rectangle (rows 28-35, columns 10-20) with at least a one-cell buffer on all sides. The automated check verifies both the cell coordinates and the buffer margin.

---

# Part II: Validation

Validation confirms that pipeline outputs are physically reasonable and consistent with independently verified reference data.

## 10. 2024 Regression Baseline

The 2024 analysis was the first year fully processed with the automated pipeline. All outputs were manually verified against legacy Excel spreadsheets produced by the prior manual workflow. These verified outputs serve as the regression baseline: any code modification must reproduce the 2024 results within defined tolerances.

The regression test works by re-running the entire pipeline from frozen inputs (the same input CSV and MODFLOW files used for the original 2024 analysis) and comparing every cell in every output table against the verified reference outputs. The comparison uses a hybrid tolerance approach: a cell passes if the absolute difference is within the absolute tolerance, OR if the relative difference is within the relative tolerance. This hybrid approach handles both small values (where a tiny absolute difference is acceptable) and large values (where a small relative difference is acceptable).

The per-table tolerances are:

| Table | Description | Absolute Tolerance | Relative Tolerance |
|-------|-------------|-------------------|-------------------|
| Table 1 | Annual pumping by well | 0.01 AF | 0.1% |
| Table 2 | Monthly pumping by well | 0.01 AF | 0.1% |
| Table 3 | Rio Pojoaque & Rio Tesuque | 0.001 AF | 0.1% |
| Table 4 | Rio Grande above/below Otowi | 0.1 AF | 1% |
| Table 5 | La Cienega Springs cumulative | 0.01 AF | 0.5% |

Before running the regression, the pipeline verifies the integrity of frozen input files by computing SHA-256 cryptographic hashes and comparing them against stored reference hashes. If any input file has been modified since the baseline was established, the regression test fails immediately with a message identifying which file changed. This prevents the baseline comparison from being invalidated by accidental input modifications.

The regression test also enforces strict handling of missing data: any NaN value in the output or any cell that is empty when the reference has a value (or vice versa) causes an immediate failure.

## 11. Cross-Model Depletion Comparison

When processing a new year, the pipeline generates a verification spreadsheet that compares the current MODFLOW run against the prior year's run. This comparison is performed at the raw post-processor output level — before any table formatting, chaining, or rounding — to detect discrepancies at their source.

For the 2025 analysis, the verification script parsed both the CY2024 and CY2025 post-processor output files and computed annual superposition acre-feet for Rio Pojoaque and Rio Tesuque across all years from 1988 through 2030. The comparison applies a 0.001 AF threshold: any historical year (1988-2024) where the two model runs disagree by more than this amount is flagged.

Historical years should agree exactly (within floating-point precision) because the MODFLOW model uses the same grid, parameters, and historical pumping data for both runs. A disagreement would indicate a problem with the MODFLOW run itself (for example, a different version of the executable, a corrupted input file, or a convergence issue in one of the runs).

Years 2025-2030 are expected to differ between the two runs because the CY2025 run incorporates the new 2025 pumping data while the CY2024 run projected those years based on 2024 pumping.

The output is an Excel workbook with year-by-year comparisons, difference columns, and yellow highlighting for any flagged values.

## 12. Historical Bounds and Ballpark Checks

Before running the full test suite (which can take several minutes), the pipeline executes a rapid ballpark check that tests for gross physics violations. This check executes in less than five seconds and uses historical bounds derived from the 2022-2024 analysis period.

**Hard failures** halt the pipeline immediately:

- Negative total pumping (physically impossible — cannot extract negative water)
- Total pumping exceeding three times the historical maximum (4,118.70 AF; the historical range is 866-1,373 AF)
- Negative stream depletion in any reach (physically impossible)
- Non-monotonic cumulative depletion (cumulative impact cannot decrease year-over-year; tolerance of 0.01 AF for floating-point errors)

**Soft flags** allow processing to continue but require human review:

- Total pumping exceeding two times the historical maximum (2,745.80 AF)
- Any metric more than two standard deviations from the historical mean

The ballpark check is designed to catch catastrophic errors early — such as loading the wrong year's input file, a unit conversion that is off by an order of magnitude, or a post-processor that failed silently — before investing time in the full regression test.

## 13. Temporal Consistency

The temporal consistency checks compare the current year's results against year-over-year patterns observed in the 2022-2024 historical period. All temporal checks produce soft flags that require human review; none are hard stops. This reflects the fact that year-over-year changes may be legitimate (a drought year followed by a wet year) and should be reviewed by a hydrogeologist rather than rejected by an algorithm.

**Year-over-year pumping change.** The threshold is 65%, derived from the maximum observed year-over-year change (58.5%, from 2023 to 2024) plus a 10% buffer for measurement uncertainty. A change exceeding this threshold has never been observed in the operational history of the wellfield and warrants investigation.

**Depletion-to-pumping ratio change.** The threshold is 45%, derived from the maximum observed ratio change (36.5%, from 2023 to 2024) plus a 10% buffer. The depletion/pumping ratio varies inversely with pumping intensity, so large changes in pumping naturally produce changes in the ratio. A change exceeding the threshold suggests the model response may be inconsistent with historical behavior.

**Seasonal pattern correlation.** The pipeline computes the Pearson correlation between the current year's normalized monthly pumping profile and the historical average profile. The threshold is r = 0.75. A correlation below this value indicates a potential stress period misalignment — for example, if January data were accidentally labeled as February. A one-month shift in the monthly profile typically produces correlations in the range of 0.5-0.7, while normal year-to-year operational variation produces correlations above 0.85.

**Multi-year envelope.** The pipeline checks whether the current year's values fall within an envelope derived from the historical range. The envelope uses a CV-adjusted buffer: the buffer is the larger of 20% or 1.5 times the coefficient of variation. This approach is used instead of a 95% prediction interval because with only three years of historical data (n=3), the t-distribution multiplier (t_0.025 = 12.71 with df=1) produces intervals so wide as to be uninformative. The CV-adjusted envelope is transparent about data limitations while still providing a defensible bound.

---

# Part III: Quality Assurance Infrastructure

## 14. Test Orchestration and Failure Handling

The pipeline's test suite is orchestrated by `run_all_tests.py`, which executes checks in a defined priority order. If a higher-priority check fails, lower-priority checks are skipped to avoid wasting time on results that cannot be trusted.

The execution order is:

1. **Ballpark check** (less than 5 seconds). Physics violation screening. A hard failure (exit code 3) halts all further testing.

2. **Smoke tests** (approximately 5 seconds). 190 automated tests verify that all Python functions execute without errors, return the correct types, and produce values of the expected magnitude. A failure indicates a code bug.

3. **Edge case and geometry tests** (approximately 2 seconds). 46 tests: 30 verify that the pipeline handles malformed inputs, boundary conditions, and missing data gracefully (negative pumping values, empty CSV files, missing well columns, leap year edge cases); 16 verify MODFLOW grid geometry, including the GHB cell validation described in Section 9.

4. **Conservation tests** (approximately 2 seconds). 4 tests verify the physics-based constraints described in Section 6 (Internal Consistency Checks): budget closure, pumping conservation, depletion constraint, and table sum integrity. These require MODFLOW output files to be present; if files are missing, the tests are skipped rather than failed.

5. **Temporal consistency** (approximately 1 second). The year-over-year pattern checks described in Section 13. These produce soft flags only.

6. **Provenance manifest** (approximately 1 second). Generates the audit trail described in Section 15.

The test suite uses three exit codes: 0 (all hard-stop checks passed; soft flags may exist), 1 (one or more hard-stop checks failed), and 3 (physics violation detected in the ballpark check). A total of 240 automated tests are distributed across 7 test files containing 5,177 lines of test code.

Error messages follow a forensic format designed for debugging: each message reports what failed, where it failed (file path and function), the actual value observed, the expected value or threshold, and a physical interpretation of the discrepancy. This format allows an analyst to diagnose the root cause without re-running the pipeline in a debugger.

## 15. Provenance and Audit Trail

Every pipeline run produces a provenance manifest and a workflow log that together document the complete chain of custody for the analysis.

**Pipeline manifest.** A JSON file recording: (1) the SHA-256 hash of every input file, so any modification can be detected; (2) the git commit hash of the pipeline code, so the exact software version can be recovered; (3) the results of every automated test, with pass/fail status and measured values; (4) a flag register listing any soft flags that require human review; and (5) run metadata including timestamps, machine identification, and Python version.

**Workflow log.** A nine-section document (produced in both Markdown and Microsoft Word formats) summarizing the pipeline execution. Sections include: metadata, executive summary, input file inventory, step-by-step execution results, output file inventory, verification summary, physical interpretation (placing the results in the context of the Rio Grande Compact and tributary stream impacts), assumptions and limitations, and an approval block with signature lines for review.

The provenance manifest answers the question: *Can you prove exactly how these depletion numbers were calculated?* By recording input hashes and the git commit, an analyst can reproduce the exact computation at any future date. By recording test results, the manifest demonstrates that quality checks were applied and passed.

---

## 16. Summary Table: All Automated Tolerances and Thresholds

The following table consolidates every numerical tolerance and threshold used by the automated V&V framework. "Hard" checks halt the pipeline on failure. "Soft" checks produce flags requiring human review.

| Check | Tolerance | Units | Hard/Soft | Source File |
|-------|-----------|-------|-----------|-------------|
| **Verification — Input Data** | | | | |
| Daily data: negative values | 0 | MGD | Hard | step1_ingest_buckman_data.py |
| Daily sum: noise threshold | 0.0015 | MGD | Informational | step1_ingest_buckman_data.py |
| Daily sum: error threshold | 0.005 | MGD | Hard | step1_ingest_buckman_data.py |
| Annual sum per well | 0.01 | MG | Hard | step1_ingest_buckman_data.py |
| **Verification — Computation** | | | | |
| MODFLOW budget closure | 0.1 | % discrepancy | Hard | test_conservation.py |
| Pumping conservation (input = applied) | 0.1 | % relative | Hard | test_conservation.py |
| Depletion cannot exceed pumping | 0.001 | ratio overshoot | Hard | test_conservation.py |
| Table sum integrity | 0.01 | AF | Hard | test_conservation.py |
| Cross-model historical agreement | 0.001 | AF | Hard | verify_depletion.py |
| Cumulative depletion monotonicity | 0.01 | AF | Hard | ballpark_check.py |
| GHB cells within extraction rectangle | exact | cell coordinates | Hard | step4_generate_depletion_tables.py |
| Spreadsheet cross-check formulas | 0.000000 | various | Informational | Tables 4 and 5 (Excel) |
| **Validation — Regression** | | | | |
| Table 1 (annual pumping) | 0.01 AF or 0.1% | hybrid | Hard | tolerances.yaml |
| Table 2 (monthly pumping) | 0.01 AF or 0.1% | hybrid | Hard | tolerances.yaml |
| Table 3 (tributary depletions) | 0.001 AF or 0.1% | hybrid | Hard | tolerances.yaml |
| Table 4 (Rio Grande depletions) | 0.1 AF or 1% | hybrid | Hard | tolerances.yaml |
| Table 5 (La Cienega Springs) | 0.01 AF or 0.5% | hybrid | Hard | tolerances.yaml |
| NaN or unexpected empty cell | zero tolerance | — | Hard | tolerances.yaml |
| **Validation — Physical Bounds** | | | | |
| Total pumping hard maximum | 3x historical max (4,118.70 AF) | AF | Hard | bounds.yaml |
| Negative pumping | 0 | AF | Hard | bounds.yaml |
| Negative depletion | 0 | AF | Hard | bounds.yaml |
| Total pumping soft maximum | 2x historical max (2,745.80 AF) | AF | Soft | bounds.yaml |
| Statistical outlier (2-sigma) | 2.0 | standard deviations | Soft | bounds.yaml |
| **Validation — Temporal** | | | | |
| Year-over-year pumping change | 65 | % | Soft | temporal_consistency.py |
| Year-over-year ratio change | 45 | % | Soft | temporal_consistency.py |
| Seasonal correlation | 0.75 | Pearson r | Soft | temporal_consistency.py |
| Multi-year envelope buffer | max(20%, 1.5 x CV) | fraction | Soft | temporal_consistency.py |

---

## 17. References

Anderson, M.P. and Woessner, W.W., 2015, Applied Groundwater Modeling: Simulation of Flow and Advective Transport, 2nd ed.: Academic Press, 630 p.

ASTM International, 1993 (reapproved 2014), D5490-93: Standard Guide for Comparing Ground-Water Flow Model Simulations to Site-Specific Information: ASTM International, West Conshohocken, PA.

Core, E.P., 2003, Analytical Solution for Stream Depletion Due to Pumping from Buckman Wellfield: Consultant report prepared for the City of Santa Fe.

McDonald, M.G. and Harbaugh, A.W., 1988, A Modular Three-Dimensional Finite-Difference Ground-Water Flow Model: U.S. Geological Survey Techniques of Water-Resources Investigations, book 6, chap. A1, 586 p.
