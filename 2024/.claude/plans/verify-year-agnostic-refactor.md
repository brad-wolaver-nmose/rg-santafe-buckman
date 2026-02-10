# Verification Plan: Year-Agnostic update_modflow.py Refactor

## Context
Refactored `update_modflow_2024.py` → `update_modflow.py` to work with any year while maintaining 100% fidelity for 2024.

## Quick Verification Checklist

### 1. File Renames Complete
```bash
ls -la update_modflow.py tests/test_update_modflow.py
# Should exist (old *_2024.py files should NOT exist)
ls -la update_modflow_2024.py 2>/dev/null && echo "ERROR: old file still exists"
```

### 2. Tests Pass
```bash
python3 -m pytest tests/test_update_modflow.py -v --tb=short
# Expected: 67 passed
```

### 3. CLI Requires --year
```bash
python3 update_modflow.py 2>&1 | head -5
# Should show: error: the following arguments are required: --year
```

### 4. 2024 Produces Identical Output
```bash
python3 update_modflow.py --year 2024
# Should complete with "Validation PASSED"
```

### 5. Key Functions Accept Year Parameter
```python
# Quick import check
python3 -c "
from update_modflow import (
    get_year_config,
    get_days_in_month,
    find_year_boundaries,
    parse_wel_file,
    generate_well_entries,
    generate_nam_file,
    run_validation,
    YearConfig
)
print('All imports successful')
"
```

### 6. Graceful Validation Degradation
```bash
# Test with hypothetical 2025 (no validation files exist)
# Should warn but not fail if CSV and prior year output exist
python3 -c "
from update_modflow import get_year_config
config = get_year_config(2025)
print(f'2025 would use input: {config.input_wel_path}')
print(f'Validation path: {config.validation_wel_path}')
"
```

## Key Architecture Changes

| Component | Before | After |
|-----------|--------|-------|
| File name | `update_modflow_2024.py` | `update_modflow.py` |
| CLI | `--year` optional (default 2024) | `--year` required |
| Input path | Hardcoded `input/modflow/2023/` | Dynamic: 2024→2023 baseline, 2025+→prior year output |
| Line boundaries | Hardcoded line numbers | Dynamic search via `find_year_boundaries()` |
| Days in month | Hardcoded `DAYS_IN_MONTH_2024` | `get_days_in_month(year)` with leap year handling |
| Validation | Fails if files missing | Warns and skips (graceful degradation) |

## Files Modified
- `update_modflow.py` (renamed from `update_modflow_2024.py`)
- `tests/test_update_modflow.py` (renamed from `tests/test_update_modflow_2024.py`)

## If Issues Found
1. Run full test suite first to identify scope
2. Check function signatures match new patterns (year parameters)
3. Verify no hardcoded "2024" remains in logic (comments are OK)
