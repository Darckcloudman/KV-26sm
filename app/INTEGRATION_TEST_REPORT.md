# Отчёт о тестировании интеграции SMP12C VibroDiag Analyzer v1.4

**Дата:** 2026-05-21
**Версия приложения:** v1.4
**Автор:** A.Telezhenko

---

## 1. Тестовое окружение

| Компонент | Версия / Значение |
|-----------|-------------------|
| ОС | Windows 11 |
| Python | 3.11.9 |
| PostgreSQL | 16 (Docker) |
| SQLAlchemy | 2.0+ |
| PySide6 | 6.6+ |
| Путь к локальным тестовым данным | `./test_data/` |
| Путь к хранилищу Кольской ВЭС | `D:\Работа [Кольская ВЭС]\SMP_SGRE\RAW_DATA` (недоступен из среды ИИ) |

---

## 2. Найденные и исправленные ошибки

### 2.1 Критическая: недостижимый код в `postgres.py`

**Файл:** `app/smp12c_vibrodiag/dal/repositories/postgres.py`
**Строки:** 137–149

**Проблема:** После `return result` в блоке проверки `parser._parsed` весь последующий код загрузки в БД был смещён на 1 уровень отступа вправо, делая его недостижимым. Приложение "успешно" парсило файл, но никогда не сохраняло данные в PostgreSQL.

```python
# Было (неверно):
if not parser or not parser._parsed:
    ...
    return result

    # Получаем метаданные прибора      # ← этот код НИКОГДА не выполнялся!
    metadata = parser.turbine_metadata or {}
```

**Исправление:** Убран лишний отступ, код возвращён на уровень `try`-блока.

### 2.2 Критическая: отсутствует `sensor_serial` в парсере

**Файл:** `app/smp12c_vibrodiag/parsers/rd2_parser.py`

**Проблема:** Поле `sensor_serial` (первое поле строки 1 .rd2 файла) не извлекалось парсером, хотя использовалось в `PostgresRepository` и в тестах уникальности.

**Исправление:** Добавлено:
```python
self.metadata['sensor_serial'] = line1[0]  # v1.4: серийный номер датчика
```

### 2.3 Средняя: отсутствует `logger` в `home_screen.py`

**Файл:** `app/smp12c_vibrodiag/gui/home_screen.py`

**Проблема:** Метод `_on_load_result` использовал `logger.error()` / `logger.info()`, но `logger` не был импортирован.

**Исправление:** Добавлен импорт:
```python
from ..dal.logger import get_logger
logger = get_logger("HomeScreen")
```

---

## 3. Созданные интеграционные тесты

**Файл:** `app/tests/test_integration.py` (811 строк)

