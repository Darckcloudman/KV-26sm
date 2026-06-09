@echo off
chcp 65001 >nul
echo ============================================
echo   KWF Prometheus v1.4.3 - Запуск приложения
echo ============================================
echo.

cd /d D:\Coding\pyton_pro\app

echo [1/3] Синхронизация версий...
xcopy /E /I /Y "D:\Coding\pyton_pro\kwf_prometheus" "D:\Coding\pyton_pro\app\kwf_prometheus" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Версии синхронизированы
) else (
    echo   ⚠ Предупреждение синхронизации
)
echo.

echo [2/3] Очистка кэша Python...
if exist kwf_prometheus\__pycache__ (
    rd /s /q kwf_prometheus\__pycache__
    echo   ✓ Удалён kwf_prometheus\__pycache__
)
if exist kwf_prometheus\dal\__pycache__ (
    rd /s /q kwf_prometheus\dal\__pycache__
    echo   ✓ Удалён kwf_prometheus\dal\__pycache__
)
if exist kwf_prometheus\gui\__pycache__ (
    rd /s /q kwf_prometheus\gui\__pycache__
    echo   ✓ Удалён kwf_prometheus\gui\__pycache__
)
if exist kwf_prometheus\parsers\__pycache__ (
    rd /s /q kwf_prometheus\parsers\__pycache__
    echo   ✓ Удалён kwf_prometheus\parsers\__pycache__
)
if exist kwf_prometheus\utils\__pycache__ (
    rd /s /q kwf_prometheus\utils\__pycache__
    echo   ✓ Удалён kwf_prometheus\utils\__pycache__
)
if exist kwf_prometheus\exporters\__pycache__ (
    rd /s /q kwf_prometheus\exporters\__pycache__
    echo   ✓ Удалён kwf_prometheus\exporters\__pycache__
)
if exist kwf_prometheus\reports\__pycache__ (
    rd /s /q kwf_prometheus\reports\__pycache__
    echo   ✓ Удалён kwf_prometheus\reports\__pycache__
)
if exist kwf_prometheus\gui\charts\__pycache__ (
    rd /s /q kwf_prometheus\gui\charts\__pycache__
    echo   ✓ Удалён kwf_prometheus\gui\charts\__pycache__
)
if exist kwf_prometheus\gui\workers\__pycache__ (
    rd /s /q kwf_prometheus\gui\workers\__pycache__
    echo   ✓ Удалён kwf_prometheus\gui\workers\__pycache__
)
if exist tests\__pycache__ (
    rd /s /q tests\__pycache__
    echo   ✓ Удалён tests\__pycache__
)
echo.

echo [3/4] Проверка версии...
python -c "from kwf_prometheus.main import *; print('   Версия приложения:', '1.4.3')" 2>nul
if errorlevel 1 (
    echo   ⚠ Не удалось проверить версию, продолжаю запуск...
)
echo.

echo [4/4] Запуск приложения...
echo.
set PYTHONPATH=D:\Coding\pyton_pro\app
python -m kwf_prometheus.main

if errorlevel 1 (
    echo.
    echo ============================================
    echo   ОШИБКА: Приложение завершилось с ошибкой!
    echo ============================================
    echo.
    pause
)
