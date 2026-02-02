# Pre-Save Checklist

## Checklist Before Saving

### Question Process
- [ ] Acknowledged understanding of user's initial description
- [ ] Explained question count, reasoning, and topic areas
- [ ] Asked questions grouped under descriptive headings
- [ ] Each question had A-G options with recommendations or explanations
- [ ] Offered brainstorming (F) and handled any brainstorming sessions
- [ ] Detected and resolved any contradictions in answers
- [ ] Presented summary and offered final brainstorming opportunity
- [ ] User confirmed answers before PRD generation

### Story Quality
- [ ] User stories use US-001 format
- [ ] Each story is an atomic task completable in ONE iteration (small enough)
- [ ] Stories ordered by dependency (schema -> backend -> frontend)
- [ ] All criteria are verifiable (not vague)
- [ ] Every story has "Typecheck passes" as criterion
- [ ] UI stories have "Verify changes work in browser"
- [ ] Script/CLI stories have "Run end-to-end with sample data"

### Code Quality Stories (if applicable)
- [ ] Configuration constants story (if 3+ hardcoded values exist)
- [ ] Error handling story (if doing file I/O, network, or external processes)
- [ ] Atomic operations story (if writing data files)
- [ ] Dependency check story (if requiring external tools)
- [ ] Progress feedback story (if operations take >10 seconds)
- [ ] Code quality stories placed after core functionality, grouped together

### Documentation
- [ ] Non-goals section defines clear boundaries
- [ ] Technical Considerations includes constants, patterns, helper functions (if applicable)
- [ ] Saved PRD.md and progress.txt

### Smoke Tests (Python Projects)
- [ ] Identified which user stories create new Python modules
- [ ] Created tests/test_<module>.py for each new module
- [ ] Test files use smoke test template (import, exists, runs, sanity)
- [ ] Test inputs are realistic for the domain
- [ ] Sanity bounds are wide (catching catastrophic errors, not precision)
