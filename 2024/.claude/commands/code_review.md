---
name: code_review
description: "Perform comprehensive code review against PRD. Creates CODE_REVIEW_CHECKLIST.md for ralph to execute. Run with --generate-fixes after review to create CODE_FIXES_PRD.md. Triggers on: review code, code review, audit code, check code quality."
---

# Code Review Generator

Create a comprehensive code review checklist that can be executed by the Ralph loop to systematically review code against PRD requirements and best practices.

---

## Philosophy

You are a senior software engineer and code quality expert. Your job is to create a thorough, systematic review checklist that leaves nothing to chance. Quality code review is methodical, not rushed.

The review process has two phases:
1. **Review Phase:** Generate checklist → Ralph executes → REVIEW_FINDINGS.md created
2. **Fix Phase (optional):** User reviews findings → Generate fix PRD → Ralph implements fixes

---

## The Job

### Standard Mode (No Flags)

1. Identify PRD.md and code files in the project
2. Ask 1-2 minimal questions (problem areas, review depth)
3. Generate CODE_REVIEW_CHECKLIST.md with review user stories
4. Create empty REVIEW_FINDINGS.md template
5. Explain how to run ralph on the checklist

### Fix Generation Mode (--generate-fixes)

1. Read REVIEW_FINDINGS.md
2. Parse all findings by severity
3. Generate CODE_FIXES_PRD.md with fix user stories
4. Explain how to run ralph on the fix PRD

---

## Step 1: Identify Project Context

First, identify the project structure:

```
I'll review your codebase against the PRD. Let me identify the key files:

**PRD:** PRD.md (found/not found)
**Main code files:** [list detected Python/JS/etc files]
**Test files:** [list if any]
**Config files:** [list if any]

Based on this, I'll create a comprehensive review checklist.
```

If PRD.md is not found, ask user to specify the requirements document or provide context.

---

## Step 2: Minimal Questions (1-2 Maximum)

Only ask questions that change the review scope. Skip if answers are obvious from context.

**Question 1 (optional):**
```
Are there any known problem areas I should prioritize?

A. No specific concerns - do a full comprehensive review
B. Focus on [let user specify]
C. Skip review of [let user specify]
```

**Question 2 (required):**
```
What review depth do you need?

A. Quick sanity check (5-10 minutes) - High-level verification only
B. Standard review (15-30 minutes) - All major aspects covered
C. Thorough pre-release audit (30-60 minutes) - Deep dive into every detail
D. [Default to B if no response]
```

---

## Step 2.5: Review Story Sizing (THE NUMBER ONE RULE)

**Each review story must be completable in ONE context window (~10 min of AI work).**

Ralph spawns a fresh instance per story with no memory of previous work. If a story is too big, the AI runs out of context and produces incomplete findings.

### Right-sized review stories:
- Run mypy and document type errors
- Check one specific function for error handling
- Verify one PRD user story is implemented correctly
- Check one input source for validation

### Too big (MUST split):
| Too Big | Split Into |
|---------|-----------|
| "Review all PRD compliance" | One story per PRD user story or functional area |
| "Audit all error handling" | One story per function or per module |
| "Check all edge cases" | One story per edge case category |
| "Review code quality" | Separate: naming, DRY, dead code, magic numbers |

**Rule of thumb:** If you cannot describe what to review in 1 sentence without using "and", it's too big.

### Story Count Guidelines by Review Depth:
| Depth | Stories | Focus |
|-------|---------|-------|
| Quick (5-10 min) | 5-10 | Type check, critical PRD items, security scan |
| Standard (15-30 min) | 15-30 | Type check + key functions + quality checks |
| Thorough (30-60 min) | 40-80+ | Comprehensive atomic review (no cap - granularity is good!) |

**Note:** More stories = more granularity = better. The iteration count in "Next Steps" will match story count.

---

## Step 2.6: Review Story Ordering

Stories execute in order. Earlier stories must NOT depend on later ones.

**Correct order:**
1. Type/syntax checks (mypy, py_compile) - quick pass/fail first
2. PRD compliance by functional area
3. Error handling per function
4. Edge cases and input validation
5. Security review
6. Code quality (DRY, naming, dead code)
7. Executive summary (compile all findings)

**Wrong order:**
```
US-R01: Executive summary (nothing to summarize yet!)
US-R02: Review function X
```

---

## Step 3: Generate CODE_REVIEW_CHECKLIST.md

Create the checklist document with user stories for Ralph to execute.

### Generating Atomic Stories

When generating CODE_REVIEW_CHECKLIST.md, dynamically create stories based on:

