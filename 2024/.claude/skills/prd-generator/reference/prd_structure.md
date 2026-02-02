# PRD Output Structure

Generate the PRD with these sections:

### 1. Introduction
Brief description of the feature and the problem it solves.

### 2. Goals
Specific, measurable objectives (bullet list).

### 3. User Stories
Each story needs:
- **ID:** Sequential (US-001, US-002, etc.)
- **Title:** Short descriptive name
- **Description:** "As a [user], I want [feature] so that [benefit]"
- **Acceptance Criteria:** Verifiable checklist

**Format:**
```markdown
### US-001: [Title]
**Description:** As a [user], I want [feature] so that [benefit].

**Acceptance Criteria:**
- [ ] Specific verifiable criterion
- [ ] Another criterion
- [ ] Typecheck passes
- [ ] [UI stories] Verify changes work in browser
```

**For Python modules, pair with smoke test:**
When a story creates a new `.py` module, the corresponding `tests/test_<module>.py` should also be created. See [smoke_test_scaffolding.md](smoke_test_scaffolding.md) for the template.

### 4. Non-Goals
What this feature will NOT include. Critical for scope.

### 5. Technical Considerations (Optional)
Document technical patterns and implementation details:

**For all projects:**
- Known constraints (APIs, rate limits, browser compatibility)
- Existing components to reuse (UI libraries, utility functions)
- Dependencies and version requirements

**For code-heavy projects, also include:**
- Configuration constants (with values and descriptions)
- Error handling patterns (atomic writes, dependency checks)
- Data validation approaches
- Helper function signatures for critical operations

**Example:**
```markdown
## Technical Considerations

### Configuration Constants
| Constant | Value | Description |
|----------|-------|-------------|
| CONFIDENCE_THRESHOLD | 95 | Minimum OCR confidence % to accept |
| MAX_RETRIES | 3 | Number of retry attempts for API calls |
| TIMEOUT_SECONDS | 30 | Request timeout in seconds |

### Error Handling Patterns
- Use atomic file writes (tempfile + move) for all data outputs
- Check system dependencies at startup with helpful error messages
- Include exception type and file path in all error logs

### Helper Functions
```python
def is_confident(confidence: int, threshold: int = 95) -> bool:
    """Check if confidence score meets threshold, handling -1 invalid case."""
```
```
