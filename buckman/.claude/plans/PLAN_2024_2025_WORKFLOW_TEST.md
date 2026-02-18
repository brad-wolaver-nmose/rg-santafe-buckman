# Buckman Workflow Test Plan: 2024 Validation → 2025 Production

**Status:** DRAFT - Awaiting final user approval
**Objective:** Validate 2024 workflow produces correct outputs, then process 2025 for regulatory reporting

---

## Expert Recommendation

**As a senior developer with 30+ years USGS groundwater modeling experience, I recommend Option A-Modified (Full Validation with Checkpoints).**

### Rationale
1. **Audit defensibility**: "I regenerated from raw inputs" is legally stronger than "I verified existing files"
2. **Unknown code changes**: Full regeneration catches any regressions
3. **Chain-of-custody**: Proving 2024 correct before generating 2025 establishes provenance
4. **Asymmetric risk**: Extra compute cost << Cost of incorrect regulatory submission

### The Modification: Pre-MODFLOW Checkpoints
Validate Steps 1-2 outputs BEFORE the expensive MODFLOW run. Catches data problems immediately without wasting compute time.

---

## Strategic Options Analysis

From the perspective of a senior developer with 30+ years USGS groundwater modeling experience, here are three approaches with trade-offs:

---

## Option A: Full Sequential Pipeline (Recommended)

**Philosophy:** "Trust but verify" - Regenerate everything from scratch

### Workflow
```
Phase 1: 2024 Full Validation (~50 min)
├── Step 1: Ingest 2024 CSV → Tables 1-2 (~1 min)
├── Step 2: Update MODFLOW files → WEL/NAM (~1 min)
├── CHECKPOINT: Smoke tests on Steps 1-2 outputs (~5 sec)
├── Step 3: Run MODFLOW96 (~35-45 min)
├── Step 4: Generate Tables 3-5 (~1 min)
├── Run regression test vs frozen expected outputs
├── Run full test suite (220 tests, ~5 sec)
└── GATE: Human review before proceeding

Phase 2: 2025 Production (~50 min)
├── Step 1: Ingest 2025 CSV → Tables 1-2
├── Step 2: Update MODFLOW (chains from 2024 WEL)
├── CHECKPOINT: Smoke tests + .wel integrity
├── Step 3: Run MODFLOW96
├── Step 4: Generate Tables 3-5
├── Ballpark checks (historical bounds)
├── Temporal consistency (vs 2024 baseline)
└── Generate provenance manifest
```

### Pros
- **Maximum confidence**: Proves entire pipeline works end-to-end
- **Clean slate**: Catches environment drift (Python version, library updates)
- **Audit defensible**: Can testify "I regenerated from raw inputs"
- **Catches regression bugs**: Any code changes since last run are tested

### Cons
- **Longest runtime**: ~1.5-2 hours total
- **Regenerates correct files**: May be unnecessary if nothing changed
- **Resource intensive**: Two MODFLOW runs

### When to choose
- Code changes were made since last 2024 run
- Moving to a new machine or environment
- Preparing for regulatory submission or audit
- Any doubt about existing output integrity

---

## Option B: 2024 Test-Only + 2025 Full Run

**Philosophy:** "Verify existing, generate new"

### Workflow
```
Phase 1: 2024 Verification Only (~10 min)
├── Verify all 2024 output files exist with correct hashes
├── Run full test suite on existing outputs (~5 sec)
├── Run regression test (cell-by-cell comparison) (~30 sec)
├── Verify MODFLOW .lst file budget closure
└── GATE: Human review before proceeding

Phase 2: 2025 Production (~50 min)
├── Steps 1-4 full pipeline
├── Ballpark + temporal + manifest
└── Final review
```

### Pros
- **Faster**: ~1 hour total (saves one MODFLOW run)
- **Validates integrity**: Confirms existing 2024 files haven't been corrupted
- **Gets to production faster**: 2025 results sooner

### Cons
- **Doesn't test pipeline**: Only tests outputs, not the code that generates them
- **Environment changes undetected**: New Python/library issues won't surface
- **Weaker audit position**: Cannot claim "I ran it from scratch"

### When to choose
- No code changes since last 2024 run
- Time pressure for 2025 results
- High confidence in existing 2024 outputs
- Will do full validation later before formal submission

---

## Option C: Incremental Checkpointed Approach

**Philosophy:** "Fail fast, invest wisely"