1. **Count PRD user stories** → Generate 1 review story per 2-3 PRD stories (quick) or 1:1 (thorough)
2. **Count functions** → Generate error handling stories for critical functions only (quick) or all (thorough)
3. **Apply one-sentence rule** → If a story needs "and", split it
4. **Embrace granularity** → More atomic stories = better. 50, 80, or 100+ stories is fine for thorough reviews.

### Atomic Story Format

Each story should be SHORT and follow this format:

```markdown
### US-RXX: [One-sentence task description]
**Check:** [Single specific thing to verify]
**Location:** [Exact function name or file:lines]
**Document:** [Exact table/section in REVIEW_FINDINGS.md]
**Pass if:** [Single measurable criterion]
```

### Checklist Structure

```markdown
# Code Review Checklist

Generated: [date]
PRD: PRD.md
Code files: [list]
Review depth: [quick/standard/thorough]
Story count: [N stories]

---

## Instructions for Ralph

For each story:
1. Read ONLY the specified location
2. Check ONLY the specified criterion
3. Add ONE row to the specified table in REVIEW_FINDINGS.md
4. Mark [x] when documented

**Keep it focused.** Each story = one check = one finding row.

---

## Review Stories

### US-R01: Run type checker
**Check:** Run `mypy [main_file.py]` and capture output
**Location:** All .py files
**Document:** Add to Type Safety section
**Pass if:** Zero errors OR each error documented

---

### US-R02: Run syntax check
**Check:** Run `python3 -m py_compile [main_file.py]`
**Location:** All .py files
**Document:** Add to Type Safety section
**Pass if:** Compiles without errors

---

### US-R03: Verify PRD US-001 implementation
**Check:** [Specific criterion from PRD US-001]
**Location:** [Relevant function]
**Document:** Add row to PRD Compliance table
**Pass if:** Criterion met as specified in PRD

---

### US-R04: Verify PRD US-002 implementation
**Check:** [Specific criterion from PRD US-002]
**Location:** [Relevant function]
**Document:** Add row to PRD Compliance table
**Pass if:** Criterion met as specified in PRD

---

[Continue with one story per PRD user story or functional grouping...]

---

### US-RXX: Check [function_name] error handling
**Check:** Does [function_name] handle [specific error type]?
**Location:** [function_name]() in [file]:lines X-Y
**Document:** Add row to Error Handling table
**Pass if:** Error caught, logged with context, returns gracefully

---

[Continue with error handling stories for critical functions...]

---

### US-RXX: Check for magic numbers
**Check:** Are there hardcoded values that should be constants?
**Location:** Scan all .py files for numeric literals
**Document:** Add rows to Code Quality table
**Pass if:** All config values in named constants with comments

---

### US-RXX: Check for path traversal risks
**Check:** Can user input influence file paths unsafely?
**Location:** All file operations (open, shutil, os.path)
**Document:** Add to Security table
**Pass if:** Paths sanitized OR no user input in paths

---

### US-RXX: Compile executive summary
**Check:** Count all findings by severity, identify top 3 issues
**Location:** Review all findings documented above
**Document:** Fill in Executive Summary section
**Pass if:** Totals accurate, top issues identified, assessment provided

---

## Completion

When all stories are complete, output: <promise>COMPLETE</promise>
```

### Example: Quick Review (~5 stories)

For a quick sanity check, generate only:
1. US-R01: Run mypy
2. US-R02: Run py_compile
3. US-R03: Verify critical PRD requirement
4. US-R04: Security scan (path traversal, injection)
5. US-R05: Compile summary

### Example: Standard Review (~12 stories)

1-2: Type/syntax checks
3-7: PRD compliance (group 2-3 user stories each)
8-9: Error handling for main functions
10: Input validation
11: Code quality scan
12: Compile summary

### Example: Thorough Review (~25 stories)

1-2: Type/syntax checks
3-15: PRD compliance (1 story per PRD user story)
16-20: Error handling per critical function
21: Edge cases (empty/null inputs)
22: Security audit
23: Magic numbers check
24: DRY/dead code check
25: Compile summary

---

## Step 4: Create REVIEW_FINDINGS.md Template

Keep the findings template simple with one table per category. Each atomic story adds one row.

