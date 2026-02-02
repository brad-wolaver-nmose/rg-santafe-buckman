# Smoke Test Scaffolding (Python Projects)

For Python projects, create a basic smoke test file alongside the PRD. These tests verify code RUNS—they don't verify calculations are correct (that's the domain expert's job).

### Why Smoke Tests Matter

Ralph uses pytest to verify each task before marking it complete. Without test files:
- Ralph falls back to syntax checking only (py_compile)
- Runtime errors won't be caught until manual testing
- The iterate-until-pass loop has no safety net

### What Smoke Tests Check

| Test Type | What It Catches |
|-----------|-----------------|
| Import test | Syntax errors, missing dependencies |
| Function exists test | Claude renamed or deleted something |
| Runs without error test | Runtime crashes on basic input |
| Basic sanity test | Output is completely wrong magnitude |

### What Smoke Tests DON'T Check

- **Calculation correctness** — You verify the hydrology/science
- **Edge cases** — These are minimal viability tests
- **Integration** — Tests run functions in isolation

### When to Create Smoke Tests

Create a `tests/test_<module>.py` file for each Python module that will be created. Match the module structure from your user stories.

**Example:** If US-001 creates `discharge_calc.py`, also create `tests/test_discharge_calc.py`

### Smoke Test Template

```python
"""
Smoke tests for [module_name].
Verifies code RUNS - domain expert must verify calculations independently.

These tests support the Ralph iterate-until-pass loop.
They catch mechanical failures, not logical errors.
"""
import pytest


def test_module_imports():
    """Verify module imports without syntax errors."""
    import module_name  # Replace with actual module name


def test_main_function_exists():
    """Verify expected function exists and is callable."""
    from module_name import main_function  # Replace with actual names
    assert callable(main_function)


def test_runs_without_error():
    """Verify function executes with basic inputs without crashing."""
    from module_name import main_function

    # Use simple, realistic inputs - not edge cases
    result = main_function(simple_input)

    # Just verify it returns SOMETHING of the right type
    assert result is not None
    assert isinstance(result, (int, float, list, dict))  # Adjust expected type


def test_basic_sanity():
    """
    Verify output is in reasonable range for known input.

    This is NOT a precision test. It catches order-of-magnitude errors
    like returning 0 when it should return 1000, or vice versa.
    """
    from module_name import main_function

    # Use input where you know the APPROXIMATE output
    result = main_function(known_input)

    # Wide bounds - just catching catastrophic errors
    # Example: if calculating discharge around 50 cfs, bounds might be 1-500
    assert lower_bound < result < upper_bound, \
        f"Result {result} outside expected range [{lower_bound}, {upper_bound}]"
```

### Adapting the Template

When generating test files:

1. **Replace placeholders** with actual module/function names from user stories
2. **Choose realistic simple inputs** based on the domain (e.g., typical stream measurements)
3. **Set wide sanity bounds** — these catch "completely broken," not "slightly off"
4. **Match return types** to what the function actually returns

### Test File Naming

| Module | Test File |
|--------|-----------|
| `discharge_calc.py` | `test_discharge_calc.py` |
| `data_validator.py` | `test_data_validator.py` |
| `report_generator.py` | `test_report_generator.py` |

### Placement in PRD Workflow

1. Generate PRD with user stories
2. Identify which user stories create new Python modules
3. Create corresponding `test_<module>.py` files with smoke tests
4. Save all files before finishing
