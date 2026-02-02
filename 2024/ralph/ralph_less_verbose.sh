#!/bin/bash
# =============================================================================
# RALPH LESS VERBOSE - Autonomous Coding Agent Loop (Optimized for Code Review)
# =============================================================================
#
# Based on ralph_enhanced.sh but optimized to reduce review time from 12+ hours
# to 2-3 hours by:
#   - Constraining progress.txt entries to 2-3 lines each
#   - Reading only the last 20 lines of progress.txt (not the entire file)
#   - Skipping test verification on read-only iterations (no code changes)
#   - Capping output verbosity (500 word limit per response)
#   - Removing Python-specific smoke test templates
#
# USAGE
# =====
#
#   ./ralph_less_verbose.sh [ITERATIONS] [SLEEP] [DOC_PATH] [MAX_TASK_TRIES] [TEST_CMD]
#
#   All arguments are optional and positional (order matters):
#
#   ITERATIONS     How many times to loop before giving up (default: 10)
#   SLEEP          Seconds to wait between iterations (default: 2)
#   DOC_PATH       Your task list file (default: PRD.md)
#   MAX_TASK_TRIES How many times to retry one task before skipping (default: 3)
#   TEST_CMD       Command to run tests (default: auto-detect)
#
# EXAMPLES
# ========
#
#   # Code review with 60 stories
#   ./ralph_less_verbose.sh 65 2 CODE_REVIEW_CHECKLIST.md
#
#   # Use all defaults
#   ./ralph_less_verbose.sh
#
# =============================================================================

set -e  # Exit on error (we'll handle errors explicitly where needed)

# =============================================================================
# CONFIGURATION
# =============================================================================

ITERATIONS=${1:-10}
SLEEP=${2:-2}
DOC_PATH=${3:-PRD.md}
MAX_TASK_TRIES=${4:-3}
TEST_CMD=${5:-""}

# TERMINAL COLORS
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# STATE TRACKING FILES
PROGRESS_FILE="progress.txt"
STATE_FILE=".ralph_state.json"
LOG_FILE=".ralph_log.jsonl"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_event() {
    local event_type="$1"
    local message="$2"
    local details="${3:-{}}"
    echo "{\"timestamp\":\"$(timestamp)\",\"event\":\"$event_type\",\"message\":\"$message\",\"details\":$details}" >> "$LOG_FILE"
}

check_dependencies() {
    local missing_deps=()

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo ""
        status "$RED" "ERROR" "Missing required system dependencies"
        echo ""

        for dep in "${missing_deps[@]}"; do
            echo "  Required: $dep"
        done

        echo ""
        echo "Installation instructions:"
        echo "  - Linux/Ubuntu: sudo apt-get install ${missing_deps[@]}"
        echo "  - macOS:        brew install ${missing_deps[@]}"
        echo ""

        exit 1
    fi
}

status() {
    local color="$1"
    local prefix="$2"
    local message="$3"
    echo -e "${color}[${prefix}]${NC} $message"
}

