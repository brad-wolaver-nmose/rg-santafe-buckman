# IS-10: Test Suite (Layers 0-1)

> **Tier 2 Implementation Specification** -- A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement the pytest test suite covering Layer 0 (smoke tests), Layer 0.5 (edge cases), and Layer 1 (conservation/mass-balance checks) across 7 test files with approximately 240 tests total.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-01: Project scaffold and constants
- IS-03: CSV ingestion (`step1_ingest_buckman_data.py`)
- IS-05: MODFLOW update (`step2_update_modflow.py`)
- IS-07: Stream depletion parsing (`stream_depletions.py`)
- IS-09: Tables 4 & 5 generation

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| pytest.ini | `pytest.ini` | Marker registration (layer0, edge_cases, conservation) |
| Ingestion module | `step1_ingest_buckman_data.py` | CSV ingestion functions |
| MODFLOW update module | `step2_update_modflow.py` | WEL file update functions |
| Stream depletions | `stream_depletions.py` | Depletion calculation functions |
| Step 4 module | `step4_generate_depletion_tables.py` | Table generation orchestrator |

### Domain Knowledge
- See DS-02 for unit conversion factors and hand-calculable examples
- See DS-03 for MODFLOW cell geometry and Otowi classification
- See DS-04 for FORTRAN post-processor extraction rectangles

---

## 3. Context for Claude Code

The test suite implements the first three layers of the 8-prompt testing framework:

**Layer 0 (Smoke Tests):** Verify code runs without crashing. Tests should complete in < 30 seconds with no MODFLOW dependency. These catch import errors, missing functions, and basic execution failures. All tests marked `@pytest.mark.layer0`.

**Layer 0.5 (Edge Cases):** Verify the pipeline handles unexpected inputs correctly -- either processing them gracefully or failing with clear diagnostic error messages. Tests cover zero pumping, leap years, empty months, malformed CSV, missing files. Marked `@pytest.mark.edge_cases`.

**Layer 1 (Conservation):** Verify physics constraints hold. Mass balance, pumping conservation, depletion upper bounds, and table sum integrity. These require pipeline outputs to exist. Marked `@pytest.mark.conservation`.

### Key Equations (Inline)

```
MG to AF:       AF = MG * 3.06889
AF to ft3/s:    rate = -(AF / num_layers) * 43560 / (days * 86400)
CFS to AF:      AF = cfs * days * 86400 / 43560  (= cfs * days * 1.9835)
CFS per day:    1 cfs = 86400 ft3/day = 1.9835 AF/day
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| MG_TO_AF_FACTOR | 3.06889 | AF/MG |
| ACRE_FT_TO_FT3 | 43560 | ft3/AF |
| SECONDS_PER_DAY | 86400 | s/day |
| BUDGET_CLOSURE_TOLERANCE | 0.1 | percent |
| PUMPING_CONSERVATION_TOLERANCE | 0.1 | percent relative |
| TABLE_SUM_TOLERANCE | 0.01 | acre-feet |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | `tests/conftest.py` with shared fixtures | Provides `sample_valid_daily_csv`, `sample_valid_table2_csv`, parametrized month/days fixtures. All 7 test files can import fixtures. **Note:** `tests/conftest.py` does not currently exist; fixtures like `sample_valid_daily_csv` and `sample_valid_table2_csv` are defined directly in `test_edge_cases.py`. |
| R2 | `tests/test_ingest_buckman_data.py` -- CSV ingestion tests | Tests: module imports, constants defined, 13-well map, MG-to-AF factor, monthly ordering, CSV read/validate/aggregate/convert. ~20 tests. All marked layer0. |
| R3 | `tests/test_update_modflow.py` -- MODFLOW WEL operations | Tests: module imports, `convert_af_to_ft3s()` hand-calculated, zero pumping, leap year February, WEL file parsing, well entry generation. ~67 tests. All marked layer0. |
| R4 | `tests/test_stream_depletions.py` -- depletion calculations | Tests: module imports, `cfs_to_acre_feet()` and `cfs_to_af()`, Core 2003 residuals exist, `parse_postprocessor_output()`, `generate_table3_data()`, `generate_table4_data()`, `generate_table5_data()`. ~71 tests. All marked layer0. |
| R5 | `tests/test_conservation.py` -- mass balance checks | Tests: MODFLOW budget closure, pumping-in equals pumping-used, depletion <= pumping, table row/column sum integrity. ~4 test functions (file contains many helper functions). Marked conservation. |
| R6 | `tests/test_edge_cases.py` -- boundary conditions | Tests: missing file handling, empty CSV, zero pumping wells, leap year, single-day month, malformed columns, NaN handling, WEL file CRLF line endings. ~30 tests. Marked edge_cases. |
| R7 | `tests/test_modflow_geometry.py` -- cell coordinate validation | Tests: GHB file parsing, La Cienega cells within FORTRAN rectangle, Otowi cell classification, above/below cell count, BUCKMAN_WELLS_CELL in BELOW_OTOWI. ~16 tests. **Note:** `test_modflow_geometry.py` does NOT have a `pytestmark = pytest.mark.layer0` assignment; running `pytest -m layer0` will not pick up these tests unless the marker is added. |
| R8 | pytest markers registered and functional | `pytest -m layer0`, `pytest -m edge_cases`, `pytest -m conservation` each select the correct subset |

---

## 5. Worked Example

### R2: test_mg_to_af_conversion

#### Input
```python
# Known conversion: 1 MG = 3.06889 AF
# Test input: 100 MG
mg_value = 100.0
```

#### Calculation Steps
```
Step 1: Apply conversion factor
        af = 100.0 * 3.06889 = 306.889 AF

