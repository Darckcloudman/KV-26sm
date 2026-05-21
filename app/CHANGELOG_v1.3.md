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

## 📅 Сессия 2025-01-26 — Интеграция экранов v1.3.1

### Исправлено
- **Миграция `upload_info_screen.py` с PyQt5 на PySide6** — полная совместимость с проектом
- **Миграция `raw_data_screen.py` с PyQt5 на PySide6** — полная совместимость с проектом
- **`PostgresRepository.get_turbine_metrics()`** — теперь корректно сохраняет и читает метрики турбины из БД (power_kw, generator_speed_rpm, wind_speed_ms, cumulative_power_kwh)

### Добавлено
- **Полная интеграция экранов в навигацию**:
  ```
  Home → UploadInfoScreen → RawDataScreen → AnalysisDataScreen
  ```
- **Кнопка "[>] Перейти к анализу"** на RawDataScreen для перехода к анализу
- **Поля метрик в модель `Archive`** — `power_kw`, `generator_speed_rpm`, `wind_speed_ms`, `cumulative_power_kwh`
- **Метод `_extract_wtg_from_path()`** в MainWindow для извлечения имени турбины

### Архитектура навигации
```
HomeScreen (выбор архива)
    ↓ [Проанализировать]
UploadInfoScreen (информация о загрузке, статусы датчиков)
    ↓ [<- Назад] / [[>] Обработать]
RawDataScreen (визуализация сырых данных, сетка 2×4)
    ↓ [<- Назад] / [[>] Перейти к анализу]
AnalysisDataScreen (спектры, зоны ISO 10816)
```

---

## 📅 Сессия 2025-01-26 — DAL + Функциональность v1.3.1 (Вариант Б)

### 1. Логирование в DAL
- **Новый модуль** `dal/logger.py`:
  - `setup_logging()` — настройка логирования в файл `app.log` + консоль
  - `get_logger(name)` — получение логгера `DAL.<name>`
  - RotatingFileHandler: 5 МБ, 3 резервные копии
  - Формат: `2025-05-20 14:30:15 - DAL.PostgresRepository - INFO - Сообщение`
- **Логирование в компонентах**:
  - `DatabaseManager` — инициализация, создание таблиц, health check
  - `PostgresRepository` — load_archive, get_turbine_metrics, ошибки
  - `RepositoryFactory` — выбор режима, fallback
- **Настройки в `.env`**: `LOG_LEVEL=INFO`

### 2. Улучшенная обработка ошибок PostgreSQL
- **Retry-механизм** — декоратор `@_with_retry(max_retries=3, delay=1.0)`
  - Автоматические повторные попытки при `OperationalError`
  - Логирование каждой попытки
- **Graceful fallback** — `RepositoryFactory`
  - При недоступности PostgreSQL автоматически переключается на `FileSystemRepository`
  - Пользователю показывается предупреждение: «Не удалось соединиться с базой данных...»
- **Настройки в `.env`**:
  - `DB_CONNECT_RETRIES=3` — количество попыток
  - `DB_CONNECT_RETRY_DELAY=1.0` — задержка между попытками

### 3. Поиск/фильтрация в таблице архивов HomeScreen
- **QLineEdit** с placeholder «Поиск...» над таблицей
- **Фильтрация в реальном времени** по мере ввода
- **Поиск по**: Турбина, Дата записи, Имя файла (без учёта регистра)
- **Кнопка «Очистить»** — сброс фильтра
- **Сообщение «Ничего не найдено»** при пустом результате
- **Стили** в единой чёрно-белой теме

### 4. Индикатор прогресса миграции БД
- **Новый файл** `gui/migration_dialog.py`:
  - `MigrationDialog` — модальное окно с прогресс-баром
  - `MigrationWorker` (QThread) — миграция в фоне без блокировки GUI
  - Шаги: «Проверка подключения...» → «Создание таблиц...» → «Проверка структуры...»
  - Автоматическое закрытие при успехе (1.5 сек)
  - Кнопка OK при ошибке

