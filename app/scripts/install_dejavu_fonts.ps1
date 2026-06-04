# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Скрипт автоматической установки шрифтов DejaVu Sans для поддержки кириллицы в PDF-отчётах.

.DESCRIPTION
    Скачивает и устанавливает шрифты DejaVu Sans в систему Windows.
    Требуется для корректного отображения кириллицы в PDF-отчётах KWF Prometheus.

.NOTES
    Автор: NLP-Core-Team (Koda assistant)
    Дата: 2026
    Версия: 1.0

.REQUIREMENTS
    - PowerShell 5.0+
    - Права администратора (для установки шрифтов)
#>

param(
    [switch]$Help,
    [switch]$NoAdmin
)

$fontUrl = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-sans-ttf-2.37.tar.gz"
$fontZipPath = "$env:TEMP\dejavu-fonts.zip"
$fontExtractPath = "$env:TEMP\dejavu-fonts"
$fontInstallPath = "$env:WINDIR\Fonts"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-DejaVu-Fonts {
    Write-Info "Загрузка шрифтов DejaVu Sans..."
    
    try {
        # Скачиваем шрифты
        Invoke-WebRequest -Uri $fontUrl -OutFile $fontZipPath -UseBasicParsing
        Write-Success "Шрифты загружены: $fontZipPath"
    }
    catch {
        Write-Error-Custom "Не удалось загрузить шрифты: $_"
        return $false
    }
    
    Write-Info "Распаковка шрифтов..."
    
    try {
        # Создаём директорию для распаковки
        if (Test-Path $fontExtractPath) {
            Remove-Item $fontExtractPath -Recurse -Force
        }
        New-Item -ItemType Directory -Path $fontExtractPath -Force | Out-Null
        
        # Распаковываем архив
        Expand-Archive -Path $fontZipPath -DestinationPath $fontExtractPath -Force
        Write-Success "Шрифты распакованы: $fontExtractPath"
    }
    catch {
        Write-Error-Custom "Не удалось распаковать шрифты: $_"
        return $false
    }
    
    Write-Info "Поиск TTF файлов..."
    
    # Ищем файлы шрифтов
    $ttfFiles = Get-ChildItem -Path $fontExtractPath -Filter "*.ttf" -Recurse | 
                Where-Object { $_.Name -like "DejaVuSans*.ttf" }
    
    if ($ttfFiles.Count -eq 0) {
        Write-Error-Custom "Шрифты DejaVuSans не найдены в архиве"
        return $false
    }
    
    Write-Info "Найдено шрифтов: $($ttfFiles.Count)"
    
    # Копируем шрифты в системную директорию
    $installedCount = 0
    foreach ($fontFile in $ttfFiles) {
        $destPath = Join-Path $fontInstallPath $fontFile.Name
        
        try {
            if (Test-Path $destPath) {
                Write-Info "Шрифт уже установлен: $($fontFile.Name)"
            }
            else {
                Copy-Item -Path $fontFile.FullName -Destination $destPath -Force
                Write-Success "Установлен шрифт: $($fontFile.Name)"
                $installedCount++
            }
        }
        catch {
            Write-Error-Custom "Не удалось установить шрифт $($fontFile.Name): $_"
        }
    }
    
    # Очищаем временные файлы
    Write-Info "Очистка временных файлов..."
    if (Test-Path $fontZipPath) {
        Remove-Item $fontZipPath -Force
    }
    if (Test-Path $fontExtractPath) {
        Remove-Item $fontExtractPath -Recurse -Force
    }
    
    Write-Success "Установка завершена! Установлено шрифтов: $installedCount"
    Write-Info "Перезапустите KWF Prometheus для применения изменений."
    
    return $true
}

function Test-Font-Installed {
    $testFontPath = Join-Path $fontInstallPath "DejaVuSans.ttf"
    if (Test-Path $testFontPath) {
        Write-Success "Шрифт DejaVuSans уже установлен в системе"
        return $true
    }
    return $false
}

# Основная логика
if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path
    exit 0
}

Write-Info "=== Установка шрифтов DejaVu Sans для KWF Prometheus ==="
Write-Host ""

# Проверяем, установлен ли шрифт
if (Test-Font-Installed) {
    Write-Success "Шрифт DejaVuSans уже установлен. Выход."
    exit 0
}

# Проверяем права администратора
if (-not $NoAdmin) {
    if (-not (Test-Admin)) {
        Write-Error-Custom "Требуются права администратора для установки шрифтов."
        Write-Host ""
        Write-Info "Запустите скрипт от имени администратора:"
        Write-Host "  PowerShell -ExecutionPolicy Bypass -File .\install_dejavu_fonts.ps1"
        Write-Host ""
        Write-Info "ИЛИ установите шрифт вручную:"
        Write-Host "  1. Скачайте с https://dejavu-fonts.github.io/"
        Write-Host "  2. Скопируйте DejaVuSans.ttf в C:\Windows\Fonts\"
        exit 1
    }
}

# Устанавливаем шрифты
$success = Install-DejaVu-Fonts

if ($success) {
    Write-Host ""
    Write-Success "=== Установка завершена успешно ==="
    exit 0
}
else {
    Write-Host ""
    Write-Error-Custom "=== Установка завершена с ошибками ==="
    exit 1
}