detect_test_command() {
    local has_test_files=false

    if ls test_*.py 1> /dev/null 2>&1 || ls *_test.py 1> /dev/null 2>&1; then
        has_test_files=true
    fi

    if [[ -d "tests" ]]; then
        if ls tests/test_*.py 1> /dev/null 2>&1 || ls tests/*_test.py 1> /dev/null 2>&1; then
            has_test_files=true
        fi
    fi

    if [[ "$has_test_files" == true ]]; then
        echo "pytest"
        return 0
    fi

    if [[ -f "package.json" ]]; then
        echo "npm test"
        return 0
    fi

    if [[ -f "Makefile" ]] && grep -q "^test:" Makefile; then
        echo "make test"
        return 0
    fi

    if ls *.py 1> /dev/null 2>&1; then
        echo "python3 -m py_compile *.py"
        return 0
    fi

    echo ""
}

get_current_task() {
    local first_unchecked=$(grep -m1 '\- \[ \]' "$DOC_PATH" 2>/dev/null || echo "")

    if [[ -z "$first_unchecked" ]]; then
        echo ""
    else
        echo "$first_unchecked" | sed 's/^- \[ \] //'
    fi
}

count_remaining_tasks() {
    local count
    count=$(grep -c '\- \[ \]' "$DOC_PATH" 2>/dev/null) || true
    echo "${count:-0}"
}

count_completed_tasks() {
    local count
    count=$(grep -c '\- \[x\]' "$DOC_PATH" 2>/dev/null) || true
    echo "${count:-0}"
}

init_state() {
    if [[ -f "$STATE_FILE" ]]; then
        CURRENT_TASK=$(jq -r '.current_task // ""' "$STATE_FILE")
        TASK_ATTEMPTS=$(jq -r '.task_attempts // 0' "$STATE_FILE")
        SKIPPED_TASKS=$(jq -r '.skipped_tasks // []' "$STATE_FILE")
    else
        CURRENT_TASK=""
        TASK_ATTEMPTS=0
        SKIPPED_TASKS="[]"
        save_state
    fi
}

save_state() {
    cat > "$STATE_FILE" << EOF
{
    "current_task": "$CURRENT_TASK",
    "task_attempts": $TASK_ATTEMPTS,
    "skipped_tasks": $SKIPPED_TASKS,
    "last_updated": "$(timestamp)"
}
EOF
}

skip_task() {
    local task="$1"
    local reason="$2"

    local escaped_task=$(echo "$task" | sed 's/"/\\"/g')

    SKIPPED_TASKS=$(echo "$SKIPPED_TASKS" | jq --arg t "$escaped_task" --arg r "$reason" '. + [{"task": $t, "reason": $r}]')

    log_event "TASK_SKIPPED" "$task" "{\"reason\":\"$reason\",\"attempts\":$TASK_ATTEMPTS}"

    TASK_ATTEMPTS=0
    CURRENT_TASK=""
    save_state
}

verify_tests_pass() {
    if [[ -z "$TEST_CMD" ]]; then
        status "$YELLOW" "WARN" "No test command configured - skipping independent verification"
        return 0
    fi

    status "$BLUE" "TEST" "Running: $TEST_CMD"

    set +e
    eval "$TEST_CMD" > .ralph_test_output.txt 2>&1
    local exit_code=$?
    set -e

    if [[ $exit_code -eq 0 ]]; then
        status "$GREEN" "PASS" "Tests passed independently"
        log_event "TESTS_PASSED" "Independent verification successful" "{\"command\":\"$TEST_CMD\"}"
        return 0
    else
        status "$RED" "FAIL" "Tests failed independently (exit code: $exit_code)"
        log_event "TESTS_FAILED" "Independent verification failed" "{\"command\":\"$TEST_CMD\",\"exit_code\":$exit_code}"

        echo "--- Test Output (last 20 lines) ---"
        tail -20 .ralph_test_output.txt
        echo "-----------------------------------"

        return 1
    fi
}

rollback_changes() {
    status "$YELLOW" "ROLLBACK" "Stashing uncommitted changes due to failure"

    if git diff --quiet && git diff --cached --quiet; then
        status "$BLUE" "INFO" "No uncommitted changes to rollback"
        return 0
    fi

    local stash_msg="ralph-rollback-iteration-$1-$(timestamp)"
    git stash push -m "$stash_msg" --include-untracked

    log_event "ROLLBACK" "Changes stashed" "{\"stash_message\":\"$stash_msg\"}"
    status "$GREEN" "OK" "Changes stashed as: $stash_msg"
}

# -----------------------------------------------------------------------------
# has_code_changes() - Check if there are uncommitted code changes
# -----------------------------------------------------------------------------
# Returns 0 (true) if there are uncommitted changes, 1 (false) if clean.
# Used to skip test verification on read-only review iterations where
# no source code was modified.
has_code_changes() {
    if git diff --quiet && git diff --cached --quiet; then
        return 1  # No changes
    else
        return 0  # Has changes
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

echo ""
echo "==========================================="
echo "  Ralph Less Verbose - Code Review Agent"
echo "==========================================="
echo ""

check_dependencies

# Validate inputs
if [[ ! -f "$DOC_PATH" ]]; then
    status "$RED" "ERROR" "Document not found: $DOC_PATH"
    exit 1
fi

# Auto-detect or validate test command
if [[ -z "$TEST_CMD" ]]; then
    TEST_CMD=$(detect_test_command)

    if [[ -n "$TEST_CMD" ]]; then
        status "$GREEN" "DETECT" "Auto-detected test command: $TEST_CMD"

        if [[ "$TEST_CMD" == "pytest" ]]; then
            status "$BLUE" "INFO" "Protection level: SMOKE TESTS (catches runtime failures + basic sanity)"
        elif [[ "$TEST_CMD" == *"py_compile"* ]]; then
            status "$YELLOW" "INFO" "Protection level: SYNTAX ONLY (catches broken code, not logic errors)"
        else
            status "$BLUE" "INFO" "Protection level: PROJECT DEFAULT ($TEST_CMD)"
        fi
    else
        status "$YELLOW" "WARN" "No test command detected - independent verification disabled"
    fi
fi

# Show configuration
echo "Configuration:"
echo "  Max iterations:     $ITERATIONS"
echo "  Sleep between:      ${SLEEP}s"
echo "  Document:           $DOC_PATH"
echo "  Max tries per task: $MAX_TASK_TRIES"
echo "  Test command:       ${TEST_CMD:-'(none)'}"
echo ""

# Initialize state
init_state

REMAINING=$(count_remaining_tasks)
COMPLETED=$(count_completed_tasks)
status "$BLUE" "START" "Tasks: $COMPLETED completed, $REMAINING remaining"
echo ""

# =============================================================================
# MAIN LOOP
# =============================================================================

for ((i=1; i<=ITERATIONS; i++)); do
    echo "==========================================="
    echo "  Iteration $i of $ITERATIONS"
    echo "==========================================="

    TASK=$(get_current_task)

    if [[ -z "$TASK" ]]; then
        status "$GREEN" "COMPLETE" "All tasks finished!"
        log_event "ALL_COMPLETE" "All tasks marked complete" "{\"iterations\":$i}"

        SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
        if [[ "$SKIP_COUNT" -gt 0 ]]; then
            status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped due to repeated failures:"
            echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task): \(.reason)"'
        fi

        rm -f "$STATE_FILE"
        exit 0
    fi

    if [[ "$TASK" != "$CURRENT_TASK" ]]; then
        CURRENT_TASK="$TASK"
        TASK_ATTEMPTS=0
        status "$BLUE" "NEW" "New work detected - resetting attempt counter"
    fi

    ((TASK_ATTEMPTS++)) || true

    if [[ $TASK_ATTEMPTS -gt $MAX_TASK_TRIES ]]; then
        status "$RED" "STUCK" "Task failed $MAX_TASK_TRIES times - skipping: $TASK"
        skip_task "$TASK" "Exceeded max attempts ($MAX_TASK_TRIES)"
        rollback_changes "$i"
        sleep "$SLEEP"
        continue
    fi

    status "$BLUE" "ATTEMPT" "Attempt $TASK_ATTEMPTS of $MAX_TASK_TRIES for: $TASK"
    save_state

    log_event "ITERATION_START" "Beginning iteration" "{\"iteration\":$i,\"task\":\"$TASK\",\"attempt\":$TASK_ATTEMPTS}"

    FAILURE_CONTEXT=""
    if [[ $TASK_ATTEMPTS -gt 1 ]]; then
        FAILURE_CONTEXT="

## IMPORTANT: This is attempt $TASK_ATTEMPTS of $MAX_TASK_TRIES for this task!

Previous attempts failed. Before making changes:
1. Read the last 20 lines of progress.txt - see what went wrong before
2. Try a DIFFERENT approach than previous attempts
3. If the same approach keeps failing, the task may need to be broken down

Do NOT repeat the same fix that already failed."
    fi

    # -------------------------------------------------------------------------
    # BUILD THE PROMPT (optimized for less verbose output)
    # -------------------------------------------------------------------------

    PROMPT="You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

**OUTPUT LIMIT: Keep your response under 500 words. Be concise. No exhaustive enumeration.**

## Steps

1. Read $DOC_PATH and find the first user story that is NOT complete.
   - Look for story sections (### US-XXX) with unchecked criteria (- [ ])
   - Work on the FIRST incomplete story, not individual checkboxes
2. Read ONLY the last 20 lines of progress.txt (use offset/limit or tail). Do NOT read the entire file.
3. Implement that ONE story only - complete ALL its acceptance criteria.

4. Implement the changes, run builds/tests as needed, and report results accurately.
$FAILURE_CONTEXT
## Critical Rules - READ CAREFULLY

### Rules
- Only mark [x] after ALL acceptance criteria for a story are met.
- Run builds and tests to verify changes compile and pass.
- Do not hardcode values or game test results.

### Rule 4: Failure Logging
If the task fails, append to progress.txt (MAX 4 lines):
\`\`\`
## Iteration $i - FAILED (Attempt $TASK_ATTEMPTS) | [story ID]
- Error: [one sentence]
- Next: [one sentence - different approach]
---
\`\`\`

### Rule 5: Success Logging
If the task succeeds, append to progress.txt (MAX 2 lines):
\`\`\`
## Iteration $i - OK | [story ID] | [PASS/FAIL/ACCEPTABLE] | [one-sentence finding]
---
\`\`\`

## End Condition

After completing work:
- If task succeeded AND all tasks in $DOC_PATH are now [x]: output exactly: <promise>COMPLETE</promise>
- If task failed OR tasks remain: just end your response"

    # -------------------------------------------------------------------------
    # Execute Claude
    # -------------------------------------------------------------------------

    set +e
    result=$(claude --dangerously-skip-permissions -p "$PROMPT" 2>&1 | tee /dev/tty)
    claude_exit_code=$?
    set -e

    echo ""

    # -------------------------------------------------------------------------
    # POST-EXECUTION VERIFICATION
    # -------------------------------------------------------------------------

    # CHECK 1: Did Claude claim everything is done?
    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
        status "$BLUE" "VERIFY" "Claude claims all tasks complete - verifying..."

        if has_code_changes; then
            if verify_tests_pass; then
                REMAINING=$(count_remaining_tasks)
                if [[ "$REMAINING" -eq 0 ]]; then
                    status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations!"
                    log_event "ALL_COMPLETE" "Verified all tasks complete" "{\"iterations\":$i}"

                    SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
                    if [[ "$SKIP_COUNT" -gt 0 ]]; then
                        echo ""
                        status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
                        echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task)"'
                    fi

                    rm -f "$STATE_FILE"
                    exit 0
                else
                    status "$YELLOW" "MISMATCH" "Claude said complete but $REMAINING tasks remain unchecked"
                    log_event "COMPLETION_MISMATCH" "Claude claimed complete but tasks remain" "{\"remaining\":$REMAINING}"
                fi
            else
                status "$RED" "VERIFY_FAIL" "Claude claimed complete but tests fail!"
                log_event "FALSE_COMPLETION" "Claude claimed complete but tests fail" "{}"
                rollback_changes "$i"
            fi
        else
            # No code changes — skip test verification for read-only review
            status "$BLUE" "SKIP" "No code changes - skipping test verification"
            REMAINING=$(count_remaining_tasks)
            if [[ "$REMAINING" -eq 0 ]]; then
                status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations!"
                log_event "ALL_COMPLETE" "Verified all tasks complete" "{\"iterations\":$i}"

                SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
                if [[ "$SKIP_COUNT" -gt 0 ]]; then
                    echo ""
                    status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
                    echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task)"'
                fi

                rm -f "$STATE_FILE"
                exit 0
            else
                status "$YELLOW" "MISMATCH" "Claude said complete but $REMAINING tasks remain unchecked"
                log_event "COMPLETION_MISMATCH" "Claude claimed complete but tasks remain" "{\"remaining\":$REMAINING}"
            fi
        fi
    fi

    # CHECK 2: Did Claude mark a task complete?
    NEW_TASK=$(get_current_task)
    if [[ "$NEW_TASK" != "$TASK" ]] && [[ -n "$TASK" ]]; then
        status "$BLUE" "VERIFY" "Task marked complete - checking for code changes..."

        if has_code_changes; then
            # Code was modified — run test verification
            status "$BLUE" "VERIFY" "Code changes detected - running independent test verification..."
            if verify_tests_pass; then
                status "$GREEN" "VERIFIED" "Task completion verified: $TASK"
                log_event "TASK_COMPLETE" "Task verified complete" "{\"task\":\"$TASK\",\"attempts\":$TASK_ATTEMPTS}"

                TASK_ATTEMPTS=0
                CURRENT_TASK="$NEW_TASK"
                save_state

                REMAINING=$(count_remaining_tasks)
                if [[ "$REMAINING" -eq 0 ]]; then
                    status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations!"
                    log_event "ALL_COMPLETE" "Verified all tasks complete" "{\"iterations\":$i}"

                    SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
                    if [[ "$SKIP_COUNT" -gt 0 ]]; then
                        echo ""
                        status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
                        echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task)"'
                    fi

                    rm -f "$STATE_FILE"
                    exit 0
                fi
            else
                status "$RED" "REJECT" "Task marked complete but tests fail - rolling back"
                log_event "FALSE_COMPLETION" "Task marked complete but tests fail" "{\"task\":\"$TASK\"}"
                rollback_changes "$i"
                status "$YELLOW" "REVERTED" "All changes rolled back including checkbox marks - will retry"
            fi
        else
            # No code changes — read-only review iteration, skip tests
            status "$BLUE" "SKIP" "No code changes - skipping test verification"
            status "$GREEN" "VERIFIED" "Task completion verified (read-only): $TASK"
            log_event "TASK_COMPLETE" "Task verified complete (read-only)" "{\"task\":\"$TASK\",\"attempts\":$TASK_ATTEMPTS}"

            TASK_ATTEMPTS=0
            CURRENT_TASK="$NEW_TASK"
            save_state

            REMAINING=$(count_remaining_tasks)
            if [[ "$REMAINING" -eq 0 ]]; then
                status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations!"
                log_event "ALL_COMPLETE" "Verified all tasks complete" "{\"iterations\":$i}"

                SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
                if [[ "$SKIP_COUNT" -gt 0 ]]; then
                    echo ""
                    status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
                    echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task)"'
                fi

                rm -f "$STATE_FILE"
                exit 0
            fi
        fi
    fi

    # Show progress update
    REMAINING=$(count_remaining_tasks)
    COMPLETED=$(count_completed_tasks)
    status "$BLUE" "PROGRESS" "Tasks: $COMPLETED completed, $REMAINING remaining"

    sleep "$SLEEP"
done

# =============================================================================
# MAX ITERATIONS REACHED
# =============================================================================

echo ""
echo "==========================================="
status "$YELLOW" "LIMIT" "Reached max iterations ($ITERATIONS)"
echo "==========================================="

REMAINING=$(count_remaining_tasks)
COMPLETED=$(count_completed_tasks)

echo ""
echo "Final Status:"
echo "  Completed: $COMPLETED"
echo "  Remaining: $REMAINING"

SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
if [[ "$SKIP_COUNT" -gt 0 ]]; then
    echo "  Skipped:   $SKIP_COUNT"
    echo ""
    echo "Skipped tasks (failed $MAX_TASK_TRIES+ times each):"
    echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task): \(.reason)"'
fi

log_event "MAX_ITERATIONS" "Reached iteration limit" "{\"completed\":$COMPLETED,\"remaining\":$REMAINING,\"skipped\":$SKIP_COUNT}"

echo ""
echo "What to do next:"
echo "  1. Review $LOG_FILE for detailed execution history"
echo "  2. Review $PROGRESS_FILE for task-level notes"
echo "  3. Check skipped tasks - they may need to be broken into smaller pieces"
echo "  4. Run again with more iterations: ./ralph_less_verbose.sh $((ITERATIONS + 10))"

exit 1
