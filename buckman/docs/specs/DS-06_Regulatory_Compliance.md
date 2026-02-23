# DS-06: Regulatory & Compliance Context

> **Tier 1 Domain Specification** -- Captures scientific basis, assumptions, and domain knowledge for a hydrologist audience. Reusable across projects. A reader with groundwater modeling background can understand the system without seeing code.

**Status:** Final
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Purpose & Scope

This specification documents the regulatory framework within which the Buckman Wellfield depletion pipeline operates. The pipeline produces deliverables for the New Mexico Office of the State Engineer (OSE) that directly affect interstate water compact accounting. Understanding the regulatory context is essential because it dictates precision requirements, audit trail standards, and the consequences of errors.

The Buckman Wellfield serves the City of Santa Fe's municipal water supply. Pumping from the wellfield depletes surface water flows in the Rio Grande system, and these depletions are chargeable against New Mexico's delivery obligations under the Rio Grande Compact. The pipeline quantifies these depletions annually and produces 5 Excel tables that are copy-pasted into the official OSE report.

---

## 2. Scientific Basis

### 2.1 The Rio Grande Compact (1938)

The Rio Grande Compact allocates water from the Rio Grande among Colorado, New Mexico, and Texas. Key provisions affecting this pipeline:

- **Otowi Gage** (USGS 08313000) is the accounting point for New Mexico's deliveries to Texas
- Water depletions that occur **below Otowi** are chargeable against New Mexico's delivery obligation
- Water depletions that occur **above Otowi** do not directly affect Compact accounting (but are still reported)
- New Mexico's approximate annual allocation is ~405,000 AF/year (varies with upstream supply)

The Buckman Wellfield lies below Otowi Bridge. Groundwater pumping at Buckman creates stream depletions in:
- The Rio Grande itself (both above and below Otowi, due to aquifer geometry)
- Tributary streams (Rio Pojoaque-Nambe, Rio Tesuque)
- Springs (La Cienega Springs)

All of these depletions must be quantified and reported annually.

### 2.2 Depletion Accounting Framework

The total depletion from Buckman pumping is partitioned into components reported in separate tables:

```
Total Depletion = Table 3 (Tributaries) + Table 4 (Rio Grande) + Table 5 (Springs)

Where:
  Table 3: Rio Pojoaque-Nambe + Rio Tesuque (cumulative AF)
  Table 4: Above Otowi + Below Otowi (annual AF, monthly detail)
  Table 5: La Cienega Springs (cumulative AF)

Compact-chargeable depletions = Table 4 (Below Otowi) + portions of Tables 3 and 5
```

### 2.3 Superposition + Analytical Residual Framework

Stream depletions are calculated using a two-component approach:

**Component 1: MODFLOW Superposition (1988--present)**

The MODFLOW96 model simulates aquifer response to pumping from 1988 through the current year using the principle of superposition. The model calculates how much stream flow is reduced by each year's pumping.

**Component 2: Analytical Residuals (pre-1988)**

Buckman wellfield pumping began in 1972. The MODFLOW superposition model only covers 1988--present. The effects of 1972--1987 pumping continue to propagate through the aquifer as "residual" depletions. These are calculated using Core (2003) analytical projections extending Spinks (1988) through approximately 2050.

For Table 3, each stream's total impact is:

```
Total Impact = Residual (Core 2003) + Superposition (MODFLOW)

Note: Pojoaque residual exhausted in 2015 (projected to zero by Core 2003)
      Tesuque residual continues through ~2050
```

### 2.4 Worked Example: Compact Impact

**2024 Buckman Wellfield Impact on Compact Accounting:**

```
Total pumping:              1,372.90 AF
Below Otowi depletion:        842.94 AF (Table 4)
Above Otowi depletion:        101.43 AF (Table 4)
Pojoaque depletion:            60.80 AF (Table 3, cumulative)
Tesuque depletion:             33.58 AF (Table 3, cumulative)
La Cienega cumulative:          3.74 AF (Table 5, cumulative since 2004)

Compact-chargeable (Table 4 Below):  842.94 AF
As fraction of NM allocation:        842.94 / 405,000 = 0.21%

Physical interpretation:
  For every 1 AF pumped at Buckman, approximately 0.61 AF depletes
  the Rio Grande below Otowi (842.94 / 1,372.90 = 0.614).
  The remainder affects tributaries, above-Otowi reaches, and springs.
```

---

## 3. Assumptions