```markdown
# Code Review Findings

**Generated:** [date]
**PRD:** PRD.md
**Review depth:** [quick/standard/thorough]
**Stories completed:** _/_

---

## Executive Summary

- **Total findings:** _ | **Critical:** _ | **High:** _ | **Medium:** _ | **Low:** _
- **Assessment:** [PASS / PASS WITH FIXES / NEEDS MAJOR REVISION]
- **Top 3 issues:** 1) _ 2) _ 3) _

---

## Type Safety

| Check | Result | Details |
|-------|--------|---------|
| mypy | | |
| py_compile | | |

---

## PRD Compliance

| PRD Story | Status | Location | Notes |
|-----------|--------|----------|-------|
| US-001 | | | |
| US-002 | | | |
[Add rows as needed]

---

## Error Handling

| Function | Status | Issue (if any) |
|----------|--------|----------------|
| | | |

---

## Security

| Check | Status | Finding |
|-------|--------|---------|
| Path traversal | | |
| Command injection | | |
| Secrets exposure | | |

---

## Code Quality

| Check | Status | Finding |
|-------|--------|---------|
| Magic numbers | | |
| DRY violations | | |
| Dead code | | |

---

## Action Items

### Must Fix (Critical/High)
- [ ] _

### Should Fix (Medium)
- [ ] _

### Optional (Low)
- [ ] _
```

---

## Step 5: Provide Next Steps

After generating the checklist:

```
## Files Created

1. **CODE_REVIEW_CHECKLIST.md** - Review tasks for Ralph to execute
2. **REVIEW_FINDINGS.md** - Template for documenting findings

## Next Steps

**This checklist has [N] stories.** Run Ralph with at least [N+5] iterations:

```bash
./ralph.sh [N+5] 2 CODE_REVIEW_CHECKLIST.md
```

For example, if 50 stories were generated, run:
```bash
./ralph.sh 55 2 CODE_REVIEW_CHECKLIST.md
```

After review completes, read REVIEW_FINDINGS.md to see results.

If fixes are needed, run:
```bash
claude /code_review --generate-fixes
```

This will create CODE_FIXES_PRD.md that Ralph can execute to implement fixes.
```

---

## Fix Generation Mode (--generate-fixes)

When user runs `/code_review --generate-fixes`:

### Step 1: Read REVIEW_FINDINGS.md

Parse all findings by severity. If REVIEW_FINDINGS.md doesn't exist or is empty, explain that the review must be run first.

### Step 2: Generate CODE_FIXES_PRD.md

```markdown
# Code Fixes PRD

**Generated from:** REVIEW_FINDINGS.md
**Generated on:** [date]

---

## Introduction

This PRD contains fixes for issues identified during code review. Each user story addresses a specific finding.

## User Stories

### US-F01: [CRITICAL] [Title from finding]
**Description:** As a developer, I need to fix [issue] so that [impact is resolved].

**Finding reference:** [Link to specific finding in REVIEW_FINDINGS.md]

**Acceptance Criteria:**
- [ ] [Specific fix criterion]
- [ ] [Verification criterion]
- [ ] Typecheck passes
- [ ] Original issue no longer present

---

### US-F02: [HIGH] [Title]
...

[Continue for all findings worth fixing]
```

### Step 3: Prioritization Rules

- **Critical findings:** Always generate fix stories
- **High findings:** Always generate fix stories
- **Medium findings:** Generate fix stories unless explicitly skipped
- **Low findings:** List in "Optional Fixes" section, don't generate stories

### Step 4: Provide Next Steps

```
## Files Created

1. **CODE_FIXES_PRD.md** - Fix tasks for Ralph to implement

## Next Steps

Review CODE_FIXES_PRD.md to confirm the fixes look correct.

**This fix PRD has [N] stories.** Run Ralph with at least [N+5] iterations:

```bash
./ralph.sh [N+5] 2 CODE_FIXES_PRD.md
```

After fixes are complete, consider re-running the code review to verify:
```bash
claude /code_review
./ralph.sh [STORY_COUNT+5] 2 CODE_REVIEW_CHECKLIST.md
```
```

---

## Checklist Before Saving

### Standard Mode
- [ ] Identified PRD.md and code files
- [ ] Asked 1-2 questions (or skipped if obvious)
- [ ] Generated CODE_REVIEW_CHECKLIST.md with atomic review stories (see story count guidelines)
- [ ] Each story passes the "one sentence without and" test
- [ ] Created REVIEW_FINDINGS.md template
- [ ] Provided clear next steps

### Fix Generation Mode
- [ ] Read REVIEW_FINDINGS.md successfully
- [ ] Parsed findings by severity
- [ ] Generated CODE_FIXES_PRD.md with prioritized fix stories
- [ ] Excluded low-priority items from fix stories
- [ ] Provided clear next steps

---

## Severity Definitions

| Severity | Definition | Action |
|----------|------------|--------|
| **Critical** | Security vulnerability, data loss risk, or complete feature breakage | Must fix before any deployment |
| **High** | Significant bug, PRD non-compliance, or reliability issue | Should fix in current sprint |
| **Medium** | Code quality issue, minor bug, or maintainability concern | Fix when convenient |
| **Low** | Style issue, minor optimization, or nice-to-have improvement | Optional |
