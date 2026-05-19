# Изменения в версии 1.3

## Дата
2026-01-XX

## Обзор
Версия 1.3 добавляет **Data Access Layer (DAL)** - слой абстракции для работы с данными, поддерживающий как файловую систему (режим v1.2), так и PostgreSQL для хранения больших объёмов данных.

---

## ✨ Новые возможности

### 1. Data Access Layer (DAL)
- **Абстрактный репозиторий** `IVibrationRepository` с методами для работы с данными
- **Две реализации**:
  - `FileSystemRepository` - режим v1.2 (работа с файлами)
  - `PostgresRepository` - режим v1.3 (работа с PostgreSQL)
- **Фабрика репозиториев** `get_repository()` для создания нужной реализации

### 2. PostgreSQL поддержка
- **Модели SQLAlchemy 2.0**:
  - `Turbine` - турбины
  - `Archive` - архивные записи с дедупликацией по SHA256
  - `SensorData` - временные ряды (ARRAY типы)
  - `AnalysisCache` - кэш результатов анализа
- **Асинхронный доступ** через `asyncpg` и SQLAlchemy async
- **Менеджер подключений** `DatabaseManager` с пулом соединений

### 3. Миграции
- **Alembic** для управления миграциями схемы БД
- **Автоматическое создание таблиц** при первом запуске
- **Утилита миграции** `migrate_archives.py` для импорта старых архивов

### 4. Кэширование
- **Кэш спектров** - результаты FFT сохраняются в БД
- **Кэш анализа** - RMS, зона, пики не пересчитываются повторно

### 5. Конфигурация
- **`.env` файл** для настроек
- **Pydantic Settings** для валидации конфигурации
- **Флаг `USE_DATABASE`** для переключения режимов

---

## 🔧 Технические улучшения

### Асинхронность
- Интеграция `asyncio` с `QThread` для неблокирующей работы GUI
- Паттерн `asyncio.to_thread()` для блокирующих операций
- `scoped_session` для многопоточной работы

### Инъекция зависимостей
- `MainWindow` создаёт репозиторий через фабрику
- `HomeScreen` получает репозиторий через конструктор
- Полная абстракция UI от источника данных

### Структура проекта
```
app/
├── .env                          ← Новый файл конфигурации
├── migrate_archives.py           ← Утилита миграции
├── smp12c_vibrodiag/
│   ├── main.py                   ← Обновлена версия
│   ├── gui/
│   │   ├── main_window.py        ← Инъекция репозитория
│   │   └── home_screen.py        ← Работа с репозиторием
│   ├── parsers/
│   │   └── rd2_parser.py         ← Без изменений
│   └── dal/                      ← НОВЫЙ ПАКЕТ
│       ├── config.py
│       ├── database.py
│       ├── utils.py
│       ├── models/
│       ├── repositories/
│       └── alembic/
```

---

## 📦 Зависимости

### Новые
```
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.12.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
```

### Обновлённые
```
numpy>=1.26.0        (было 1.24.0)
scipy>=1.11.0        (было 1.10.0)
PySide6>=6.6.0       (было 6.5.0)
```

---

## 🎯 Обратная совместимость

### Сохранено
- ✅ Все UI элементы (вкладки, стили, схема турбины)
- ✅ Формат файлов .zip/.rd2
- ✅ MultiSensorRD2Parser
- ✅ ParseThread (QThread)
- ✅ Анализ данных и графики

### Изменено (минимально)
- ⚠️ `HomeScreen.__init__()` теперь принимает `repository`
- ⚠️ `MainWindow.__init__()` создаёт репозиторий
- ⚠️ `ParseThread` использует репозиторий

---

## 🚀 Быстрый старт

### Режим файловой системы (по умолчанию)
```bash
# Ничего менять не нужно
python -m smp12c_vibrodiag.main
```

### Режим PostgreSQL
```bash
# 1. Настроить .env
USE_DATABASE=true
DB_HOST=localhost
DB_NAME=vibrodiag
DB_USER=postgres
DB_PASSWORD=your_password

# 2. Создать БД
createdb -U postgres vibrodiag

# 3. Запустить
python -m smp12c_vibrodiag.main
```