### Новые/изменённые файлы
```
app/
├── .env                                          ← Обновлён: LOG_LEVEL, DB_CONNECT_RETRIES
├── requirements.txt                              ← Обновлён: +psycopg2-binary
├── app.log                                       ← Новый: файл логов
├── smp12c_vibrodiag/
│   ├── main.py                                   ← Обновлён: setup_logging()
│   ├── dal/
│   │   ├── logger.py                             ← Новый: модуль логирования
│   │   ├── config.py                             ← Обновлён: log_level, db_connect_retries
│   │   ├── database.py                           ← Обновлён: connect_with_retry(), логирование
│   │   └── repositories/
│   │       ├── factory.py                        ← Обновлён: graceful fallback
│   │       └── postgres.py                       ← Обновлён: @_with_retry, логирование
│   └── gui/
│       ├── home_screen.py                        ← Обновлён: поиск/фильтрация
│       └── migration_dialog.py                   ← Новый: диалог миграции
```

---

## 📅 Сессия 2025-01-27 — Экспорт и отчёты v1.3.1 (Вариант В)

### 1. Экспорт результатов анализа в CSV/Excel
- **CSV экспорт** (`exporters/csv_exporter.py`):
  - Разделитель: точка с запятой (`;`)
  - Кодировка: UTF-8 with BOM
  - Содержит 4 раздела: Метаданные, Временные ряды, Спектры, Результаты анализа
- **Excel экспорт** (`exporters/excel_exporter.py`):
  - Использует openpyxl (без pandas)
  - 4 листа: «Метаданные», «Временные ряды», «Спектры», «Результаты анализа»
  - Чёрно-белая тема оформления
- **Интерфейс**:
  - Кнопки «CSV», «Excel» на вкладке «Анализ данных» (справа от зон ISO)
  - Пункты меню «Файл» → «Экспорт» → CSV / Excel
- **Потоки**: `ExportWorker` (QThread) — не блокирует GUI, с QProgressDialog

### 2. График трендов RMS по времени
- **Новая вкладка** «Тренды» (`gui/trends_screen.py`):
  - pyqtgraph для производительности
  - Выбор: турбина, датчик (1–8), тип фильтра (НЧ/ВЧ/ВЧ(ф))
  - Ось X: дата/время, Ось Y: RMS
  - Статистика: мин, макс, среднее, количество записей
- **Источники данных**:
  - PostgreSQL: из таблиц archives + sensor_data
  - Файловый режим: сканирование каталога, парсинг архивов
- **Меню**: «Анализ» → «График трендов»

### 3. PDF-отчёт по турбине
- **Генератор** (`reports/pdf_generator.py`):
  - Использует reportlab
  - Содержание:
    1. Параметры турбины (мощность, RPM, ветер, выработка)
    2. Таблица состояния датчиков (RMS, зоны ISO 10816)
    3. Встроенные графики (временной ряд + спектры)
    4. Заключение (автоматическое на основе зон)
    5. Подвал (дата, версия, автор)
  - Подсветка зон: A (зелёный), B (жёлтый), C (оранжевый), D (красный)
- **Интерфейс**:
  - Кнопка «PDF» на вкладке «Анализ данных»
  - Пункт меню «Файл» → «Экспорт» → «PDF-отчёт»
- **Потоки**: `PDFReportWorker` (QThread) — генерация в фоне, с прогресс-диалогом

### Новые/изменённые файлы
```
app/
├── requirements.txt                              ← +openpyxl, +reportlab
├── smp12c_vibrodiag/
│   ├── exporters/
│   │   ├── __init__.py                           ← Новый
│   │   ├── csv_exporter.py                       ← Новый
│   │   └── excel_exporter.py                     ← Новый
│   ├── reports/
│   │   ├── __init__.py                           ← Новый
│   │   └── pdf_generator.py                      ← Новый
│   └── gui/
│       ├── analysis_data_screen.py               ← +кнопки CSV/Excel/PDF
│       ├── export_thread.py                      ← Новый
│       ├── pdf_report_thread.py                  ← Новый
│       ├── trends_screen.py                      ← Новый
│       └── main_window.py                        ← +вкладка Тренды, +меню Экспорт
```

---

## 📅 Сессия 2025-01-28 — Тестирование и стабилизация v1.3.1 (Вариант Г)