### Workflow
```
Phase 1: Pre-Flight Checks (~2 min)
├── Verify all source files exist (2024 + 2025 input CSVs)
├── Verify 2024 expected outputs exist
├── Quick ballpark check on existing 2024 outputs
└── DECISION: If fail → investigate; If pass → continue

Phase 2: 2024 Pre-MODFLOW Validation (~5 min)
├── Run Steps 1-2 only (ingest + MODFLOW setup)
├── Smoke tests + edge cases on Steps 1-2
├── Compare Table 1-2 vs expected
└── CHECKPOINT: Stop here if mismatch

Phase 3: 2025 Pre-MODFLOW Setup (~5 min)
├── Run Steps 1-2 for 2025
├── Smoke tests on 2025 Steps 1-2
├── Validate .wel file integrity (line counts, CRLF)
└── CHECKPOINT: Review before MODFLOW investment

Phase 4: MODFLOW Runs (~75 min)
├── Run 2024 MODFLOW (if full validation needed)
├── Run 2025 MODFLOW
└── Both can run in parallel if resources allow

Phase 5: Post-Processing & Validation
├── Generate all Tables 3-5
├── Full test suites
├── Manifests
```

### Pros
- **Fast failure**: Catches problems before 45-min MODFLOW investment
- **Progressive confidence**: Build certainty incrementally
- **Flexible**: Can skip 2024 MODFLOW if pre-checks pass

### Cons
- **Complex workflow**: More decision points
- **May backtrack**: If late issues found, need to restart
- **Requires judgment**: Not fully automatable

### When to choose
- Uncertain about input data quality
- Limited time for debugging
- Experienced operator who can interpret intermediate results

---

## Recommendation Matrix

| Scenario | Recommended Option |
|----------|-------------------|
| First run after code changes | **Option A** (full validation) |
| Routine annual processing | **Option B** (test-only + 2025) |
| New environment or machine | **Option A** (full validation) |
| OSE/ISC regulatory submission | **Option A** (full validation) |
| Time pressure, high confidence | **Option B** (test-only + 2025) |
| Uncertain input data quality | **Option C** (incremental) |

---

## Files Involved

### Input Files
- `input/csv/Buckman_Well_Prod_2024.csv` (or subdirectory)
- `input/csv/Buckman_Well_Prod_2025.xlsx` (confirmed real data)
- `input/modflow/2023/thruCY2165.wel` (2003-2023 baseline)

### Validation Reference
- `validation/2024/expected_outputs/Table_{1-5}_expected.xlsx`
- `validation/2024/tolerances.yaml`
- `validation/historical/bounds.yaml`

### Key Scripts
- `step1_ingest_buckman_data.py --year YYYY`
- `step2_update_modflow.py --year YYYY`
- `step3_run_modflow.sh --year YYYY`
- `step4_generate_depletion_tables.py --year YYYY`
- `run_all_tests.py --year YYYY`
- `validation/2024/run_regression_2024.py`
- `validation/temporal_consistency.py --year YYYY`
- `validation/ballpark_check.py --year YYYY`

### Output Directories
- `output/ingested_data/` (Tables 1-2)
- `output/modflow/{YEAR}/` (MODFLOW artifacts)
- `output/depletion/` (Tables 3-5)
- `output/manifests/` (Provenance JSON)
- `output/test_results/` (Test reports)

---

## Success Criteria

### 2024 Validation Pass Criteria
- [ ] Regression test: All cells within `tolerances.yaml` thresholds
- [ ] Test suite: 220 tests pass (0 failures)
- [ ] Budget closure: MODFLOW volumetric budget ≤ 0.1%
- [ ] Files match: SHA-256 hashes match frozen baselines

### 2025 Ballpark Pass Criteria
- [ ] Annual pumping: Within 2σ of historical (866-1373 AF ±2σ)
- [ ] Depletions: Within envelope bounds (bounds.yaml)
- [ ] YoY pumping change: ≤65% vs 2024
- [ ] YoY ratio change: ≤45% vs 2024
- [ ] Seasonal correlation: r ≥0.75 vs historical profile
- [ ] Physics: Depletion ≤ Pumping, non-negative values, monotonic cumulative

---

## Documentation Deliverables

### Required (this task):
1. **README.md** (root) - Project overview, quick-start, architecture
2. **docs/BUCKMAN_WORKFLOW.md** - Detailed step-by-step workflow for technical hydrologists
3. **PLAN_WORKFLOW_REVIEW.md** - Comprehensive workflow review + verification checklist
4. **PLAN_WORKFLOW_REVIEW_OUT.md** - Results of workflow review execution
5. **This plan file `_OUT.md`** - Results of test execution

### Generated automatically:
6. **`output/manifests/buckman_manifest_2024.json`** - 2024 provenance
7. **`output/manifests/buckman_manifest_2025.json`** - 2025 provenance