| # | Assumption | Justification | Risk if Wrong | Mitigation |
|---|-----------|---------------|---------------|------------|
| 1 | OSE report tables are copy-pasted directly from pipeline output | Current workflow; tables must match exact format | Format changes require pipeline update | Template-based Excel generation with validation against prior years |
| 2 | MODFLOW superposition is valid for Buckman aquifer system | Tested against 2003 aquifer test data; linear response confirmed | Non-linear effects underestimated in high-pumping years | Depletion/pumping ratio monitored in bounds.yaml (0.069--0.108) |
| 3 | Core (2003) analytical residuals remain valid | Projection based on 1988 aquifer properties; no new calibration data | Residuals over/underestimated | Pojoaque residual already exhausted (2015); Tesuque residual is small and declining |
| 4 | Pipeline outputs must withstand legal challenge | Rio Grande Compact disputes are adjudicated in federal court | Inadequate documentation undermines credibility | Provenance logging (Layer 6) documents every input, code version, and test result |
| 5 | Precision requirements match OSE reporting conventions | Tables 1-2: 2 decimal places; Table 3: 3 decimal places; Tables 4-5: 2 decimal places | Rounding differences vs. OSE expectations | Tolerances defined per table in tolerances.yaml |
| 6 | Annual reporting cycle: one report per calendar year | OSE requires annual depletion report for compact accounting | Multi-year processing gap requires sequential catch-up | Year chaining (DS-04) supports sequential processing of any year |

---

## 4. Data Sources & Provenance

| Source | Description | Access Method | Update Frequency | QC Procedure |
|--------|-------------|---------------|------------------|--------------|
| City of Santa Fe pumping records | Daily MGD by well (CSV) | Annual delivery from City | Annual | Three-tier validation (noise, info, error thresholds) |
| MODFLOW96 executable | USGS MODFLOW-96 groundwater flow model | Static binary (1996 release) | Never | SHA-256 hash verification |
| sfmodflx_2245.exe | Fortran stream depletion post-processor | Static binary (custom for Buckman) | Never | SHA-256 hash verification |
| Core (2003) analytical residuals | Pre-1988 pumping depletion projections | Hardcoded in stream_depletions.py | Never (fixed projection) | Values from published report |
| Prior-year OSE reports | Historical pumping and depletion tables | PDF files in docs/reports_prior_year/ | Annual archive | Manual cross-check during Table 1 chaining |

---

## 5. Key Constants & Conversions

| Constant | Value | Units | Derivation | Source |
|----------|-------|-------|------------|--------|
| NM Compact allocation | ~405,000 | AF/year | Approximate (varies with upstream supply) | Rio Grande Compact (1938) |
| 1 MG to AF | 3.06889 | AF/MG | 1,000,000 gal / 325,851 gal/AF | USGS definition |
| 1 AF to ft^3 | 43,560 | ft^3/AF | 1 acre x 1 ft | USGS definition |
| cfs to AF/day | 1.9835 | AF/day/cfs | 86,400 s/day / 43,560 ft^3/AF | Unit conversion |

### Regulatory Precision Requirements

| Table | Content | Precision | Physical Basis |
|-------|---------|-----------|---------------|
| Table 1 | Annual pumping by well | 2 decimal places (AF) | Well meter accuracy (~1%) |
| Table 2 | Monthly pumping by well | 2 decimal places (AF) | Aggregated from daily readings |
| Table 3 | Tributary depletions | 3 decimal places (AF) | MODFLOW precision at stream cells |
| Table 4 | Rio Grande depletions | 2 decimal places (AF) | Aggregated from monthly values |
| Table 5 | La Cienega cumulative | 2 decimal places (AF) | Small values require resolution |

---

## 6. Domain-Specific Constraints

### 6.1 The Five Report Tables

Each table serves a specific regulatory purpose. Together they document the complete impact of Buckman pumping on the Rio Grande system.

#### Table 1: Historical Annual Pumping by Well (AF/year)

**Purpose:** Trend analysis. Shows whether total extraction is increasing, decreasing, or stable over the 1988--present record. Allows regulators to identify changes in pumping patterns.

**Structure:** Rows = years (1988--present), Columns = wells (B1 through B13) + Total + Rank.

**Regulatory significance:** Establishes the factual basis for how much water was extracted. Pumping data comes from City of Santa Fe production records.

#### Table 2: Monthly Pumping Detail for Current Year (AF/month)

**Purpose:** Seasonal pattern documentation. Shows how pumping varies through the year, reflecting municipal demand cycles (low winter, high summer).

**Structure:** Rows = wells (B1 through B13) + Total, Columns = months (JAN--DEC) + Annual Total.

**Regulatory significance:** Monthly resolution is required because MODFLOW stress periods are monthly. This table provides the pumping rates used in the model.

#### Table 3: Tributary Stream Depletions (Cumulative AF)

