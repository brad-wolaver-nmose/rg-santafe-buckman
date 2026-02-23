# IS-XX: [Module Name]

> **Tier 2 Implementation Specification** — A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Draft | Review | Final
**Author:** [Name]
**Created:** YYYY-MM-DD
**Last Updated:** YYYY-MM-DD

---

## 1. Session Goal

One sentence: what this Claude Code session produces.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- [IS-XX: Module Name]

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| | | |

### Domain Knowledge
- See [DS-XX] sections X.Y for [topic]

---

## 3. Context for Claude Code

Brief scientific context sufficient to implement correctly. Include the key equations and conversion factors inline (don't force Claude Code to open another file). Reference DS-XX for deep background.

### Key Equations (Inline)

```
[Equation with variable definitions — copied from DS-XX for self-containedness]
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| | | |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | | |
| R2 | | |
| R3 | | |

---

## 5. Worked Example

Hand-calculable input → output with intermediate steps shown. Use actual Buckman data values where possible.

### Input
```
[Concrete input values]
```

### Calculation Steps
```
Step 1: [operation] → [intermediate result]
Step 2: [operation] → [intermediate result]
Step 3: [operation] → [final result]
```

### Expected Output
```
[Expected output values with units]
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `src/foo.py` | [What it does] |
| Modify | `src/bar.py` | [What changes] |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:
pytest tests/test_foo.py -v --tb=short
ruff check src/foo.py
mypy src/foo.py
```

Expected output: [Describe what passing looks like]

---

## 8. Known Gotchas

- [ ] [Gotcha 1 with explanation]
- [ ] [Gotcha 2 with explanation]

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| | | |

What comes from the prior year's output vs. computed fresh.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
[command]
```

Expected result: [What success looks like]

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-XX | [Domain knowledge used] |
| IS-XX | [Dependency or dependent] |
