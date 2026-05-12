# Запуск анализа вибродиагностики
# Используйте: .\run_analysis.ps1

$pythonPath = "python"
$scriptPath = Join-Path $PSScriptRoot "rd2_parser.py"
$testDataPath = Join-Path $PSScriptRoot "test_data\W1436 WTG37 SMP_20250901_38408_SENSOR_01_LOW_W.rd2"

Write-Host "Запуск анализа файла: $testDataPath" -ForegroundColor Cyan
Write-Host "Скрипт: $scriptPath" -ForegroundColor Cyan
Write-Host ""

& $pythonPath $scriptPath $testDataPath
