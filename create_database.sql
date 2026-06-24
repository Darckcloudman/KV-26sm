-- Создание базы данных vibrodiag
-- Запуск: psql -U postgres -f create_database.sql

-- Создаём базу данных
CREATE DATABASE vibrodiag
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Russian_Russia.1251'
    LC_CTYPE = 'Russian_Russia.1251'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Комментарий
COMMENT ON DATABASE vibrodiag IS 'KWF Prometheus - Вибродиагностика ВЭУ';
