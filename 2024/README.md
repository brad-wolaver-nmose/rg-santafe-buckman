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
├── ingest_buckman_data.py       # Main entry point
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
