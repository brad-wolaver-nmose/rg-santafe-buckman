# Plan: Comprehensive Code Quality Sweep + Full Workflow Test

**Date:** 2026-02-18
**Output file:** `.claude/plans/RUFF_MYPY_OUTPUT_20260218.md`

---

## Purpose

Run ruff and mypy across the entire Buckman pipeline codebase, fix any issues, then verify the full workflow with tests.

---

## Scope: 33 Python Files

| Category | Files |
|----------|-------|
| Pipeline steps | `step1_ingest_buckman_data.py`, `step2_update_modflow.py`, `step4_generate_depletion_tables.py`, `step5_verify_workflow.py` |
| Core library | `src/pipeline_manifest.py`, `src/workflow_logger.py`, `src/generate_workflow_log.py` |
| Support | `stream_depletions.py`, `run_all_tests.py` |
| Tests | `tests/test_*.py` (6 files) |
| Validation | `validation/ballpark_check.py`, `validation/temporal_consistency.py`, `validation/2024/run_regression_2024.py` |
| Scripts | `scripts/*.py` (7 files) |
| Verify helpers | `input/modflow/2023/verify_*.py`, `output/modflow/*/verify_*.py` |

Existing config: `ruff.toml` (E, F, W, I, UP rules), `mypy.ini` (check_untyped_defs, warn_return_any)

---

## Execution Steps

### Step 1: Run Ruff on All Python Files
```bash
ruff check . --exclude ".venv,__pycache__"
```
- Fix any issues found (auto-fix where possible: `ruff check . --fix`)
- Document remaining issues requiring manual intervention

### Step 2: Run Mypy on Core Files
```bash
mypy src/ tests/ step*.py stream_depletions.py run_all_tests.py validation/
```
- Fix type errors
- Note: scripts/ and verify_*.py may have looser typing (document but don't necessarily fix all)

### Step 3: Run Full Test Suite
```bash
python3 run_all_tests.py --year 2024
```
- Verify all 220 tests pass
- Confirm workflow log is generated

### Step 4: Optional - Test 2025 as Well
```bash
python3 run_all_tests.py --year 2025
```
- Verify multi-year consistency

---

## Success Criteria

| Check | Pass Criteria |
|-------|---------------|
| ruff | 0 errors on core pipeline files |
| mypy | 0 errors on src/, tests/, step*.py |
| Tests (2024) | 220 passed, 0 failed |
| Workflow log | Generated with correct values |

---

## Notes

- Scripts in `scripts/` are utility/one-off tools - may have lower priority for strict typing
- verify_*.py files in input/output are verification helpers - similar treatment