### Unit-тесты
- **Новая директория** `tests/`:
  - `conftest.py` — фикстуры (sample_vibration_data, sample_turbine_metrics, temp_dir)
  - `test_utils.py` — тесты конвертаций и анализа вибрации (16 тестов)
  - `test_exporters.py` — тесты CSV и Excel экспорта (7 тестов)
  - `test_reports.py` — тесты PDF генерации (5 тестов)
  - `test_dal.py` — тесты DAL, Settings, RepositoryFactory (9 тестов)
  - `test_rd2_parser.py` — тесты парсера (5 тестов)
  - `pytest.ini` — конфигурация pytest
  - `README.md` — документация по запуску тестов
- **Результаты**: 41 passed, 3 skipped (PostgreSQL / тестовые данные)

### Исправления
- **Pydantic deprecation** — `dal/config.py`: заменён class-based `Config` на `SettingsConfigDict`
- **Границы зон ISO 10816** — тесты подтвердили корректные пороги:
  - Ускорение: A ≤1.0, B ≤2.5, C ≤5.0, D >5.0 (м/с²)
  - Скорость: A ≤2.3, B ≤4.5, C ≤11.2, D >11.2 (мм/с)
- **FFT edge cases** — обработка пустых массивов (ValueError)

### Новые/изменённые файлы
```
app/
├── pytest.ini                                    ← Новый
├── tests/
│   ├── __init__.py                               ← Новый
│   ├── conftest.py                               ← Новый
│   ├── README.md                                 ← Новый
│   ├── test_utils.py                             ← Новый
│   ├── test_exporters.py                         ← Новый
│   ├── test_reports.py                           ← Новый
│   ├── test_dal.py                               ← Новый
│   └── test_rd2_parser.py                        ← Новый (существовал)
└── smp12c_vibrodiag/
    └── dal/
        └── config.py                             ← SettingsConfigDict
```

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

## 📅 Сессия 2025-05-20 — v1.4 Дедупликация, Идентификация приборов, Статус-бар, Настройки, Ветропарк

### Дедупликация записей

**Модель Turbine (обновлена):**
- Добавлены поля прибора: `device`, `serial_number`, `mac_address`, `ip_address`, `firmware_version`
- Уникальные индексы: `serial_number`, `mac_address` (глобально уникальны)
- Привязка прибора к турбине: один прибор → одна турбина (навсегда)

**Модель Archive (обновлена):**
- Добавлены поля: `sensor_id` (1-8), `filter_type` (FILTER/LOW/HIGH)
- Уникальный составной индекс: `(turbine_id, record_datetime, sensor_id, filter_type)`
- Дедупликация на уровне логической записи (а не только по хэшу файла)

**Алгоритм загрузки (PostgresRepository.load_archive):**
- Для каждого .rd2 файла проверяется уникальность по ключу `(turbine_id, record_datetime, sensor_id, filter_type)`
- Дубликаты пропускаются с логированием
- Возвращает результат: `{success: bool, added: int, skipped: int, errors: List[str]}`

**Обработка конфликтов:**
- Если `serial_number` уже привязан к другой `wtg_id` — критическая ошибка, загрузка отменяется
- Пользователю показывается сообщение с деталями конфликта
- Логирование с уровнем ERROR

### Идентификация прибора SMP12C

**Метаданные из .rd2 файла:**
| Поле | Где находится | Уникальность | Использование |
|------|---------------|--------------|---------------|
| serial_number | Строка 4: Serial Number | Глобально уникален | Главный идентификатор |
| mac_address | Строка 4: MAC | Глобально уникален | Резервный идентификатор |
| device | Строка 4: Device | — | Модель (12C) |
| firmware_version | Строка 4: Firmware version | — | Версия прошивки |
| ip_address | Строка 4: IP | Может меняться | Последний известный IP |
| wtg_id | Строка 1: WTG ID | Локально уникален | Человеко-читаемое имя |

**Порядок поиска турбины:**
1. По `serial_number` (главный идентификатор)
2. По `mac_address` (если serial не найден)
3. По `wtg_id` (если прибор ещё не зарегистрирован)

**Обновление данных:**
- `ip_address`, `firmware_version` — обновляются при каждой загрузке
- `serial_number`, `mac_address`, `device` — заполняются один раз
- `wtg_id` — никогда не меняется (привязка постоянна)

