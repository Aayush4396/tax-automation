# run_and_verify.ps1
# Runs the tax_automation narration engine for a specified Entity and Financial Year
param (
    [string]$Entity = "aayush",
    [string]$FY = "FY26"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")

$PYTHON_EXE = "python"
if (Test-Path ".venv/Scripts/python.exe") {
    $PYTHON_EXE = ".venv/Scripts/python.exe"
}

Write-Host "================================================================="
Write-Host " Running tax_automation pipeline for $Entity ($FY)..."
Write-Host "================================================================="

& $PYTHON_EXE -m tax_automation process --entity $Entity --fy $FY
& $PYTHON_EXE -m tax_automation.tools.check_contras --entity $Entity --fy $FY
