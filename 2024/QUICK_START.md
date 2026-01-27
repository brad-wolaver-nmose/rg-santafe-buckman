# Quick Start

Two workflows: **Create code** from requirements, then **Review** that code.

---

## Workflow A: Create Code from PRD

Turn your feature idea into working code.

| Step | Command | What Happens |
|------|---------|--------------|
| 1 | `claude /prd_create` | Answer questions, generate PRD.md |
| 2 | `./ralph.sh` | Ralph implements each user story |

**Result:** Working code with commits for each feature.

---

## Workflow B: Review Code

Systematically audit code for bugs, security, and PRD compliance.

| Step | Command | What Happens |
|------|---------|--------------|
| 1 | `claude /code_review` | Creates CODE_REVIEW_CHECKLIST.md (tells you story count) |
| 2 | `./ralph.sh [N+5] 2 CODE_REVIEW_CHECKLIST.md` | Ralph reviews, outputs REVIEW_FINDINGS.md |
| 3 | Read `REVIEW_FINDINGS.md` | You decide what needs fixing |
| 4 | `claude /code_review --generate-fixes` | Creates CODE_FIXES_PRD.md (tells you story count) |
| 5 | `./ralph.sh [N+5] 2 CODE_FIXES_PRD.md` | Ralph implements fixes |

**Important:** Set ITERATIONS to match story count + 5. The `/code_review` command tells you how many stories were generated.

**Result:** Documented findings + automated fixes.

---

## ralph.sh Parameters

```bash
./ralph.sh [ITERATIONS] [SLEEP] [DOC_PATH]
```

| Param | Default | Description |
|-------|---------|-------------|
| ITERATIONS | 10 | Max loops. **Set to story count + 5.** |
| SLEEP | 2 | Seconds between loops |
| DOC_PATH | PRD.md | Document to process |

**Key insight:** Each iteration = 1 user story. If your document has 50 stories, run `./ralph.sh 55 2 DOC.md`.

---

## Installation

```bash
# Copy to your project
mkdir -p .claude/commands
cp .claude/commands/prd_create.md YOUR_PROJECT/.claude/commands/
cp .claude/commands/code_review.md YOUR_PROJECT/.claude/commands/
cp ralph.sh YOUR_PROJECT/
chmod +x YOUR_PROJECT/ralph.sh
```

---

## Full Documentation

- `WORKFLOW_QUICKSTART.md` - Detailed workflow guide
- `templates/PRD_PROMPT_TEMPLATE.md` - Reusable prompt template
- `templates/PRD_PROMPT_EXAMPLE.md` - Example filled template
