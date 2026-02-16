# CLAUDE CODE HANDOFF: Buckman Wellfield Red Team Testing Framework

## WHO YOU ARE

You are acting as a guru-level senior software engineer and hydrologist with 30+ years of practical experience in groundwater modeling, government water resource workflows, and building defensible analytical pipelines for court-facing deliverables. You are advising Brad, Lead Hydrologist at the New Mexico Office of the State Engineer (OSE), on building an adversarial testing harness for his Buckman wellfield pipeline.

## CONTEXT: THE PIPELINE

Brad has built (or is finalizing) an automated workflow that does the following:

1. **Ingests** pumping data for the Buckman wellfield (wells serving the City of Santa Fe)
2. **Runs MODFLOW-96** (the original 1996 MODFLOW executable — NOT FloPy, NOT MODFLOW-2005/6) to simulate groundwater flow under the pumping regime
3. **Runs a compiled Fortran post-processor** that evaluates project-specific streamflow depletion from the MODFLOW output
4. **Produces 5 Excel (.xlsx) report tables** that get copy-pasted into an annual report

The pipeline is written in **Python** calling the MODFLOW96 .exe and the Fortran post-processor as subprocesses. Outputs are Excel files.

Brad has **independent validation data for 2024 only**, stored as a spreadsheet (xlsx or csv) with expected values produced by an independent method. He does NOT have independent validation data for 2025 or future years. That's the core problem: how to rigorously test pipeline outputs for years where no second-method ground truth exists.

## YOUR FIRST TASK: EXPLORE THE PROJECT

Before writing any code, you MUST thoroughly explore the project structure to understand:

1. **Directory layout** — where are the Python scripts, MODFLOW input files, Fortran post-processor, output files, and the 2024 validation data?
2. **The main pipeline script(s)** — read the Python code to understand:
   - How pumping data is ingested (file format, parsing logic)
   - How MODFLOW input files (.bas, .bcf, .wel, .oc, .pcg, etc.) are constructed or modified
   - How MODFLOW96 is called (subprocess? os.system?)
   - How the Fortran post-processor is called and what it reads/writes
   - How the 5 report tables are generated from MODFLOW/post-processor output
   - What hand-off points exist where data transforms between formats
3. **The existing smoke test** — Brad isn't sure what testing currently exists. Look at the Python code for any assert statements, try/except blocks, validation checks, logging, or test scripts. Document what you find.
4. **The 2024 validation data** — find the spreadsheet, understand its structure, and determine what values it contains and at what precision.
5. **Historical data availability** — look for any multi-year pumping records, historical model runs, or archived outputs that could support temporal consistency checks.

Summarize your findings BEFORE proposing any implementation. Ask Brad to confirm your understanding is correct.

## THE SIX-LAYER TESTING FRAMEWORK TO IMPLEMENT

Below are six testing layers, ordered from easiest to most sophisticated. Layers 1–4 and 5–6 are non-negotiable for court-facing deliverables. Each layer catches a different class of failure. The overall principle:

> **The pipeline is not the product. The test harness is the product.** The pipeline produces answers. The harness produces confidence.

> **Governing principles:**
> - "Review the output, not the code. Test code against the objective." (Bloch)
> - "Automate the evaluation before you automate the work. Build the test harness first." (Wissner-Gross)

### Layer 0: Smoke Test (Already exists — verify and document)

**What it catches:** Pipeline crashes, missing files, NaN/null outputs, files that don't write.

**Action:** Read the existing code, document what checks currently exist, and identify gaps. At minimum, a smoke test should verify:
- MODFLOW96 ran to completion (check return code and/or listing file for "NORMAL TERMINATION")
- The Fortran post-processor ran to completion
- All 5 output Excel files were created and are non-empty
- No NaN, Inf, or null values appear in the output tables
- All expected columns/rows are present in each table

### Layer 1: Conservation and Mass-Balance Checks

**What it catches:** Physics violations — water created or destroyed at pipeline hand-off points.

**Tests to implement:**

- **Volumetric budget closure:** After MODFLOW run, parse the listing file (.lst) to extract the volumetric budget summary. Assert total percent discrepancy < 0.1%. MODFLOW96 prints this in a specific format in the listing file — look for "PERCENT DISCREPANCY" in the output.

