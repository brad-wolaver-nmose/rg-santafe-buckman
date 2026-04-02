# Session Summary: Appendix A V&V Review
**Date:** 2026-04-02
**Report:** `docs/reporting/MSC_2026_XXX_Buckman Depletions 2025_2026 03 31_lhp_bdw.docx` — Appendix A
**Model:** Claude Opus 4.6 (1M context)

---

## What We Did

### 1. Reviewed Appendix A Introduction (Section 1)
Identified 11 issues across typos, scientific accuracy, claims not matching code, and structural problems. Key findings:
- "constans.py" typo (still present from 4/1 session)
- "entrieds" typo
- Duplicate "And" in bullet list
- Second verification sub-bullet conflated verification with validation (per Anderson & Woessner 2002)
- "Identical historical year" check claimed but not implemented in code
- Depletion constraint tolerance described as "0.1%" but implementation is 0.001 ratio units
- Semicolon error ("However;")
- Incomplete/orphaned "Validation" line
- Prior-year results called "independent observations" (they're prior pipeline outputs)
- Regression test listed under Validation (could be Verification) — decided to keep under Validation

### 2. Drafted Revised Wording for Multiple Sections

**V&V definitions (groundwater modeling sense):**
- Merged two verification sub-bullets into one to avoid conflating verification and validation
- Aligned with Anderson & Woessner (2002) definitions

**"Identical historical year" claim:**
- Three options provided (A: reword to match regression test, B: flag as design property, C: implement the test)
- Recommended Option A — explains frozen MODFLOW inputs guarantee identical values by construction

**MODFLOW Numerical Integrity (Section 3):**
- Changed from hard stop to soft target per reviewer comment and Brad's notes
- Added tiered tolerance: 0.1% target, 1.0% acceptable, >1.0% for a few stress periods requires analyst judgment
- Added explanation of why 0.1% is achievable: superposition model has simpler water budget than elevation-based models
- Softened "should not be used" → "should be reviewed before use in regulatory reporting"

**Table 5 (La Cienega Springs) cross-check columns:**
- Rewrote to clarify Column B is total model-predicted impact (not a running sum of annual depletions)
- Explained cross-check columns C/D/E appear in Excel but not in the memo
- Added audit mechanism sentence (reviewer can verify with Excel)

**2024 Regression section (Part II):**
- Added back-reference "(as defined in Section 1)" for Validation heading
- Replaced "any code modification must reproduce" with explanation of what kinds of changes could break results (bug fixes, reorganization, library updates)

**Tolerance table:**
- Reviewer asked why tolerances differ across tables
- Tested uniform 0.01 ac-ft / 0.1% across all 5 tables — all 2,889 cells pass
- Updated `validation/2024/tolerances.yaml` to uniform values
- Drafted integrated paragraph replacing per-table tolerance table

**Multi-year envelope:**
- Rewrote to define "coefficient of variation" in plain English on first use
- Explained the two-threshold logic (20% floor + 1.5×CV scaling)
- Stated n=3 limitation explicitly with the t-distribution context

**Depletion-to-pumping ratio:**
- Confirmed ratio uses Rio Pojoaque-Nambe + Rio Tesuque only (Table 3), not Table 4 or Table 5
- Confirmed "varies inversely" is physically correct (high pumping → low ratio due to lagged response)
- Corrected "Tables 3 and 4" → "Table 3"
- Explained La Cienega exclusion (~0.15 ac-ft/yr negligible)

---

## Decisions Made

| Decision | Details |
|----------|---------|
| V&V definitions | Merge two verification bullets into one; align with A&W 2002 |
| Identical year check | Reword to explain frozen inputs guarantee identity by construction (Option A) |
| MODFLOW convergence | Soft target, not hard stop; tiered 0.1% / 1.0% / analyst review |
| Table 5 wording | "total model-predicted reduction" not "running sum of annual depletions" |
| Regression test placement | Keep under Validation (prior-year results are accepted reference values) |
| Regression tolerance | Uniform 0.01 ac-ft / 0.1% for all tables (tested, passes) |
| "Code modification" language | Explain types of changes (bug fixes, reorganization, library updates) |
| Ratio streams | Table 3 only (Pojoaque-Nambe + Tesuque); La Cienega excluded |
| Inversely vs directly | Inversely confirmed (high pumping → low ratio due to lagged depletion response) |

---

## Code Changes Made

**File:** `validation/2024/tolerances.yaml` — Unified all per-table tolerances:

| Table | Previous Abs | Previous Rel | New Abs | New Rel |
|-------|-------------|-------------|---------|---------|
| Table 1 | 0.01 | 0.1% | 0.01 | 0.1% |
| Table 2 | 0.01 | 0.1% | 0.01 | 0.1% |
| Table 3 | 0.001 | 0.1% | 0.01 | 0.1% |
| Table 4 | 0.1 | 1% | 0.01 | 0.1% |
| Table 5 | 0.01 | 0.5% | 0.01 | 0.1% |

Regression test confirmed: all 2,889 cells pass at tighter uniform tolerances.

---

## What's Still Unresolved

### From this session
- **MODFLOW convergence code:** Text now says soft target, but code may still implement as hard stop — needs verification and possible code change (similar to depletion constraint soft flag change from 4/1)
- **Multi-year envelope wording:** Revised text drafted but not yet confirmed by Brad
- **"Identical historical year" wording:** Option A recommended, not yet confirmed

### Carried from prior sessions (2026-04-01, 2026-04-02)
1. Step 3 platform requirements paragraph — text drafted, not in DOCX
2. "Drift" → "remain fixed and reproducible" + regression test sentence
3. Regression testing "why would code break" explanation
4. Spot-check table revision (two conversion paths + explanatory text)
5. Table 4 paragraph simplification
6. Corrected depletion constraint text (annual check, now soft flag)
7. Geometry checks table row (4 options provided, none selected yet)
8. All typos/errors from initial scan (12 items)
9. **Barroll and Keyes (2005) vs (2025):** Which is the correct citation year?
10. **Spot-check table format:** Not confirmed
11. **git push --force-with-lease:** Currently denied by prefix match

### Code changes not yet committed
- `tests/test_conservation.py` — depletion constraint hard→soft flag (from 4/1)
- `validation/2024/tolerances.yaml` — uniform tolerances (this session)

---

## Context for Fresh Conversation

**Who:** Brad Wolaver, Senior Hydrologist at NMOSE Hydrology Bureau. Reviewing draft 2025 Buckman depletion memo (MSC_2026_XXX) before submission to Water Rights Division and ISC. A reviewer ("lhp") has provided comments.

**Claude's role:** Senior USGS research-grade groundwater modeler with deep Python fluency and expert report editing skills.

**Working mode:**
- Text suggestions only — do NOT edit the DOCX unless explicitly told
- Plan-first workflow for multi-step tasks (see project CLAUDE.md)
- Clarification protocol: ask A–E multiple-choice questions when prompt is ambiguous

**What happened across sessions:**
1. **2026-04-01:** Full report review — 12 issues found, text suggestions drafted for 9 items, depletion constraint softened in code (uncommitted), reviewer comments addressed
2. **2026-04-02 (setup):** Role assignment, clarification protocol added
3. **2026-04-02 (this session):** Appendix A V&V review — 11 issues in intro, revised wording for 8 sections, unified regression tolerances in code, confirmed ratio physics and stream scope

**Key files:**
- Report: `docs/reporting/MSC_2026_XXX_Buckman Depletions 2025_2026 03 31_lhp_bdw.docx`
- Session notes: `docs/dreams/2026-04-01_report_review_session.md`, `docs/dreams/2026-04-02_session_setup.md`, `docs/dreams/2026-04-02_appendix_a_review.md`
- Regression tolerances: `validation/2024/tolerances.yaml` (modified this session)
- Regression test: `validation/2024/run_regression_2024.py`
- Temporal consistency: `validation/temporal_consistency.py`
- Ballpark checks: `validation/ballpark_check.py`
- Depletion constraint: `tests/test_conservation.py` (lines 560-664)
- Table 5 generation: `stream_depletions.py` (lines 1821-2015)
- Constants: `src/constants.py`
- Bounds config: `validation/historical/bounds.yaml`
