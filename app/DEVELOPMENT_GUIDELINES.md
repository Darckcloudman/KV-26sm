# Руководство по разработке SMP12C VibroDiag Analyzer

## ЗАПРЕЩЕНО: Emoji в коде

**Никогда не используйте emoji (символы Юникода вида 😀⚙️📊🔧) в:**
- Текстах интерфейса (заголовки, кнопки, метки)
- Комментариях к коду
- Именах переменных и функций
- Документации (включая заголовки разделов)
- Строковых константах и сообщениях об ошибках

**Почему:**
- Проблемы с кодировкой на Windows (особенно в PowerShell, консоли)
- Непредсказуемое отображение на разных системах
- Усложнение парсинга и локализации
- Профессиональный стиль кода

**Чем заменять:**

| Смысл | Замена (QtAwesome) | Код |
|-------|-------------------|-----|
| Настройки | `mdi.cog` | `qta.icon('mdi.cog')` |
| Диаграмма | `mdi.chart-bar` | `qta.icon('mdi.chart-bar')` |
| Папка | `mdi.folder` | `qta.icon('mdi.folder')` |
| База данных | `mdi.database` | `qta.icon('mdi.database')` |
| Документ | `mdi.file-document` | `qta.icon('mdi.file-document')` |
| Инструменты | `mdi.wrench` | `qta.icon('mdi.wrench')` |
| Успех | `mdi.check-circle` | `qta.icon('mdi.check-circle')` |
| Ошибка | `mdi.close-circle` | `qta.icon('mdi.close-circle')` |
| Предупреждение | `mdi.alert` | `qta.icon('mdi.alert')` |
| Информация | `mdi.information` | `qta.icon('mdi.information')` |
| Помощь | `mdi.help-circle` | `qta.icon('mdi.help-circle')` |
| Поиск | `mdi.magnify` | `qta.icon('mdi.magnify')` |
| Тренд вверх | `mdi.trending-up` | `qta.icon('mdi.trending-up')` |
| Сохранить | `mdi.content-save` | `qta.icon('mdi.content-save')` |
| Обновить | `mdi.refresh` | `qta.icon('mdi.refresh')` |
| Домой | `mdi.home` | `qta.icon('mdi.home')` |
| Дубликат | `mdi.content-duplicate` | `qta.icon('mdi.content-duplicate')` |
| Устройство | `mdi.developer-board` | `qta.icon('mdi.developer-board')` |
| Серийный номер | `mdi.barcode` | `qta.icon('mdi.barcode')` |
| MAC-адрес | `mdi.network` | `qta.icon('mdi.network')` |

**Пример:**
```python
# ПЛОХО:
title = QLabel("⚙ Настройки")
btn = QPushButton("📁 Открыть")

# ХОРОШО:
import qtawesome as qta
title = QLabel("Настройки")
btn = QPushButton()
btn.setIcon(qta.icon('mdi.folder', color='#FFFFFF'))
btn.setText("Открыть")
```

---

## Дедупликация записей (v1.4)

### Правила уникальности

**Турбина (таблица turbines):**
- `serial_number` — уникален глобально (главный идентификатор прибора)
- `mac_address` — уникален глобально (резервный идентификатор)
- `wtg_id` — уникален локально (человеко-читаемое имя)

**Архив (таблица archives):**
- Уникальный ключ: `(turbine_id, record_datetime, sensor_id, filter_type)`
- Один прибор не может в одно время с одного датчика создать два файла с одинаковым фильтром

### Алгоритм загрузки

```python
async def load_archive(self, archive_path: Path) -> Dict[str, Any]:
    # 1. Парсим файл, извлекаем метаданные прибора
    device_info = {
        'serial_number': metadata.get('device_serial'),
        'mac_address': metadata.get('mac_address'),
        'ip_address': metadata.get('ip_address'),
        'device': metadata.get('device'),
        'firmware_version': metadata.get('firmware_version'),
    }
    
    # 2. Ищем или создаём турбину
    turbine = await self._get_or_create_turbine(session, wtg_id, device_info)
    
    # 3. Для каждого датчика и фильтра проверяем уникальность
    existing = await self._find_archive_by_unique_key(
        session, turbine.id, record_datetime, sensor_id, filter_type
    )
    
    if existing:
        # Пропускаем дубликат
        result['skipped'] += 1
        continue
    
    # 4. Сохраняем новую запись
    result['added'] += 1
```

