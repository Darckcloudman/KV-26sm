# Заметки разработчика v1.3

## Обзор изменений

Этот документ описывает технические изменения в версии 1.3 для разработчиков.

---

## Ключевые изменения

### 1. Инъекция зависимостей

**До (v1.2):**
```python
class HomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = None
```

**После (v1.3):**
```python
class HomeScreen(QWidget):
    def __init__(self, repository: IVibrationRepository, parent=None):
        super().__init__(parent)
        self.repository = repository  # ← Инъекция
        self.parser = None
```

### 2. Асинхронные операции

**Проблема:** PyQt/PySide не поддерживает async/await напрямую в слотах.

**Решение:** Обёртка в QThread:

```python
class ParseThread(QThread):
    def run(self):
        import asyncio
        # Запускаем async-код в отдельном потоке
        success = asyncio.run(self.repository.load_archive(path))
```

### 3. Паттерн Repository

**Интерфейс:**
```python
class IVibrationRepository(ABC):
    @abstractmethod
    async def load_archive(self, archive_path: Path) -> bool: ...
    @abstractmethod
    async def get_sensor_data(self, sensor_id: int) -> Dict: ...
    # ...
```

**Реализации:**
- `FileSystemRepository` - режим v1.2 (файлы)
- `PostgresRepository` - режим v1.3 (БД)

**Фабрика:**
```python
repository = get_repository(settings)
```

---

## Структура пакета dal/

```
dal/
├── __init__.py           # Экспорт settings, DatabaseManager
├── config.py             # Pydantic Settings (.env)
├── database.py           # DatabaseManager (SQLAlchemy async)
├── utils.py              # Утилиты (check, drop)
│
├── models/               # SQLAlchemy модели
│   ├── base.py           # DeclarativeBase
│   ├── turbine.py        # Турбины
│   ├── archive.py        # Архивы
│   ├── sensor_data.py    # Данные датчиков (ARRAY)
│   └── analysis_cache.py # Кэш анализа
│
├── repositories/         # Репозитории
│   ├── base.py           # IVibrationRepository
│   ├── file_system.py    # FileSystemRepository
│   ├── postgres.py       # PostgresRepository
│   └── factory.py        # get_repository()
│
└── alembic/              # Миграции
    ├── env.py
    ├── versions/
    │   └── 001_initial_schema.py
    └── alembic.ini
```

---

## Модели данных

### Turbine
```python
id: int              # PK
wtg_id: str          # WTG37 (unique)
name: str            # Полное имя
created_at: datetime
```

### Archive
```python
id: int              # PK
turbine_id: int      # FK -> turbines
file_path: str       # Путь к файлу
file_hash: str       # SHA256 (unique, для дедупликации)
record_datetime: datetime
file_size_kb: int
created_at: datetime
```

### SensorData
```python
id: int              # PK
archive_id: int      # FK -> archives
sensor_id: int       # 1-8
filter_type: str     # FILTER/LOW/HIGH
timestamps: float[]  # PostgreSQL ARRAY
values: float[]      # PostgreSQL ARRAY
sampling_frequency: float
samples_count: int
created_at: datetime

# Unique: (archive_id, sensor_id, filter_type)
```

### AnalysisCache
```python
id: int              # PK
archive_id: int      # FK -> archives
sensor_id: int       # 1-8
filter_type: str     # FILTER/LOW/HIGH
rms_total: float     # СКЗ
zone: str            # A/B/C/D
peak: float
peak_to_peak: float
spectrum_frequencies: float[]  # ARRAY
spectrum_amplitudes: float[]   # ARRAY
peaks: JSONB         # Топ пиков
analyzed_at: datetime

# Unique: (archive_id, sensor_id, filter_type)
```

---

## Работа с репозиторием

### Создание

```python
from dal.repositories import get_repository
from dal.config import settings

repository = get_repository(settings)
```

### Загрузка архива

```python
from pathlib import Path

success = await repository.load_archive(Path("archive.zip"))
```

### Получение данных

