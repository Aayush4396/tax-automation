# run_and_verify.ps1
# Runs the narration automation engine for a given Financial Year (or ALL years)
# and prints a verification summary of the confidence scores and human match rates.

param (
    [string]$FY = "ALL"
)

# Force UTF-8 console output encoding to print Unicode characters (like ₹, →, ─, ≥) correctly
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Change to the script's directory so paths resolve correctly regardless of where it is invoked from
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir) {
    Set-Location $ScriptDir
}

# Detect python executable
$PYTHON_EXE = "python"
if (Test-Path "../.venv/Scripts/python.exe") {
    $PYTHON_EXE = "../.venv/Scripts/python.exe"
} elseif (Test-Path "../../.venv/Scripts/python.exe") {
    $PYTHON_EXE = "../../.venv/Scripts/python.exe"
} elseif (Test-Path ".venv/Scripts/python.exe") {
    $PYTHON_EXE = ".venv/Scripts/python.exe"
}

function Run-Year ($fy_val) {
    Write-Host "================================================================="
    Write-Host " Running Narration Engine for $fy_val..."
    Write-Host "================================================================="

    $base_in = "E:/Tax/Ajay/Data/$fy_val/Bank_Statements"
    if (-not (Test-Path $base_in)) {
        Write-Warning "Bank statements directory not found at $base_in. Skipping $fy_val."
        return
    }

    # Consolidate individual bank statements dynamically if they exist
    Write-Host "Consolidating individual statements..."
    & $PYTHON_EXE consolidate_statements.py --fy $fy_val

    # Run narration and capture output to a temp file
    $output_log = "temp_run_${fy_val}_output.tmp"
    & $PYTHON_EXE run_narration.py --fy $fy_val > $output_log 2>&1

    if (-not (Test-Path $output_log)) {
        Write-Error "Narration run failed to write output for $fy_val."
        return
    }

    # Print pipeline console output
    Get-Content $output_log -Encoding UTF8

    Write-Host ""
    Write-Host "================================================================="
    Write-Host " VERIFICATION SUMMARY FOR $fy_val"
    Write-Host "================================================================="

    # Extract overall summary statistics from output log
    Write-Host "--- Overall Classification Stats ---"
    $lines = Get-Content $output_log -Encoding UTF8
    $foundSummary = $false
    $summaryCount = 0
    foreach ($line in $lines) {
        if ($line -like "*OVERALL SUMMARY*") {
            $foundSummary = $true
        }
        if ($foundSummary) {
            Write-Host $line
            $summaryCount++
            if ($summaryCount -ge 6) {
                break
            }
        }
    }

    Write-Host ""
    Write-Host "--- Per-Bank Sheet Match Rates & Tiers ---"
    foreach ($line in $lines) {
        if ($line -like "*Sheet    :*" -or $line -like "*Total    :*" -or $line -like "*Confidence →*") {
            Write-Host "  $line"
        }
    }

    # Run deep verification script to check low confidence and human mismatches
    Write-Host ""
    Write-Host "--- Deep Verification (Mismatches & Low-Confidence Lists) ---"
    & $PYTHON_EXE check_narration_results.py --fy $fy_val

    # Clean up temp file
    Remove-Item $output_log -ErrorAction SilentlyContinue
    Write-Host "================================================================="
    Write-Host ""
}

$FY_UPPER = $FY.ToUpper()
if ($FY_UPPER -eq "ALL") {
    Write-Host "Running verification for all available years..."
    Run-Year "FY24"
    Run-Year "FY25"
} else {
    Run-Year $FY
}