### Обработка конфликтов

**Конфликт serial_number ↔ wtg_id:**
```python
if turbine.wtg_id != wtg_id:
    raise ValueError(
        f"Несоответствие: прибор с серийным номером {serial_number} "
        f"уже привязан к турбине {turbine.wtg_id}, "
        f"но текущий файл содержит турбину {wtg_id}. "
        f"Загрузка отменена."
    )
```

**UI-обработка:**
- Показывать критическое сообщение через `show_critical()`
- Не блокировать загрузку остальных файлов в архиве
- Логировать ошибку с уровнем ERROR

### Возврат результата

Метод `load_archive` возвращает словарь:
```python
{
    'success': bool,      # Общий успех операции
    'added': int,         # Количество добавленных записей
    'skipped': int,       # Количество пропущенных дубликатов
    'errors': List[str],  # Список ошибок (конфликты, парсинг)
}
```

---

## Идентификация прибора SMP12C

### Метаданные из .rd2 файла

| Поле | Строка заголовка | Уникальность | Использование |
|------|-----------------|--------------|---------------|
| serial_number | Строка 4: Serial Number | Глобально уникален | Главный идентификатор |
| mac_address | Строка 4: MAC | Глобально уникален | Резервный идентификатор |
| device | Строка 4: Device | — | Модель (12C) |
| firmware_version | Строка 4: Firmware version | — | Версия прошивки |
| ip_address | Строка 4: IP | Может меняться | Последний известный IP |
| wtg_id | Строка 1: WTG ID | Локально уникален | Человеко-читаемое имя |

### Порядок поиска турбины

1. **По serial_number** — главный идентификатор
2. **По mac_address** — если serial не найден
3. **По wtg_id** — если прибор ещё не зарегистрирован

### Обновление данных

При повторной загрузке от того же прибора:
- `ip_address` — обновляется (может меняться)
- `firmware_version` — обновляется
- `mac_address` — обновляется если был пуст
- `serial_number` — обновляется если был пуст
- `wtg_id` — **никогда не меняется** (привязка постоянна)

---

## Библиотека иконок QtAwesome

**Установка:**
```bash
pip install qtawesome>=1.4.0
```

**Использование:**
```python
import qtawesome as qta

# Базовая иконка
icon = qta.icon('mdi.cog', color='#FFFFFF')

# Иконка с размером
pixmap = qta.icon('mdi.database').pixmap(24, 24)
label.setPixmap(pixmap)

# Анимированная иконка
spin_icon = qta.icon('mdi.loading', color='#FFC107', spin=True)
```

