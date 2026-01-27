# PRD & Code Review Workflow - Quick Reference

Two automated workflows: create code from requirements, then review that code. Both use Ralph (a bash loop) to do the heavy lifting.

---

## Part 1: Create Code from PRD

**Goal:** Turn your feature idea into working code.

1. Run `claude /prd_create`
2. Describe your feature when prompted
3. Answer the multiple-choice questions (e.g., "1E, 2A, 3B")
4. Type "done" when satisfied with summary
5. Run `./ralph.sh`

**Result:** PRD.md created, then Ralph implements each user story. Code appears, commits happen automatically.

---

## Part 2: Review the Code

**Goal:** Systematically check the code for bugs, security issues, and PRD compliance.

1. Run `claude /code_review`
2. Answer 1-2 questions about review depth
3. Note the **story count** shown (e.g., "This checklist has 50 stories")
4. Run `./ralph.sh [STORY_COUNT+5] 2 CODE_REVIEW_CHECKLIST.md`
5. Read `REVIEW_FINDINGS.md` when done

**Example:** If 50 stories generated, run `./ralph.sh 55 2 CODE_REVIEW_CHECKLIST.md`

**Result:** Detailed findings report with issues categorized by severity (Critical/High/Medium/Low).

---

## Part 3: Fix Issues (Optional)

**Goal:** Auto-generate fixes for review findings.

1. Run `claude /code_review --generate-fixes`
2. Review `CODE_FIXES_PRD.md`
3. Note the **story count** shown (e.g., "This fix PRD has 10 stories")
4. Run `./ralph.sh [STORY_COUNT+5] 2 CODE_FIXES_PRD.md`

**Example:** If 10 fix stories generated, run `./ralph.sh 15 2 CODE_FIXES_PRD.md`

**Result:** Ralph implements fixes for each finding. Re-run code review to verify.

---

## Command Cheat Sheet

| Task | Command |
|------|---------|
| Create PRD | `claude /prd_create` |
| Build code from PRD | `./ralph.sh [STORY_COUNT+5]` |
| Generate review checklist | `claude /code_review` |
| Run code review | `./ralph.sh [STORY_COUNT+5] 2 CODE_REVIEW_CHECKLIST.md` |
| Generate fix PRD | `claude /code_review --generate-fixes` |
| Apply fixes | `./ralph.sh [STORY_COUNT+5] 2 CODE_FIXES_PRD.md` |

**Note:** Replace `[STORY_COUNT+5]` with actual number. The `/code_review` and `/prd_create` commands tell you how many stories were generated.

---

## ralph.sh Parameters

```
./ralph.sh [ITERATIONS] [SLEEP] [DOC_PATH]
```

- `ITERATIONS` - Max loops (default: 10). **Set to story count + 5 to ensure completion.**
- `SLEEP` - Seconds between loops (default: 2)
- `DOC_PATH` - Document to process (default: PRD.md)

**Key insight:** Each iteration = 1 user story completed. If your PRD/checklist has 50 stories, run at least 55 iterations.