- **Pumping-in = pumping-used:** Sum the raw pumping data that was ingested (from the source spreadsheet/csv). Sum the pumping that MODFLOW applied (from the .wel file or listing file well budget). Assert they match within floating-point tolerance (e.g., < 0.01 AF or whatever units are used). This catches: mis-mapped well IDs, dropped records during parsing, stress period alignment errors.

- **Depletion ≤ pumping:** For every time step and every reach in the post-processor output, assert that cumulative streamflow depletion does not exceed cumulative pumping. Depletion cannot create water. This catches: sign errors, boundary condition artifacts, reach connectivity errors.

- **Table row/column sum integrity:** If any of the 5 report tables contain values that should sum to a known total (e.g., total annual pumping across all wells, total annual depletion across all reaches), assert the sums match. This catches: rounding artifacts, dropped rows during table generation.

### Layer 2: Temporal Consistency and Stationarity Checks

**What it catches:** Values that are physically possible but historically implausible.

**Tests to implement:**

- **Year-over-year rate-of-change bounds:** For each well, flag if annual pumping changed by more than X% relative to prior year. Brad should define X based on operational knowledge (suggest starting with 30–50% for wells that could go offline, 15% for steady wells). For depletion: flag if the depletion/pumping ratio for any reach shifted by more than Y% year-over-year. These are FLAGS (force human review), not hard fails.

- **Seasonal pattern validation:** Buckman pumping has a seasonal signature driven by Santa Fe municipal demand. Extract monthly pumping profile for the current year, normalize it, compute Pearson correlation against the mean historical monthly profile. If correlation drops below threshold (e.g., r < 0.85), flag. This catches stress period misalignment — the most insidious bug where everything looks right but months are shifted by one.

- **Multi-year trend continuity:** Compare current year values against historical time series. Compute simple linear regression on prior 10 years. Assert current year falls within 95% prediction interval. Flag (not fail) if outside. Purpose: force confirmation that any outlier is real before it enters a report.

**Note:** This layer requires historical pumping/depletion data. If it's not already in the project, Brad may need to assemble it from archived annual reports or previous model runs.

### Layer 3: Cross-Comparison / Pseudo-Validation

**What it catches:** Systematic errors that are internally consistent but externally wrong.

**Tests to implement:**

- **Municipal demand cross-check:** Buckman pumping is driven by City of Santa Fe demand. If City total water production data is available (public records), assert that the ratio of Buckman pumping to total City production is consistent with historical ratios ± a tolerance band. This is an independent data source external to the pipeline.

- **USGS gage cross-check:** If streamflow depletion targets reaches with USGS gaging stations, compare modeled depletion signal direction against observed streamflow anomalies. A gross inconsistency (model predicts increasing depletion while gage shows increasing baseflow) is a hard flag.

- **SCADA/operational record comparison:** If available, cross-reference ingested pumping data against City SCADA or operational logs. Different source, same physical reality. Discrepancies = ingestion error or reporting inconsistency.

- **2024 retroactive validation (THE MOST POWERFUL TEST):** Run 2024 data through the EXACT same pipeline code/config being used for 2025. Compare output against the independent 2024 validation spreadsheet. If the current pipeline reproduces 2024 correctly, confidence in 2025 results increases significantly. If it doesn't, STOP — the pipeline has drifted.

### Layer 4: Perturbation / Sensitivity Testing

**What it catches:** Fragility — results that change dramatically from small input changes.

**Tests to implement:**

- **Input perturbation suite:** Take the current year's pumping data and create controlled perturbations:
  - Add ±5% uniform noise to all pumping values
  - Shift one well's data by one stress period (time offset)
  - Zero out one well entirely
  - Double one well's pumping for one month
  Run full pipeline on each perturbed input. Assert output changes are proportional and physically reasonable. If zeroing out one minor well causes 40% change in depletion at a distant reach, something is wrong.

- **Boundary condition sensitivity:** If the MODFLOW model uses head-dependent boundaries (GHBs, rivers, drains), perturb boundary conductances by ±20%. Assert depletion results are stable within a defined envelope. Large sensitivity = must disclose in report.

- **Swapped-well test:** Swap pumping data between two wells of similar magnitude. Total pumping unchanged, spatial distribution changed. Assert total depletion changes by a physically reasonable amount. Catches: incorrectly connected model cells, pathological conductivities.

### Layer 5: Regression Testing Against the 2024 Harness Year

**What it catches:** Pipeline drift over time.

**This is the single highest-value layer.** Implementation:

- **Create a frozen, version-controlled archive:**
  - `validation/2024/inputs/` — the exact 2024 raw input files
  - `validation/2024/expected_outputs/` — the 2024 expected output tables (from independent validation)
  - `validation/2024/tolerances.json` (or .yaml) — acceptance criteria for each value (absolute and/or relative tolerance)

- **Compute SHA-256 hashes** of all 2024 input files. Store hashes in the test suite. Before running the regression, verify hashes match. This prevents the failure where someone "fixes" a 2024 input and the regression passes for the wrong reason.

- **Build the regression runner:** A single script (e.g., `run_regression_2024.py`) that:
  1. Verifies input file hashes
  2. Runs the full pipeline on 2024 inputs
  3. Compares every value in the 5 output tables against expected values
  4. Reports pass/fail with specific cell-level detail on any failures
  5. Can be run with ONE COMMAND by anyone, without understanding pipeline internals

- **Policy:** Every time the pipeline is modified — new code, new model version, new config — the 2024 regression runs FIRST. If it fails, the change is rejected. No exceptions.

- **Extend over time:** When independent validation for 2025 or later years becomes available, add them to the regression suite. The harness grows harder to pass and more trustworthy.

### Layer 6: Provenance and Reproducibility Logging

**What it catches:** Inability to explain or reproduce results under legal challenge.

**Implementation:** Every pipeline run should produce, alongside the 5 report tables, a provenance manifest (JSON, YAML, or human-readable text) containing:

- **Input manifest:** File names, SHA-256 hashes, row counts, date ranges, and source system for every input file
- **Pipeline manifest:** Git commit hash (or version identifier) of every script, config file, and model executable used
- **Test results manifest:** Pass/fail status of every automated test (Layers 0–5), with the specific values checked and thresholds applied
- **Flag register:** Any tests that flagged (not failed but require review), with space for analyst disposition: "Reviewed, determined to be [real operational change / data quality issue / within acceptable bounds]. Analyst initials, date."

This manifest goes into the project file alongside the report. It transforms "I checked the numbers" into "43 automated tests passed, 2 flags were reviewed and dispositioned, the pipeline reproduced the independently validated 2024 dataset within tolerance, and here's the hash of every input file."

## RECOMMENDED IMPLEMENTATION ORDER

Optimize for maximum confidence gain per unit of effort:

1. **Week 1: Layer 5 (Regression Harness)** — Freeze 2024 data, build regression runner. This is highest value because it validates the entire pipeline end-to-end against known truth.
2. **Week 1–2: Layer 1 (Conservation Checks)** — Mass-balance assertions at every hand-off point. Cheap to write, catches entire error categories. Parse MODFLOW96 listing file for volumetric budget.
3. **Week 2–3: Layer 6 (Provenance Logging)** — Wire pipeline to emit manifest. Mostly file-hashing and test-result collection. Low difficulty, high courtroom value.
4. **Week 3–4: Layer 2 (Temporal Consistency)** — Requires historical dataset and Brad's domain judgment on statistical envelopes.
5. **Week 4–5: Layer 3 (Cross-Comparison)** — Requires external data sources (City records, USGS). The 2024 retroactive validation should be done as part of Layer 5.
6. **Future: Layer 4 (Perturbation Testing)** — Most sophisticated and time-intensive. Build when other layers are stable.

## CODING STANDARDS FOR THIS PROJECT

Brad is an advanced-novice Python developer. All code must include:
- Detailed comments explaining EVERY step — what, why, and what the code means
- Explanations suitable for a Python beginner at a very detailed level
- Clear variable names that reflect the hydrological concepts
- No clever one-liners — explicit is better than implicit
- Print/logging statements that report progress and results in plain English
- Docstrings on every function explaining inputs, outputs, and purpose

## HOW TO PROCEED

1. **First:** Explore the project directory structure completely. List what you find.
2. **Second:** Read the main pipeline Python script(s). Summarize the workflow step by step.
3. **Third:** Identify and document any existing tests/checks in the code.
4. **Fourth:** Locate the 2024 validation data. Describe its structure.
5. **Fifth:** Present your findings to Brad and confirm understanding before writing any test code.
6. **Sixth:** Implement layers in the order specified above, one at a time, with Brad's review after each.

Do NOT write test code until you've completed steps 1–5 and confirmed understanding. The test harness must be built against the ACTUAL pipeline, not assumptions about it.