**Purpose:** Quantifies cumulative impact on Rio Pojoaque-Nambe and Rio Tesuque from Buckman pumping since 1988.

**Structure:** Rows = years (1988--present), Columns = Residual Impact, Superposition Impact, Total Impact for each stream.

**Regulatory significance:** Tributary depletions reduce flow available to downstream users and may affect junior water rights. Values are cumulative and generally increasing, though strict monotonicity is not guaranteed by physics -- it depends on whether new superposition gains exceed residual losses. For example, the Residual Impact column for Pojoaque decreases from 40.432 AF in 1988 to 0 AF after 2015 as the Core (2003) analytical projection exhausts.

#### Table 4: Rio Grande Above/Below Otowi (AF)

**Purpose:** Compact accounting. Separates depletions above and below the Otowi Gage for Rio Grande Compact bookkeeping.

**Structure:** Cell-level monthly detail + summary rows for Above Otowi and Below Otowi. Below Otowi total is the Compact-chargeable depletion.

**Regulatory significance:** This is the most Compact-critical table. Below Otowi depletions are debited against New Mexico's delivery obligation to Texas.

#### Table 5: La Cienega Springs Cumulative Depletions (AF)

**Purpose:** Track impact on La Cienega Springs, located approximately 15 km south of the wellfield.

**Structure:** Rows = years (2004--2030), Column = cumulative depletion (AF).

**Regulatory significance:** Spring impacts were first calculated in 2005 (Barroll & Keyes). Values are small (3--4 AF cumulative through 2024) but monitored because springs have ecological and cultural significance.

### 6.2 Provenance Chain-of-Custody

The pipeline produces a provenance manifest (JSON) that documents the complete chain of custody from raw input to report table. This is designed for auditability in regulatory and legal settings.

#### Input Manifest

For every input file consumed by the pipeline:
- File name and full path
- SHA-256 cryptographic hash (proves file has not been altered)
- File size in bytes
- Row count (for CSV/Excel files)
- Date range of data (for pumping records)
- Source system identification

**Purpose:** Proves which specific data went into the calculation. If a dispute arises over whether the correct pumping data was used, the hash proves it.

#### Pipeline Manifest

For the software that produced the results:
- Git commit hash (exact code version)
- Git working tree status (clean vs. dirty -- uncommitted changes flagged)
- Modification dates of all pipeline scripts
- MODFLOW96 and sfmodflx_2245 executable modification dates and sizes
- Python version

**Purpose:** Proves which specific code version produced the results. Enables exact reproduction of any past calculation.

#### Test Results Manifest

For every automated test that was run:
- Layer name and test name
- Pass/fail/skip status
- Specific value tested and threshold applied
- Timestamp of test execution

**Purpose:** Documents that quality assurance was performed and what specifically was verified.

#### Flag Register

For any test that raised a soft flag (not a hard fail):
- Test name and flagged value
- Threshold that was exceeded
- **Disposition field:** Space for analyst to record: "Reviewed, determined to be [real operational change / data quality issue / within acceptable bounds]. Analyst initials, date."

**Purpose:** Creates a documented human-in-the-loop for statistical outliers. Transforms "the analyst reviewed the numbers" into "Flag X was reviewed by [initials] on [date] and determined to be [reason]."

### 6.3 Workflow Log (Audit Trail)

The pipeline generates a comprehensive workflow log in both Markdown and DOCX formats. DOCX generation requires `pandoc` to be installed; if pandoc is unavailable, the workflow logger degrades gracefully to Markdown-only output. The log is structured as a formal audit document with the following sections:

| Section | Content | Regulatory Purpose |
|---------|---------|-------------------|
| 1. Metadata | Timestamp, operator, machine, git commit, branch | Establishes when, where, and by whom the calculation was performed |
| 2. Executive Summary | Total pumping, key depletions, verification status | One-page summary for management review |
| 3. Input Inventory | File names, sizes, SHA-256 hashes, roles | Proves which data was consumed |
| 4. Step-by-Step Execution | Each pipeline step with inputs/outputs | Documents the calculation sequence |
| 5. Output Inventory | Generated files with hashes | Proves what was produced |
| 6. Verification Summary | Test results by layer (pass/fail/skip counts) | Documents QA was performed |
| 7. Physical Interpretation | Pumping analysis, Compact implications, tributary/spring impacts | Provides context for non-technical reviewers |
| 8. Assumptions & Limitations | Model assumptions, data limitations, known caveats | Required disclosure for scientific reporting |
| 9. Approval Block | Prepared by, Reviewed by, Approved by (with signature lines) | Formal sign-off for regulatory submission |

