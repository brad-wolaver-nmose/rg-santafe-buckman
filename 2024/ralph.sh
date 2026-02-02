#!/bin/bash
# =============================================================================
# RALPH - Autonomous Coding Agent Loop with Guardrails
# =============================================================================
#
# General-purpose agent loop that works through a checklist (PRD.md or
# CODE_REVIEW_CHECKLIST.md) one task at a time, verifying each before
# marking complete.
#
# Two modes:
#   dev    - Full development workflow with smoke tests, verbose logging,
#            always-verify-tests behavior (default)
#   review - Optimized for code review: condensed logging, 500-word limit,
#            skips tests when no code changes detected
#
# USAGE
# =====
#
#   ./ralph.sh [--mode dev|review] [ITERATIONS] [SLEEP] [DOC_PATH] [MAX_TASK_TRIES] [TEST_CMD]
#
#   --mode         dev (default) or review
#   ITERATIONS     How many times to loop (default: 10)
#   SLEEP          Seconds between iterations (default: 2)
#   DOC_PATH       Task list file (default: PRD.md)
#   MAX_TASK_TRIES Retries per task before skipping (default: 3)
#   TEST_CMD       Test command (default: auto-detect)
#
# EXAMPLES
# ========
#
#   # Development - work through PRD
#   ./ralph.sh 15 2 PRD.md
#
#   # Code review - 60 stories
#   ./ralph.sh --mode review 65 2 CODE_REVIEW_CHECKLIST.md
#
#   # Specify test command
#   ./ralph.sh --mode dev 15 2 PRD.md 3 "pytest tests/ -v"
#
# =============================================================================

set -e

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

# Parse named arguments first (--mode), then positional
MODE="dev"
while [[ $# -gt 0 && "$1" == --* ]]; do
    case "$1" in
        --mode)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --mode requires a value (dev or review)"
                exit 1
            fi
            MODE="$2"
            if [[ "$MODE" != "dev" && "$MODE" != "review" ]]; then
                echo "Error: --mode must be 'dev' or 'review', got '$MODE'"
                exit 1
            fi
            shift 2
            ;;
        *)
            echo "Error: Unknown option '$1'"
            echo "Usage: ./ralph.sh [--mode dev|review] [ITERATIONS] [SLEEP] [DOC_PATH] [MAX_TASK_TRIES] [TEST_CMD]"
            exit 1
            ;;
    esac
done

# Positional arguments (after named args consumed)
ITERATIONS=${1:-10}
SLEEP=${2:-2}
DOC_PATH=${3:-PRD.md}
MAX_TASK_TRIES=${4:-3}
TEST_CMD=${5:-""}

# =============================================================================
# CONFIGURATION
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROGRESS_FILE="progress.txt"
STATE_FILE=".ralph_state.json"
LOG_FILE=".ralph_log.jsonl"
TEST_OUTPUT_FILE=".ralph_test_output.txt"

START_TIME=$(date +%s)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

elapsed_time() {
    local now=$(date +%s)
    local elapsed=$((now - START_TIME))
    local hours=$((elapsed / 3600))
    local minutes=$(( (elapsed % 3600) / 60 ))
    local seconds=$((elapsed % 60))
    printf "%02d:%02d:%02d" $hours $minutes $seconds
}

log_event() {
    local event_type="$1"
    local message="$2"
    local details="${3:-{}}"
    echo "{\"timestamp\":\"$(timestamp)\",\"event\":\"$event_type\",\"message\":\"$message\",\"details\":$details}" >> "$LOG_FILE"
}

