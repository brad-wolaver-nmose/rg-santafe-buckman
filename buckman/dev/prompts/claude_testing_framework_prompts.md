# Claude Code Prompts — Buckman Red Team Testing Framework

## How to Use This File

These are sequential prompts for Claude Code. Use them in order.
- **Prompt 1** goes into Planning Mode (use `--plan` flag or shift+tab to plan mode)
- **Prompts 2–8** are implementation prompts, one per layer, issued after you review and approve each step  (note: P2.5 is inserted between P2 and P3)
- Drop the `claude_code_handoff_prompt.md` file into your project root BEFORE starting
- Each prompt assumes Claude Code has memory of the prior conversation in the same session

---

## PROMPT 1: Planning Mode — Exploration & Understanding

```
Read the file TESTING_FRAMEWORK.md in this project root. It contains a comprehensive adversarial testing framework for this Buckman wellfield pipeline.

Before writing ANY code, I need you to execute the exploration steps described in that document. Specifically:

1. Map the full directory structure of this project. List every file and folder.

2. Read the main Python pipeline script(s) end to end. For each script, summarize step by step:
   - What input files it reads and their formats
   - How it constructs or modifies MODFLOW input files
   - How it calls the MODFLOW96 executable (what command, what arguments)
   - How it calls the Fortran post-processor (what command, what it reads/writes)
   - How the 5 report Excel tables are generated from the model/post-processor output
   - Every hand-off point where data transforms between formats

3. Identify ANY existing validation, testing, or error-checking in the code — assert statements, try/except blocks, if-checks on outputs, logging, print statements that verify values, separate test scripts, anything. Document exactly what is currently being checked and what is not.

4. Find the 2024 independent validation data (should be an xlsx or csv file). Describe its structure: what columns, what rows, what values, what units, what precision.  Note that reports from prior years (2022, 2023, 2024) are located in docs/prior_year_reports.  You have data from 2024 report in existing validation data for 2024; you can read 2023 and 2024 reports to understand annual pumping (Table 2 and Table 1); Tables 3, 4, and 5 are created using ouput from MODFLOW96 and stream depletion fortran executable.

5. Look for any historical pumping data, archived model runs, or multi-year output files that could support temporal consistency checks (Layer 2 in the framework).

6. Read the MODFLOW96 listing file from the most recent run. Show me the exact format of the volumetric budget summary section — I need to see the actual text so we know how to parse it for Layer 1.

7. Read the Fortran post-processor output file(s). Show me the exact format — headers, columns, delimiters, units.

Present your findings as a structured summary. DO NOT write any test code yet. I need to confirm your understanding is correct before we build anything.
```

---

## PROMPT 2: Confirm Understanding, Then Start Layer 5

> **Before issuing this prompt:** Review Claude Code's exploration summary from Prompt 1. Correct any misunderstandings. Then proceed.

