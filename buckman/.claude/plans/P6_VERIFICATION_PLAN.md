# P6: Layer 3 Cross-Comparison Checks

## Status: NOT IMPLEMENTED - Scientifically Inapplicable

**Decision Date:** 2026-02-17
**Reviewed By:** Project team during P6 planning

---

## Original Proposal

The original 8-prompt testing framework proposed Layer 3 cross-comparison checks that would validate Buckman Wellfield depletion results against external data sources:

1. **Municipal Demand Cross-Check:** Compare Buckman pumping to City of Santa Fe total water production
2. **USGS Gage Cross-Check:** Compare modeled depletion direction against observed streamflow anomalies

---

## Why This Layer Was Not Implemented

Upon scientific review, both proposed checks were determined to be **inapplicable to this system**:

### Municipal Demand Ratio Check

**Problem:** This check does not validate model correctness.

The ratio of Buckman pumping to total City water production varies based on:
- Drought conditions and water supply availability
- Policy decisions on source allocation
- Infrastructure capacity and maintenance schedules
- Seasonal demand patterns

A ratio outside historical bounds indicates operational changes, not model errors. This is contextual metadata, not a cross-validation of depletion calculations.

### USGS Gage Consistency Check

**Problem:** Signal-to-noise ratio makes this check physically meaningless.

- Rio Grande flows at Otowi Bridge: ~500-1500 cfs (highly variable)
- Buckman stream depletions: ~1-2 cfs cumulative (developed over decades)
- USGS measurement uncertainty: typically ±5-10%

The modeled depletions are 2-3 orders of magnitude smaller than natural streamflow variability, upstream reservoir operations, and measurement error. Detecting Buckman's impact in real-time gage data is not physically possible.

---

## What Provides Adequate Validation Instead

The existing verification layers adequately cover model validation:

| Layer | Purpose | Status |
|-------|---------|--------|
| Layer 0 (Smoke) | Code executes without errors | IMPLEMENTED |
| Layer 1 (Conservation) | Mass balance, physics constraints | IMPLEMENTED |
| Layer 2 (Temporal) | Year-over-year consistency | PLANNED (P5) |
| Layer 5 (Regression) | Match known-good 2024 baseline | IMPLEMENTED |
| Layer 6 (Provenance) | Audit trail and reproducibility | IMPLEMENTED |

**Key insight:** Layer 5 regression testing against a verified 2024 baseline provides the primary validation. If outputs match known-good results, the model is working correctly. External cross-comparison adds no meaningful verification for this system.

---

## Conclusion

Layer 3 cross-comparison checks are **not applicable** to the Buckman Wellfield depletion model due to fundamental signal-to-noise limitations. No implementation was performed.

This document serves as the record that the approach was evaluated and rejected on scientific grounds, not overlooked.

---

## Files Created/Modified

None. No code was written for Layer 3.
