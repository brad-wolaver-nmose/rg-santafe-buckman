# Ralph

PRD-driven development with automated code generation and review for Claude Code.

## Commands

| Command | Description |
|---------|-------------|
| `/prd_create` | Generate a PRD from your feature idea through guided Q&A |
| `/code_review` | Create systematic code review checklist + auto-fix PRD |

## Quick Start

### 1. Create a PRD

1. Run `claude /prd_create`
2. Describe your feature when prompted
3. Answer multiple-choice questions (e.g., "1E, 2A, 3B")
4. Type "done" when satisfied with summary
5. Result: `dev/PRD.md` + `dev/progress.txt`

### 2. Build Code from PRD

```bash
./ralph.sh [STORY_COUNT+5]
```

Each iteration completes one user story. If your PRD has 20 stories, run at least 25 iterations.

### 3. Review the Code

1. Run `claude /code_review`
2. Answer 1-2 questions about review depth
3. Note the story count shown
4. Run: `./ralph.sh --mode review [STORY_COUNT+5] 2 review/CODE_REVIEW_CHECKLIST.md`
5. Read `review/REVIEW_FINDINGS.md` when done

### 4. Fix Issues (Optional)

1. Run `claude /code_review --generate-fixes`
2. Review `review/CODE_FIXES_PRD.md`
3. Run: `./ralph.sh --mode dev [STORY_COUNT+5] 2 review/CODE_FIXES_PRD.md`

## ralph.sh

Autonomous coding agent loop with guardrails.

```bash
./ralph.sh [--mode dev|review] [ITERATIONS] [SLEEP] [DOC_PATH]
```

| Param | Default | Description |
|-------|---------|-------------|
| `--mode` | `dev` | `dev` for building code, `review` for code review |
| `ITERATIONS` | 10 | Max loops (set to story count + 5) |
| `SLEEP` | 2 | Seconds between loops |
| `DOC_PATH` | `dev/PRD.md` | Task document to process |

## Command Cheat Sheet

| Task | Command |
|------|---------|
| Create PRD | `claude /prd_create` |
| Build code from PRD | `./ralph.sh [STORY_COUNT+5]` |
| Generate review checklist | `claude /code_review` |
| Run code review | `./ralph.sh --mode review [N+5] 2 review/CODE_REVIEW_CHECKLIST.md` |
| Generate fix PRD | `claude /code_review --generate-fixes` |
| Apply fixes | `./ralph.sh --mode dev [N+5] 2 review/CODE_FIXES_PRD.md` |

## Project Structure

```
.
├── .claude/
│   ├── commands/
│   │   ├── prd_create.md        # PRD generator command
│   │   └── code_review.md       # Code review command
│   └── skills/prd-generator/
│       ├── SKILL.md             # Skill-based PRD generator
│       └── reference/           # Supporting reference files
│
├── ralph.sh                     # Autonomous agent loop
├── step1_ingest_buckman_data.py # Ingest daily pumping CSV → Tables 1 & 2
├── step2_update_modflow.py      # Generate MODFLOW WEL/NAM files
├── step3_run_modflow.sh         # Run MODFLOW96 with verification
├── step4_generate_depletion_tables.py  # Parse MODFLOW output → Tables 3-5
├── step5_verify_workflow.py     # Comprehensive workflow verification
├── stream_depletions.py         # Library: depletion calculation functions
├── requirements.txt             # Dependencies
├── mypy.ini                     # Type checking config
├── pytest.ini                   # Test config
│
├── dev/                         # PRD workspace + archives
│   ├── PRD.md                   # Active PRD
│   ├── progress.txt             # Active progress log
│   └── PRD_v*.md                # Archived PRD versions
│
├── review/                      # Review workspace + archives
│   ├── CODE_REVIEW_CHECKLIST.md # Active review checklist
│   ├── REVIEW_FINDINGS.md       # Active findings
│   ├── CODE_FIXES_PRD.md        # Active fixes PRD
│   └── *_v*.md                  # Archived review versions
│
├── tests/                       # Test files
│   └── test_ingest_buckman_data.py
│
├── scripts/                     # Utility scripts
├── docs/                        # Supplementary documentation
├── examples/                    # Reference/example files
├── input/                       # Source data
├── output/                      # Generated outputs
└── validation/                  # Reference validation data
```

## Installation

```bash
# Clone the repo
git clone https://github.com/bradwolaver/create_prd.git

# Copy commands to your project
mkdir -p YOUR_PROJECT/.claude/commands
cp .claude/commands/prd_create.md YOUR_PROJECT/.claude/commands/
cp .claude/commands/code_review.md YOUR_PROJECT/.claude/commands/
cp ralph.sh YOUR_PROJECT/
chmod +x YOUR_PROJECT/ralph.sh

# Create workspace directories
mkdir -p YOUR_PROJECT/dev YOUR_PROJECT/review
```

## License

MIT

---

## Buckman Wellfield Workflow

This repository contains the Buckman wellfield annual depletion calculation workflow for Santa Fe water rights compliance.

**📖 For complete workflow details, see [docs/BUCKMAN_WORKFLOW.md](docs/BUCKMAN_WORKFLOW.md)**

### Script Architecture