status() {
    local color="$1"
    local prefix="$2"
    local message="$3"
    echo -e "${color}[${prefix}]${NC} $message"
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

# -----------------------------------------------------------------------------
# version_file() - Archive existing file with version suffix
# -----------------------------------------------------------------------------
# If file exists, rename to file_v0.ext, file_v1.ext, etc.
# Finds next available version number to avoid overwriting.
version_file() {
    local filepath="$1"
    if [[ ! -f "$filepath" ]]; then return 0; fi

    local dir=$(dirname "$filepath")
    local filename=$(basename "$filepath")

    # Split filename into base and extension(s)
    # Handle dotfiles like .ralph_log.jsonl and regular files like progress.txt
    if [[ "$filename" == .* ]]; then
        # Dotfile: .ralph_log.jsonl -> base=.ralph_log, ext=jsonl
        local without_leading_dot="${filename#.}"
        local base_part="${without_leading_dot%%.*}"
        local ext_part="${without_leading_dot#*.}"
        local base=".${base_part}"
        local ext="$ext_part"
    else
        # Regular file: progress.txt -> base=progress, ext=txt
        local base="${filename%%.*}"
        local ext="${filename#*.}"
    fi

    # Find next available version number
    local version=0
    while [[ -f "${dir}/${base}_v${version}.${ext}" ]]; do
        ((version++))
    done

    mv "$filepath" "${dir}/${base}_v${version}.${ext}"
    status "$BLUE" "VERSION" "Archived: $filepath -> ${base}_v${version}.${ext}"
}

# -----------------------------------------------------------------------------
# Checklist functions - handle both PRD and review checklist formats
# -----------------------------------------------------------------------------
# PRD.md format:          "- [ ] criterion text"
# Review checklist format: "### US-R01: Title [ ]"
# Grep pattern \[ \] matches both without requiring dash prefix.

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
    local first_unchecked=$(grep -m1 '\[ \]' "$DOC_PATH" 2>/dev/null || echo "")

    if [[ -z "$first_unchecked" ]]; then
        echo ""
    else
        # Strip common prefixes: "- [ ] " or "### US-RXX: ... [ ]"
        echo "$first_unchecked" | sed -e 's/^- \[ \] //' -e 's/^[# ]*//' -e 's/ \[ \]$//'
    fi
}

count_remaining_tasks() {
    local count
    count=$(grep -c '\[ \]' "$DOC_PATH" 2>/dev/null) || true
    echo "${count:-0}"
}

count_completed_tasks() {
    local count
    count=$(grep -c '\[x\]' "$DOC_PATH" 2>/dev/null) || true
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
    eval "$TEST_CMD" > "$TEST_OUTPUT_FILE" 2>&1
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
        tail -20 "$TEST_OUTPUT_FILE"
        echo "-----------------------------------"

        return 1
    fi
}

