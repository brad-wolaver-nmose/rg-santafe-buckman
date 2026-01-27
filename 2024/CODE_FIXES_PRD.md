# Code Fixes PRD

**Generated from:** REVIEW_FINDINGS.md
**Generated on:** 2026-01-27
**Source file:** ingest_buckman_data.py

---

## Introduction

This PRD contains fixes for issues identified during code review. Each user story addresses a specific finding from REVIEW_FINDINGS.md.

**Review Status Note:** The code review (US-R01 through US-R37) is complete with 2 partial findings identified. Sections US-R38 through US-R49 were not yet executed. Fixes below address the documented partial findings only.

---

## Summary of Findings

| Finding | Severity | Issue |
|---------|----------|-------|
| US-R25 | Low | `extract_date_from_pdf()` error handler missing traceback |
| US-R32 | Low-Medium | `validate_and_prepare_pdfs()` shutil.copy2() not wrapped in try/except |

---

## User Stories

### US-F01: [LOW] Add Traceback to extract_date_from_pdf Error Handler

**Description:** As a developer debugging OCR issues, I need to see the abbreviated traceback in `extract_date_from_pdf()` error messages so that I can quickly identify the source of failures, consistent with the pattern used in `pdf_to_image()`.

**Finding reference:** REVIEW_FINDINGS.md US-R25

**Current behavior (lines 358-362):**
```python
except Exception as e:
    print(f"Error extracting date from PDF:")
    print(f"  Exception type: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    return (0, "NOT_OK", "NOT_OK", "NOT_OK")
```

**Required behavior:** Add abbreviated traceback (last 4 lines = last 2 frames) matching the pattern in `pdf_to_image()` (lines 258-262).

**Acceptance Criteria:**
- [ ] Error handler prints traceback using `traceback.format_exc().strip().split('\n')[-4:]`
- [ ] Output format matches pdf_to_image(): `"  Traceback (last 2 frames):"` header followed by indented traceback lines
- [ ] Traceback import already exists at line 7, no new imports needed
- [ ] mypy passes with zero errors
- [ ] Function still returns `(0, "NOT_OK", "NOT_OK", "NOT_OK")` on error

---

### US-F02: [LOW-MEDIUM] Add Try/Except Around shutil.copy2 in validate_and_prepare_pdfs

**Description:** As a user running the validation step, I need file copy errors (disk full, permission denied, file locked) to be handled gracefully so that one failed copy doesn't crash the entire validation process.

**Finding reference:** REVIEW_FINDINGS.md US-R32

**Current behavior (lines 1466-1467):**
```python
if original_path != standard_path:
    shutil.copy2(original_path, standard_path)
```

**Required behavior:** Wrap `shutil.copy2()` in try/except, log the error with filename and exception details, and continue processing remaining files.

**Acceptance Criteria:**
- [ ] shutil.copy2() wrapped in try/except catching OSError (covers permission, disk space, etc.)
- [ ] Error message includes: original filename, standard filename, exception type, exception message
- [ ] Copy failure is tracked in report (e.g., add to a "copy_errors" list or increment error count)
- [ ] Function continues processing remaining months after a copy failure
- [ ] mypy passes with zero errors
- [ ] Pre-flight report shows copy errors to user before they decide to proceed

---

## Optional Improvements (Not Required)

The following items were identified as potential improvements but are **not required fixes**:

1. **Temp file cleanup on exception (US-R31 note):** If an exception occurs between temp file creation and shutil.move, the temp file is not cleaned up. Minor issue since it's in output_dir with .csv suffix. Could add `try/finally` pattern if desired.

---

## Completion Criteria

When all required fixes are complete:
1. Both user stories marked complete
2. `mypy ingest_buckman_data.py` returns 0 errors
3. `python3 -m py_compile ingest_buckman_data.py` succeeds

Output: <promise>COMPLETE</promise>