Step 2: Verify range bounds (smoke test style)
        assert 306.0 < af < 307.0
```

#### Expected Output
```python
# 306.889 AF (within tolerance)
```

### R3: test_convert_af_to_ft3s_known_answer

#### Input
```python
# Well 1 JAN 2024: 16.887963 AF, 31 days, 2 layers
acre_feet = 16.887963
days_in_month = 31
num_layers = 2
```

#### Calculation Steps
```
Step 1: Per-layer volume
        per_layer_af = 16.887963 / 2 = 8.443982 AF

Step 2: Convert to ft3
        ft3 = 8.443982 * 43560 = 367,803.0 ft3

Step 3: Convert to rate (ft3/s)
        rate = 367,803.0 / (31 * 86400) = 367,803.0 / 2,678,400 = 0.13730 ft3/s

Step 4: Apply pumping convention (negative)
        result = -0.13730 ft3/s
```

#### Expected Output
```python
# -0.13730 ft3/s (within [-0.15, -0.12] smoke test range)
```

### R4: test_cfs_to_af_sanity

#### Input
```python
# 0.1 cfs for 31 days (January)
cfs = 0.1
days = 31
```

#### Calculation Steps
```
Step 1: Daily AF = 0.1 * 86400 / 43560 = 0.19835 AF/day
Step 2: Monthly AF = 0.19835 * 31 = 6.149 AF
```

#### Expected Output
```python
# 6.149 AF (within [5.0, 8.0] range)
```

### R5: test_depletion_does_not_exceed_pumping

#### Input
```python
# 2024 data: total_pumping ~ 1372.90 AF
# Rio Pojoaque total ~ 60.8 AF, Rio Tesuque total ~ 33.6 AF
# Total depletion ~ 94.4 AF
```

#### Calculation Steps
```
Step 1: Sum depletions from all streams
        total_depletion = pojoaque_total + tesuque_total = 60.8 + 33.6 = 94.4 AF

Step 2: Compare to pumping
        94.4 AF < 1372.90 AF -> PASS (depletion < pumping)

Step 3: Verify ratio is physically reasonable
        ratio = 94.4 / 1372.90 = 0.069 -> within [0.05, 0.15] expected range
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create/Modify | `tests/conftest.py` | Shared fixtures for all test files |
| Create/Modify | `tests/test_ingest_buckman_data.py` | Step 1 ingestion smoke tests |
| Create/Modify | `tests/test_update_modflow.py` | Step 2 MODFLOW update smoke tests |
| Create/Modify | `tests/test_stream_depletions.py` | Stream depletion calculation tests |
| Create/Modify | `tests/test_conservation.py` | Layer 1 conservation/mass-balance checks |
| Create/Modify | `tests/test_edge_cases.py` | Layer 0.5 edge case and boundary tests |
| Create/Modify | `tests/test_modflow_geometry.py` | MODFLOW cell geometry validation |
| Modify | `pytest.ini` | Register markers: layer0, edge_cases, conservation |

---

## 7. Acceptance Criteria

