#!/bin/bash
# =============================================================================
# RALPH ENHANCED - Autonomous Coding Agent Loop with Guardrails
# =============================================================================
#
# PLAIN ENGLISH: WHAT THIS SCRIPT DOES
# =====================================
# 
# Imagine you have a to-do list (PRD.md) with coding tasks marked like this:
#   - [ ] Create a function to calculate stream discharge
#   - [ ] Add error handling for missing data
#   - [x] Set up project folder (already done)
#
# This script runs Claude Code in a loop to work through that list:
#
#   1. READ THE LIST    → Find the first unchecked task (- [ ])
#   2. ASK CLAUDE       → "Hey Claude, please do this ONE task"
#   3. VERIFY IT WORKS  → Run tests to make sure Claude didn't break anything
#   4. CHECK THE BOX    → If tests pass, mark it done (- [x])
#   5. REPEAT           → Go back to step 1 until all tasks are done
#
# WHY "ENHANCED"? THE RALPH WIGGUM PROBLEM
# =========================================
#
# The original simple loop had a dangerous flaw: it trusted Claude completely.
# Claude might say "tests pass!" when they actually failed, or get stuck
# trying the same broken approach over and over (like Ralph Wiggum from
# The Simpsons cheerfully failing at something repeatedly).
#
# This enhanced version adds "guardrails" - safety checks that prevent:
#
#   PROBLEM                          GUARDRAIL
#   ─────────────────────────────    ─────────────────────────────────────
#   Claude lies about tests passing  We run tests ourselves to verify
#   Claude gets stuck on one task    After 3 failures, skip it and move on
#   Bad code accumulates             Undo (rollback) changes when tests fail
#   No memory of what failed         Log everything so Claude can learn
#   Loop runs forever                Maximum iteration limit
#
# HOW TEST VERIFICATION WORKS
# ===========================
#
# The script automatically detects what kind of project you have:
#
#   IF YOU HAVE...                   SCRIPT WILL USE...
#   ─────────────────────────────    ─────────────────────────────────────
#   test_*.py files                  pytest (BEST - catches runtime errors)
#   Only .py files, no tests         py_compile (OK - catches syntax errors)
#   package.json (JavaScript)        npm test
#   Makefile with test target        make test
#   Nothing recognized               Warning, no verification
#
# "SMOKE TESTS" EXPLAINED
# =======================
#
# When Claude creates a new Python file, it will also create a simple test
# file (like test_discharge.py) that checks:
#
#   ✓ Can Python even read the file? (no typos/syntax errors)
#   ✓ Does the function exist?
#   ✓ Does it run without crashing?
#   ✓ Does it return a reasonable-looking number?
#
# These are called "smoke tests" - like turning on a machine to see if
# smoke comes out. They DON'T verify your calculations are correct
# (you're the hydrologist, that's your job). They just catch obvious
# failures so the loop doesn't mark broken code as "done."
#
# FILES THIS SCRIPT CREATES
# =========================
#
#   progress.txt          Human-readable log of what happened each iteration
#   .ralph_state.json     Tracks current task and attempt count (machine use)
#   .ralph_log.jsonl      Detailed event log for debugging problems
#   .ralph_test_output.txt  Latest test output (overwritten each iteration)
#
# USAGE
# =====
#
#   ./ralph_enhanced.sh [ITERATIONS] [SLEEP] [DOC_PATH] [MAX_TASK_TRIES] [TEST_CMD]
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
#   # Use all defaults - good starting point
#   ./ralph_enhanced.sh
#
#   # More iterations, custom PRD file
#   ./ralph_enhanced.sh 20 2 MY_TASKS.md
#
#   # Specify exact test command
#   ./ralph_enhanced.sh 15 2 PRD.md 3 "pytest tests/ -v"
#
# REQUIREMENTS
# ============
#
#   - bash (comes with Mac/Linux)
#   - jq (JSON processor) - install with: sudo apt install jq (Linux) 
#                                      or: brew install jq (Mac)
#   - git (for rollback feature)
#   - claude CLI (Claude Code command line tool)
#
# =============================================================================

set -e  # Exit on error (we'll handle errors explicitly where needed)

# =============================================================================
# CONFIGURATION - These are the "settings" for the script
# =============================================================================
# 
# The ${1:-10} syntax means: "Use the first argument ($1), but if nothing
# was provided, use 10 as the default." This lets you run the script with
# or without specifying each option.

# ITERATIONS: Maximum times to run the loop before stopping
# - Too low: might not finish all tasks
# - Too high: wastes time if something is fundamentally broken
# - Default of 10 is good for small PRDs (5-8 tasks)
ITERATIONS=${1:-10}

