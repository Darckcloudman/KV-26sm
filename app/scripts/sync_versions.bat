@echo off
chcp 65001 >nul
echo ============================================
echo   KWF Prometheus - Синхронизация версий
echo ============================================
echo.

echo [1/2] Синхронизация версий...
xcopy /E /I /Y "D:\Coding\pyton_pro\kwf_prometheus" "D:\Coding\pyton_pro\app\kwf_prometheus"
if %errorlevel% equ 0 (
    echo   ✓ Версии синхронизированы
) else (
    echo   ✗ Ошибка синхронизации
)
echo.

echo [2/2] Очистка кэша...
for /d /r "D:\Coding\pyton_pro\app" %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d"
)
del /s /q "D:\Coding\pyton_pro\app\*.pyc" 2>nul
echo   ✓ Кэш очищён
echo.

echo ============================================
echo   Готово! Можно запускать приложение
echo ============================================
