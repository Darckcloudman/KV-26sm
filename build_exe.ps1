# KWF Prometheus - EXE Build Script
# Best practice: run via powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1

Write-Host "=== KWF Prometheus - Building EXE" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run first: .\install_and_run.ps1" -ForegroundColor Yellow
    exit 1
}

# Activate environment with execution policy handling
Write-Host "Activating environment..." -ForegroundColor Yellow
try {
    .\venv\Scripts\Activate.ps1 -ErrorAction Stop
    Write-Host "   Environment activated" -ForegroundColor Green
} catch [System.Management.Automation.PSSecurityException] {
    Write-Host "   PowerShell execution policy blocks activation. Using Bypass..." -ForegroundColor Yellow
    powershell.exe -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Error: Failed to activate environment. Run script via:" -ForegroundColor Red
        Write-Host "   powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "   Environment activated (Bypass)" -ForegroundColor Green
} catch {
    Write-Host "   Activation error: $_" -ForegroundColor Red
    exit 1
}

# Install pyinstaller if missing
Write-Host "Checking PyInstaller..." -ForegroundColor Yellow
pip show pyinstaller | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Clean previous builds
Write-Host ""
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path "build", "dist", "*.spec" -Recurse -Force -ErrorAction SilentlyContinue

# Build EXE
Write-Host ""
Write-Host "Building EXE (this may take a few minutes)..." -ForegroundColor Yellow
Write-Host ""

# Single EXE file
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
python -m PyInstaller --onefile --windowed --name "KWF_Prometheus" `
    --add-data "test_data;test_data" `
    smp12c_vibrodiag/main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Build completed successfully! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "EXE file: dist\KWF_Prometheus.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To run: dist\KWF_Prometheus.exe" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Build error!" -ForegroundColor Red
}