### Миграция (Alembic)

**Файл:** `dal/alembic/versions/002_add_device_info_and_deduplication.py`

**Изменения turbines:**
- `device VARCHAR(20)` — модель устройства
- `serial_number VARCHAR(50) UNIQUE` — серийный номер
- `mac_address VARCHAR(17) UNIQUE` — MAC-адрес
- `ip_address VARCHAR(45)` — IP-адрес
- `firmware_version VARCHAR(20)` — версия прошивки

**Изменения archives:**
- `sensor_id INTEGER NOT NULL` — номер датчика
- `filter_type VARCHAR(10) NOT NULL` — тип фильтра
- `UNIQUE(turbine_id, record_datetime, sensor_id, filter_type)` — уникальный ключ

### UI: Информация о загрузке

**Статус-бар (main_window.py):**
- Убрано текстовое меню — оставлена только иконка состояния
- Иконки QtAwesome для индикации состояния:
  - `mdi.check-circle` (зелёная) — готово к работе
  - `mdi.loading` (жёлтая) — загрузка данных
  - `mdi.alert-circle` (красная) — ошибка
  - `mdi.database` (синяя) — режим PostgreSQL
  - `mdi.folder` (серая) — режим файловой системы
- **Новый метод `show_status_message()`** — показ сообщения с иконкой
- Индикатор прогресса (QProgressBar) — справа, скрыт по умолчанию
- Часы (HH:MM:SS) — обновляются каждую секунду
- ToolTip — показывает текущее состояние при наведении

**Уведомления о дедупликации:**
- После загрузки архива показывается сообщение:
  - «Загружено: X новых, пропущено: Y дубликатов»
  - Иконка: `mdi.info` (синяя) или `mdi.check-circle` (зелёная)
- Длительность: 5 секунд

### Настройки (settings_dialog.py)

**Диалог настроек с 4 вкладками:**
- База данных (хост, порт, пользователь, БД, ретраи)
- Хранилище (путь к архивам)
- Логирование (уровень, файл/консоль)
- Модули (статус 9 критических модулей)

**Сохранение в .env** — изменения записываются в файл конфигурации

**Индикаторы модулей** — зелёный/красный статус с описанием

### Ветропарк (57 ВЭУ)

**Идентификация ВЭУ** — автоматическое распознавание по метаданным .rd2

**Статистика по ВЭУ** — на экране UploadInfoScreen (записи, даты, RMS, зона D)

**Тренды RMS** — на экране TrendsScreen:
- Выбор конкретной ВЭУ из списка
- "Среднее по ветропарку" — агрегация по всем турбинам
- Пороговые линии зон ISO 10816 (A/B/C/D)

**Асинхронная загрузка** — через QThread + asyncio

### Руководство разработчика (DEVELOPMENT_GUIDELINES.md)

**Обновлено:**
- **Запрет на emoji** — правило "никогда не использовать emoji в коде"
- **Таблица замен** — 20+ emoji → QtAwesome иконки
- **Раздел о дедупликации** — правила уникальности, алгоритм загрузки
- **Раздел об идентификации прибора** — метаданные, порядок поиска
- **Цветовая палитра** — справочник по ui_styles.py
- **Архитектура GUI** — структура экранов и навигация
- **Стиль кода** — именование, документирование, обработка ошибок

### Стили (ui_styles.py)

**Добавлены:**
- `STATUSBAR_STYLE` — оформление статус-бара
- `PROGRESSBAR_STYLE` — оформление прогресс-бара
- `STATUSBAR_ICON_STYLE` — стиль иконки статуса

### Документация

**Обновлено:**
- `CHANGELOG_v1.3.md` — раздел v1.4 Дедупликация/Идентификация/Статус-бар
- `COLORS.md` — разделы main_window.py, settings_dialog.py, trends_screen.py
- `README.md` — ссылка на DEVELOPMENT_GUIDELINES.md

### Новые/изменённые файлы

