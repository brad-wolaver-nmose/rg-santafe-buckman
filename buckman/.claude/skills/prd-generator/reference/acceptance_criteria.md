# Acceptance Criteria Reference

## Acceptance Criteria (Must Be Verifiable)

Each criterion must be something Ralph can CHECK, not something vague.

### Good criteria (verifiable):
- "Add `status` column to tasks table with default 'pending'"
- "Filter dropdown has options: All, Active, Completed"
- "Clicking delete shows confirmation dialog"
- "Script processes all 12 months and generates output CSV"
- "Function returns (year, month_name, month_numeric, month_abbrev) tuple"
- "Typecheck passes"
- "Tests pass"

### Bad criteria (vague):
- "Works correctly"
- "User can do X easily"
- "Good UX"
- "Handles edge cases"
- "Properly processes data"
- "Error handling works"

### Always include as final criterion:
```
"Typecheck passes"
```

### For stories that change UI, also include:
```
"Verify changes work in browser"
```

### For data processing/scripts, also include:
```
"Run script end-to-end with sample data successfully"
```