```
Your understanding of the pipeline looks mostly correct — here are corrections:
You're missing calculation of stream depletions using sfmodflx_2245.exe (fortran); this should be between Step 3 and Step 4 here:
| step3_run_modflow.sh | 5.1 KB | 5,121 bytes | ✅ Match |
| step4_generate_depletion_tables.py | 38 KB | 38,066 bytes | ✅ Match |


Now implement Layer 5: the 2024 Regression Harness. This is the single highest-value test. Here's what I need:

1. Create a directory structure:
   validation/
   └── 2024/
       ├── inputs/          # frozen copies of 2024 raw input files
       ├── expected_outputs/ # the 2024 validation spreadsheet(s)
       └── tolerances.yaml  # acceptance criteria for each compared value

2. Copy the 2024 input files into validation/2024/inputs/. Compute SHA-256 hashes of each file and store them in a hashes.json file in that directory.

3. Copy or link the 2024 validation spreadsheet into validation/2024/expected_outputs/.

4. Create tolerances.yaml with reasonable starting tolerances for each value that gets compared. Use absolute tolerance where values are small, relative tolerance (e.g., 1%) where values are large. Flag any values where you're unsure of appropriate tolerance so I can set them.

5. Create run_regression_2024.py — a standalone script that:
   a. Verifies input file hashes match (catches accidental edits to frozen data)
   b. Runs the full pipeline on the 2024 inputs (calling the same code path the production pipeline uses)
   c. Reads the pipeline's output Excel tables
   d. Reads the expected output from the validation spreadsheet
   e. Compares every value cell-by-cell against tolerances
   f. Prints a clear PASS/FAIL report with specific detail on any failures (which table, which cell, expected vs actual, tolerance)
   g. Returns exit code 0 for pass, 1 for fail

This script must be runnable with ONE command: python run_regression_2024.py
It must work for someone who has never seen the pipeline code.
Include detailed comments explaining every step per my coding preferences.

Start with step 1-4 (the data setup), show me the structure, then build the regression runner.
```

 ## PROMPT 2.5: Historical Data Archive & Ballpark Validation

  > **Before issuing this prompt:** Ensure P2 (2024 Regression Harness) is complete. See `.claude/plans/P2.5_VERIFICATION_PLAN.md` for detailed
  implementation spec.

  Layer 5 regression harness is in place. Now create the historical data archive
  that supports temporal consistency checks (Layer 2) and provides fast ballpark
  validation.

  1. Create directory structure:
  validation/
  └── historical/
  ├── extraction_log.md
  ├── raw_extractions/
  ├── Table_1_historical.xlsx  (2022, 2023, 2024)
  ├── Table_2_historical.xlsx
  ├── Table_3_historical.xlsx
  ├── Table_4_historical.xlsx
  ├── Table_5_historical.xlsx
  ├── bounds.yaml
  └── hashes.json
  2. Extract Tables 1-5 data from PDF reports in docs/reports_prior_year/:
    - Memo_bkmanISCWRD_2022_ANALYSIS.pdf (2022)
    - MSC_2024_001_Buckman Well Field_2023_ANALYSIS.pdf (2023)
    - Use 2024 data already in validation/2024/expected_outputs/
  3. Create consolidated historical Excel files with all years (2022-2024).
  4. Create bounds.yaml with:
    - Summary statistics (min, max, mean, std) for each metric
    - Raw time_series values for P5 regression fitting
    - Mean monthly profile for seasonal validation
    - Depletion ratios by reach
  5. Create ballpark_check.py that runs in <5 seconds and checks:
    - Total pumping within historical envelope
    - Cumulative depletions monotonically increasing
    - Depletion/pumping ratios within bounds
    - Monthly profile correlation

  This runs BEFORE the full regression test to catch gross errors quickly.
  See .claude/plans/P2.5_VERIFICATION_PLAN.md for complete implementation details.



---

## PROMPT 3: Layer 1 — Conservation and Mass-Balance Checks

```
Layer 5 regression harness is in place. Now implement Layer 1: Conservation and Mass-Balance Checks.

Create a module (e.g., tests/test_conservation.py) that runs the following checks after every pipeline execution:

1. VOLUMETRIC BUDGET CLOSURE: Parse the MODFLOW96 listing file (you showed me the format in the exploration step). Extract the percent discrepancy. Assert it is < 0.1%. If you can't find the budget summary, that itself is a hard fail.

2. PUMPING-IN = PUMPING-USED: Sum the raw pumping data from the input file(s). Sum the pumping that MODFLOW applied (extract from the listing file well budget or the .wel stress period data). Assert they match within tolerance. Use the same units — be explicit about unit conversions if any exist.

3. DEPLETION ≤ PUMPING: For every time step and every reach in the post-processor output, assert that cumulative streamflow depletion does not exceed cumulative pumping. This is a physics constraint — depletion cannot create water.

4. TABLE SUM INTEGRITY: For each of the 5 report tables, identify any rows or columns that should sum to a known total (e.g., well totals, reach totals, annual totals). Assert the sums are internally consistent.

Each check should:
- Print a clear description of what it's testing
- Print PASS or FAIL with the specific values
- Return a structured result (dict or dataclass) that can be collected into the provenance manifest later

Wire these checks so they can be called from the main pipeline script OR run standalone.
```

---

## PROMPT 4: Layer 6 — Provenance and Reproducibility Logging

```
Now implement Layer 6: Provenance and Reproducibility Logging.

 Create a module (e.g., pipeline_manifest.py) that the main pipeline script calls at the end of every run. It should generate a manifest file (JSON or
  YAML, your pick — I want it human-readable) alongside the 5 report tables containing:

  1. INPUT MANIFEST:
    - File name, full path, SHA-256 hash, file size, row count (for tabular files), and date range of data for every input file the pipeline consumed
    - Include historical baseline files from validation/historical/ with their hashes
  2. PIPELINE MANIFEST:
    - Git commit hash of the project (if git is available; otherwise note "not under version control")
    - Python version
    - Names and modification dates of the main pipeline scripts
    - Name and modification date of the MODFLOW96 executable
    - Name and modification date of the Fortran post-processor executable
  3. TEST RESULTS MANIFEST:
    - Pass/fail status of every Layer 0 (smoke) and Layer 1 (conservation) check
    - Pass/fail status of ballpark_check.py (from P2.5)
    - The specific values that were tested and the thresholds applied
    - Timestamp of when each test ran
  4. FLAG REGISTER:
    - Placeholder section (will be populated by Layer 2 and 3 flags later)
    - Format: test name, flagged value, threshold, disposition field (blank — for analyst to fill in manually), analyst initials field, date field
  5. RUN METADATA:
    - Timestamp of pipeline run (start and end)
    - Total runtime
    - Machine name / OS

  The manifest file should be named with the run date, e.g., buckman_manifest_2025.json.

  Also create a simple print_manifest_summary() function that prints a one-page human-readable summary to the console (e.g., "47 tests passed, 0 failed,
  2 flags pending review, all input hashes verified").
```

