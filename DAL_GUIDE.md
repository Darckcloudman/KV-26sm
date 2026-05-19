# SMP12C VibroDiag Analyzer v1.3 - Руководство по DAL

## Обзор изменений

Версия 1.3 добавляет **Data Access Layer (DAL)** - слой доступа к данным с поддержкой:
- ✅ Файловая система (.zip/.rd2) - режим работы v1.2
- ✅ PostgreSQL - новое в v1.3 для хранения больших объёмов данных

### Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                     UI (PySide6)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ HomeScreen   │  │ AnalysisData │  │ RawData      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                       │                                │
│              ┌────────▼────────┐                       │
│              │ IVibrationRepo  │ (интерфейс)           │
│              └────────┬────────┘                       │
└───────────────────────│────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────┐           ┌─────────▼────────┐
│ FileSystemRepo │           │  PostgresRepo    │
│   (режим v1.2) │           │   (режим v1.3)   │
└────────────────┘           └─────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   PostgreSQL    │
                              │  - turbines     │
                              │  - archives     │
                              │  - sensor_data  │
                              │  - analysis_cache│
                              └─────────────────┘
```

## Быстрый старт

### 1. Режим файловой системы (по умолчанию)

Ничего менять не нужно. Приложение работает как v1.2:

```bash
cd app
python -m smp12c_vibrodiag.main
```

### 2. Режим PostgreSQL

#### Шаг 1: Установите зависимости

```bash
pip install -r requirements.txt
```

#### Шаг 2: Настройте `.env`

```env
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vibrodiag
DB_USER=postgres
DB_PASSWORD=your_password
```

#### Шаг 3: Создайте базу данных

```bash
createdb -U postgres vibrodiag
```

#### Шаг 4: Запустите приложение

```bash
python -m smp12c_vibrodiag.main
```

Таблицы будут созданы автоматически при первом запуске.

## Миграции

### Автоматические миграции

При первом запуске с `USE_DATABASE=true` таблицы создаются автоматически.

### Ручные миграции (Alembic)

```bash
cd app/smp12c_vibrodiag/dal

# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

### Миграция существующих архивов в БД

```bash
# Тестовый режим (показать что будет сделано)
python migrate_archives.py --dry-run

# Реальная миграция
python migrate_archives.py --path ./test_data
```

## Структура DAL

```
dal/
├── __init__.py           # Экспорт настроек и DatabaseManager
├── config.py             # Настройки из .env (Pydantic)
├── database.py           # DatabaseManager (SQLAlchemy async)
├── utils.py              # Утилиты (проверка подключения, и т.д.)
│
├── models/               # SQLAlchemy модели
│   ├── __init__.py
│   ├── base.py           # Базовый класс DeclarativeBase
│   ├── turbine.py        # Модель турбины
│   ├── archive.py        # Модель архивной записи
│   ├── sensor_data.py    # Временные ряды датчиков
│   └── analysis_cache.py # Кэш результатов анализа
│
├── repositories/         # Репозитории
│   ├── __init__.py
│   ├── base.py           # IVibrationRepository (интерфейс)
│   ├── file_system.py    # FileSystemRepository
│   ├── postgres.py       # PostgresRepository
│   └── factory.py        # get_repository() фабрика
│
├── alembic/              # Миграции Alembic
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
│
└── alembic.ini           # Конфигурация Alembic
```

## API репозитория

### IVibrationRepository

```python
from dal.repositories import IVibrationRepository

class IVibrationRepository(ABC):
    async def load_archive(self, archive_path: Path) -> bool: ...
    async def get_turbine_metrics(self) -> Dict: ...
    async def get_sensor_data(self, sensor_id: int) -> Dict: ...
    async def get_spectrum(self, sensor_id: int, filter_type: str) -> Dict: ...
    async def get_analysis_results(self, sensor_id: int, filter_type: str) -> Dict: ...
    async def save_analysis_results(self, sensor_id: int, filter_type: str, results: Dict) -> bool: ...
    async def list_archives(self) -> List[Dict]: ...
    async def get_archive_parser(self, archive_path: str) -> Optional[MultiSensorRD2Parser]: ...
```

### Использование

```python
from dal.repositories import get_repository
from dal.config import settings

# Создание репозитория
repository = get_repository(settings)

# Загрузка архива
from pathlib import Path
success = await repository.load_archive(Path("archive.zip"))

# Получение данных датчика
sensor_data = await repository.get_sensor_data(sensor_id=1)

# Получение спектра
spectrum = await repository.get_spectrum(sensor_id=1, filter_type="HIGH")

# Получение результатов анализа
results = await repository.get_analysis_results(sensor_id=1, filter_type="HIGH")
```

## Модели данных

### Turbine
```python
id: int              # Первичный ключ
wtg_id: str          # WTG37
name: str            # Полное имя
created_at: datetime
```

### Archive
```python
id: int              # Первичный ключ
turbine_id: int      # Ссылка на турбину
file_path: str       # Путь к файлу
file_hash: str       # SHA256 для дедупликации
record_datetime: datetime
file_size_kb: int
created_at: datetime
```

### SensorData
```python
id: int              # Первичный ключ
archive_id: int      # Ссылка на архив
sensor_id: int       # 1-8
filter_type: str     # FILTER/LOW/HIGH
timestamps: float[]  # Временные метки
values: float[]      # Значения виброскорости
sampling_frequency: float
samples_count: int
```

### AnalysisCache
```python
id: int              # Первичный ключ
archive_id: int      # Ссылка на архив
sensor_id: int       # 1-8
filter_type: str     # FILTER/LOW/HIGH
rms_total: float     # СКЗ
zone: str            # A/B/C/D
peak: float
peak_to_peak: float
spectrum_frequencies: float[]
spectrum_amplitudes: float[]
peaks: JSON          # Топ пиков
analyzed_at: datetime
```

## Асинхронность и PyQt

PySide6/PyQt не поддерживает async/await напрямую. Используем паттерны:

### 1. QThread для async-кода

```python
class ParseThread(QThread):
    def run(self):
        import asyncio
        result = asyncio.run(self.repository.load_archive(path))
```

### 2. asyncio.to_thread() для блокирующих операций

```python
# В репозитории
async def load_archive(self, path: Path) -> bool:
    parser = await asyncio.to_thread(self._parse_sync, path)
```

## Производительность

### Оптимизации в v1.3

1. **Кэширование спектров** - результаты FFT сохраняются в БД
2. **Дедупликация архивов** - SHA256 хэш предотвращает дублирование
3. **Пул соединений** - SQLAlchemy pool_size=10, max_overflow=20
4. **ARRAY типы** - PostgreSQL ARRAY для временных рядов

### Рекомендации

- Для больших объёмов данных используйте индексы
- Настройте `DB_POOL_SIZE` под нагрузку
- Регулярно делайте VACUUM ANALYZE в PostgreSQL

## Откат к v1.2

Чтобы вернуться к режиму файловой системы:

1. Установите `USE_DATABASE=false` в `.env`
2. Перезапустите приложение

Все данные в БД сохраняются и могут быть использованы позже.

## Тестирование

```bash
# Проверка подключения к БД
python -m smp12c_vibrodiag.dal.utils check

# Удаление всех таблиц (осторожно!)
python -m smp12c_vibrodiag.dal.utils drop
```

## Поддержка

При возникновении проблем:

1. Проверьте `.env` настройки
2. Убедитесь, что PostgreSQL запущен
3. Проверьте логи приложения
4. Запустите `python -m smp12c_vibrodiag.dal.utils check`
