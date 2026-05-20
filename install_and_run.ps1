# SMP12C VibroDiag Analyzer - Installation and Launch Script
# Best practice: run via powershell.exe -ExecutionPolicy Bypass -File .\install_and_run.ps1

Write-Host "=== SMP12C VibroDiag Analyzer - Installation & Launch" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "1. Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "   Python: $pythonVersion" -ForegroundColor Green

# Create virtual environment
Write-Host ""
Write-Host "2. Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   Virtual environment already exists" -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "   Virtual environment created" -ForegroundColor Green
}

# Activate environment with execution policy handling
Write-Host ""
Write-Host "3. Activating environment..." -ForegroundColor Yellow
try {
    .\venv\Scripts\Activate.ps1 -ErrorAction Stop
    Write-Host "   Environment activated" -ForegroundColor Green
} catch [System.Management.Automation.PSSecurityException] {
    Write-Host "   PowerShell execution policy blocks activation. Using Bypass..." -ForegroundColor Yellow
    powershell.exe -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Error: Failed to activate environment. Run script via:" -ForegroundColor Red
        Write-Host "   powershell.exe -ExecutionPolicy Bypass -File .\install_and_run.ps1" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "   Environment activated (Bypass)" -ForegroundColor Green
} catch {
    Write-Host "   Activation error: $_" -ForegroundColor Red
    exit 1
}

# Update pip
Write-Host ""
Write-Host "4. Updating pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "   pip updated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "5. Installing dependencies..." -ForegroundColor Yellow
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
python -m pip install -r requirements.txt
Write-Host "   Dependencies installed" -ForegroundColor Green

# Launch application
Write-Host ""
Write-Host "6. Launching application..." -ForegroundColor Yellow
Write-Host ""
python -m smp12c_vibrodiag.main

