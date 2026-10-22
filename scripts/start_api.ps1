# start_api.ps1
# Starts the Tax Automation FastAPI server
param (
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")

$PYTHON_EXE = "python"
if (Test-Path ".venv/Scripts/python.exe") {
    $PYTHON_EXE = ".venv/Scripts/python.exe"
}

Write-Host "================================================================="
Write-Host " Tax Automation API Server"
Write-Host " Host: $Host  Port: $Port"
Write-Host " Swagger UI: http://localhost:$Port/docs"
Write-Host " ReDoc:      http://localhost:$Port/redoc"
Write-Host "================================================================="

if ($Reload) {
    & $PYTHON_EXE -m uvicorn tax_automation.api.main:app --host $Host --port $Port --reload
} else {
    & $PYTHON_EXE -m uvicorn tax_automation.api.main:app --host $Host --port $Port
}
