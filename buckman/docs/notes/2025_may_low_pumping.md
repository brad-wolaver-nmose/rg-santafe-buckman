# May 2025 Low Pumping — Operational Explanation

**Date of note:** 2026-02-25
**Prepared by:** Brad Wolaver

---

## Observation

May 2025 Buckman Wellfield pumping was anomalously low: **4.05 AF** total,
compared to April 2025 (139.31 AF) and June 2025 (76.83 AF). This represented
a ~97% reduction from the prior month.

## Explanation

Per personal communication (email) with **Chris Helvey, City of Santa Fe Public Works**
(chelvey@santafenm.gov) on 2025-02-25:

- Snowpack was above normal in spring 2025, providing good local surface water supply
  via the Santa Fe River.
- The City used **Rio Grande water via Buckman Direct Diversion (BDD)** as the primary
  supply source during May 2025.
- As a result, the Buckman Wellfield was **hardly pumped** during May 2025.

## Disposition

The near-zero May 2025 pumping values in `Buckman_Well_Prod_2025.csv` are **correct
as reported**. No correction or imputation is needed. The data accurately reflects
actual operational conditions.

The seasonal pattern FLAG raised by `validation/temporal_consistency.py` (Layer 2,
r=0.546) for 2025 is resolved by this explanation — it reflects a legitimate operational
shift, not a data error or stress-period misalignment.

## Reference

> Chris Helvey, City of Santa Fe Public Works, personal communication via email,
> 2026-02-25.