**Поиск иконок:**
- [Material Design Icons](https://pictogrammers.com/library/mdi/)
- [Font Awesome](https://fontawesome.com/icons)
- Префиксы: `mdi.*` (Material), `fa.*` (Font Awesome)

---

## Цветовая палитра (ui_styles.py)

**Основные цвета:**
```python
COLOR_BG_PRIMARY = "#000000"      # Основной фон
COLOR_BG_SECONDARY = "#1A1A1A"    # Вторичный фон
COLOR_BG_TERTIARY = "#2A2A2A"     # Третичный фон

COLOR_TEXT_PRIMARY = "#FFFFFF"    # Основной текст
COLOR_TEXT_SECONDARY = "#BBBBBB"  # Вторичный текст
COLOR_TEXT_TERTIARY = "#888888"   # Третичный текст

COLOR_ACCENT = "#FFFFFF"          # Акцент (кнопки)
COLOR_BORDER = "#333333"          # Границы
```

**Зоны ISO 10816:**
```python
ZONE_COLORS = {
    'A': '#00C853',   # Зелёный — норма
    'B': '#FFD600',   # Жёлтый — внимание
    'C': '#FF6D00',   # Оранжевый — требует внимания
    'D': '#DD2C00',   # Красный — критично
}
```

**Использование стилей:**
```python
from .ui_styles import BUTTON_STYLE, PANEL_STYLE, COLOR_ACCENT

btn = QPushButton("Сохранить")
btn.setStyleSheet(BUTTON_STYLE)

panel = QFrame()
panel.setStyleSheet(PANEL_STYLE)
```

---

## Архитектура GUI

### Структура экранов:
```
MainWindow (QMainWindow)
├── MenuBar (Файл, Анализ, Настройки, Справка)
├── CentralWidget
│   └── QTabWidget
│       ├── HomeScreen (выбор архива)
│       ├── UploadInfoScreen (информация о загрузке)
│       ├── RawDataScreen (сырые данные)
│       ├── AnalysisDataScreen (анализ)
│       └── TrendsScreen (тренды RMS)
└── StatusBar (иконка + прогресс + время)
```

### Навигация:
```python
# Переход между экранами
self.tabs.setCurrentWidget(self.target_screen)

# Обновление статуса
self.status_icon.setToolTip("Загрузка...")
self._update_status_icon('loading')
```

### Асинхронные операции:
```python
# QThread для фоновых задач
class MyWorker(QThread):
    result_ready = Signal(object)
    
    def run(self):
        result = asyncio.run(self.repository.some_method())
        self.result_ready.emit(result)

# Использование
worker = MyWorker(self.repository)
worker.result_ready.connect(self._on_result)
worker.start()
```

---

## Стиль кода

### Именование:
```python
# Классы: PascalCase
class SettingsDialog(QDialog): ...

# Функции/методы: snake_case
def load_settings(self): ...

# Переменные: snake_case
archive_path = Path(...)

# Константы: UPPER_SNAKE_CASE
MAX_RETRIES = 3
```

### Документирование:
```python
def get_turbine_statistics(self, wtg_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить статистику по конкретной ВЭУ.
    
    Args:
        wtg_id: Идентификатор турбины (например, 'WTG37').
        
    Returns:
        Словарь со статистикой или None.
    """
```

### Обработка ошибок:
```python
try:
    result = await self.repository.get_data()
except Exception as e:
    logger.error("Ошибка получения данных: %s", e, exc_info=True)
    show_critical(self, "Ошибка", f"Не удалось загрузить данные:\n{str(e)}")
```

---

## Тестирование

### Запуск тестов:
```bash
cd app
python -m pytest tests/ -v
```

### Покрытие:
```bash
python -m pytest tests/ --cov=smp12c_vibrodiag --cov-report=html
```

---

## Сборка

### EXE:
```bash
python setup.py build_exe
```

### Проверка зависимостей:
```bash
pip check
```

---

## Безопасность

**Никогда не коммитьте:**
- Пароли от БД
- API ключи
- Личные данные
- Файлы `.env` (добавьте в `.gitignore`)

**Пример `.gitignore`:**
```gitignore
.env
__pycache__/
*.pyc
venv/
build/
dist/
*.log
```

---

## Единый сервис сохранения данных (DataPersistenceService)

### Архитектура

`DataPersistenceService` — фасад над `PostgresRepository`, обеспечивающий единый интерфейс для всех точек входа:

```python
class DataPersistenceService:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository
    
    async def save_archive(self, archive_path: Path) -> Dict[str, Any]:
        # Возвращает: {success, added, skipped, errors, wtg_id}
```

### Точки входа

| Компонент | Как использует DataPersistenceService |
|-----------|--------------------------------------|
| `HomeScreen` | Через `ParseThread` (опционально) |
| `AutoScanService` | Напрямую `save_archive()` |
| `migrate_archives.py` | Напрямую `save_archive()` |

### Результат сохранения

```python
{
    'success': bool,      # Общий успех
    'added': int,         # Добавлено записей
    'skipped': int,       # Пропущено дубликатов
    'errors': List[str],  # Ошибки
    'wtg_id': Optional[str],  # Идентификатор ВЭУ
}
```

### Обработка ZIP-архивов

1. Распаковка во временную папку (`tempfile.mkdtemp`)
2. Поиск всех `.rd2` файлов (`rglob("*.rd2")`)
3. Обработка каждого файла через `repository.load_archive()`
4. Автоматическая очистка временной папки (`shutil.rmtree`)

### Инкрементальная обработка

Таблица `processed_archives` отслеживает уже обработанные ZIP-архивы:
- `file_path` — полный путь (уникальный ключ)
- `file_size` + `file_mtime` — для определения изменений
- `records_added`, `records_skipped` — статистика

При повторном сканировании:
1. Проверяем наличие записи в `processed_archives`
2. Сравниваем `size` и `mtime`
3. Если совпадают — пропускаем архив
4. Если изменился — обрабатываем заново

---

## Автопарсинг иерархического хранилища (AutoScanService)

### Структура хранилища

```
Корневой_каталог/
    YYYYMM/              # Год + месяц
        DD/              # День
            *SMP_RWD_*.zip
```

### Компоненты

**AutoScanService:**
- Управляет таймером `QTimer` (интервал в минутах)
- Создаёт `AutoScanWorker` для фонового сканирования
- Обрабатывает сигналы прогресса и завершения

**AutoScanWorker (QThread):**
- Рекурсивный обход каталога (`Path.rglob`)
- Ограничение глубины (`max_depth=5`)
- Асинхронная обработка каждого архива через `DataPersistenceService`
- Сигналы: `progress`, `archive_processed`, `finished_scan`, `error`

### Настройки (.env)

```bash
AUTO_SCAN_ENABLED=true              # Включить автопарсинг
AUTO_SCAN_INTERVAL_MINUTES=10       # Интервал сканирования
AUTO_SCAN_MAX_DEPTH=5               # Максимальная глубина вложенности
```

### Интеграция с GUI

**HomeScreen:**
- Флажок «Автоматически импортировать новые архивы»
- Кнопка «Сканировать хранилище» (ручной запуск)
- Метка статуса сканирования

**MainWindow:**
- Создаёт `DataPersistenceService` и `AutoScanService` при инициализации
- Передаёт сервисы в `HomeScreen`
- Запускает автопарсинг если `USE_DATABASE=true`

### Алгоритм сканирования

```python
def _find_archives(self) -> List[Path]:
    archives = []
    for path in self.root_path.rglob("*SMP_RWD_*.zip"):
        relative = path.relative_to(self.root_path)
        depth = len(relative.parts) - 1
        if depth <= self.max_depth:
            archives.append(path)
    return sorted(archives)
```

---

## Уникальность серийного номера датчика (v1.4)

### Поле sensor_serial

Добавлено в модель `Archive`:
```python
sensor_serial: Mapped[Optional[str]] = mapped_column(
    String(50), nullable=True,
    comment="Серийный номер датчика (для анализа уникальности)"
)
```

### Статус

- **По умолчанию:** не входит в уникальный ключ
- **Заполняется:** из первого поля строки 1 .rd2 файла
- **Анализ:** через `utils/check_sensor_serial_uniqueness.py`

### Утилита проверки

```bash
python -m smp12c_vibrodiag.utils.check_sensor_serial_uniqueness D:\WindFarmData
```

**Вывод:**
- Глобальная уникальность sensor_serial
- Уникальность в пределах одного датчика
- Уникальность в пределах (датчик + фильтр)
- Рекомендация по использованию

### Решение по результатам анализа

| Результат | Действие |
|-----------|----------|
| Глобально уникален | Миграция добавляет `sensor_serial` в `uq_archive_unique_record` |
| Уникален в пределах датчика | Использовать как вспомогательный идентификатор |
| Не уникален | Игнорировать для дедупликации |

---

## Дополнительные ресурсы

- [Qt for Python (PySide6) Documentation](https://doc.qt.io/qtforpython-6/)
- [QtAwesome GitHub](https://github.com/spyder-ide/qtawesome)
- [Material Design Icons](https://pictogrammers.com/library/mdi/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
