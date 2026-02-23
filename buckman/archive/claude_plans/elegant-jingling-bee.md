# Plan: Chain Table 5 (La Cienega Springs) from Prior Year's Output

## Goal

Modify Table 5 generation so that year N's output chains from year N-1's Table 5 xlsx:
- **Years 2004 through N-1**: preserved from prior year's Table 5 (locked in by their respective MODFLOW runs)
- **Years N through 2030**: recomputed from current MODFLOW post-processor output
- **Fallback**: if no prior-year Table 5 xlsx exists, use `LA_CIENEGA_CUMULATIVE` dict

This mirrors the Table 3 chaining pattern already implemented.

---

## Current State

- `write_table5_xlsx(output_path, years=None)` — writes ALL rows (2004-2030) from `LA_CIENEGA_CUMULATIVE` hardcoded dict
- `generate_table5_data(parsed_data, year)` — extracts one year's LC SPRINGS cfs from parsed_data, converts to cumulative AF
- `parsed_data` contains LC SPRINGS for years 1988-2165 (all available)
- MODFLOW superposition output is already cumulative, so `cfs_monthly_to_af_annual()` directly gives the cumulative AF value for any year

---

## Code Changes

### File 1: `stream_depletions.py`

#### Change 1A: New helper `load_historical_table5()` (~line 1840, before write_table5_xlsx)

```python
def load_historical_table5(
    baseline_path: Path | str | None = None
) -> dict[int, float]:
    """Load historical Table 5 cumulative values from a prior-year xlsx.

    Reads columns A (Year) and B (Total cumulative AF) from a Table 5 xlsx.
    Returns dict mapping year -> cumulative_af.

    Falls back to LA_CIENEGA_CUMULATIVE dict if baseline_path is None or
    file doesn't exist.
    """
```

Logic:
1. If `baseline_path` is None or file doesn't exist, return `dict(LA_CIENEGA_CUMULATIVE)` (copy of the hardcoded dict)
2. Otherwise, open xlsx with openpyxl, iterate data rows (row 2+), read col A (year) and col B (cumulative AF)
3. Return `{year: cumulative_af}` dict

#### Change 1B: Modify `write_table5_xlsx()` signature and logic (~line 1842)

New signature:
```python
def write_table5_xlsx(
    output_path: str | Path,
    parsed_data: dict[int, dict[str, dict[str, float]]] | None = None,
    processing_year: int | None = None,
    years: list[int] | None = None,
    historical_baseline: Path | str | None = None,
) -> Path:
```

New logic (inserted after style definitions, before data rows loop):
```python
# Load historical baseline for chaining
historical_values: dict[int, float] = {}
if processing_year is not None:
    if historical_baseline is not None:
        historical_values = load_historical_table5(historical_baseline)
    else:
        # Auto-resolve: try prior year's Table 5 output
        prior_year_path = Path(
            f"output/depletion/TABLE_5_La_Cienega_Springs_{processing_year - 1}.xlsx"
        )
        if prior_year_path.exists():
            print(f"  Chaining Table 5 from prior year: {prior_year_path}")
            historical_values = load_historical_table5(prior_year_path)
        else:
            print(f"  Prior year Table 5 not found: {prior_year_path}")
            print(f"  Falling back to LA_CIENEGA_CUMULATIVE dict")
            historical_values = dict(LA_CIENEGA_CUMULATIVE)
```

Modified data row loop — replace the current `cumulative_value = LA_CIENEGA_CUMULATIVE.get(year, 0.0)`:
```python
if processing_year is not None and year < processing_year and year in historical_values:
    # Historical year: use chained value from prior year's output
    cumulative_value = historical_values[year]
elif processing_year is not None and year >= processing_year and parsed_data is not None:
    # Current + future years: recompute from MODFLOW output
    if year in parsed_data and "LC SPRINGS" in parsed_data[year]:
        months = ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
        lc_cfs = [parsed_data[year]["LC SPRINGS"][m] for m in months]
        is_leap = calendar.isleap(year)
        cumulative_value = cfs_monthly_to_af_annual(lc_cfs, year=year, use_leap_year=is_leap)
    else:
        # Year not in parsed data (shouldn't happen for 2004-2030)
        cumulative_value = LA_CIENEGA_CUMULATIVE.get(year, 0.0)
else:
    # No chaining (backward-compatible path for tests)
    cumulative_value = LA_CIENEGA_CUMULATIVE.get(year, 0.0)
```

**Backward compatibility**: When `processing_year` is None (which is how all existing tests call it), behavior is identical to current code — reads from `LA_CIENEGA_CUMULATIVE`.

### File 2: `step4_generate_depletion_tables.py`

#### Change 2A: Update Table 5 write call (~line 1055)

Current:
```python
sd.write_table5_xlsx(table5_path)
```

New:
```python
sd.write_table5_xlsx(table5_path, parsed_data=parsed_data, processing_year=year)
```

### File 3: `tests/test_stream_depletions.py`

#### No test changes needed

All existing tests call `write_table5_xlsx(output_path)` or `write_table5_xlsx(output_path, years=[...])` without `processing_year`, so they hit the backward-compatible path and behavior is unchanged.

---

## Validation

1. `ruff check stream_depletions.py step4_generate_depletion_tables.py && mypy stream_depletions.py step4_generate_depletion_tables.py`
2. `python3 -m pytest tests/ -v --tb=short` — 224 tests pass
3. `python3 step4_generate_depletion_tables.py --year 2024` — Table 5 should use dict fallback (no 2023 Table 5 exists), values identical to current
4. `python3 step4_generate_depletion_tables.py --year 2025` — Table 5 should chain from 2024 output; years 2004-2024 from 2024 xlsx, years 2025-2030 from MODFLOW
5. Open both xlsx files, verify:
   - 2024: values match LA_CIENEGA_CUMULATIVE exactly
   - 2025: years 2004-2024 match 2024 output; years 2025-2030 are MODFLOW-computed
   - Cross-check formulas (columns C-E) still work correctly

---

## Key Design Decisions

1. **`generate_table5_data()` unchanged** — It's used for validation/verification printing, not for the xlsx. The chaining logic lives entirely in `write_table5_xlsx()`.
2. **Direct cfs-to-AF computation in write function** — Rather than calling `generate_table5_data()` in a loop (which would need refactoring for its `previous_cumulative` lookup), we compute `cfs_monthly_to_af_annual()` directly. This is the same computation — just inlined.
3. **`LA_CIENEGA_CUMULATIVE` dict kept** — Still used as fallback for first-time runs and for `generate_table5_data()` validation. Not deleted.
4. **All new parameters optional with None defaults** — Ensures zero breakage for existing callers/tests.