---

## PLAN_WORKFLOW_REVIEW.md Outline

**Purpose:** Comprehensive reference verifying entire workflow handles:
- 2024 input → processing → validation
- Year-agnostic N+1 workflow (2025+)
- All P1-P8 testing properly incorporated

**Audience:** Brad + OSE technical hydrologists

**Structure:**
```
1. Executive Summary
2. Workflow Architecture
   - Data flow diagram
   - File pathways (input → output)
   - Year chaining logic
3. Step-by-Step Verification
   3.1 Step 1: Ingest (code trace + checklist)
   3.2 Step 2: MODFLOW Setup (code trace + checklist)
   3.3 Step 3: MODFLOW Execution (checklist)
   3.4 Step 4: Depletion Tables (code trace + checklist)
4. Test Layer Verification
   4.1 Layer 0 (smoke) - incorporated? ☐
   4.2 Layer 0.5 (edge) - incorporated? ☐
   4.3 Layer 1 (conservation) - incorporated? ☐
   4.4 Layer 2 (temporal) - incorporated? ☐
   4.5 Layer 5 (regression) - incorporated? ☐
   4.6 Layer 6 (provenance) - incorporated? ☐
5. Year-Agnostic Verification
   - 2024 baseline handling
   - N+1 year chaining
   - Input file discovery
   - Output directory structure
6. Cross-References
   - Link to P1-P8 verification plans
   - Link to test execution plan
7. Verification Checklist (consolidated)
```

---

## Recommended Execution Sequence (Option A-Modified)

### Phase 1: Pre-Flight Verification
```bash
# Verify required files exist
ls input/csv/Buckman_Well_Prod_2024.csv  # or subdirectory
ls input/csv/Buckman_Well_Prod_2025.xlsx
ls input/modflow/2023/thruCY2165.wel
ls validation/2024/expected_outputs/
```

### Phase 2: 2024 Full Pipeline
```bash
# Step 1: Ingest
python3 step1_ingest_buckman_data.py --year 2024

# Step 2: MODFLOW setup
python3 step2_update_modflow.py --year 2024

# CHECKPOINT: Pre-MODFLOW validation
pytest -m layer0 -v --tb=short 2>&1 | head -50
pytest -m edge_cases -v --tb=short

# Step 3: MODFLOW execution (long-running)
./step3_run_modflow.sh --year 2024

# Step 4: Depletion tables
python3 step4_generate_depletion_tables.py --year 2024

# Full test suite
python3 run_all_tests.py --year 2024 --verbose

# Regression test
python3 validation/2024/run_regression_2024.py
```

### Phase 3: Human Review Gate
- Review test results
- Verify regression output
- Check manifest
- **DECISION: Proceed to 2025?**

### Phase 4: 2025 Production Pipeline
```bash
# Steps 1-4 for 2025
python3 step1_ingest_buckman_data.py --year 2025
python3 step2_update_modflow.py --year 2025

# CHECKPOINT: Pre-MODFLOW
pytest -m layer0 -v --tb=short
pytest -m edge_cases -v --tb=short

# Step 3: MODFLOW (uses 2024 WEL as input)
./step3_run_modflow.sh --year 2025

# Step 4: Generate tables
python3 step4_generate_depletion_tables.py --year 2025

# Full validation (ballpark + temporal)
python3 run_all_tests.py --year 2025 --verbose
```

### Phase 5: Documentation
```bash
# Generate/update documentation
# - README.md
# - docs/BUCKMAN_WORKFLOW.md
# - PLAN_WORKFLOW_REVIEW.md → PLAN_WORKFLOW_REVIEW_OUT.md
# - This plan → _OUT.md
```

---

## Execution Order Summary

| Step | Action | Gate |
|------|--------|------|
| 1 | Create PLAN_WORKFLOW_REVIEW.md | Review before execution |
| 2 | 2024 Steps 1-2 | Pre-MODFLOW checkpoint |
| 3 | 2024 MODFLOW | - |
| 4 | 2024 Step 4 + tests | **Human review gate** |
| 5 | 2025 Steps 1-2 | Pre-MODFLOW checkpoint |
| 6 | 2025 MODFLOW | - |
| 7 | 2025 Step 4 + tests | Review flags |
| 8 | Documentation updates | Final review |
| 9 | Create _OUT.md files | Archive |

---

## Final Approval Required

**Confirm you want to proceed with Option A-Modified:**
- Full 2024 regeneration + validation
- Pre-MODFLOW checkpoints
- Human review gate before 2025
- Full 2025 production run
- Documentation updates

Or specify modifications.