---

## PROMPT 5: Layer 2 — Temporal Consistency Checks

```
 Now implement Layer 2: Temporal Consistency and Stationarity Checks.

  Historical data is now available from P2.5:
  - validation/historical/bounds.yaml (statistics + time_series)
  - validation/historical/Table_*_historical.xlsx (raw data)

  Use these files directly. The data exists — do not stub.

  1. YEAR-OVER-YEAR RATE-OF-CHANGE:
    - Load prior year data from bounds.yaml → time_series section
    - For each well: flag if annual pumping changed by more than X% relative to prior year
    - For each reach: flag if the depletion/pumping ratio shifted by more than Y% year-over-year
    - [Defaults: X=40%, Y=25% — make configurable]
    - These are FLAGS not fails — they produce entries in the flag register, not hard stops
  2. SEASONAL PATTERN VALIDATION:
    - Load mean historical monthly profile from bounds.yaml → monthly_profile.mean_profile
    - Extract monthly pumping profile for the current run year
    - Normalize it (fraction of annual total per month)
    - Compute Pearson correlation against the mean historical monthly profile
    - Flag if r < 0.85
    - This specifically catches stress period misalignment (months shifted by one)
  3. MULTI-YEAR TREND CHECK:
    - Load time series from bounds.yaml → time_series section
    - For key output values (total annual pumping, total annual depletion per reach), fit a simple linear regression to 2022-2024 values
    - Compute 95% prediction interval
    - Flag if current year falls outside the PI

  For all three checks: the thresholds should be configurable (in bounds.yaml or at the top of the module as named constants). Every flag should include
  the flagged value, the threshold, and a plain-English explanation of what it means.

  Wire all flags into the Layer 6 provenance manifest flag register.
```

---

## PROMPT 6: Layer 3 — Cross-Comparison / Pseudo-Validation

```
Now implement Layer 3: Cross-Comparison Checks.

1. 2024 RETROACTIVE VALIDATION:
   This should already be covered by the Layer 5 regression harness. Confirm it's wired in. If the regression harness passes, log it as a Layer 3 cross-comparison pass in the manifest.

2. MUNICIPAL DEMAND CROSS-CHECK:
   - Create a stub function that accepts City of Santa Fe total annual water production (a single number or a simple CSV with year + production columns)
   - Computes the ratio of Buckman pumping to City production
   - Compares against historical ratio range
   - Flags if outside tolerance
   - I'll provide the City data separately — just build the interface

3. USGS GAGE CROSS-CHECK:
   - Create a stub function that accepts USGS daily streamflow data for the relevant gage(s)
   - Computes a simple anomaly metric (e.g., departure from historical mean baseflow for the same month)
   - Compares direction of anomaly against direction of modeled depletion change
   - Flags gross inconsistencies (model says more depletion, gage says more baseflow)
   - I'll provide gage numbers and data — build the interface

For the stubs: include clear docstrings explaining exactly what input data format is expected (column names, units, date format) so I know precisely what to prepare.

Wire all checks into the manifest system from Layer 6.
```

---

## PROMPT 7: Layer 0.5 — Pipeline Edge Case Testing

> **Note:** This replaces the original Layer 4 Perturbation Testing. See `.claude/plans/P7_VERIFICATION_OMITTED.md` for the full perturbation framework design and rationale for omission.

