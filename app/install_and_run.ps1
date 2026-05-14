# Скрипт установки зависимостей и запуска приложения SMP12C VibroDiag

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

# Активация окружения
Write-Host ""
Write-Host "3. Активация окружения..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Обновление pip
Write-Host ""
Write-Host "4. Обновление pip..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --upgrade pip
Write-Host "   pip обновлён" -ForegroundColor Green

# Установка зависимостей
Write-Host ""
Write-Host "5. Установка зависимостей..." -ForegroundColor Yellow
Set-Location "D:\Сoding\pyton_pro\app"
python -m pip install -r requirements.txt
Write-Host "   Зависимости установлены" -ForegroundColor Green

# Запуск приложения
Write-Host ""
Write-Host "6. Запуск приложения..." -ForegroundColor Yellow
Write-Host ""
python -m smp12c_vibrodiag.main
