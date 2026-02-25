# Part I: Manual Validation and Verification

Manual validation and verification procedures occur after the pipeline runs and after the automated procedures described in Parts II--IV are executed. Because this is a new automated workflow and given the importance of confirming results by a hydrologist, the manual V&V procedure is described in this appendix prior to the lengthier description of the automated V&V procedures. Manual V&V was performed on February 25, 2026.

## Summary of Manual V&V Checks

| # | Check | What Was Compared | Result | Status |
|---|-------|-------------------|--------|--------|
| 1 | Input data integrity | Annual MG sums in pipeline output vs. City CSV | Agreed within 0.01 MG | Pass |
| 2 | Unit conversion (MG to AF) | Manual AF conversion vs. Table 2 output | Agreed within 0.01 AF | Pass |
| 3 | Well file spot-check (low value) | Manual cfs conversion for May 2025 Well 1 vs. `.wel` file | Agreed within 0.001 cfs | Pass |
| 4 | Well file spot-check (high value) | Manual cfs conversion for Sept 2025 Well 6 vs. `.wel` file | Agreed within 0.001 cfs | Pass |
| 5 | Well file year-over-year consistency | 2024 and 2025 `.wel` files for overlapping months | Identical for Dec 2024, Sep 2024, May 2013 | Pass |
| 6 | Table 3 chaining verification | 2024 and 2025 depletion values for years 2006--2024 | Identical | Pass |
| 7 | Table 3 output formatting correction | Manual review identified incorrect year range in output | Script corrected; values verified post-fix | Pass |
| 8 | Table 3 regression to 2024 memo | Pipeline Table 3 vs. 2024 memo (Wolaver, 2025) | Match | Pass |
| 9 | Table 4 regression to 2024 memo | Pipeline Table 4 vs. 2024 memo (Wolaver, 2025) | Match | Pass |
| 10 | Table 5 chaining and regression | Pipeline Table 5 vs. 2024 memo (Wolaver, 2025) | Match | Pass |
| 11 | Anomalous value investigation | May 2025 low-pumping flag reviewed with City | Confirmed correct by City of Santa Fe | Pass |
| 12 | Year-over-year change flag | Percentage change flag triggered by May 2025 | Confirmed acceptable per City data | Pass |

## Manual Verification

Manual verification confirms that the pipeline computes correctly at each step --- that input data are read accurately, unit conversions are applied properly, MODFLOW input files are constructed correctly, and output tables faithfully represent the model results.

### 1. Input Data Validation (Step 1)

