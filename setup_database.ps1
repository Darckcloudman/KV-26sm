# Скрипт создания базы данных vibrodiag для KWF Prometheus
# Требует установленного PostgreSQL и psql в PATH

$env:PGPASSWORD = "postgres"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "СОЗДАНИЕ БАЗЫ ДАННЫХ vibrodiag" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Проверяем наличие psql
try {
    $psqlVersion = psql --version 2>&1
    Write-Host "[OK] psql найден: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] psql не найден в PATH" -ForegroundColor Red
    Write-Host "Убедитесь, что PostgreSQL установлен и psql добавлен в PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Обычно psql находится в:" -ForegroundColor Yellow
    Write-Host "  C:\Program Files\PostgreSQL\16\bin\psql.exe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Добавьте путь к bin в环境变量 PATH или запустите отладку вручную:" -ForegroundColor Yellow
    Write-Host "  psql -U postgres -f create_database.sql" -ForegroundColor Cyan
    exit 1
}

Write-Host "`nПопытка создания базы данных..." -ForegroundColor White

# Создаём БД
$createDbQuery = "CREATE DATABASE vibrodiag WITH OWNER = postgres ENCODING = 'UTF8' LC_COLLATE = 'Russian_Russia.1251' LC_CTYPE = 'Russian_Russia.1251' TABLESPACE = pg_default CONNECTION LIMIT = -1;"

try {
    $result = psql -U postgres -h localhost -c "$createDbQuery" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] База данных vibrodiag успешно создана!" -ForegroundColor Green
    } else {
        if ($result -like "*already exists*") {
            Write-Host "[WARNING] База данных уже существует" -ForegroundColor Yellow
        } else {
            Write-Host "[ERROR] Ошибка создания БД: $result" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "[ERROR] Исключение при создании БД: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ИНИЦИАЛИЗАЦИЯ ТАБЛИЦ (Alembic)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Запускаем Alembic для создания таблиц
try {
    Write-Host "`nЗапуск alembic upgrade head..." -ForegroundColor White
    alembic upgrade head
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Таблицы успешно созданы!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Ошибка при создании таблиц" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Исключение при запуске alembic: $_" -ForegroundColor Red
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ГОТОВО" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "`nТеперь можно запустить приложение:" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor Cyan
