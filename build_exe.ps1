# Скрипт сборки EXE файла SMP12C VibroDiag
# Лучшая практика: запускать через powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1

Write-Host "=== SMP12C VibroDiag Analyzer - Сборка EXE" -ForegroundColor Cyan
Write-Host ""

# Проверка виртуального окружения
if (-not (Test-Path "venv")) {
    Write-Host "Ошибка: Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Сначала запустите: .\install_and_run.ps1" -ForegroundColor Yellow
    exit 1
}

# Активация окружения с обработкой политики выполнения
Write-Host "Активация окружения..." -ForegroundColor Yellow
try {
    .\venv\Scripts\Activate.ps1 -ErrorAction Stop
    Write-Host "   Окружение активировано" -ForegroundColor Green
} catch [System.Management.Automation.PSSecurityException] {
    Write-Host "   Политика выполнения PowerShell блокирует активацию. Обходим через Bypass..." -ForegroundColor Yellow
    powershell.exe -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Ошибка: не удалось активировать окружение. Запустите скрипт через:" -ForegroundColor Red
        Write-Host "   powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "   Окружение активировано (Bypass)" -ForegroundColor Green
} catch {
    Write-Host "   Ошибка активации: $_" -ForegroundColor Red
    exit 1
}

# Установка pyinstaller если нет
Write-Host "Проверка PyInstaller..." -ForegroundColor Yellow
pip show pyinstaller | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Установка PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Очистка предыдущих сборок
Write-Host ""
Write-Host "Очистка предыдущих сборок..." -ForegroundColor Yellow
Remove-Item -Path "build", "dist", "*.spec" -Recurse -Force -ErrorAction SilentlyContinue

# Сборка EXE
Write-Host ""
Write-Host "Сборка EXE (это займёт несколько минут)..." -ForegroundColor Yellow
Write-Host ""

# Вариант 1: Один EXE файл
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
python -m PyInstaller --onefile --windowed --name "SMP12C_VibroDiag" `
    --add-data "test_data;test_data" `
    smp12c_vibrodiag/main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Сборка успешно завершена! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "EXE файл: dist\SMP12C_VibroDiag.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Для запуска: dist\SMP12C_VibroDiag.exe" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Ошибка сборки!" -ForegroundColor Red
}