```
Now implement Layer 0.5: Pipeline Edge Case Testing.

This layer validates that the pipeline's Python code handles unexpected, malformed, or boundary-condition inputs correctly. These tests run in <30 seconds with NO MODFLOW execution — they test our code, not the model.

Why "Layer 0.5": These tests logically fit between Layer 0 (smoke tests) and Layer 1 (conservation checks). They validate input handling BEFORE any MODFLOW execution.

Create tests/test_edge_cases.py with the following test categories:

1. INPUT VALIDATION TESTS:
   - test_missing_input_file: step1 with nonexistent CSV raises clear FileNotFoundError
   - test_empty_csv: CSV with headers but no data rows produces clear error
   - test_malformed_csv_missing_columns: Missing column (e.g., 'BWell 5') identifies which column
   - test_csv_wrong_encoding: Non-UTF-8 file rejected with encoding error
   - test_csv_with_extra_columns: Extra columns ignored without crashing

2. DATA QUALITY TESTS:
   - test_missing_days_in_input: CSV with <365 rows produces warning with count
   - test_duplicate_dates: Duplicate date entries detected and reported
   - test_out_of_order_dates: Unsorted dates handled or rejected with message
   - test_negative_pumping_value: Negative MGD rejected as physically impossible
   - test_unreasonably_large_pumping: Value >100 MGD flagged as likely error
   - test_nan_values_in_input: NaN/blank cells produce error identifying row/column

3. BOUNDARY CONDITION TESTS:
   - test_zero_pumping_all_wells: All wells = 0 completes without error
   - test_zero_pumping_one_well: Single well = 0 handled correctly
   - test_single_day_of_pumping: Only Jan 1 has data, monthly aggregation correct
   - test_leap_year_handling: 366 vs 365 days handled correctly
   - test_february_days: Feb has 28 or 29 days depending on year

4. FILE OPERATION TESTS:
   - test_output_directory_missing: Missing dir created or clear error
   - test_output_file_exists: Existing file overwritten without error
   - test_input_file_permissions: Unreadable file produces permission error

5. WEL FILE INTEGRITY TESTS:
   - test_wel_file_line_count: Exactly 324 lines per year
   - test_wel_file_crlf_endings: Windows CRLF for MODFLOW96 compatibility
   - test_wel_file_column_alignment: Fixed-width columns match MODFLOW spec
   - test_well_name_mapping: Well 3 maps to 'BUCKMAN 3A'
   - test_pumping_rate_sign: All rates negative (extraction convention)
   - test_layer_split: Pumping split equally between Layer 1 and 2

Use pytest fixtures to create test data programmatically. Use parameterized tests where appropriate. All tests must produce clear, diagnostic error messages that identify: what failed, where, actual vs expected, how to fix.

Add pytest marker 'edge_cases' to pytest.ini for selective execution: pytest -m edge_cases
```

---

## PROMPT 8: Integration — Wire Everything Together

```
All individual layers are built. Now wire them together.

  1. Create a master test runner script (e.g., run_all_tests.py) that:
    - Runs ballpark_check.py FIRST (fast sanity check from P2.5, <5 sec)
    - If ballpark has HARD FAILS, stop immediately with exit code 2
    - Runs Layer 0 (smoke) checks
    - Runs Layer 0.5 (edge case) checks — input validation, data quality, boundary conditions
    - Runs Layer 1 (conservation) checks
    - Runs Layer 2 (temporal consistency) checks
    - Runs Layer 3 (cross-comparison) checks
    - Generates the Layer 6 provenance manifest
    - Prints a final summary: total tests, passed, failed, flagged
    - Returns exit code 0 only if all hard-stop tests pass
    - Flags are listed but do NOT cause a non-zero exit code (they require human review)
  2. Modify the main pipeline script to call run_all_tests.py automatically after generating the 5 report tables. The pipeline should:
    - Run the model and generate tables (existing workflow)
    - Run all tests (starting with ballpark check)
    - Generate the manifest
    - Print the summary
    - If any hard-stop test fails, print a clear WARNING that the outputs should not be used until the failure is investigated
  3. Ensure the Layer 5 regression harness (run_regression_2024.py) remains a SEPARATE standalone script. It should be run manually before deploying any
  pipeline changes, not as part of every production run.
  4. Create a brief README.md in the tests/ directory explaining:
    - What each test layer does:
      - Layer 0: Smoke tests (does code run?)
      - Layer 0.5: Edge case tests (input validation, data quality, boundary conditions)
      - Layer 1: Conservation checks (mass balance)
      - Layer 2: Temporal consistency (year-over-year changes)
      - Layer 3: Cross-comparison (external validation)
      - Layer 5: Regression harness (frozen 2024 baseline)
      - Layer 6: Provenance manifest
    - How to run the full test suite
    - How to run the regression harness
    - How to run edge case tests selectively: pytest -m edge_cases
    - What to do when a test flags (review procedure)
    - Where the manifest file is written

  Review the entire test suite for consistency, then show me the final directory structure and a summary of what's been built.
```

---

## NOTES

- If Claude Code's context window gets long during implementation, you can start a new session and say: "Read TESTING_FRAMEWORK.md and the existing test code in tests/ to get up to speed. We're implementing Layer [N] next."
- After each layer, run the tests against actual data to verify they work before moving on.
- **Layer 4 (perturbation) was intentionally omitted.** After critical review, we determined that 54 hours of compute to verify MODFLOW physics provides no value for a compliance pipeline. See `.claude/plans/P7_VERIFICATION_OMITTED.md` for the full design and rationale. Layer 0.5 (edge case tests) replaces it with <30 second tests that catch actual production failure modes.
- Keep the handoff document in the project permanently — it serves as the architectural spec for the test harness, which is useful for your successor.
