@echo off
chcp 65001 >nul
echo ============================================
echo   KWF Prometheus - Очистка кэша Python
echo ============================================
echo.

cd /d D:\Coding\pyton_pro\app

echo Удаление __pycache__ директорий...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d"
    echo   ✓ Удалён: %%d
)

echo.
echo Удаление *.pyc файлов...
del /s /q *.pyc 2>nul
echo   ✓ Готово

echo.
echo ============================================
echo   Кэш очищён!
echo ============================================