# SLEEP: Seconds to pause between iterations
# - Gives you time to read output
# - Prevents hammering the API too fast
# - 2 seconds is a reasonable default
SLEEP=${2:-2}

# DOC_PATH: The file containing your task checklist
# - Must use markdown checkbox format: - [ ] task or - [x] done
# - Script reads this to find work, writes to it to mark progress
DOC_PATH=${3:-PRD.md}

# MAX_TASK_TRIES: How many times to attempt ONE task before giving up
# - Prevents infinite loops on impossible tasks
# - 3 is usually enough to catch real issues vs. bad luck
# - If a task fails 3 times, something is probably wrong with the task itself
MAX_TASK_TRIES=${4:-3}

# TEST_CMD: The command to verify code works
# - Leave empty to auto-detect (recommended for beginners)
# - Override if auto-detection picks wrong command
TEST_CMD=${5:-""}

# TERMINAL COLORS - Makes output easier to scan visually
# =============================================================================
# These are "escape codes" that tell the terminal to change text color.
# When you see status messages, colors help you quickly spot problems:
#   RED    = Something failed, needs attention
#   GREEN  = Success, good news
#   YELLOW = Warning, not critical but worth noting
#   BLUE   = Informational, just FYI
#   NC     = "No Color" - resets back to normal text
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# STATE TRACKING FILES - How the script remembers what's happening
# =============================================================================
# These files store information between iterations and runs:

# PROGRESS_FILE: Human-readable log you can review
# - Contains notes from each iteration (what worked, what failed)
# - Claude reads this to learn from past attempts
# - You can read this to understand what happened
PROGRESS_FILE="progress.txt"

# STATE_FILE: Machine-readable JSON tracking current state
# - Which task is being worked on
# - How many times we've tried it
# - Which tasks have been skipped
# - Survives if you stop and restart the script
STATE_FILE=".ralph_state.json"

# LOG_FILE: Detailed event log in JSONL format (one JSON object per line)
# - Every significant event is recorded with timestamp
# - Useful for debugging if something goes wrong
# - You probably won't read this directly, but it's there if needed
LOG_FILE=".ralph_log.jsonl"

# =============================================================================
# UTILITY FUNCTIONS - Reusable "helper" code blocks
# =============================================================================
# 
# In programming, we group repeated tasks into "functions" - named blocks
# of code we can call by name. Think of them like recipes: instead of 
# writing out all the steps every time, we just say "make_bread()" and
# the computer knows what to do.

# -----------------------------------------------------------------------------
# timestamp() - Get current time in a standard format
# -----------------------------------------------------------------------------
# Returns the current date/time in ISO 8601 format (international standard)
# Example output: "2025-01-29T15:30:45Z"
# The 'Z' means UTC (Universal Time), avoiding timezone confusion in logs
timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# -----------------------------------------------------------------------------
# log_event() - Record something that happened to the log file
# -----------------------------------------------------------------------------
# Creates a JSON entry (structured data) that's easy for programs to parse
# Parameters:
#   $1 = event_type: What kind of thing happened (e.g., "TASK_COMPLETE")
#   $2 = message: Human-readable description
#   $3 = details: Additional data in JSON format (optional)
#
# Example call: log_event "TESTS_PASSED" "All tests green" "{\"count\":5}"
# Example output in file: {"timestamp":"2025-01-29T15:30:45Z","event":"TESTS_PASSED",...}
log_event() {
    local event_type="$1"
    local message="$2"
    local details="${3:-{}}"  # Default to empty JSON object if not provided
    
    # The '>>' means "append to file" (don't overwrite previous entries)
    echo "{\"timestamp\":\"$(timestamp)\",\"event\":\"$event_type\",\"message\":\"$message\",\"details\":$details}" >> "$LOG_FILE"
}

# -----------------------------------------------------------------------------
# status() - Print a colored status message to the terminal
# -----------------------------------------------------------------------------
# Makes output visually scannable with color-coded prefixes
# Parameters:
#   $1 = color: Which color to use (use the variables defined above)
#   $2 = prefix: Short label like "OK", "FAIL", "WARN"
#   $3 = message: The actual message to display
#
# Example call: status "$GREEN" "OK" "Tests passed!"
# Example output: [OK] Tests passed!  (in green)
status() {
    local color="$1"
    local prefix="$2"
    local message="$3"
    # -e flag tells echo to interpret escape codes (for colors)
    echo -e "${color}[${prefix}]${NC} $message"
}

