# Buckman Wellfield Test Framework

This document describes the multi-layer verification framework for the Buckman wellfield depletion pipeline. The framework ensures computational accuracy and physics compliance for regulatory reporting.

## Quick Start

```bash
# Run full test suite
python run_all_tests.py --year 2024

# Run with verbose output
python run_all_tests.py --year 2024 --verbose

# Dry run (show what would execute)
python run_all_tests.py --year 2024 --dry-run
```

## Test Layers

| Layer | Purpose | Type | Marker | Timeout |
|-------|---------|------|--------|---------|
| **Ballpark** | Fast sanity check | Hard fail | N/A | 30s |
| **Layer 0** | Smoke tests - does code run? | Hard fail | `layer0` | 300s |
| **Layer 0.5** | Edge cases - bad input handling | Hard fail | `edge_cases` | 120s |
| **Layer 1** | Conservation - mass balance | Hard fail | `conservation` | 120s |
| **Layer 2** | Temporal - year-over-year | Flags only | N/A | 60s |
| **Layer 5** | Regression - 2024 baseline | Standalone | N/A | ~45min |
| **Layer 6** | Provenance manifest | Generated | N/A | 60s |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All hard-stop tests passed (flags may exist) |
| 1 | Hard-stop test failure OR script error |
| 3 | Ballpark check critical failure (physics violation) |

## Running Individual Layers

```bash
# Layer 0 (smoke tests)
pytest -m layer0 -v

# Layer 0.5 (edge cases)
pytest -m edge_cases -v

# Layer 1 (conservation)
pytest -m conservation -v

# Layer 2 (temporal)
python validation/temporal_consistency.py --year 2024

# Ballpark check only
python validation/ballpark_check.py --year 2024
```

## Layer 1 Prerequisites

Layer 1 (conservation) requires pipeline outputs to exist. If you see:
```
Layer 1 (conservation) SKIPPED: pipeline outputs not found
```

Run the full pipeline first:
```bash
python step1_ingest_buckman_data.py --year 2024
python step2_update_modflow.py --year 2024
./step3_run_modflow.sh --year 2024
python step4_generate_depletion_tables.py --year 2024
```

## First Year After Baseline (2025+)

The first year after baseline establishment (2025) will likely produce **flags on all Layer 2 checks**. This is **expected and normal**.

**Why:** Layer 2 compares against historical patterns (2022-2024). 2025 has no prior year in the baseline to compare against.

**What to do:**
1. Review the flags manually
2. If values are reasonable, document review in FLAG_REGISTER
3. After verification, add 2025 to baseline (update bounds.yaml)

## Regression Harness (Layer 5)

```bash
python validation/2024/run_regression_2024.py
```

**When to run:**
- Before deploying pipeline code changes (any .py file)
- Before deploying config changes (bounds.yaml, tolerances.yaml)
- When something seems wrong and you want to verify baseline

**Runtime:** ~45 minutes (runs full MODFLOW model)

## What to Do When Tests Fail

### Hard Fail (exit 1 or 3)

1. **DO NOT use outputs for compliance reporting**
2. Read the error message - it explains what failed
3. Check the specific value vs. expected value
4. Fix the underlying issue
5. Re-run tests

### Flags (Layer 2 temporal checks)

1. Flags do NOT block output use
2. Review each flag in the manifest
3. Document your review decision:
   - Open `output/manifests/buckman_manifest_{year}.json`
   - Find the `flag_register` section
   - Fill in `disposition`, `reviewed_by`, `review_date`
4. Flags require analyst sign-off before finalizing report

## Flag Review Workflow

When Layer 2 produces flags:

1. Open the manifest: `output/manifests/buckman_manifest_{year}.json`
2. Find the `flag_register` section
3. For each flag, document:
   ```json
   {
     "flag_id": "yoy_pumping_change",
     "disposition": "ACCEPTED - Drought year caused reduced pumping",
     "reviewed_by": "J. Smith",
     "review_date": "2026-02-17"
   }
   ```
4. Save the manifest (this is your audit trail)

## Manifest Location

```
output/manifests/buckman_manifest_{year}.json
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
- name: Run verification tests
  run: python run_all_tests.py --year ${{ env.YEAR }}

- name: Upload manifest artifact
  uses: actions/upload-artifact@v3
  with:
    name: verification-manifest
    path: output/manifests/buckman_manifest_*.json

- name: Upload test results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: output/test_results/*.json
```

Exit codes in CI:
- Exit 0: Proceed with deployment
- Exit 1: Block deployment, review failures
- Exit 3: Block deployment, critical issue

## Test Statistics

- **Layer 0:** ~188 smoke tests
- **Layer 0.5:** 30 edge case tests
- **Layer 1:** 4 conservation checks
- **Layer 2:** 4 temporal checks (flags)
- **Total runtime:** <60 seconds (excluding regression harness)

## Adding New Tests

### Layer 0 (Smoke)
Add `pytestmark = pytest.mark.layer0` to your test file, or decorate individual tests:
```python
@pytest.mark.layer0
def test_new_feature():
    pass
```

### Layer 0.5 (Edge Cases)
Add tests to `tests/test_edge_cases.py` or create new file with:
```python
pytestmark = pytest.mark.edge_cases
```

### Layer 1 (Conservation)
Add tests to `tests/test_conservation.py` with:
```python
pytestmark = pytest.mark.conservation
```

## Dependencies

```bash
pip install pytest-json-report
```

## Troubleshooting

### "pytest-json-report not installed"
```bash
pip install pytest-json-report
```

### "ModuleNotFoundError: No module named 'step1_ingest_buckman_data'"
Run tests from the project root directory:
```bash
cd /path/to/buckman
python run_all_tests.py --year 2024
```

### Tests timing out
- Check for infinite loops
- Check for file locking issues
- Increase timeout in run_all_tests.py if needed (not recommended)

### Layer 1 always skipping
Run the pipeline first to generate outputs:
```bash
python step1_ingest_buckman_data.py --year 2024
# ... etc
```