```
app/
├── DEVELOPMENT_GUIDELINES.md                    ← Новый: руководство разработчика
├── CHANGELOG_v1.3.md                            ← Обновлён: v1.4 раздел
├── COLORS.md                                    ← Обновлён: новые экраны
├── smp12c_vibrodiag/
│   ├── dal/
│   │   ├── alembic/versions/
│   │   │   └── 002_add_device_info_and_deduplication.py  ← Новый
│   │   ├── models/
│   │   │   ├── turbine.py                       ← Обновлён: поля прибора
│   │   │   └── archive.py                       ← Обновлён: sensor_id, filter_type
│   │   └── repositories/
│   │       ├── base.py                          ← Обновлён: сигнатура load_archive
│   │       ├── postgres.py                      ← Обновлён: дедупликация, _get_or_create_turbine
│   │       └── file_system.py                   ← Обновлён: возврат Dict
│   └── gui/
│       ├── main_window.py                       ← Обновлён: show_status_message()
│       ├── home_screen.py                       ← Обновлён: обработка load_result
│       ├── settings_dialog.py                   ← Обновлён: 4 вкладки, без emoji
│       └── ui_styles.py                         ← Обновлён: статус-бар стили
```

---

## 📅 Сессия 2025-06-01 — v1.4 Единый сервис сохранения, Автопарсинг, Иерархическое хранилище

### Единый сервис сохранения данных (DataPersistenceService)

**Файл:** `dal/persistence_service.py`

**Архитектура:**
- Единый фасад над `PostgresRepository` для всех точек входа
- Асинхронный, не блокирует GUI
- Возвращает структурированный результат: `{success, added, skipped, errors, wtg_id}`

**Функции:**
- `save_archive(path)` — сохранение .zip или .rd2 файла
- Для ZIP: распаковка во временную папку, обработка каждого .rd2
- Для .rd2: прямая загрузка через репозиторий
- Проверка `processed_archives` перед обработкой (пропуск уже обработанных)
- Автоматическая очистка временных файлов

**Интеграция:**
- `HomeScreen` — через `ParseThread` (с `persistence_service`)
- `AutoScanService` — через `save_archive()`
- `MainWindow` — создание сервиса при инициализации

### Автопарсинг иерархического хранилища (AutoScanService)

**Файл:** `dal/auto_scan_service.py`

**Структура хранилища:**
```
Корневой_каталог/
    YYYYMM/
        DD/
            *SMP_RWD_*.zip
```

**Компоненты:**
- `AutoScanService` — управление таймером и запуском сканирования
- `AutoScanWorker` (QThread) — фоновое сканирование без блокировки GUI
- `ScanResult` — результат сканирования (found, processed, skipped, added_records)

**Функции:**
- Периодическое сканирование по таймеру (QTimer, интервал в минутах)
- Рекурсивный обход с ограничением глубины (max_depth=5)
- Поиск ZIP-архивов по маске `*SMP_RWD_*.zip`
- Инкрементальная обработка: проверка `file_size` + `mtime`
- Сигналы прогресса: `progress`, `archive_processed`, `finished_scan`, `error`

**Настройки (.env):**
- `AUTO_SCAN_ENABLED=true` — включить автопарсинг
- `AUTO_SCAN_INTERVAL_MINUTES=10` — интервал сканирования
- `AUTO_SCAN_MAX_DEPTH=5` — максимальная глубина вложенности

**UI (HomeScreen):**
- Флажок «Автоматически импортировать новые архивы»
- Кнопка «Сканировать хранилище» (ручной запуск)
- Метка статуса сканирования
- Уведомления в статус-баре по завершении

### Таблица processed_archives

**Файл:** `dal/models/processed_archive.py`

**Поля:**
- `file_path` (UNIQUE) — полный путь к архиву
- `file_size` — размер в байтах
- `file_mtime` — время модификации
- `turbine_wtg_id` — WTG ID (если определён)
- `records_added` — количество добавленных записей
- `records_skipped` — количество пропущенных дубликатов
- `processed_at` — дата обработки

**Назначение:**
- Отслеживание уже обработанных архивов
- Инкрементальное сканирование (без повторной обработки)
- Определение изменённых архивов (по size + mtime)

### Уникальность серийного номера датчика (v1.4)

**Модель Archive (обновлена):**
- Добавлено поле `sensor_serial VARCHAR(50) NULL`
- Не входит в уникальный ключ по умолчанию
- Заполняется из первого поля строки 1 .rd2 файла

