#!/bin/bash
# step3_run_modflow.sh - MODFLOW execution wrapper with verification
#
# Runs MODFLOW96 via Wine with enhanced logging and automatic verification.
# Preserves manual oversight - modeler watches convergence during run.
#
# Usage: ./step3_run_modflow.sh --year 2025

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Parse command-line arguments
YEAR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --year)
            YEAR="${2:-}"
            if [[ -z "$YEAR" ]]; then
                echo "ERROR: --year requires a value"
                echo "Usage: $0 --year YYYY"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --year YYYY"
            echo ""
            echo "Run MODFLOW96 with enhanced logging for specified year."
            echo ""
            echo "Options:"
            echo "  --year YYYY    Target year (e.g., 2025)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "What this script does:"
            echo "  1. Navigate to output/modflow/YYYY/"
            echo "  2. Run MODFLOW96 via Wine (30-45 minutes)"
            echo "  3. Log output to {YEAR}_modflow_run.log"
            echo "  4. Automatically run verify_modflow_run.py"
            echo "  5. Report runtime and verification status"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Usage: $0 --year YYYY"
            echo "Try '$0 --help' for more information."
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$YEAR" ]]; then
    echo "ERROR: --year is required"
    echo "Usage: $0 --year YYYY"
    echo "Try '$0 --help' for more information."
    exit 1
fi

# Validate year is a number
if ! [[ "$YEAR" =~ ^[0-9]+$ ]]; then
    echo "ERROR: --year must be a number, got: $YEAR"
    exit 1
fi

# Define paths
MODFLOW_DIR="output/modflow/$YEAR"
NAM_FILE="CY${YEAR}.nam"

# Check prerequisites
echo "=============================================================="
echo "MODFLOW96 Execution - Year $YEAR"
echo "Started: $(date)"
echo "=============================================================="
echo

# Check directory exists
if [[ ! -d "$MODFLOW_DIR" ]]; then
    echo "ERROR: Directory not found: $MODFLOW_DIR"
    echo ""
    echo "Hint: Run 'python3 step2_update_modflow.py --year $YEAR' first"
    exit 1
fi

# Check Wine installed
if ! command -v wine &> /dev/null; then
    echo "ERROR: Wine not installed"
    echo ""
    echo "Wine is required to run MODFLOW96 on Linux/WSL."
    echo "Install with: sudo apt-get install wine"
    exit 1
fi

# Change to MODFLOW directory
cd "$MODFLOW_DIR" || exit 1
echo "Working directory: $(pwd)"
echo

# Check NAM file exists
if [[ ! -f "$NAM_FILE" ]]; then
    echo "ERROR: NAM file not found: $NAM_FILE"
    echo ""
    echo "Expected location: $MODFLOW_DIR/$NAM_FILE"
    exit 1
fi

echo "NAM file: $NAM_FILE"
echo "Executable: modflow96.exe"
echo ""
echo "Running MODFLOW96 (this will take 30-45 minutes)..."
echo "You can watch convergence behavior in real-time."
echo "Press Ctrl+C to abort if you see problems."
echo ""
echo "--------------------------------------------------------------"

# Run MODFLOW with logging
START_TIME=$(date +%s)
echo "$NAM_FILE" | wine ./modflow96.exe 2>&1 | tee "${YEAR}_modflow_run.log"
EXIT_CODE=${PIPESTATUS[0]}
END_TIME=$(date +%s)
RUNTIME=$((END_TIME - START_TIME))

echo "--------------------------------------------------------------"
echo
echo "=============================================================="
echo "MODFLOW96 Execution Complete"
echo "Runtime: $((RUNTIME / 60)) minutes $((RUNTIME % 60)) seconds"
echo "Exit code: $EXIT_CODE"
echo "=============================================================="
echo

# Check for successful completion
if [[ $EXIT_CODE -ne 0 ]]; then
    echo "✗ MODFLOW96 failed with exit code $EXIT_CODE"
    echo ""
    echo "Review log file: $MODFLOW_DIR/${YEAR}_modflow_run.log"
    exit $EXIT_CODE
fi

echo "✓ MODFLOW96 completed successfully"
echo

# Run verification automatically
echo "Running post-execution verification..."
echo

if [[ ! -f "verify_modflow_run.py" ]]; then
    echo "⚠ Warning: verify_modflow_run.py not found"
    echo ""
    echo "Skipping verification, but MODFLOW run completed."
    exit 0
fi

python3 verify_modflow_run.py
VERIFY_CODE=$?

echo
echo "=============================================================="
echo "SUMMARY"
echo "=============================================================="
echo "MODFLOW runtime: $((RUNTIME / 60))m $((RUNTIME % 60))s"
echo "Log file: ${YEAR}_modflow_run.log"

if [[ $VERIFY_CODE -eq 0 ]]; then
    echo ""
    echo "✓ All checks passed!"
    echo ""
    echo "➡️  Next Step:"
    echo "  cd ../../.."
    echo "  python3 step4_generate_depletion_tables.py --year $YEAR"
    exit 0
else
    echo ""
    echo "⚠ Verification found issues"
    echo ""
    echo "Review verification report: ${YEAR}_verify_modflow.md"
    echo "Fix issues before proceeding to step 4."
    exit 1
fi