```python
# Данные датчика
sensor_data = await repository.get_sensor_data(sensor_id=1)

# Спектр
spectrum = await repository.get_spectrum(
    sensor_id=1,
    filter_type="HIGH"
)

# Результаты анализа
results = await repository.get_analysis_results(
    sensor_id=1,
    filter_type="HIGH"
)
```

### Сохранение результатов

```python
await repository.save_analysis_results(
    sensor_id=1,
    filter_type="HIGH",
    results={'rms_total': 3.5, 'zone': 'B', ...}
)
```

---

## Миграции

### Автоматические

При первом запуске с `USE_DATABASE=true`:
```python
db_manager = DatabaseManager(settings)
await db_manager.init_db()  # Создаёт таблицы
```

### Ручные (Alembic)

```bash
cd app/kwf_prometheus/dal

# Создать миграцию
alembic revision --autogenerate -m "Description"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```

---

## Тестирование

### Модульные тесты

```python
# tests/test_dal.py
import pytest
from dal.repositories import FileSystemRepository

@pytest.mark.asyncio
async def test_load_archive():
    repo = FileSystemRepository(Path("./test_data"))
    success = await repo.load_archive(Path("test.zip"))
    assert success
```

### Интеграционные тесты

```python
# tests/test_postgres.py
@pytest.mark.asyncio
async def test_postgres_repository():
    settings.use_database = True
    repo = get_repository(settings)
    
    await repo.load_archive(Path("test.zip"))
    metrics = await repo.get_turbine_metrics()
    
    assert metrics['power_kw'] > 0
```

---

## Производительность

### Кэширование

PostgresRepository автоматически кэширует:
- Спектры (spectrum_frequencies, spectrum_amplitudes)
- Результаты анализа (RMS, зона, пики)

При повторном запросе данные берутся из кэша.

### Дедупликация

Архивы проверяются по SHA256 хэшу:
```python
file_hash = hashlib.sha256(open(file, 'rb').read()).hexdigest()

# Проверка в БД
existing = await session.execute(
    select(Archive).where(Archive.file_hash == file_hash)
)
```

### Пул соединений

```python
# database.py
self.engine = create_async_engine(
    url,
    pool_size=10,        # Соединений в пуле
    max_overflow=20,     # Дополнительные соединения
    pool_pre_ping=True,  # Проверка перед использованием
)
```

---

## Отладка

### Логирование SQL

В `.env`:
```env
DB_ECHO=true
```

SQLAlchemy будет выводить все SQL-запросы.

### Проверка подключения

```bash
python -m kwf_prometheus.dal.utils check
```

### Удаление таблиц

```bash
python -m kwf_prometheus.dal.utils drop
```

---

## Расширение функциональности

### Добавление нового поля в модель

1. Измените модель:
```python
# models/archive.py
class Archive(Base):
    # ...
    new_field: Mapped[str] = mapped_column(String(100))
```

2. Создайте миграцию:
```bash
alembic revision --autogenerate -m "Add new_field to archive"
```

3. Примените миграцию:
```bash
alembic upgrade head
```

### Добавление нового метода репозитория

1. Обновите интерфейс:
```python
# repositories/base.py
class IVibrationRepository(ABC):
    @abstractmethod
    async def new_method(self, ...) -> ...: ...
```

2. Реализуйте в FileSystemRepository и PostgresRepository

3. Обновите фабрику если нужно

---

## Сборка EXE

### Обновление зависимостей

```bash
# requirements.txt уже обновлён
pip install -r requirements.txt
```

### Сборка

```bash
python setup.py build_exe
```

**Важно:** Убедитесь, что SQLAlchemy и asyncpg включены в hiddenimports.

---

## Частые ошибки

### "No module named 'dal'"

**Решение:** Проверьте, что dal/ находится внутри kwf_prometheus/

### "could not connect to server"

**Решение:** PostgreSQL не запущен

### "table already exists"

**Решение:** Нормально, таблицы создаются один раз

### "asyncio.run() called in an async environment"

**Решение:** Event loop уже запущен (например, в PyQt). Используйте:
```python
loop = asyncio.get_event_loop()
loop.run_until_complete(coro)
```

---

## Ресурсы

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/current/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/)