#### Physical Interpretation Templates

The workflow log includes pre-formatted interpretation sections that contextualize the numbers:

**Pumping Analysis:** Compares current year pumping to 5-year historical average, characterizes as above/below/normal, and notes active well distribution.

**Rio Grande Compact Implications:** States the below-Otowi depletion in AF, notes it is chargeable against NM allocation, and computes the fraction of typical annual allocation consumed.

**Tributary Impacts:** Reports Pojoaque and Tesuque depletions with residual/superposition breakdown, and notes the status of Core (2003) residual projections (Pojoaque exhausted 2015, Tesuque continues).

**La Cienega Springs:** Reports cumulative and annual increment, and provides context on the springs' distance from the wellfield and the history of the GHB representation.

### 6.4 Analyst Disposition Workflow

When the test framework raises soft flags (exit code 2), the analyst must review each flag before outputs can be submitted. The disposition workflow is:

```
1. Test framework raises flag --> recorded in flag register
2. Analyst reviews the flagged value and its context
3. Analyst records disposition:
   - "Reviewed. [Value] is within expected range for [reason]."
   - OR "Reviewed. [Value] reflects [operational change]. No error."
   - OR "Reviewed. Identified [data quality issue]. Corrective action: [action]."
4. Analyst signs with initials and date
5. Flag register is included in provenance manifest
```

This workflow ensures that unusual values receive explicit human judgment before entering the regulatory record. It also creates a defensible audit trail: if challenged on an outlier value, the response is "This value was flagged by automated testing, reviewed by [analyst] on [date], and determined to be [reason]."

### 6.5 Regulatory Limits

| Constraint | Source | Enforcement |
|-----------|--------|-------------|
| Annual reporting deadline | OSE administrative requirement | Pipeline designed for single-command execution per year |
| Table format must match OSE template | OSE report format | Excel generation uses openpyxl with format-matching styles |
| Below-Otowi depletions charged to NM | Rio Grande Compact Art. IV | Table 4 explicitly separates Above/Below Otowi |
| Cumulative total depletions generally increasing | Physics (net depletion grows under continued pumping, though individual residual components can decline) | Flagged in ballpark_check.py; strict monotonicity not guaranteed for all columns |
| All pumping must be non-negative | Physics (cannot inject water through production wells) | Hard fail for negative values |
| Historical values preserved across years | Regulatory consistency | Year chaining locks historical rows (DS-04) |

---

## 7. References

### Publications
- Core, A.A. (2003). Santa Fe River Water Budget Model Technical Report. New Mexico Office of the State Engineer.
- Spinks, K.L. (1988). Buckman Wellfield Analytical Depletion Projections. New Mexico Bureau of Geology and Mineral Resources.
- Barroll, P. & Keyes, L. (2005). La Cienega Springs Depletion Analysis. New Mexico Office of the State Engineer.
- McDonald, M.G. & Harbaugh, A.W. (1988). A Modular Three-Dimensional Finite-Difference Ground-Water Flow Model. USGS TWRI Book 6, Chapter A1.

### Legal Framework
- Rio Grande Compact (1938). Interstate agreement among Colorado, New Mexico, and Texas governing apportionment of Rio Grande water.
- Texas v. New Mexico, No. 141 Original (U.S. Supreme Court). Ongoing litigation regarding Compact compliance.

### Standards
- New Mexico Office of the State Engineer annual reporting requirements for groundwater depletions
- USGS Water-Use Data System (WUDS) unit conversion standards

### Data Sources
- USGS Otowi Gage (08313000) -- Compact accounting point
- City of Santa Fe Buckman Wellfield production records (annual CSV delivery)

---

## 8. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-01 | Pumping data ingestion -- produces Tables 1 and 2 for regulatory submission |
| DS-02 | MODFLOW model -- generates the depletion calculations underlying Tables 3-5 |
| DS-03 | Stream depletion calculations -- scientific basis for Table 3-5 values |
| DS-04 | Year chaining -- ensures cumulative consistency across annual reports |
| DS-05 | Quality assurance -- verification framework that produces audit evidence |
| IS-09 | Implementation of workflow_logger.py (audit trail generation) |
| IS-10 | Implementation of pipeline_manifest.py (provenance manifest) |
| IS-11 | Implementation of run_all_tests.py (test orchestration) |

---

*Document Maintenance:*
- *Next Review:* When OSE reporting requirements change, or when new regulatory obligations are identified (e.g., additional spring monitoring, new Compact accounting rules)
- *Change Triggers:* Changes to OSE report format, new Compact litigation requirements, addition of new wells to the wellfield, changes to the depletion accounting framework
