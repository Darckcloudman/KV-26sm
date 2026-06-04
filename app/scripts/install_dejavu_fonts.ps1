# Установка шрифтов DejaVu Sans для KWF Prometheus
# РУЧНАЯ ИНСТРУКЦИЯ (если скрипт не работает):

# 1. Скачайте шрифты:
#    https://dejavu-fonts.github.io/Downloads.html
#    или напрямую:
#    - https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf
#    - https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf

# 2. Скопируйте файлы в:
#    C:\Windows\Fonts\

# 3. Перезапустите KWF Prometheus

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Установка шрифтов DejaVu Sans для PDF" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$fontPath = "$env:WINDIR\Fonts\DejaVuSans.ttf"
$boldPath = "$env:WINDIR\Fonts\DejaVuSans-Bold.ttf"

if (Test-Path $fontPath) {
    Write-Host "[OK] Шрифт DejaVuSans уже установлен" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Шрифт DejaVuSans НЕ найден" -ForegroundColor Red
    Write-Host ""
    Write-Host "Установите шрифт вручную:" -ForegroundColor Yellow
    Write-Host "1. Откройте браузер" -ForegroundColor Yellow
    Write-Host "2. Перейдите: https://dejavu-fonts.github.io/Downloads.html" -ForegroundColor Cyan
    Write-Host "3. Скачайте и распакуйте архив" -ForegroundColor Yellow
    Write-Host "4. Скопируйте DejaVuSans.ttf в C:\Windows\Fonts\" -ForegroundColor Yellow
    Write-Host "5. Перезапустите KWF Prometheus" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "ИЛИ напрямую:" -ForegroundColor Yellow
    Write-Host "  https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf" -ForegroundColor Cyan
}

if (Test-Path $boldPath) {
    Write-Host "[OK] DejaVuSans-Bold уже установлен" -ForegroundColor Green
} else {
    Write-Host "[WARN] DejaVuSans-Bold НЕ найден (будет использован обычный)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