rollback_changes() {
    status "$YELLOW" "ROLLBACK" "Stashing uncommitted changes due to failure"

    if git diff --quiet && git diff --cached --quiet && \
       [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
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
# Returns 0 (true) if there are uncommitted changes or untracked files,
# 1 (false) if working tree is clean.
has_code_changes() {
    # Check tracked file changes (staged + unstaged)
    if ! git diff --quiet || ! git diff --cached --quiet; then
        return 0  # Has changes
    fi

    # Check for new untracked files
    if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
        return 0  # Has new files
    fi

    return 1  # Clean
}

# -----------------------------------------------------------------------------
# check_all_complete() - Check if all tasks done, exit if so
# -----------------------------------------------------------------------------
# Deduplicates the completion-and-exit logic used in multiple verification paths.
# Parameters:
#   $1 = context string for logging (e.g., "CHECK 1 with tests")
check_all_complete() {
    local context="$1"
    REMAINING=$(count_remaining_tasks)
    if [[ "$REMAINING" -eq 0 ]]; then
        status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations! ($(elapsed_time) elapsed)"
        log_event "ALL_COMPLETE" "Verified all tasks complete ($context)" "{\"iterations\":$i}"

        SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
        if [[ "$SKIP_COUNT" -gt 0 ]]; then
            echo ""
            status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
            echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task): \(.reason)"'
        fi

        rm -f "$STATE_FILE"
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# cleanup() - Trap handler for clean exit on signals
# -----------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    echo ""
    status "$YELLOW" "EXIT" "Ralph stopped ($(elapsed_time) elapsed)"
    save_state
    log_event "EXIT" "Script exited" "{\"exit_code\":$exit_code,\"elapsed\":\"$(elapsed_time)\"}"
    exit $exit_code
}

trap cleanup INT TERM

# =============================================================================
# MAIN EXECUTION
# =============================================================================

echo ""
echo "==========================================="
if [[ "$MODE" == "review" ]]; then
    echo "  Ralph - Autonomous Agent (review mode)"
else
    echo "  Ralph - Autonomous Agent (dev mode)"
fi
echo "==========================================="
echo ""

check_dependencies

# Validate inputs
if [[ ! -f "$DOC_PATH" ]]; then
    status "$RED" "ERROR" "Document not found: $DOC_PATH"
    exit 1
fi

# Archive existing output files before starting fresh
version_file "$PROGRESS_FILE"
version_file "$LOG_FILE"
version_file "$TEST_OUTPUT_FILE"
version_file "$STATE_FILE"

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
echo "  Mode:               $MODE"
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
    echo "  Iteration $i of $ITERATIONS  ($(elapsed_time) elapsed)"
    echo "==========================================="

    TASK=$(get_current_task)

    if [[ -z "$TASK" ]]; then
        status "$GREEN" "COMPLETE" "All tasks finished! ($(elapsed_time) elapsed)"
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
1. Read the last 100 lines of progress.txt - see what went wrong before
2. Try a DIFFERENT approach than previous attempts
3. If the same approach keeps failing, the task may need to be broken down

Do NOT repeat the same fix that already failed."
    fi

    # -------------------------------------------------------------------------
    # BUILD THE PROMPT (mode-conditional)
    # -------------------------------------------------------------------------

    if [[ "$MODE" == "review" ]]; then
        # REVIEW MODE: concise output, condensed logging
        PROMPT="You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

**OUTPUT LIMIT: Keep your response under 500 words. Be concise. No exhaustive enumeration.**

## Steps

1. Read $DOC_PATH and find the first story that is NOT complete.
   - Look for story sections (### US-XXX) with unchecked items (\[ \])
   - Work on the FIRST incomplete story, not individual checkboxes
2. Read ONLY the last 100 lines of progress.txt (use offset/limit or tail). Do NOT read the entire file.
3. Implement that ONE story only - complete ALL its acceptance criteria.
4. Implement the changes, run builds/tests as needed, and report results accurately.
$FAILURE_CONTEXT
## Critical Rules

- Only mark [x] after ALL acceptance criteria for a story are met.
- Run builds and tests to verify changes compile and pass.
- Do not hardcode values or game test results.
- Do not delete or modify tests to make them pass.

### Failure Logging
If the task fails, append to progress.txt (MAX 4 lines):
\`\`\`
## Iteration $i - FAILED (Attempt $TASK_ATTEMPTS) | [story ID]
- Error: [one sentence]
- Next: [one sentence - different approach]
---
\`\`\`

### Success Logging
If the task succeeds, append to progress.txt (MAX 2 lines):
\`\`\`
## Iteration $i - OK | [story ID] | [PASS/FAIL/ACCEPTABLE] | [one-sentence finding]
---
\`\`\`

## End Condition

After completing work:
- If task succeeded AND all tasks in $DOC_PATH are now [x]: output exactly: <promise>COMPLETE</promise>
- If task failed OR tasks remain: just end your response"

    else
        # DEV MODE: full rules, verbose logging, smoke test template
        PROMPT="You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

## Steps

1. Read $DOC_PATH and find the first user story that is NOT complete.
   - Look for story sections (### US-XXX) with unchecked criteria (\[ \])
   - Work on the FIRST incomplete story, not individual checkboxes
2. Read ONLY the last 100 lines of progress.txt (use offset/limit or tail). Do NOT read the entire file.
   Check Learnings section for patterns from previous iterations.
3. Implement that ONE story only - complete ALL its acceptance criteria.
4. Run the project's test suite to verify your changes work.
5. Report results accurately.
$FAILURE_CONTEXT
## Critical Rules - READ CAREFULLY

### Rule 1: Honest Test Reporting
- Run actual tests (pytest, npm test, make test, etc.)
- Report the REAL result - do not claim tests pass if they fail
- If you're unsure whether tests passed, say so

### Rule 2: Only Mark Complete If Tests Actually Pass
- If tests PASS: Mark ALL criteria for the story as complete ([ ] -> [x]), then commit
- If tests FAIL: Do NOT mark complete, do NOT commit, just log what went wrong

### Rule 3: No Gaming
- Do not delete or modify tests to make them pass
- Do not hardcode values to satisfy specific test cases
- Do not mark tasks complete without running tests

### Rule 4: Learn From Failures
If tests fail, append to progress.txt:
\`\`\`
## Iteration $i - FAILED (Attempt $TASK_ATTEMPTS)
- Story attempted:
- What was tried:
- Why it failed:
- What to try differently next time:
---
\`\`\`

### Rule 5: Success Logging
If tests pass, append to progress.txt:
\`\`\`
## Iteration $i - SUCCESS
- Story completed:
- What was implemented:
- Files changed:
- Learnings:
---
\`\`\`

### Rule 6: Smoke Test Maintenance
When you CREATE a new Python module (new .py file with functions):
- Check if a corresponding test_*.py file exists
- If NO test file exists, create one with basic smoke tests

Smoke test template (adapt to actual module/function names):
\`\`\`python
\"\"\"
Smoke tests for [module_name].
Verifies code RUNS - hydrologist must verify calculations independently.
\"\"\"
import pytest

def test_module_imports():
    \"\"\"Verify module imports without syntax errors.\"\"\"
    import module_name

def test_main_function_exists():
    \"\"\"Verify expected function exists and is callable.\"\"\"
    from module_name import main_function
    assert callable(main_function)

def test_runs_without_error():
    \"\"\"Verify function executes with basic inputs.\"\"\"
    from module_name import main_function
    result = main_function(simple_input)
    assert result is not None
    assert isinstance(result, (int, float, list, dict))

def test_basic_sanity():
    \"\"\"Verify output is in reasonable range for known input.\"\"\"
    from module_name import main_function
    result = main_function(known_input)
    assert reasonable_lower < result < reasonable_upper, f\"Result {result} outside expected range\"
\`\`\`

Important: Smoke tests verify code RUNS, not that calculations are correct.
Only create tests for functions YOU created - don't test standard library.

## End Condition

After completing work:
- If task succeeded AND all tasks in $DOC_PATH are now [x]: output exactly: <promise>COMPLETE</promise>
- If task failed OR tasks remain: just end your response"
    fi

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

    # Decide whether to run tests based on mode and code changes
    # Dev mode: always verify tests
    # Review mode: only verify if code was actually changed
    should_run_tests() {
        if [[ "$MODE" == "dev" ]]; then
            return 0  # Always run in dev mode
        fi
        # Review mode: check for code changes
        has_code_changes
    }

    # CHECK 1: Did Claude claim everything is done?
    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
        status "$BLUE" "VERIFY" "Claude claims all tasks complete - verifying..."

        if should_run_tests; then
            if verify_tests_pass; then
                check_all_complete "COMPLETE claim with passing tests"
                status "$YELLOW" "MISMATCH" "Claude said complete but tasks remain unchecked"
                log_event "COMPLETION_MISMATCH" "Claude claimed complete but tasks remain" "{}"
            else
                status "$RED" "VERIFY_FAIL" "Claude claimed complete but tests fail!"
                log_event "FALSE_COMPLETION" "Claude claimed complete but tests fail" "{}"
                rollback_changes "$i"
            fi
        else
            # No code changes in review mode — skip tests, check checklist only
            status "$BLUE" "SKIP" "No code changes - skipping test verification"
            check_all_complete "COMPLETE claim (read-only review)"
            status "$YELLOW" "MISMATCH" "Claude said complete but tasks remain unchecked"
            log_event "COMPLETION_MISMATCH" "Claude claimed complete but tasks remain" "{}"
        fi
    fi

    # CHECK 2: Did Claude mark a task complete?
    NEW_TASK=$(get_current_task)
    if [[ "$NEW_TASK" != "$TASK" ]] && [[ -n "$TASK" ]]; then
        status "$BLUE" "VERIFY" "Task marked complete - checking..."

        if should_run_tests; then
            status "$BLUE" "VERIFY" "Running independent test verification..."
            if verify_tests_pass; then
                status "$GREEN" "VERIFIED" "Task completion verified: $TASK"
                log_event "TASK_COMPLETE" "Task verified complete" "{\"task\":\"$TASK\",\"attempts\":$TASK_ATTEMPTS}"

                TASK_ATTEMPTS=0
                CURRENT_TASK="$NEW_TASK"
                save_state
                check_all_complete "task verification with tests"
            else
                status "$RED" "REJECT" "Task marked complete but tests fail - rolling back"
                log_event "FALSE_COMPLETION" "Task marked complete but tests fail" "{\"task\":\"$TASK\"}"
                rollback_changes "$i"
                status "$YELLOW" "REVERTED" "All changes rolled back including checkbox marks - will retry"
            fi
        else
            # No code changes in review mode — skip tests
            status "$BLUE" "SKIP" "No code changes - skipping test verification"
            status "$GREEN" "VERIFIED" "Task completion verified (read-only): $TASK"
            log_event "TASK_COMPLETE" "Task verified complete (read-only)" "{\"task\":\"$TASK\",\"attempts\":$TASK_ATTEMPTS}"

            TASK_ATTEMPTS=0
            CURRENT_TASK="$NEW_TASK"
            save_state
            check_all_complete "task verification (read-only review)"
        fi
    fi

    # Show progress update
    REMAINING=$(count_remaining_tasks)
    COMPLETED=$(count_completed_tasks)
    status "$BLUE" "PROGRESS" "Tasks: $COMPLETED completed, $REMAINING remaining ($(elapsed_time) elapsed)"

    sleep "$SLEEP"
done

# =============================================================================
# MAX ITERATIONS REACHED
# =============================================================================

echo ""
echo "==========================================="
status "$YELLOW" "LIMIT" "Reached max iterations ($ITERATIONS) after $(elapsed_time)"
echo "==========================================="

REMAINING=$(count_remaining_tasks)
COMPLETED=$(count_completed_tasks)

echo ""
echo "Final Status:"
echo "  Completed: $COMPLETED"
echo "  Remaining: $REMAINING"
echo "  Elapsed:   $(elapsed_time)"

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
echo "  4. Run again with more iterations: ./ralph.sh --mode $MODE $((ITERATIONS + 10)) $SLEEP $DOC_PATH"

exit 1
