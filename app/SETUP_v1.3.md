# Настройка KWF Prometheus v1.3

## Быстрый старт

### Вариант 1: Режим файловой системы (по умолчанию)

Ничего настраивать не нужно. Приложение работает как v1.2:

```bash
cd app
python -m kwf_prometheus.main
```

### Вариант 2: Режим PostgreSQL

#### 1. Установите PostgreSQL

**Windows:**
- Скачайте с https://www.postgresql.org/download/windows/
- Установите, запомните пароль пользователя `postgres`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

#### 2. Установите зависимости Python

```bash
cd app
pip install -r requirements.txt
```

#### 3. Настройте .env

Откройте файл `app/.env` и измените:

```env
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vibrodiag
DB_USER=postgres
DB_PASSWORD=ваш_пароль_от_postgres
```

#### 4. Создайте базу данных

**Windows (PowerShell):**
```powershell
createdb -U postgres vibrodiag
```

**Linux/macOS:**
```bash
sudo -u postgres createdb vibrodiag
```

Или через SQL:
```sql
CREATE DATABASE vibrodiag;
```

#### 5. Запустите приложение

```bash
python -m kwf_prometheus.main
```

Таблицы будут созданы автоматически при первом запуске.

---

## Проверка установки

### 1. Проверка подключения к БД

```bash
python -m kwf_prometheus.dal.utils check
```

Ожидаемый вывод:
```
✓ Подключение к БД 'vibrodiag' успешно
```

### 2. Просмотр таблиц

```bash
psql -U postgres -d vibrodiag -c "\dt"
```

Ожидаемые таблицы:
```
public.archives
public.sensor_data
public.analysis_cache
public.turbines
```

---

## Миграция существующих архивов

Если у вас есть архивы в каталоге `test_data`, их можно импортировать в БД:

### Тестовый режим (без записи)

```bash
python migrate_archives.py --dry-run
```

### Реальная миграция

```bash
python migrate_archives.py --path ./test_data
```

### Миграция из другого каталога

```bash
python migrate_archives.py --path C:/Archives/WindTurbines
```

---

## Управление миграциями (Alembic)

### Создать новую миграцию

```bash
cd app/kwf_prometheus/dal
alembic revision --autogenerate -m "Описание изменений"
```

### Применить миграции

```bash
alembic upgrade head
```

### Откатить миграцию

```bash
alembic downgrade -1
```

### Проверить статус

```bash
alembic current
```

---

## Переключение режимов

### Из файловой системы в PostgreSQL

1. Откройте `.env`
2. Установите `USE_DATABASE=true`
3. Настройте параметры БД
4. Перезапустите приложение

### Из PostgreSQL в файловую систему

1. Откройте `.env`
2. Установите `USE_DATABASE=false`
3. Перезапустите приложение

Все данные в БД сохраняются и могут быть использованы позже.

---

## Решение проблем

### Ошибка: "could not connect to server"

**Причина:** PostgreSQL не запущен

**Решение:**
```bash
# Windows (службы)
net start postgresql

# Linux
sudo systemctl start postgresql

# macOS
brew services start postgresql
```

### Ошибка: "database 'vibrodiag' does not exist"

**Причина:** База данных не создана

**Решение:**
```bash
createdb -U postgres vibrodiag
```

### Ошибка: "password authentication failed"

**Причина:** Неверный пароль

**Решение:**
1. Проверьте пароль в `.env`
2. Сбросьте пароль PostgreSQL:
```bash
psql -U postgres
ALTER USER postgres WITH PASSWORD 'new_password';
```

### Ошибка: "No module named 'sqlalchemy'"

**Причина:** Зависимости не установлены

**Решение:**
```bash
pip install -r requirements.txt
```

### Ошибка: "table already exists"

**Причина:** Таблицы уже созданы

**Решение:** Это нормально. Таблицы создаются один раз при первом запуске.

Если нужно пересоздать:
```bash
python -m kwf_prometheus.dal.utils drop
# Затем перезапустите приложение
```

---

## Производительность

### Настройка пула соединений

В `.env` измените:

```env
DB_POOL_SIZE=10      # Количество соединений в пуле
```

Рекомендации:
- Для локальной разработки: 5-10
- Для продакшена: 20-50

### Оптимизация PostgreSQL

```sql
-- Анализ таблиц (после импорта больших объёмов)
VACUUM ANALYZE;

-- Создание индексов (если не созданы автоматически)
CREATE INDEX idx_sensor_data_archive ON sensor_data(archive_id);
CREATE INDEX idx_analysis_cache_archive ON analysis_cache(archive_id);
```

---

## Резервное копирование

### Дамп базы данных

```bash
pg_dump -U postgres vibrodiag > backup.sql
```

### Восстановление

```bash
psql -U postgres vibrodiag < backup.sql
```

### Автоматический бэкап (cron)

```bash
# Добавить в crontab (каждый день в 3:00)
0 3 * * * pg_dump -U postgres vibrodiag > /backups/vibrodiag_$(date +\%Y\%m\%d).sql
```

---

## Дополнительная документация

- [DAL_GUIDE.md](DAL_GUIDE.md) - полное руководство по DAL
- [CHANGELOG_v1.3.md](CHANGELOG_v1.3.md) - список изменений
- [README.md](README.md) - общая информация

---

## Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Запустите `python -m kwf_prometheus.dal.utils check`
3. Проверьте настройки в `.env`
4. Убедитесь, что PostgreSQL запущен