The raw daily pumping CSV provided by the City of Santa Fe (`Buckman_Well_Prod_2025.csv`) was independently checked using a manual spreadsheet (`Buckman_Well_Prod_2025_BDW_CHECK.xlsx`, a copy of the City's CSV with manual check formulas added).

**Annual sum verification.** The annual sum of daily pumping values in million gallons (MG) for each well was computed manually in the check spreadsheet and compared to the corresponding annual sum produced by Step 1 of the pipeline (`2025_Table_2_output.xlsx`). The two values agreed within 0.01 MG for all wells. This agreement confirms that Step 1 correctly reads and aggregates daily pumping records from the City's CSV.

**Unit conversion verification.** The manual annual sum in MG was converted to acre-feet (AF) using the standard conversion factor:

    1 MG x (1,000,000 gal / 325,851 gal/AF) = 3.0689 AF/MG    (EQN 1)

The manually computed annual AF total (row 374 of the check spreadsheet) matched the corresponding column total in Table 2 within 0.01 AF. Agreement of annual sums by well provides confidence that monthly totals are also correct, because the annual value is the sum of the 12 monthly values.

### 2. MODFLOW Well File Verification (Step 2)

To verify that the pipeline correctly converts monthly pumping data to MODFLOW well-file input rates, two representative months were selected for spot-checking: a low-value month (May 2025, Well 1, total pumping = 0.036 MG) and a high-value month (September 2025, Well 6, total pumping = 13.597 MG). These endpoints bracket the range of monthly pumping values encountered in the 2025 dataset.

The MODFLOW well file (`.wel`) stores pumping rates in cubic feet per second (cfs), not acre-feet. The conversion from monthly MG to cfs is:

    Q (cfs) = V (MG) x 10^6 / (7.48 gal/ft^3) / (D x 86,400 s/day)    (EQN 2)

where D is the number of days in the month. Because each Buckman well is split equally between MODFLOW Layer 1 and Layer 2, the per-layer rate is Q/2.

| Month | Well | MG | Days | Manual cfs (EQN 2) | Per-layer cfs | `.wel` file value | Agreement |
|-------|------|----|------|---------------------|---------------|-------------------|-----------|
| May 2025 | Well 1 | 0.036 | 31 | 0.00180 | 0.000898 | -0.00090 | Within 0.001 cfs |
| Sep 2025 | Well 6 | 13.597 | 30 | 0.7013 | 0.35065 | -0.35063 | Within 0.001 cfs |

The negative sign in the `.wel` file denotes extraction (MODFLOW convention). Both spot-checks confirm that the pipeline correctly converts monthly pumping from MG to cfs and splits the rate between layers.

**Year-over-year well file consistency.** The 2024 and 2025 `.wel` files were compared for months that should be identical in both files (because the 2025 file appends a new year to the 2024 file without modifying historical entries). December 2024 and September 2024 pumping rates were identical in both files, as was a historical check of May 2013. This confirms that the pipeline's well-file update mechanism for year N+1 correctly preserves all prior-year entries.

### 3. Post-Processor and Table 3 Verification (Steps 3--4)

Table 3 reports cumulative stream depletions for Rio Pojoaque--Nambe and Rio Tesuque reaches. These values originate from MODFLOW96 binary flux files (`.flx`), which are processed by the FORTRAN post-processor (`sfmodflx_2245.exe`) to extract stream depletion by reach, and then parsed by the Python pipeline (`step4_generate_depletion_tables.py`) to produce the final table.

**Cross-year consistency of post-processor output.** The raw post-processor output from the CY2024 and CY2025 MODFLOW runs was compared for overlapping historical years. Rio Tesuque depletion values for 2023 and 2024 were identical between the two runs. La Cienega Springs values for the same years were also identical. This agreement confirms that the chain from CSV input through MODFLOW through the post-processor is functioning correctly and that identical inputs produce identical outputs.

**Output formatting correction.** Manual review of Table 3 identified that `step4_generate_depletion_tables.py` was writing raw superposition depletion results for all years 1988--2030, rather than writing only year N+1 results (2025--2030) and chaining historical values from the prior year's output. This distinction matters because the superposition MODFLOW model (Barroll and Keyes, 2005) was published in 2005, and superposition results for years prior to 2005 are not physically meaningful without the chaining mechanism. The script was corrected to write only year N+1 superposition depletion results and to chain all prior-year values from the previous output file. After the correction, the 2024 and 2025 depletion results for years 2006 through 2024 were compared and confirmed identical, demonstrating that chaining of prior-year values is working correctly. This finding illustrates the value of manual V&V: the formatting issue would not have been caught by automated tests that check only numerical accuracy.

**Regression to 2024 memo.** Table 3 values for years 1988--2024 produced by the pipeline match the corresponding values in the 2024 depletion memo (Wolaver, 2025), confirming that the pipeline reproduces previously verified results.

### 4. Table 4 Verification: Rio Grande Depletions Above and Below Otowi (Step 4)

Table 4 reports annual stream depletion on the Rio Grande, disaggregated into reaches above and below the Otowi gage. The MODFLOW grid cells representing these reaches are hardcoded in `step4_generate_depletion_tables.py` as the `ABOVE_OTOWI_CELLS` and `BELOW_OTOWI_CELLS` dictionaries.

**Regression to 2024 memo.** Table 4 values produced by the pipeline for the 2024 analysis year match the 2024 depletion memo (Wolaver, 2025). This comparison provides additional confidence in the year N+1 processing, because the pipeline's Table 4 output for 2024 was generated using 2023 input data (the CY2024 MODFLOW run).

### 5. Table 5 Verification: La Cienega Springs (Step 4)

Table 5 reports estimated annual impacts on La Cienega Springs as cumulative depletion totals. Like Table 3, Table 5 uses a chaining mechanism: year N results serve as the starting point, and only year N+1 through 2030 annual depletions are computed from the current MODFLOW run.

**Regression to 2024 memo.** Table 5 values produced by the pipeline match the corresponding values in the 2024 depletion memo (Wolaver, 2025), confirming that both the chaining mechanism and the spring-depletion calculation are functioning correctly.

## Manual Validation

Manual validation confirms that pipeline outputs are physically reasonable and consistent with independent data sources.

### 6. 2024 Regression Baseline

All five output tables (Tables 1--5) produced by the pipeline for the 2024 analysis year were compared to the verified 2024 depletion memo (Wolaver, 2025). Tables 1 and 2 (pumping summaries) agreed within 0.01 AF, which is attributable to minor rounding differences between Excel and Python (XLSX vs. Python floating-point representation). Tables 3, 4, and 5 (depletion tables) matched the 2024 memo values. This regression confirms that the pipeline reproduces the complete set of previously verified results.

### 7. Anomalous Value Investigation and City Follow-Up

After running the full pipeline for the 2025 analysis year (using the execution plan documented in `.claude/plans/P_FULL_PIPELINE_2024_2025_PLAN.md`, with results recorded in `.claude/plans/P_FULL_PIPELINE_2024_2025_OUTPUT.md`), the automated pipeline flagged two items requiring human review:

**May 2025 low-pumping anomaly.** The historical bounds check flagged May 2025 total pumping as anomalously low compared to the 2022--2024 historical range. This flag was investigated by contacting the City of Santa Fe to verify the source data. The City confirmed that the May 2025 pumping values in the CSV are correct and reflect actual operational conditions during that month.

**Year-over-year percentage change flag.** The temporal consistency check flagged a year-over-year percentage change attributable to the low May 2025 pumping. Based on the City's confirmation that the underlying data are correct, this flag was reviewed and determined to be acceptable --- the percentage change reflects a genuine operational variation rather than a data error.

Both flags were resolved through direct communication with the data provider. This follow-up demonstrates the intended interaction between the automated flagging system and manual expert review: the pipeline identifies values that fall outside historical patterns, and the hydrologist investigates whether the anomaly reflects a data error or a legitimate operational change.
