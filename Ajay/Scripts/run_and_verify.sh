#!/usr/bin/env bash

# run_and_verify.sh
# Runs the narration automation engine for a given Financial Year (or ALL years)
# and prints a verification summary of the confidence scores and human match rates.

# Default FY is ALL
FY_INPUT="${1:-ALL}"

# Change to the script's directory so paths resolve correctly regardless of where it is invoked from
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Detect python executable (checking virtual environments first)
PYTHON_EXE="python"
if [ -f "../.venv/Scripts/python" ]; then
    PYTHON_EXE="../.venv/Scripts/python"
elif [ -f "../../.venv/Scripts/python" ]; then
    PYTHON_EXE="../../.venv/Scripts/python"
elif [ -f ".venv/Scripts/python" ]; then
    PYTHON_EXE=".venv/Scripts/python"
elif [ -f "../.venv/bin/python" ]; then
    PYTHON_EXE="../.venv/bin/python"
elif [ -f "../../.venv/bin/python" ]; then
    PYTHON_EXE="../../.venv/bin/python"
fi

run_year() {
    local fy="$1"
    echo "================================================================="
    echo " Running Narration Engine for $fy..."
    echo "================================================================="

    # Check if input file directory exists
    local base_in="E:/Tax/Ajay/Data/$fy/Bank_Statements"
    if [ ! -d "$base_in" ]; then
        echo "Warning: Bank statements directory not found at $base_in. Skipping $fy."
        return
    fi

    # Consolidate individual bank statements dynamically if they exist
    echo "Consolidating individual statements..."
    "$PYTHON_EXE" consolidate_statements.py --fy "$fy"

    # Run narration engine and capture output
    local output_log="temp_run_${fy}_output.tmp"
    "$PYTHON_EXE" run_narration.py --fy "$fy" 2>&1 | tee "$output_log"

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "Error: narration run failed for $fy!"
        rm -f "$output_log"
        return
    fi

    echo ""
    echo "================================================================="
    echo " VERIFICATION SUMMARY FOR $fy"
    echo "================================================================="

    # Extract overall summary statistics from output log
    echo "--- Overall Classification Stats ---"
    grep -A 5 "OVERALL SUMMARY" "$output_log" || echo "Overall summary not found in log."

    echo ""
    echo "--- Per-Bank Sheet Match Rates & Tiers ---"
    # Extract Sheet, Matched, and Confidence lines
    grep -E "Sheet\s*:|Total\s*:|Confidence\s*→" "$output_log" | while read -r line; do
        echo "  $line"
    done

    # Run deep verification script to check low confidence and human mismatches
    echo ""
    echo "--- Deep Verification (Mismatches & Low-Confidence Lists) ---"
    "$PYTHON_EXE" check_narration_results.py --fy "$fy"

    # Clean up temp file
    rm -f "$output_log"
    echo "================================================================="
    echo ""
}

# Normalize input to uppercase
FY_UPPER=$(echo "$FY_INPUT" | tr '[:lower:]' '[:upper:]')

if [ "$FY_UPPER" = "ALL" ]; then
    echo "Running verification for all available years..."
    run_year "FY24"
    run_year "FY25"
else
    run_year "$FY_INPUT"
fi