| Script | Type | Purpose |
|--------|------|---------|
| `step1_ingest_buckman_data.py` | CLI | Ingest daily pumping CSV → Tables 1 & 2 |
| `step2_update_modflow.py` | CLI | Generate MODFLOW WEL/NAM files |
| `step3_run_modflow.sh` | CLI | Run MODFLOW96 with verification (30-45 min) |
| `step4_generate_depletion_tables.py` | CLI | Parse MODFLOW output → Tables 3, 4, 5 |
| `step5_verify_workflow.py` | CLI | Comprehensive workflow verification for a given year |
| `stream_depletions.py` | Library | Depletion calculation functions (imported by step4) |

### Year-Agnostic Processing

All CLI scripts use the same `--year` flag and support processing any year:
```bash
python3 step1_ingest_buckman_data.py --year 2025
python3 step2_update_modflow.py --year 2025
./step3_run_modflow.sh --year 2025
python3 step4_generate_depletion_tables.py --year 2025
python3 step5_verify_workflow.py --year 2025
```

---

## Processing a New Year

When annual pumping data arrives (e.g., for 2025):

### Prerequisites

1. Previous year's MODFLOW output exists: `output/modflow/2024/thruCY2165_2024.wel`
2. New year's pumping CSV: `input/csv/Buckman_Well_Prod_2025.csv`

### Step-by-Step

```bash
# Step 1: Ingest pumping data → Tables 1 & 2
# Script shows which Table 1 template is being used (validation file or prior year)
python3 step1_ingest_buckman_data.py --year 2025

# Step 2: Generate MODFLOW files (auto-copies 10 baseline files from 2023)
# Script shows input source year and file paths
python3 step2_update_modflow.py --year 2025

# Step 3: Run MODFLOW96 with verification (30-45 minutes)
# Wrapper script handles Wine execution, logging, and automatic verification
./step3_run_modflow.sh --year 2025

# Step 4: Generate depletion Tables 3, 4, 5
# Script auto-runs post-processor (sfmodflx_2245.exe) and parses output
python3 step4_generate_depletion_tables.py --year 2025

# Step 5: Comprehensive workflow verification (runs all tests)
python3 step5_verify_workflow.py --year 2025

# Step 6: (Optional) Commit results
git add output/
git commit -m "Complete 2025 Buckman workflow"
```

### Enhanced Features

**File Source Visibility:**
Each script now shows which input files are being used:
- step1: Reports Table 1 template source (validation file or prior year)
- step2: Reports source year and input WEL file path
- step3: Shows MODFLOW runtime and verification status
- step4: Reports directory structure (nested ≤2024, flat 2025+) and flux file sizes

**Automated Verification:**
- `step3_run_modflow.sh`: Includes MODFLOW convergence verification (verify_modflow_run.py)
- `step5_verify_workflow.py`: Comprehensive check of all outputs and test suite
- Both generate markdown reports for documentation

**File Propagation:**
Year-to-year chaining is automatic:
- Table 1: Uses prior year output if no validation file exists
- WEL file: Extends from prior year (2024→2023, 2025→2024, etc.)
- Baseline files: 10 support files auto-copied from 2023 baseline to each year's output

### What If Something Fails?

Each script checks prerequisites and shows exactly which files are needed:

```
✗ Error: Input .wel file not found: output/modflow/2024/thruCY2165_2024.wel
  Cause: Year 2024 has not been processed through Step 2
  Solution: Run 'python3 step2_update_modflow.py --year 2024' first.
```

### Workflow Dependencies

```
Year N-1 ──────────────> Year N
   │                        │
   ├─ Table 1 (template) ──>│ Extends historical data
   ├─ WEL file ────────────>│ Appends new year pumping
   └─ 2023 baseline ───────>│ 10 support files copied
```

**File Dependency Chain:**
- **Table 1:** Uses validation file OR prior year output as template
- **WEL file:** Chains from prior year (2024→2023, 2025→2024, etc.)
- **Baseline files:** 10 MODFLOW support files copied from 2023 baseline
- **Tables 2-5:** Generated fresh each year

See [docs/FILE_DEPENDENCIES.md](docs/FILE_DEPENDENCIES.md) for visual diagram.

### Output Tables

| Table | Description |
|-------|-------------|
| Table 1 | Historical pumping by well (1988-present) |
| Table 2 | Current year monthly pumping detail |
| Table 3 | Rio Pojoaque-Nambe & Rio Tesuque depletions |
| Table 4 | Rio Grande above/below Otowi depletions |
| Table 5 | La Cienega Springs cumulative depletions |

### Documentation

For complete workflow details and troubleshooting:
- **Main Workflow Guide:** [docs/BUCKMAN_WORKFLOW.md](docs/BUCKMAN_WORKFLOW.md)
- **File Dependencies:** [docs/FILE_DEPENDENCIES.md](docs/FILE_DEPENDENCIES.md) - Visual file flow diagram
- **Processing Checklist:** [docs/NEW_YEAR_CHECKLIST.md](docs/NEW_YEAR_CHECKLIST.md) - Step-by-step guide

Methodology documentation:
- **Tables 1 & 2:** [output/ingested_data/METHODOLOGY_Tables_1_2.md](output/ingested_data/METHODOLOGY_Tables_1_2.md)
- **Tables 3, 4, 5:** [output/depletion/METHODOLOGY_Tables_3_4_5.md](output/depletion/METHODOLOGY_Tables_3_4_5.md)

**See [docs/BUCKMAN_WORKFLOW.md](docs/BUCKMAN_WORKFLOW.md) for complete workflow details.**