---

## 📝 Миграции

### Автоматические
Таблицы создаются при первом запуске с `USE_DATABASE=true`.

### Ручные (Alembic)
```bash
cd app/smp12c_vibrodiag/dal
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Импорт архивов
```bash
# Тестовый режим
python migrate_archives.py --dry-run

# Реальная миграция
python migrate_archives.py --path ./test_data
```

---

## 🧪 Тестирование

```bash
# Проверка подключения
python -m smp12c_vibrodiag.dal.utils check

# Удаление таблиц (осторожно!)
python -m smp12c_vibrodiag.dal.utils drop
```

---

## 📊 Производительность

### Улучшения
- Кэширование спектров (без повторного FFT)
- Дедупликация архивов (SHA256)
- Пул соединений (10 + 20 overflow)
- ARRAY типы PostgreSQL для временных рядов

### Рекомендации
- Настройте `DB_POOL_SIZE` под нагрузку
- Регулярно делайте `VACUUM ANALYZE` в PostgreSQL
- Используйте индексы для частых запросов

---

## 🐛 Известные ограничения

1. **PostgreSQL требуется** для режима БД (не работает с SQLite)
2. **ARRAY типы** специфичны для PostgreSQL
3. **Миграции** требуют Alembic и psycopg2

---

## 📅 Сессия 2025-01-25 — UI/UX доработки

### Новый диалог выбора директории (`directory_tree_dialog.py`)
- **QFileSystemModel + QTreeView** — нативный просмотр файловой системы
- **Панель навигации** (Back / Forward / Up / Home / Refresh) с иконками QtAwesome (`mdi.*`)
- **История навигации** — стек `_history` с ходом назад/вперёд
- **Цикличный Home** — 1-е нажатие: свернуть до дисков; 2-е нажатие: перейти в домашнюю папку
- **Фиксированный размер** `480×530 px`
- **Компактные строки** `min-height: 14px`, иконки `8×8 px`, шрифт `10px`
- **Пунктирные связи** яркостью `rgba(255,255,255,0.28)`
- **Кастомный скроллбар** (тонкий, серый фон, белый ползунок)

### Стилизованные сообщения (`styled_message_box.py`)
- Единый модуль для всех `QMessageBox` в проекте
- **Фон `#5A5A5A`** — не чёрный, читаемый
- **Иконки QtAwesome** на заголовке окна:
  - `mdi.alert` (красная) — critical
  - `mdi.alert` (жёлтая) — warning
  - `mdi.information` (синяя) — info
  - `mdi.help-circle` (синяя) — question
- Заменены все `QMessageBox` в `home_screen.py`, `main_window.py`, `main_window_old.py`, `analysis_data_screen.py`, `directory_tree_dialog.py`

### PowerShell launch scripts
- `install_and_run.ps1` и `build_exe.ps1` — `try/catch [PSSecurityException]`
- **Автоматический fallback** на `powershell.exe -ExecutionPolicy Bypass` для venv

### Зависимости
- Добавлен `QtAwesome>=1.4.0` в `requirements.txt` и `setup.py`

### Документация
- **COLORS.md** — полный справочник цветов всех экранов (Home, Analysis, DirectoryTreeDialog)
- Обновлены `README.md`, `GETTING_STARTED.md`, `TESTING_INSTRUCTIONS.md`

---

## 🔜 Планы на v1.4

- [ ] Сравнение трендов (график изменения RMS по времени)
- [ ] Экспорт результатов в CSV/Excel
- [ ] Отчёты по турбинам
- [ ] Веб-интерфейс для просмотра данных
- [ ] Поддержка SQLite для локального хранения

---

## 👥 Авторы

- **Разработка**: A.Telezhenko, 2026
- **DAL архитектура**: NLP-Core-Team
- **Стандарты**: ISO 10816-21:2015, ГОСТ 10816-21-2021

---

## 📄 Документация

- [DAL_GUIDE.md](DAL_GUIDE.md) - полное руководство по DAL
- [README.md](README.md) - общая информация
- [GETTING_STARTED.md](GETTING_STARTED.md) - быстрый старт