| Тест | Описание | Статус (код) |
|------|----------|-------------|
| `TestSaveSingleRD2::test_save_single_rd2` | Сохранение одного .rd2, проверка таблиц turbines, archives, sensor_data, analysis_cache | ✅ Написан |
| `TestSaveSingleRD2::test_turbine_device_info` | Проверка извлечения wtg_id, serial_number, MAC | ✅ Написан |
| `TestSaveZipArchive::test_save_zip_archive` | Сохранение ZIP с ~24 .rd2, проверка дедупликации по прибору | ✅ Написан |
| `TestDeduplication::test_duplicate_rd2_skipped` | Повторное сохранение .rd2 → skipped, added=0 | ✅ Написан |
| `TestDeduplication::test_duplicate_zip_skipped` | Повторное сохранение ZIP → пропуск через processed_archives | ✅ Написан |
| `TestDeviceIdentification::test_same_device_same_turbine` | Один serial → одна турбина | ✅ Написан |
| `TestAutoScan::test_scan_directory` | Сканирование иерархии YYYYMM/DD/*.zip | ✅ Написан |
| `TestAutoScan::test_incremental_scan` | Инкрементальное сканирование (только новые) | ✅ Написан |
| `TestTurbineStatistics::test_get_turbine_statistics` | Статистика: архивы, даты, RMS, критические | ✅ Написан |
| `TestRMSTrends::test_get_rms_trend_single_turbine` | Тренд RMS для конкретной ВЭУ | ✅ Написан |
| `TestRMSTrends::test_get_rms_trend_aggregated` | Агрегированный тренд по парку | ✅ Написан |
| `TestSensorSerialUniqueness::test_sensor_serial_extraction` | Извлечение sensor_serial из .rd2 | ✅ Написан |
| `TestSensorSerialUniqueness::test_sensor_serial_matches_record_number` | Проверка соответствия record_number | ✅ Написан |
| `TestPerformance::test_single_zip_load_time` | ZIP < 3 секунд | ✅ Написан |
| `TestPerformance::test_single_rd2_load_time` | .rd2 < 1 секунды | ✅ Написан |

---

## 4. Инфраструктура тестирования

| Файл | Назначение |
|------|-----------|
| `app/.env.test` | Конфигурация тестовой БД (vibrodiag_test_kola) |
| `app/docker-compose.test.yml` | PostgreSQL 16 в Docker |
| `app/run_integration_tests.ps1` | PowerShell-скрипт: запускает БД, миграции, тесты |
| `app/pytest.ini` | asyncio_mode = auto, маркеры |
| `app/requirements.txt` | +pytest, +pytest-asyncio |

---

## 5. Запуск тестов (инструкция для пользователя)

### 5.1 Установить Docker Desktop

### 5.2 Запустить тесты одной командой:
```powershell
cd app
powershell -ExecutionPolicy Bypass -File .\run_integration_tests.ps1
```

### 5.3 Или вручную:
```powershell
# 1. Запустить PostgreSQL
docker-compose -f docker-compose.test.yml up -d

# 2. Применить миграции
alembic -c smp12c_vibrodiag/dal/alembic.ini upgrade head

# 3. Запустить тесты
$env:PYTHONPATH = "."
pytest tests/test_integration.py -v
```

---

## 6. Проверка существующих unit-тестов

```
tests/test_utils.py    : 16 passed
tests/test_exporters.py:  6 passed, 1 skipped
tests/test_reports.py  :  4 passed, 1 skipped
-------------------------------------------
Итого                  : 26 passed, 2 skipped
```

**Статус:** Регрессий нет. Все существующие тесты проходят.

---

## 7. Рекомендации по дальнейшему тестированию на Кольской ВЭС

1. **Установить PostgreSQL** на рабочей станции (или использовать Docker).
2. **Скопировать подмножество архивов** (~10–20 ZIP) из `D:\Работа [Кольская ВЭС]\SMP_SGRE\RAW_DATA` в `./test_data/kola/` для офлайн-тестирования.
3. **Запустить интеграционные тесты** и проверить:
   - Корректность извлечения `wtg_id` из имён файлов
   - Уникальность `serial_number` приборов (WTG6 vs WTG8 и т.д.)
   - Производительность на реальных архивах (ожидается < 3 сек/архив)
4. **Если `sensor_serial` окажется глобально уникальным** — добавить его в составной уникальный индекс `uq_archive_unique_record` через Alembic-миграцию.
5. **Настроить `AUTO_SCAN_INTERVAL_MINUTES = 60`** для production.

---

## 8. Итоговый статус

| Критерий | Статус |
|----------|--------|
| Исправлены критические баги в DAL | ✅ |
| Написаны интеграционные тесты (15 тестов) | ✅ |
| Подготовлена инфраструктура (Docker, скрипты) | ✅ |
| Unit-тесты не сломаны | ✅ |
| Код запушен на GitHub | ✅ |

**Приложение готово к тестированию на реальных данных Кольской ВЭС.**

---

## 9. Список изменённых файлов

```
app/smp12c_vibrodiag/dal/repositories/postgres.py   ← Исправлены отступы (критично)
app/smp12c_vibrodiag/parsers/rd2_parser.py           ← +sensor_serial
app/smp12c_vibrodiag/gui/home_screen.py              ← +import logger
app/tests/test_integration.py                        ← Новый (15 тестов)
app/.env.test                                        ← Новый
app/docker-compose.test.yml                          ← Новый
app/run_integration_tests.ps1                        ← Новый
app/pytest.ini                                       ← +asyncio_mode
app/requirements.txt                                 ← +pytest, +pytest-asyncio
```
