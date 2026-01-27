# create_prd

Claude Code commands for PRD-driven development with automated code generation and review.

## What's Included

| Command | Description |
|---------|-------------|
| `/prd_create` | Generate a PRD from your feature idea through guided Q&A |
| `/code_review` | Create systematic code review checklist + auto-fix PRD |

| File | Description |
|------|-------------|
| `ralph.sh` | Bash loop that executes PRD user stories autonomously |
| `templates/` | Reusable prompt templates for PRD creation |

## Quick Start

See [QUICK_START.md](QUICK_START.md) for the 5-step workflow.

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
```

## The Workflow

```
/prd_create → PRD.md → ralph.sh → code
                                    ↓
                        /code_review → CHECKLIST.md → ralph.sh → FINDINGS.md
                                                                      ↓
                                                        /code_review --generate-fixes
                                                                      ↓
                                                      FIXES_PRD.md → ralph.sh → fixed code
```

## Commands

### `/prd_create`

Generates a Product Requirements Document through structured Q&A:

1. Describe your feature
2. Answer 7+ clarifying questions (A-G options)
3. Review summary, brainstorm if needed
4. Generate PRD.md with atomic user stories

**Key features:**
- Stories sized to fit one AI context window
- Dependency ordering (DB → backend → UI)
- Verifiable acceptance criteria
- Code quality stories (error handling, constants, atomic writes)

### `/code_review`

Creates a systematic code review checklist:

1. Run `/code_review` → generates CODE_REVIEW_CHECKLIST.md
2. Run `ralph.sh` on checklist → outputs REVIEW_FINDINGS.md
3. Review findings, decide what to fix
4. Run `/code_review --generate-fixes` → creates CODE_FIXES_PRD.md
5. Run `ralph.sh` on fixes PRD → implements fixes

**Reviews 9 aspects:**
- PRD compliance
- Error handling
- Edge cases
- Input validation
- Security
- Performance
- Code quality
- Dependencies
- Final prioritization

## ralph.sh

The automation engine. Loops through user stories, implementing one per iteration.

```bash
./ralph.sh [ITERATIONS] [SLEEP] [DOC_PATH]

# Examples
./ralph.sh                              # PRD.md, 10 iterations
./ralph.sh 15 2 CODE_REVIEW_CHECKLIST.md  # Review checklist
./ralph.sh 20 2 CODE_FIXES_PRD.md         # Fix PRD
```

## Templates

- `templates/PRD_PROMPT_TEMPLATE.md` - Structured template for optimal PRD generation
- `templates/PRD_PROMPT_EXAMPLE.md` - Filled example (Buckman water data project)

## Documentation

- [QUICK_START.md](QUICK_START.md) - 5-minute getting started
- [WORKFLOW_QUICKSTART.md](WORKFLOW_QUICKSTART.md) - Detailed workflow reference

## License

MIT
