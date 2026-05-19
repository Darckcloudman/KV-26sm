# Скрипт установки зависимостей и запуска приложения SMP12C VibroDiag
# Лучшая практика: запускать через powershell.exe -ExecutionPolicy Bypass -File .\install_and_run.ps1

Write-Host "=== SMP12C VibroDiag Analyzer - Установка и запуск" -ForegroundColor Cyan
Write-Host ""

# Проверка Python
Write-Host "1. Проверка Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "   Python: $pythonVersion" -ForegroundColor Green

# Создание виртуального окружения
Write-Host ""
Write-Host "2. Создание виртуального окружения..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   Виртуальное окружение уже существует" -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "   Виртуальное окружение создано" -ForegroundColor Green
}

# Активация окружения с обработкой политики выполнения
Write-Host ""
Write-Host "3. Активация окружения..." -ForegroundColor Yellow
try {
    .\venv\Scripts\Activate.ps1 -ErrorAction Stop
    Write-Host "   Окружение активировано" -ForegroundColor Green
} catch [System.Management.Automation.PSSecurityException] {
    Write-Host "   Политика выполнения PowerShell блокирует активацию. Обходим через Bypass..." -ForegroundColor Yellow
    powershell.exe -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Ошибка: не удалось активировать окружение. Запустите скрипт через:" -ForegroundColor Red
        Write-Host "   powershell.exe -ExecutionPolicy Bypass -File .\install_and_run.ps1" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "   Окружение активировано (Bypass)" -ForegroundColor Green
} catch {
    Write-Host "   Ошибка активации: $_" -ForegroundColor Red
    exit 1
}

# Обновление pip
Write-Host ""
Write-Host "4. Обновление pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "   pip обновлён" -ForegroundColor Green

# Установка зависимостей
Write-Host ""
Write-Host "5. Установка зависимостей..." -ForegroundColor Yellow
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
python -m pip install -r requirements.txt
Write-Host "   Зависимости установлены" -ForegroundColor Green

# Запуск приложения
Write-Host ""
Write-Host "6. Запуск приложения..." -ForegroundColor Yellow
Write-Host ""
python -m smp12c_vibrodiag.main