```bash
# Run all layers independently:
pytest tests/ -m layer0 -v --tb=short           # ~120 smoke tests
pytest tests/ -m edge_cases -v --tb=short        # ~50 edge case tests
pytest tests/ -m conservation -v --tb=short      # ~20 conservation tests (requires pipeline outputs)

# Run full suite:
pytest tests/ -v --tb=short

# Code quality:
ruff check tests/
mypy tests/ --ignore-missing-imports
```

Expected output: All Layer 0 and edge case tests pass without MODFLOW dependency. Conservation tests pass if pipeline has been run for the target year. Total: ~240 tests.

---

## 8. Known Gotchas

- [ ] **conftest.py fixtures must not depend on MODFLOW outputs.** Layer 0 and 0.5 tests must run on any machine without pipeline execution. Use mock data and tmp_path fixtures.
- [ ] **Conservation tests (Layer 1) require `output/modflow/{year}/` to exist.** These tests are skipped gracefully if pipeline outputs are missing. Use `pytest.importorskip` or `skipIf` patterns.
- [ ] **The `pytestmark = pytest.mark.layer0` module-level marker applies to ALL tests in a file.** Do not mix markers within a single file -- use separate files for each layer.
- [ ] **`step1_ingest_buckman_data.py` is in project root, not `src/`.** Import paths must account for this: `import step1_ingest_buckman_data` (not `from src import ...`).
- [ ] **Edge case tests that create temporary files must use `tmp_path` fixture** to avoid polluting the working directory.
- [ ] **The test_conservation.py module doubles as a standalone script** (`python tests/test_conservation.py --year 2024`) and a pytest module. Both entry points must work.
- [ ] **Well numbers are 1-indexed (1-13), not 0-indexed.** All well iteration should use `range(1, 14)`.

---

## 9. Year-Chaining Behavior

Not directly applicable to tests, but test fixtures should cover chaining scenarios:

| Data Element | Test Fixture Approach |
|-------------|----------------------|
| Table 3 historical | Mock XLSX with 3 years of data |
| Table 5 cumulative | Use LA_CIENEGA_CUMULATIVE dict values directly |
| Prior year outputs | Create minimal fixtures in tmp_path |

---

## 10. Verification

Single command to confirm the test suite works end-to-end:

```bash
pytest tests/ -v --tb=short -m "layer0 or edge_cases" 2>&1 | tail -5
```

Expected result: `~170 passed` with no failures. Conservation tests are separate because they require pipeline outputs.

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-02 | Unit conversion factors used in hand-calculated test values |
| DS-03 | Cell geometry constants verified by test_modflow_geometry |
| IS-03 | step1_ingest_buckman_data.py -- target of test_ingest_buckman_data |
| IS-05 | step2_update_modflow.py -- target of test_update_modflow |
| IS-07 | stream_depletions.py -- target of test_stream_depletions |
| IS-09 | Tables 4 & 5 generation -- tested by test_stream_depletions |
| IS-11 | Validation framework consumes test results from this suite |

---

## Appendix: Test Distribution by File

| File | Layer | Est. Tests | Key Focus Areas |
|------|-------|-----------|-----------------|
| `test_ingest_buckman_data.py` | 0 | ~20 | Constants, CSV parsing, validation flags, MG-to-AF |
| `test_update_modflow.py` | 0 | ~67 | AF-to-ft3/s, WEL parsing, well entries, leap year |
| `test_stream_depletions.py` | 0 | ~71 | CFS conversion, Core 2003, parsing, Tables 3-5 data |
| `test_generate_depletion_tables.py` | 0 | ~32 | Step 4 orchestrator, constants, print_error |
| `test_conservation.py` | 1 | ~4 | Budget closure, pumping conservation, depletion bounds (many helpers) |
| `test_edge_cases.py` | 0.5 | ~30 | Missing files, zero pumping, leap year, NaN, CRLF |
| `test_modflow_geometry.py` | 0 | ~16 | GHB parsing, Otowi cells, FORTRAN rectangle |
| **Total** | | **~240** | |

### Marker Configuration (pytest.ini)

```ini
[pytest]
markers =
    layer0: Layer 0 smoke tests (fast, no MODFLOW dependency)
    edge_cases: Layer 0.5 edge case and boundary condition tests
    conservation: Layer 1 conservation and mass-balance checks (requires pipeline outputs)
```