**Утилита анализа:** `utils/check_sensor_serial_uniqueness.py`
- Сканирует все .rd2 файлы в хранилище
- Анализирует уникальность sensor_serial:
  1. Глобальная уникальность
  2. Уникальность в пределах одного датчика
  3. Уникальность в пределах (датчик + фильтр)
- Генерирует JSON-отчёт `sensor_serial_analysis.json`
- Выводит рекомендацию по использованию в уникальном ключе

**Гибкость:**
- После подтверждения глобальной уникальности — миграция добавит `sensor_serial` в `uq_archive_unique_record`
- До подтверждения — поле собирает данные, но не влияет на дедупликацию

### Интеграция точек входа

| Точка входа | Действие |
|-------------|----------|
| Меню «Файл → Открыть» | `save_archive()` + QMessageBox с результатом |
| Кнопка «Проанализировать» (HomeScreen) | `save_archive()` для выбранного архива |
| Автопарсинг (таймер) | `save_archive()` для новых архивов в фоне |
| Утилита migrate_archives.py | `DataPersistenceService` (без GUI) |

### Статистика по ВЭУ (UploadInfoScreen)

**Обновления:**
- Убраны emoji из всех строк статуса
- Загрузка статистики из БД через `StatisticsWorker` (QThread)
- Отображение:
  - Всего записей в БД
  - Диапазон дат (первая/последняя запись)
  - Количество критических записей (зона D) с цветовой индикацией
  - Средний RMS датчика 1 с зоной ISO 10816

### Тренды (TrendsScreen)

**Обновления:**
- Убраны emoji из предупреждений и кнопок
- Заголовок «Тренды RMS по времени»
- Кнопка «Построить» (без символа play)
- Предупреждение: «Для отображения трендов требуется подключение к PostgreSQL»

### Миграция (Alembic)

**Файл:** `dal/alembic/versions/003_add_processed_archives_and_sensor_serial.py`

**Изменения:**
- Создание таблицы `processed_archives`
- Добавление колонки `sensor_serial` в `archives`
- Индексы: `idx_processed_path` (UNIQUE), `idx_processed_wtg`, `idx_archive_sensor_serial`

### Новые/изменённые файлы

```
app/
├── smp12c_vibrodiag/
│   ├── dal/
│   │   ├── persistence_service.py              ← Новый: единый сервис сохранения
│   │   ├── auto_scan_service.py                ← Новый: автопарсинг хранилища
│   │   ├── config.py                           ← Обновлён: AUTO_SCAN_ENABLED, INTERVAL, MAX_DEPTH
│   │   ├── models/
│   │   │   ├── __init__.py                     ← Обновлён: +ProcessedArchive
│   │   │   ├── archive.py                      ← Обновлён: +sensor_serial
│   │   │   └── processed_archive.py            ← Новый: модель processed_archives
│   │   ├── repositories/
│   │   │   └── postgres.py                     ← Обновлён: +sensor_serial в load_archive
│   │   └── alembic/versions/
│   │       └── 003_add_processed_archives_and_sensor_serial.py  ← Новый
│   ├── gui/
│   │   ├── main_window.py                      ← Обновлён: +DataPersistenceService, AutoScanService
│   │   ├── home_screen.py                      ← Обновлён: +автопарсинг UI, persistence_service
│   │   ├── upload_info_screen.py               ← Обновлён: убраны emoji
│   │   └── trends_screen.py                    ← Обновлён: убраны emoji
│   └── utils/
│       └── check_sensor_serial_uniqueness.py   ← Новый: утилита анализа
```

### Чеклист готовности v1.4

- [x] Таблицы с уникальными индексами создаются при первом запуске
- [x] Загрузка .rd2 и .zip сохраняет данные в БД, дубликаты пропускаются
- [x] Автопарсинг находит новые архивы в иерархии год/месяц/день
- [x] Статистика по ВЭУ отображается на экране «Информация о загрузке»
- [x] Тренды: выбор ВЭУ из 57, график RMS, среднее по ветропарку
- [x] GUI в чёрно-белой минималистичной теме (без emoji)
- [x] Файловый режим работает без ошибок (автопарсинг отключён)
- [x] Утилита проверки уникальности sensor_serial готова к использованию

---

## 🔜 Планы на v1.5

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
