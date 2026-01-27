# PRD Prompt Template

Use this template when running `/prd_create`. Copy, fill in your details, then paste as your prompt.

---

## 1. PROJECT CONTEXT (Required)

### What is this?
<!-- One sentence: What does this tool/feature do? -->


### Who uses it and why?
<!-- Who is the end user? What problem does this solve for them? -->


### Stakes & Constraints
<!-- What happens if this fails? Regulatory, financial, reputational? -->


### Workflow Position
<!-- Is this standalone or part of a larger process? What comes before/after? -->


---

## 2. CORE REQUIREMENTS (Required)

### Input → Output Summary
<!-- What goes in? What comes out? One paragraph. -->


### Data Transformation Rules
<!-- List the specific business logic, calculations, or transformations -->
-
-
-

### Validation Requirements
<!-- What makes data valid/invalid? What checks are needed? -->
-
-

---

## 3. FILE & DATA SPECS (Required)

### Input
- **Location:** `./input/`
- **Format:**
- **Naming pattern:**
- **Example filename:**

### Output
- **Location:** `./output/`
- **Format:**
- **Naming pattern:**
- **Example filename:**

### Sample Data (Optional but helpful)
<!-- Paste a small example of input and expected output -->
```
Input example:

Output example:
```

---

## 4. QUALITY & INTEGRITY (Required)

### Critical Invariants
<!-- What must NEVER go wrong? What's the worst-case failure? -->


### Validation Strategy
<!-- Choose one and explain: -->
- [ ] **Strict:** Reject anything questionable, flag for human review
- [ ] **Lenient:** Best-effort processing, log warnings
- [ ] **Mixed:** Strict for X, lenient for Y

### Human Review Points
<!-- Where should a human check the work? -->
-

---

## 5. TECHNICAL REFERENCES (If Applicable)

### Constants & Conversion Factors
<!-- List any magic numbers with sources -->
| Constant | Value | Source |
|----------|-------|--------|
|  |  |  |

### External Standards
<!-- Cite any standards, APIs, or authoritative sources -->


### Existing Code to Integrate
<!-- Any existing files, functions, or patterns to follow? -->


---

## 6. ROBUSTNESS CHECKLIST (Review & Check)

<!-- Check all that apply - helps Claude add the right user stories -->

### Dependencies
- [ ] Requires external tools (list them: _____________)
- [ ] Requires Python packages (list them: _____________)
- [ ] No special dependencies

### Error Handling
- [ ] Fail fast on first error
- [ ] Continue processing, collect all errors
- [ ] Interactive: ask user how to proceed

### User Experience
- [ ] Needs progress feedback (long operations)
- [ ] Needs pre-flight validation before processing
- [ ] Needs interactive prompts (e.g., confirm before overwrite)
- [ ] Silent/batch mode is fine

### File Safety
- [ ] Use atomic writes (prevent corruption on crash)
- [ ] Preserve original inputs (work on copies)
- [ ] Simple overwrites are acceptable

### Code Quality
- [ ] Extract magic numbers to named constants
- [ ] Add detailed comments for beginners
- [ ] Keep it minimal, no extra abstractions

---

## 7. NON-GOALS (Recommended)

### Explicitly Out of Scope
<!-- What should this NOT do? Prevents scope creep. -->
-
-

### Future Phases
<!-- What's deferred to later? -->
-

---

## 8. ADDITIONAL CONTEXT (Optional)

### Known Edge Cases
<!-- Any tricky situations you're aware of? -->


### Examples of Similar Work
<!-- Links or references to similar projects/code -->


### Questions for Claude
<!-- Anything you're unsure about? -->


---

# How to Use This Template

1. **Copy** this entire file
2. **Fill in** each section (delete placeholder comments)
3. **Run** `claude /prd_create`
4. **Paste** your filled template as the initial prompt
5. **Answer** Claude's follow-up questions
6. **Review** the generated PRD.md

## Tips for Best Results

- **Be specific about file paths** - `./input/pdfs/` beats "the input folder"
- **Include sample data** - Even one row helps Claude understand format
- **State your priorities** - "Data integrity > speed" guides tradeoffs
- **Cite your sources** - Technical references prevent Claude from guessing
- **Check the robustness boxes** - Prompts Claude to add reliability features