# -----------------------------------------------------------------------------
# detect_test_command() - Figure out what command to use for testing
# -----------------------------------------------------------------------------
# Looks at your project files to guess the right test command.
# This is "auto-detection" - the script figures it out so you don't have to.
#
# Priority order (first match wins):
#   1. pytest - If you have test_*.py files (best protection)
#   2. npm test - If you have package.json (JavaScript projects)
#   3. make test - If you have a Makefile with a test target
#   4. py_compile - If you have .py files but no tests (syntax check only)
#   5. nothing - No tests possible, will warn you

# Auto-detect test command based on project files
# Priority: pytest (if tests exist) > py_compile (syntax check fallback)
detect_test_command() {
    # Start by assuming no test files exist
    local has_test_files=false
    
    # Look for pytest-style test files in current directory
    # The pattern test_*.py matches files like: test_discharge.py, test_utils.py
    # The pattern *_test.py matches files like: discharge_test.py, utils_test.py
    # The "2>&1" redirects error messages to nowhere (keeps output clean)
    if ls test_*.py 1> /dev/null 2>&1 || ls *_test.py 1> /dev/null 2>&1; then
        has_test_files=true
    fi
    
    # Also check inside a "tests/" folder if one exists
    # Many projects organize tests in a dedicated directory
    if [[ -d "tests" ]]; then
        if ls tests/test_*.py 1> /dev/null 2>&1 || ls tests/*_test.py 1> /dev/null 2>&1; then
            has_test_files=true
        fi
    fi
    
    # BEST CASE: Test files exist, use pytest
    # pytest is the standard Python testing tool - it finds and runs your tests
    if [[ "$has_test_files" == true ]]; then
        echo "pytest"
        return 0  # "return 0" means success, we're done
    fi
    
    # JavaScript/Node projects use npm for package management
    # If package.json exists, "npm test" is the standard way to run tests
    if [[ -f "package.json" ]]; then
        echo "npm test"
        return 0
    fi
    
    # Makefiles are build automation files common in C/C++ and some Python projects
    # If there's a Makefile with a "test:" target, use that
    if [[ -f "Makefile" ]] && grep -q "^test:" Makefile; then
        echo "make test"
        return 0
    fi
    
    # FALLBACK: No tests exist, but there are Python files
    # py_compile just checks if Python can parse the files (no syntax errors)
    # This is minimal protection - catches typos but not logic errors
    # Better than nothing while you're learning to write tests
    if ls *.py 1> /dev/null 2>&1; then
        echo "python3 -m py_compile *.py"
        return 0
    fi
    
    # WORST CASE: Can't figure out how to verify anything
    # Return empty string, caller will show a warning
    echo ""
}

# -----------------------------------------------------------------------------
# get_current_task() - Find the first uncompleted user story in the PRD
# -----------------------------------------------------------------------------
# Looks for user story headers (### US-XXX:) that DON'T have all their
# acceptance criteria checked off. This is more robust than finding bare
# checkboxes, which would match individual criteria instead of stories.
#
# IMPORTANT: This function provides a HINT for tracking/display purposes.
# Claude actually interprets the document structure to find work - this
# just helps us track progress and detect stuck conditions.
#
# Returns: The user story title, or empty string if all complete
get_current_task() {
    # Strategy: Find the first "### US-" line that is followed by an unchecked "- [ ]"
    # before the next "### US-" line. This correctly identifies incomplete stories.
    #
    # However, this is complex in pure bash. Simpler approach: 
    # Find any unchecked item, then let Claude interpret context.
    # We use this for stuck detection, not for telling Claude what to do.
    
    # Look for the first unchecked checkbox - used for progress tracking
    # Claude reads the actual document and understands story structure
    local first_unchecked=$(grep -m1 '\- \[ \]' "$DOC_PATH" 2>/dev/null || echo "")
    
    if [[ -z "$first_unchecked" ]]; then
        echo ""  # All done
    else
        # Return a normalized version for tracking purposes
        # Strip the checkbox prefix if present
        echo "$first_unchecked" | sed 's/^- \[ \] //'
    fi
}

# -----------------------------------------------------------------------------
# count_remaining_tasks() - How many tasks are still unchecked?
# -----------------------------------------------------------------------------
# Counts lines containing "- [ ]" (unchecked boxes)
# Used for progress display: "3 tasks remaining"
count_remaining_tasks() {
    # grep -c = count matching lines instead of showing them
    grep -c '\- \[ \]' "$DOC_PATH" 2>/dev/null || echo "0"
}

# -----------------------------------------------------------------------------
# count_completed_tasks() - How many tasks are already done?
# -----------------------------------------------------------------------------
# Counts lines containing "- [x]" (checked boxes)
# Used for progress display: "5 tasks completed"
count_completed_tasks() {
    grep -c '\- \[x\]' "$DOC_PATH" 2>/dev/null || echo "0"
}

# -----------------------------------------------------------------------------
# init_state() - Load saved state or create fresh state
# -----------------------------------------------------------------------------
# This function handles "persistence" - remembering state between runs.
# If you stop the script and restart, it picks up where it left off.
#
# State includes:
#   - CURRENT_TASK: Which task we're working on
#   - TASK_ATTEMPTS: How many times we've tried this task
#   - SKIPPED_TASKS: List of tasks we gave up on

# Initialize or load state
init_state() {
    # Check if we have a saved state file from a previous run
    if [[ -f "$STATE_FILE" ]]; then
        # Load existing state using 'jq' (a tool for reading JSON files)
        # The '-r' flag means "raw" - don't add quotes around the output
        # The '// ""' is a default value if the field doesn't exist
        CURRENT_TASK=$(jq -r '.current_task // ""' "$STATE_FILE")
        TASK_ATTEMPTS=$(jq -r '.task_attempts // 0' "$STATE_FILE")
        SKIPPED_TASKS=$(jq -r '.skipped_tasks // []' "$STATE_FILE")
    else
        # No saved state - start fresh
        CURRENT_TASK=""
        TASK_ATTEMPTS=0
        SKIPPED_TASKS="[]"  # Empty JSON array
        save_state  # Create the state file
    fi
}

# -----------------------------------------------------------------------------
# save_state() - Write current state to file
# -----------------------------------------------------------------------------
# Saves our tracking variables to a JSON file so we don't lose progress
# if the script stops unexpectedly (Ctrl+C, power outage, etc.)
#
# The "cat > file << EOF" syntax is called a "here document" - it lets us
# write multiple lines to a file easily.
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

# -----------------------------------------------------------------------------
# skip_task() - Mark a task as skipped (gave up after too many failures)
# -----------------------------------------------------------------------------
# When a task fails MAX_TASK_TRIES times, we skip it and move on.
# This prevents one broken task from blocking all progress.
#
# Parameters:
#   $1 = task: The task description that failed
#   $2 = reason: Why we're skipping it (e.g., "Exceeded max attempts")
skip_task() {
    local task="$1"
    local reason="$2"
    
    # Escape quote characters in task name so they don't break JSON
    # sed replaces " with \" (escaped quote)
    local escaped_task=$(echo "$task" | sed 's/"/\\"/g')
    
    # Add this task to our list of skipped tasks
    # jq is used to append to the JSON array properly
    SKIPPED_TASKS=$(echo "$SKIPPED_TASKS" | jq --arg t "$escaped_task" --arg r "$reason" '. + [{"task": $t, "reason": $r}]')
    
    # Record this event in the log
    log_event "TASK_SKIPPED" "$task" "{\"reason\":\"$reason\",\"attempts\":$TASK_ATTEMPTS}"
    
    # Reset counters for the next task
    TASK_ATTEMPTS=0
    CURRENT_TASK=""
    save_state
}

# -----------------------------------------------------------------------------
# verify_tests_pass() - Run tests and check if they actually pass
# -----------------------------------------------------------------------------
# THIS IS THE KEY ANTI-RALPH-WIGGUM FUNCTION
#
# Instead of trusting Claude when it says "tests pass", we run the tests
# ourselves and check the exit code. In Unix/Linux:
#   - Exit code 0 = success (tests passed)
#   - Any other code = failure (something went wrong)
#
# Returns: 0 if tests pass, 1 if tests fail

# Run tests independently (not trusting Claude's word)
verify_tests_pass() {
    # If no test command is configured, we can't verify anything
    # This is the "flying without a net" scenario - warn but continue
    if [[ -z "$TEST_CMD" ]]; then
        status "$YELLOW" "WARN" "No test command configured - skipping independent verification"
        return 0  # Assume OK since we can't check (but we logged a warning)
    fi
    
    status "$BLUE" "TEST" "Running: $TEST_CMD"
    
    # Run the test command and capture the output
    # The 'set +e' temporarily allows errors without killing the script
    # (normally 'set -e' at the top makes any error stop everything)
    set +e
    
    # 'eval' runs the command stored in our variable
    # '> file 2>&1' redirects both normal output and errors to the file
    eval "$TEST_CMD" > .ralph_test_output.txt 2>&1
    local exit_code=$?  # Capture the exit code (0 = success, other = failure)
    
    set -e  # Re-enable "exit on error" mode
    
    # Check the exit code and report results
    if [[ $exit_code -eq 0 ]]; then
        # EXIT CODE 0 = Tests passed!
        status "$GREEN" "PASS" "Tests passed independently"
        log_event "TESTS_PASSED" "Independent verification successful" "{\"command\":\"$TEST_CMD\"}"
        return 0  # Signal success to caller
    else
        # NON-ZERO EXIT CODE = Something failed
        status "$RED" "FAIL" "Tests failed independently (exit code: $exit_code)"
        log_event "TESTS_FAILED" "Independent verification failed" "{\"command\":\"$TEST_CMD\",\"exit_code\":$exit_code}"
        
        # Show the last 20 lines of test output so you can see what went wrong
        # This helps debugging without overwhelming you with output
        echo "--- Test Output (last 20 lines) ---"
        tail -20 .ralph_test_output.txt
        echo "-----------------------------------"
        
        return 1  # Signal failure to caller
    fi
}

# -----------------------------------------------------------------------------
# rollback_changes() - Undo uncommitted changes when something goes wrong
# -----------------------------------------------------------------------------
# Uses git's "stash" feature to save broken changes somewhere safe.
# Think of it like: "these changes didn't work, put them aside"
#
# The stashed changes aren't deleted - you can recover them later with
# 'git stash list' (see what's stashed) and 'git stash pop' (restore)
#
# Parameter:
#   $1 = iteration number (for labeling the stash)

# Rollback uncommitted changes on failure
rollback_changes() {
    status "$YELLOW" "ROLLBACK" "Stashing uncommitted changes due to failure"
    
    # Check if there are actually any changes to stash
    # 'git diff --quiet' returns exit code 0 if there are NO changes
    # We check both unstaged changes (diff) and staged changes (diff --cached)
    if git diff --quiet && git diff --cached --quiet; then
        status "$BLUE" "INFO" "No uncommitted changes to rollback"
        return 0
    fi
    
    # Create a descriptive name for the stash so we can find it later
    # Example: "ralph-rollback-iteration-5-2025-01-29T15:30:45Z"
    local stash_msg="ralph-rollback-iteration-$1-$(timestamp)"
    
    # 'git stash push' saves changes and reverts files to last commit
    # '-m' adds our descriptive message
    # '--include-untracked' also saves new files that haven't been committed yet
    git stash push -m "$stash_msg" --include-untracked
    
    log_event "ROLLBACK" "Changes stashed" "{\"stash_message\":\"$stash_msg\"}"
    status "$GREEN" "OK" "Changes stashed as: $stash_msg"
}

# =============================================================================
# MAIN EXECUTION - This is where the actual work happens
# =============================================================================
# Everything above was setup (configuration, helper functions).
# Now we actually run the loop.

# Print a nice header so you know what's starting
echo ""
echo "==========================================="
echo "  Ralph Enhanced - Autonomous Coding Agent"
echo "==========================================="
echo ""

# -----------------------------------------------------------------------------
# STEP 1: Validate inputs before doing anything
# -----------------------------------------------------------------------------

# Make sure the PRD file actually exists
# [[ -f "$DOC_PATH" ]] tests if a file exists at that path
if [[ ! -f "$DOC_PATH" ]]; then
    status "$RED" "ERROR" "Document not found: $DOC_PATH"
    exit 1  # Exit with error code 1 (failure)
fi

# -----------------------------------------------------------------------------
# STEP 2: Auto-detect or validate test command
# -----------------------------------------------------------------------------

# Auto-detect test command if not provided by user
if [[ -z "$TEST_CMD" ]]; then
    # Call our detection function to figure out what to use
    TEST_CMD=$(detect_test_command)
    
    if [[ -n "$TEST_CMD" ]]; then
        # We found something! Tell the user what we'll use
        status "$GREEN" "DETECT" "Auto-detected test command: $TEST_CMD"
        
        # Explain the protection level so the user knows what's being verified
        # This is important because different commands catch different problems
        if [[ "$TEST_CMD" == "pytest" ]]; then
            # BEST CASE: Real tests exist
            status "$BLUE" "INFO" "Protection level: SMOKE TESTS (catches runtime failures + basic sanity)"
        elif [[ "$TEST_CMD" == *"py_compile"* ]]; then
            # OK CASE: No tests, but we can at least check syntax
            status "$YELLOW" "INFO" "Protection level: SYNTAX ONLY (catches broken code, not logic errors)"
            echo ""
            echo "  Tip: Add test_*.py files to enable smoke tests for better protection."
            echo "       Ralph will auto-detect and switch to pytest when tests exist."
            echo ""
        else
            # Other commands (npm test, make test, etc.)
            status "$BLUE" "INFO" "Protection level: PROJECT DEFAULT ($TEST_CMD)"
        fi
    else
        # WORST CASE: Couldn't figure out how to run tests
        status "$YELLOW" "WARN" "No test command detected - independent verification disabled"
        status "$YELLOW" "WARN" "Flying without a net! Consider adding test_*.py files."
    fi
fi

# -----------------------------------------------------------------------------
# STEP 3: Show configuration summary
# -----------------------------------------------------------------------------
# Let the user see all settings before we start the loop

# Show configuration
echo "Configuration:"
echo "  Max iterations:     $ITERATIONS"
echo "  Sleep between:      ${SLEEP}s"
echo "  Document:           $DOC_PATH"
echo "  Max tries per task: $MAX_TASK_TRIES"
echo "  Test command:       ${TEST_CMD:-'(none)'}"
echo ""

# -----------------------------------------------------------------------------
# STEP 4: Initialize state tracking
# -----------------------------------------------------------------------------
# Load any saved state from previous runs (or create fresh state)
init_state

# Show where we're starting from
REMAINING=$(count_remaining_tasks)
COMPLETED=$(count_completed_tasks)
status "$BLUE" "START" "Tasks: $COMPLETED completed, $REMAINING remaining"
echo ""

# =============================================================================
# MAIN LOOP - The heart of the script
# =============================================================================
# This loop runs up to ITERATIONS times, each time:
#   1. Find the next uncompleted task
#   2. Ask Claude to do it
#   3. Verify the work
#   4. Mark complete or handle failure

# for ((i=1; i<=ITERATIONS; i++)) is a counting loop
# It sets i=1, then repeats as long as i <= ITERATIONS, incrementing i each time
for ((i=1; i<=ITERATIONS; i++)); do
    # Visual separator for each iteration (makes output easier to read)
    echo "==========================================="
    echo "  Iteration $i of $ITERATIONS"
    echo "==========================================="
    
    # -------------------------------------------------------------------------
    # LOOP STEP 1: Check document for remaining work
    # -------------------------------------------------------------------------
    # NOTE: This is for TRACKING purposes (stuck detection, progress display).
    # Claude actually reads the document and interprets its structure to find
    # the correct user story to work on. We just need to know if there's still
    # unchecked work remaining.
    TASK=$(get_current_task)
    
    # -------------------------------------------------------------------------
    # LOOP STEP 2: Check if we're done (no more tasks)
    # -------------------------------------------------------------------------
    # If TASK is empty, all checkboxes are checked - we're finished!
    if [[ -z "$TASK" ]]; then
        status "$GREEN" "COMPLETE" "All tasks finished!"
        log_event "ALL_COMPLETE" "All tasks marked complete" "{\"iterations\":$i}"
        
        # Before celebrating, report any tasks we had to skip
        SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
        if [[ "$SKIP_COUNT" -gt 0 ]]; then
            status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped due to repeated failures:"
            # jq formats the skipped tasks nicely for display
            echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task): \(.reason)"'
        fi
        
        exit 0  # Success! Exit with code 0
    fi
    
    # -------------------------------------------------------------------------
    # LOOP STEP 3: Track progress for stuck detection
    # -------------------------------------------------------------------------
    # We track what unchecked item we see to detect if we're stuck on the
    # same work across multiple iterations. This enables the MAX_TASK_TRIES
    # guardrail. Note: Claude finds the actual story to work on by reading
    # the document structure.
    if [[ "$TASK" != "$CURRENT_TASK" ]]; then
        CURRENT_TASK="$TASK"
        TASK_ATTEMPTS=0
        status "$BLUE" "NEW" "New work detected - resetting attempt counter"
    fi
    
    # Increment the attempt counter for this task
    ((TASK_ATTEMPTS++))
    
    # -------------------------------------------------------------------------
    # LOOP STEP 4: Check if we've tried too many times (stuck detection)
    # -------------------------------------------------------------------------
    # This is the key anti-Ralph-Wiggum check!
    # If we've failed MAX_TASK_TRIES times, give up on this task and move on
    if [[ $TASK_ATTEMPTS -gt $MAX_TASK_TRIES ]]; then
        status "$RED" "STUCK" "Task failed $MAX_TASK_TRIES times - skipping: $TASK"
        skip_task "$TASK" "Exceeded max attempts ($MAX_TASK_TRIES)"
        
        # Undo any broken work from the failed attempts
        rollback_changes "$i"
        
        # Wait a moment, then continue to the next iteration
        # (which will pick up the NEXT task in the list)
        sleep "$SLEEP"
        continue  # Skip the rest of this iteration, go to next
    fi
    
    status "$BLUE" "ATTEMPT" "Attempt $TASK_ATTEMPTS of $MAX_TASK_TRIES for: $TASK"
    save_state  # Save our progress in case script is interrupted
    
    log_event "ITERATION_START" "Beginning iteration" "{\"iteration\":$i,\"task\":\"$TASK\",\"attempt\":$TASK_ATTEMPTS}"
    
    # -------------------------------------------------------------------------
    # LOOP STEP 5: Build context for Claude
    # -------------------------------------------------------------------------
    # If this isn't the first attempt at a task, tell Claude what's happening
    # This helps Claude try a DIFFERENT approach instead of repeating failures
    FAILURE_CONTEXT=""
    if [[ $TASK_ATTEMPTS -gt 1 ]]; then
        FAILURE_CONTEXT="

## IMPORTANT: This is attempt $TASK_ATTEMPTS of $MAX_TASK_TRIES for this task!

Previous attempts failed. Before making changes:
1. Read progress.txt carefully - see what went wrong before
2. Try a DIFFERENT approach than previous attempts
3. If the same approach keeps failing, the task may need to be broken down

Do NOT repeat the same fix that already failed."
    fi
    
    # -------------------------------------------------------------------------
    # LOOP STEP 6: Build the prompt for Claude
    # -------------------------------------------------------------------------
    # This is a multi-line string containing detailed instructions for Claude
    # We embed the current task, rules, and context directly in the prompt
    
    # The enhanced prompt with guardrails built into instructions
    # NOTE: Claude finds the actual task by reading the document structure.
    # The bash-level tracking is just for stuck detection and progress display.
    PROMPT="You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

## Steps

1. Read $DOC_PATH and find the first user story that is NOT complete.
   - Look for story sections (### US-XXX) with unchecked criteria (- [ ])
   - Work on the FIRST incomplete story, not individual checkboxes
2. Read progress.txt FIRST - check Learnings section for patterns from previous iterations.
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
- If tests PASS: Mark ALL criteria for the story as complete ([ ] → [x]), then commit
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
    import module_name  # Replace with actual module name

def test_main_function_exists():
    \"\"\"Verify expected function exists and is callable.\"\"\"
    from module_name import main_function  # Replace with actual names
    assert callable(main_function)

def test_runs_without_error():
    \"\"\"Verify function executes with basic inputs.\"\"\"
    from module_name import main_function
    result = main_function(simple_input)  # Replace with realistic simple input
    assert result is not None
    assert isinstance(result, (int, float, list, dict))  # Expected return type

def test_basic_sanity():
    \"\"\"Verify output is in reasonable range for known input.\"\"\"
    from module_name import main_function
    result = main_function(known_input)  # Use input where you know approximate output
    # Adjust range based on expected output magnitude
    assert reasonable_lower < result < reasonable_upper, f\"Result {result} outside expected range\"
\`\`\`

Important: Smoke tests verify code RUNS, not that calculations are correct.
Only create tests for functions YOU created - don't test standard library.

## End Condition

After completing work:
- If task succeeded AND all tasks in $DOC_PATH are now [x]: output exactly: <promise>COMPLETE</promise>
- If task failed OR tasks remain: just end your response"

    # -------------------------------------------------------------------------
    # LOOP STEP 7: Execute Claude
    # -------------------------------------------------------------------------
    # Now we actually call Claude with our prompt
    #
    # Breaking down this command:
    #   claude                         = The Claude Code CLI tool
    #   --dangerously-skip-permissions = Skip confirmation prompts (needed for automation)
    #   -p "$PROMPT"                   = Pass our prompt as input
    #   2>&1                           = Combine error output with normal output  
    #   | tee /dev/tty                 = Show output on screen AND capture it in variable
    #
    # The result variable will contain everything Claude outputs
    
    set +e  # Temporarily allow errors (Claude might fail, that's OK)
    result=$(claude --dangerously-skip-permissions -p "$PROMPT" 2>&1 | tee /dev/tty)
    claude_exit_code=$?  # Capture exit code in case we need it
    set -e  # Re-enable error checking
    
    echo ""  # Blank line for readability
    
    # -------------------------------------------------------------------------
    # LOOP STEP 8: Verify Claude's claims (anti-Ralph-Wiggum checks)
    # -------------------------------------------------------------------------
    # This is where we don't just trust Claude - we verify independently!
    
    # -------------------------------------------------------------------------
    # POST-EXECUTION VERIFICATION
    # -------------------------------------------------------------------------
    # This is where we check Claude's work. Trust but verify!
    
    # CHECK 1: Did Claude claim everything is done?
    # We look for the special marker "<promise>COMPLETE</promise>" in the output
    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
        status "$BLUE" "VERIFY" "Claude claims all tasks complete - verifying..."
        
        # Don't just trust Claude - run tests ourselves
        if verify_tests_pass; then
            # Tests passed! Now double-check the PRD file
            REMAINING=$(count_remaining_tasks)
            if [[ "$REMAINING" -eq 0 ]]; then
                # Everything checks out - we're really done!
                status "$GREEN" "COMPLETE" "All tasks verified complete after $i iterations!"
                log_event "ALL_COMPLETE" "Verified all tasks complete" "{\"iterations\":$i}"
                
                # Report any tasks that were skipped along the way
                SKIP_COUNT=$(echo "$SKIPPED_TASKS" | jq 'length')
                if [[ "$SKIP_COUNT" -gt 0 ]]; then
                    echo ""
                    status "$YELLOW" "WARN" "$SKIP_COUNT task(s) were skipped:"
                    echo "$SKIPPED_TASKS" | jq -r '.[] | "  - \(.task)"'
                fi
                
                # Clean up our state file since we're done
                rm -f "$STATE_FILE"
                
                exit 0  # Success!
            else
                # Claude said "complete" but unchecked boxes remain
                # This is a lie or mistake - Claude jumped the gun
                status "$YELLOW" "MISMATCH" "Claude said complete but $REMAINING tasks remain unchecked"
                log_event "COMPLETION_MISMATCH" "Claude claimed complete but tasks remain" "{\"remaining\":$REMAINING}"
            fi
        else
            # Claude said "complete" but tests actually fail
            # This is a Ralph Wiggum moment - cheerfully wrong
            status "$RED" "VERIFY_FAIL" "Claude claimed complete but tests fail!"
            log_event "FALSE_COMPLETION" "Claude claimed complete but tests fail" "{}"
            
            # Undo the broken changes
            rollback_changes "$i"
        fi
    fi
    
    # CHECK 2: Did Claude mark a task complete?
    # Compare current task to what it was before - if different, task was checked off
    NEW_TASK=$(get_current_task)
    if [[ "$NEW_TASK" != "$TASK" ]] && [[ -n "$TASK" ]]; then
        # The task changed - Claude marked something complete
        status "$BLUE" "VERIFY" "Task marked complete - running independent test verification..."
        
        if verify_tests_pass; then
            # Tests pass - the completion is legitimate
            status "$GREEN" "VERIFIED" "Task completion verified: $TASK"
            log_event "TASK_COMPLETE" "Task verified complete" "{\"task\":\"$TASK\",\"attempts\":$TASK_ATTEMPTS}"
            
            # Reset counters for the next task
            TASK_ATTEMPTS=0
            CURRENT_TASK="$NEW_TASK"
            save_state
        else
            # Tests fail - Claude marked it complete but the code is broken
            # This is another Ralph Wiggum moment
            status "$RED" "REJECT" "Task marked complete but tests fail - rolling back"
            log_event "FALSE_COMPLETION" "Task marked complete but tests fail" "{\"task\":\"$TASK\"}"
            
            # Undo ALL changes including the checkbox marks
            # git stash will revert the PRD file along with code changes
            rollback_changes "$i"
            
            status "$YELLOW" "REVERTED" "All changes rolled back including checkbox marks - will retry"
        fi
    fi
    
    # Show progress update
    REMAINING=$(count_remaining_tasks)
    COMPLETED=$(count_completed_tasks)
    status "$BLUE" "PROGRESS" "Tasks: $COMPLETED completed, $REMAINING remaining"
    
    # Pause before next iteration
    sleep "$SLEEP"
done

# =============================================================================
# MAX ITERATIONS REACHED - We ran out of attempts
# =============================================================================
# If we get here, the loop finished without completing all tasks.
# This isn't necessarily a failure - maybe there's just a lot of work,
# or some tasks need human intervention.

echo ""
echo "==========================================="
status "$YELLOW" "LIMIT" "Reached max iterations ($ITERATIONS)"
echo "==========================================="

# Gather final statistics
REMAINING=$(count_remaining_tasks)
COMPLETED=$(count_completed_tasks)

echo ""
echo "Final Status:"
echo "  Completed: $COMPLETED"
echo "  Remaining: $REMAINING"

# Report skipped tasks (ones that failed too many times)
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
echo "  4. Run again with more iterations: ./ralph_enhanced.sh $((ITERATIONS + 10))"

exit 1  # Exit with code 1 to indicate incomplete
