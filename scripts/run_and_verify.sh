#!/usr/bin/env bash
# run_and_verify.sh
# Runs the tax_automation narration engine for a specified Entity and Financial Year

ENTITY="${1:-aayush}"
FY="${2:-FY26}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON_EXE="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_EXE=".venv/bin/python"
fi

echo "================================================================="
echo " Running tax_automation pipeline for $ENTITY ($FY)..."
echo "================================================================="

$PYTHON_EXE -m tax_automation process --entity "$ENTITY" --fy "$FY"
$PYTHON_EXE -m tax_automation.tools.check_contras --entity "$ENTITY" --fy "$FY"
