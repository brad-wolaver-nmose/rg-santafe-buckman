#!/bin/bash
# Ralph - Autonomous coding agent loop
#
# Usage: ./ralph.sh [ITERATIONS] [SLEEP] [DOC_PATH]
#   ITERATIONS: Max iterations (default: 10)
#   SLEEP: Seconds between iterations (default: 2)
#   DOC_PATH: Document to process (default: PRD.md)
#
# Examples:
#   ./ralph.sh                           # Process PRD.md, 10 iterations
#   ./ralph.sh 20 2 CODE_REVIEW_CHECKLIST.md   # Process review checklist
#   ./ralph.sh 15 2 CODE_FIXES_PRD.md    # Process fix PRD

set -e

ITERATIONS=${1:-10}
SLEEP=${2:-2}
DOC_PATH=${3:-PRD.md}

echo "Starting Ralph - ITERATIONS: $ITERATIONS, DOC: $DOC_PATH"
echo ""

for ((i=1; i<=$ITERATIONS; i++)); do
    echo "==========================================="
    echo "  Iteration $i of $ITERATIONS"
    echo "==========================================="

    result=$(claude --dangerously-skip-permissions -p "You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

## Steps

1. Read $DOC_PATH and find the first task that is NOT complete (marked [ ]).
2. Read progress.txt - check the Learnings section first for patterns from previous iterations.
3. Implement that ONE task only.
4. Run tests/typecheck to verify it works.

## Critical: Only Complete If Tests Pass

- If tests PASS:
  - Update $DOC_PATH to mark the task complete (change [ ] to [x])
  - Commit your changes with message: feat: [task description]
  - Append what worked to progress.txt

- If tests FAIL:
  - Do NOT mark the task complete
  - Do NOT commit broken code
  - Append what went wrong to progress.txt (so next iteration can learn)

## Progress Notes Format

Append to progress.txt using this format:

## Iteration [N] - [Task Name]
- What was implemented
- Files changed
- Learnings for future iterations:
  - Patterns discovered
  - Gotchas encountered
  - Useful context
---

## Update AGENTS.md (If Applicable)

If you discover a reusable pattern that future work should know about:
- Check if AGENTS.md exists in the project root
- Add patterns like: 'This codebase uses X for Y' or 'Always do Z when changing W'
- Only add genuinely reusable knowledge, not task-specific details

## End Condition

After completing your task, check $DOC_PATH:
- If ALL tasks are [x], output exactly: <promise>COMPLETE</promise>
- If tasks remain [ ], just end your response (next iteration will continue)" 2>&1 | tee /dev/tty)

    echo ""

    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
        echo "==========================================="
        echo "  All tasks complete after $i iterations!"
        echo "==========================================="
        exit 0
    fi

    sleep $SLEEP
done

echo "==========================================="
echo "  Reached max iterations ($ITERATIONS)"
echo "==========================================="
exit 1
