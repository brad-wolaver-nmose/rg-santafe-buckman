# Buckman Wellfield Pipeline — Specification Index

> After-the-fact specification suite for the Buckman wellfield depletion pipeline.
> Serves as reproducibility proof, future maintainer documentation, and reusable template
> for OSE/USGS to spec similar computational hydrology pipelines for AI-assisted development.

**Created:** 2026-02-20
**Fidelity Level:** Functional + Architectural (USGS SIR standard)
**Self-Containedness:** Hybrid with appendices

---

## Two-Tier Architecture

### Tier 1: Domain Specifications
Scientific basis, assumptions, and domain knowledge. Written for a hydrologist audience.

### Tier 2: Implementation Specifications
Claude Code session-sized prompts. Each is a complete spec — paste it into a fresh
Claude Code session with the Tier 1 domain docs available, and get a working module back.

---

## Tier 1: Domain Specifications

| Doc ID | Domain | Status | Key Content |
|--------|--------|--------|-------------|
| **DS-01** | [Buckman Wellfield & Well Production Data](DS-01_Well_Production_Data.md) | Draft | 13 wells, OSE permit mapping, CSV format, MG→AF conversion, daily→monthly aggregation, Tables 1-2 |
| **DS-02** | [MODFLOW96 Santa Fe Local-Scale Model](DS-02_MODFLOW96_Model.md) | Draft | Grid (23×25×2), boundary conditions (RIV, GHB), well package format, AF→ft³/s conversion, stress periods, convergence |
| **DS-03** | [Stream Depletion Analysis](DS-03_Stream_Depletion_Analysis.md) | Draft | Superposition principle, Core 2003 analytical residuals, FORTRAN post-processor I/O, cfs→AF conversion, cell-to-stream mapping, Tables 3-5 |
| **DS-04** | [Year-Chaining & Temporal Architecture](DS-04_Year_Chaining.md) | Draft | WEL file accumulation (1988→present), Table 1 row extension, Table 3 historical preservation, directory structure, leap years |
| **DS-05** | [Quality Assurance Framework](DS-05_Quality_Assurance.md) | Draft | 7-layer hierarchy, hard-fail vs flag policy, physical bounds, tolerance model, regression harness |
| **DS-06** | [Regulatory & Compliance Context](DS-06_Regulatory_Compliance.md) | Draft | Rio Grande Compact, OSE reporting, court-facing standards, provenance chain-of-custody, analyst disposition |

### Build Order
```
DS-01 (Well Production) ─── foundational data
DS-02 (MODFLOW96 Model) ── numerical model context
DS-03 (Stream Depletion) ── core science (depends on DS-01, DS-02)
DS-04 (Year Chaining) ──── architectural pattern (depends on DS-01, DS-02)
DS-05 (QA Framework) ───── verification philosophy
DS-06 (Regulatory) ──────── compliance requirements
```

---

## Tier 2: Implementation Specifications

| Spec ID | Module | Depends On | Status | Key Deliverables |
|---------|--------|------------|--------|------------------|
| **IS-01** | [Project Scaffold & Constants](IS-01_Project_Scaffold.md) | — | Draft | Directory structure, `requirements.txt`, constants module, `pyproject.toml` |
| **IS-02** | [CSV Ingestion & Table 2](IS-02_CSV_Ingestion_Table2.md) | IS-01 | Draft | `step1_ingest_buckman_data.py`: CSV parser, daily validation, monthly aggregation, MG→AF, Table 2 XLSX |
| **IS-03** | [Table 1 Chaining](IS-03_Table1_Chaining.md) | IS-02 | Draft | Table 1 template loading, row extension, historical preservation, XLSX export |
| **IS-04** | [WEL File Management](IS-04_WEL_File_Management.md) | IS-01 | Draft | `step2_update_modflow.py`: WEL parser, AF→ft³/s conversion, stress period extension, well ordering |
| **IS-05** | [MODFLOW Execution Wrapper](IS-05_MODFLOW_Execution.md) | IS-04 | Draft | `step3_run_modflow.sh`: NAM generation, baseline copy, Wine execution, convergence check |
| **IS-06** | [Post-Processor & Output Parsing](IS-06_Post_Processor.md) | IS-05 | Draft | FORTRAN post-processor execution, `parse_postprocessor_output()`, cell coordinate extraction |
| **IS-07** | [Stream Depletion Library](IS-07_Stream_Depletion_Library.md) | IS-01 | Draft | `stream_depletions.py`: `cfs_to_acre_feet()`, analytical residuals, Otowi cell classification |
| **IS-08** | [Table 3 Generation](IS-08_Table3_Generation.md) | IS-06, IS-07 | Draft | Rio Pojoaque & Tesuque: residual + superposition, year chaining, XLSX export |
| **IS-09** | [Tables 4 & 5 Generation](IS-09_Tables4_5_Generation.md) | IS-06, IS-07 | Draft | Rio Grande above/below Otowi (Table 4), La Cienega cumulative (Table 5) |
| **IS-10** | [Test Suite (Layers 0-1)](IS-10_Test_Suite_Layers_0_1.md) | IS-02–IS-09 | Draft | pytest smoke tests, edge cases, conservation checks, `conftest.py` |
| **IS-11** | [Validation Framework (Layers 2-5)](IS-11_Validation_Framework.md) | IS-10 | Draft | Ballpark bounds, temporal consistency, regression harness, tolerance config |
| **IS-12** | [Provenance & Compliance (Layer 6)](IS-12_Provenance_Compliance.md) | IS-10 | Draft | `pipeline_manifest.py`, `workflow_logger.py`, SHA-256 hashing, JSON manifest |

