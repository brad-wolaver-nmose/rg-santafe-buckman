# Example: Full PRD Generation Flow

Here's a complete example showing the entire PRD generation process:

---

**User:** I want to build a task priority system for my todo app.

---

**Claude:**

Thank you for that description. Based on what you've shared, I understand:
- You have an existing todo application
- You want to add priority levels to tasks
- This will help users focus on what matters most

With this foundation, let me ask some questions to ensure we capture everything needed for a thorough PRD.

I'll be asking 11 questions across 4 topic areas. Priority systems seem simple but have important UX implications—how priorities are displayed, selected, and filtered significantly impacts daily usability. Getting these details right now prevents frustrating rework later.

Topic areas I'll cover:
- User Context & Goals
- Core Functionality
- UI/UX Requirements
- Scope & Constraints

---

### User Context & Goals

**Question 1 of 11** - Understanding why users need priorities helps design the right solution.

1. What's the main reason users need task priorities?
   A. To see urgent tasks first in a long list
   B. To plan their day by importance
   C. To communicate urgency to team members
   D. To meet external deadlines
   E. To see urgent tasks first (Recommended: Most common need for personal todo apps.)
   F. Let's brainstorm together to explore this further
   G. Something else: [please specify]

   → Recommendation: E. For personal todo apps, visual scanning of urgent items is the primary use case.

**Question 2 of 11** - Different user types have different priority needs.

2. Who primarily uses this todo app?
   A. Individual users (personal tasks)
   B. Small teams (shared tasks)
   C. Both individual and team contexts
   D. Enterprise users with complex workflows
   E. Individual users (Recommended: Simpler priority model works best here.)
   F. Let's brainstorm together to explore this further
   G. Something else: [please specify]

   → Recommendation: E. Individual users benefit from straightforward priority without collaboration complexity.

---

### Core Functionality

**Question 3 of 11** - The number of priority levels affects both UX and decision fatigue.

3. How many priority levels should exist?
   A. Two (high/normal)
   B. Three (high/medium/low)
   C. Four (urgent/high/medium/low)
   D. Five or more with custom labels
   E. Three levels (Recommended: Balances expressiveness with quick decisions.)
   F. Let's brainstorm together to explore this further
   G. Something else: [please specify]

   → Recommendation: E. Three levels (high/medium/low) is the sweet spot—expressive enough without causing decision paralysis.

[...questions 4-11 continue similarly...]

---

**User responds:** 1E, 2E, 3E, 4A, 5B, 6F, 7A, 8E, 9B, 10A, 11E

---

**Claude:** You selected F (brainstorm) for Question 6. Let's explore that now.

**Question 6 was:** How should priority be displayed on task cards?

Let's think through this together. A few considerations:
- Color coding is fast to scan but can be problematic for colorblind users
- Icons are accessible but add visual clutter
- Badge/pill style is common but takes horizontal space
- Position-based (priority tasks at top) uses no extra visual element

What matters most to you—scannability, accessibility, minimal visual clutter, or something else?

---

**User:** I want it scannable but also accessible. Not too cluttered. Done.

---

**Claude:** Great input. I now have enough information.

Based on our brainstorming, here's the updated question:

**Question 6 of 11** (Revised)

6. How should priority be displayed on task cards?
   A. Colored left border (subtle, scannable, accessible with pattern)
   B. Small icon + color (redundant cues for accessibility)
   C. Text badge with background color
   D. Priority shown only on hover/focus
   E. Colored left border with pattern (Recommended: Based on our discussion, this balances scannability and accessibility while staying minimal.)
   F. Let's brainstorm more
   G. Something else: [please specify]

   → Recommendation: E. The border approach is subtle, fast to scan, and can include patterns for accessibility.

**Your answer?**

---

**User:** 6E

---

**Claude:**

## Summary of Your Answers

### User Context & Goals
- Q1: E - See urgent tasks first in long lists
- Q2: E - Individual users (personal tasks)

### Core Functionality
- Q3: E - Three priority levels (high/medium/low)
- Q4: A - Default new tasks to medium priority
- Q5: B - Allow changing priority from task list (no modal needed)

### UI/UX Requirements
- Q6: E (brainstormed) - Colored left border with pattern for accessibility
- Q7: A - Filter dropdown in toolbar
- Q8: E - Sort by priority as default, user can change

### Scope & Constraints
- Q9: B - No priority-based notifications (keep it simple)
- Q10: A - No due date interaction (separate feature)
- Q11: E - No bulk priority changes in v1

---

**Are you satisfied with these answers?**

- To brainstorm any question further, type the question number(s) (e.g., "3" or "3, 6, 14")
- Type "done" or "generate PRD" when ready to proceed

---

**User:** done

---

**Claude:** Generating your PRD now...

[PRD is generated and saved to PRD.md]

---

## Example PRD Output

```markdown
# PRD: Task Priority System

## Introduction

Add priority levels to tasks so users can focus on what matters most. Tasks can be marked as high, medium, or low priority, with visual indicators and filtering.

## Goals

- Allow assigning priority (high/medium/low) to any task
- Provide clear visual differentiation that is accessible
- Enable filtering by priority
- Default new tasks to medium priority
- Sort by priority by default

## User Stories

### US-001: Add priority field to database
**Description:** As a developer, I need to store task priority so it persists across sessions.

**Acceptance Criteria:**
- [ ] Add priority column: 'high' | 'medium' | 'low' (default 'medium')
- [ ] Generate and run migration successfully
- [ ] Typecheck passes

### US-002: Display priority indicator on task cards
**Description:** As a user, I want to see task priority at a glance so I know what needs attention first.

**Acceptance Criteria:**
- [ ] Each task card shows colored left border (red=high, yellow=medium, gray=low)
- [ ] Border includes subtle pattern for colorblind accessibility
- [ ] Priority visible without hovering or clicking
- [ ] Typecheck passes
- [ ] Verify changes work in browser

### US-003: Add priority selector to task list
**Description:** As a user, I want to change a task's priority directly from the list without opening a modal.

**Acceptance Criteria:**
- [ ] Priority dropdown appears on task row hover/focus
- [ ] Shows current priority as selected
- [ ] Saves immediately on selection change
- [ ] Typecheck passes
- [ ] Verify changes work in browser

### US-004: Filter tasks by priority
**Description:** As a user, I want to filter the task list to see only high-priority items when I'm focused.

**Acceptance Criteria:**
- [ ] Filter dropdown in toolbar with options: All | High | Medium | Low
- [ ] Filter persists in URL params
- [ ] Empty state message when no tasks match filter
- [ ] Typecheck passes
- [ ] Verify changes work in browser

### US-005: Sort by priority as default
**Description:** As a user, I want tasks sorted by priority by default so urgent items appear first.

**Acceptance Criteria:**
- [ ] Default sort order: high → medium → low
- [ ] User can change sort order via sort dropdown
- [ ] Sort preference persists in URL params
- [ ] Typecheck passes
- [ ] Verify changes work in browser

## Non-Goals

- No priority-based notifications or reminders
- No automatic priority assignment based on due date
- No bulk priority changes (v1)
- No priority inheritance for subtasks

## Technical Considerations

### Existing Components
- Reuse existing dropdown component for priority selector
- Filter and sort state managed via URL search params

### Visual Design
- Border patterns: solid (high), dashed (medium), dotted (low)
- Colors: red (high), yellow (medium), gray (low)
```
