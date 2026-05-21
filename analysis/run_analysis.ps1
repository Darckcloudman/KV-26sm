# Vibration Diagnostics Analysis Runner
# Usage: .\run_analysis.ps1

$pythonPath = "python"
$scriptPath = Join-Path $PSScriptRoot "rd2_parser.py"
$testDataPath = Join-Path $PSScriptRoot "test_data\W1436 WTG37 SMP_20250901_38408_SENSOR_01_LOW_W.rd2"

Write-Host "Analyzing file: $testDataPath" -ForegroundColor Cyan
Write-Host "Script: $scriptPath" -ForegroundColor Cyan
Write-Host ""

& $pythonPath $scriptPath $testDataPath