### Dependency Graph
```
IS-01 ─────┬── IS-02 ── IS-03
            │
            ├── IS-04 ── IS-05
            │
            └── IS-07
                  │
IS-05 ── IS-06 ──┤
                  │
IS-07 ────────────┤
                  │
                  ├── IS-08
                  └── IS-09

IS-02..IS-09 ── IS-10 ── IS-11
                   │
                   └──── IS-12
```

---

## Source Code → Spec Mapping

| Source File | Lines | Primary Spec | Secondary Specs |
|-------------|-------|-------------|-----------------|
| `step1_ingest_buckman_data.py` | 2,002 | IS-02, IS-03 | DS-01 |
| `step2_update_modflow.py` | 1,529 | IS-04 | DS-02, DS-04 |
| `step3_run_modflow.sh` | ~150 | IS-05 | DS-02 |
| `step4_generate_depletion_tables.py` | 1,125 | IS-06 | DS-03 |
| `stream_depletions.py` | 2,732 | IS-07, IS-08, IS-09 | DS-03, DS-04 |
| `run_all_tests.py` | 894 | IS-10, IS-11 | DS-05 |
| `src/pipeline_manifest.py` | 766 | IS-12 | DS-06 |
| `src/workflow_logger.py` | 893 | IS-12 | DS-06 |
| `validation/ballpark_check.py` | ~350 | IS-11 | DS-05 |
| `validation/temporal_consistency.py` | ~200 | IS-11 | DS-05 |
| `validation/2024/run_regression_2024.py` | ~600 | IS-11 | DS-05 |
| `tests/test_ingest_buckman_data.py` | ~800 | IS-10 | DS-01 |
| `tests/test_update_modflow.py` | ~700 | IS-10 | DS-02 |
| `tests/test_stream_depletions.py` | ~900 | IS-10 | DS-03 |
| `tests/test_generate_depletion_tables.py` | ~600 | IS-10 | DS-03 |
| `tests/test_conservation.py` | ~500 | IS-10 | DS-05 |
| `tests/test_edge_cases.py` | ~500 | IS-10 | DS-05 |
| `tests/test_modflow_geometry.py` | ~300 | IS-10 | DS-02 |

---

## Reference Documents

| Document | Path | Used By |
|----------|------|---------|
| MODFLOW Cell Mapping | `docs/MODFLOW_CELL_MAPPING.md` | DS-02, DS-03, IS-06, IS-07 |
| File Dependencies | `docs/FILE_DEPENDENCIES.md` | DS-04, IS-04, IS-05 |
| Handoff Prompt | `docs/claude_code_handoff_prompt.md` | DS-05, DS-06 |
| Historical Bounds | `validation/historical/bounds.yaml` | DS-05, IS-11 |
| Tolerances | `validation/2024/tolerances.yaml` | DS-05, IS-11 |
| Excel Format Specs | `docs/EXCEL_FORMAT_SPECIFICATIONS.md` | IS-02, IS-03, IS-08, IS-09 |
| New Year Checklist | `docs/NEW_YEAR_CHECKLIST.md` | DS-04 |
| Testing Framework | `docs/TESTING_FRAMEWORK.md.md` | DS-05, IS-10 |

---

## Verification Checklist

- [ ] **Completeness:** Every function in the pipeline has a home in at least one IS-XX spec
- [ ] **Accuracy:** Unit conversions, constants, and cell mappings in specs match the code
- [ ] **Dependency:** No circular dependencies between specs; build order is valid
- [ ] **Reproducibility (optional):** Fresh Claude Code session can build from specs and pass tests
- [ ] **Domain review:** Brad reviews DS-01 through DS-06 for scientific accuracy

---

## Templates

- [Domain Spec Template](DOMAIN_SPEC_TEMPLATE.md) — For Tier 1 domain specs
- [Implementation Spec Template](IMPLEMENTATION_SPEC_TEMPLATE.md) — For Tier 2 implementation specs
